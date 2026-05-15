"""Audit log — records configuration changes and significant daemon events."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

_DEFAULT_PATH = Path("cronwatch_audit.log")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_event(
    event_type: str,
    detail: str,
    path: Path | None = None,
    actor: str | None = None,
) -> None:
    """Append a single audit event as a JSON line."""
    target = path or _DEFAULT_PATH
    entry = {
        "ts": _now_iso(),
        "event": event_type,
        "detail": detail,
    }
    if actor:
        entry["actor"] = actor
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def iter_events(path: Path | None = None) -> Iterator[dict]:
    """Yield parsed audit events from *path* (oldest first)."""
    target = path or _DEFAULT_PATH
    if not target.exists():
        return
    with target.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def recent_events(n: int = 50, path: Path | None = None) -> list[dict]:
    """Return the *n* most recent audit events."""
    return list(iter_events(path))[-n:]


def prune_audit_log(max_lines: int = 10_000, path: Path | None = None) -> int:
    """Keep only the last *max_lines* lines. Returns number of lines removed."""
    target = path or _DEFAULT_PATH
    if not target.exists():
        return 0
    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) <= max_lines:
        return 0
    removed = len(lines) - max_lines
    target.write_text("".join(lines[-max_lines:]), encoding="utf-8")
    return removed
