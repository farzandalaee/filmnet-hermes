# FilmNet Workflows

## Task Persistence Rule

When the assistant creates or reuses a Task ID, it MUST persist it in:
`state/active-tasks.md`

If `state/active-tasks.md` is missing, deleted, or empty:
1. Recreate the file.
2. Add `# Active Tasks` as the title.
3. Save the new task there.

A Task ID shown to Farzan is invalid unless it is also saved in `state/active-tasks.md`.

For every message draft task, save:
- Task ID
- Title
- Status
- Recipient
- Channel
- Topic
- Draft summary
- Next step
- Last updated date

## Incident Follow-up Message Rule

For incident/payment/service issue follow-up messages, the draft MUST ask about:
1. root cause
2. current status / whether resolved
3. user/business impact
4. next prevention action such as fix, monitoring, or alert
5. other involved owner if relevant

If Farzan asks for an incident/payment/service issue follow-up draft, do not ask a generic preflight questionnaire before drafting. Use the standard incident follow-up questions above unless Farzan asks for a different style.

For the request "Draft a Telegram message to Masih about payment service issue. Do not send.", reuse the active payment-service task if it exists and produce the Persian draft immediately.

## Persian Name/Tone Rule

For internal Persian Telegram messages:
- Do not write "مستر".
- Do not mix awkward English name style like "Masih" inside Persian greeting.
- Prefer:
  "مسیح جان سلام،"
- Use friendly professional tone.
- Keep the message clear and direct.

## Draft Response Format Rule

Every draft response must include:
Task: <Task ID>
Title: <Task title>
Status: <status>

Recipient:
Channel:

Draft:
<message>

Approval:
Should I keep this draft, edit it, or prepare it for sending?

## Production Incident Follow-Up

Use this workflow when there is a production issue, outage, major bug, CDN problem, playback issue, payment issue, or customer-impacting incident.

Steps:
1. Create a task in `state/active-tasks.md` with a Task ID.
2. Capture the current known facts:
   - what happened
   - affected service or product area
   - start time, if known
   - customer impact, if known
   - current owner or team, if known
3. Identify missing information instead of guessing.
4. Draft follow-up questions for the responsible team.
5. Track next action, owner, and status in the task.
6. After resolution, summarize:
   - root cause, if known
   - fix
   - prevention or follow-up work

## Product Request Workflow

Use this workflow when Farzan wants to define, clarify, prioritize, or follow up on a product idea or request.

Steps:
1. Create a task in `state/active-tasks.md` with a Task ID.
2. Write the request in simple language.
3. Capture:
   - goal
   - user or business problem
   - affected platform or service
   - owner or team, if known
   - open questions
4. Draft a short requirement or message for the relevant team.
5. Ask Farzan to approve or edit the draft before sharing.

## Message Approval Workflow

Use this workflow before sending or forwarding any external or team message.

Rules:
1. Do not send messages automatically.
2. Draft the message first.
3. Show Farzan the draft and ask for approval.
4. If Farzan says "yes" or "ok", apply it only to the latest active question.
5. If Farzan asks for changes, update the draft and ask again.

## Documentation Update Workflow

Use this workflow when new FilmNet knowledge should become source of truth.

Steps:
1. Decide which file should be updated:
   - `resources/filmnet/teams-organization.md`
   - `resources/filmnet/workflows.md`
   - `resources/filmnet/services.md`
   - `state/active-tasks.md`
2. Keep the update small and clear.
3. Do not invent missing details.
4. If the information is uncertain, mark it as unknown or ask Farzan.
5. Prefer simple Markdown over complex systems.
