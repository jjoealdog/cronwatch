"""Periodic scheduler that drives the cronwatch check loop."""

import logging
import time
from datetime import datetime
from typing import Callable

from cronwatch.checker import Checker
from cronwatch.config import CronwatchConfig
from cronwatch.tracker import JobTracker

logger = logging.getLogger(__name__)


class Scheduler:
    """Runs the checker on a fixed tick interval and logs activity."""

    def __init__(
        self,
        config: CronwatchConfig,
        tracker: JobTracker,
        alert_fn: Callable,
        tick_seconds: int = 60,
    ) -> None:
        self.config = config
        self.tracker = tracker
        self.alert_fn = alert_fn
        self.tick_seconds = tick_seconds
        self._running = False

    def run_once(self) -> None:
        """Run a single check cycle across all configured jobs."""
        checker = Checker(self.config, self.tracker, self.alert_fn)
        for job in self.config.jobs:
            logger.debug("Checking job: %s", job.name)
            checker.check_job(job.name)

    def start(self) -> None:
        """Start the blocking scheduler loop."""
        self._running = True
        logger.info("Scheduler started (tick=%ds)", self.tick_seconds)
        while self._running:
            self.run_once()
            time.sleep(self.tick_seconds)

    def stop(self) -> None:
        """Signal the scheduler loop to stop after the current tick."""
        self._running = False
        logger.info("Scheduler stopped")
