"""Wraps an alert function with an AlertBudget gate."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from cronwatch.budget import AlertBudget


class BudgetedAlerter:
    """Calls the underlying alert_fn only while the job's budget is not exhausted."""

    def __init__(
        self,
        alert_fn: Callable[[str, str], bool],
        state_file: Optional[Path] = None,
        window_seconds: int = 3600,
        max_alerts: int = 5,
    ) -> None:
        self._fn = alert_fn
        self._budget = AlertBudget(
            state_file=state_file,
            window_seconds=window_seconds,
            max_alerts=max_alerts,
        )
        self._suppressed: int = 0
        self._delivered: int = 0

    def alert(self, job: str, reason: str) -> bool:
        if self._budget.is_exhausted(job):
            self._suppressed += 1
            return False
        result = self._fn(job, reason)
        if result:
            self._budget.record(job)
            self._delivered += 1
        return result

    def __call__(self, job: str, reason: str) -> bool:
        return self.alert(job, reason)

    @property
    def suppressed_count(self) -> int:
        return self._suppressed

    @property
    def delivered_count(self) -> int:
        return self._delivered

    def remaining(self, job: str) -> int:
        return self._budget.remaining(job)

    def reset(self, job: str) -> None:
        self._budget.reset(job)


def build_budget_alert_fn(
    alert_fn: Callable[[str, str], bool],
    state_file: Optional[Path] = None,
    window_seconds: int = 3600,
    max_alerts: int = 5,
) -> BudgetedAlerter:
    return BudgetedAlerter(
        alert_fn=alert_fn,
        state_file=state_file,
        window_seconds=window_seconds,
        max_alerts=max_alerts,
    )
