#!/usr/bin/env python3
"""FilmNet Messenger Telegram dispatcher.

Reads approved send requests from inbox/messenger-send-requests.jsonl, sends exact
approved Telegram messages, records delivery events to inbox/messenger-events.jsonl,
and sends exact pre-approved follow-ups for non-responders when configured.

Reliability properties:
- A single corrupt JSONL line is skipped, never fatal (see messenger_common.read_jsonl).
- Initial sends are capped at max_send_attempts and short-circuit on permanent
  errors (blocked / never-started / chat-not-found), so an unreachable recipient
  produces exactly one terminal failure instead of an infinite retry/notify loop.
- A per-contact reachability cache (inbox/telegram-reachability.json) records who
  can be DM'd so the assistant can warn before scheduling.
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
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import messenger_common as mc  # noqa: E402

ROOT = mc.ROOT
REQUESTS_PATH = ROOT / "inbox/messenger-send-requests.jsonl"
EVENTS_PATH = ROOT / "inbox/messenger-events.jsonl"
CONTROL_PATH = ROOT / "inbox/messenger-control.jsonl"
STATE_PATH = ROOT / "inbox/messenger-telegram-dispatcher-state.json"

DEFAULT_MAX_INITIAL_ATTEMPTS = 3
DEFAULT_REVIEW_WINDOW_MINUTES = 10
DEFAULT_ESCALATE_AFTER_HOURS = 48

# Telegram error fragments that will never succeed on retry for the same chat.
PERMANENT_ERROR_MARKERS = (
    "chat not found",
    "bot was blocked",
    "bot can't initiate",
    "bot can`t initiate",
    "user is deactivated",
    "user not found",
    "peer_id_invalid",
    "have no rights to send",
    "forbidden: user is deactivated",
)


def is_permanent_send_error(message: str) -> bool:
    low = (message or "").lower()
    return any(marker in low for marker in PERMANENT_ERROR_MARKERS)


def load_control_state(control_rows: Iterable[Dict[str, Any]], authorized_user_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Collapse control commands (cancel / send_now / edit) into per-request state.

    Commands are honored only from the authorized control user (Farzan); a row
    from anyone else is ignored so a team member can never steer a send. Later
    commands override earlier ones.
    """
    state: Dict[str, Dict[str, Any]] = {}
    for row in control_rows:
        request_id = str(row.get("request_id") or "").strip()
        if not request_id:
            continue
        issued_by = str(row.get("issued_by") or "").strip()
        if authorized_user_id and issued_by and issued_by != authorized_user_id:
            continue
        command = str(row.get("command") or "").strip().lower()
        st = state.setdefault(request_id, {"canceled": False, "send_now": False, "message": None, "send_after": None})
        if command == "cancel":
            st["canceled"] = True
            st["send_now"] = False
        elif command == "send_now":
            st["canceled"] = False
            st["send_now"] = True
        elif command == "edit":
            if row.get("message"):
                st["message"] = str(row.get("message"))
            if row.get("send_after"):
                st["send_after"] = str(row.get("send_after"))
            st["canceled"] = False
    return state


def load_state() -> Dict[str, Any]:
    return mc.load_json_state(STATE_PATH, {"initialized_at": mc.utc_now(), "last_run_at": None})


def save_state(state: Dict[str, Any]) -> None:
    mc.save_json_state(STATE_PATH, state)


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
    recipients = mc.normalize_recipients(request)
    if not recipients:
        errors.append("recipient or recipients is required")
    for idx, recipient in enumerate(recipients, 1):
        if not str(recipient.get("name") or "").strip():
            errors.append(f"recipient #{idx} missing name")
        if not mc.usable_telegram_id(recipient):
            errors.append(
                f"recipient #{idx} needs a numeric telegram_id "
                "(a @username alone cannot be used to DM a user)"
            )
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
        payload["reply_parameters"] = json.dumps({
            "message_id": int(reply_to_message_id),
            "allow_sending_without_reply": True,
        })
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


def _key_events(
    index: Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    request_id: str,
    lookup_key: str,
    phase: str,
    recipient_name: Optional[str],
) -> List[Dict[str, Any]]:
    events = list(index.get((request_id, lookup_key, phase), []))
    if recipient_name:
        events.extend(index.get((request_id, recipient_name, phase), []))
    return events


def latest_sent_event(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    sent = [e for e in events if e.get("event") == "delivery_result" and e.get("status") == "sent"]
    if not sent:
        return None
    sent.sort(key=lambda e: e.get("sent_at") or "")
    return sent[-1]


def reply_received(events: Iterable[Dict[str, Any]], request_id: str, lookup_key: str, recipient_name: Optional[str] = None) -> bool:
    for event in events:
        if event.get("event") != "reply_received":
            continue
        if str(event.get("request_id") or "").strip() != request_id:
            continue
        sender_id = str((event.get("sender") or {}).get("telegram_id") or "").strip()
        if sender_id and sender_id == lookup_key:
            return True
        event_recipient_id = str(event.get("recipient_telegram_id") or "").strip()
        if event_recipient_id and event_recipient_id == lookup_key:
            return True
        if recipient_name and str(event.get("recipient") or "").strip() == recipient_name:
            return True
    return False


def send_for_request(
    token: str,
    request: Dict[str, Any],
    events_index: Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    reachability: Dict[str, Any],
    control: Dict[str, Any],
    now: datetime,
    dry_run: bool = False,
) -> Tuple[int, bool]:
    count = 0
    reach_changed = False
    request_id = str(request.get("request_id"))
    task_id = str(request.get("task_id"))
    channel = str(request.get("channel"))
    message = str(control.get("message") or request.get("message"))
    canceled = bool(control.get("canceled"))
    send_now = bool(control.get("send_now"))
    effective_send_after = control.get("send_after") or request.get("send_after")
    try:
        max_attempts = max(1, int(request.get("max_send_attempts", DEFAULT_MAX_INITIAL_ATTEMPTS)))
    except Exception:
        max_attempts = DEFAULT_MAX_INITIAL_ATTEMPTS

    for recipient_index, recipient in enumerate(mc.normalize_recipients(request), 1):
        lookup_key = mc.recipient_lookup_key(recipient, recipient_index)
        recipient_name = str(recipient.get("name") or "").strip() or None
        key_events = _key_events(events_index, request_id, lookup_key, "initial", recipient_name)

        if latest_sent_event(key_events):
            continue
        if any(e.get("event") == "delivery_failed" and e.get("terminal") for e in key_events):
            continue  # already gave up on this recipient for this request

        failed_attempts = sum(1 for e in key_events if e.get("event") == "delivery_failed")
        chat_id = mc.usable_telegram_id(recipient)
        event_base = {
            "request_id": request_id,
            "task_id": task_id,
            "recipient": recipient.get("name"),
            "recipient_telegram_id": chat_id,
            "recipient_index": recipient_index,
            "channel": channel,
            "phase": "initial",
            "attempt": failed_attempts + 1,
        }

        # Review-window control gating (checked before send so a STOP wins even
        # at the window boundary).
        if canceled:
            if not any(e.get("event") == "send_canceled" for e in key_events):
                cancel_event = {**event_base, "event": "send_canceled", "status": "canceled", "sent_at": mc.utc_now(), "platform_message_id": None, "error": None, "terminal": True}
                if dry_run:
                    print(json.dumps(cancel_event, ensure_ascii=False))
                else:
                    mc.append_jsonl(EVENTS_PATH, cancel_event)
                    events_index.setdefault((request_id, lookup_key, "initial"), []).append(cancel_event)
                count += 1
            continue
        if not send_now and effective_send_after:
            due_at = mc.parse_iso8601(effective_send_after)
            if due_at is not None and now < due_at:
                continue  # still inside the review window

        if dry_run:
            print(json.dumps({**event_base, "event": "delivery_result", "status": "dry_run", "sent_at": mc.utc_now(), "platform_message_id": None, "error": None}, ensure_ascii=False))
            count += 1
            continue

        if not chat_id:
            event = {**event_base, "event": "delivery_failed", "status": "failed", "sent_at": mc.utc_now(), "platform_message_id": None, "error": "no usable numeric telegram_id for DM", "permanent": True, "terminal": True}
            mc.append_jsonl(EVENTS_PATH, event)
            events_index.setdefault((request_id, lookup_key, "initial"), []).append(event)
            count += 1
            continue

        try:
            result = telegram_send_message(token, chat_id, message)
            event = {**event_base, "event": "delivery_result", "status": "sent", "sent_at": mc.utc_now(), "platform_message_id": str(result.get("message_id")) if result.get("message_id") is not None else None, "error": None}
            reach_changed |= mc.mark_reachability(reachability, chat_id, True)
        except Exception as exc:
            err = str(exc)
            permanent = is_permanent_send_error(err)
            terminal = permanent or (failed_attempts + 1 >= max_attempts)
            event = {**event_base, "event": "delivery_failed", "status": "failed", "sent_at": mc.utc_now(), "platform_message_id": None, "error": err, "permanent": permanent, "terminal": terminal}
            if terminal:
                reach_changed |= mc.mark_reachability(reachability, chat_id, False, reason=err[:200])
        mc.append_jsonl(EVENTS_PATH, event)
        events_index.setdefault((request_id, lookup_key, "initial"), []).append(event)
        count += 1
    return count, reach_changed


def send_follow_ups(
    token: str,
    requests: Iterable[Dict[str, Any]],
    all_events: List[Dict[str, Any]],
    events_index: Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    reachability: Dict[str, Any],
    dry_run: bool = False,
) -> Tuple[int, bool]:
    count = 0
    reach_changed = False
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
        for recipient_index, recipient in enumerate(mc.normalize_recipients(request), 1):
            lookup_key = mc.recipient_lookup_key(recipient, recipient_index)
            recipient_name = str(recipient.get("name") or "").strip() or None
            if reply_received(all_events, request_id, lookup_key, recipient_name=recipient_name):
                continue
            initial_events = _key_events(events_index, request_id, lookup_key, "initial", recipient_name)
            initial_sent = latest_sent_event(initial_events)
            if not initial_sent:
                continue
            initial_sent_at = mc.parse_iso8601(initial_sent.get("sent_at"))
            if initial_sent_at is None:
                continue
            due_at = initial_sent_at + timedelta(hours=delay_hours)
            if now < due_at:
                continue
            follow_events = _key_events(events_index, request_id, lookup_key, "follow_up", recipient_name)
            if any(e.get("event") == "delivery_failed" and e.get("terminal") for e in follow_events):
                continue
            prior_follow_up_attempts = sum(1 for e in follow_events if e.get("event") == "delivery_result" and e.get("status") == "sent")
            if prior_follow_up_attempts >= max_attempts:
                continue
            chat_id = mc.usable_telegram_id(recipient)
            reply_to_message_id = initial_sent.get("platform_message_id")
            event_base = {
                "request_id": request_id,
                "task_id": str(request.get("task_id") or ""),
                "recipient": recipient.get("name"),
                "recipient_telegram_id": chat_id,
                "recipient_index": recipient_index,
                "channel": str(request.get("channel") or "telegram"),
                "phase": "follow_up",
                "attempt": prior_follow_up_attempts + 1,
                "follow_up_due_at": due_at.isoformat(),
            }
            if dry_run:
                print(json.dumps({**event_base, "event": "delivery_result", "status": "dry_run_follow_up", "sent_at": mc.utc_now(), "platform_message_id": None, "error": None}, ensure_ascii=False))
                count += 1
                continue
            if not chat_id:
                continue
            try:
                result = telegram_send_message(token, chat_id, message, reply_to_message_id=reply_to_message_id)
                event = {**event_base, "event": "delivery_result", "status": "sent", "sent_at": mc.utc_now(), "platform_message_id": str(result.get("message_id")) if result.get("message_id") is not None else None, "error": None}
                reach_changed |= mc.mark_reachability(reachability, chat_id, True)
            except Exception as exc:
                err = str(exc)
                permanent = is_permanent_send_error(err)
                terminal = permanent or (prior_follow_up_attempts + 1 >= max_attempts)
                event = {**event_base, "event": "delivery_failed", "status": "failed", "sent_at": mc.utc_now(), "platform_message_id": None, "error": err, "permanent": permanent, "terminal": terminal}
                if terminal:
                    reach_changed |= mc.mark_reachability(reachability, chat_id, False, reason=err[:200])
            mc.append_jsonl(EVENTS_PATH, event)
            events_index.setdefault((request_id, lookup_key, "follow_up"), []).append(event)
            all_events.append(event)
            count += 1
    return count, reach_changed


def maybe_escalate(
    requests: Iterable[Dict[str, Any]],
    all_events: List[Dict[str, Any]],
    events_index: Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    now: datetime,
    dry_run: bool = False,
) -> int:
    """Emit a one-time `reply_overdue` event when a reply-tracked recipient has
    not answered by the escalation deadline (default 48h after the initial send),
    so the event-assistant can escalate to Farzan."""
    count = 0
    for request in requests:
        reply_tracking = request.get("reply_tracking") or {}
        if not reply_tracking.get("required"):
            continue
        request_id = str(request.get("request_id") or "").strip()
        if not request_id:
            continue
        try:
            escalate_hours = float(request.get("escalate_after_hours", DEFAULT_ESCALATE_AFTER_HOURS))
        except Exception:
            escalate_hours = float(DEFAULT_ESCALATE_AFTER_HOURS)
        for recipient_index, recipient in enumerate(mc.normalize_recipients(request), 1):
            lookup_key = mc.recipient_lookup_key(recipient, recipient_index)
            recipient_name = str(recipient.get("name") or "").strip() or None
            if reply_received(all_events, request_id, lookup_key, recipient_name=recipient_name):
                continue
            initial_events = _key_events(events_index, request_id, lookup_key, "initial", recipient_name)
            initial_sent = latest_sent_event(initial_events)
            if not initial_sent:
                continue
            initial_sent_at = mc.parse_iso8601(initial_sent.get("sent_at"))
            if initial_sent_at is None or now < initial_sent_at + timedelta(hours=escalate_hours):
                continue
            if any(e.get("event") == "reply_overdue" for e in initial_events):
                continue
            event = {
                "request_id": request_id,
                "task_id": str(request.get("task_id") or ""),
                "recipient": recipient.get("name"),
                "recipient_telegram_id": mc.usable_telegram_id(recipient),
                "recipient_index": recipient_index,
                "channel": str(request.get("channel") or "telegram"),
                "phase": "initial",
                "event": "reply_overdue",
                "escalate_after_hours": escalate_hours,
                "initial_sent_at": initial_sent.get("sent_at"),
                "noted_at": mc.utc_now(),
            }
            if dry_run:
                print(json.dumps(event, ensure_ascii=False))
            else:
                mc.append_jsonl(EVENTS_PATH, event)
                events_index.setdefault((request_id, lookup_key, "initial"), []).append(event)
            count += 1
    return count


def run_once(token: str, dry_run: bool = False) -> Tuple[int, int, int]:
    requests = mc.read_jsonl(REQUESTS_PATH)
    all_events = mc.read_jsonl(EVENTS_PATH)
    events_index = index_events(all_events)
    reachability = mc.load_reachability()
    control_state = load_control_state(mc.read_jsonl(CONTROL_PATH), mc.control_user_id())
    now = datetime.now(timezone.utc)
    reach_changed = False

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
                    "sent_at": mc.utc_now(),
                    "platform_message_id": None,
                    "error": "; ".join(errors),
                    "terminal": True,
                }
                if dry_run:
                    print(json.dumps(event, ensure_ascii=False))
                else:
                    mc.append_jsonl(EVENTS_PATH, event)
                    all_events.append(event)
                send_count += 1
            continue
        control = control_state.get(request_id, {})
        count, changed = send_for_request(token, request, events_index, reachability, control, now, dry_run=dry_run)
        send_count += count
        reach_changed |= changed

    follow_up_count, changed = send_follow_ups(token, requests, all_events, events_index, reachability, dry_run=dry_run)
    reach_changed |= changed

    escalation_count = maybe_escalate(requests, all_events, events_index, now, dry_run=dry_run)

    if reach_changed and not dry_run:
        mc.save_reachability(reachability)
    return send_count, follow_up_count, escalation_count


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Dispatch FilmNet Messenger Telegram send requests.")
    parser.add_argument("--once", action="store_true", help="Process one batch then exit.")
    parser.add_argument("--poll", action="store_true", help="Continuously process requests.")
    parser.add_argument("--interval", type=float, default=15.0, help="Delay between loops in --poll mode.")
    parser.add_argument("--dry-run", action="store_true", help="Print events instead of writing real send results.")
    args = parser.parse_args(argv)

    if not args.once and not args.poll:
        parser.error("choose --once or --poll")

    token = ""
    if not args.dry_run:
        try:
            token = mc.messenger_bot_token()
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    state = load_state()

    def do_run() -> Tuple[int, int, int]:
        send_count, follow_up_count, escalation_count = run_once(token, dry_run=args.dry_run)
        state["last_run_at"] = mc.utc_now()
        state["last_send_count"] = send_count
        state["last_follow_up_count"] = follow_up_count
        state["last_escalation_count"] = escalation_count
        if not args.dry_run:
            save_state(state)
        return send_count, follow_up_count, escalation_count

    if args.once:
        send_count, follow_up_count, escalation_count = do_run()
        print(f"send_events={send_count} follow_up_events={follow_up_count} escalations={escalation_count}")
        return 0

    while True:
        try:
            send_count, follow_up_count, escalation_count = do_run()
            if send_count or follow_up_count or escalation_count:
                print(f"{mc.utc_now()} send_events={send_count} follow_up_events={follow_up_count} escalations={escalation_count}", flush=True)
        except KeyboardInterrupt:
            return 130
        except Exception as exc:
            print(f"{mc.utc_now()} dispatcher_error={exc}", file=sys.stderr, flush=True)
            time.sleep(max(args.interval, 5.0))
            continue
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
