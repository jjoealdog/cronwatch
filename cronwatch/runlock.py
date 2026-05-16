"""Run-lock: prevent duplicate concurrent executions of the same cron job."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional


def _now() -> float:
    return time.time()


def _lock_path(lock_dir: Path, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return lock_dir / f"{safe}.lock"


def acquire(lock_dir: Path, job_name: str, pid: Optional[int] = None) -> bool:
    """Try to acquire a lock for *job_name*.

    Returns True if the lock was acquired, False if it already exists and the
    owning process is still alive.
    """
    lock_dir.mkdir(parents=True, exist_ok=True)
    path = _lock_path(lock_dir, job_name)

    if path.exists():
        try:
            data = json.loads(path.read_text())
            owner_pid = int(data.get("pid", 0))
            # Check if the owning process is still running.
            if owner_pid and _pid_alive(owner_pid):
                return False
            # Stale lock — remove and continue.
            path.unlink(missing_ok=True)
        except (ValueError, KeyError, OSError):
            path.unlink(missing_ok=True)

    pid = pid if pid is not None else os.getpid()
    payload = {"job": job_name, "pid": pid, "acquired_at": _now()}
    path.write_text(json.dumps(payload))
    return True


def release(lock_dir: Path, job_name: str) -> bool:
    """Release the lock for *job_name*.  Returns True if a lock file was removed."""
    path = _lock_path(lock_dir, job_name)
    if path.exists():
        path.unlink(missing_ok=True)
        return True
    return False


def is_locked(lock_dir: Path, job_name: str) -> bool:
    """Return True if a live lock exists for *job_name*."""
    path = _lock_path(lock_dir, job_name)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        owner_pid = int(data.get("pid", 0))
        return owner_pid > 0 and _pid_alive(owner_pid)
    except (ValueError, KeyError, OSError):
        return False


def lock_info(lock_dir: Path, job_name: str) -> Optional[dict]:
    """Return the lock metadata dict, or None if no lock file exists."""
    path = _lock_path(lock_dir, job_name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
