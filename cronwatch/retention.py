"""Retention policy: prune old history entries beyond a configured age or count."""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from cronwatch.history import iter_runs, append_run


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def prune_by_age(history_dir: str, job_name: str, max_age_days: int) -> int:
    """Remove runs older than *max_age_days*. Returns number of entries removed."""
    cutoff = _utcnow() - timedelta(days=max_age_days)
    kept = []
    removed = 0

    for run in iter_runs(history_dir, job_name):
        try:
            ts = datetime.fromisoformat(run["timestamp"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            kept.append(run)
            continue

        if ts >= cutoff:
            kept.append(run)
        else:
            removed += 1

    _rewrite(history_dir, job_name, kept)
    return removed


def prune_by_count(history_dir: str, job_name: str, max_count: int) -> int:
    """Keep only the *max_count* most-recent runs. Returns number removed."""
    all_runs = list(iter_runs(history_dir, job_name))
    if len(all_runs) <= max_count:
        return 0

    kept = all_runs[-max_count:]
    removed = len(all_runs) - len(kept)
    _rewrite(history_dir, job_name, kept)
    return removed


def prune_job(history_dir: str, job_name: str,
             max_age_days: Optional[int] = None,
             max_count: Optional[int] = None) -> dict:
    """Apply both pruning strategies (age first, then count). Returns summary dict."""
    by_age = 0
    by_count = 0

    if max_age_days is not None:
        by_age = prune_by_age(history_dir, job_name, max_age_days)
    if max_count is not None:
        by_count = prune_by_count(history_dir, job_name, max_count)

    return {"job": job_name, "removed_by_age": by_age, "removed_by_count": by_count}


def _rewrite(history_dir: str, job_name: str, runs: list) -> None:
    """Overwrite the history file with *runs* (in order)."""
    import json
    path = Path(history_dir) / f"{job_name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for run in runs:
            fh.write(json.dumps(run) + "\n")
