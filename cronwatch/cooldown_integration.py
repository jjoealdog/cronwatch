"""Integration wrapper: wraps an alert function with cooldown suppression."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from cronwatch.cooldown import AlertCooldown


class CooldownAlerter:
    """Wraps an alert callable and suppresses repeated alerts within a cooldown window."""

    def __init__(
        self,
        alert_fn: Callable[[str, str], bool],
        state_file: Path,
        default_window: int = 300,
    ):
        self._fn = alert_fn
        self._cooldown = AlertCooldown(state_file, default_window=default_window)
        self.suppressed_count = 0
        self.delivered_count = 0

    def alert(self, job_name: str, reason: str, window_seconds: Optional[int] = None) -> bool:
        if self._cooldown.is_cooling(job_name):
            self.suppressed_count += 1
            return False
        result = self._fn(job_name, reason)
        if result:
            self._cooldown.record_alert(job_name, window_seconds=window_seconds)
            self.delivered_count += 1
        return result

    def reset(self, job_name: str) -> None:
        self._cooldown.reset(job_name)

    def remaining(self, job_name: str) -> float:
        return self._cooldown.remaining(job_name)

    def __call__(self, job_name: str, reason: str) -> bool:
        return self.alert(job_name, reason)


def build_cooldown_alert_fn(
    alert_fn: Callable[[str, str], bool],
    state_file: Path,
    default_window: int = 300,
) -> CooldownAlerter:
    """Convenience factory that returns a CooldownAlerter wrapping alert_fn."""
    return CooldownAlerter(alert_fn, state_file, default_window=default_window)
