#!/usr/bin/env python3
"""Shared helpers for the FilmNet Messenger Telegram workers.

Centralizes env/token resolution, corruption-tolerant JSONL I/O, atomic file
writes, and the Telegram reachability cache so the dispatcher, intake, and
event-assistant behave identically and never crash-loop on a single bad line.
"""

from __future__ import annotations

import fcntl
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path("/Users/farzan/filmnet-hermes")
GLOBAL_ENV = Path("/Users/farzan/.hermes/.env")
# The Hermes gateway ("control") bot lives in the taskmanager profile. The
# messenger workers must NEVER poll/send on it: doing so would trigger a
# Telegram getUpdates 409 against the gateway and leak team traffic onto
# Farzan's private control channel. We read this token only to exclude it and
# to deliver Farzan's notifications on the channel he actually talks to.
CONTROL_PROFILE_ENV = Path("/Users/farzan/.hermes/profiles/taskmanager/.env")
# Optional dedicated messenger profile env. It does not exist today; if it is
# ever created with the messenger bot token, it takes priority over the global
# env without any further code change.
MESSENGER_PROFILE_ENV = Path("/Users/farzan/.hermes/profiles/messenger/.env")

REACHABILITY_PATH = ROOT / "inbox/telegram-reachability.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def load_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _env_token(path: Path) -> Optional[str]:
    token = load_env_file(path).get("TELEGRAM_BOT_TOKEN")
    return token.strip() if token else None


def control_bot_token() -> Optional[str]:
    """Token of the Hermes gateway/control bot (read-only; never used to poll)."""
    return os.environ.get("CONTROL_TELEGRAM_BOT_TOKEN") or _env_token(CONTROL_PROFILE_ENV)


def control_user_id() -> Optional[str]:
    """Numeric Telegram id of the sole authorized control user (Farzan).

    Only this user may steer a send (STOP / SEND NOW / EDIT). Resolved from the
    control profile env, then global env; never inferred from inbound traffic.
    """
    for env_path in (CONTROL_PROFILE_ENV, GLOBAL_ENV):
        env = load_env_file(env_path)
        for key in ("TELEGRAM_HOME_CHANNEL", "TELEGRAM_ALLOWED_USERS"):
            value = str(env.get(key) or "").strip()
            if not value:
                continue
            first = value.split(",")[0].strip()
            if ":" in first:  # e.g. "telegram:88227782"
                first = first.split(":")[-1].strip()
            if first.lstrip("-").isdigit():
                return first
    explicit = os.environ.get("CONTROL_TELEGRAM_USER_ID")
    return explicit.strip() if explicit else None


def messenger_bot_token() -> str:
    """Resolve the team-facing messenger bot token deterministically.

    Priority: explicit MESSENGER_TELEGRAM_BOT_TOKEN env > messenger profile
    .env > global .env. We intentionally do NOT inherit an ambient
    TELEGRAM_BOT_TOKEN (a Hermes gateway process may export the control bot
    token), and we refuse the control bot token outright.
    """
    token = (
        os.environ.get("MESSENGER_TELEGRAM_BOT_TOKEN")
        or _env_token(MESSENGER_PROFILE_ENV)
        or _env_token(GLOBAL_ENV)
    )
    if not token:
        raise RuntimeError(
            "No messenger bot token found. Set MESSENGER_TELEGRAM_BOT_TOKEN, "
            "or add TELEGRAM_BOT_TOKEN to a messenger profile/global .env."
        )
    control = control_bot_token()
    if control and token == control:
        raise RuntimeError(
            "Refusing to use the control-gateway bot token for the messenger "
            "worker: it would cause a Telegram getUpdates 409 against the "
            "Hermes gateway and leak team traffic onto Farzan's control "
            "channel. Configure a distinct messenger bot token."
        )
    return token


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL rows, skipping (and logging) corrupt/partial/non-object lines.

    A single malformed line must never crash a long-running worker, so we log
    to stderr and continue instead of raising.
    """
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"{utc_now()} skip_bad_jsonl {path.name}:{line_no}: {exc}", file=sys.stderr, flush=True)
                continue
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                print(f"{utc_now()} skip_non_object_jsonl {path.name}:{line_no}", file=sys.stderr, flush=True)
    return rows


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """Append one JSON object as a line, serialized against concurrent writers.

    All three workers append to inbox/messenger-events.jsonl; an exclusive
    advisory lock prevents interleaved partial lines that would otherwise
    corrupt the log.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False, sort_keys=False) + "\n"
    with path.open("a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def atomic_write_text(path: Path, text: str) -> None:
    """Write text via a temp file + atomic rename so readers never see a
    half-written file and a crash mid-write cannot truncate the original."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_json_state(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(default)
    return data if isinstance(data, dict) else dict(default)


def save_json_state(path: Path, state: Dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def normalize_recipients(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    recipients = request.get("recipients")
    if isinstance(recipients, list) and recipients:
        return [r for r in recipients if isinstance(r, dict)]
    recipient = request.get("recipient")
    if isinstance(recipient, dict) and recipient:
        return [recipient]
    return []


def usable_telegram_id(recipient: Dict[str, Any]) -> Optional[str]:
    """Return a numeric Telegram chat id usable for a DM, else None.

    The Bot API can only DM a user by numeric chat id; an @username cannot be
    used to initiate or send a DM, so a username-only contact is unusable.
    """
    telegram_id = str(recipient.get("telegram_id") or "").strip()
    if telegram_id and "to be filled" not in telegram_id.lower() and telegram_id.lstrip("-").isdigit():
        return telegram_id
    return None


def recipient_lookup_key(recipient: Dict[str, Any], recipient_index: int) -> str:
    """Stable identity for event indexing (numeric id > username > index)."""
    telegram_id = usable_telegram_id(recipient)
    if telegram_id:
        return telegram_id
    username = str(recipient.get("telegram_username") or "").strip()
    if username and "to be filled" not in username.lower():
        return username
    return f"recipient_index:{recipient_index}"


def load_reachability() -> Dict[str, Any]:
    return load_json_state(REACHABILITY_PATH, {})


def save_reachability(data: Dict[str, Any]) -> None:
    save_json_state(REACHABILITY_PATH, data)


def mark_reachability(data: Dict[str, Any], telegram_id: Optional[str], reachable: bool, reason: Optional[str] = None) -> bool:
    """Update an in-memory reachability map. Returns True if it changed."""
    if not telegram_id:
        return False
    key = str(telegram_id)
    prior = data.get(key) or {}
    if prior.get("reachable") == reachable and prior.get("reason") == reason:
        # Touch timestamp only; treat as unchanged to avoid churny writes.
        return False
    data[key] = {"reachable": bool(reachable), "reason": reason, "updated_at": utc_now()}
    return True
