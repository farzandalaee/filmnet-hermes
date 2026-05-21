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

Use `recipient` for single-person sends and `recipients` for announcements/broadcasts. Messenger should support both.

## Required validation before sending

Messenger must confirm:
1. `request_id` is present.
2. `approval_status` is exactly `approved_by_farzan`.
3. `message` is present and non-empty.
4. At least one recipient is present via `recipient` or `recipients`.
5. `channel` is specified.
6. Channel-specific contact is usable:
   - Telegram: Telegram ID preferred; username acceptable if supported.
   - Email: valid email address.
   - SMS/call: full mobile number.
7. `task_id` is present.

If any validation fails, Messenger reports a failure event and does not send.

## Assistant-side send sequence

1. Resolve the recipient from `resources/filmnet/team-contacts.md` by grep/searching likely matching CONTACT lines.
2. Draft message, get Farzan approval, and persist/update the Task ID in `state/active-tasks.jsonl` plus `state/active-tasks.md`.
3. Append one approved request JSON line to `inbox/messenger-send-requests.jsonl`.
4. Wait briefly or inspect `inbox/messenger-events.jsonl` for the same `request_id`.
5. Report `sent` only after a `delivery_result` confirms it.
6. Re-read the task row because `scripts/messenger_event_assistant.py` may update Messenger automation state.
