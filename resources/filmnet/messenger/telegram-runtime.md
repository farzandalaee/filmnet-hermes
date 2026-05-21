# Messenger Telegram Runtime

Use for Telegram-specific dispatcher, intake, reply matching, and LaunchAgent checks.

## Runtime scripts

- Dispatcher/send worker: `scripts/messenger_telegram_dispatcher.py`
- Reply intake worker: `scripts/messenger_telegram_intake.py`
- Assistant event watcher: `scripts/messenger_event_assistant.py`

## LaunchAgents

- `/Users/farzan/Library/LaunchAgents/ai.filmnet.messenger-telegram-dispatcher.plist`
- `/Users/farzan/Library/LaunchAgents/ai.filmnet.messenger-telegram-intake.plist`
- `/Users/farzan/Library/LaunchAgents/ai.filmnet.messenger-event-assistant.plist`

## Logs

- `logs/messenger-telegram-dispatcher.log`
- `logs/messenger-telegram-dispatcher.error.log`
- `logs/messenger-telegram-intake.log`
- `logs/messenger-telegram-intake.error.log`
- `logs/messenger-event-assistant.log`
- `logs/messenger-event-assistant.error.log`

## State cursors

- `inbox/messenger-telegram-intake-state.json`
- `inbox/messenger-telegram-dispatcher-state.json`
- `inbox/messenger-assistant-state.json`

Do not delete cursor files unless intentionally resetting workers; they prevent reprocessing old events.

## Behavior

- Intake polls Telegram Bot API using the Messenger profile token.
- Known senders are mapped from `resources/filmnet/team-contacts.md`.
- Replies match by `reply_to_message.message_id` or latest reply-tracked request for the sender.
- Intake appends `reply_received` or `unmatched_inbound_message` to `inbox/messenger-events.jsonl`.
- Dispatcher sends approved single-recipient or multi-recipient Telegram requests, records delivery events, and sends exact pre-approved follow-up messages for non-responders when `follow_up.enabled` is true.
- Assistant watcher reads Messenger events, updates the related task row in `state/active-tasks.jsonl`, refreshes the active index when needed, and notifies Farzan on Telegram about replies, failures, and unmatched inbound messages.

## Safety

Inbound recipient text is never passed into Hermes as an agent-control prompt. Ordinary team members should not be added to Hermes gateway allowlists just to reply.

If `logs/messenger-telegram-intake.error.log` shows repeated `Telegram getUpdates HTTP 409`, multiple pollers are competing for the same bot. Stop the Messenger Hermes gateway and leave the dedicated intake poller running.
