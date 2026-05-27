#!/usr/bin/env python3
"""Utilities for FilmNet task JSONL state files."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _atomic_write_text(path: Path, text: str) -> None:
    """Write via temp file + atomic rename so a crash mid-write cannot truncate
    or corrupt the existing file and readers never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

TASK_ID_PATTERN = r"FN-\d{4}-\d{4}-\d{3}"
TASK_HEADING_RE = re.compile(rf"^##\s+({TASK_ID_PATTERN})\s*$", re.MULTILINE)
TASK_SPLIT_RE = re.compile(rf"(?=^##\s+{TASK_ID_PATTERN}\s*$)", re.MULTILINE)
TITLE_RE = re.compile(r"^- Title:\s*(.+?)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^- Status:\s*(.+?)\s*$", re.MULTILINE)
READ_FILE_PREFIX_RE = re.compile(r"^\s*\d+\|\s?")

TaskRecord = Dict[str, str]


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


def task_jsonl_path(task_dir: Path) -> Path:
    """Return the JSONL file that replaces a legacy per-task Markdown directory."""
    return task_dir.with_suffix(".jsonl")


def task_to_record(task_text: str) -> TaskRecord:
    markdown = task_text.rstrip() + "\n"
    return {
        "task_id": task_id(markdown),
        "title": task_title(markdown),
        "status": task_status(markdown),
        "markdown": markdown,
    }


def record_to_task(record: TaskRecord) -> str:
    markdown = str(record.get("markdown") or "").rstrip() + "\n"
    if markdown.strip():
        return markdown
    tid = str(record.get("task_id") or "").strip()
    title = str(record.get("title") or "[title missing]").strip()
    status = str(record.get("status") or "").strip()
    return f"## {tid}\n- Title: {title}\n- Status: {status}\n"


def read_task_records(task_dir: Path) -> List[TaskRecord]:
    """Read task records from JSONL, with legacy .md fallback during migration."""
    jsonl_path = task_jsonl_path(task_dir)
    records: List[TaskRecord] = []
    seen: set[str] = set()
    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in {jsonl_path}:{line_no}: {exc}") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"Invalid task row in {jsonl_path}:{line_no}: expected object")
                markdown = record_to_task(row)
                record = task_to_record(markdown)
                records.append(record)
                seen.add(record["task_id"])
    if task_dir.exists():
        for path in sorted(task_dir.glob("*.md")):
            if not re.fullmatch(rf"{TASK_ID_PATTERN}\.md", path.name):
                continue
            markdown = path.read_text(encoding="utf-8")
            record = task_to_record(markdown)
            if record["task_id"] not in seen:
                records.append(record)
                seen.add(record["task_id"])
    return sorted(records, key=lambda r: r["task_id"])


def write_task_records(task_dir: Path, records: Iterable[TaskRecord]) -> Path:
    jsonl_path = task_jsonl_path(task_dir)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    by_id: Dict[str, TaskRecord] = {}
    for record in records:
        normalized = task_to_record(record_to_task(record))
        by_id[normalized["task_id"]] = normalized
    lines = [json.dumps(by_id[tid], ensure_ascii=False, separators=(",", ":")) for tid in sorted(by_id)]
    _atomic_write_text(jsonl_path, ("\n".join(lines) + "\n") if lines else "")
    return jsonl_path


def write_task_file(task_dir: Path, task_text: str) -> Path:
    """Upsert one task record into the JSONL store.

    The name is kept for backward compatibility with older scripts; it no
    longer creates `state/*/<Task ID>.md` files.
    """
    record = task_to_record(task_text)
    records = [r for r in read_task_records(task_dir) if r["task_id"] != record["task_id"]]
    records.append(record)
    return write_task_records(task_dir, records)


def read_task_files(task_dir: Path) -> List[str]:
    """Return task Markdown bodies from the JSONL store."""
    return [record_to_task(record) for record in read_task_records(task_dir)]


def read_task(task_dir: Path, task_id_value: str) -> str:
    if not re.fullmatch(TASK_ID_PATTERN, task_id_value):
        raise ValueError(f"Invalid FilmNet task ID: {task_id_value}")
    for record in read_task_records(task_dir):
        if record["task_id"] == task_id_value:
            return record_to_task(record)
    raise FileNotFoundError(f"Task not found in {task_jsonl_path(task_dir)}: {task_id_value}")


def write_index(index_path: Path, heading: str, tasks: Iterable[str]) -> None:
    lines = [f"# {heading}", ""]
    for task in sorted(tasks, key=task_id):
        lines.append(f"- {task_id(task)} — {task_title(task)}")
    _atomic_write_text(index_path, "\n".join(lines).rstrip() + "\n")


def migrate_legacy_file(legacy_path: Path, task_dir: Path, index_path: Path, heading: str) -> int:
    tasks = read_task_files(task_dir)
    if legacy_path.exists():
        tasks.extend(split_legacy_tasks(legacy_path.read_text(encoding="utf-8")))
    if tasks:
        write_task_records(task_dir, [task_to_record(task) for task in tasks])
    write_index(index_path, heading, read_task_files(task_dir))
    return len(read_task_files(task_dir))


def remove_legacy_task_files(task_dir: Path) -> int:
    """Delete legacy per-task Markdown files after a verified JSONL migration."""
    removed = 0
    if not task_dir.exists():
        return removed
    for path in sorted(task_dir.glob("*.md")):
        if re.fullmatch(rf"{TASK_ID_PATTERN}\.md", path.name):
            path.unlink()
            removed += 1
    try:
        task_dir.rmdir()
    except OSError:
        pass
    return removed


def rebuild_index(task_dir: Path, index_path: Path, heading: str) -> int:
    tasks = read_task_files(task_dir)
    write_index(index_path, heading, tasks)
    return len(tasks)


def archive_completed(active_dir: Path, history_dir: Path, active_index: Path, history_index: Path) -> Tuple[int, int, int]:
    active_records = read_task_records(active_dir)
    history_records = read_task_records(history_dir)
    history_by_id = {record["task_id"]: record for record in history_records}
    remaining_records: List[TaskRecord] = []
    archived = 0
    skipped = 0
    for record in active_records:
        task_text = record_to_task(record)
        if not is_completed(task_text):
            remaining_records.append(record)
            continue
        if record["task_id"] in history_by_id:
            skipped += 1
            continue
        history_by_id[record["task_id"]] = record
        archived += 1
    write_task_records(active_dir, remaining_records)
    write_task_records(history_dir, history_by_id.values())
    remaining = rebuild_index(active_dir, active_index, "Active Tasks")
    rebuild_index(history_dir, history_index, "History Tasks")
    return archived, remaining, skipped
