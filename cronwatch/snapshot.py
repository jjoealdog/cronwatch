"""Point-in-time snapshot of all job states for reporting and diagnostics."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from cronwatch.tracker import JobTracker


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobSnapshot:
    name: str
    last_run: str | None
    last_status: str | None
    failure_count: int
    captured_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "JobSnapshot":
        return cls(
            name=d["name"],
            last_run=d.get("last_run"),
            last_status=d.get("last_status"),
            failure_count=d.get("failure_count", 0),
            captured_at=d["captured_at"],
        )


def capture(tracker: JobTracker) -> list[JobSnapshot]:
    """Return a snapshot of every tracked job right now."""
    now = _utcnow()
    snapshots: list[JobSnapshot] = []
    for name, state in tracker.all_states().items():
        snapshots.append(
            JobSnapshot(
                name=name,
                last_run=state.last_run,
                last_status=state.last_status,
                failure_count=state.failure_count,
                captured_at=now,
            )
        )
    return snapshots


def save_snapshot(snapshots: list[JobSnapshot], path: str) -> None:
    """Persist snapshots to a JSON file (atomic write via temp file)."""
    tmp = path + ".tmp"
    data = [s.to_dict() for s in snapshots]
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def load_snapshot(path: str) -> list[JobSnapshot]:
    """Load snapshots from a previously saved JSON file."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return [JobSnapshot.from_dict(d) for d in data]
