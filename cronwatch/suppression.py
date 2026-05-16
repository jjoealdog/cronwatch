"""Time-window based alert suppression (maintenance windows)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SuppressionWindow:
    """A named time window during which alerts for a job are suppressed."""

    def __init__(self, job: str, start: datetime, end: datetime, reason: str = ""):
        self.job = job
        self.start = start
        self.end = end
        self.reason = reason

    def is_active(self, at: Optional[datetime] = None) -> bool:
        t = at or _now()
        return self.start <= t <= self.end

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SuppressionWindow":
        return cls(
            job=d["job"],
            start=datetime.fromisoformat(d["start"]),
            end=datetime.fromisoformat(d["end"]),
            reason=d.get("reason", ""),
        )


class SuppressionStore:
    """Persists and queries suppression windows."""

    def __init__(self, state_file: Path):
        self._path = Path(state_file)
        self._windows: List[SuppressionWindow] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self._windows = [SuppressionWindow.from_dict(d) for d in data]
        except (json.JSONDecodeError, KeyError):
            self._windows = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([w.to_dict() for w in self._windows], indent=2))

    def add(self, window: SuppressionWindow) -> None:
        self._windows.append(window)
        self._save()

    def remove(self, job: str) -> int:
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.job != job]
        self._save()
        return before - len(self._windows)

    def is_suppressed(self, job: str, at: Optional[datetime] = None) -> bool:
        return any(w.job == job and w.is_active(at) for w in self._windows)

    def active_windows(self, at: Optional[datetime] = None) -> List[SuppressionWindow]:
        return [w for w in self._windows if w.is_active(at)]

    def prune_expired(self, at: Optional[datetime] = None) -> int:
        t = at or _now()
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.end >= t]
        self._save()
        return before - len(self._windows)
