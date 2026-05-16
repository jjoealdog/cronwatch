"""Alert correlation: group related alerts to reduce noise."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

_WINDOW_SECONDS = 60


def _now() -> float:
    return time.time()


@dataclass
class CorrelationGroup:
    key: str
    job_names: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    first_seen: float = field(default_factory=_now)
    last_seen: float = field(default_factory=_now)
    delivered: bool = False

    def add(self, job_name: str, reason: str) -> None:
        if job_name not in self.job_names:
            self.job_names.append(job_name)
        if reason not in self.reasons:
            self.reasons.append(reason)
        self.last_seen = _now()

    def is_expired(self, window: float = _WINDOW_SECONDS) -> bool:
        return (_now() - self.last_seen) > window

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "job_names": self.job_names,
            "reasons": self.reasons,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "delivered": self.delivered,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CorrelationGroup":
        g = cls(key=d["key"])
        g.job_names = d.get("job_names", [])
        g.reasons = d.get("reasons", [])
        g.first_seen = d.get("first_seen", _now())
        g.last_seen = d.get("last_seen", _now())
        g.delivered = d.get("delivered", False)
        return g


class AlertCorrelator:
    """Buffers alerts within a time window and flushes correlated groups."""

    def __init__(
        self,
        state_file: Optional[Path] = None,
        window: float = _WINDOW_SECONDS,
    ) -> None:
        self._state_file = state_file
        self._window = window
        self._groups: Dict[str, CorrelationGroup] = {}
        if state_file and Path(state_file).exists():
            self._load()

    def ingest(self, job_name: str, reason: str, group_key: str = "default") -> None:
        if group_key not in self._groups:
            self._groups[group_key] = CorrelationGroup(key=group_key)
        self._groups[group_key].add(job_name, reason)
        self._save()

    def flush(self, alert_fn: Callable[[str, str], None]) -> int:
        """Deliver pending undelivered groups; returns count flushed."""
        flushed = 0
        for g in list(self._groups.values()):
            if not g.delivered:
                subject = f"[cronwatch] correlated alert: {len(g.job_names)} job(s)"
                body = "Jobs: {}\nReasons: {}".format(
                    ", ".join(g.job_names), "; ".join(g.reasons)
                )
                alert_fn(subject, body)
                g.delivered = True
                flushed += 1
        self._purge_expired()
        self._save()
        return flushed

    def _purge_expired(self) -> None:
        self._groups = {
            k: v for k, v in self._groups.items() if not v.is_expired(self._window)
        }

    def group_count(self) -> int:
        return len(self._groups)

    def _save(self) -> None:
        if not self._state_file:
            return
        data = {k: v.to_dict() for k, v in self._groups.items()}
        Path(self._state_file).write_text(json.dumps(data))

    def _load(self) -> None:
        try:
            data = json.loads(Path(self._state_file).read_text())
            self._groups = {k: CorrelationGroup.from_dict(v) for k, v in data.items()}
        except Exception:
            self._groups = {}
