"""Tests for cronwatch.backoff and cronwatch.backoff_integration."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.backoff import AlertBackoff
from cronwatch.backoff_integration import BackoffAlerter, build_backoff_alert_fn


@pytest.fixture()
def backoff() -> AlertBackoff:
    return AlertBackoff(base=2.0, cap=3600.0, jitter=0.0)


def test_new_backoff_is_ready(backoff: AlertBackoff) -> None:
    assert backoff.is_ready("job_a") is True


def test_after_attempt_not_immediately_ready(backoff: AlertBackoff) -> None:
    backoff.record_attempt("job_a")
    # attempt=1 → delay = 2^1 = 2 s; should not be ready right away
    assert backoff.is_ready("job_a") is False


def test_attempt_count_increments(backoff: AlertBackoff) -> None:
    assert backoff.attempt_count("job_a") == 0
    backoff.record_attempt("job_a")
    assert backoff.attempt_count("job_a") == 1
    backoff.record_attempt("job_a")
    assert backoff.attempt_count("job_a") == 2


def test_reset_clears_state(backoff: AlertBackoff) -> None:
    backoff.record_attempt("job_a")
    backoff.reset("job_a")
    assert backoff.attempt_count("job_a") == 0
    assert backoff.is_ready("job_a") is True


def test_different_jobs_are_independent(backoff: AlertBackoff) -> None:
    backoff.record_attempt("job_a")
    assert backoff.is_ready("job_b") is True


def test_delay_is_capped(backoff: AlertBackoff) -> None:
    b = AlertBackoff(base=2.0, cap=5.0, jitter=0.0)
    for _ in range(20):
        b.record_attempt("job_x")
    now = time.time()
    next_at = b.next_allowed_at("job_x")
    assert next_at is not None
    assert next_at - now <= 6.0  # cap=5 + tiny tolerance


# --- BackoffAlerter integration tests ---

@pytest.fixture()
def alert_fn():
    return MagicMock(return_value=True)


def test_alerter_delivers_first_call(alert_fn) -> None:
    alerter = BackoffAlerter(alert_fn, base=2.0, cap=3600.0, jitter=0.0)
    result = alerter.alert("job_a", "boom")
    assert result is True
    alert_fn.assert_called_once_with("job_a", "boom")


def test_alerter_suppresses_immediate_retry(alert_fn) -> None:
    alerter = BackoffAlerter(alert_fn, base=2.0, cap=3600.0, jitter=0.0)
    alerter.alert("job_a", "first")
    result = alerter.alert("job_a", "second")
    assert result is False
    assert alerter.suppressed_count("job_a") == 1


def test_alerter_reset_allows_immediate_alert(alert_fn) -> None:
    alerter = BackoffAlerter(alert_fn, base=2.0, cap=3600.0, jitter=0.0)
    alerter.alert("job_a", "first")
    alerter.reset("job_a")
    result = alerter.alert("job_a", "second")
    assert result is True
    assert alert_fn.call_count == 2


def test_delivered_count_tracks_successes(alert_fn) -> None:
    alerter = BackoffAlerter(alert_fn, base=2.0, cap=3600.0, jitter=0.0)
    alerter.alert("job_a", "msg")
    assert alerter.delivered_count("job_a") == 1


def test_build_backoff_alert_fn_returns_alerter(alert_fn) -> None:
    alerter = build_backoff_alert_fn(alert_fn, base=4.0, cap=60.0)
    assert isinstance(alerter, BackoffAlerter)
