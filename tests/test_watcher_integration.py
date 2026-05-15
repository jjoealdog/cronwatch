"""Tests for cronwatch.watcher_integration."""

import pytest
from unittest.mock import MagicMock, patch

from cronwatch.config import CronwatchConfig, JobConfig, AlertConfig
from cronwatch.tracker import JobTracker
from cronwatch.watcher_integration import WatcherIntegration
from cronwatch.watcher import MarkerEvent


@pytest.fixture()
def alert_fn():
    return MagicMock()


@pytest.fixture()
def cfg():
    alert = AlertConfig(recipients=["ops@example.com"])
    job = JobConfig(name="backup", schedule="0 2 * * *", alert=None)
    return CronwatchConfig(alert=alert, jobs=[job])


@pytest.fixture()
def tracker(tmp_path):
    return JobTracker(str(tmp_path / "state.json"))


@pytest.fixture()
def log_file(tmp_path):
    return str(tmp_path / "cron.log")


def _make_wi(cfg, tracker, alert_fn, log_file):
    return WatcherIntegration(cfg, tracker, alert_fn, log_file, skip_existing=False)


def test_poll_success_event_records_success(cfg, tracker, alert_fn, log_file):
    wi = _make_wi(cfg, tracker, alert_fn, log_file)
    with open(log_file, "w") as fh:
        fh.write("[CRONWATCH] job=backup status=success duration=5.0\n")
    wi.poll()
    state = tracker.get_state("backup")
    assert state is not None
    assert state.last_success is not None
    assert state.consecutive_failures == 0


def test_poll_failure_event_records_failure(cfg, tracker, alert_fn, log_file):
    wi = _make_wi(cfg, tracker, alert_fn, log_file)
    with open(log_file, "w") as fh:
        fh.write("[CRONWATCH] job=backup status=failure duration=0.2\n")
    wi.poll()
    state = tracker.get_state("backup")
    assert state is not None
    assert state.consecutive_failures == 1


def test_unknown_job_is_ignored(cfg, tracker, alert_fn, log_file):
    wi = _make_wi(cfg, tracker, alert_fn, log_file)
    with open(log_file, "w") as fh:
        fh.write("[CRONWATCH] job=unknown_job status=success duration=1.0\n")
    wi.poll()
    # tracker should have no state for unknown job
    assert tracker.get_state("unknown_job") is None
    alert_fn.assert_not_called()


def test_skip_existing_true_ignores_old_lines(cfg, tracker, alert_fn, log_file):
    # write content BEFORE creating the integration
    with open(log_file, "w") as fh:
        fh.write("[CRONWATCH] job=backup status=success duration=3.0\n")

    wi = WatcherIntegration(cfg, tracker, alert_fn, log_file, skip_existing=True)
    wi.poll()  # should not process pre-existing line
    assert tracker.get_state("backup") is None
