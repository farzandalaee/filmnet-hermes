# Messenger Testing and Production

Use when Farzan asks to test Telegram/email communications, productionize Option A, or verify Messenger health.

## Testing rule

For current Messenger Option A Telegram, test it as a send-and-track system, not as a conversational bot.

Success criteria:
- `delivery_result` events are written for approved sends.
- `reply_received` events are written for matched replies.
- Direct Telegram messages sent to the bot may be recorded as `unmatched_inbound_message`; do not expect an automatic chat reply.

## Bot-start prerequisite

- A Telegram recipient usually must start the Messenger bot once before direct delivery works.
- Before sending a Telegram Messenger request, check whether the recipient has already started the bot when that fact is known.
- If intended recipients have not started the bot, do not attempt delivery; update the task with the prerequisite/date.
- Use a known eligible recipient only after Farzan explicitly redirects the test.
- `/start` from a known team member can satisfy an existing bot-start prerequisite, but still do not send anything without Farzan approval.

## Unmatched inbound handling

If a known team member texts the Messenger bot without a prior tracked request:
- identify the sender via `team-contacts.md`
- log/inspect the event
- notify Farzan
- do not reply, create a task, or advance a task unless Farzan approves or an existing task has a clear prerequisite that the message satisfies

## Productionize Option A checklist

1. Verify dispatcher, intake, and assistant watcher LaunchAgents are loaded/running.
2. Run syntax checks:
   - `python3 -m py_compile scripts/messenger_telegram_dispatcher.py scripts/messenger_telegram_intake.py scripts/messenger_event_assistant.py`
3. Inspect recent event JSONL and error logs for delivery/reply health; do not treat old resolved setup conflicts as current blockers.
4. Pick the first real pending approved-candidate communication when possible.
5. Persist its draft/next step in `state/active-tasks.jsonl`, refresh `state/active-tasks.md`, then validate the would-be Messenger payload with dispatcher validation logic.
6. Do not append the JSONL send request until Farzan approves exact message text.

Messenger must not choose recipients, invent contacts, rewrite content, send without approval, or continue conversations without explicit thread-level instructions.
