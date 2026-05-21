#!/usr/bin/env python3
"""Move completed FilmNet tasks from active JSONL to history JSONL.

Usage:
  python3 state/archive-completed-tasks.py

The script keeps `state/active-tasks.md` as a small task index and stores full
records as one JSON object per line in `state/active-tasks.jsonl` and
`state/history-task.jsonl`.
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
    if not task_store.task_jsonl_path(ACTIVE_DIR).exists() and ACTIVE_INDEX.exists():
        task_store.migrate_legacy_file(ACTIVE_INDEX, ACTIVE_DIR, ACTIVE_INDEX, "Active Tasks")
    if not task_store.task_jsonl_path(HISTORY_DIR).exists() and HISTORY_INDEX.exists():
        task_store.migrate_legacy_file(HISTORY_INDEX, HISTORY_DIR, HISTORY_INDEX, "History Tasks")

    archived, remaining, skipped = task_store.archive_completed(
        ACTIVE_DIR,
        HISTORY_DIR,
        ACTIVE_INDEX,
        HISTORY_INDEX,
    )
    print(f"Archived {archived} completed task(s).")
    print(f"Remaining active task(s): {remaining}.")
    print(f"Skipped duplicate completed task(s): {skipped}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
