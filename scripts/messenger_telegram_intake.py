#!/usr/bin/env python3
"""Telegram reply-intake adapter for FilmNet Messenger.

Polls Telegram Bot API updates and writes inbound human replies as append-only
JSONL events to inbox/messenger-events.jsonl. It is intentionally NOT a Hermes
gateway session: recipient text is never passed to an LLM as a command, so team
members can reply without being granted agent-control access.

Secrets are read from the messenger bot env and never printed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import messenger_common as mc  # noqa: E402

ROOT = mc.ROOT
TEAM_CONTACTS = ROOT / "resources/filmnet/team-contacts.md"
REQUESTS_PATH = ROOT / "inbox/messenger-send-requests.jsonl"
EVENTS_PATH = ROOT / "inbox/messenger-events.jsonl"
STATE_PATH = ROOT / "inbox/messenger-telegram-intake-state.json"


def load_state() -> Dict[str, Any]:
    data = mc.load_json_state(STATE_PATH, {"last_update_id": None, "processed_update_ids": []})
    if not isinstance(data.get("processed_update_ids"), list):
        data["processed_update_ids"] = []
    return data


def save_state(state: Dict[str, Any]) -> None:
    state["processed_update_ids"] = list(dict.fromkeys(state.get("processed_update_ids", [])))[-500:]
    mc.save_json_state(STATE_PATH, state)


def contact_key(raw_key: str) -> str:
    return raw_key.strip().lower().replace(" ", "_").replace("-", "_")


def clean_contact_value(value: str) -> str:
    return value.strip().replace("\\[", "[").replace("\\]", "]")


def parse_contact_line(raw: str) -> Optional[Dict[str, str]]:
    """Parse one-line CONTACT records from resources/filmnet/team-contacts.md."""
    line = raw.strip()
    if not line.startswith("CONTACT |"):
        return None
    contact: Dict[str, str] = {}
    for part in line.split("|")[1:]:
        if "=" not in part:
            continue
        raw_key, raw_value = part.split("=", 1)
        key = contact_key(raw_key)
        value = clean_contact_value(raw_value)
        if key == "telegram":
            contact["telegram_username"] = value
        elif key == "name_fa":
            contact["name_fa"] = value
        elif key == "family_fa":
            contact["family_fa"] = value
        elif key == "telegram_id":
            contact["telegram_id"] = value
        else:
            contact[key] = value
    return contact


def parse_team_contacts(path: Path = TEAM_CONTACTS) -> Dict[str, Dict[str, str]]:
    """Return contacts keyed by Telegram ID as string."""
    if not path.exists():
        return {}
    contacts: Dict[str, Dict[str, str]] = {}
    current: Optional[Dict[str, str]] = None
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line_contact = parse_contact_line(raw)
        if line_contact is not None:
            telegram_id = line_contact.get("telegram_id", "")
            if telegram_id and "to be filled" not in telegram_id:
                contacts[telegram_id] = line_contact
            continue
        if raw.startswith("### "):
            if current and current.get("telegram_id") and "to be filled" not in current["telegram_id"]:
                contacts[current["telegram_id"]] = current
            current = {"name": raw[4:].strip()}
            continue
        if current is None:
            continue
        m = re.match(r"-\s*([^:]+):\s*(.*)$", raw.strip())
        if not m:
            continue
        key = contact_key(m.group(1))
        value = clean_contact_value(m.group(2))
        if key == "telegram_id":
            current["telegram_id"] = value
        elif key == "telegram":
            current["telegram_username"] = value
        elif key == "name_fa":
            current["name_fa"] = value
        elif key == "family_fa":
            current["family_fa"] = value
        elif key == "role":
            current["role"] = value
    if current and current.get("telegram_id") and "to be filled" not in current["telegram_id"]:
        contacts[current["telegram_id"]] = current
    return contacts


def answered_keys(events: Iterable[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    """(request_id, telegram_id) pairs that already have a reply."""
    answered: Set[Tuple[str, str]] = set()
    for event in events:
        if event.get("event") != "reply_received":
            continue
        request_id = str(event.get("request_id") or "").strip()
        sender_id = str((event.get("sender") or {}).get("telegram_id") or "").strip()
        if not sender_id:
            sender_id = str(event.get("recipient_telegram_id") or "").strip()
        if request_id and sender_id:
            answered.add((request_id, sender_id))
    return answered


def sent_request_index() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Build indexes for matching replies to a sent request.

    Returns:
      by_telegram_id: latest reply-tracked, still-unanswered send request per
                      recipient Telegram ID (so a person's next message does not
                      keep matching a request they already answered)
      by_platform_message_id: send request by Telegram sent message id
    """
    requests = mc.read_jsonl(REQUESTS_PATH)
    events = mc.read_jsonl(EVENTS_PATH)
    request_by_id = {r.get("request_id"): r for r in requests if r.get("request_id")}
    answered = answered_keys(events)

    by_telegram_id: Dict[str, Dict[str, Any]] = {}
    by_platform_message_id: Dict[str, Dict[str, Any]] = {}
    for event in events:
        if event.get("event") != "delivery_result" or event.get("status") != "sent":
            continue
        request_id = event.get("request_id")
        req = request_by_id.get(request_id)
        if not req:
            continue
        if not req.get("reply_tracking", {}).get("required"):
            continue
        telegram_id = str(event.get("recipient_telegram_id") or "").strip()
        if not telegram_id:
            recipient_index = event.get("recipient_index")
            if isinstance(recipient_index, int):
                recipients = mc.normalize_recipients(req)
                if 1 <= recipient_index <= len(recipients):
                    telegram_id = str(recipients[recipient_index - 1].get("telegram_id") or "").strip()
            if not telegram_id:
                telegram_id = str(req.get("recipient", {}).get("telegram_id") or "").strip()
        if telegram_id and "to be filled" not in telegram_id.lower():
            if (str(request_id), telegram_id) not in answered:
                by_telegram_id[telegram_id] = req  # latest unanswered wins
        platform_message_id = event.get("platform_message_id")
        if platform_message_id is not None:
            by_platform_message_id[str(platform_message_id)] = req
    return by_telegram_id, by_platform_message_id


def telegram_get_updates(token: str, offset: Optional[int], timeout: int) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "timeout": timeout,
        "allowed_updates": json.dumps(["message", "edited_message"]),
    }
    if offset is not None:
        params["offset"] = offset
    url = f"https://api.telegram.org/bot{token}/getUpdates?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout + 10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        # Do not print the URL because it contains the bot token.
        raise RuntimeError(f"Telegram getUpdates HTTP {exc.code}: {body[:500]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Telegram getUpdates failed: {type(exc).__name__}: {exc}") from exc
    data = json.loads(body)
    if not data.get("ok"):
        raise RuntimeError(f"Telegram getUpdates returned ok=false: {data.get('description', 'unknown error')}")
    return data.get("result", [])


def extract_message(update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return update.get("message") or update.get("edited_message")


def make_event(update: Dict[str, Any], contacts: Dict[str, Dict[str, str]], by_user: Dict[str, Dict[str, Any]], by_reply_msg: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    message = extract_message(update)
    if not message:
        return None
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    sender_id = str(sender.get("id") or chat.get("id") or "").strip()
    if not sender_id:
        return None
    if sender.get("is_bot"):
        return None

    text = message.get("text") or message.get("caption") or ""
    message_id = message.get("message_id")
    chat_id = chat.get("id")
    reply_to = message.get("reply_to_message") or {}
    reply_to_message_id = reply_to.get("message_id")
    is_edit = "edited_message" in update

    contact = contacts.get(sender_id)
    matched_request = None
    match_reason = None
    if reply_to_message_id is not None and str(reply_to_message_id) in by_reply_msg:
        matched_request = by_reply_msg[str(reply_to_message_id)]
        match_reason = "reply_to_platform_message_id"
    elif sender_id in by_user:
        matched_request = by_user[sender_id]
        match_reason = "latest_unanswered_reply_tracked_request_for_sender"

    username = sender.get("username")
    sender_meta = {
        "telegram_id": sender_id,
        "telegram_username": ("@" + str(username)) if username else None,
        "first_name": sender.get("first_name"),
        "last_name": sender.get("last_name"),
        "chat_id": str(chat_id) if chat_id is not None else None,
        "chat_type": chat.get("type"),
        "known_contact": bool(contact),
        "contact_name": contact.get("name") if contact else None,
        "contact_name_fa": contact.get("name_fa") if contact else None,
    }

    # Stable per-message id so an edited reply dedupes against the original
    # instead of generating a second reply_received notification.
    if chat_id is not None and message_id is not None:
        event_id = f"tgmsg-{chat_id}-{message_id}"
    else:
        event_id = f"tgu-{update.get('update_id')}-{message_id}"

    base = {
        "event_id": event_id,
        "request_id": matched_request.get("request_id") if matched_request else None,
        "task_id": matched_request.get("task_id") if matched_request else None,
        "recipient": (contact.get("name") if contact else None) or (matched_request.get("recipient", {}).get("name") if matched_request else None),
        "recipient_telegram_id": sender_id if matched_request else None,
        "channel": "telegram",
        "received_at": mc.utc_now(),
        "platform_update_id": update.get("update_id"),
        "platform_message_id": str(message_id) if message_id is not None else None,
        "reply_to_platform_message_id": str(reply_to_message_id) if reply_to_message_id is not None else None,
        "is_edit": is_edit,
        "sender": sender_meta,
        "raw_reply": text,
        "needs_assistant_action": True,
    }

    if matched_request:
        base.update({
            "event": "reply_received",
            "summary": f"Reply received from {base['recipient'] or sender_id} for Messenger request {matched_request.get('request_id')}",
            "match_reason": match_reason,
        })
    else:
        sender_label = f"known contact {contact.get('name') or sender_id}" if contact else f"unknown sender {sender_id}"
        base.update({
            "event": "unmatched_inbound_message",
            "summary": f"Inbound Telegram message from {sender_label}; no reply-tracked request matched.",
            "match_reason": None,
        })
    return base


def process_updates(updates: Iterable[Dict[str, Any]], state: Dict[str, Any], dry_run: bool = False) -> int:
    contacts = parse_team_contacts()
    by_user, by_reply_msg = sent_request_index()
    processed = set(state.get("processed_update_ids") or [])
    count = 0
    for update in updates:
        update_id = update.get("update_id")
        if update_id is None:
            continue
        if update_id in processed:
            continue
        event = make_event(update, contacts, by_user, by_reply_msg)
        if event:
            if dry_run:
                print(json.dumps(event, ensure_ascii=False))
            else:
                mc.append_jsonl(EVENTS_PATH, event)
            count += 1
        processed.add(update_id)
        state["last_update_id"] = max(int(update_id), int(state.get("last_update_id") or update_id))
    state["processed_update_ids"] = list(processed)[-500:]
    return count


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Poll Telegram replies into FilmNet Messenger JSONL events.")
    parser.add_argument("--once", action="store_true", help="Fetch/process one Telegram batch then exit.")
    parser.add_argument("--poll", action="store_true", help="Continuously poll Telegram.")
    parser.add_argument("--interval", type=float, default=2.0, help="Delay between polling batches in --poll mode.")
    parser.add_argument("--timeout", type=int, default=25, help="Telegram long-poll timeout seconds.")
    parser.add_argument("--fixture-json", type=Path, help="Process a saved Telegram getUpdates JSON fixture instead of calling Telegram.")
    parser.add_argument("--dry-run", action="store_true", help="Print events instead of writing messenger-events.jsonl/state.")
    args = parser.parse_args(argv)

    if not args.once and not args.poll and not args.fixture_json:
        parser.error("choose --once, --poll, or --fixture-json")

    state = load_state()

    if args.fixture_json:
        data = json.loads(args.fixture_json.read_text(encoding="utf-8"))
        updates = data.get("result", data if isinstance(data, list) else [])
        count = process_updates(updates, state, dry_run=args.dry_run)
        if not args.dry_run:
            save_state(state)
        print(f"processed_events={count}")
        return 0

    try:
        token = mc.messenger_bot_token()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    def run_once() -> int:
        offset = None
        if state.get("last_update_id") is not None:
            offset = int(state["last_update_id"]) + 1
        updates = telegram_get_updates(token, offset=offset, timeout=args.timeout)
        count = process_updates(updates, state, dry_run=args.dry_run)
        if not args.dry_run:
            save_state(state)
        return count

    if args.once:
        count = run_once()
        print(f"processed_events={count}")
        return 0

    while True:
        try:
            count = run_once()
            if count:
                print(f"{mc.utc_now()} processed_events={count}", flush=True)
        except KeyboardInterrupt:
            return 130
        except Exception as exc:
            # Never include token-bearing URLs in errors.
            print(f"{mc.utc_now()} intake_error={exc}", file=sys.stderr, flush=True)
            time.sleep(max(args.interval, 5.0))
            continue
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
