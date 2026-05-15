"""Tests for cronwatch.snapshot."""

import json
import os
import pytest

from cronwatch.tracker import JobTracker
from cronwatch.snapshot import (
    JobSnapshot,
    capture,
    load_snapshot,
    save_snapshot,
)


@pytest.fixture()
def tracker(tmp_path):
    t = JobTracker(state_file=str(tmp_path / "state.json"))
    return t


def test_capture_empty_tracker_returns_empty_list(tracker):
    snaps = capture(tracker)
    assert snaps == []


def test_capture_includes_recorded_jobs(tracker):
    tracker.record_success("backup", duration=5.0)
    tracker.record_failure("cleanup", duration=1.2)
    snaps = capture(tracker)
    names = {s.name for s in snaps}
    assert names == {"backup", "cleanup"}


def test_capture_reflects_correct_status(tracker):
    tracker.record_success("backup", duration=3.0)
    tracker.record_failure("cleanup", duration=0.5)
    snaps = {s.name: s for s in capture(tracker)}
    assert snaps["backup"].last_status == "success"
    assert snaps["cleanup"].last_status == "failure"


def test_capture_failure_count(tracker):
    tracker.record_failure("job", duration=1.0)
    tracker.record_failure("job", duration=1.0)
    snaps = {s.name: s for s in capture(tracker)}
    assert snaps["job"].failure_count == 2


def test_capture_success_resets_failure_count(tracker):
    tracker.record_failure("job", duration=1.0)
    tracker.record_success("job", duration=1.0)
    snaps = {s.name: s for s in capture(tracker)}
    assert snaps["job"].failure_count == 0


def test_save_and_load_roundtrip(tracker, tmp_path):
    tracker.record_success("alpha", duration=2.0)
    tracker.record_failure("beta", duration=0.3)
    snaps = capture(tracker)
    path = str(tmp_path / "snapshot.json")
    save_snapshot(snaps, path)
    loaded = load_snapshot(path)
    assert len(loaded) == 2
    names = {s.name for s in loaded}
    assert names == {"alpha", "beta"}


def test_load_missing_file_returns_empty(tmp_path):
    result = load_snapshot(str(tmp_path / "nonexistent.json"))
    assert result == []


def test_save_creates_valid_json(tracker, tmp_path):
    tracker.record_success("myjob", duration=1.0)
    snaps = capture(tracker)
    path = str(tmp_path / "snap.json")
    save_snapshot(snaps, path)
    with open(path) as fh:
        data = json.load(fh)
    assert isinstance(data, list)
    assert data[0]["name"] == "myjob"


def test_job_snapshot_to_dict_and_from_dict():
    s = JobSnapshot(
        name="x",
        last_run="2024-01-01T00:00:00+00:00",
        last_status="success",
        failure_count=0,
        captured_at="2024-01-01T01:00:00+00:00",
    )
    d = s.to_dict()
    s2 = JobSnapshot.from_dict(d)
    assert s2.name == s.name
    assert s2.last_status == s.last_status
    assert s2.failure_count == 0
