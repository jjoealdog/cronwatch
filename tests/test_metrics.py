"""Tests for MetricsCollector."""
import time

import pytest

from cronwatch.metrics import MetricsCollector, JobMetrics


@pytest.fixture
def collector():
    return MetricsCollector()


def test_initial_state_empty(collector):
    assert collector.all_metrics() == []
    assert collector.get("job1") is None


def test_record_end_success(collector):
    collector.record_end("job1", success=True)
    m = collector.get("job1")
    assert m is not None
    assert m.total_runs == 1
    assert m.successful_runs == 1
    assert m.failed_runs == 0


def test_record_end_failure(collector):
    collector.record_end("job1", success=False)
    m = collector.get("job1")
    assert m.failed_runs == 1
    assert m.successful_runs == 0


def test_success_rate(collector):
    collector.record_end("job1", success=True)
    collector.record_end("job1", success=True)
    collector.record_end("job1", success=False)
    m = collector.get("job1")
    assert abs(m.success_rate - 2 / 3) < 1e-9


def test_success_rate_none_when_no_runs():
    m = JobMetrics(job_name="x")
    assert m.success_rate is None


def test_duration_recorded(collector):
    collector.record_start("job1")
    time.sleep(0.01)
    collector.record_end("job1", success=True)
    m = collector.get("job1")
    assert m.last_duration_seconds is not None
    assert m.last_duration_seconds >= 0.005
    assert m.avg_duration is not None


def test_no_start_no_duration(collector):
    collector.record_end("job1", success=True)
    m = collector.get("job1")
    assert m.last_duration_seconds is None
    assert m.avg_duration is None


def test_multiple_jobs_independent(collector):
    collector.record_end("job1", success=True)
    collector.record_end("job2", success=False)
    assert collector.get("job1").successful_runs == 1
    assert collector.get("job2").failed_runs == 1


def test_reset_clears_job(collector):
    collector.record_end("job1", success=True)
    collector.reset("job1")
    assert collector.get("job1") is None


def test_all_metrics_returns_dicts(collector):
    collector.record_end("job1", success=True)
    all_m = collector.all_metrics()
    assert len(all_m) == 1
    assert "job_name" in all_m[0]
    assert "success_rate" in all_m[0]
