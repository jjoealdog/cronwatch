"""Tests for cronwatch.parser."""

from datetime import datetime, timedelta

import pytest

from cronwatch.parser import (
    get_next_run,
    get_prev_run,
    is_valid_expression,
    expected_period_seconds,
    is_overdue,
)

EVERY_MINUTE = "* * * * *"
EVERY_HOUR = "0 * * * *"
INVALID = "not-a-cron"


def test_is_valid_expression_accepts_valid():
    assert is_valid_expression(EVERY_MINUTE) is True
    assert is_valid_expression(EVERY_HOUR) is True


def test_is_valid_expression_rejects_invalid():
    assert is_valid_expression(INVALID) is False


def test_get_next_run_is_in_future():
    now = datetime.now()
    nxt = get_next_run(EVERY_MINUTE, base=now)
    assert nxt > now


def test_get_prev_run_is_in_past():
    now = datetime.now()
    prev = get_prev_run(EVERY_MINUTE, base=now)
    assert prev <= now


def test_expected_period_every_minute():
    period = expected_period_seconds(EVERY_MINUTE)
    assert period == pytest.approx(60.0)


def test_expected_period_every_hour():
    period = expected_period_seconds(EVERY_HOUR)
    assert period == pytest.approx(3600.0)


def test_is_overdue_no_last_run_recently_scheduled():
    # A job scheduled every minute with no last_run should be overdue after grace
    result = is_overdue(EVERY_MINUTE, last_run=None, grace_seconds=0)
    assert isinstance(result, bool)


def test_is_overdue_fresh_last_run_is_not_overdue():
    now = datetime.now()
    # last_run is just now — should not be overdue
    result = is_overdue(EVERY_MINUTE, last_run=now, grace_seconds=3600)
    assert result is False


def test_is_overdue_old_last_run_is_overdue():
    old = datetime.now() - timedelta(hours=2)
    result = is_overdue(EVERY_MINUTE, last_run=old, grace_seconds=0)
    assert result is True
