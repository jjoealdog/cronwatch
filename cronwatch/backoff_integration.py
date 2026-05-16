"""Wraps an alert function with exponential backoff retry logic."""

from __future__ import annotations

from typing import Callable, Optional

from cronwatch.backoff import AlertBackoff


AlertFn = Callable[[str, str], bool]


class BackoffAlerter:
    """Wraps an alert function, suppressing calls that arrive too soon."""

    def __init__(
        self,
        alert_fn: AlertFn,
        base: float = 2.0,
        cap: float = 3600.0,
        jitter: float = 0.1,
    ) -> None:
        self._alert_fn = alert_fn
        self._backoff = AlertBackoff(base=base, cap=cap, jitter=jitter)
        self._suppressed: dict[str, int] = {}
        self._delivered: dict[str, int] = {}

    def alert(self, job_name: str, message: str) -> bool:
        if not self._backoff.is_ready(job_name):
            self._suppressed[job_name] = self._suppressed.get(job_name, 0) + 1
            return False
        success = self._alert_fn(job_name, message)
        self._backoff.record_attempt(job_name)
        if success:
            self._delivered[job_name] = self._delivered.get(job_name, 0) + 1
        return success

    def reset(self, job_name: str) -> None:
        """Call on job recovery to clear backoff state."""
        self._backoff.reset(job_name)
        self._suppressed.pop(job_name, None)

    def suppressed_count(self, job_name: Optional[str] = None) -> int:
        if job_name is not None:
            return self._suppressed.get(job_name, 0)
        return sum(self._suppressed.values())

    def delivered_count(self, job_name: Optional[str] = None) -> int:
        if job_name is not None:
            return self._delivered.get(job_name, 0)
        return sum(self._delivered.values())

    def backoff_state(self) -> dict:
        return self._backoff.state()


def build_backoff_alert_fn(
    alert_fn: AlertFn,
    base: float = 2.0,
    cap: float = 3600.0,
) -> BackoffAlerter:
    """Convenience factory returning a BackoffAlerter around *alert_fn*."""
    return BackoffAlerter(alert_fn, base=base, cap=cap)
