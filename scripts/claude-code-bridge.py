#!/usr/bin/env python3
"""Hermes -> Claude Code bridge.

Runs Claude Code in print mode using the user's Claude Code auth (Claude Team/Max/Pro OAuth),
not Hermes' Anthropic API provider. Records request/response JSONL for auditability.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DIR = ROOT / "inbox" / "claude-code-bridge"
REQUESTS = BRIDGE_DIR / "requests.jsonl"
RESPONSES = BRIDGE_DIR / "responses.jsonl"


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        timeout=timeout,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a task through Claude Code and persist bridge records.")
    parser.add_argument("--task", "-t", required=True, help="Task/prompt to send to Claude Code")
    parser.add_argument("--workdir", "-C", default=str(ROOT), help="Working directory for Claude Code")
    parser.add_argument("--model", default="", help="Claude Code model alias/name, e.g. haiku, sonnet, opus")
    parser.add_argument("--max-turns", type=int, default=10, help="Claude Code print-mode max turns")
    parser.add_argument("--timeout", type=int, default=600, help="Process timeout seconds")
    parser.add_argument("--allowed-tools", default="Read", help="Comma-separated Claude Code allowed tools")
    parser.add_argument("--effort", default="", help="Claude Code effort: low, medium, high, max, auto")
    parser.add_argument("--json", action="store_true", help="Return full Claude Code JSON instead of plain result")
    args = parser.parse_args()

    claude = shutil.which("claude")
    if not claude:
        print("ERROR: Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code", file=sys.stderr)
        return 127

    workdir = Path(args.workdir).expanduser().resolve()
    if not workdir.exists():
        print(f"ERROR: workdir does not exist: {workdir}", file=sys.stderr)
        return 2

    auth = run([claude, "auth", "status", "--text"], cwd=workdir, timeout=30)
    if auth.returncode != 0 or "Not logged in" in (auth.stdout + auth.stderr):
        print("ERROR: Claude Code is installed but not logged in.", file=sys.stderr)
        print("Run once in your terminal: claude auth login", file=sys.stderr)
        return 3

    job_id = f"cc-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    prompt = f"""You are Claude Code running as a delegated worker for Farzan's Hermes agent.\n\nTask ID: {job_id}\n\nTask:\n{args.task}\n\nReturn a concise handoff with: summary, files read/changed, commands run, verification, blockers, next step. Do not send messages to FilmNet team members. Do not commit or push unless explicitly requested."""

    request_record = {
        "id": job_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "workdir": str(workdir),
        "model": args.model or None,
        "max_turns": args.max_turns,
        "allowed_tools": args.allowed_tools,
        "task": args.task,
    }
    append_jsonl(REQUESTS, request_record)

    cmd = [claude, "-p", prompt, "--output-format", "json", "--max-turns", str(args.max_turns)]
    if args.allowed_tools:
        cmd += ["--allowedTools", args.allowed_tools]
    if args.model:
        cmd += ["--model", args.model]
    if args.effort:
        cmd += ["--effort", args.effort]

    started = time.time()
    try:
        proc = run(cmd, cwd=workdir, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        response_record = {
            "id": job_id,
            "status": "timeout",
            "duration_seconds": args.timeout,
            "error": f"Claude Code timed out after {args.timeout}s",
        }
        append_jsonl(RESPONSES, response_record)
        print(response_record["error"], file=sys.stderr)
        return 124

    duration = round(time.time() - started, 2)
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()

    parsed: Any = None
    result_text = stdout
    if stdout:
        try:
            parsed = json.loads(stdout)
            result_text = parsed.get("result") or parsed.get("message") or stdout
        except json.JSONDecodeError:
            parsed = None

    response_record = {
        "id": job_id,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": "success" if proc.returncode == 0 else "error",
        "returncode": proc.returncode,
        "duration_seconds": duration,
        "stdout_json": parsed,
        "stdout_text": stdout if parsed is None else None,
        "stderr": stderr,
    }
    append_jsonl(RESPONSES, response_record)

    if args.json:
        print(json.dumps(response_record, ensure_ascii=False, indent=2))
    else:
        if result_text:
            print(result_text)
        if stderr and proc.returncode != 0:
            print(stderr, file=sys.stderr)

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
