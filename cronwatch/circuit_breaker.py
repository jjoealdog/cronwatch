"""Circuit breaker for alert delivery — stops hammering failing notifiers."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_OPEN = "open"
_CLOSED = "closed"
_HALF_OPEN = "half_open"


@dataclass
class BreakerEntry:
    state: str = _CLOSED
    failure_count: int = 0
    last_failure_ts: float = 0.0
    opened_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_ts": self.last_failure_ts,
            "opened_at": self.opened_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BreakerEntry":
        return cls(
            state=d.get("state", _CLOSED),
            failure_count=d.get("failure_count", 0),
            last_failure_ts=d.get("last_failure_ts", 0.0),
            opened_at=d.get("opened_at", 0.0),
        )


def _now() -> float:
    return time.time()


class CircuitBreaker:
    """Per-channel circuit breaker persisted to a JSON file."""

    def __init__(
        self,
        state_file: Path,
        failure_threshold: int = 3,
        recovery_timeout: float = 300.0,
    ) -> None:
        self._path = Path(state_file)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._entries: dict[str, BreakerEntry] = {}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                self._entries = {
                    k: BreakerEntry.from_dict(v) for k, v in data.items()
                }
            except Exception:
                self._entries = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({k: v.to_dict() for k, v in self._entries.items()}, indent=2)
        )

    def _entry(self, channel: str) -> BreakerEntry:
        if channel not in self._entries:
            self._entries[channel] = BreakerEntry()
        return self._entries[channel]

    # ------------------------------------------------------------------
    def is_open(self, channel: str) -> bool:
        """Return True when the circuit is open (calls should be blocked)."""
        e = self._entry(channel)
        if e.state == _OPEN:
            if _now() - e.opened_at >= self.recovery_timeout:
                e.state = _HALF_OPEN
                self._save()
                return False
            return True
        return False

    def record_success(self, channel: str) -> None:
        e = self._entry(channel)
        e.state = _CLOSED
        e.failure_count = 0
        self._save()

    def record_failure(self, channel: str) -> None:
        e = self._entry(channel)
        e.failure_count += 1
        e.last_failure_ts = _now()
        if e.failure_count >= self.failure_threshold:
            e.state = _OPEN
            e.opened_at = _now()
        self._save()

    def state(self, channel: str) -> str:
        self.is_open(channel)  # trigger half-open transition if needed
        return self._entry(channel).state

    def reset(self, channel: str) -> None:
        self._entries.pop(channel, None)
        self._save()
