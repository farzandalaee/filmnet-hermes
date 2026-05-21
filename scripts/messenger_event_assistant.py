#!/usr/bin/env python3
"""Assistant-side watcher for FilmNet Messenger events.

Reads messenger-events.jsonl, updates related per-task files under
state/active-tasks/ with an auto-generated Messenger summary block, and notifies
Farzan on Telegram when important events arrive.
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from state import task_store  # noqa: E402

PROFILE_ENV = Path("/Users/farzan/.hermes/profiles/messenger/.env")
GLOBAL_ENV = Path("/Users/farzan/.hermes/.env")
REQUESTS_PATH = ROOT / "inbox/messenger-send-requests.jsonl"
EVENTS_PATH = ROOT / "inbox/messenger-events.jsonl"
STATE_PATH = ROOT / "inbox/messenger-assistant-state.json"
ACTIVE_TASKS_INDEX = ROOT / "state/active-tasks.md"
ACTIVE_TASKS_DIR = ROOT / "state/active-tasks"
TEAM_CONTACTS = ROOT / "resources/filmnet/team-contacts.md"


TASK_SECTION_RE = re.compile(r"(^##\s+(FN-\d{4}-\d{4}-\d{3})\n)(.*?)(?=^##\s+FN-|\Z)", re.MULTILINE | re.DOTALL)
MESSENGER_BLOCK_RE = re.compile(r"\n- Messenger automation:\n(?:  .*\n)*?(?=- Last updated date:|\Z)", re.MULTILINE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_env() -> Dict[str, str]:
    env: Dict[str, str] = {}
    env.update(load_env_file(GLOBAL_ENV))
    env.update(load_env_file(PROFILE_ENV))
    env.update(os.environ)
    return env


def load_token() -> Optional[str]:
    env = load_env()
    return env.get("TELEGRAM_BOT_TOKEN")


def load_farzan_chat_id() -> Optional[str]:
    env = load_env()
    home_channel = str(env.get("TELEGRAM_HOME_CHANNEL") or "").strip()
    if home_channel:
        parts = [p for p in home_channel.split(":") if p]
        if len(parts) >= 2 and parts[0] == "telegram":
            return parts[1]
        if home_channel.lstrip("-").isdigit():
            return home_channel
    if TEAM_CONTACTS.exists():
        text = TEAM_CONTACTS.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"###\s+Farzan Dalaee\n(?:.*\n)*?- Telegram ID:\s*([^\n]+)", text)
        if m:
            value = m.group(1).strip().replace("\\[", "[").replace("\\]", "]")
            if value and "to be filled" not in value.lower():
                return value
    return None


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


def load_state(path: Path = STATE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"initialized": False, "processed_event_ids": [], "last_run_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"initialized": False, "processed_event_ids": [], "last_run_at": None}
    if not isinstance(data, dict):
        return {"initialized": False, "processed_event_ids": [], "last_run_at": None}
    if "processed_event_ids" not in data or not isinstance(data["processed_event_ids"], list):
        data["processed_event_ids"] = []
    if "initialized" not in data:
        data["initialized"] = False
    return data


def save_state(state: Dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["processed_event_ids"] = list(dict.fromkeys(state.get("processed_event_ids", [])))[-2000:]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def normalize_recipients(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    recipients = request.get("recipients")
    if isinstance(recipients, list) and recipients:
        return [r for r in recipients if isinstance(r, dict)]
    recipient = request.get("recipient")
    if isinstance(recipient, dict) and recipient:
        return [recipient]
    return []


def recipient_lookup_key(recipient: Dict[str, Any], recipient_index: int) -> str:
    telegram_id = str(recipient.get("telegram_id") or "").strip()
    if telegram_id and "to be filled" not in telegram_id.lower():
        return telegram_id
    username = str(recipient.get("telegram_username") or "").strip()
    if username and "to be filled" not in username.lower():
        return username
    return f"recipient_index:{recipient_index}"


def load_requests_by_task() -> Dict[str, List[Dict[str, Any]]]:
    by_task: Dict[str, List[Dict[str, Any]]] = {}
    for request in read_jsonl(REQUESTS_PATH):
        task_id = str(request.get("task_id") or "").strip()
        request_id = str(request.get("request_id") or "").strip()
        if not task_id or not request_id:
            continue
        by_task.setdefault(task_id, []).append(request)
    return by_task


def latest_event(events: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    rows = list(events)
    if not rows:
        return None
    rows.sort(key=lambda e: (e.get("received_at") or e.get("sent_at") or "", e.get("event_id") or e.get("request_id") or ""))
    return rows[-1]


def truncate(text: str, limit: int = 90) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def recipient_status_summary(request: Dict[str, Any], events: List[Dict[str, Any]]) -> List[str]:
    request_id = str(request.get("request_id") or "")
    lines: List[str] = []
    for recipient_index, recipient in enumerate(normalize_recipients(request), 1):
        lookup_key = recipient_lookup_key(recipient, recipient_index)
        related = []
        for event in events:
            if str(event.get("request_id") or "") != request_id:
                continue
            recipient_id = str(event.get("recipient_telegram_id") or "").strip()
            sender_id = str((event.get("sender") or {}).get("telegram_id") or "").strip()
            recipient_name = str(event.get("recipient") or "").strip()
            if lookup_key in (recipient_id, sender_id) or recipient_name == str(recipient.get("name") or ""):
                related.append(event)
        reply_events = [e for e in related if e.get("event") == "reply_received"]
        if reply_events:
            reply_events.sort(key=lambda e: e.get("received_at") or "")
            last = reply_events[-1]
            lines.append(
                f"    - {recipient.get('name')}: replied at {(last.get('received_at') or '[time missing]')} | {truncate(str(last.get('raw_reply') or ''))}"
            )
            continue
        failed = [e for e in related if e.get("event") == "delivery_failed"]
        if failed:
            failed.sort(key=lambda e: e.get("sent_at") or "")
            last = failed[-1]
            lines.append(
                f"    - {recipient.get('name')}: delivery failed | {truncate(str(last.get('error') or 'unknown error'))}"
            )
            continue
        follow_ups = [e for e in related if e.get("event") == "delivery_result" and e.get("status") == "sent" and str(e.get("phase") or "") == "follow_up"]
        initials = [e for e in related if e.get("event") == "delivery_result" and e.get("status") == "sent" and str(e.get("phase") or "initial") == "initial"]
        if follow_ups:
            follow_ups.sort(key=lambda e: e.get("sent_at") or "")
            last = follow_ups[-1]
            lines.append(
                f"    - {recipient.get('name')}: waiting for reply | follow-up sent at {(last.get('sent_at') or '[time missing]')}"
            )
        elif initials:
            initials.sort(key=lambda e: e.get("sent_at") or "")
            last = initials[-1]
            lines.append(
                f"    - {recipient.get('name')}: waiting for reply | sent at {(last.get('sent_at') or '[time missing]')}"
            )
        else:
            lines.append(f"    - {recipient.get('name')}: pending send")
    return lines


def messenger_block_for_task(task_id: str, requests: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> str:
    lines: List[str] = ["- Messenger automation:"]
    if not requests:
        lines.append("  - Requests: none")
        return "\n".join(lines) + "\n"

    lines.append("  - Requests:")
    for request in requests:
        reply_tracking = request.get("reply_tracking") or {}
        deadline = reply_tracking.get("deadline") or "[none]"
        follow_up = request.get("follow_up") or {}
        follow_up_text = "disabled"
        if isinstance(follow_up, dict) and follow_up.get("enabled"):
            follow_up_text = f"enabled after {follow_up.get('delay_hours', 24)}h, max {follow_up.get('max_attempts', 1)}"
        recipients = normalize_recipients(request)
        lines.append(
            f"    - {request.get('request_id')}: channel={request.get('channel')} recipients={len(recipients)} reply_required={bool(reply_tracking.get('required'))} deadline={deadline} follow_up={follow_up_text}"
        )
    lines.append("  - Recipients:")
    for request in requests:
        lines.extend(recipient_status_summary(request, events))

    unmatched = [e for e in events if e.get("event") == "unmatched_inbound_message" and str(e.get("task_id") or "").strip() == task_id]
    if unmatched:
        lines.append("  - Unmatched inbound:")
        for event in unmatched[-3:]:
            sender = event.get("sender") or {}
            sender_name = sender.get("contact_name") or sender.get("first_name") or sender.get("telegram_id") or "unknown"
            lines.append(f"    - {(event.get('received_at') or '[time missing]')}: {sender_name} | {truncate(str(event.get('raw_reply') or ''))}")

    last = latest_event([e for e in events if str(e.get("task_id") or "").strip() == task_id])
    if last:
        when = last.get("received_at") or last.get("sent_at") or "[time missing]"
        lines.append(
            f"  - Latest event: {last.get('event')} at {when}"
        )
    return "\n".join(lines) + "\n"


def upsert_messenger_block(section_body: str, block: str) -> str:
    if MESSENGER_BLOCK_RE.search(section_body):
        return MESSENGER_BLOCK_RE.sub("\n" + block, section_body, count=1)
    marker = "- Last updated date:"
    idx = section_body.find(marker)
    if idx == -1:
        return section_body.rstrip() + "\n" + block
    return section_body[:idx] + block + section_body[idx:]


def update_task_file(events: List[Dict[str, Any]], dry_run: bool = False) -> List[str]:
    requests_by_task = load_requests_by_task()
    relevant_task_ids = set(requests_by_task)
    relevant_task_ids.update(str(e.get("task_id") or "").strip() for e in events if e.get("task_id"))
    relevant_task_ids.discard("")
    if not relevant_task_ids:
        return []

    if not ACTIVE_TASKS_DIR.exists() and ACTIVE_TASKS_INDEX.exists():
        task_store.migrate_legacy_file(ACTIVE_TASKS_INDEX, ACTIVE_TASKS_DIR, ACTIVE_TASKS_INDEX, "Active Tasks")
    if not ACTIVE_TASKS_DIR.exists():
        return []

    updated_task_ids: List[str] = []
    for task_id in sorted(relevant_task_ids):
        path = task_store.task_path(ACTIVE_TASKS_DIR, task_id)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        match = TASK_SECTION_RE.search(text)
        if not match:
            continue
        header, body = match.group(1), match.group(3)
        block = messenger_block_for_task(task_id, requests_by_task.get(task_id, []), events)
        new_body = upsert_messenger_block(body, block)
        new_body = re.sub(r"- Last updated date:\s*[^\n]+", f"- Last updated date: {today_utc()}", new_body, count=1)
        new_text = header + new_body
        if new_text != text:
            updated_task_ids.append(task_id)
            if not dry_run:
                path.write_text(new_text.rstrip() + "\n", encoding="utf-8")

    if updated_task_ids and not dry_run:
        task_store.rebuild_index(ACTIVE_TASKS_DIR, ACTIVE_TASKS_INDEX, "Active Tasks")
    return updated_task_ids


def notify_text_for_event(event: Dict[str, Any]) -> Optional[str]:
    event_type = str(event.get("event") or "")
    if event_type == "reply_received":
        sender = event.get("sender") or {}
        sender_name = sender.get("contact_name") or event.get("recipient") or sender.get("first_name") or "Unknown"
        return (
            f"FilmNet Messenger update\n"
            f"Task: {event.get('task_id') or '[no task]'}\n"
            f"Reply from: {sender_name}\n"
            f"Message: {truncate(str(event.get('raw_reply') or ''), 220)}"
        )
    if event_type == "delivery_failed":
        return (
            f"FilmNet Messenger delivery failed\n"
            f"Task: {event.get('task_id') or '[no task]'}\n"
            f"Recipient: {event.get('recipient') or '[unknown]'}\n"
            f"Reason: {truncate(str(event.get('error') or 'unknown error'), 220)}"
        )
    if event_type == "unmatched_inbound_message":
        sender = event.get("sender") or {}
        sender_name = sender.get("contact_name") or sender.get("first_name") or sender.get("telegram_id") or "Unknown"
        return (
            f"FilmNet Messenger unmatched inbound\n"
            f"From: {sender_name}\n"
            f"Message: {truncate(str(event.get('raw_reply') or ''), 220)}"
        )
    return None


def telegram_send_message(token: str, chat_id: str, text: str) -> Dict[str, Any]:
    payload = urllib.parse.urlencode({
        "chat_id": str(chat_id),
        "text": text,
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram sendMessage HTTP {exc.code}: {raw[:500]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Telegram sendMessage failed: {type(exc).__name__}: {exc}") from exc
    data = json.loads(raw)
    if not data.get("ok"):
        raise RuntimeError(f"Telegram sendMessage returned ok=false: {data.get('description', 'unknown error')}")
    return data.get("result", {})


def process_once(dry_run: bool = False, notify: bool = True) -> Tuple[List[str], int, bool]:
    state = load_state()
    events = read_jsonl(EVENTS_PATH)
    event_ids = [str(e.get("event_id") or f"{e.get('event')}:{e.get('request_id')}:{e.get('recipient')}:{e.get('sent_at') or e.get('received_at')}") for e in events]
    updated_task_ids = update_task_file(events, dry_run=dry_run)

    if not state.get("initialized"):
        state["initialized"] = True
        state["processed_event_ids"] = event_ids
        state["last_run_at"] = utc_now()
        if not dry_run:
            save_state(state)
        return updated_task_ids, 0, True

    processed = set(state.get("processed_event_ids") or [])
    new_events = []
    for event, event_id in zip(events, event_ids):
        if event_id in processed:
            continue
        new_events.append((event_id, event))

    notifications_sent = 0
    token = load_token() if notify and not dry_run else None
    chat_id = load_farzan_chat_id() if notify and not dry_run else None
    for event_id, event in new_events:
        text = notify_text_for_event(event)
        if text and notify:
            if dry_run:
                print(json.dumps({"notify_event_id": event_id, "text": text}, ensure_ascii=False))
                notifications_sent += 1
            else:
                if token and chat_id:
                    telegram_send_message(token, chat_id, text)
                    notifications_sent += 1
        processed.add(event_id)

    state["processed_event_ids"] = list(processed)
    state["last_run_at"] = utc_now()
    if not dry_run:
        save_state(state)
    return updated_task_ids, notifications_sent, False


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Update FilmNet tasks and notify Farzan from Messenger events.")
    parser.add_argument("--once", action="store_true", help="Process one batch then exit.")
    parser.add_argument("--poll", action="store_true", help="Continuously process events.")
    parser.add_argument("--interval", type=float, default=15.0, help="Delay between loops in --poll mode.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files or send notifications.")
    parser.add_argument("--no-notify", action="store_true", help="Update task state only; skip Telegram notifications.")
    args = parser.parse_args(argv)

    if not args.once and not args.poll:
        parser.error("choose --once or --poll")

    if not args.dry_run and not args.no_notify:
        if not load_token():
            print("TELEGRAM_BOT_TOKEN is not configured for the messenger profile", file=sys.stderr)
            return 2
        if not load_farzan_chat_id():
            print("Could not determine Farzan Telegram chat id", file=sys.stderr)
            return 2

    def do_run() -> Tuple[List[str], int, bool]:
        return process_once(dry_run=args.dry_run, notify=not args.no_notify)

    if args.once:
        updated_task_ids, notifications_sent, initialized = do_run()
        print(
            f"updated_tasks={len(updated_task_ids)} notifications_sent={notifications_sent} initialized={str(initialized).lower()}"
        )
        return 0

    while True:
        try:
            updated_task_ids, notifications_sent, initialized = do_run()
            if updated_task_ids or notifications_sent:
                print(
                    f"{utc_now()} updated_tasks={len(updated_task_ids)} notifications_sent={notifications_sent} initialized={str(initialized).lower()}",
                    flush=True,
                )
        except KeyboardInterrupt:
            return 130
        except Exception as exc:
            print(f"{utc_now()} assistant_event_error={exc}", file=sys.stderr, flush=True)
            time.sleep(max(args.interval, 5.0))
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
