"""Tests for cronwatch.fingerprint_integration."""

from __future__ import annotations

import pytest

from cronwatch.fingerprint import FingerprintStore
from cronwatch.fingerprint_integration import (
    FingerprintedAlerter,
    build_fingerprint_alert_fn,
)


@pytest.fixture
def store(tmp_path):
    return FingerprintStore(str(tmp_path / "fp.json"), ttl_seconds=60.0)


@pytest.fixture
def calls():
    return []


@pytest.fixture
def alert_fn(calls):
    def _fn(job_name, reason, **kwargs):
        calls.append((job_name, reason))
        return True
    return _fn


def test_first_alert_is_delivered(store, alert_fn, calls):
    alerter = FingerprintedAlerter(alert_fn, store)
    result = alerter.alert("backup", "failed")
    assert result is True
    assert len(calls) == 1
    assert alerter.delivered_count == 1


def test_duplicate_alert_is_suppressed(store, alert_fn, calls):
    alerter = FingerprintedAlerter(alert_fn, store)
    alerter.alert("backup", "failed")
    result = alerter.alert("backup", "failed")
    assert result is False
    assert len(calls) == 1
    assert alerter.suppressed_count == 1


def test_different_jobs_are_independent(store, alert_fn, calls):
    alerter = FingerprintedAlerter(alert_fn, store)
    alerter.alert("job_a", "failed")
    alerter.alert("job_b", "failed")
    assert len(calls) == 2
    assert alerter.suppressed_count == 0


def test_failed_inner_does_not_mark_seen(store, calls):
    def failing_fn(job_name, reason, **kwargs):
        return False

    alerter = FingerprintedAlerter(failing_fn, store)
    alerter.alert("job", "failed")
    alerter.alert("job", "failed")  # should NOT be suppressed
    assert alerter.suppressed_count == 0
    assert alerter.delivered_count == 0


def test_reset_clears_counters(store, alert_fn):
    alerter = FingerprintedAlerter(alert_fn, store)
    alerter.alert("job", "failed")
    alerter.alert("job", "failed")
    alerter.reset()
    assert alerter.suppressed_count == 0
    assert alerter.delivered_count == 0


def test_callable_interface(store, alert_fn, calls):
    alerter = FingerprintedAlerter(alert_fn, store)
    alerter("job", "failed")
    assert len(calls) == 1


def test_build_fingerprint_alert_fn_returns_alerter(tmp_path, alert_fn):
    path = str(tmp_path / "fp.json")
    alerter = build_fingerprint_alert_fn(alert_fn, path, ttl_seconds=60.0)
    assert isinstance(alerter, FingerprintedAlerter)
    result = alerter("job", "failed")
    assert result is True
