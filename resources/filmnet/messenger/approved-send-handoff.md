# Messenger Approved Send Handoff

Use when the FilmNet assistant prepares, validates, or appends an approved Messenger send request.

## Standard request JSON

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
  "message": "exact message text the assistant self-drafted",
  "send_after": "ISO8601 — hold until then (the review window, default now + 10 min); omit to send immediately",
  "review_window": { "window_minutes": 10 },
  "escalate_after_hours": 48,
  "max_send_attempts": 3,
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

Use `recipient` for single-person sends and `recipients` for announcements/broadcasts. Messenger should support both.

## Control signals (review window)

To cancel, expedite, or edit a queued send before it fires, append one line to `inbox/messenger-control.jsonl`. Only Farzan (the authorized control user) may issue these; the assistant writes them when Farzan sends STOP / SEND NOW / EDIT on the control bot.

```json
{
  "request_id": "msgreq-...",
  "task_id": "FN-YYYY-MMDD-XXX",
  "command": "cancel | send_now | edit",
  "issued_by": "<Farzan numeric telegram id>",
  "issued_at": "ISO8601",
  "message": "new text (edit only)",
  "send_after": "ISO8601 (edit only — restart the window)"
}
```

- `cancel` → the dispatcher writes a `send_canceled` event and never sends.
- `send_now` → the dispatcher ignores `send_after` and sends on its next tick.
- `edit` → replaces the message and, if `send_after` is given, restarts the window.

## Required validation before sending

Messenger must confirm:
1. `request_id` is present.
2. `approval_status` is exactly `approved_by_farzan`.
3. `message` is present and non-empty.
4. At least one recipient is present via `recipient` or `recipients`.
5. `channel` is specified.
6. Channel-specific contact is usable:
   - Telegram: a numeric `telegram_id` is **required** (a `@username` alone cannot be used to DM a user).
   - Email: valid email address.
   - SMS/call: full mobile number.
7. `task_id` is present.

If any validation fails, Messenger reports a failure event and does not send.

## Assistant-side send sequence

1. Resolve the recipient from `resources/filmnet/team-contacts.md` by grep/searching likely matching CONTACT lines; you need a numeric `telegram_id`. If more than one contact matches, ask Farzan which one.
2. Check `inbox/telegram-reachability.json`; if the contact is known unreachable, mark the task blocked on reachability, tell Farzan, and stop — do not queue a send.
3. Self-draft the message (Persian by default) and persist/update the Task ID in `state/active-tasks.jsonl` plus `state/active-tasks.md`.
4. Append one approved request JSON line to `inbox/messenger-send-requests.jsonl` with `send_after` = now + 10 minutes, then announce it to Farzan with STOP / SEND NOW / EDIT.
5. Do not wait. The dispatcher sends after the window unless a control signal cancels/edits/expedites it; the event-assistant records `delivery_result` and notifies Farzan.
6. Re-read the task row when needed because `scripts/messenger_event_assistant.py` keeps the Messenger automation block current.
