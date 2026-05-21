# Messenger Runtime Hygiene

Use for Messenger runtime maintenance, log/JSONL rotation, and git hygiene.

## Git hygiene

Ignore runtime queues, cursors, logs, `.env` files, Python caches, and archives. Keep source/docs/scripts tracked.

Recommended ignored local runtime paths include:
- `logs/`
- `archive/`
- `*.gz`
- `inbox/*.jsonl`
- `inbox/*-state.json`
- bridge queue JSONL files

If JSONL queues or caches were already tracked, untrack with `git rm --cached ...` without deleting local files.

## Rotation

Use repo script:
- dry run: `python3 scripts/rotate_runtime_files.py --dry-run`
- rotate: `python3 scripts/rotate_runtime_files.py`

The script archives old/large runtime files under `archive/runtime/`, keeps recent JSONL lines active for reply matching, and deliberately does not rotate state cursor files.

## Cursor safety

Do not casually delete these cursor files:
- `inbox/messenger-telegram-intake-state.json`
- `inbox/messenger-telegram-dispatcher-state.json`
- `inbox/messenger-assistant-state.json`

Delete cursor files only when intentionally resetting workers and accepting old-event reprocessing risk.

## Performance note

Before heavy production use, keep deterministic rotation enabled/available because dispatcher, intake, and event-assistant scripts read/index JSONL queues directly.
