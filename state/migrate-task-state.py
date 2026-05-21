#!/usr/bin/env python3
"""Migrate FilmNet task state from Markdown task records to JSONL.

Usage:
  python3 state/migrate-task-state.py

After migration:
- `state/active-tasks.md` contains only `Task ID — Title` index rows.
- `state/history-task.md` contains only completed task index rows.
- Full active task records live in `state/active-tasks.jsonl`, one JSON object per line.
- Full history task records live in `state/history-task.jsonl`, one JSON object per line.
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
    active_removed = task_store.remove_legacy_task_files(ACTIVE_DIR)
    history_removed = task_store.remove_legacy_task_files(HISTORY_DIR)
    print(f"Active JSONL rows: {active_count}")
    print(f"History JSONL rows: {history_count}")
    print(f"Removed legacy active Markdown files: {active_removed}")
    print(f"Removed legacy history Markdown files: {history_removed}")
    print(f"Active index: {ACTIVE_INDEX}")
    print(f"History index: {HISTORY_INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
