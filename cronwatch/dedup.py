"""Alert deduplication — suppress repeated identical alerts within a time window."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


def _now() -> float:
    return time.time()


@dataclass
class DedupEntry:
    key: str
    first_seen: float
    last_seen: float
    count: int = 1

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "count": self.count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DedupEntry":
        return cls(
            key=d["key"],
            first_seen=d["first_seen"],
            last_seen=d["last_seen"],
            count=d.get("count", 1),
        )


def _make_key(job_name: str, reason: str) -> str:
    raw = f"{job_name}:{reason}"
    return hashlib.sha1(raw.encode()).hexdigest()


class AlertDedup:
    """Suppress duplicate alerts for the same job+reason within a window."""

    def __init__(self, state_file: str, window_seconds: int = 300) -> None:
        self._path = state_file
        self._window = window_seconds
        self._entries: Dict[str, DedupEntry] = {}
        self._load()

    # ------------------------------------------------------------------
    def is_duplicate(self, job_name: str, reason: str) -> bool:
        """Return True if an identical alert was already sent within the window."""
        key = _make_key(job_name, reason)
        entry = self._entries.get(key)
        if entry is None:
            return False
        return (_now() - entry.last_seen) < self._window

    def record(self, job_name: str, reason: str) -> None:
        """Record that an alert was sent; updates count and last_seen."""
        key = _make_key(job_name, reason)
        now = _now()
        if key in self._entries:
            self._entries[key].last_seen = now
            self._entries[key].count += 1
        else:
            self._entries[key] = DedupEntry(key=key, first_seen=now, last_seen=now)
        self._save()

    def evict_expired(self) -> None:
        """Remove entries older than the dedup window."""
        cutoff = _now() - self._window
        self._entries = {
            k: v for k, v in self._entries.items() if v.last_seen >= cutoff
        }
        self._save()

    def count(self, job_name: str, reason: str) -> int:
        key = _make_key(job_name, reason)
        entry = self._entries.get(key)
        return entry.count if entry else 0

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path) as fh:
                data = json.load(fh)
            self._entries = {k: DedupEntry.from_dict(v) for k, v in data.items()}
        except (json.JSONDecodeError, KeyError):
            self._entries = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w") as fh:
            json.dump({k: v.to_dict() for k, v in self._entries.items()}, fh)
