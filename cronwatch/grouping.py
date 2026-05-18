"""Alert grouping: batch multiple alerts within a time window into a single notification."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional


def _now() -> float:
    return time.time()


@dataclass
class PendingAlert:
    job_name: str
    reason: str
    queued_at: float = field(default_factory=_now)


class AlertGrouper:
    """Collect alerts and flush them as a single batched call after a window expires."""

    def __init__(
        self,
        alert_fn: Callable[[str, str], None],
        window_seconds: float = 60.0,
        max_size: int = 20,
    ) -> None:
        self._alert_fn = alert_fn
        self._window = window_seconds
        self._max_size = max_size
        self._pending: List[PendingAlert] = []
        self._window_start: Optional[float] = None

    def ingest(self, job_name: str, reason: str) -> None:
        """Add an alert to the current group, flushing first if the window has expired."""
        now = _now()
        if self._window_start is not None and (now - self._window_start) >= self._window:
            self.flush()
        if self._window_start is None:
            self._window_start = now
        self._pending.append(PendingAlert(job_name=job_name, reason=reason, queued_at=now))
        if len(self._pending) >= self._max_size:
            self.flush()

    def flush(self) -> int:
        """Send a single grouped alert for all pending items. Returns the count flushed."""
        if not self._pending:
            return 0
        count = len(self._pending)
        lines = [f"  [{p.job_name}] {p.reason}" for p in self._pending]
        subject = f"cronwatch: {count} alert(s) grouped"
        body = "Grouped alerts:\n" + "\n".join(lines)
        self._alert_fn(subject, body)
        self._pending.clear()
        self._window_start = None
        return count

    def pending_count(self) -> int:
        return len(self._pending)

    def is_window_expired(self) -> bool:
        if self._window_start is None:
            return False
        return (_now() - self._window_start) >= self._window


def build_grouping_alert_fn(
    alert_fn: Callable[[str, str], None],
    window_seconds: float = 60.0,
    max_size: int = 20,
) -> AlertGrouper:
    """Convenience factory returning a configured AlertGrouper."""
    return AlertGrouper(alert_fn, window_seconds=window_seconds, max_size=max_size)
