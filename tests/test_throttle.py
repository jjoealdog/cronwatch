"""Tests for cronwatch.throttle."""

import time
import pytest
from unittest.mock import patch

from cronwatch.throttle import AlertThrottle, ThrottleEntry


@pytest.fixture
def throttle() -> AlertThrottle:
    return AlertThrottle(cooldown_seconds=300)


def test_new_throttle_does_not_suppress(throttle):
    assert throttle.is_suppressed("backup") is False


def test_after_record_alert_is_suppressed(throttle):
    throttle.record_alert("backup")
    assert throttle.is_suppressed("backup") is True


def test_different_jobs_are_independent(throttle):
    throttle.record_alert("backup")
    assert throttle.is_suppressed("cleanup") is False


def test_alert_count_increments(throttle):
    assert throttle.alert_count("backup") == 0
    throttle.record_alert("backup")
    throttle.record_alert("backup")
    assert throttle.alert_count("backup") == 2


def test_reset_clears_suppression(throttle):
    throttle.record_alert("backup")
    throttle.reset("backup")
    assert throttle.is_suppressed("backup") is False
    assert throttle.alert_count("backup") == 0


def test_reset_nonexistent_job_is_safe(throttle):
    throttle.reset("nonexistent")  # should not raise


def test_suppression_expires_after_cooldown():
    throttle = AlertThrottle(cooldown_seconds=10)
    fake_now = time.time()
    with patch.object(throttle, "_now", return_value=fake_now):
        throttle.record_alert("backup")
    # simulate time passing beyond cooldown
    with patch.object(throttle, "_now", return_value=fake_now + 11):
        assert throttle.is_suppressed("backup") is False


def test_suppression_still_active_within_cooldown():
    throttle = AlertThrottle(cooldown_seconds=60)
    fake_now = time.time()
    with patch.object(throttle, "_now", return_value=fake_now):
        throttle.record_alert("backup")
    with patch.object(throttle, "_now", return_value=fake_now + 30):
        assert throttle.is_suppressed("backup") is True


def test_last_alerted_at_returns_none_before_alert(throttle):
    assert throttle.last_alerted_at("backup") is None


def test_last_alerted_at_returns_timestamp_after_alert(throttle):
    before = time.time()
    throttle.record_alert("backup")
    after = time.time()
    ts = throttle.last_alerted_at("backup")
    assert ts is not None
    assert before <= ts <= after


def test_throttle_entry_roundtrip():
    entry = ThrottleEntry(job_name="myjob", last_alerted_at=1234567890.0, alert_count=3)
    restored = ThrottleEntry.from_dict(entry.to_dict())
    assert restored.job_name == entry.job_name
    assert restored.last_alerted_at == entry.last_alerted_at
    assert restored.alert_count == entry.alert_count
