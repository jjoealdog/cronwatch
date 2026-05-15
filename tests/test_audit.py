"""Tests for cronwatch.audit."""

import json
from pathlib import Path

import pytest

from cronwatch.audit import (
    iter_events,
    prune_audit_log,
    recent_events,
    record_event,
)


@pytest.fixture()
def audit_file(tmp_path: Path) -> Path:
    return tmp_path / "audit.log"


def test_record_creates_file(audit_file: Path) -> None:
    record_event("test_event", "hello", path=audit_file)
    assert audit_file.exists()


def test_record_writes_valid_json(audit_file: Path) -> None:
    record_event("job_fail", "job=backup failed", path=audit_file)
    lines = audit_file.read_text().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["event"] == "job_fail"
    assert data["detail"] == "job=backup failed"
    assert "ts" in data


def test_record_includes_actor(audit_file: Path) -> None:
    record_event("alert", "sent", path=audit_file, actor="cli")
    data = json.loads(audit_file.read_text().strip())
    assert data["actor"] == "cli"


def test_iter_events_yields_all(audit_file: Path) -> None:
    for i in range(3):
        record_event("ev", f"detail {i}", path=audit_file)
    events = list(iter_events(audit_file))
    assert len(events) == 3


def test_iter_events_missing_file_yields_nothing(tmp_path: Path) -> None:
    events = list(iter_events(tmp_path / "nope.log"))
    assert events == []


def test_iter_events_skips_malformed_lines(audit_file: Path) -> None:
    audit_file.write_text("not json\n{\"event\": \"ok\", \"detail\": \"d\", \"ts\": \"x\"}\n")
    events = list(iter_events(audit_file))
    assert len(events) == 1
    assert events[0]["event"] == "ok"


def test_recent_events_limits_output(audit_file: Path) -> None:
    for i in range(10):
        record_event("ev", str(i), path=audit_file)
    events = recent_events(n=4, path=audit_file)
    assert len(events) == 4
    assert events[-1]["detail"] == "9"


def test_prune_removes_old_lines(audit_file: Path) -> None:
    for i in range(20):
        record_event("ev", str(i), path=audit_file)
    removed = prune_audit_log(max_lines=10, path=audit_file)
    assert removed == 10
    remaining = list(iter_events(audit_file))
    assert len(remaining) == 10
    assert remaining[0]["detail"] == "10"


def test_prune_noop_when_under_limit(audit_file: Path) -> None:
    for i in range(5):
        record_event("ev", str(i), path=audit_file)
    removed = prune_audit_log(max_lines=100, path=audit_file)
    assert removed == 0
