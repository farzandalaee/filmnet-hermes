# FilmNet Workflows

Reusable workflows for FilmNet Hermes agents.

## 1. Source-of-Truth Workflow

Before FilmNet work:
1. Read `state/active-tasks.md`.
2. Read relevant files under `resources/filmnet/`.
3. For internal messages, read `resources/filmnet/communication-rules.md` and `resources/filmnet/team-contacts.md`.

Do not rely on chat history for active task state.
Do not recreate `resources/filmnet/teams-organization.md`; it was merged into `team-contacts.md` and removed.

## 2. Task Persistence Workflow

When creating or reusing a Task ID, persist it in `state/active-tasks.md`.

If `state/active-tasks.md` is missing, deleted, or empty:
1. Recreate the file.
2. Add `# Active Tasks` as the title.
3. Save the task there.

A Task ID shown to Farzan is invalid unless it is saved in `state/active-tasks.md`.

Task record fields:
- Title
- Status
- Recipient
- Channel
- Topic
- Draft summary
- Next step
- Last updated date

## 3. Status Report Workflow

Use this workflow when Farzan says `status`, `show active tasks`, or asks what is pending.

Steps:
1. Read `state/active-tasks.md`.
2. Show all active / waiting / pending tasks first, with Task ID, title, status, and next step.
3. For completed tasks, do not show the full historical completed list.
4. Get the current local date.
5. Show completed tasks whose `Last updated date` matches the current local date.
6. If no completed task matches the current local date, show only the last 5 completed tasks, ordered newest first.
7. Label the completed section as either:
   - `Completed today`
   - `Recent completed tasks (last 5 because none completed today)`

## 4. Message Draft Workflow

Use this workflow before sending or forwarding any external or team message.

Rules:
1. Do not send messages automatically.
2. Draft the message first.
3. Use Persian/Farsi for internal FilmNet messages unless Farzan explicitly asks for English.
4. Use `name-fa` from `team-contacts.md` for Persian greetings when available.
5. Show Farzan the draft and ask for approval.
6. If Farzan asks for changes, update the draft and ask again.
7. If Farzan says `yes` or `ok`, apply it only to the latest active question.

Draft response format:

```text
Task: <Task ID>
Title: <Task title>
Status: Draft waiting for Farzan approval
Recipient: <recipient>
Channel: <Telegram/Slack/Email/etc>

Draft:
<message>

Approval: Should I keep this draft, edit it, or prepare it for sending?
```

## 5. Production Incident Follow-Up Workflow

Use this workflow for production issues, outages, major bugs, CDN problems, playback issues, payment issues, or customer-impacting incidents.

Steps:
1. Find or create a task in `state/active-tasks.md`.
2. Capture only known facts:
   - what happened
   - affected service or product area
   - start time, if known
   - customer/business impact, if known
   - current owner or team, if known
3. Identify missing information instead of guessing.
4. Draft follow-up questions for the responsible team.
5. Track next action, owner, and status in the task.
6. After resolution, summarize root cause, fix, and prevention if known.

The follow-up draft must ask about:
1. root cause
2. current status and whether it is resolved
3. user/business impact
4. next prevention action such as fix, monitoring, or alert
5. other involved owner if relevant

Do not ask a generic preflight questionnaire before drafting a standard incident follow-up.

## 6. Product Request Workflow

Use this workflow when Farzan wants to define, clarify, prioritize, or follow up on a product idea or request.

Steps:
1. Find or create a task in `state/active-tasks.md`.
2. Write the request in simple language.
3. Capture:
   - goal
   - user or business problem
   - affected platform or service
   - owner or team, if known
   - open questions
4. Draft a short requirement or message for the relevant team.
5. Ask Farzan to approve or edit the draft before sharing.

## 7. Documentation Update Workflow

Use this workflow when new FilmNet knowledge should become source of truth.

Steps:
1. Decide which source-of-truth file should be updated:
   - `resources/filmnet/team-contacts.md`
   - `resources/filmnet/communication-rules.md`
   - `resources/filmnet/workflows.md`
   - `resources/filmnet/services.md`
   - `state/active-tasks.md`
2. Keep the update small and clear.
3. Do not invent missing details.
4. If information is uncertain, mark it as `[to be filled]` or ask Farzan.
5. Prefer simple Markdown over complex systems.
6. After editing, verify references do not point to removed files.
