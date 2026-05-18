#!/usr/bin/env python3
"""Move completed FilmNet tasks from active-tasks.md to history-task.md.

Usage:
  python3 state/archive-completed-tasks.py

The script is intentionally dependency-free so it can be run manually or by a
scheduler once per day. It keeps `active-tasks.md` small while preserving all
completed task records in `history-task.md`.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PATH = ROOT / "state" / "active-tasks.md"
HISTORY_PATH = ROOT / "state" / "history-task.md"

TASK_RE = re.compile(r"(?=^## FN-\d{4}-\d{4}-\d{3}\s*$)", re.M)
ID_RE = re.compile(r"^## (FN-\d{4}-\d{4}-\d{3})\s*$", re.M)
STATUS_RE = re.compile(r"^- Status:\s*(.+?)\s*$", re.M)


def split_tasks(text: str) -> tuple[str, list[str]]:
    parts = TASK_RE.split(text.rstrip() + "\n")
    header = parts[0].rstrip() + "\n"
    tasks = [part.strip() + "\n" for part in parts[1:] if part.strip()]
    return header, tasks


def task_id(task: str) -> str:
    match = ID_RE.search(task)
    if not match:
        raise ValueError(f"Task block missing ID: {task[:80]!r}")
    return match.group(1)


def is_completed(task: str) -> bool:
    match = STATUS_RE.search(task)
    return bool(match and match.group(1).strip().lower() == "completed")


def history_ids(history_text: str) -> set[str]:
    return set(ID_RE.findall(history_text))


def main() -> int:
    if not ACTIVE_PATH.exists():
        raise SystemExit(f"Missing active task file: {ACTIVE_PATH}")

    active_text = ACTIVE_PATH.read_text(encoding="utf-8")
    active_header, active_tasks = split_tasks(active_text)

    completed = [task for task in active_tasks if is_completed(task)]
    remaining = [task for task in active_tasks if not is_completed(task)]

    if HISTORY_PATH.exists():
        history_text = HISTORY_PATH.read_text(encoding="utf-8").rstrip() + "\n"
    else:
        history_text = "# History Tasks\n\nCompleted FilmNet tasks archived from `state/active-tasks.md`.\n"

    existing = history_ids(history_text)
    new_completed = [task for task in completed if task_id(task) not in existing]

    new_active_text = active_header.rstrip() + "\n"
    if remaining:
        new_active_text += "\n" + "\n\n".join(task.rstrip() for task in remaining) + "\n"
    ACTIVE_PATH.write_text(new_active_text, encoding="utf-8")

    if new_completed:
        if not history_text.endswith("\n\n"):
            history_text = history_text.rstrip() + "\n\n"
        history_text += "\n\n".join(task.rstrip() for task in new_completed) + "\n"
        HISTORY_PATH.write_text(history_text, encoding="utf-8")
    elif not HISTORY_PATH.exists():
        HISTORY_PATH.write_text(history_text, encoding="utf-8")

    print(f"Archived {len(new_completed)} completed task(s).")
    print(f"Remaining active task(s): {len(remaining)}.")
    print(f"Skipped duplicate completed task(s): {len(completed) - len(new_completed)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
