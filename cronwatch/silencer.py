"""Silence/mute alerts for specific jobs during maintenance windows."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SilenceEntry:
    job_name: str
    until: datetime
    reason: str = ""

    def is_active(self) -> bool:
        return _now() < self.until

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "until": self.until.isoformat(),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SilenceEntry":
        return cls(
            job_name=data["job_name"],
            until=datetime.fromisoformat(data["until"]),
            reason=data.get("reason", ""),
        )


class Silencer:
    """Persists and checks per-job silence windows."""

    def __init__(self, state_path: str | Path = "/tmp/cronwatch_silences.json"):
        self._path = Path(state_path)
        self._entries: Dict[str, SilenceEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
            for item in raw:
                entry = SilenceEntry.from_dict(item)
                self._entries[entry.job_name] = entry
        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self) -> None:
        self._path.write_text(
            json.dumps([e.to_dict() for e in self._entries.values()], indent=2)
        )

    def silence(self, job_name: str, until: datetime, reason: str = "") -> None:
        """Silence alerts for *job_name* until *until*."""
        self._entries[job_name] = SilenceEntry(job_name=job_name, until=until, reason=reason)
        self._save()

    def unsilence(self, job_name: str) -> bool:
        """Remove silence for *job_name*. Returns True if an entry existed."""
        existed = job_name in self._entries
        self._entries.pop(job_name, None)
        if existed:
            self._save()
        return existed

    def is_silenced(self, job_name: str) -> bool:
        entry = self._entries.get(job_name)
        return entry is not None and entry.is_active()

    def active_silences(self) -> list[SilenceEntry]:
        return [e for e in self._entries.values() if e.is_active()]

    def purge_expired(self) -> int:
        """Remove expired entries and return how many were removed."""
        expired = [name for name, e in self._entries.items() if not e.is_active()]
        for name in expired:
            del self._entries[name]
        if expired:
            self._save()
        return len(expired)
