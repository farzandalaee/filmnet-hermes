# FilmNet Messenger Agent Workflow

This workflow defines how the FilmNet assistant hands approved communications to the Messenger agent.

## Roles

FilmNet assistant / Farzan assistant:
- owns Farzan interaction
- identifies recipient from a single matching CONTACT line in `resources/filmnet/team-contacts.md`
- drafts message content
- gets Farzan approval before sending
- creates/updates the FilmNet Task ID in the task index `state/active-tasks.md` and the full task row in `state/active-tasks.jsonl`
- sends an approved delivery payload to Messenger
- receives Messenger delivery/reply events and decides next steps

Messenger agent:
- validates the approved delivery payload
- sends the exact approved content through the requested channel
- records delivery result
- tracks and reports replies
- does not rewrite content or choose recipients

## Standard Send Handoff

```json
{
  "task_id": "FN-YYYY-MMDD-XXX",
  "request_id": "msgreq-...",
  "action": "send_message",
  "approval_status": "approved_by_farzan",
  "recipient": {
    "name": "Full Name",
    "name_fa": "Persian first name if available",
    "telegram_username": "@username or [to be filled]",
    "telegram_id": "numeric id or [to be filled]",
    "email": "email or [to be filled]",
    "mobile": "full mobile or [full mobile to be filled]"
  },
  "recipients": [
    {
      "name": "Full Name",
      "name_fa": "Persian first name if available",
      "telegram_username": "@username or [to be filled]",
      "telegram_id": "numeric id or [to be filled]",
      "email": "email or [to be filled]",
      "mobile": "full mobile or [full mobile to be filled]"
    }
  ],
  "channel": "telegram|email|sms|other",
  "message": "exact approved message text",
  "reply_tracking": {
    "required": true,
    "expected_response": "accept/decline/answer/details/etc",
    "deadline": "optional date/time"
  },
  "follow_up": {
    "enabled": true,
    "delay_hours": 24,
    "max_attempts": 1,
    "message": "exact approved follow-up text"
  }
}
```

## Required Validation Before Sending

Messenger must confirm:
1. `request_id` is present.
2. `approval_status` is exactly `approved_by_farzan`.
3. `message` is present and non-empty.
4. At least one recipient is present via `recipient` or `recipients`.
5. Channel is specified.
6. Channel-specific contact is usable:
   - Telegram: Telegram ID preferred, username acceptable if supported.
   - Email: valid email address.
   - SMS/call: full mobile number.
7. Task ID is present.

If any validation fails, Messenger reports a failure event and does not send.

## Delivery Result Event

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

## Reply Event

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

## Operating Notes

- Messenger should be channel-agnostic: Telegram first, email/SMS/other later.
- Messenger should not maintain a separate team directory.
- For ambiguous replies or unmatched inbound messages, Messenger should report `task_id: null` plus best-effort sender/channel metadata to FilmNet assistant for triage.
- FilmNet assistant remains responsible for updating the relevant full task row in `state/active-tasks.jsonl` after delivery or replies, then refreshing `state/active-tasks.md` if the title changes.

## Implementation Roadmap

### Option A: JSONL inbox/outbox first

Use this as the first implementation because it is simple, auditable, and safe.

Proposed paths:
- `inbox/messenger-send-requests.jsonl` for approved send commands from FilmNet assistant to Messenger.
- `inbox/messenger-events.jsonl` for delivery results, failures, replies, and unmatched inbound messages from Messenger to FilmNet assistant.

Rules:
- Every send request must include `task_id`, `approval_status: approved_by_farzan`, one or more recipients, channel, message, and reply-tracking fields.
- Use `recipients` for announcements/broadcasts and `recipient` for single-person sends; Messenger should support both.
- Messenger validates and sends only approved requests.
- Messenger writes all results as append-only events.
- FilmNet assistant reads events and updates the matching task row in `state/active-tasks.jsonl`.
- Dry-run validation should exist before real Telegram/email sending is enabled.

Telegram reply intake implementation:
- Telegram dispatcher/send worker: `scripts/messenger_telegram_dispatcher.py`
- Script: `scripts/messenger_telegram_intake.py`
- Assistant event watcher: `scripts/messenger_event_assistant.py`
- LaunchAgent: `/Users/farzan/Library/LaunchAgents/ai.filmnet.messenger-telegram-intake.plist`
- LaunchAgents:
  - `/Users/farzan/Library/LaunchAgents/ai.filmnet.messenger-telegram-dispatcher.plist`
  - `/Users/farzan/Library/LaunchAgents/ai.filmnet.messenger-event-assistant.plist`
- Logs:
  - `logs/messenger-telegram-dispatcher.log`
  - `logs/messenger-telegram-dispatcher.error.log`
  - `logs/messenger-telegram-intake.log`
  - `logs/messenger-telegram-intake.error.log`
  - `logs/messenger-event-assistant.log`
  - `logs/messenger-event-assistant.error.log`
- State cursor: `inbox/messenger-telegram-intake-state.json`
- Dispatcher state: `inbox/messenger-telegram-dispatcher-state.json`
- Assistant watcher state: `inbox/messenger-assistant-state.json`
- Behavior: polls Telegram Bot API using the Messenger profile token, maps known senders from `team-contacts.md`, matches replies to sent Messenger requests by `reply_to_message.message_id` or latest reply-tracked request for the sender, and appends `reply_received` or `unmatched_inbound_message` events to `inbox/messenger-events.jsonl`.
- Dispatcher behavior: sends approved single-recipient or multi-recipient Telegram requests, records delivery events, and sends exact pre-approved follow-up messages for non-responders when `follow_up.enabled` is true.
- Assistant watcher behavior: reads Messenger events, updates the related task row in `state/active-tasks.jsonl` with a Messenger automation summary block, refreshes the active index when needed, and notifies Farzan on Telegram about replies, failures, and unmatched inbound messages.
- Safety: inbound recipient text is never passed into Hermes as an agent-control prompt. Ordinary team members should not be added to Hermes gateway allowlists just to reply.
- Runtime maintenance: run `python3 scripts/rotate_runtime_files.py --dry-run` to inspect rotation and `python3 scripts/rotate_runtime_files.py` to rotate logs/JSONL queues. The script archives old/large runtime files under `archive/runtime/`, keeps recent JSONL lines active for reply matching, and deliberately does not rotate state cursor files such as `inbox/messenger-telegram-intake-state.json`.

### Option C: JSONL plus Kanban later

Implement only after Option A is stable.

Use Kanban for durable Messenger jobs such as:
- send approved message and track reply until a deadline
- follow up when no reply is received
- escalate failed delivery
- summarize pending communication status

Keep JSONL as the canonical event layer. Kanban should reference JSONL request/event IDs instead of replacing the event log.
