"""Hooks MetricsCollector into WatcherIntegration events."""
from __future__ import annotations

from cronwatch.metrics import MetricsCollector
from cronwatch.watcher import MarkerEvent


class MetricsIntegration:
    """Wraps a MetricsCollector and processes MarkerEvents from the log watcher."""

    def __init__(self, collector: MetricsCollector | None = None) -> None:
        self.collector = collector or MetricsCollector()

    def on_event(self, event: MarkerEvent) -> None:
        """Process a single MarkerEvent, updating metrics accordingly."""
        job_name = event.job_name
        # Use the event timestamp as a proxy — we record start then immediate end
        # because the marker line only tells us about completion.
        # Duration is only available when both start/end markers are logged;
        # here we capture what we can from a single completion event.
        self.collector._get_or_create(job_name)  # ensure entry exists
        m = self.collector._jobs[job_name]
        m.total_runs += 1
        import time as _time
        m.last_run_ts = _time.time()
        if event.status == "success":
            m.successful_runs += 1
        else:
            m.failed_runs += 1
        if event.duration_seconds is not None:
            m.last_duration_seconds = event.duration_seconds
            m.durations.append(event.duration_seconds)
            if len(m.durations) > 100:
                m.durations = m.durations[-100:]

    def summary_table(self) -> str:
        from cronwatch.metrics_reporter import metrics_table
        return metrics_table(self.collector)

    def summary_for_job(self, job_name: str) -> str:
        from cronwatch.metrics_reporter import metrics_for_job
        return metrics_for_job(self.collector, job_name)
