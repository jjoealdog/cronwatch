"""Alert budget — limits total alerts fired per job per time window."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


def _now() -> float:
    return time.time()


@dataclass
class BudgetEntry:
    job: str
    window_seconds: int
    max_alerts: int
    timestamps: List[float] = field(default_factory=list)

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self.timestamps = [t for t in self.timestamps if t >= cutoff]

    def is_exhausted(self) -> bool:
        self._prune(_now())
        return len(self.timestamps) >= self.max_alerts

    def record(self) -> None:
        self._prune(_now())
        self.timestamps.append(_now())

    def remaining(self) -> int:
        self._prune(_now())
        return max(0, self.max_alerts - len(self.timestamps))

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "window_seconds": self.window_seconds,
            "max_alerts": self.max_alerts,
            "timestamps": self.timestamps,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BudgetEntry":
        return cls(
            job=d["job"],
            window_seconds=d["window_seconds"],
            max_alerts=d["max_alerts"],
            timestamps=d.get("timestamps", []),
        )


class AlertBudget:
    def __init__(
        self,
        state_file: Optional[Path] = None,
        window_seconds: int = 3600,
        max_alerts: int = 5,
    ) -> None:
        self._state_file = state_file
        self._window = window_seconds
        self._max = max_alerts
        self._entries: Dict[str, BudgetEntry] = {}
        if state_file and state_file.exists():
            self._load()

    def _entry(self, job: str) -> BudgetEntry:
        if job not in self._entries:
            self._entries[job] = BudgetEntry(job, self._window, self._max)
        return self._entries[job]

    def is_exhausted(self, job: str) -> bool:
        return self._entry(job).is_exhausted()

    def record(self, job: str) -> None:
        self._entry(job).record()
        self._save()

    def remaining(self, job: str) -> int:
        return self._entry(job).remaining()

    def reset(self, job: str) -> None:
        if job in self._entries:
            self._entries[job].timestamps.clear()
        self._save()

    def _load(self) -> None:
        try:
            data = json.loads(self._state_file.read_text())
            for item in data:
                e = BudgetEntry.from_dict(item)
                self._entries[e.job] = e
        except Exception:
            pass

    def _save(self) -> None:
        if self._state_file is None:
            return
        self._state_file.write_text(
            json.dumps([e.to_dict() for e in self._entries.values()], indent=2)
        )
