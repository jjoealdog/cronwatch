"""Integration helpers: tag-aware scheduler and alert filtering."""

from __future__ import annotations

from typing import Callable

from cronwatch.tags import filter_jobs


class TagFilteredAlerter:
    """Wrap an alert function so it only fires for jobs matching tag rules.

    Parameters
    ----------
    alert_fn:
        Underlying ``(job_name, message)`` callable.
    include:
        Only alert when the job carries at least one of these tags.
    exclude:
        Never alert when the job carries any of these tags.
    jobs:
        Iterable of ``JobConfig`` objects used for tag look-up.
    """

    def __init__(
        self,
        alert_fn: Callable[[str, str], None],
        jobs: list,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> None:
        self._alert_fn = alert_fn
        self._jobs = jobs
        self._include = include or []
        self._exclude = exclude or []
        self.suppressed: int = 0
        self.delivered: int = 0

    def _job_by_name(self, name: str):
        for j in self._jobs:
            if j.name == name:
                return j
        return None

    def __call__(self, job_name: str, message: str) -> None:
        job = self._job_by_name(job_name)
        # If job not found we let the alert through to avoid silent drops.
        if job is not None:
            allowed = filter_jobs([job], include=self._include or None,
                                  exclude=self._exclude or None)
            if not allowed:
                self.suppressed += 1
                return
        self.delivered += 1
        self._alert_fn(job_name, message)


def build_tag_alert_fn(
    alert_fn: Callable[[str, str], None],
    jobs: list,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> TagFilteredAlerter:
    """Convenience factory returning a :class:`TagFilteredAlerter`."""
    return TagFilteredAlerter(alert_fn, jobs, include=include, exclude=exclude)
