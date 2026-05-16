"""Alert fingerprinting — deduplicate alerts by content hash across restarts."""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional


def _now() -> float:
    return time.time()


def make_fingerprint(job_name: str, reason: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """Return a stable hex fingerprint for a given alert event."""
    payload = {"job": job_name, "reason": reason}
    if extra:
        payload.update(extra)
    serialised = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialised.encode()).hexdigest()


def _load(path: str) -> Dict[str, float]:
    try:
        with open(path) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(path: str, data: Dict[str, float]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh)


class FingerprintStore:
    """Persist seen fingerprints so duplicate alerts are suppressed across restarts."""

    def __init__(self, state_file: str, ttl_seconds: float = 3600.0) -> None:
        self._path = state_file
        self._ttl = ttl_seconds
        self._data: Dict[str, float] = _load(self._path)

    def _prune(self) -> None:
        cutoff = _now() - self._ttl
        self._data = {k: v for k, v in self._data.items() if v > cutoff}

    def is_seen(self, fingerprint: str) -> bool:
        self._prune()
        return fingerprint in self._data

    def mark_seen(self, fingerprint: str) -> None:
        self._prune()
        self._data[fingerprint] = _now()
        _save(self._path, self._data)

    def clear(self) -> None:
        self._data = {}
        _save(self._path, self._data)

    def seen_count(self) -> int:
        self._prune()
        return len(self._data)
