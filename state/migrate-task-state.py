#!/usr/bin/env python3
"""Migrate FilmNet task state from monolithic Markdown files to per-task files.

Usage:
  python3 state/migrate-task-state.py

After migration:
- `state/active-tasks.md` contains only `Task ID — Title` index rows.
- `state/history-task.md` contains only completed task index rows.
- Full active task records live in `state/active-tasks/<task-id>.md`.
- Full history task records live in `state/history-task/<task-id>.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from state import task_store  # noqa: E402

ACTIVE_INDEX = ROOT / "state" / "active-tasks.md"
HISTORY_INDEX = ROOT / "state" / "history-task.md"
ACTIVE_DIR = ROOT / "state" / "active-tasks"
HISTORY_DIR = ROOT / "state" / "history-task"


def main() -> int:
    active_count = task_store.migrate_legacy_file(ACTIVE_INDEX, ACTIVE_DIR, ACTIVE_INDEX, "Active Tasks")
    history_count = task_store.migrate_legacy_file(HISTORY_INDEX, HISTORY_DIR, HISTORY_INDEX, "History Tasks")
    print(f"Active task files: {active_count}")
    print(f"History task files: {history_count}")
    print(f"Active index: {ACTIVE_INDEX}")
    print(f"History index: {HISTORY_INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
