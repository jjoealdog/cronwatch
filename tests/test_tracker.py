"""Tests for the job tracker."""

import json
import time

import pytest

from cronwatch.config import JobConfig
from cronwatch.tracker import JobState, JobTracker


@pytest.fixture()
def tracker(tmp_path):
    return JobTracker(state_file=str(tmp_path / "state.json"))


def test_initial_state_is_empty(tracker):
    state = tracker.get("my-job")
    assert state.job_name == "my-job"
    assert state.last_run_at is None
    assert state.consecutive_failures == 0


def test_record_successful_run(tracker):
    state = tracker.record_run("backup", exit_code=0)
    assert state.last_exit_code == 0
    assert state.consecutive_failures == 0
    assert state.last_run_at is not None


def test_record_failed_run_increments_counter(tracker):
    tracker.record_run("backup", exit_code=1)
    state = tracker.record_run("backup", exit_code=1)
    assert state.consecutive_failures == 2


def test_success_resets_failure_counter(tracker):
    tracker.record_run("backup", exit_code=1)
    tracker.record_run("backup", exit_code=1)
    state = tracker.record_run("backup", exit_code=0)
    assert state.consecutive_failures == 0


def test_state_persists_across_instances(tmp_path):
    path = str(tmp_path / "state.json")
    t1 = JobTracker(state_file=path)
    t1.record_run("nightly", exit_code=0)

    t2 = JobTracker(state_file=path)
    state = t2.get("nightly")
    assert state.last_exit_code == 0


def test_is_overdue_when_past_interval(tracker):
    job = JobConfig(name="quick", schedule="* * * * *", expected_interval_seconds=10)
    state = tracker.get("quick")
    state.last_run_at = time.time() - 20
    tracker._save()
    assert tracker.is_overdue(job) is True


def test_is_not_overdue_when_recent(tracker):
    job = JobConfig(name="quick", schedule="* * * * *", expected_interval_seconds=3600)
    tracker.record_run("quick", exit_code=0)
    assert tracker.is_overdue(job) is False


def test_is_not_overdue_when_never_run(tracker):
    job = JobConfig(name="new-job", schedule="0 * * * *", expected_interval_seconds=3600)
    assert tracker.is_overdue(job) is False


def test_mark_alerted_sets_timestamp(tracker):
    tracker.mark_alerted("myjob")
    state = tracker.get("myjob")
    assert state.last_alert_at is not None
