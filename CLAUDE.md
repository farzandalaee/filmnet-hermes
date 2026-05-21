# Claude Code Bridge

This file is loaded only when Claude Code is invoked by Hermes through the local bridge scripts. The full FilmNet operating rules live in `agents/assistant.md`; read that for any FilmNet work.

## Role

- Hermes is Farzan's primary orchestrator and source-of-truth keeper.
- Claude Code is a delegated worker for analysis, coding, refactoring, reviews, and structured handoff notes.
- Farzan communicates with Hermes first. Claude Code returns factual results to bridge output files/stdout; it does not message FilmNet team members.

## Bridge output expectations

When invoked by Hermes, return:
- concise summary
- files changed/read
- commands run
- verification result
- blockers or required Farzan decision
- suggested next step

For code changes, do not commit or push unless Farzan explicitly requests it through Hermes.

Bridge setup, usage examples, and recommended `--allowed-tools` defaults: `resources/filmnet/claude-code-bridge.md`.
