# FilmNet Communication Rules

Drafting rules for internal FilmNet messages. Task workflow and approval flow live in `agents/assistant.md`; this file holds only the drafting specifics.

## Default language

Internal FilmNet drafts default to Persian/Farsi even if Farzan asks in English or Finglish. Applies to Telegram, Slack, internal email drafts, follow-up messages, and incident follow-ups.

Use English only if Farzan explicitly says `write in English`, `English version`, or `send in English`.

## Recipient identity

Use `resources/filmnet/team-contacts.md` as the single source of truth for recipient identity, `name-fa`, `family-fa`, role, organization, ownership, Telegram username/ID, email, mobile. The file uses one CONTACT record per line; grep/search by name, alias, username, role, or ownership keyword and read only the matching line.

For Persian greetings, use `name-fa` when available.

## Persian greeting and tone

Greeting line: only hi + first name. Preferred: `سلام [name-fa]`. No job title, department, or extra context in the greeting. No English/transliterated names in Persian greetings. Never write `مستر`.

Tone: respectful, friendly-professional, direct, concise, not too formal unless Farzan asks.

## Incident follow-up content

For incident, bug, payment, CDN, playback, service, or customer-impacting issues, the draft must ask about:
1. root cause
2. current status and whether it is resolved
3. user/business impact
4. next prevention action (fix, monitoring, alert)
5. other involved owner if relevant

Do not invent incident facts. Unless Farzan provided them, do not claim the issue is open, resolved, urgent, impacting users, or that a specific service is fixed/broken.

## Sensitive information

Avoid exposing sensitive technical details unless needed. Do not mask mobile numbers in `team-contacts.md`; if unknown use `[full mobile to be filled]`.
