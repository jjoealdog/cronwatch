"""Tests for cronwatch.suppression and cronwatch.suppression_integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.suppression import SuppressionStore, SuppressionWindow
from cronwatch.suppression_integration import SuppressionAlerter


def _utc(**kwargs) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**kwargs)


@pytest.fixture()
def store(tmp_path: Path) -> SuppressionStore:
    return SuppressionStore(tmp_path / "suppression.json")


@pytest.fixture()
def alerter(tmp_path: Path):
    calls: list = []

    def _fn(job, status, msg):
        calls.append((job, status, msg))
        return True

    a = SuppressionAlerter(tmp_path / "suppression.json", _fn)
    return a, calls


def test_window_active_within_range():
    w = SuppressionWindow("job1", _utc(seconds=-10), _utc(seconds=10))
    assert w.is_active()


def test_window_not_active_before_start():
    w = SuppressionWindow("job1", _utc(seconds=5), _utc(seconds=20))
    assert not w.is_active()


def test_window_not_active_after_end():
    w = SuppressionWindow("job1", _utc(seconds=-20), _utc(seconds=-5))
    assert not w.is_active()


def test_store_is_suppressed_when_active(store: SuppressionStore):
    store.add(SuppressionWindow("backup", _utc(seconds=-5), _utc(seconds=60)))
    assert store.is_suppressed("backup")


def test_store_not_suppressed_outside_window(store: SuppressionStore):
    store.add(SuppressionWindow("backup", _utc(seconds=-60), _utc(seconds=-1)))
    assert not store.is_suppressed("backup")


def test_store_remove_clears_job(store: SuppressionStore):
    store.add(SuppressionWindow("backup", _utc(seconds=-5), _utc(seconds=60)))
    removed = store.remove("backup")
    assert removed == 1
    assert not store.is_suppressed("backup")


def test_store_persists_across_reload(tmp_path: Path):
    path = tmp_path / "s.json"
    s1 = SuppressionStore(path)
    s1.add(SuppressionWindow("job", _utc(seconds=-5), _utc(seconds=60)))
    s2 = SuppressionStore(path)
    assert s2.is_suppressed("job")


def test_prune_removes_expired(store: SuppressionStore):
    store.add(SuppressionWindow("old", _utc(seconds=-60), _utc(seconds=-1)))
    store.add(SuppressionWindow("live", _utc(seconds=-5), _utc(seconds=60)))
    pruned = store.prune_expired()
    assert pruned == 1
    assert store.is_suppressed("live")


def test_alerter_suppresses_during_window(alerter):
    a, calls = alerter
    a.suppress("nightly", _utc(seconds=-10), _utc(seconds=60))
    result = a.alert("nightly", "failure", "exit 1")
    assert result is False
    assert a.suppressed_count == 1
    assert calls == []


def test_alerter_delivers_outside_window(alerter):
    a, calls = alerter
    a.suppress("nightly", _utc(seconds=-60), _utc(seconds=-1))
    result = a.alert("nightly", "failure", "exit 1")
    assert result is True
    assert a.delivered_count == 1
    assert len(calls) == 1


def test_alerter_reset_counters(alerter):
    a, _ = alerter
    a.suppress("j", _utc(seconds=-5), _utc(seconds=60))
    a.alert("j", "failure", "msg")
    a.reset_counters()
    assert a.suppressed_count == 0
    assert a.delivered_count == 0
