"""Tests for cronwatch.checker."""

from unittest.mock import MagicMock

import pytest

from cronwatch.checker import Checker
from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.tracker import JobTracker


@pytest.fixture()
def tracker(tmp_path):
    return JobTracker(str(tmp_path / "state.json"))


@pytest.fixture()
def alert_fn():
    return MagicMock(return_value=True)


def _config(jobs=None, default_alert=None):
    return CronwatchConfig(
        jobs=jobs or [],
        default_alert=default_alert,
        state_file="/tmp/state.json",
    )


def _job(name="test", schedule="* * * * *", max_duration=None, alert=None):
    return JobConfig(name=name, schedule=schedule, max_duration=max_duration, alert=alert)


def test_no_alert_on_clean_run(tracker, alert_fn):
    job = _job(alert=AlertConfig(email=["a@b.com"]))
    cfg = _config(jobs=[job])
    tracker.record(job.name, exit_code=0, duration=5)
    Checker(cfg, tracker, alert_fn).check_all()
    alert_fn.assert_not_called()


def test_alert_on_failure(tracker, alert_fn):
    job = _job(alert=AlertConfig(email=["a@b.com"], failure_threshold=1))
    cfg = _config(jobs=[job])
    tracker.record(job.name, exit_code=1, duration=2)
    Checker(cfg, tracker, alert_fn).check_all()
    alert_fn.assert_called_once()
    _, name, reason, _ = alert_fn.call_args[0]
    assert name == job.name
    assert "failed" in reason


def test_no_alert_below_threshold(tracker, alert_fn):
    job = _job(alert=AlertConfig(email=["a@b.com"], failure_threshold=3))
    cfg = _config(jobs=[job])
    tracker.record(job.name, exit_code=1, duration=2)
    Checker(cfg, tracker, alert_fn).check_all()
    alert_fn.assert_not_called()


def test_alert_on_exceeded_duration(tracker, alert_fn):
    job = _job(max_duration=10, alert=AlertConfig(email=["a@b.com"]))
    cfg = _config(jobs=[job])
    tracker.record(job.name, exit_code=0, duration=30)
    Checker(cfg, tracker, alert_fn).check_all()
    alert_fn.assert_called_once()
    _, name, reason, _ = alert_fn.call_args[0]
    assert "duration" in reason


def test_uses_default_alert_when_job_has_none(tracker, alert_fn):
    default = AlertConfig(email=["ops@example.com"], failure_threshold=1)
    job = _job(alert=None)
    cfg = _config(jobs=[job], default_alert=default)
    tracker.record(job.name, exit_code=2, duration=1)
    Checker(cfg, tracker, alert_fn).check_all()
    alert_fn.assert_called_once()


def test_no_alert_without_any_alert_config(tracker, alert_fn):
    job = _job(alert=None)
    cfg = _config(jobs=[job], default_alert=None)
    tracker.record(job.name, exit_code=1, duration=1)
    Checker(cfg, tracker, alert_fn).check_all()
    alert_fn.assert_not_called()
