"""Checks job state and triggers alerts when necessary."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.tracker import JobState, JobTracker

logger = logging.getLogger(__name__)

AlertFn = Callable[[AlertConfig, str, str, Optional[str]], bool]


class Checker:
    def __init__(
        self,
        config: CronwatchConfig,
        tracker: JobTracker,
        alert_fn: AlertFn,
    ) -> None:
        self.config = config
        self.tracker = tracker
        self.alert_fn = alert_fn

    def _effective_alert(self, job: JobConfig) -> Optional[AlertConfig]:
        return job.alert or self.config.default_alert

    def _should_alert(self, alert_cfg: AlertConfig, state: JobState) -> bool:
        return state.consecutive_failures >= alert_cfg.failure_threshold

    def check_job(self, job: JobConfig) -> None:
        state = self.tracker.get_state(job.name)
        if state is None:
            logger.debug("No state recorded yet for job '%s'", job.name)
            return

        alert_cfg = self._effective_alert(job)
        if alert_cfg is None:
            return

        if state.last_exit_code != 0 and self._should_alert(alert_cfg, state):
            details = f"exit_code={state.last_exit_code}, failures={state.consecutive_failures}"
            self.alert_fn(alert_cfg, job.name, "job failed", details)
            return

        if job.max_duration and state.last_duration is not None:
            if state.last_duration > job.max_duration:
                details = f"duration={state.last_duration}s, max={job.max_duration}s"
                self.alert_fn(alert_cfg, job.name, "job exceeded max duration", details)

    def check_all(self) -> None:
        for job in self.config.jobs:
            self.check_job(job)
