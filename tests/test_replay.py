"""Tests for cronwatch.replay."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cronwatch.replay import find_missed_runs, replay_alerts
from cronwatch.config import JobConfig, AlertConfig, CronwatchConfig


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _job(name: str = "backup") -> JobConfig:
    return JobConfig(name=name, schedule="0 * * * *", alert=AlertConfig())


def _cfg(*names: str) -> CronwatchConfig:
    alert = AlertConfig()
    jobs = [JobConfig(name=n, schedule="0 * * * *", alert=alert) for n in names]
    return CronwatchConfig(jobs=jobs, alert=alert)


def _write_run(history_dir: Path, job_name: str, ts: datetime, status: str, exit_code: int = 0):
    d = history_dir / job_name
    d.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": ts.isoformat(),
        "status": status,
        "exit_code": exit_code,
        "reason": "test failure" if status == "failure" else "",
    }
    with open(d / "runs.jsonl", "a") as fh:
        fh.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# find_missed_runs
# ---------------------------------------------------------------------------

def test_find_missed_runs_returns_failures_in_window(tmp_path):
    now = datetime.now(timezone.utc)
    _write_run(tmp_path, "backup", now - timedelta(hours=2), "failure", exit_code=1)
    _write_run(tmp_path, "backup", now - timedelta(hours=1), "success", exit_code=0)

    since = now - timedelta(hours=3)
    result = find_missed_runs(_job(), since, history_dir=str(tmp_path))
    assert len(result) == 1
    assert result[0]["status"] == "failure"


def test_find_missed_runs_excludes_outside_window(tmp_path):
    now = datetime.now(timezone.utc)
    _write_run(tmp_path, "backup", now - timedelta(hours=5), "failure", exit_code=1)

    since = now - timedelta(hours=3)
    result = find_missed_runs(_job(), since, history_dir=str(tmp_path))
    assert result == []


def test_find_missed_runs_empty_history(tmp_path):
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    result = find_missed_runs(_job(), since, history_dir=str(tmp_path))
    assert result == []


# ---------------------------------------------------------------------------
# replay_alerts
# ---------------------------------------------------------------------------

def test_replay_alerts_fires_for_each_failure(tmp_path):
    now = datetime.now(timezone.utc)
    _write_run(tmp_path, "backup", now - timedelta(hours=1), "failure", exit_code=2)
    _write_run(tmp_path, "backup", now - timedelta(minutes=30), "failure", exit_code=3)

    fired: list[tuple[str, str]] = []
    cfg = _cfg("backup")
    count = replay_alerts(cfg, lambda j, m: fired.append((j, m)),
                          since=now - timedelta(hours=2),
                          history_dir=str(tmp_path))
    assert count == 2
    assert all(j == "backup" for j, _ in fired)
    assert all("REPLAY" in m for _, m in fired)


def test_replay_dry_run_does_not_call_alert_fn(tmp_path):
    now = datetime.now(timezone.utc)
    _write_run(tmp_path, "nightly", now - timedelta(hours=1), "failure", exit_code=1)

    fired: list = []
    cfg = _cfg("nightly")
    count = replay_alerts(cfg, lambda j, m: fired.append((j, m)),
                          since=now - timedelta(hours=2),
                          history_dir=str(tmp_path),
                          dry_run=True)
    assert count == 1
    assert fired == []


def test_replay_returns_zero_when_no_failures(tmp_path):
    now = datetime.now(timezone.utc)
    _write_run(tmp_path, "sync", now - timedelta(hours=1), "success")

    cfg = _cfg("sync")
    count = replay_alerts(cfg, lambda j, m: None,
                          since=now - timedelta(hours=2),
                          history_dir=str(tmp_path))
    assert count == 0
