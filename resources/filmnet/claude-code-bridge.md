# Claude Code Bridge

This bridge lets Hermes delegate work to Claude Code CLI while Claude Code uses Farzan's Claude subscription login/OAuth instead of Hermes' Anthropic API provider.

## Files

- `CLAUDE.md` — Claude Code project context for this FilmNet Hermes workspace.
- `scripts/claude-code-bridge.py` — wrapper Hermes can call via terminal.
- `inbox/claude-code-bridge/requests.jsonl` — append-only request log.
- `inbox/claude-code-bridge/responses.jsonl` — append-only response log.

## One-time setup

Claude Code is installed, but must be logged in once:

```bash
claude auth login
```

Use the Claude Team account in the browser login. This should use Claude Code subscription login, not Hermes' `ANTHROPIC_API_KEY` provider.

Check:

```bash
claude auth status --text
```

## Usage from Hermes / terminal

Read-only analysis:

```bash
python3 scripts/claude-code-bridge.py \
  --task "Review state/active-tasks.md and summarize current blockers" \
  --allowed-tools Read \
  --max-turns 5
```

Allow edits in the workspace:

```bash
python3 scripts/claude-code-bridge.py \
  --task "Update CLAUDE.md to add a concise testing checklist" \
  --allowed-tools Read,Edit,Write \
  --max-turns 8
```

Code tasks with commands:

```bash
python3 scripts/claude-code-bridge.py \
  --task "Run tests, identify failures, and propose fixes" \
  --allowed-tools Read,Bash \
  --max-turns 10
```

## Recommended defaults

- Start with `--allowed-tools Read`.
- Add `Edit,Write` only for file changes.
- Add `Bash` only when commands/tests are needed.
- Use `--max-turns` to avoid runaway Claude Code work.
- Do not ask Claude Code to send FilmNet messages; it should draft only.

## Why this solves the billing issue

Hermes direct provider `anthropic` uses Anthropic API / third-party extra usage.
Claude Code login can use the Claude Team/Max/Pro account path.
The bridge keeps Hermes as orchestrator but delegates Claude work through the `claude` CLI.

If `scripts/claude-code-bridge.py` says `Not logged in`, run `claude auth login` manually in a terminal.
