"""Tests for the Checker logic."""

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.checker import MIN_ALERT_INTERVAL, Checker
from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.tracker import JobState, JobTracker


@pytest.fixture()
def tracker(tmp_path):
    return JobTracker(state_file=str(tmp_path / "state.json"))


@pytest.fixture()
def alert_fn():
    return MagicMock()


def _config(*jobs, default_alert=None):
    return CronwatchConfig(jobs=list(jobs), default_alert=default_alert)


def _job(name="test-job", interval=3600, failures=1):
    return JobConfig(
        name=name,
        schedule="0 * * * *",
        expected_interval_seconds=interval,
        alert_after_failures=failures,
    )


def test_no_alert_on_clean_run(tracker, alert_fn):
    job = _job()
    tracker.record_run(job.name, exit_code=0)
    checker = Checker(_config(job), tracker, alert_fn)
    checker.check_job(job)
    alert_fn.assert_not_called()


def test_alert_on_failure(tracker, alert_fn):
    job = _job(failures=1)
    tracker.record_run(job.name, exit_code=1)
    checker = Checker(_config(job), tracker, alert_fn)
    checker.check_job(job)
    alert_fn.assert_called_once()
    _, _, reason = alert_fn.call_args[0]
    assert reason == "failure"


def test_no_alert_below_failure_threshold(tracker, alert_fn):
    job = _job(failures=3)
    tracker.record_run(job.name, exit_code=1)
    tracker.record_run(job.name, exit_code=1)
    checker = Checker(_config(job), tracker, alert_fn)
    checker.check_job(job)
    alert_fn.assert_not_called()


def test_alert_on_missed_run(tracker, alert_fn):
    job = _job(interval=10)
    state = tracker.get(job.name)
    state.last_run_at = time.time() - 30
    state.last_exit_code = 0
    tracker._save()
    checker = Checker(_config(job), tracker, alert_fn)
    checker.check_job(job)
    alert_fn.assert_called_once()
    _, _, reason = alert_fn.call_args[0]
    assert reason == "missed"


def test_no_duplicate_alert_within_cooldown(tracker, alert_fn):
    job = _job(failures=1)
    tracker.record_run(job.name, exit_code=1)
    tracker.mark_alerted(job.name)
    # Pretend alert was very recent
    state = tracker.get(job.name)
    state.last_alert_at = time.time()
    tracker._save()
    checker = Checker(_config(job), tracker, alert_fn)
    checker.check_job(job)
    alert_fn.assert_not_called()


def test_uses_default_alert_when_job_has_none(tracker, alert_fn):
    job = _job(failures=1)
    default = AlertConfig(on_failure=False, on_missed=False)
    tracker.record_run(job.name, exit_code=1)
    checker = Checker(_config(job, default_alert=default), tracker, alert_fn)
    checker.check_job(job)
    alert_fn.assert_not_called()
