"""Wraps an alert callable with circuit-breaker protection."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from cronwatch.circuit_breaker import CircuitBreaker


class CircuitBreakerAlerter:
    """Decorates an alert function; skips delivery when circuit is open."""

    def __init__(
        self,
        channel: str,
        alert_fn: Callable[[str, str, dict], bool],
        breaker: CircuitBreaker,
    ) -> None:
        self.channel = channel
        self._fn = alert_fn
        self._breaker = breaker
        self.suppressed_count = 0
        self.delivered_count = 0
        self.failure_count = 0

    def alert(self, job_name: str, reason: str, meta: Optional[dict] = None) -> bool:
        meta = meta or {}
        if self._breaker.is_open(self.channel):
            self.suppressed_count += 1
            return False
        try:
            ok = self._fn(job_name, reason, meta)
        except Exception:
            ok = False
        if ok:
            self._breaker.record_success(self.channel)
            self.delivered_count += 1
        else:
            self._breaker.record_failure(self.channel)
            self.failure_count += 1
        return ok

    def __call__(self, job_name: str, reason: str, meta: Optional[dict] = None) -> bool:
        return self.alert(job_name, reason, meta)

    def state(self) -> str:
        return self._breaker.state(self.channel)

    def reset(self) -> None:
        self._breaker.reset(self.channel)
        self.suppressed_count = 0
        self.delivered_count = 0
        self.failure_count = 0


def build_circuit_breaker_alert_fn(
    channel: str,
    alert_fn: Callable[[str, str, dict], bool],
    state_file: Path,
    failure_threshold: int = 3,
    recovery_timeout: float = 300.0,
) -> CircuitBreakerAlerter:
    """Convenience factory used by CLI / scheduler wiring."""
    breaker = CircuitBreaker(
        state_file=state_file,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
    )
    return CircuitBreakerAlerter(channel=channel, alert_fn=alert_fn, breaker=breaker)
