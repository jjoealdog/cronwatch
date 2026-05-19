"""Tests for cronwatch.sampling."""

from __future__ import annotations

import random
from typing import List

import pytest

from cronwatch.sampling import SampledAlerter, SamplingStats, build_sampled_alert_fn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

calls: List[tuple] = []


def alert_fn(job: str, reason: str, detail: str) -> bool:
    calls.append((job, reason, detail))
    return True


@pytest.fixture(autouse=True)
def _clear_calls():
    calls.clear()
    yield


# ---------------------------------------------------------------------------
# SamplingStats
# ---------------------------------------------------------------------------

def test_stats_initial_zeros():
    s = SamplingStats()
    assert s.total == 0
    assert s.effective_rate == 0.0


def test_stats_effective_rate():
    s = SamplingStats(delivered=3, dropped=1)
    assert s.total == 4
    assert s.effective_rate == pytest.approx(0.75)


def test_stats_to_dict_keys():
    s = SamplingStats(delivered=2, dropped=2)
    d = s.to_dict()
    assert set(d.keys()) == {"delivered", "dropped", "total", "effective_rate"}


# ---------------------------------------------------------------------------
# SampledAlerter — rate=1.0 (always deliver)
# ---------------------------------------------------------------------------

def test_rate_one_always_delivers():
    alerter = SampledAlerter(alert_fn, rate=1.0)
    for _ in range(10):
        alerter.alert("job", "failed", "exit 1")
    assert alerter.stats_for("job").delivered == 10
    assert alerter.stats_for("job").dropped == 0


# ---------------------------------------------------------------------------
# SampledAlerter — rate=0.0 (never deliver)
# ---------------------------------------------------------------------------

def test_rate_zero_never_delivers():
    alerter = SampledAlerter(alert_fn, rate=0.0)
    for _ in range(10):
        alerter.alert("job", "failed", "exit 1")
    assert len(calls) == 0
    assert alerter.stats_for("job").dropped == 10
    assert alerter.stats_for("job").delivered == 0


# ---------------------------------------------------------------------------
# SampledAlerter — deterministic RNG
# ---------------------------------------------------------------------------

def test_deterministic_sampling():
    rng = random.Random(42)
    alerter = SampledAlerter(alert_fn, rate=0.5, rng=rng)
    for _ in range(100):
        alerter.alert("job", "failed", "x")
    stats = alerter.stats_for("job")
    # With seed 42 and rate 0.5 we expect roughly 50 deliveries; just check bounds.
    assert 30 <= stats.delivered <= 70


# ---------------------------------------------------------------------------
# Multiple jobs tracked independently
# ---------------------------------------------------------------------------

def test_different_jobs_tracked_independently():
    alerter = SampledAlerter(alert_fn, rate=1.0)
    alerter.alert("job_a", "failed", "x")
    alerter.alert("job_a", "failed", "x")
    alerter.alert("job_b", "failed", "x")
    assert alerter.stats_for("job_a").delivered == 2
    assert alerter.stats_for("job_b").delivered == 1


# ---------------------------------------------------------------------------
# reset_stats
# ---------------------------------------------------------------------------

def test_reset_stats_clears_single_job():
    alerter = SampledAlerter(alert_fn, rate=1.0)
    alerter.alert("job", "failed", "x")
    alerter.reset_stats("job")
    assert alerter.stats_for("job").delivered == 0


def test_reset_stats_clears_all():
    alerter = SampledAlerter(alert_fn, rate=1.0)
    alerter.alert("job_a", "failed", "x")
    alerter.alert("job_b", "failed", "x")
    alerter.reset_stats()
    assert alerter.stats_for("job_a").total == 0
    assert alerter.stats_for("job_b").total == 0


# ---------------------------------------------------------------------------
# Invalid rate
# ---------------------------------------------------------------------------

def test_invalid_rate_raises():
    with pytest.raises(ValueError):
        SampledAlerter(alert_fn, rate=1.5)


def test_negative_rate_raises():
    with pytest.raises(ValueError):
        SampledAlerter(alert_fn, rate=-0.1)


# ---------------------------------------------------------------------------
# build_sampled_alert_fn
# ---------------------------------------------------------------------------

def test_build_sampled_alert_fn_returns_alerter():
    alerter = build_sampled_alert_fn(alert_fn, rate=1.0)
    assert isinstance(alerter, SampledAlerter)
    result = alerter("job", "failed", "x")
    assert result is True
