"""Tests for cronwatch.reporter."""

from __future__ import annotations

import json
import os
import pytest

from cronwatch.config import JobConfig, AlertConfig
from cronwatch.tracker import JobTracker
from cronwatch.reporter import job_summary, full_report


@pytest.fixture()
def history_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture()
def tracker():
    return JobTracker(state_file=None)  # in-memory only


def _job(name="backup", schedule="0 2 * * *"):
    return JobConfig(
        name=name,
        schedule=schedule,
        alert=AlertConfig(recipients=["ops@example.com"]),
    )


def _write_run(history_dir, job_name, success=True, timestamp="2024-01-01T02:00:00+00:00"):
    path = os.path.join(history_dir, f"{job_name}.jsonl")
    with open(path, "a") as fh:
        fh.write(json.dumps({"timestamp": timestamp, "success": success}) + "\n")


def test_job_summary_never_run(history_dir, tracker):
    summary = job_summary(_job(), tracker, history_dir)
    assert "backup" in summary
    assert "never" in summary
    assert "Recent runs (0)" in summary


def test_job_summary_after_run(history_dir, tracker):
    tracker.record("backup", success=True)
    _write_run(history_dir, "backup", success=True)
    summary = job_summary(_job(), tracker, history_dir)
    assert "Recent runs (1)" in summary
    assert "[OK]" in summary
    assert "Failures : 0" in summary


def test_job_summary_failure_streak(history_dir, tracker):
    for _ in range(3):
        tracker.record("backup", success=False)
        _write_run(history_dir, "backup", success=False)
    summary = job_summary(_job(), tracker, history_dir)
    assert "Failures : 3" in summary
    assert "Failure streak (history): 3" in summary


def test_full_report_contains_all_jobs(history_dir, tracker):
    jobs = [_job("backup"), _job("cleanup", "30 3 * * *")]
    report = full_report(jobs, tracker, history_dir)
    assert "backup" in report
    assert "cleanup" in report
    assert "cronwatch report" in report


def test_full_report_separators(history_dir, tracker):
    jobs = [_job("job1"), _job("job2")]
    report = full_report(jobs, tracker, history_dir)
    assert report.count("-" * 40) == 2
