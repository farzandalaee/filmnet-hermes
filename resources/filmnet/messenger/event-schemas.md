# Messenger Event Schemas

Use when reading or writing Messenger events in `inbox/messenger-events.jsonl`.

## Delivery result event

```json
{
  "request_id": "msgreq-...",
  "task_id": "FN-YYYY-MMDD-XXX",
  "event": "delivery_result",
  "status": "sent|failed|queued|unknown",
  "recipient": "Full Name",
  "recipient_telegram_id": "numeric id if known",
  "recipient_index": 1,
  "channel": "telegram|email|sms|other",
  "phase": "initial|follow_up",
  "attempt": 1,
  "sent_at": "ISO timestamp if sent",
  "platform_message_id": "optional",
  "error": "optional error details"
}
```

A failed delivery also carries `"permanent": true/false` and `"terminal": true/false`. The dispatcher gives up (and the event-assistant notifies Farzan) only on a `terminal` failure — a permanent error (blocked / never-started / chat-not-found) or `max_send_attempts` exhausted. Transient failures are retried silently.

## Reply event

```json
{
  "request_id": "msgreq-...",
  "task_id": "FN-YYYY-MMDD-XXX",
  "event": "reply_received",
  "recipient": "Full Name",
  "recipient_telegram_id": "numeric id if known",
  "channel": "telegram|email|sms|other",
  "received_at": "ISO timestamp",
  "raw_reply": "exact reply text",
  "summary": "concise operational meaning",
  "needs_assistant_action": true
}
```

## Unmatched inbound event

Use for known/unknown inbound messages that cannot safely be matched to a request. Prefer `task_id: null` and include best-effort sender/channel metadata.

## Send canceled event

Written by the dispatcher when a queued send is canceled by a `cancel` control signal before its review window fires.

```json
{
  "request_id": "msgreq-...",
  "task_id": "FN-YYYY-MMDD-XXX",
  "event": "send_canceled",
  "status": "canceled",
  "recipient": "Full Name",
  "recipient_telegram_id": "numeric id",
  "phase": "initial",
  "terminal": true,
  "sent_at": "ISO timestamp"
}
```

## Reply overdue (escalation) event

Written by the dispatcher when a reply-tracked recipient has not answered by `escalate_after_hours` (default 48h after the initial send). The event-assistant escalates this to Farzan on the control bot.

```json
{
  "request_id": "msgreq-...",
  "task_id": "FN-YYYY-MMDD-XXX",
  "event": "reply_overdue",
  "recipient": "Full Name",
  "recipient_telegram_id": "numeric id",
  "phase": "initial",
  "escalate_after_hours": 48,
  "initial_sent_at": "ISO timestamp",
  "noted_at": "ISO timestamp"
}
```

Control signals (cancel / send_now / edit) are documented in `resources/filmnet/messenger/approved-send-handoff.md`; they live in `inbox/messenger-control.jsonl`, not the events log.

Rules:
- Append events; do not overwrite historical JSONL logs.
- Exact reply text belongs in `raw_reply`.
- For ambiguous replies or unmatched inbound messages, report to FilmNet assistant for triage.
- The event-assistant updates matching full task rows in `state/active-tasks.jsonl` after delivery, replies, cancellations, and escalations, and notifies Farzan on the control bot.
