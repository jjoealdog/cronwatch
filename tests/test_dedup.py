"""Tests for cronwatch.dedup."""

import os
import time
import pytest

from cronwatch.dedup import AlertDedup, _make_key


@pytest.fixture
def dedup(tmp_path):
    return AlertDedup(str(tmp_path / "dedup.json"), window_seconds=60)


# ---------------------------------------------------------------------------
# _make_key
# ---------------------------------------------------------------------------

def test_make_key_is_deterministic():
    assert _make_key("backup", "missed") == _make_key("backup", "missed")


def test_make_key_differs_by_job():
    assert _make_key("jobA", "missed") != _make_key("jobB", "missed")


def test_make_key_differs_by_reason():
    assert _make_key("backup", "missed") != _make_key("backup", "failed")


# ---------------------------------------------------------------------------
# is_duplicate / record
# ---------------------------------------------------------------------------

def test_new_dedup_not_duplicate(dedup):
    assert dedup.is_duplicate("backup", "missed") is False


def test_after_record_is_duplicate(dedup):
    dedup.record("backup", "missed")
    assert dedup.is_duplicate("backup", "missed") is True


def test_different_reason_not_duplicate(dedup):
    dedup.record("backup", "missed")
    assert dedup.is_duplicate("backup", "failed") is False


def test_different_job_not_duplicate(dedup):
    dedup.record("backup", "missed")
    assert dedup.is_duplicate("sync", "missed") is False


def test_count_increments_on_repeat(dedup):
    dedup.record("backup", "missed")
    dedup.record("backup", "missed")
    assert dedup.count("backup", "missed") == 2


def test_count_zero_for_unknown(dedup):
    assert dedup.count("nope", "nope") == 0


# ---------------------------------------------------------------------------
# expiry / eviction
# ---------------------------------------------------------------------------

def test_expired_entry_not_duplicate(tmp_path):
    d = AlertDedup(str(tmp_path / "dedup.json"), window_seconds=1)
    d.record("backup", "missed")
    time.sleep(1.1)
    assert d.is_duplicate("backup", "missed") is False


def test_evict_removes_expired(tmp_path):
    d = AlertDedup(str(tmp_path / "dedup.json"), window_seconds=1)
    d.record("backup", "missed")
    time.sleep(1.1)
    d.evict_expired()
    assert d.count("backup", "missed") == 0


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------

def test_state_persists_across_instances(tmp_path):
    path = str(tmp_path / "dedup.json")
    d1 = AlertDedup(path, window_seconds=60)
    d1.record("backup", "missed")

    d2 = AlertDedup(path, window_seconds=60)
    assert d2.is_duplicate("backup", "missed") is True


def test_corrupt_state_file_handled_gracefully(tmp_path):
    path = str(tmp_path / "dedup.json")
    with open(path, "w") as fh:
        fh.write("not json{{{")
    d = AlertDedup(path, window_seconds=60)
    assert d.is_duplicate("backup", "missed") is False
