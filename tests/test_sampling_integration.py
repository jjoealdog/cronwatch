"""Tests for cronwatch.sampling_integration."""

from __future__ import annotations

import random
from typing import List

import pytest

from cronwatch.sampling_integration import SamplingMiddleware, build_sampling_alert_fn
from cronwatch.config import CronwatchConfig, AlertConfig, JobConfig


calls: List[tuple] = []


def _fn(job: str, reason: str, detail: str) -> bool:
    calls.append((job, reason, detail))
    return True


@pytest.fixture(autouse=True)
def _clear():
    calls.clear()
    yield


# ---------------------------------------------------------------------------
# SamplingMiddleware
# ---------------------------------------------------------------------------

def test_middleware_rate_one_passes_all():
    mw = SamplingMiddleware(_fn, rate=1.0)
    for _ in range(5):
        mw("job", "failed", "x")
    assert len(calls) == 5


def test_middleware_rate_zero_drops_all():
    mw = SamplingMiddleware(_fn, rate=0.0)
    for _ in range(5):
        mw("job", "failed", "x")
    assert len(calls) == 0


def test_middleware_stats_aggregate_across_jobs():
    mw = SamplingMiddleware(_fn, rate=1.0)
    mw("job_a", "failed", "x")
    mw("job_b", "failed", "x")
    mw("job_b", "failed", "x")
    s = mw.stats
    assert s["delivered"] == 3
    assert s["dropped"] == 0
    assert s["total"] == 3


def test_middleware_stats_effective_rate_mixed():
    rng = random.Random(0)
    mw = SamplingMiddleware(_fn, rate=0.5, rng=rng)
    for _ in range(100):
        mw("job", "failed", "x")
    s = mw.stats
    assert s["total"] == 100
    assert 0.0 < s["effective_rate"] < 1.0


# ---------------------------------------------------------------------------
# build_sampling_alert_fn
# ---------------------------------------------------------------------------

def _make_cfg(rate: float) -> CronwatchConfig:
    alert = AlertConfig(
        email="ops@example.com",
        smtp_host="localhost",
        smtp_port=25,
        smtp_tls=False,
        extra={"sampling_rate": rate},
    )
    job = JobConfig(name="j", schedule="* * * * *")
    return CronwatchConfig(alert=alert, jobs=[job])


def test_build_returns_callable():
    cfg = _make_cfg(1.0)
    fn = build_sampling_alert_fn(cfg, _fn)
    assert callable(fn)


def test_build_rate_one_delivers():
    cfg = _make_cfg(1.0)
    fn = build_sampling_alert_fn(cfg, _fn)
    fn("job", "failed", "x")
    assert len(calls) == 1


def test_build_rate_zero_drops():
    cfg = _make_cfg(0.0)
    fn = build_sampling_alert_fn(cfg, _fn)
    fn("job", "failed", "x")
    assert len(calls) == 0
