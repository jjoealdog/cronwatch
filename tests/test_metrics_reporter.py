"""Tests for metrics_reporter formatting helpers."""
import pytest

from cronwatch.metrics import MetricsCollector
from cronwatch.metrics_reporter import metrics_table, metrics_for_job


@pytest.fixture
def collector():
    c = MetricsCollector()
    c.record_end("backup", success=True)
    c.record_end("backup", success=True)
    c.record_end("backup", success=False)
    c.record_end("cleanup", success=False)
    return c


def test_metrics_table_contains_job_names(collector):
    table = metrics_table(collector)
    assert "backup" in table
    assert "cleanup" in table


def test_metrics_table_empty_collector():
    c = MetricsCollector()
    result = metrics_table(c)
    assert "No metrics" in result


def test_metrics_table_shows_counts(collector):
    table = metrics_table(collector)
    # backup has 3 total runs
    assert "3" in table


def test_metrics_for_job_known(collector):
    summary = metrics_for_job(collector, "backup")
    assert "backup" in summary
    assert "Total runs" in summary
    assert "Success rate" in summary


def test_metrics_for_job_unknown(collector):
    result = metrics_for_job(collector, "nonexistent")
    assert "No metrics" in result
    assert "nonexistent" in result


def test_metrics_for_job_success_rate_format(collector):
    summary = metrics_for_job(collector, "backup")
    # 2/3 success rate => ~66.7%
    assert "%" in summary


def test_metrics_table_header_present(collector):
    table = metrics_table(collector)
    assert "Job" in table
    assert "Runs" in table
