"""Alert jitter: randomly delay alerts to avoid thundering-herd when many
jobs fail simultaneously.  The jitter window is configurable per-job or
globally via AlertConfig.jitter_seconds (default 0 = disabled)."""

from __future__ import annotations

import random
import threading
import time
from typing import Callable, Optional


def _sleep(seconds: float) -> None:  # pragma: no cover – thin wrapper for tests
    time.sleep(seconds)


def jittered_alert(
    alert_fn: Callable[[str, str], bool],
    job_name: str,
    message: str,
    max_jitter_seconds: float = 0.0,
    *,
    _sleep_fn: Optional[Callable[[float], None]] = None,
) -> bool:
    """Call *alert_fn* after a random delay in [0, max_jitter_seconds].

    Returns the return value of *alert_fn*.  When *max_jitter_seconds* is
    zero or negative the call is immediate (no jitter applied).
    """
    sleep_fn = _sleep_fn if _sleep_fn is not None else _sleep
    if max_jitter_seconds > 0:
        delay = random.uniform(0.0, max_jitter_seconds)
        sleep_fn(delay)
    return alert_fn(job_name, message)


class JitteredAlerter:
    """Wraps an alert callable and applies per-call jitter in a background
    thread so the caller is never blocked."""

    def __init__(
        self,
        alert_fn: Callable[[str, str], bool],
        max_jitter_seconds: float = 0.0,
        *,
        _sleep_fn: Optional[Callable[[float], None]] = None,
    ) -> None:
        self._alert_fn = alert_fn
        self._max_jitter = max_jitter_seconds
        self._sleep_fn = _sleep_fn
        self._lock = threading.Lock()
        self._pending: list[threading.Thread] = []

    def alert(self, job_name: str, message: str) -> None:
        """Fire-and-forget: dispatch alert in a daemon thread with jitter."""
        t = threading.Thread(
            target=self._run,
            args=(job_name, message),
            daemon=True,
        )
        with self._lock:
            self._pending.append(t)
        t.start()

    def _run(self, job_name: str, message: str) -> None:
        try:
            jittered_alert(
                self._alert_fn,
                job_name,
                message,
                self._max_jitter,
                _sleep_fn=self._sleep_fn,
            )
        finally:
            with self._lock:
                self._pending = [p for p in self._pending if p.is_alive()]

    def pending_count(self) -> int:
        """Number of alert threads still in-flight."""
        with self._lock:
            return len(self._pending)

    def wait(self, timeout: float = 5.0) -> None:
        """Block until all in-flight alerts finish (useful in tests)."""
        with self._lock:
            threads = list(self._pending)
        for t in threads:
            t.join(timeout=timeout)
