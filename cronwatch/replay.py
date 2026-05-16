"""Replay missed alerts by re-checking job history for a given time window."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, List, Optional

from cronwatch.history import iter_runs
from cronwatch.config import JobConfig, CronwatchConfig


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def find_missed_runs(
    job: JobConfig,
    since: datetime,
    until: Optional[datetime] = None,
    history_dir: str = "/var/lib/cronwatch/history",
) -> List[dict]:
    """Return run records for *job* that ended in failure within [since, until]."""
    if until is None:
        until = _utcnow()

    missed = []
    for run in iter_runs(job.name, history_dir=history_dir):
        ts_raw = run.get("timestamp")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(ts_raw)
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if since <= ts <= until and run.get("status") == "failure":
            missed.append(run)
    return missed


def replay_alerts(
    config: CronwatchConfig,
    alert_fn: Callable[[str, str], None],
    since: datetime,
    until: Optional[datetime] = None,
    history_dir: str = "/var/lib/cronwatch/history",
    dry_run: bool = False,
) -> int:
    """Re-fire alerts for every failed run found in [since, until].

    Returns the number of alerts replayed.
    """
    replayed = 0
    for job in config.jobs:
        missed = find_missed_runs(job, since, until=until, history_dir=history_dir)
        for run in missed:
            ts = run.get("timestamp", "unknown")
            reason = run.get("reason") or "non-zero exit"
            message = (
                f"[REPLAY] Job '{job.name}' failed at {ts}. "
                f"Reason: {reason}. "
                f"Exit code: {run.get('exit_code', '?')}"
            )
            if not dry_run:
                alert_fn(job.name, message)
            replayed += 1
    return replayed
