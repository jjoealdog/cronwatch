"""Integration layer: gate job checks behind dependency satisfaction."""

from __future__ import annotations

from typing import Callable, Optional, Set

from cronwatch.config import CronwatchConfig, JobConfig
from cronwatch.dependency import DependencyGraph, blocking_dependencies, build_graph
from cronwatch.tracker import JobTracker


AlertFn = Callable[[str, str], None]


class DependencyAwareChecker:
    """Wraps an alert function and skips alerting when dependencies are unmet."""

    def __init__(
        self,
        cfg: CronwatchConfig,
        tracker: JobTracker,
        alert_fn: AlertFn,
        *,
        graph: Optional[DependencyGraph] = None,
    ) -> None:
        self._cfg = cfg
        self._tracker = tracker
        self._alert_fn = alert_fn
        self._graph = graph if graph is not None else build_graph(cfg)

    # ------------------------------------------------------------------
    # public helpers
    # ------------------------------------------------------------------

    def successful_jobs(self) -> Set[str]:
        """Return names of jobs whose last recorded run was successful."""
        ok: Set[str] = set()
        for job in self._cfg.jobs:
            state = self._tracker.get(job.name)
            if state and state.last_status == "success":
                ok.add(job.name)
        return ok

    def is_blocked(self, job_name: str) -> bool:
        """Return True when at least one dependency of *job_name* has not succeeded."""
        blocked = blocking_dependencies(
            job_name, self._graph, self.successful_jobs()
        )
        return len(blocked) > 0

    def alert(self, job_name: str, reason: str) -> None:
        """Fire the wrapped alert only if *job_name*'s dependencies are satisfied."""
        if self.is_blocked(job_name):
            return
        self._alert_fn(job_name, reason)


def build_dependency_alert_fn(
    cfg: CronwatchConfig,
    tracker: JobTracker,
    alert_fn: AlertFn,
) -> AlertFn:
    """Convenience factory — returns a plain callable usable as an alert_fn."""
    checker = DependencyAwareChecker(cfg, tracker, alert_fn)
    return checker.alert
