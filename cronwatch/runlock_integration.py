"""Integration layer: wrap an alert function with run-lock awareness."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from cronwatch import runlock

AlertFn = Callable[[str, str], None]


class RunLockIntegration:
    """Guards job execution and fires an alert if a duplicate run is detected."""

    def __init__(
        self,
        lock_dir: Path,
        alert_fn: AlertFn,
        *,
        alert_on_duplicate: bool = True,
    ) -> None:
        self._lock_dir = lock_dir
        self._alert_fn = alert_fn
        self._alert_on_duplicate = alert_on_duplicate
        self.duplicate_count: int = 0

    def try_acquire(self, job_name: str, pid: Optional[int] = None) -> bool:
        """Attempt to acquire the lock.  Fires an alert and returns False on
        collision."""
        acquired = runlock.acquire(self._lock_dir, job_name, pid=pid)
        if not acquired:
            self.duplicate_count += 1
            if self._alert_on_duplicate:
                info = runlock.lock_info(self._lock_dir, job_name)
                owner = info.get("pid", "unknown") if info else "unknown"
                self._alert_fn(
                    job_name,
                    f"Duplicate run detected for '{job_name}' — already running (pid {owner}).",
                )
        return acquired

    def release(self, job_name: str) -> bool:
        return runlock.release(self._lock_dir, job_name)

    def is_locked(self, job_name: str) -> bool:
        return runlock.is_locked(self._lock_dir, job_name)

    def reset_counters(self) -> None:
        self.duplicate_count = 0


def build_runlock_alert_fn(
    lock_dir: Path,
    alert_fn: AlertFn,
    *,
    alert_on_duplicate: bool = True,
) -> RunLockIntegration:
    """Convenience factory — returns a RunLockIntegration instance."""
    return RunLockIntegration(
        lock_dir,
        alert_fn,
        alert_on_duplicate=alert_on_duplicate,
    )
