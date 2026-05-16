"""Exponential backoff for alert retries."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

_DEFAULT_BASE = 2.0
_DEFAULT_CAP = 3600  # 1 hour max
_DEFAULT_JITTER = 0.1


@dataclass
class BackoffEntry:
    attempt: int = 0
    next_allowed: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"attempt": self.attempt, "next_allowed": self.next_allowed}

    @classmethod
    def from_dict(cls, d: dict) -> "BackoffEntry":
        return cls(attempt=d.get("attempt", 0), next_allowed=d.get("next_allowed", 0.0))


class AlertBackoff:
    """Tracks per-job exponential backoff state for alert retries."""

    def __init__(
        self,
        base: float = _DEFAULT_BASE,
        cap: float = _DEFAULT_CAP,
        jitter: float = _DEFAULT_JITTER,
    ) -> None:
        self._base = base
        self._cap = cap
        self._jitter = jitter
        self._entries: Dict[str, BackoffEntry] = {}

    def _entry(self, job_name: str) -> BackoffEntry:
        if job_name not in self._entries:
            self._entries[job_name] = BackoffEntry()
        return self._entries[job_name]

    def is_ready(self, job_name: str) -> bool:
        """Return True if enough time has passed to retry alerting."""
        return time.time() >= self._entry(job_name).next_allowed

    def record_attempt(self, job_name: str) -> None:
        """Record an alert attempt and schedule the next allowed time."""
        entry = self._entry(job_name)
        entry.attempt += 1
        delay = min(self._base ** entry.attempt, self._cap)
        import random
        jitter_amount = delay * self._jitter * (2 * random.random() - 1)
        entry.next_allowed = time.time() + delay + jitter_amount

    def reset(self, job_name: str) -> None:
        """Reset backoff state after a successful alert or job recovery."""
        self._entries.pop(job_name, None)

    def attempt_count(self, job_name: str) -> int:
        return self._entry(job_name).attempt

    def next_allowed_at(self, job_name: str) -> Optional[float]:
        entry = self._entries.get(job_name)
        return entry.next_allowed if entry else None

    def state(self) -> dict:
        return {k: v.to_dict() for k, v in self._entries.items()}
