"""Helpers to build an AlertRouter from CronwatchConfig."""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from cronwatch.config import CronwatchConfig, JobConfig
from cronwatch.routing import AlertRouter, Route

log = logging.getLogger(__name__)

AlertFn = Callable[[str, str, str], bool]


def _job_tags(config: CronwatchConfig, job_name: str) -> List[str]:
    """Return tags for a job by name, or empty list."""
    for job in config.jobs:
        if job.name == job_name:
            return list(getattr(job, "tags", None) or [])
    return []


def build_router(
    named_alert_fns: Dict[str, AlertFn],
    route_specs: Optional[List[dict]] = None,
    default_fn: Optional[AlertFn] = None,
) -> AlertRouter:
    """Build an AlertRouter from a list of route spec dicts.

    Each spec dict may contain:
      - name (str)
      - job_patterns (list[str])  — fnmatch patterns
      - tags (list[str])
      - alert (str)               — key into named_alert_fns
    """
    router = AlertRouter(default_fn=default_fn)
    for spec in (route_specs or []):
        fn_name = spec.get("alert", "")
        fn = named_alert_fns.get(fn_name)
        if fn is None:
            log.warning("routing: unknown alert function %r in route %r", fn_name, spec.get("name"))
            continue
        route = Route(
            name=spec.get("name", fn_name),
            job_patterns=spec.get("job_patterns") or [],
            tags=spec.get("tags") or [],
            alert_fn=fn,
        )
        router.add_route(route)
    return router


class ConfigAwareRouter:
    """Wraps AlertRouter and automatically resolves job tags from config."""

    def __init__(self, router: AlertRouter, config: CronwatchConfig) -> None:
        self._router = router
        self._config = config

    def alert(self, job_name: str, reason: str, message: str) -> bool:
        tags = _job_tags(self._config, job_name)
        return self._router.alert(job_name, reason, message, job_tags=tags)

    @property
    def delivered(self) -> int:
        return self._router.delivered

    @property
    def dropped(self) -> int:
        return self._router.dropped

    def reset_counters(self) -> None:
        self._router.reset_counters()
