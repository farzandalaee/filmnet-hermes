# Active Tasks

## FN-2026-0518-007
- Title: Follow up on Tapsi integration with Masih
- Status: Waiting on Tapsi
- Recipient: Masih Akbari (Backend Lead / Tech Lead)
- Channel: Telegram / Tapsi coordination
- Topic: Tapsi integration follow-up
- Draft summary: Farzan spoke with Masih. Masih has already connected with Tapsi and the current blocker is Tapsi whitelisting FilmNet numbers for the Tapsi staging environment.
- Current update: Masih is waiting for Tapsi to whitelist FilmNet numbers in the Tapsi staging environment.
- Next step: Follow up with Masih/Tapsi if whitelisting is not completed; once whitelisted, proceed with staging validation.
- Last updated date: 2026-05-19

## FN-2026-0518-008
- Title: Follow up on Samsung TV payment dashboard with Mohsen Arghand
- Status: Waiting to schedule time with Mohsen
- Recipient: Mohsen Arghand (stakeholder), Hossein Tahmasebi, Masih Akbari, BI team
- Channel: Internal coordination / BI dashboard request
- Topic: Samsung TV payment integration and BI dashboard
- Draft summary: Farzan spoke with Hossein, Masih, and Mohsen Arghand. Backend and Android code already exist; no further FilmNet backend/Android changes are needed from their side. Remaining need is to ask the BI team to create a dashboard for Samsung TV payments.
- Current update: Technical implementation is ready on backend and Android; next dependency is BI dashboard creation for Samsung TV payments.
- Next step: Farzan to give Mohsen Arghand some time to align on the dashboard/stakeholder side, then ask BI team to create the Samsung TV payments dashboard.
- Last updated date: 2026-05-19

## FN-2026-0518-009
- Title: Create Hermes Agent workshop topic for team training
- Status: Draft waiting for Farzan approval
- Recipient: Entire FilmNet Team
- Channel: Telegram / In-person / Google Meet
- Topic: Hermes Agent training workshop curriculum and announcement
- Draft summary: Recovered from old `/Users/farzan/filmnet-hermes/state/active-tasks.md`; Persian announcement draft exists but should be reviewed for exact audience, time, and channel.
- Draft:
  سلام همکاران عزیز

  برای ارتقای بهره‌وری و آشنایی بهتر با ابزارهای هوشمند، می‌خواهیم یک کارگاه آموزشی درباره Hermes Agent برگزار کنیم.

  هدف کارگاه، آشنایی عملی با استفاده از Hermes Agent در کارهای روزمره مثل مدیریت وظایف، مستندسازی، آماده‌سازی پیام‌ها و هماهنگی بین تیم‌هاست.

  زمان و جزئیات برگزاری بعداً اعلام می‌شود.

  ممنون
  فرزان
- Next step: Farzan to approve/edit the announcement and decide timing/channel.
- Last updated date: 2026-05-18

## FN-2026-0519-008
- Title: Link Hermes with Claude Code using bridge file workflow
- Status: Waiting for Claude Code login
- Recipient: Farzan
- Channel: CLI / local bridge files
- Topic: Use Claude Team subscription through Claude Code CLI while Hermes remains the orchestrator
- Draft summary: Created Claude Code bridge files: root `CLAUDE.md`, executable `scripts/claude-code-bridge.py`, and `resources/filmnet/claude-code-bridge.md`. Verified Claude Code CLI is installed at `/opt/homebrew/bin/claude` and script syntax/executable status is OK. Bridge currently stops safely because Claude Code is not logged in.
- Next step: Farzan to run `claude auth login` in a terminal with the Claude Team account, then test `python3 scripts/claude-code-bridge.py --task "Summarize active tasks" --allowed-tools Read --max-turns 3` from `/Users/farzan/filmnet-hermes`.
- Last updated date: 2026-05-19

## FN-2026-0519-009
- Title: Give feedback to Parsa with Masih collaboration
- Status: Pending tomorrow
- Recipient: Parsa Khodaverdi (Junior Backend Developer), Masih Akbari
- Channel: Internal coordination / feedback
- Topic: Feedback to Parsa, in collaboration with Masih
- Draft summary: Farzan asked to give feedback tomorrow to Parsa Khodaverdi, a recently-started Junior Backend Developer who works with Masih Akbari.
- Next step: On 2026-05-20, coordinate with Masih and prepare/give feedback to Parsa; confirm contact channel if a message draft or direct follow-up is needed.
- Last updated date: 2026-05-19

## FN-2026-0520-013
- Title: Schedule meeting with Shahrokh and Mohammad DevOps about shared storage for edge production servers
- Status: Pending Saturday bot-start prerequisite
- Recipient: Shahrokh Nemati (Infrastructure Lead), Mohammad Ziaee (Full-stack / DevOps)
- Channel: Telegram / meeting coordination
- Topic: Shared storage implementation for production servers, specifically edge servers
- Draft summary: Farzan wants to schedule a meeting with Shahrokh and Mohammad DevOps to discuss shared storage implementation for production edge servers, align on approach, and clarify constraints, risks, and next steps. This remains the target production communication, but Shahrokh and Mohammad have not started the Messenger bot yet.
- Current update: Farzan will ask Shahrokh and Mohammad on Saturday 2026-05-23 to start the bot before Messenger delivery is attempted.
- Draft:
  سلام شاهرخ و محمد

  برای پیاده‌سازی shared storage روی سرورهای production، مخصوصاً edge serverها، می‌خوام یک جلسه کوتاه هماهنگ کنیم تا روی راهکار، محدودیت‌ها، ریسک‌ها و قدم‌های بعدی هم‌نظر بشیم.

  لطفاً زمان‌های خالی‌تون برای امروز یا فردا رو بگید تا جلسه رو هماهنگ کنیم.

  ممنون
- Next step: On Saturday 2026-05-23, Farzan asks Shahrokh and Mohammad to start the bot; after they do, use Messenger Option A to send the approved meeting coordination message with reply tracking.
- Last updated date: 2026-05-20

## FN-2026-0520-014
- Title: Implement Messenger Option A JSONL inbox/outbox workflow
- Status: Waiting for Hossein reply
- Recipient: Hossein Tahmasebi for immediate Messenger test; Shahrokh Nemati and Mohammad Ziaee after bot-start prerequisite
- Channel: Hermes agent workflow / JSONL inbox-outbox / Telegram / Email / future channels
- Topic: Messenger agent sends approved messages and tracks replies for FilmNet assistant using simple auditable JSONL queues first
- Draft summary: Farzan chose Option A as the first Messenger implementation path. Option A means a file-based JSONL command inbox for approved send requests and a JSONL event outbox for delivery results, failures, replies, and unmatched inbound messages. FilmNet assistant remains the orchestrator and updates `state/active-tasks.md`; Messenger only sends exact approved content and reports events.
- Current update: Messenger Phase 1 through Phase 3 are now implemented on the current JSONL architecture. Added Telegram dispatcher `scripts/messenger_telegram_dispatcher.py` to process approved send requests, support both single-recipient and multi-recipient sends, and record delivery events. Kept Telegram reply intake in `scripts/messenger_telegram_intake.py`, updated it for recipient arrays, and preserved the single-poller safety model to avoid Telegram HTTP 409 conflicts. Added assistant-side watcher `scripts/messenger_event_assistant.py` to read Messenger events, update the related task in `state/active-tasks.md` with a Messenger automation summary block, and notify Farzan on Telegram for replies, failures, and unmatched inbound messages. Added LaunchAgents for dispatcher and assistant watcher alongside the existing intake agent, plus state files and logs. Phase 3 follow-up support is implemented through exact pre-approved `follow_up` message payloads with delay/max-attempt controls for non-responders. On 2026-05-20, health check confirmed dispatcher, intake, and assistant watcher LaunchAgents are loaded/running; Python syntax checks pass; no current dispatcher/assistant errors; earlier intake HTTP 409 conflict is recorded in the error log but the intake service is currently running. Shahrokh and Mohammad have not started the bot yet, so Farzan will ask them on Saturday 2026-05-23; for now, use Hossein Tahmasebi because he has already started the bot.
- Draft:
  سلام حسین

  این یک پیام تست از Messenger Hermes FilmNet است. لطفاً اگر دریافت کردی همینجا یک پاسخ کوتاه بده.

  ممنون
- Next step: Wait for Hossein's reply to the new Messenger test request `msgreq-20260520T161715Z-8a5cd207`; when reply arrives, verify reply event, task update, and Telegram notification behavior.
- Messenger automation:
  - Requests:
    - msgreq-20260520T151852Z-942421e4: channel=telegram recipients=1 reply_required=True deadline=[none] follow_up=disabled
    - msgreq-20260520T161715Z-8a5cd207: channel=telegram recipients=1 reply_required=True deadline=[none] follow_up=disabled
  - Recipients:
    - Hossein Tahmasebi: replied at 2026-05-20T15:27:51.947646+00:00 | Got your message
    - Hossein Tahmasebi: replied at 2026-05-20T16:37:03.113030+00:00 | Did you call me?
  - Latest event: reply_received at 2026-05-20T16:37:03.113030+00:00
- Last updated date: 2026-05-20

## FN-2026-0520-015
- Title: Future Messenger Option C JSONL plus Kanban architecture
- Status: Pending future implementation
- Recipient: Farzan / Messenger agent / FilmNet assistant / Hermes Kanban
- Channel: Hermes Kanban / JSONL inbox-outbox / Telegram / Email / future channels
- Topic: Upgrade Messenger from JSONL-only to JSONL event streams plus Kanban durable agent work queue
- Draft summary: Farzan wants Option C implemented in the future after Option A is stable. Option C keeps JSONL/event inbox-outbox as the canonical communication event layer, while using Hermes Kanban for durable work assignments such as send-and-track, follow-up by deadline, failed delivery escalation, and reply-summary jobs.
- Current update: Future architecture decision captured; do not implement until Option A is working and reviewed.
- Next step: After Option A is stable, design Kanban task types, payload links to JSONL events, dispatcher behavior, and completion/blocking rules for Messenger jobs.
- Last updated date: 2026-05-20
