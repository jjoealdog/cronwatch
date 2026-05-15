"""Tests for cronwatch.scheduler."""

from unittest.mock import MagicMock, patch, call

import pytest

from cronwatch.config import CronwatchConfig, JobConfig, AlertConfig
from cronwatch.scheduler import Scheduler
from cronwatch.tracker import JobTracker


@pytest.fixture()
def alert_cfg():
    return AlertConfig(recipients=["ops@example.com"])


@pytest.fixture()
def config(alert_cfg):
    jobs = [
        JobConfig(name="backup", schedule="0 2 * * *", alert=alert_cfg),
        JobConfig(name="report", schedule="0 8 * * 1", alert=alert_cfg),
    ]
    return CronwatchConfig(jobs=jobs, default_alert=alert_cfg)


@pytest.fixture()
def tracker(tmp_path):
    return JobTracker(state_file=str(tmp_path / "state.json"))


@pytest.fixture()
def alert_fn():
    return MagicMock(return_value=True)


def test_run_once_calls_check_for_each_job(config, tracker, alert_fn):
    scheduler = Scheduler(config, tracker, alert_fn, tick_seconds=1)
    with patch("cronwatch.scheduler.Checker") as MockChecker:
        mock_checker = MockChecker.return_value
        scheduler.run_once()
        assert mock_checker.check_job.call_count == len(config.jobs)
        mock_checker.check_job.assert_any_call("backup")
        mock_checker.check_job.assert_any_call("report")


def test_start_stop_runs_loop(config, tracker, alert_fn):
    scheduler = Scheduler(config, tracker, alert_fn, tick_seconds=0)
    call_count = 0

    original_run_once = scheduler.run_once

    def patched_run_once():
        nonlocal call_count
        call_count += 1
        original_run_once()
        scheduler.stop()

    scheduler.run_once = patched_run_once
    scheduler.start()
    assert call_count == 1
    assert scheduler._running is False


def test_stop_sets_running_false(config, tracker, alert_fn):
    scheduler = Scheduler(config, tracker, alert_fn)
    scheduler._running = True
    scheduler.stop()
    assert scheduler._running is False
