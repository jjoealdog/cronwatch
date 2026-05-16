"""Tests for cronwatch.correlation and cronwatch.correlation_integration."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwatch.correlation import AlertCorrelator, CorrelationGroup
from cronwatch.correlation_integration import CorrelatedAlerter, build_correlated_alert_fn


# ---------------------------------------------------------------------------
# CorrelationGroup
# ---------------------------------------------------------------------------

def test_group_add_deduplicates_jobs():
    g = CorrelationGroup(key="k")
    g.add("job_a", "fail")
    g.add("job_a", "fail")
    assert g.job_names == ["job_a"]
    assert g.reasons == ["fail"]


def test_group_add_multiple_jobs():
    g = CorrelationGroup(key="k")
    g.add("job_a", "timeout")
    g.add("job_b", "exit 1")
    assert len(g.job_names) == 2
    assert len(g.reasons) == 2


def test_group_not_expired_immediately():
    g = CorrelationGroup(key="k")
    assert not g.is_expired(window=60)


def test_group_roundtrip():
    g = CorrelationGroup(key="test")
    g.add("job_x", "reason_x")
    g.delivered = True
    g2 = CorrelationGroup.from_dict(g.to_dict())
    assert g2.key == "test"
    assert g2.job_names == ["job_x"]
    assert g2.delivered is True


# ---------------------------------------------------------------------------
# AlertCorrelator
# ---------------------------------------------------------------------------

@pytest.fixture
def correlator(tmp_path):
    return AlertCorrelator(state_file=tmp_path / "corr.json", window=60)


def test_ingest_creates_group(correlator):
    correlator.ingest("backup", "exit 1")
    assert correlator.group_count() == 1


def test_ingest_same_key_merges(correlator):
    correlator.ingest("backup", "exit 1", group_key="ops")
    correlator.ingest("sync", "timeout", group_key="ops")
    assert correlator.group_count() == 1
    grp = correlator._groups["ops"]
    assert "backup" in grp.job_names
    assert "sync" in grp.job_names


def test_flush_calls_alert_fn(correlator):
    correlator.ingest("job_a", "fail")
    calls = []
    correlator.flush(lambda s, b: calls.append((s, b)))
    assert len(calls) == 1
    assert "job_a" in calls[0][1]


def test_flush_marks_delivered(correlator):
    correlator.ingest("job_a", "fail")
    correlator.flush(lambda s, b: None)
    # second flush should not re-deliver
    calls = []
    correlator.flush(lambda s, b: calls.append(1))
    assert calls == []


def test_state_persists_across_instances(tmp_path):
    sf = tmp_path / "state.json"
    c1 = AlertCorrelator(state_file=sf, window=60)
    c1.ingest("job_z", "crash")
    c2 = AlertCorrelator(state_file=sf, window=60)
    assert c2.group_count() == 1


# ---------------------------------------------------------------------------
# CorrelatedAlerter integration
# ---------------------------------------------------------------------------

def test_correlated_alerter_flush_sends(tmp_path):
    calls = []
    alerter = CorrelatedAlerter(lambda s, b: calls.append(b), window=60)
    alerter.ingest("job_a", "fail")
    alerter.ingest("job_b", "fail")
    count = alerter.flush()
    assert count == 1
    assert "job_a" in calls[0]
    assert "job_b" in calls[0]


def test_correlated_alerter_reset_clears(tmp_path):
    alerter = CorrelatedAlerter(MagicMock(), window=60)
    alerter.ingest("job_a", "fail")
    alerter.reset()
    assert alerter.pending_count() == 0


def test_build_correlated_alert_fn_auto_flush():
    calls = []
    fn = build_correlated_alert_fn(lambda s, b: calls.append(b), auto_flush=True)
    fn("job_a", "exit 1")
    assert len(calls) == 1


def test_build_correlated_alert_fn_no_auto_flush():
    calls = []
    fn = build_correlated_alert_fn(lambda s, b: calls.append(b), auto_flush=False)
    fn("job_a", "exit 1")
    assert len(calls) == 0
    fn._alerter.flush()
    assert len(calls) == 1
