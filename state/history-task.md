# History Tasks

Completed FilmNet tasks archived from `state/active-tasks.md`.

## FN-2026-0518-001
- Title: Merge FilmNet team contacts and organization files
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Update `resources/filmnet/team-contacts.md` from `contact-info.txt`, merge `teams-organization.md`, and remove old organization file.
- Draft summary: N/A
- Next step: Use `resources/filmnet/team-contacts.md` as the single source of truth for team organization and contacts.
- Last updated date: 2026-05-18

## FN-2026-0518-002
- Title: Add Persian name fields to FilmNet team contacts
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Add `name-fa` and `family-fa` fields for every person in `resources/filmnet/team-contacts.md`.
- Draft summary: N/A
- Next step: Use `name-fa` for Persian greeting lines in internal message drafts.
- Last updated date: 2026-05-18

## FN-2026-0518-003
- Title: Review and optimize FilmNet Hermes workspace instructions
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Review `/Users/farzan/filmnet-hermes2` as a Hermes Agent expert/developer and update instruction/resource files to be easy for Hermes agents to read and follow.
- Draft summary: N/A
- Next step: Use `AGENTS.md`, `agents/assistant.md`, and `resources/filmnet/` as the stable instruction set for future FilmNet Hermes sessions.
- Last updated date: 2026-05-18

## FN-2026-0518-004
- Title: Update mobile number storage rule for communication agents
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Do not mask mobile numbers in FilmNet contact files because SMS/call communication agents need full numbers.
- Draft summary: N/A
- Next step: Fill full mobile numbers in `resources/filmnet/team-contacts.md` when available; do not store partially masked mobile numbers.
- Last updated date: 2026-05-18

## FN-2026-0518-005
- Title: Review FilmNet profile SOUL.md entry point
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Read `/Users/farzan/.hermes/profiles/filmnet2/SOUL.md` and provide suggestions without overwriting it.
- Draft summary: Suggestions only; no SOUL.md edits made.
- Next step: Farzan can choose which suggested changes to apply to `SOUL.md`.
- Last updated date: 2026-05-18

## FN-2026-0518-006
- Title: Update FilmNet profile SOUL.md entry point
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Replace `/Users/farzan/.hermes/profiles/filmnet2/SOUL.md` with the approved concise bootstrap instructions for FilmNet Hermes agent behavior.
- Draft summary: N/A
- Next step: Future FilmNet Hermes sessions should load the updated SOUL.md and then read AGENTS.md, assistant.md, active-tasks.md, and relevant resources.
- Last updated date: 2026-05-18

## FN-2026-0519-001
- Title: Promote FilmNet2 Hermes profile to FilmNet
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Rename the previous `filmnet` Hermes profile to `filmnet-old`, rename the stronger `filmnet2` profile to `filmnet`, and set `filmnet` as the sticky/default profile.
- Draft summary: N/A
- Next step: Use `/Users/farzan/filmnet-hermes` as the current FilmNet workspace and `filmnet` / `hermes -p filmnet` for future sessions. The previous profile is preserved as `filmnet-old`.
- Last updated date: 2026-05-19

## FN-2026-0519-002
- Title: Update FilmNet status report completed-task display rule
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Change status reports so completed tasks show only current-day completions, or the last 5 completed tasks if none were completed today.
- Draft summary: Updated `agents/assistant.md`, `resources/filmnet/workflows.md`, and the `filmnet-orchestrator` skill to avoid long historical completed-task lists in status reports.
- Next step: Future `status` responses should show active/waiting/pending tasks first, then completed tasks for today's local date; if none today, show only the last 5 completed tasks.
- Last updated date: 2026-05-19

## FN-2026-0519-003
- Title: Archive completed FilmNet tasks out of active task state
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Move completed tasks from `state/active-tasks.md` to `state/history-task.md` and document a daily archive workflow so active state stays small and cheap to read.
- Draft summary: Created `state/history-task.md`, `state/archive-completed-tasks.py`, and updated workspace/assistant/workflow/skill instructions so completed task history is archived out of active state.
- Next step: Run `python3 state/archive-completed-tasks.py` daily or after marking tasks completed; status reports should read active work from `active-tasks.md` and completed history from `history-task.md`.
- Last updated date: 2026-05-19

## FN-2026-0519-004
- Title: Schedule daily completed-task archive
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Schedule the completed-task archive to run every day at 00:05.
- Draft summary: Created quiet wrapper `/Users/farzan/.hermes/profiles/filmnet/scripts/archive-filmnet-completed-tasks.sh` and cron job `bc38ba39c5e3` scheduled for `5 0 * * *`.
- Next step: Cron job will run daily at 00:05 local time and only deliver output when tasks were archived or if an error occurs.
- Last updated date: 2026-05-19

## FN-2026-0519-005
- Title: Analyze FilmNet Hermes agent token efficiency for jobs
- Status: Completed
- Recipient: N/A
- Channel: N/A
- Topic: Review FilmNet Hermes agent/profile/task-state/skills/cron setup for token overhead and identify optimization opportunities, especially for scheduled jobs.
- Draft summary: Audit completed and saved to `references/filmnet-orchestrator/token-efficiency-audit-2026-05-19.md`; daily archive cron is optimized with `no_agent: true`, while interactive sessions are moderate-to-heavy mainly due to toolsets, skill catalog, and duplicated FilmNet rules.
- Next step: If Farzan approves, slim `filmnet-orchestrator` and `agents/assistant.md`, and optionally create a lean `filmnet-lite` profile.
- Last updated date: 2026-05-19

## FN-2026-0519-007
- Title: Audit FilmNet Hermes agent token efficiency for jobs
- Status: Completed
- Recipient: Farzan
- Channel: CLI / Hermes configuration
- Topic: FilmNet Hermes profile, startup context, enabled toolsets, and cron job token usage
- Draft summary: Optimization completed. Slimmed `agents/assistant.md` from ~1,936 to ~1,292 tokens, slimmed `filmnet-orchestrator` skill from ~3,992 to ~1,480 tokens, and added `references/lean-cron-jobs.md` for no_agent/script-only and restricted-toolset job patterns. Mandatory FilmNet startup subtotal reduced from ~3,826 to ~3,328 rough tokens despite this task record increasing active state slightly.
- Next step: For future FilmNet cron jobs, use `no_agent: true` for deterministic scripts or set narrow `enabled_toolsets` such as `["file"]`; avoid attaching `hermes-agent` unless the job is specifically about Hermes setup/debugging.
- Last updated date: 2026-05-19
