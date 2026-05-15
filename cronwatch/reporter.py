"""Generate human-readable status reports for monitored cron jobs."""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from typing import Iterable

from cronwatch.history import recent_runs, failure_streak
from cronwatch.tracker import JobTracker
from cronwatch.config import JobConfig


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def job_summary(job: JobConfig, tracker: JobTracker, history_dir: str, limit: int = 5) -> str:
    """Return a short text summary for a single job."""
    state = tracker.get(job.name)
    runs = recent_runs(history_dir, job.name, n=limit)
    streak = failure_streak(history_dir, job.name)

    lines = [
        f"Job : {job.name}",
        f"Schedule : {job.schedule}",
    ]

    if state:
        last = state.last_run or "never"
        lines.append(f"Last run : {last}")
        lines.append(f"Failures : {state.consecutive_failures}")
    else:
        lines.append("Last run : never")
        lines.append("Failures : 0")

    lines.append(f"Failure streak (history): {streak}")
    lines.append(f"Recent runs ({len(runs)}):")
    for r in runs:
        status = "OK" if r.get("success") else "FAIL"
        lines.append(f"  [{status}] {r.get('timestamp', '?')}")

    return "\n".join(lines)


def full_report(jobs: Iterable[JobConfig], tracker: JobTracker, history_dir: str) -> str:
    """Return a full report covering all jobs."""
    now = _utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    sections = [f"=== cronwatch report — {now} ==="]
    for job in jobs:
        sections.append("")
        sections.append(job_summary(job, tracker, history_dir))
        sections.append("-" * 40)
    return "\n".join(sections)
