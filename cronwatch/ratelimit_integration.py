"""Integrates RateLimiter with the alert pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from cronwatch.ratelimit import RateLimiter


class RateLimitedAlerter:
    """Wraps an alert function with rate limiting per job."""

    def __init__(
        self,
        alert_fn: Callable[[str, str], None],
        state_path: Optional[Path] = None,
        window_seconds: int = 3600,
        max_alerts: int = 5,
    ) -> None:
        self._alert_fn = alert_fn
        self._limiter = RateLimiter(
            state_path=state_path,
            default_window=window_seconds,
            default_max=max_alerts,
        )
        self._suppressed: dict[str, int] = {}

    def alert(self, job_name: str, message: str) -> bool:
        """Send alert if not rate limited. Returns True if alert was sent."""
        if self._limiter.check_and_record(job_name):
            self._alert_fn(job_name, message)
            return True
        self._suppressed[job_name] = self._suppressed.get(job_name, 0) + 1
        return False

    def suppressed_count(self, job_name: str) -> int:
        """Return how many alerts were suppressed for a given job."""
        return self._suppressed.get(job_name, 0)

    def reset(self, job_name: str) -> None:
        """Reset rate limit and suppression counter for a job."""
        self._limiter.reset(job_name)
        self._suppressed.pop(job_name, None)

    def summary(self) -> dict:
        """Return a summary of suppressed alert counts."""
        return dict(self._suppressed)
