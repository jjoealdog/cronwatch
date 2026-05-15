"""Alert throttling — suppress repeated alerts for the same job within a cooldown window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ThrottleEntry:
    job_name: str
    last_alerted_at: float  # unix timestamp
    alert_count: int = 1

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_alerted_at": self.last_alerted_at,
            "alert_count": self.alert_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ThrottleEntry":
        return cls(
            job_name=d["job_name"],
            last_alerted_at=float(d["last_alerted_at"]),
            alert_count=int(d.get("alert_count", 1)),
        )


class AlertThrottle:
    """Tracks per-job alert cooldowns so we don't spam on repeated failures."""

    def __init__(self, cooldown_seconds: int = 3600) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._entries: Dict[str, ThrottleEntry] = {}

    def _now(self) -> float:
        return time.time()

    def is_suppressed(self, job_name: str) -> bool:
        """Return True if an alert for *job_name* should be suppressed."""
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        elapsed = self._now() - entry.last_alerted_at
        return elapsed < self.cooldown_seconds

    def record_alert(self, job_name: str) -> None:
        """Mark that an alert was just sent for *job_name*."""
        entry = self._entries.get(job_name)
        if entry is None:
            self._entries[job_name] = ThrottleEntry(
                job_name=job_name, last_alerted_at=self._now()
            )
        else:
            entry.last_alerted_at = self._now()
            entry.alert_count += 1

    def reset(self, job_name: str) -> None:
        """Clear throttle state for *job_name* (e.g. after a successful run)."""
        self._entries.pop(job_name, None)

    def alert_count(self, job_name: str) -> int:
        entry = self._entries.get(job_name)
        return entry.alert_count if entry else 0

    def last_alerted_at(self, job_name: str) -> Optional[float]:
        entry = self._entries.get(job_name)
        return entry.last_alerted_at if entry else None
