"""Wire SampledAlerter into the broader cronwatch alert pipeline."""

from __future__ import annotations

import random
from typing import Callable, Optional

from cronwatch.config import CronwatchConfig
from cronwatch.sampling import SampledAlerter


def build_sampling_alert_fn(
    cfg: CronwatchConfig,
    downstream: Callable[[str, str, str], bool],
    rng: Optional[random.Random] = None,
) -> Callable[[str, str, str], bool]:
    """Return a SampledAlerter configured from *cfg.alert.sampling_rate*.

    If the config carries no ``sampling_rate`` key the alerter defaults to
    ``rate=1.0`` (pass-through), so existing deployments are unaffected.
    """
    rate: float = 1.0
    if cfg.alert and hasattr(cfg.alert, "extra"):
        rate = float(cfg.alert.extra.get("sampling_rate", 1.0))
    return SampledAlerter(downstream, rate=rate, rng=rng)


class SamplingMiddleware:
    """Middleware layer that adds sampling to any alert pipeline.

    Intended to be composed with other alerters::

        base = log_alert
        sampled = SamplingMiddleware(base, rate=0.25)
        scheduler = Scheduler(cfg, tracker, sampled)
    """

    def __init__(
        self,
        downstream: Callable[[str, str, str], bool],
        rate: float = 1.0,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._alerter = SampledAlerter(downstream, rate=rate, rng=rng)

    def __call__(self, job_name: str, reason: str, detail: str) -> bool:
        return self._alerter.alert(job_name, reason, detail)

    @property
    def stats(self) -> dict:
        """Aggregate stats across all observed jobs."""
        total_delivered = sum(
            s.delivered for s in self._alerter._stats.values()
        )
        total_dropped = sum(
            s.dropped for s in self._alerter._stats.values()
        )
        total = total_delivered + total_dropped
        return {
            "delivered": total_delivered,
            "dropped": total_dropped,
            "total": total,
            "effective_rate": round(total_delivered / total, 4) if total else 0.0,
        }
