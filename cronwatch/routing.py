"""Alert routing — send alerts to different destinations based on job tags or name patterns."""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

log = logging.getLogger(__name__)

AlertFn = Callable[[str, str, str], bool]


@dataclass
class Route:
    """A single routing rule."""
    name: str
    job_patterns: List[str]  # fnmatch patterns matched against job name
    tags: List[str]          # if non-empty, job must have at least one matching tag
    alert_fn: AlertFn

    def matches(self, job_name: str, job_tags: Optional[List[str]] = None) -> bool:
        """Return True if this route applies to the given job."""
        pattern_match = any(
            fnmatch.fnmatch(job_name, p) for p in self.job_patterns
        ) if self.job_patterns else True

        if not pattern_match:
            return False

        if self.tags:
            job_tags_lower = [t.lower() for t in (job_tags or [])]
            tag_match = any(t.lower() in job_tags_lower for t in self.tags)
            return tag_match

        return True


class AlertRouter:
    """Routes alerts to one or more alert functions based on routing rules."""

    def __init__(self, routes: Optional[List[Route]] = None, default_fn: Optional[AlertFn] = None) -> None:
        self._routes: List[Route] = routes or []
        self._default_fn = default_fn
        self.delivered: int = 0
        self.dropped: int = 0

    def add_route(self, route: Route) -> None:
        self._routes.append(route)

    def alert(self, job_name: str, reason: str, message: str, job_tags: Optional[List[str]] = None) -> bool:
        """Dispatch alert through all matching routes; fall back to default if none match."""
        matched = [r for r in self._routes if r.matches(job_name, job_tags)]

        if not matched:
            if self._default_fn is not None:
                log.debug("routing: no route matched %s, using default", job_name)
                result = self._default_fn(job_name, reason, message)
                if result:
                    self.delivered += 1
                else:
                    self.dropped += 1
                return result
            log.debug("routing: no route and no default for %s, dropping alert", job_name)
            self.dropped += 1
            return False

        ok = False
        for route in matched:
            try:
                result = route.alert_fn(job_name, reason, message)
                if result:
                    self.delivered += 1
                    ok = True
                else:
                    self.dropped += 1
            except Exception as exc:  # noqa: BLE001
                log.error("routing: route %s raised %s", route.name, exc)
                self.dropped += 1
        return ok

    def reset_counters(self) -> None:
        self.delivered = 0
        self.dropped = 0
