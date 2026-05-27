# Messenger Telegram Runtime

Use for Telegram-specific dispatcher, intake, reply matching, and LaunchAgent checks.

## Two-bot model

- **Control bot** (taskmanager profile): the bot Farzan DMs to talk to the assistant. Notifications and control commands (STOP / SEND NOW / EDIT) live here.
- **Messenger bot** (separate token, resolved by `messenger_common.messenger_bot_token()` from the messenger/global env): the bot that DMs the team and whose updates intake polls. It must be a different bot from the control bot — `messenger_common` refuses the control token to avoid a `getUpdates` 409.

## Runtime scripts

- Dispatcher/send worker: `scripts/messenger_telegram_dispatcher.py`
- Reply intake worker: `scripts/messenger_telegram_intake.py`
- Assistant event watcher: `scripts/messenger_event_assistant.py`

## LaunchAgents

- `/Users/farzan/Library/LaunchAgents/ai.filmnet.messenger-telegram-dispatcher.plist`
- `/Users/farzan/Library/LaunchAgents/ai.filmnet.messenger-telegram-intake.plist`
- `/Users/farzan/Library/LaunchAgents/ai.filmnet.messenger-event-assistant.plist`

The plists no longer pin `HERMES_HOME`; the messenger bot token resolves deterministically in `messenger_common`. After editing a plist, reload it (`launchctl unload`/`load`, or `launchctl kickstart -k gui/$UID/<label>`).

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

Other runtime files (not cursors):
- `inbox/messenger-control.jsonl` — append-only control queue (cancel / send_now / edit), written by the assistant, read by the dispatcher.
- `inbox/telegram-reachability.json` — advisory per-contact reachability cache, written by the dispatcher; the assistant reads it before scheduling a send.

## Behavior

- Intake polls the Telegram Bot API using the **messenger bot** token (refuses the control-gateway token).
- Known senders are mapped from `resources/filmnet/team-contacts.md`.
- Replies match by `reply_to_message.message_id`, else the latest reply-tracked request for that sender that is **not already answered**. An edited reply reuses a stable per-message `event_id`, so it does not re-notify.
- Intake appends `reply_received` or `unmatched_inbound_message` to `inbox/messenger-events.jsonl`.
- Dispatcher holds each request until its `send_after` review window elapses, then sends (single or multi-recipient). It honors `cancel` / `send_now` / `edit` control signals from `inbox/messenger-control.jsonl` (authorized control user only), caps initial attempts (`max_send_attempts`, default 3), stops immediately on permanent errors, records reachability in `inbox/telegram-reachability.json`, sends pre-approved follow-ups when `follow_up.enabled`, and raises `reply_overdue` after `escalate_after_hours` (default 48h).
- Event-assistant reads Messenger events, keeps the related task row in `state/active-tasks.jsonl` current, refreshes the active index when needed, and notifies Farzan **on the control bot** about replies, terminal failures, cancellations, unmatched inbound, and escalations.

## Safety

Inbound recipient text is never passed into Hermes as an agent-control prompt. Ordinary team members should not be added to Hermes gateway allowlists just to reply.

If `logs/messenger-telegram-intake.error.log` shows repeated `Telegram getUpdates HTTP 409`, more than one client is polling the messenger bot. Ensure nothing else (a stray `getUpdates` client, a second intake instance, or a gateway accidentally bound to the messenger bot token) is running, and leave a single intake poller. The control bot and messenger bot must remain distinct tokens.
