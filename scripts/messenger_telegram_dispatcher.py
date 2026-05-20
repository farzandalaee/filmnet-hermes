#!/usr/bin/env python3
"""FilmNet Messenger Telegram dispatcher.

Reads approved send requests from inbox/messenger-send-requests.jsonl, sends exact
approved Telegram messages, records delivery events to inbox/messenger-events.jsonl,
and sends exact pre-approved follow-ups for non-responders when configured.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path("/Users/farzan/filmnet-hermes")
PROFILE_ENV = Path("/Users/farzan/.hermes/profiles/messenger/.env")
GLOBAL_ENV = Path("/Users/farzan/.hermes/.env")
REQUESTS_PATH = ROOT / "inbox/messenger-send-requests.jsonl"
EVENTS_PATH = ROOT / "inbox/messenger-events.jsonl"
STATE_PATH = ROOT / "inbox/messenger-telegram-dispatcher-state.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        return {"initialized_at": utc_now(), "last_run_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"initialized_at": utc_now(), "last_run_at": None}
    if not isinstance(data, dict):
        return {"initialized_at": utc_now(), "last_run_at": None}
    return data


def save_state(state: Dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def recipient_key(recipient: Dict[str, Any], recipient_index: int) -> str:
    telegram_id = str(recipient.get("telegram_id") or "").strip()
    if telegram_id and "to be filled" not in telegram_id.lower():
        return telegram_id
    username = str(recipient.get("telegram_username") or "").strip()
    if username and "to be filled" not in username.lower():
        return username
    return f"recipient_index:{recipient_index}"


def validate_request(request: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not request.get("request_id"):
        errors.append("missing request_id")
    if not request.get("task_id"):
        errors.append("missing task_id")
    if request.get("action") != "send_message":
        errors.append("action must be send_message")
    if request.get("approval_status") != "approved_by_farzan":
        errors.append("approval_status must be approved_by_farzan")
    if request.get("channel") != "telegram":
        errors.append("only telegram channel is currently implemented")
    if not str(request.get("message") or "").strip():
        errors.append("message is empty")
    recipients = normalize_recipients(request)
    if not recipients:
        errors.append("recipient or recipients is required")
    for idx, recipient in enumerate(recipients, 1):
        if not str(recipient.get("name") or "").strip():
            errors.append(f"recipient #{idx} missing name")
        telegram_id = str(recipient.get("telegram_id") or "").strip()
        username = str(recipient.get("telegram_username") or "").strip()
        usable_id = telegram_id and "to be filled" not in telegram_id.lower()
        usable_username = username and "to be filled" not in username.lower()
        if not usable_id and not usable_username:
            errors.append(f"recipient #{idx} missing usable Telegram contact")
    follow_up = request.get("follow_up")
    if follow_up not in (None, False):
        if not isinstance(follow_up, dict):
            errors.append("follow_up must be an object when present")
        elif follow_up.get("enabled"):
            if not str(follow_up.get("message") or "").strip():
                errors.append("follow_up.message is required when follow_up.enabled is true")
            delay_hours = follow_up.get("delay_hours", 24)
            try:
                if float(delay_hours) <= 0:
                    errors.append("follow_up.delay_hours must be > 0")
            except Exception:
                errors.append("follow_up.delay_hours must be numeric")
            try:
                if int(follow_up.get("max_attempts", 1)) < 1:
                    errors.append("follow_up.max_attempts must be >= 1")
            except Exception:
                errors.append("follow_up.max_attempts must be an integer")
    return errors


def telegram_send_message(token: str, chat_id: str, text: str, reply_to_message_id: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "chat_id": str(chat_id),
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_to_message_id is not None:
        payload["reply_parameters"] = json.dumps({"message_id": int(reply_to_message_id)})
    body = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
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


def index_events(events: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    index: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for event in events:
        request_id = str(event.get("request_id") or "").strip()
        if not request_id:
            continue
        recipient_id = str(event.get("recipient_telegram_id") or "").strip()
        if not recipient_id:
            recipient_id = str(event.get("recipient") or "").strip()
        phase = str(event.get("phase") or "initial").strip() or "initial"
        key = (request_id, recipient_id, phase)
        index.setdefault(key, []).append(event)
    return index


def latest_sent_event(
    index: Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    request_id: str,
    recipient_lookup_key: str,
    phase: str,
    recipient_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    events = list(index.get((request_id, recipient_lookup_key, phase), []))
    if recipient_name:
        events.extend(index.get((request_id, recipient_name, phase), []))
    sent = [e for e in events if e.get("event") == "delivery_result" and e.get("status") == "sent"]
    if not sent:
        return None
    sent.sort(key=lambda e: e.get("sent_at") or "")
    return sent[-1]


def reply_received(events: Iterable[Dict[str, Any]], request_id: str, recipient_lookup_key: str, recipient_name: Optional[str] = None) -> bool:
    for event in events:
        if event.get("event") != "reply_received":
            continue
        if str(event.get("request_id") or "").strip() != request_id:
            continue
        sender = event.get("sender") or {}
        sender_id = str(sender.get("telegram_id") or "").strip()
        if sender_id and sender_id == recipient_lookup_key:
            return True
        event_recipient_id = str(event.get("recipient_telegram_id") or "").strip()
        if event_recipient_id and event_recipient_id == recipient_lookup_key:
            return True
        if recipient_name and str(event.get("recipient") or "").strip() == recipient_name:
            return True
    return False


def attempts_sent(
    index: Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    request_id: str,
    recipient_lookup_key: str,
    phase: str,
    recipient_name: Optional[str] = None,
) -> int:
    events = list(index.get((request_id, recipient_lookup_key, phase), []))
    if recipient_name:
        events.extend(index.get((request_id, recipient_name, phase), []))
    sent = [e for e in events if e.get("event") == "delivery_result" and e.get("status") == "sent"]
    return len(sent)


def send_for_request(token: str, request: Dict[str, Any], events_index: Dict[Tuple[str, str, str], List[Dict[str, Any]]], dry_run: bool = False) -> int:
    count = 0
    request_id = str(request.get("request_id"))
    task_id = str(request.get("task_id"))
    channel = str(request.get("channel"))
    message = str(request.get("message"))
    for recipient_index, recipient in enumerate(normalize_recipients(request), 1):
        lookup_key = recipient_key(recipient, recipient_index)
        recipient_name = str(recipient.get("name") or "").strip() or None
        if latest_sent_event(events_index, request_id, lookup_key, "initial", recipient_name=recipient_name):
            continue
        event_base = {
            "request_id": request_id,
            "task_id": task_id,
            "recipient": recipient.get("name"),
            "recipient_telegram_id": str(recipient.get("telegram_id") or "").strip() or None,
            "recipient_index": recipient_index,
            "channel": channel,
            "phase": "initial",
            "attempt": 1,
        }
        if dry_run:
            print(json.dumps({**event_base, "event": "delivery_result", "status": "dry_run", "sent_at": utc_now(), "platform_message_id": None, "error": None}, ensure_ascii=False))
            count += 1
            continue
        try:
            result = telegram_send_message(token, str(recipient.get("telegram_id") or recipient.get("telegram_username")), message)
            event = {
                **event_base,
                "event": "delivery_result",
                "status": "sent",
                "sent_at": utc_now(),
                "platform_message_id": str(result.get("message_id")) if result.get("message_id") is not None else None,
                "error": None,
            }
        except Exception as exc:
            event = {
                **event_base,
                "event": "delivery_failed",
                "status": "failed",
                "sent_at": utc_now(),
                "platform_message_id": None,
                "error": str(exc),
            }
        append_jsonl(EVENTS_PATH, event)
        events_index.setdefault((request_id, lookup_key, "initial"), []).append(event)
        count += 1
    return count


def send_follow_ups(token: str, requests: Iterable[Dict[str, Any]], all_events: List[Dict[str, Any]], events_index: Dict[Tuple[str, str, str], List[Dict[str, Any]]], dry_run: bool = False) -> int:
    count = 0
    now = datetime.now(timezone.utc)
    for request in requests:
        follow_up = request.get("follow_up")
        if not isinstance(follow_up, dict) or not follow_up.get("enabled"):
            continue
        request_id = str(request.get("request_id") or "").strip()
        if not request_id:
            continue
        message = str(follow_up.get("message") or "").strip()
        if not message:
            continue
        try:
            delay_hours = float(follow_up.get("delay_hours", 24))
        except Exception:
            delay_hours = 24.0
        try:
            max_attempts = int(follow_up.get("max_attempts", 1))
        except Exception:
            max_attempts = 1
        for recipient_index, recipient in enumerate(normalize_recipients(request), 1):
            lookup_key = recipient_key(recipient, recipient_index)
            recipient_name = str(recipient.get("name") or "").strip() or None
            if reply_received(all_events, request_id, lookup_key, recipient_name=recipient_name):
                continue
            initial_sent = latest_sent_event(events_index, request_id, lookup_key, "initial", recipient_name=recipient_name)
            if not initial_sent:
                continue
            initial_sent_at = parse_iso8601(initial_sent.get("sent_at"))
            if initial_sent_at is None:
                continue
            due_at = initial_sent_at + timedelta(hours=delay_hours)
            if now < due_at:
                continue
            prior_follow_up_attempts = attempts_sent(events_index, request_id, lookup_key, "follow_up", recipient_name=recipient_name)
            if prior_follow_up_attempts >= max_attempts:
                continue
            reply_to_message_id = initial_sent.get("platform_message_id")
            event_base = {
                "request_id": request_id,
                "task_id": str(request.get("task_id") or ""),
                "recipient": recipient.get("name"),
                "recipient_telegram_id": str(recipient.get("telegram_id") or "").strip() or None,
                "recipient_index": recipient_index,
                "channel": str(request.get("channel") or "telegram"),
                "phase": "follow_up",
                "attempt": prior_follow_up_attempts + 1,
                "follow_up_due_at": due_at.isoformat(),
            }
            if dry_run:
                print(json.dumps({**event_base, "event": "delivery_result", "status": "dry_run_follow_up", "sent_at": utc_now(), "platform_message_id": None, "error": None}, ensure_ascii=False))
                count += 1
                continue
            try:
                result = telegram_send_message(
                    token,
                    str(recipient.get("telegram_id") or recipient.get("telegram_username")),
                    message,
                    reply_to_message_id=reply_to_message_id,
                )
                event = {
                    **event_base,
                    "event": "delivery_result",
                    "status": "sent",
                    "sent_at": utc_now(),
                    "platform_message_id": str(result.get("message_id")) if result.get("message_id") is not None else None,
                    "error": None,
                }
            except Exception as exc:
                event = {
                    **event_base,
                    "event": "delivery_failed",
                    "status": "failed",
                    "sent_at": utc_now(),
                    "platform_message_id": None,
                    "error": str(exc),
                }
            append_jsonl(EVENTS_PATH, event)
            events_index.setdefault((request_id, lookup_key, "follow_up"), []).append(event)
            all_events.append(event)
            count += 1
    return count


def run_once(token: str, dry_run: bool = False) -> Tuple[int, int]:
    requests = read_jsonl(REQUESTS_PATH)
    all_events = read_jsonl(EVENTS_PATH)
    events_index = index_events(all_events)

    send_count = 0
    for request in requests:
        errors = validate_request(request)
        request_id = str(request.get("request_id") or "")
        task_id = str(request.get("task_id") or "")
        if errors:
            has_validation_failure = any(
                str(event.get("request_id") or "") == request_id
                and str(event.get("phase") or "") == "validation"
                and event.get("event") == "delivery_failed"
                for event in all_events
            )
            if request_id and not has_validation_failure:
                event = {
                    "request_id": request_id or None,
                    "task_id": task_id or None,
                    "recipient": None,
                    "recipient_telegram_id": None,
                    "recipient_index": None,
                    "channel": request.get("channel"),
                    "phase": "validation",
                    "attempt": 1,
                    "event": "delivery_failed",
                    "status": "failed",
                    "sent_at": utc_now(),
                    "platform_message_id": None,
                    "error": "; ".join(errors),
                }
                if dry_run:
                    print(json.dumps(event, ensure_ascii=False))
                else:
                    append_jsonl(EVENTS_PATH, event)
                    all_events.append(event)
                send_count += 1
            continue
        send_count += send_for_request(token, request, events_index, dry_run=dry_run)

    follow_up_count = send_follow_ups(token, requests, all_events, events_index, dry_run=dry_run)
    return send_count, follow_up_count


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Dispatch FilmNet Messenger Telegram send requests.")
    parser.add_argument("--once", action="store_true", help="Process one batch then exit.")
    parser.add_argument("--poll", action="store_true", help="Continuously process requests.")
    parser.add_argument("--interval", type=float, default=15.0, help="Delay between loops in --poll mode.")
    parser.add_argument("--dry-run", action="store_true", help="Print events instead of writing real send results.")
    args = parser.parse_args(argv)

    if not args.once and not args.poll:
        parser.error("choose --once or --poll")

    token = load_token()
    if not token and not args.dry_run:
        print("TELEGRAM_BOT_TOKEN is not configured for the messenger profile", file=sys.stderr)
        return 2

    state = load_state()

    def do_run() -> Tuple[int, int]:
        send_count, follow_up_count = run_once(token or "", dry_run=args.dry_run)
        state["last_run_at"] = utc_now()
        state["last_send_count"] = send_count
        state["last_follow_up_count"] = follow_up_count
        if not args.dry_run:
            save_state(state)
        return send_count, follow_up_count

    if args.once:
        send_count, follow_up_count = do_run()
        print(f"send_events={send_count} follow_up_events={follow_up_count}")
        return 0

    while True:
        try:
            send_count, follow_up_count = do_run()
            if send_count or follow_up_count:
                print(f"{utc_now()} send_events={send_count} follow_up_events={follow_up_count}", flush=True)
        except KeyboardInterrupt:
            return 130
        except Exception as exc:
            print(f"{utc_now()} dispatcher_error={exc}", file=sys.stderr, flush=True)
            time.sleep(max(args.interval, 5.0))
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
