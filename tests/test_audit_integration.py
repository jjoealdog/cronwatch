"""Tests for cronwatch.audit_integration."""

from pathlib import Path

import pytest

from cronwatch.audit import iter_events
from cronwatch.audit_integration import (
    AuditHook,
    record_config_loaded,
    record_daemon_start,
    record_daemon_stop,
    record_silence,
)


@pytest.fixture()
def audit_file(tmp_path: Path) -> Path:
    return tmp_path / "audit.log"


def _make_alert_fn(succeed: bool = True):
    def _fn(job_name: str, subject: str, body: str) -> bool:
        return succeed
    return _fn


def test_audit_hook_records_delivered(audit_file: Path) -> None:
    hook = AuditHook(_make_alert_fn(True), audit_path=audit_file)
    result = hook("backup", "Failure", "body")
    assert result is True
    events = list(iter_events(audit_file))
    assert len(events) == 1
    assert events[0]["event"] == "alert"
    assert "delivered" in events[0]["detail"]


def test_audit_hook_records_failed_delivery(audit_file: Path) -> None:
    hook = AuditHook(_make_alert_fn(False), audit_path=audit_file)
    hook("nightly", "Missed", "body")
    events = list(iter_events(audit_file))
    assert "failed" in events[0]["detail"]


def test_audit_hook_uses_actor(audit_file: Path) -> None:
    hook = AuditHook(_make_alert_fn(), audit_path=audit_file, actor="test-actor")
    hook("job", "s", "b")
    events = list(iter_events(audit_file))
    assert events[0].get("actor") == "test-actor"


def test_record_config_loaded(audit_file: Path) -> None:
    record_config_loaded("/etc/cronwatch.yaml", audit_path=audit_file)
    events = list(iter_events(audit_file))
    assert events[0]["event"] == "config_loaded"
    assert "/etc/cronwatch.yaml" in events[0]["detail"]


def test_record_daemon_start_stop(audit_file: Path) -> None:
    record_daemon_start(audit_path=audit_file)
    record_daemon_stop(audit_path=audit_file)
    events = list(iter_events(audit_file))
    assert events[0]["event"] == "daemon_start"
    assert events[1]["event"] == "daemon_stop"


def test_record_silence(audit_file: Path) -> None:
    record_silence("backup", 3600, audit_path=audit_file)
    events = list(iter_events(audit_file))
    assert events[0]["event"] == "silence"
    assert "backup" in events[0]["detail"]
    assert "3600" in events[0]["detail"]
