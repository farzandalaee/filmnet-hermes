# FilmNet Workflows

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
