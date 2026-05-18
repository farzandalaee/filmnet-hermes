# FilmNet Hermes Token Efficiency Audit — 2026-05-19

## Scope

Reviewed the FilmNet Hermes profile and workspace as a Hermes/AI-agent optimization audit, with focus on whether scheduled jobs and normal FilmNet sessions are token-heavy.

## Measured sizes

Approximate token estimates use `chars / 4`.

| Component | Chars | Approx tokens | Assessment |
|---|---:|---:|---|
| `~/.hermes/profiles/filmnet/SOUL.md` | 1,669 | 417 | Good / compact |
| `AGENTS.md` | 1,805 | 451 | Good / compact |
| `agents/assistant.md` | 7,859 | 1,964 | Moderate; can be trimmed |
| `state/active-tasks.md` | 4,011 | 1,002 | Good after completed-task archive |
| `state/history-task.md` | 5,261 | 1,315 | Fine because it is not read by default |
| `resources/filmnet/*.md` total | 16,503 | 4,125 | Fine if read selectively |
| `filmnet-orchestrator` skill | 12,228 | 3,057 | Heavy and duplicative with assistant/workflows |
| `hermes-agent` skill | 45,908 | 11,477 | Very heavy; load only for Hermes Agent questions |
| All installed `SKILL.md` files | 1,006,326 | 251,581 | Not all loaded fully, but skill catalog/list overhead exists |

## Scheduled job assessment

The daily completed-task archive job is optimized:

- Job ID: `bc38ba39c5e3`
- Schedule: `5 0 * * *` / 00:05 local time
- `no_agent: true`
- Script: `archive-filmnet-completed-tasks.sh`

Because it uses `no_agent: true`, Hermes does not call an LLM for the job. The wrapper is quiet when zero tasks are archived. This is the correct low-token/near-zero-token design for deterministic maintenance.

## Main findings

1. The daily archive job is not a token eater.
2. Normal interactive FilmNet sessions are moderate-to-heavy because the profile has many enabled toolsets and many installed skills in the available-skills catalog.
3. The biggest repeated FilmNet-specific overhead is duplication across `SOUL.md`, `AGENTS.md`, `agents/assistant.md`, `resources/filmnet/workflows.md`, and the `filmnet-orchestrator` skill.
4. `SOUL.md` is already healthy: compact and pointer-based.
5. `active-tasks.md` is now healthy after completed tasks moved to `history-task.md`.
6. `history-task.md` should not be included in mandatory startup reads; read it only for status completed-task sections or history lookups.

## Recommendations

### Keep as-is

- Keep the archive cron as `no_agent: true`.
- Keep `SOUL.md` compact.
- Keep completed tasks out of `active-tasks.md`.

### Optimize next

1. Slim `filmnet-orchestrator` skill from about 12.2 KB to 4–6 KB by removing duplicated full rules and linking to source files instead.
2. Slim `agents/assistant.md` from about 7.9 KB to 4–5 KB by moving detailed examples and repeated rules into `workflows.md` or skill references.
3. Update status workflow to read `history-task.md` only when completed-task output is needed.
4. Consider reducing CLI toolsets for the FilmNet profile if most FilmNet work is coordination/documentation. Heavy toolsets for default CLI sessions include browser, computer_use, image_gen, tts, vision, web, delegation, cronjob, messaging, and todo. Keep them if Farzan wants a fully capable orchestrator; otherwise create a lean `filmnet-lite` profile for cheap daily use.
5. Consider moving broad creative/research/ML skills out of the FilmNet profile or disabling them from the default catalog if Hermes supports per-profile skill catalog pruning. The profile currently has 89 skills totaling ~1 MB of skill text; they are not fully loaded, but the catalog still adds prompt overhead.

## Priority conclusion

- For scheduled jobs: optimized.
- For day-to-day interactive FilmNet work: acceptable but can be lighter.
- Biggest quick win: slim `filmnet-orchestrator` and `agents/assistant.md`; expected savings around 2,000–3,000 tokens in common FilmNet sessions when the skill is loaded.
