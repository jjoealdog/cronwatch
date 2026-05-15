"""Periodic digest report generation and delivery."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from cronwatch.config import CronwatchConfig
from cronwatch.reporter import full_report
from cronwatch.tracker import JobTracker

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_digest_subject(cfg: CronwatchConfig, now: Optional[datetime] = None) -> str:
    """Return a subject line for the digest email."""
    now = now or _utcnow()
    ts = now.strftime("%Y-%m-%d %H:%M UTC")
    return f"[cronwatch] digest report — {ts}"


def send_digest(
    cfg: CronwatchConfig,
    tracker: JobTracker,
    alert_fn: Callable[[str, str], None],
    history_dir: str = "history",
    now: Optional[datetime] = None,
) -> bool:
    """Generate a full report and dispatch it via *alert_fn*.

    Returns True when the alert was dispatched, False when there are no jobs
    configured (nothing to report).
    """
    if not cfg.jobs:
        logger.debug("digest: no jobs configured, skipping")
        return False

    now = now or _utcnow()
    subject = build_digest_subject(cfg, now)
    body = full_report(cfg, tracker, history_dir=history_dir)

    logger.info("Sending digest: %s", subject)
    alert_fn(subject, body)
    return True


class DigestScheduler:
    """Calls *send_digest* every *interval_seconds* when *run_once* is invoked."""

    def __init__(
        self,
        cfg: CronwatchConfig,
        tracker: JobTracker,
        alert_fn: Callable[[str, str], None],
        interval_seconds: int = 86400,
        history_dir: str = "history",
    ) -> None:
        self._cfg = cfg
        self._tracker = tracker
        self._alert_fn = alert_fn
        self._interval = interval_seconds
        self._history_dir = history_dir
        self._last_sent: Optional[datetime] = None

    def run_once(self, now: Optional[datetime] = None) -> bool:
        """Send a digest if the interval has elapsed since the last send."""
        now = now or _utcnow()
        if self._last_sent is None:
            elapsed = self._interval  # trigger on first call
        else:
            elapsed = (now - self._last_sent).total_seconds()

        if elapsed >= self._interval:
            sent = send_digest(
                self._cfg, self._tracker, self._alert_fn,
                history_dir=self._history_dir, now=now,
            )
            if sent:
                self._last_sent = now
            return sent
        return False
