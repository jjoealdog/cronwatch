"""Tests for cronwatch.budget_integration."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwatch.budget_integration import BudgetedAlerter, build_budget_alert_fn


@pytest.fixture
def calls():
    return []


@pytest.fixture
def alert_fn(calls):
    def _fn(job, reason):
        calls.append((job, reason))
        return True
    return _fn


@pytest.fixture
def alerter(alert_fn, tmp_path):
    return BudgetedAlerter(
        alert_fn=alert_fn,
        state_file=tmp_path / "budget.json",
        window_seconds=60,
        max_alerts=2,
    )


def test_first_alert_delivered(alerter, calls):
    result = alerter.alert("job_a", "failed")
    assert result is True
    assert len(calls) == 1


def test_delivered_count_increments(alerter):
    alerter.alert("job_a", "failed")
    assert alerter.delivered_count == 1


def test_suppressed_when_budget_exhausted(alerter, calls):
    alerter.alert("job_a", "failed")
    alerter.alert("job_a", "failed")
    result = alerter.alert("job_a", "failed")  # 3rd — over budget
    assert result is False
    assert alerter.suppressed_count == 1
    assert len(calls) == 2


def test_remaining_decrements_on_delivery(alerter):
    assert alerter.remaining("job_a") == 2
    alerter.alert("job_a", "failed")
    assert alerter.remaining("job_a") == 1


def test_reset_restores_budget(alerter):
    alerter.alert("job_a", "failed")
    alerter.alert("job_a", "failed")
    alerter.reset("job_a")
    assert alerter.remaining("job_a") == 2


def test_callable_interface(alerter, calls):
    alerter("job_b", "missed")
    assert len(calls) == 1


def test_build_budget_alert_fn_returns_budgeted_alerter(tmp_path):
    fn = lambda j, r: True
    alerter = build_budget_alert_fn(fn, state_file=tmp_path / "b.json")
    assert isinstance(alerter, BudgetedAlerter)


def test_failed_delivery_does_not_consume_budget(tmp_path):
    failing_fn = lambda j, r: False
    alerter = BudgetedAlerter(
        alert_fn=failing_fn,
        state_file=tmp_path / "b.json",
        window_seconds=60,
        max_alerts=2,
    )
    alerter.alert("job_a", "failed")
    alerter.alert("job_a", "failed")
    # budget not consumed because fn returned False
    assert alerter.remaining("job_a") == 2
    assert alerter.delivered_count == 0
