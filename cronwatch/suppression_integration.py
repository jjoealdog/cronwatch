"""Integrates SuppressionStore with the alert pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from cronwatch.suppression import SuppressionStore, SuppressionWindow


AlertFn = Callable[[str, str, str], bool]


class SuppressionAlerter:
    """Wraps an alert function, skipping delivery during active suppression windows."""

    def __init__(self, state_file: Path, inner: AlertFn):
        self._store = SuppressionStore(Path(state_file))
        self._inner = inner
        self.suppressed_count = 0
        self.delivered_count = 0

    def suppress(self, job: str, start: datetime, end: datetime, reason: str = "") -> None:
        self._store.add(SuppressionWindow(job, start, end, reason))

    def lift(self, job: str) -> int:
        return self._store.remove(job)

    def is_suppressed(self, job: str, at: Optional[datetime] = None) -> bool:
        return self._store.is_suppressed(job, at)

    def alert(self, job: str, status: str, message: str) -> bool:
        if self._store.is_suppressed(job):
            self.suppressed_count += 1
            return False
        result = self._inner(job, status, message)
        if result:
            self.delivered_count += 1
        return result

    def prune(self) -> int:
        return self._store.prune_expired()

    def reset_counters(self) -> None:
        self.suppressed_count = 0
        self.delivered_count = 0


def build_suppression_alert_fn(
    state_file: Path,
    inner: AlertFn,
) -> SuppressionAlerter:
    """Factory that returns a SuppressionAlerter wrapping *inner*."""
    return SuppressionAlerter(state_file, inner)
