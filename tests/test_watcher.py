"""Tests for cronwatch.watcher."""

import os
import pytest
from cronwatch.watcher import parse_marker_line, LogWatcher, MarkerEvent


# ---------------------------------------------------------------------------
# parse_marker_line
# ---------------------------------------------------------------------------

def test_parse_valid_success_line():
    line = "2024-01-15 03:00:01 [CRONWATCH] job=backup status=success duration=4.2"
    ev = parse_marker_line(line)
    assert ev is not None
    assert ev.job_name == "backup"
    assert ev.success is True
    assert ev.duration_seconds == pytest.approx(4.2)


def test_parse_valid_failure_line():
    line = "[CRONWATCH] job=cleanup status=failure duration=0.5"
    ev = parse_marker_line(line)
    assert ev is not None
    assert ev.success is False
    assert ev.job_name == "cleanup"


def test_parse_returns_none_for_unrelated_line():
    assert parse_marker_line("nothing interesting here") is None


def test_parse_returns_none_for_unknown_status():
    line = "[CRONWATCH] job=x status=unknown duration=1.0"
    assert parse_marker_line(line) is None


# ---------------------------------------------------------------------------
# LogWatcher
# ---------------------------------------------------------------------------

@pytest.fixture()
def log_file(tmp_path):
    return str(tmp_path / "cron.log")


def test_poll_missing_file_returns_zero(log_file):
    events = []
    w = LogWatcher(log_file, events.append)
    assert w.poll() == 0
    assert events == []


def test_poll_detects_new_markers(log_file):
    events = []
    w = LogWatcher(log_file, events.append)

    with open(log_file, "w") as fh:
        fh.write("[CRONWATCH] job=nightly status=success duration=10.0\n")

    count = w.poll()
    assert count == 1
    assert len(events) == 1
    assert events[0].job_name == "nightly"


def test_poll_does_not_reread_old_lines(log_file):
    events = []
    w = LogWatcher(log_file, events.append)

    with open(log_file, "w") as fh:
        fh.write("[CRONWATCH] job=first status=success duration=1.0\n")

    w.poll()
    assert len(events) == 1

    # second poll — no new content
    w.poll()
    assert len(events) == 1

    # append a new line
    with open(log_file, "a") as fh:
        fh.write("[CRONWATCH] job=second status=failure duration=0.1\n")

    w.poll()
    assert len(events) == 2
    assert events[1].job_name == "second"
    assert events[1].success is False


def test_reset_skips_existing_content(log_file):
    events = []
    w = LogWatcher(log_file, events.append)

    with open(log_file, "w") as fh:
        fh.write("[CRONWATCH] job=old status=success duration=2.0\n")

    w.reset()  # skip existing content
    w.poll()
    assert events == []
