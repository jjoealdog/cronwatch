"""Glue layer: connects LogWatcher events to the Tracker and Checker pipeline."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from cronwatch.watcher import LogWatcher, MarkerEvent
from cronwatch.tracker import JobTracker
from cronwatch.checker import Checker
from cronwatch.config import CronwatchConfig

logger = logging.getLogger(__name__)


class WatcherIntegration:
    """Owns a LogWatcher and routes MarkerEvents through Tracker + Checker."""

    def __init__(
        self,
        config: CronwatchConfig,
        tracker: JobTracker,
        alert_fn: Callable[[str, str], None],
        log_path: str,
        *,
        skip_existing: bool = True,
    ) -> None:
        self.config = config
        self.tracker = tracker
        self.checker = Checker(config, tracker, alert_fn)
        self._watcher = LogWatcher(log_path, self._on_event)
        if skip_existing:
            self._watcher.reset()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_event(self, event: MarkerEvent) -> None:
        job_cfg = self._find_job(event.job_name)
        if job_cfg is None:
            logger.debug("Ignoring marker for unknown job %r", event.job_name)
            return

        if event.success:
            self.tracker.record_success(event.job_name)
            logger.info("Job %r completed successfully (%.2fs)", event.job_name, event.duration_seconds)
        else:
            self.tracker.record_failure(event.job_name)
            logger.warning("Job %r reported failure (%.2fs)", event.job_name, event.duration_seconds)

        self.checker.check_job(job_cfg)

    def _find_job(self, name: str):
        for job in self.config.jobs:
            if job.name == name:
                return job
        return None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def poll(self) -> int:
        """Delegate to the underlying LogWatcher.poll()."""
        return self._watcher.poll()
