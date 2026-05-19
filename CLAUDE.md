# FilmNet Hermes / Claude Code Bridge

This repository is Farzan's FilmNet Hermes workspace. Claude Code may be invoked by Hermes as a delegated coding/reasoning worker through local bridge scripts.

## Role Split

- Hermes is Farzan's primary orchestrator and source-of-truth keeper.
- Claude Code is a delegated worker for analysis, coding, refactoring, reviews, and structured handoff notes.
- Farzan communicates with Hermes first. Claude Code should return factual results to bridge output files/stdout; it should not message FilmNet team members.

## Source of Truth

Before FilmNet-related work, read:
1. `AGENTS.md`
2. `agents/assistant.md`
3. `state/active-tasks.md`
4. Relevant files under `resources/filmnet/`

Do not rely on chat history for FilmNet task state.

## Safety and Communication

- Do not send FilmNet messages automatically.
- Draft internal FilmNet messages in Persian/Farsi unless Farzan explicitly asks for English.
- Use `resources/filmnet/team-contacts.md` as the single source of truth for team identity/contact/ownership.
- Do not recreate `resources/filmnet/teams-organization.md`.
- Do not mask mobile numbers in `team-contacts.md`; use full numbers or `[full mobile to be filled]`.
- Do not invent FilmNet facts. Mark missing details as `[to be filled]`.

## Bridge Output Expectations

When invoked by Hermes, return:
- concise summary
- files changed/read
- commands run
- verification result
- blockers or required Farzan decision
- suggested next step

For code changes, avoid committing or pushing unless explicitly requested by Farzan through Hermes.
