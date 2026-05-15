"""Rate limiting for alert notifications to prevent alert storms."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class RateLimitEntry:
    job_name: str
    window_seconds: int
    max_alerts: int
    timestamps: list = field(default_factory=list)

    def record(self) -> None:
        """Record a new alert timestamp and prune old ones."""
        now = time.time()
        self.timestamps.append(now)
        self._prune(now)

    def is_limited(self) -> bool:
        """Return True if the rate limit has been exceeded."""
        self._prune(time.time())
        return len(self.timestamps) >= self.max_alerts

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self.timestamps = [t for t in self.timestamps if t >= cutoff]

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "window_seconds": self.window_seconds,
            "max_alerts": self.max_alerts,
            "timestamps": self.timestamps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RateLimitEntry":
        return cls(
            job_name=data["job_name"],
            window_seconds=data["window_seconds"],
            max_alerts=data["max_alerts"],
            timestamps=data.get("timestamps", []),
        )


class RateLimiter:
    def __init__(
        self,
        state_path: Optional[Path] = None,
        default_window: int = 3600,
        default_max: int = 5,
    ) -> None:
        self._path = state_path
        self._default_window = default_window
        self._default_max = default_max
        self._entries: Dict[str, RateLimitEntry] = {}
        if self._path and self._path.exists():
            self._load()

    def check_and_record(self, job_name: str) -> bool:
        """Return True if alert should be sent (not rate limited), and record it."""
        entry = self._get_or_create(job_name)
        if entry.is_limited():
            return False
        entry.record()
        self._save()
        return True

    def reset(self, job_name: str) -> None:
        if job_name in self._entries:
            self._entries[job_name].timestamps = []
            self._save()

    def _get_or_create(self, job_name: str) -> RateLimitEntry:
        if job_name not in self._entries:
            self._entries[job_name] = RateLimitEntry(
                job_name=job_name,
                window_seconds=self._default_window,
                max_alerts=self._default_max,
            )
        return self._entries[job_name]

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
            for item in data:
                e = RateLimitEntry.from_dict(item)
                self._entries[e.job_name] = e
        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self) -> None:
        if self._path:
            self._path.write_text(
                json.dumps([e.to_dict() for e in self._entries.values()], indent=2)
            )
