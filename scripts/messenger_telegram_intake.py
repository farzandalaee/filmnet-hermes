#!/usr/bin/env python3
"""Telegram reply-intake adapter for FilmNet Messenger.

This script polls Telegram Bot API updates and writes inbound human replies as
append-only JSONL events to inbox/messenger-events.jsonl. It is intentionally
not a Hermes gateway session: recipient text is never passed to an LLM as a
command, so team members can reply without being granted agent-control access.

Secrets are read from /Users/farzan/.hermes/profiles/messenger/.env and never
printed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path("/Users/farzan/filmnet-hermes")
PROFILE_ENV = Path("/Users/farzan/.hermes/profiles/messenger/.env")
GLOBAL_ENV = Path("/Users/farzan/.hermes/.env")
TEAM_CONTACTS = ROOT / "resources/filmnet/team-contacts.md"
REQUESTS_PATH = ROOT / "inbox/messenger-send-requests.jsonl"
EVENTS_PATH = ROOT / "inbox/messenger-events.jsonl"
STATE_PATH = ROOT / "inbox/messenger-telegram-intake-state.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        env[key.strip()] = value
    return env


def load_token() -> Optional[str]:
    env: Dict[str, str] = {}
    env.update(load_env_file(GLOBAL_ENV))
    env.update(load_env_file(PROFILE_ENV))
    return os.environ.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON in {path}:{line_no}: {exc}") from exc
    return rows


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def load_state(path: Path = STATE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"last_update_id": None, "processed_update_ids": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"last_update_id": None, "processed_update_ids": []}
    if "processed_update_ids" not in data or not isinstance(data["processed_update_ids"], list):
        data["processed_update_ids"] = []
    return data


def save_state(state: Dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    # Keep the de-dupe list bounded. Telegram offset is the primary cursor.
    state["processed_update_ids"] = list(dict.fromkeys(state.get("processed_update_ids", [])))[-500:]
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def parse_team_contacts(path: Path = TEAM_CONTACTS) -> Dict[str, Dict[str, str]]:
    """Return contacts keyed by Telegram ID as string."""
    if not path.exists():
        return {}
    contacts: Dict[str, Dict[str, str]] = {}
    current: Optional[Dict[str, str]] = None
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
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
        key = m.group(1).strip().lower().replace(" ", "_").replace("-", "_")
        value = m.group(2).strip().replace("\\[", "[").replace("\\]", "]")
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


def normalize_recipients(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    recipients = request.get("recipients")
    if isinstance(recipients, list) and recipients:
        return [r for r in recipients if isinstance(r, dict)]
    recipient = request.get("recipient")
    if isinstance(recipient, dict) and recipient:
        return [recipient]
    return []


def sent_request_index(requests_path: Path = REQUESTS_PATH, events_path: Path = EVENTS_PATH) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Build indexes for matching replies to the latest sent request.

    Returns:
      by_telegram_id: latest reply-tracked send request per recipient Telegram ID
      by_platform_message_id: send request by Telegram sent message id
    """
    requests = read_jsonl(requests_path)
    events = read_jsonl(events_path)
    request_by_id = {r.get("request_id"): r for r in requests if r.get("request_id")}

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
                recipients = normalize_recipients(req)
                if 1 <= recipient_index <= len(recipients):
                    telegram_id = str(recipients[recipient_index - 1].get("telegram_id") or "").strip()
            if not telegram_id:
                telegram_id = str(req.get("recipient", {}).get("telegram_id") or "").strip()
        if telegram_id and "to be filled" not in telegram_id.lower():
            by_telegram_id[telegram_id] = req
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
    reply_to = message.get("reply_to_message") or {}
    reply_to_message_id = reply_to.get("message_id")

    contact = contacts.get(sender_id)
    matched_request = None
    match_reason = None
    if reply_to_message_id is not None and str(reply_to_message_id) in by_reply_msg:
        matched_request = by_reply_msg[str(reply_to_message_id)]
        match_reason = "reply_to_platform_message_id"
    elif sender_id in by_user:
        matched_request = by_user[sender_id]
        match_reason = "latest_reply_tracked_request_for_sender"

    username = sender.get("username")
    sender_meta = {
        "telegram_id": sender_id,
        "telegram_username": ("@" + str(username)) if username else None,
        "first_name": sender.get("first_name"),
        "last_name": sender.get("last_name"),
        "chat_id": str(chat.get("id")) if chat.get("id") is not None else None,
        "chat_type": chat.get("type"),
        "known_contact": bool(contact),
        "contact_name": contact.get("name") if contact else None,
        "contact_name_fa": contact.get("name_fa") if contact else None,
    }

    base = {
        "event_id": f"tgu-{update.get('update_id')}-{message_id}",
        "request_id": matched_request.get("request_id") if matched_request else None,
        "task_id": matched_request.get("task_id") if matched_request else None,
        "recipient": (contact.get("name") if contact else None) or (matched_request.get("recipient", {}).get("name") if matched_request else None),
        "recipient_telegram_id": sender_id if matched_request else None,
        "channel": "telegram",
        "received_at": utc_now(),
        "platform_update_id": update.get("update_id"),
        "platform_message_id": str(message_id) if message_id is not None else None,
        "reply_to_platform_message_id": str(reply_to_message_id) if reply_to_message_id is not None else None,
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


def process_updates(updates: Iterable[Dict[str, Any]], state: Dict[str, Any], events_path: Path = EVENTS_PATH, dry_run: bool = False) -> int:
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
                append_jsonl(events_path, event)
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

    token = load_token()
    if not token:
        print("TELEGRAM_BOT_TOKEN is not configured for the messenger profile", file=sys.stderr)
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
                print(f"{utc_now()} processed_events={count}", flush=True)
        except KeyboardInterrupt:
            return 130
        except Exception as exc:
            # Never include token-bearing URLs in errors.
            print(f"{utc_now()} intake_error={exc}", file=sys.stderr, flush=True)
            time.sleep(max(args.interval, 5.0))
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
