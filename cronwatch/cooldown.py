"""Alert cooldown: suppress repeated alerts for the same job within a time window."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Optional


def _now() -> float:
    return time.time()


class CooldownEntry:
    def __init__(self, last_alerted: float, window_seconds: int):
        self.last_alerted = last_alerted
        self.window_seconds = window_seconds

    def is_cooling(self, now: Optional[float] = None) -> bool:
        t = now if now is not None else _now()
        return (t - self.last_alerted) < self.window_seconds

    def to_dict(self) -> dict:
        return {"last_alerted": self.last_alerted, "window_seconds": self.window_seconds}

    @classmethod
    def from_dict(cls, d: dict) -> "CooldownEntry":
        return cls(d["last_alerted"], d["window_seconds"])


class AlertCooldown:
    def __init__(self, state_file: Path, default_window: int = 300):
        self._path = Path(state_file)
        self.default_window = default_window
        self._entries: Dict[str, CooldownEntry] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                self._entries = {
                    k: CooldownEntry.from_dict(v) for k, v in data.items()
                }
            except (json.JSONDecodeError, KeyError):
                self._entries = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({k: v.to_dict() for k, v in self._entries.items()}))

    def is_cooling(self, job_name: str, now: Optional[float] = None) -> bool:
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        return entry.is_cooling(now)

    def record_alert(self, job_name: str, window_seconds: Optional[int] = None, now: Optional[float] = None) -> None:
        t = now if now is not None else _now()
        w = window_seconds if window_seconds is not None else self.default_window
        self._entries[job_name] = CooldownEntry(last_alerted=t, window_seconds=w)
        self._save()

    def reset(self, job_name: str) -> None:
        self._entries.pop(job_name, None)
        self._save()

    def remaining(self, job_name: str, now: Optional[float] = None) -> float:
        entry = self._entries.get(job_name)
        if entry is None:
            return 0.0
        t = now if now is not None else _now()
        remaining = entry.window_seconds - (t - entry.last_alerted)
        return max(0.0, remaining)
