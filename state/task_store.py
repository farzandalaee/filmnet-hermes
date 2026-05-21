#!/usr/bin/env python3
"""Utilities for FilmNet per-task Markdown state files."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Iterable, List, Tuple

TASK_ID_PATTERN = r"FN-\d{4}-\d{4}-\d{3}"
TASK_HEADING_RE = re.compile(rf"^##\s+({TASK_ID_PATTERN})\s*$", re.MULTILINE)
TASK_SPLIT_RE = re.compile(rf"(?=^##\s+{TASK_ID_PATTERN}\s*$)", re.MULTILINE)
TITLE_RE = re.compile(r"^- Title:\s*(.+?)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^- Status:\s*(.+?)\s*$", re.MULTILINE)
READ_FILE_PREFIX_RE = re.compile(r"^\s*\d+\|\s?")


def normalize_read_file_prefixes(text: str) -> str:
    """Remove accidental read_file line-number prefixes from persisted Markdown."""
    normalized_lines: List[str] = []
    for line in text.splitlines():
        previous = None
        current = line
        while previous != current:
            previous = current
            current = READ_FILE_PREFIX_RE.sub("", current, count=1)
        normalized_lines.append(current)
    return "\n".join(normalized_lines) + ("\n" if text.endswith("\n") else "")


def split_legacy_tasks(text: str) -> List[str]:
    normalized = normalize_read_file_prefixes(text).rstrip() + "\n"
    parts = TASK_SPLIT_RE.split(normalized)
    return [part.strip() + "\n" for part in parts[1:] if part.strip()]


def task_id(task_text: str) -> str:
    match = TASK_HEADING_RE.search(task_text)
    if not match:
        raise ValueError(f"Task block missing ID: {task_text[:120]!r}")
    return match.group(1)


def task_title(task_text: str) -> str:
    match = TITLE_RE.search(task_text)
    if match:
        return match.group(1).strip()
    return "[title missing]"


def task_status(task_text: str) -> str:
    match = STATUS_RE.search(task_text)
    if match:
        return match.group(1).strip()
    return ""


def is_completed(task_text: str) -> bool:
    return task_status(task_text).lower() == "completed"


def task_path(task_dir: Path, task_id_value: str) -> Path:
    if not re.fullmatch(TASK_ID_PATTERN, task_id_value):
        raise ValueError(f"Invalid FilmNet task ID: {task_id_value}")
    return task_dir / f"{task_id_value}.md"


def write_task_file(task_dir: Path, task_text: str) -> Path:
    task_dir.mkdir(parents=True, exist_ok=True)
    tid = task_id(task_text)
    path = task_path(task_dir, tid)
    path.write_text(task_text.rstrip() + "\n", encoding="utf-8")
    return path


def read_task_files(task_dir: Path) -> List[str]:
    if not task_dir.exists():
        return []
    tasks: List[str] = []
    for path in sorted(task_dir.glob("*.md")):
        if re.fullmatch(rf"{TASK_ID_PATTERN}\.md", path.name):
            tasks.append(path.read_text(encoding="utf-8"))
    return tasks


def write_index(index_path: Path, heading: str, tasks: Iterable[str]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {heading}", ""]
    for task in sorted(tasks, key=task_id):
        lines.append(f"- {task_id(task)} — {task_title(task)}")
    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def migrate_legacy_file(legacy_path: Path, task_dir: Path, index_path: Path, heading: str) -> int:
    if not legacy_path.exists():
        task_dir.mkdir(parents=True, exist_ok=True)
        write_index(index_path, heading, read_task_files(task_dir))
        return 0
    tasks = split_legacy_tasks(legacy_path.read_text(encoding="utf-8"))
    task_dir.mkdir(parents=True, exist_ok=True)
    if not tasks:
        return rebuild_index(task_dir, index_path, heading)
    for task in tasks:
        write_task_file(task_dir, task)
    write_index(index_path, heading, tasks)
    return len(tasks)


def rebuild_index(task_dir: Path, index_path: Path, heading: str) -> int:
    tasks = read_task_files(task_dir)
    write_index(index_path, heading, tasks)
    return len(tasks)


def archive_completed(active_dir: Path, history_dir: Path, active_index: Path, history_index: Path) -> Tuple[int, int, int]:
    active_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    archived = 0
    skipped = 0
    for path in sorted(active_dir.glob("*.md")):
        if not re.fullmatch(rf"{TASK_ID_PATTERN}\.md", path.name):
            continue
        task_text = path.read_text(encoding="utf-8")
        if not is_completed(task_text):
            continue
        destination = task_path(history_dir, task_id(task_text))
        if destination.exists():
            skipped += 1
            path.unlink()
            continue
        shutil.move(str(path), str(destination))
        archived += 1
    remaining = rebuild_index(active_dir, active_index, "Active Tasks")
    rebuild_index(history_dir, history_index, "History Tasks")
    return archived, remaining, skipped
