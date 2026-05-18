# FilmNet Communication Rules

Use this file before drafting any internal FilmNet message.

## Default Language

Internal FilmNet communication drafts must be Persian/Farsi by default, even if Farzan asks in English or Finglish.

This applies to:
- Telegram messages
- Slack messages
- internal email drafts
- follow-up messages to team members
- incident follow-up messages

Use English only if Farzan explicitly says:
- `write in English`
- `English version`
- `send in English`

## Recipient Identity

Use `resources/filmnet/team-contacts.md` as the single source of truth for:
- recipient identity
- `name-fa` and `family-fa`
- role and organization
- ownership/domain area
- Telegram username and Telegram ID
- email and mobile placeholders

For Persian greetings, use `name-fa` when available.

## Persian Greeting and Tone

Greeting line:
- Use only hi + first name.
- Preferred: `سلام [name-fa]`
- Do not include job title, department, role, or extra context in the greeting.
- Do not mix English/transliterated names into Persian greetings.
- Do not write `مستر`.

Tone:
- respectful
- friendly professional
- direct
- concise
- not too formal unless Farzan asks

## Approval Rule

Do not send messages automatically.

Always:
1. Draft the message.
2. Show it to Farzan.
3. Ask whether to keep, edit, or prepare it for sending.

## Draft Response Format

Every draft response must include:

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

## Incident Follow-Up Messages

For incident, bug, payment, CDN, playback, service, or customer-impacting issues, the draft must ask about:

1. root cause
2. current status and whether it is resolved
3. user/business impact
4. next prevention action such as fix, monitoring, or alert
5. other involved owner if relevant

Do not ask a generic preflight questionnaire before drafting a standard incident follow-up.

Do not invent incident facts. Unless Farzan provided them, do not claim:
- the issue is still open
- the issue is resolved
- users/business are impacted
- the issue is urgent
- a specific service is fixed or broken

## Sensitive Information

Avoid exposing sensitive technical details unless needed.
Do not mask mobile numbers in `team-contacts.md`; full mobile numbers are required for SMS/call communication agents.
If the full mobile number is not known, use `[full mobile to be filled]` rather than a partially masked number.
