"""Tests for cronwatch.jitter."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.jitter import JitteredAlerter, jittered_alert


# ---------------------------------------------------------------------------
# jittered_alert
# ---------------------------------------------------------------------------

def test_no_jitter_calls_immediately():
    fn = MagicMock(return_value=True)
    sleep_calls: list[float] = []
    result = jittered_alert(fn, "job1", "boom", 0.0, _sleep_fn=sleep_calls.append)
    fn.assert_called_once_with("job1", "boom")
    assert result is True
    assert sleep_calls == []


def test_negative_jitter_calls_immediately():
    fn = MagicMock(return_value=False)
    sleep_calls: list[float] = []
    jittered_alert(fn, "job1", "msg", -5.0, _sleep_fn=sleep_calls.append)
    fn.assert_called_once()
    assert sleep_calls == []


def test_positive_jitter_sleeps_before_call():
    fn = MagicMock(return_value=True)
    sleep_calls: list[float] = []
    with patch("random.uniform", return_value=2.5):
        jittered_alert(fn, "job2", "msg", 10.0, _sleep_fn=sleep_calls.append)
    assert sleep_calls == [2.5]
    fn.assert_called_once_with("job2", "msg")


def test_jitter_delay_within_range():
    delays: list[float] = []
    fn = MagicMock(return_value=True)
    for _ in range(50):
        jittered_alert(fn, "j", "m", 1.0, _sleep_fn=delays.append)
    assert all(0.0 <= d <= 1.0 for d in delays)


# ---------------------------------------------------------------------------
# JitteredAlerter
# ---------------------------------------------------------------------------

def _instant_sleep(_: float) -> None:
    """Sleep stub that returns immediately."""


def test_alerter_fires_alert_fn():
    fn = MagicMock(return_value=True)
    alerter = JitteredAlerter(fn, max_jitter_seconds=0.0, _sleep_fn=_instant_sleep)
    alerter.alert("job3", "error")
    alerter.wait(timeout=2.0)
    fn.assert_called_once_with("job3", "error")


def test_alerter_multiple_alerts():
    fn = MagicMock(return_value=True)
    alerter = JitteredAlerter(fn, max_jitter_seconds=0.0, _sleep_fn=_instant_sleep)
    for i in range(5):
        alerter.alert(f"job{i}", "msg")
    alerter.wait(timeout=2.0)
    assert fn.call_count == 5


def test_alerter_pending_count_reaches_zero():
    fn = MagicMock(return_value=True)
    alerter = JitteredAlerter(fn, max_jitter_seconds=0.0, _sleep_fn=_instant_sleep)
    alerter.alert("j", "m")
    alerter.wait(timeout=2.0)
    assert alerter.pending_count() == 0


def test_alerter_is_nonblocking():
    barrier = threading.Event()
    released: list[bool] = []

    def slow_alert(job: str, msg: str) -> bool:
        barrier.wait(timeout=2.0)
        released.append(True)
        return True

    alerter = JitteredAlerter(slow_alert, max_jitter_seconds=0.0, _sleep_fn=_instant_sleep)
    alerter.alert("j", "m")  # should return immediately
    assert alerter.pending_count() == 1
    barrier.set()
    alerter.wait(timeout=2.0)
    assert released == [True]
