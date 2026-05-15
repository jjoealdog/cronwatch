"""Persistent run history for cron jobs, stored as JSON lines."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

DEFAULT_HISTORY_FILE = "/var/lib/cronwatch/history.jsonl"
MAX_ENTRIES_PER_JOB = 100


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_run(
    history_file: str,
    job_name: str,
    success: bool,
    exit_code: int | None = None,
    duration_seconds: float | None = None,
    note: str = "",
) -> None:
    """Append a single run record to the history file."""
    path = Path(history_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "job": job_name,
        "ts": _now_iso(),
        "success": success,
        "exit_code": exit_code,
        "duration_seconds": duration_seconds,
        "note": note,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def iter_runs(history_file: str, job_name: str | None = None) -> Iterator[dict]:
    """Yield run records from the history file, optionally filtered by job."""
    path = Path(history_file)
    if not path.exists():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if job_name is None or record.get("job") == job_name:
                yield record


def recent_runs(history_file: str, job_name: str, limit: int = 10) -> list[dict]:
    """Return the *limit* most recent run records for a job."""
    all_runs = list(iter_runs(history_file, job_name))
    return all_runs[-limit:]


def failure_streak(history_file: str, job_name: str) -> int:
    """Return how many consecutive failures are at the end of the history."""
    runs = recent_runs(history_file, job_name, limit=MAX_ENTRIES_PER_JOB)
    streak = 0
    for record in reversed(runs):
        if record.get("success"):
            break
        streak += 1
    return streak
