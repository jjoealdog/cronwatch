"""Tests for cronwatch.circuit_breaker_integration."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwatch.circuit_breaker import CircuitBreaker
from cronwatch.circuit_breaker_integration import (
    CircuitBreakerAlerter,
    build_circuit_breaker_alert_fn,
)


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "cb.json"


@pytest.fixture
def breaker(state_file):
    return CircuitBreaker(state_file=state_file, failure_threshold=2, recovery_timeout=60.0)


@pytest.fixture
def alert_fn():
    return MagicMock(return_value=True)


def test_successful_delivery_increments_delivered(breaker, alert_fn):
    alerter = CircuitBreakerAlerter("email", alert_fn, breaker)
    result = alerter.alert("job1", "failed")
    assert result is True
    assert alerter.delivered_count == 1
    assert alerter.failure_count == 0


def test_failed_delivery_increments_failure_and_records(breaker, alert_fn):
    alert_fn.return_value = False
    alerter = CircuitBreakerAlerter("email", alert_fn, breaker)
    alerter.alert("job1", "failed")
    assert alerter.failure_count == 1
    assert breaker._entry("email").failure_count == 1


def test_open_circuit_suppresses_alert(breaker, alert_fn):
    alerter = CircuitBreakerAlerter("email", alert_fn, breaker)
    # open the circuit
    breaker.record_failure("email")
    breaker.record_failure("email")
    result = alerter.alert("job1", "failed")
    assert result is False
    assert alerter.suppressed_count == 1
    alert_fn.assert_not_called()


def test_exception_in_alert_fn_counts_as_failure(breaker):
    def boom(job, reason, meta):
        raise RuntimeError("network down")

    alerter = CircuitBreakerAlerter("email", boom, breaker)
    result = alerter.alert("job1", "failed")
    assert result is False
    assert alerter.failure_count == 1


def test_reset_clears_all_counters(breaker, alert_fn):
    alert_fn.return_value = False
    alerter = CircuitBreakerAlerter("email", alert_fn, breaker)
    alerter.alert("job1", "failed")
    alerter.reset()
    assert alerter.failure_count == 0
    assert alerter.suppressed_count == 0
    assert alerter.delivered_count == 0


def test_callable_interface(breaker, alert_fn):
    alerter = CircuitBreakerAlerter("email", alert_fn, breaker)
    assert alerter("job1", "missed") is True


def test_build_factory_returns_alerter(tmp_path, alert_fn):
    alerter = build_circuit_breaker_alert_fn(
        channel="slack",
        alert_fn=alert_fn,
        state_file=tmp_path / "cb.json",
        failure_threshold=3,
        recovery_timeout=120.0,
    )
    assert isinstance(alerter, CircuitBreakerAlerter)
    assert alerter.channel == "slack"
