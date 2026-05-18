"""Tests for cronwatch.grouping."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from cronwatch.grouping import AlertGrouper, build_grouping_alert_fn


@pytest.fixture()
def calls():
    return []


@pytest.fixture()
def alert_fn(calls):
    def _fn(subject: str, body: str) -> None:
        calls.append((subject, body))
    return _fn


@pytest.fixture()
def grouper(alert_fn):
    return AlertGrouper(alert_fn, window_seconds=5.0, max_size=10)


def test_ingest_does_not_immediately_alert(grouper, calls):
    grouper.ingest("job_a", "failed")
    assert len(calls) == 0


def test_flush_sends_single_alert(grouper, calls):
    grouper.ingest("job_a", "failed")
    grouper.ingest("job_b", "missed")
    flushed = grouper.flush()
    assert flushed == 2
    assert len(calls) == 1
    subject, body = calls[0]
    assert "2" in subject
    assert "job_a" in body
    assert "job_b" in body


def test_flush_empty_returns_zero(grouper, calls):
    assert grouper.flush() == 0
    assert len(calls) == 0


def test_pending_count_tracks_ingested(grouper):
    assert grouper.pending_count() == 0
    grouper.ingest("job_a", "failed")
    assert grouper.pending_count() == 1
    grouper.ingest("job_b", "missed")
    assert grouper.pending_count() == 2


def test_flush_clears_pending(grouper):
    grouper.ingest("job_a", "failed")
    grouper.flush()
    assert grouper.pending_count() == 0


def test_max_size_triggers_auto_flush(alert_fn, calls):
    grouper = AlertGrouper(alert_fn, window_seconds=60.0, max_size=3)
    grouper.ingest("j1", "r")
    grouper.ingest("j2", "r")
    assert len(calls) == 0
    grouper.ingest("j3", "r")  # hits max_size
    assert len(calls) == 1
    assert grouper.pending_count() == 0


def test_expired_window_flushes_before_new_ingest(alert_fn, calls):
    grouper = AlertGrouper(alert_fn, window_seconds=0.01, max_size=100)
    grouper.ingest("job_a", "failed")
    time.sleep(0.05)
    grouper.ingest("job_b", "missed")  # triggers flush of previous window
    assert len(calls) == 1
    assert "job_a" in calls[0][1]
    assert grouper.pending_count() == 1  # job_b is now in new window


def test_is_window_expired_false_when_empty(grouper):
    assert grouper.is_window_expired() is False


def test_build_grouping_alert_fn_returns_grouper(alert_fn):
    g = build_grouping_alert_fn(alert_fn, window_seconds=30.0, max_size=5)
    assert isinstance(g, AlertGrouper)
    g.ingest("job_x", "reason")
    assert g.pending_count() == 1
