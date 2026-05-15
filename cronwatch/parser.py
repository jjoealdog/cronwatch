"""Parse cron expressions and determine next/previous run times."""

from datetime import datetime, timedelta
from typing import Optional

from croniter import croniter


def get_next_run(expression: str, base: Optional[datetime] = None) -> datetime:
    """Return the next scheduled run time for a cron expression."""
    base = base or datetime.now()
    itr = croniter(expression, base)
    return itr.get_next(datetime)


def get_prev_run(expression: str, base: Optional[datetime] = None) -> datetime:
    """Return the most recent scheduled run time for a cron expression."""
    base = base or datetime.now()
    itr = croniter(expression, base)
    return itr.get_prev(datetime)


def is_valid_expression(expression: str) -> bool:
    """Return True if the cron expression is syntactically valid."""
    return croniter.is_valid(expression)


def expected_period_seconds(expression: str) -> float:
    """Estimate the period (in seconds) between consecutive runs."""
    base = datetime(2024, 1, 1, 0, 0, 0)
    itr = croniter(expression, base)
    t1 = itr.get_next(datetime)
    t2 = itr.get_next(datetime)
    return (t2 - t1).total_seconds()


def is_overdue(expression: str, last_run: Optional[datetime], grace_seconds: int = 60) -> bool:
    """Return True if a job is overdue based on its schedule and last run time."""
    if last_run is None:
        prev = get_prev_run(expression)
        return (datetime.now() - prev).total_seconds() > grace_seconds
    prev = get_prev_run(expression)
    return last_run < prev and (datetime.now() - prev).total_seconds() > grace_seconds
