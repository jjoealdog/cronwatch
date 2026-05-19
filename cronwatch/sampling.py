"""Alert sampling — only forward a fraction of alerts to reduce noise."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class SamplingStats:
    delivered: int = 0
    dropped: int = 0

    @property
    def total(self) -> int:
        return self.delivered + self.dropped

    @property
    def effective_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.delivered / self.total

    def to_dict(self) -> dict:
        return {
            "delivered": self.delivered,
            "dropped": self.dropped,
            "total": self.total,
            "effective_rate": round(self.effective_rate, 4),
        }


class SampledAlerter:
    """Wraps an alert function and only calls it *rate* fraction of the time.

    Args:
        alert_fn: The downstream alert callable.
        rate: Probability [0.0, 1.0] that any given alert is forwarded.
        rng: Optional random.Random instance for deterministic testing.
    """

    def __init__(
        self,
        alert_fn: Callable[[str, str, str], bool],
        rate: float = 1.0,
        rng: Optional[random.Random] = None,
    ) -> None:
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"rate must be in [0.0, 1.0], got {rate}")
        self._fn = alert_fn
        self._rate = rate
        self._rng = rng or random.Random()
        self._stats: dict[str, SamplingStats] = {}

    def alert(self, job_name: str, reason: str, detail: str) -> bool:
        stats = self._stats.setdefault(job_name, SamplingStats())
        if self._rng.random() <= self._rate:
            result = self._fn(job_name, reason, detail)
            stats.delivered += 1
            return result
        stats.dropped += 1
        return False

    def __call__(self, job_name: str, reason: str, detail: str) -> bool:
        return self.alert(job_name, reason, detail)

    def stats_for(self, job_name: str) -> SamplingStats:
        return self._stats.get(job_name, SamplingStats())

    def reset_stats(self, job_name: Optional[str] = None) -> None:
        if job_name is None:
            self._stats.clear()
        else:
            self._stats.pop(job_name, None)


def build_sampled_alert_fn(
    alert_fn: Callable[[str, str, str], bool],
    rate: float,
    rng: Optional[random.Random] = None,
) -> SampledAlerter:
    """Convenience factory used by CLI / scheduler wiring."""
    return SampledAlerter(alert_fn, rate=rate, rng=rng)
