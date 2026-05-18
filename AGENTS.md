# FilmNet Hermes Project Instructions

This directory is a FilmNet-specific Hermes workspace for Farzan.

## Required Read Order

Before doing any FilmNet work in this repository, read:
1. `agents/assistant.md`
2. `state/active-tasks.md`
3. Relevant files under `resources/filmnet/`

For internal FilmNet message drafting, also read:
1. `resources/filmnet/communication-rules.md`
2. `resources/filmnet/team-contacts.md`

## Source of Truth

- Active work and follow-ups: `state/active-tasks.md`
- Completed task archive: `state/history-task.md`
- Assistant behavior and operating rules: `agents/assistant.md`
- Communication rules: `resources/filmnet/communication-rules.md`
- Team identity, roles, ownership, and contact data: `resources/filmnet/team-contacts.md`
- Service ownership: `resources/filmnet/services.md`
- Reusable workflows: `resources/filmnet/workflows.md`

Do not rely on chat history for FilmNet task state. Use the files above.

## Important Constraints

- Do not send messages automatically. Draft first and ask Farzan for approval.
- Do not invent FilmNet facts. If a detail is missing, mark it as missing or ask Farzan.
- Do not recreate `resources/filmnet/teams-organization.md`; it was merged into `team-contacts.md` and removed.
- Keep Markdown simple and easy for Hermes agents to parse.

## Completed Task Archive

- Keep `state/active-tasks.md` focused on active, waiting, pending, and draft tasks.
- Move completed tasks to `state/history-task.md` so future agents do not pay to read long historical state for every status check.
- Run `python3 state/archive-completed-tasks.py` daily, or after marking tasks completed, to archive completed tasks.
- For status reports, read `state/active-tasks.md` for active work and `state/history-task.md` only for completed-task history.
