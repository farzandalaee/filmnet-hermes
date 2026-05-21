# FilmNet Workflows

Reusable workflows for FilmNet Hermes agents. Operating rules (task management, status reports, draft format, source-of-truth list) live in `agents/assistant.md`; this file holds only the step-by-step procedures.

## 1. Production incident follow-up

Use for production issues, outages, major bugs, CDN problems, playback issues, payment issues, or customer-impacting incidents.

Steps:
1. Find or create a task by reading the index `state/active-tasks.md`, then reading/updating only the relevant full task file under `state/active-tasks/`.
2. Capture only known facts: what happened, affected service or product area, start time, customer/business impact, current owner or team.
3. Identify missing information instead of guessing.
4. Draft follow-up questions for the responsible team.
5. Track next action, owner, and status in the task.
6. After resolution, summarize root cause, fix, and prevention if known.

The follow-up draft must ask about:
1. root cause
2. current status and whether it is resolved
3. user/business impact
4. next prevention action (fix, monitoring, alert)
5. other involved owner if relevant

Do not ask a generic preflight questionnaire before drafting a standard incident follow-up.

## 2. Product request

Use when Farzan wants to define, clarify, prioritize, or follow up on a product idea or request.

Steps:
1. Find or create a task by reading the index `state/active-tasks.md`, then reading/updating only the relevant full task file under `state/active-tasks/`.
2. Write the request in simple language.
3. Capture: goal, user/business problem, affected platform or service, owner or team, open questions.
4. Draft a short requirement or message for the relevant team.
5. Ask Farzan to approve or edit the draft before sharing.

## 3. Documentation update

Use when new FilmNet knowledge should become source of truth.

Steps:
1. Decide which source-of-truth file should be updated: `team-contacts.md`, `communication-rules.md`, `workflows.md`, `services.md`, the active index `state/active-tasks.md`, or a full task file under `state/active-tasks/`.
2. Keep the update small and clear.
3. Do not invent missing details. If uncertain, mark `[to be filled]` or ask Farzan.
4. Prefer simple Markdown over complex systems.
5. After editing, verify references do not point to removed files.

## 4. Completed-task archive

Purpose: keep `state/active-tasks.md` and `state/history-task.md` as cheap-to-read indexes.

Rules:
1. `state/active-tasks.md` contains only active Task IDs and titles.
2. Full active, waiting, pending, draft, and in-progress task records live in `state/active-tasks/<Task ID>.md`.
3. `state/history-task.md` contains only completed Task IDs and titles.
4. Full completed task records live in `state/history-task/<Task ID>.md`.
5. Run `python3 state/archive-completed-tasks.py` daily, or immediately after marking tasks completed.
6. Do not delete completed task history; move per-task files to the history directory.
7. For normal status reports, read only the active index unless Farzan asks for details. Consult `history-task.md` and `state/history-task/` only when Farzan explicitly asks for completed/history/archive status.
