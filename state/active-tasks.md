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
- Status: Draft waiting for Farzan approval
- Recipient: Shahrokh Nemati (Infrastructure Lead), Mohammad Ziaee (Full-stack / DevOps)
- Channel: Telegram / meeting coordination
- Topic: Shared storage implementation for production servers, specifically edge servers
- Draft summary: Farzan wants to schedule a meeting with Shahrokh and Mohammad DevOps to discuss shared storage implementation for production edge servers, align on approach, and clarify constraints, risks, and next steps.
- Next step: Review/edit the draft message, send after Farzan approval, then capture meeting time and agenda.
- Last updated date: 2026-05-20
