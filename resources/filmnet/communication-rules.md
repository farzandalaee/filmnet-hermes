# FilmNet Communication Rules

- Internal FilmNet Telegram drafts MUST be Persian/Farsi by default.
- Tone should be respectful, direct, and not too long.
- For team leads, use friendly professional tone.
- Always draft first and ask Farzan before sending.
- For incident and bug follow-up, ask root cause, status, impact, and prevention.
- Avoid exposing sensitive technical details in unnecessary places.

## Task Persistence Rule

- When a Task ID is created or reused, it MUST be saved in `state/active-tasks.md`.
- A Task ID shown to Farzan is invalid unless it is also saved in `state/active-tasks.md`.
- For every message draft task, save Task ID, title, status, recipient, channel, topic, draft summary, next step, and last updated date.

## Incident Follow-up Message Rule

For incident/payment/service issue follow-up messages, the draft MUST ask about:

1. root cause
2. current status / whether resolved
3. user/business impact
4. next prevention action such as fix, monitoring, or alert
5. other involved owner if relevant

Do not ask a generic preflight questionnaire before drafting a standard incident/payment/service issue follow-up message. Draft first using the required incident follow-up questions, then ask Farzan for approval or edits.

Do not invent incident facts while drafting. Unless Farzan provided them, do not claim a previous message is still open, users/business are currently impacted, the issue is urgent, or the service is fixed/still broken.

## Draft Response Format Rule

Every draft response must include Task ID, title, status, recipient, channel, draft text, and approval question.
