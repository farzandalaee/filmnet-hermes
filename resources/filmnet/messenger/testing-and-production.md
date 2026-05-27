# Messenger Testing and Production

Use when Farzan asks to test Telegram/email communications, productionize Option A, or verify Messenger health.

## Testing rule

For current Messenger Option A Telegram, test it as a send-and-track system, not as a conversational bot.

Success criteria:
- A queued request waits for its `send_after` window, then a `delivery_result` (sent) is written.
- `STOP` writes a `send_canceled` event before the window fires; `SEND NOW` sends immediately; `EDIT` replaces the text and restarts the window.
- `reply_received` events are written for matched replies; no reply by 48h writes `reply_overdue`.
- An unreachable recipient (never started the bot) produces exactly one terminal `delivery_failed`, not a retry loop.
- Direct messages to the bot with no tracked request are recorded as `unmatched_inbound_message`; do not expect an automatic chat reply.

## Bot-start prerequisite

- A Telegram recipient usually must start the Messenger bot once before direct delivery works.
- Before sending a Telegram Messenger request, check whether the recipient has already started the bot when that fact is known.
- If intended recipients have not started the bot, do not attempt delivery; update the task with the prerequisite/date.
- Use a known eligible recipient only after Farzan explicitly redirects the test.
- `/start` from a known team member can satisfy an existing bot-start prerequisite; reachability is then recorded in `inbox/telegram-reachability.json`.

## Unmatched inbound handling

If a known team member texts the messenger bot without a prior tracked request:
- identify the sender via `team-contacts.md`
- intake logs an `unmatched_inbound_message` event and the event-assistant notifies Farzan
- the assistant may create or advance a task autonomously per the Autonomy & review-window protocol; it does not reply to the team member on its own initiative

## Productionize Option A checklist

1. Verify dispatcher, intake, and assistant watcher LaunchAgents are loaded/running.
2. Run syntax checks:
   - `python3 -m py_compile scripts/messenger_common.py scripts/messenger_telegram_dispatcher.py scripts/messenger_telegram_intake.py scripts/messenger_event_assistant.py`
   - `python3 -m unittest discover -s tests`
3. Inspect recent event JSONL and error logs for delivery/reply health; do not treat old resolved setup conflicts as current blockers.
4. Pick the first real pending communication when possible.
5. Persist its draft/next step in `state/active-tasks.jsonl`, refresh `state/active-tasks.md`, then validate the would-be Messenger payload with dispatcher validation logic.
6. Append the JSONL send request with a `send_after` review window and announce it to Farzan; the window (not pre-approval) is the safeguard.

Messenger must not choose recipients, invent contacts, rewrite content, send before the review window elapses (unless a `send_now` control signal is present), or continue conversations on its own.
