"""Checker — evaluates job states and fires alerts when needed."""

import logging
import time
from typing import Callable, List

from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.tracker import JobState, JobTracker

logger = logging.getLogger(__name__)

AlertFn = Callable[[JobConfig, JobState, str], None]

MIN_ALERT_INTERVAL = 3600  # don't re-alert for the same job within 1 hour


class Checker:
    """Inspects tracked job states and triggers alert callbacks."""

    def __init__(
        self,
        config: CronwatchConfig,
        tracker: JobTracker,
        alert_fn: AlertFn,
    ):
        self.config = config
        self.tracker = tracker
        self.alert_fn = alert_fn

    def _effective_alert(self, job: JobConfig) -> AlertConfig:
        """Return the job-level alert config, falling back to the global default."""
        if job.alert is not None:
            return job.alert
        if self.config.default_alert is not None:
            return self.config.default_alert
        return AlertConfig()

    def _should_alert(self, state: JobState) -> bool:
        if state.last_alert_at is None:
            return True
        return (time.time() - state.last_alert_at) >= MIN_ALERT_INTERVAL

    def check_job(self, job: JobConfig) -> None:
        state = self.tracker.get(job.name)
        alert_cfg = self._effective_alert(job)

        # Check for consecutive failures
        if (
            alert_cfg.on_failure
            and state.last_exit_code is not None
            and state.last_exit_code != 0
            and state.consecutive_failures >= job.alert_after_failures
            and self._should_alert(state)
        ):
            logger.info("Job '%s' has %d consecutive failure(s).", job.name, state.consecutive_failures)
            self.alert_fn(job, state, "failure")
            self.tracker.mark_alerted(job.name)
            return

        # Check for missed run
        if alert_cfg.on_missed and self.tracker.is_overdue(job) and self._should_alert(state):
            logger.info("Job '%s' appears to have missed its scheduled run.", job.name)
            self.alert_fn(job, state, "missed")
            self.tracker.mark_alerted(job.name)

    def run_checks(self) -> None:
        for job in self.config.jobs:
            try:
                self.check_job(job)
            except Exception:  # noqa: BLE001
                logger.exception("Unexpected error while checking job '%s'.", job.name)
