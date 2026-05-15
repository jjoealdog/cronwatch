"""Formats and renders metrics summaries for cronwatch."""
from __future__ import annotations

from typing import List

from cronwatch.metrics import MetricsCollector


def _fmt_rate(rate) -> str:
    if rate is None:
        return "n/a"
    return f"{rate * 100:.1f}%"


def _fmt_duration(secs) -> str:
    if secs is None:
        return "n/a"
    return f"{secs:.2f}s"


def metrics_table(collector: MetricsCollector) -> str:
    """Return a plain-text table of all job metrics."""
    rows = collector.all_metrics()
    if not rows:
        return "No metrics recorded yet."

    header = (
        f"{'Job':<30} {'Runs':>6} {'OK':>6} {'Fail':>6} "
        f"{'Rate':>8} {'AvgDur':>10} {'LastDur':>10}"
    )
    sep = "-" * len(header)
    lines = [header, sep]
    for r in rows:
        lines.append(
            f"{r['job_name']:<30} {r['total_runs']:>6} {r['successful_runs']:>6} "
            f"{r['failed_runs']:>6} {_fmt_rate(r['success_rate']):>8} "
            f"{_fmt_duration(r['avg_duration']):>10} "
            f"{_fmt_duration(r['last_duration_seconds']):>10}"
        )
    return "\n".join(lines)


def metrics_for_job(collector: MetricsCollector, job_name: str) -> str:
    """Return a single-job metrics summary string."""
    m = collector.get(job_name)
    if m is None:
        return f"No metrics for job '{job_name}'."
    d = m.to_dict()
    lines = [
        f"Metrics for: {job_name}",
        f"  Total runs    : {d['total_runs']}",
        f"  Successful    : {d['successful_runs']}",
        f"  Failed        : {d['failed_runs']}",
        f"  Success rate  : {_fmt_rate(d['success_rate'])}",
        f"  Avg duration  : {_fmt_duration(d['avg_duration'])}",
        f"  Last duration : {_fmt_duration(d['last_duration_seconds'])}",
    ]
    return "\n".join(lines)
