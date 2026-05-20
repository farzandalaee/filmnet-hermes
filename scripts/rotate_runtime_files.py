#!/usr/bin/env python3
"""Rotate FilmNet Hermes runtime logs and JSONL queues.

This keeps active runtime files small while preserving an auditable archive.
It intentionally does not rotate state cursor JSON files such as
inbox/messenger-telegram-intake-state.json.

Default behavior is conservative:
- log files rotate when older than --log-keep-days or larger than --log-max-mb
- JSONL queue/event files rotate only old lines when file is larger than
  --jsonl-max-mb, or when --force is used
- recent lines stay in the active file so dispatch/reply matching continues

Usage:
  python3 scripts/rotate_runtime_files.py --dry-run
  python3 scripts/rotate_runtime_files.py
  python3 scripts/rotate_runtime_files.py --force --jsonl-keep-days 30
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path("/Users/farzan/filmnet-hermes")
ARCHIVE_ROOT = ROOT / "archive/runtime"

LOG_GLOBS = [
    "logs/*.log",
]

JSONL_FILES = [
    ROOT / "inbox/messenger-events.jsonl",
    ROOT / "inbox/messenger-send-requests.jsonl",
    ROOT / "inbox/claude-code-bridge/requests.jsonl",
    ROOT / "inbox/claude-code-bridge/responses.jsonl",
]

# Cursor/state files are deliberately excluded:
# - inbox/messenger-assistant-state.json
# - inbox/messenger-telegram-dispatcher-state.json
# - inbox/messenger-telegram-intake-state.json

TIMESTAMP_KEYS = [
    "created_at",
    "sent_at",
    "received_at",
    "processed_at",
    "updated_at",
    "timestamp",
]


@dataclass
class Action:
    action: str
    path: Path
    detail: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def object_timestamp(obj: Dict[str, Any]) -> Optional[datetime]:
    for key in TIMESTAMP_KEYS:
        dt = parse_iso(obj.get(key))
        if dt:
            return dt
    return None


def line_timestamp(line: str, fallback: datetime) -> datetime:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return fallback
    if isinstance(obj, dict):
        return object_timestamp(obj) or fallback
    return fallback


def archive_path(kind: str, source: Path, now: datetime, suffix: str = ".gz") -> Path:
    month_dir = ARCHIVE_ROOT / kind / f"{now.year:04d}" / f"{now.month:02d}"
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    return month_dir / f"{source.name}.{stamp}{suffix}"


def write_gzip_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        for line in lines:
            f.write(line)
            if not line.endswith("\n"):
                f.write("\n")
    tmp.replace(path)


def atomic_write_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line)
            if not line.endswith("\n"):
                f.write("\n")
    tmp.replace(path)


def rotate_log(path: Path, now: datetime, log_keep_days: int, log_max_bytes: int, dry_run: bool) -> List[Action]:
    actions: List[Action] = []
    if not path.exists() or not path.is_file():
        return actions
    stat = path.stat()
    if stat.st_size == 0:
        return actions
    age = now - datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    should_rotate = age >= timedelta(days=log_keep_days) or stat.st_size >= log_max_bytes
    if not should_rotate:
        return actions
    dest = archive_path("logs", path, now)
    detail = f"rotate log size={stat.st_size} age_days={age.days} -> {dest.relative_to(ROOT)}"
    actions.append(Action("rotate_log", path, detail))
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        with path.open("rb") as src, gzip.open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst)
        tmp.replace(dest)
        path.write_text("", encoding="utf-8")
    return actions


def rotate_jsonl(path: Path, now: datetime, jsonl_keep_days: int, jsonl_max_bytes: int, force: bool, dry_run: bool) -> List[Action]:
    actions: List[Action] = []
    if not path.exists() or not path.is_file():
        return actions
    stat = path.stat()
    if stat.st_size == 0:
        return actions
    if not force and stat.st_size < jsonl_max_bytes:
        return actions

    fallback_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    cutoff = now - timedelta(days=jsonl_keep_days)
    raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    archive_lines: List[str] = []
    keep_lines: List[str] = []
    for line in raw_lines:
        if not line.strip():
            continue
        if line_timestamp(line, fallback_dt) < cutoff:
            archive_lines.append(line)
        else:
            keep_lines.append(line)

    if not archive_lines:
        actions.append(Action("skip_jsonl", path, f"no lines older than {cutoff.isoformat()}"))
        return actions

    dest = archive_path("jsonl", path, now)
    detail = (
        f"archive {len(archive_lines)} old lines, keep {len(keep_lines)} recent lines "
        f"cutoff={cutoff.date()} -> {dest.relative_to(ROOT)}"
    )
    actions.append(Action("rotate_jsonl", path, detail))
    if not dry_run:
        write_gzip_lines(dest, archive_lines)
        atomic_write_lines(path, keep_lines)
    return actions


def delete_old_archives(now: datetime, archive_keep_days: int, dry_run: bool) -> List[Action]:
    actions: List[Action] = []
    if not ARCHIVE_ROOT.exists():
        return actions
    cutoff = now - timedelta(days=archive_keep_days)
    for path in ARCHIVE_ROOT.rglob("*"):
        if not path.is_file():
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if mtime >= cutoff:
            continue
        actions.append(Action("delete_archive", path, f"older than {archive_keep_days} days"))
        if not dry_run:
            path.unlink()
    return actions


def collect_logs() -> List[Path]:
    paths: List[Path] = []
    for pattern in LOG_GLOBS:
        paths.extend(ROOT.glob(pattern))
    return sorted(set(paths))


def main() -> int:
    parser = argparse.ArgumentParser(description="Rotate FilmNet Hermes runtime logs and JSONL queues.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files.")
    parser.add_argument("--force", action="store_true", help="Evaluate JSONL rotation even below size threshold.")
    parser.add_argument("--log-keep-days", type=int, default=7)
    parser.add_argument("--log-max-mb", type=float, default=5.0)
    parser.add_argument("--jsonl-keep-days", type=int, default=30)
    parser.add_argument("--jsonl-max-mb", type=float, default=10.0)
    parser.add_argument("--archive-keep-days", type=int, default=365)
    args = parser.parse_args()

    now = utc_now()
    log_max_bytes = int(args.log_max_mb * 1024 * 1024)
    jsonl_max_bytes = int(args.jsonl_max_mb * 1024 * 1024)

    actions: List[Action] = []
    for path in collect_logs():
        actions.extend(rotate_log(path, now, args.log_keep_days, log_max_bytes, args.dry_run))
    for path in JSONL_FILES:
        actions.extend(rotate_jsonl(path, now, args.jsonl_keep_days, jsonl_max_bytes, args.force, args.dry_run))
    actions.extend(delete_old_archives(now, args.archive_keep_days, args.dry_run))

    if not actions:
        print("No rotation needed.")
        return 0

    prefix = "DRY-RUN " if args.dry_run else ""
    for item in actions:
        print(f"{prefix}{item.action}: {item.path.relative_to(ROOT)} | {item.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
