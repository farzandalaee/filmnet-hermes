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

Rules:
- Append events; do not overwrite historical JSONL logs.
- Exact reply text belongs in `raw_reply`.
- For ambiguous replies or unmatched inbound messages, report to FilmNet assistant for triage.
- FilmNet assistant updates matching full task rows in `state/active-tasks.jsonl` after delivery or replies.
