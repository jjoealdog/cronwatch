"""Tests for cronwatch.history."""

import json
import pytest

from cronwatch.history import (
    append_run,
    iter_runs,
    recent_runs,
    failure_streak,
)


@pytest.fixture
def hist(tmp_path):
    return str(tmp_path / "history.jsonl")


def test_append_creates_file(hist):
    append_run(hist, "backup", success=True)
    import os
    assert os.path.exists(hist)


def test_append_and_iter(hist):
    append_run(hist, "backup", success=True, exit_code=0, duration_seconds=1.2)
    append_run(hist, "backup", success=False, exit_code=1)
    append_run(hist, "other", success=True)

    all_records = list(iter_runs(hist))
    assert len(all_records) == 3

    backup_records = list(iter_runs(hist, "backup"))
    assert len(backup_records) == 2
    assert backup_records[0]["success"] is True
    assert backup_records[1]["exit_code"] == 1


def test_iter_missing_file_yields_nothing(hist):
    records = list(iter_runs(hist))
    assert records == []


def test_iter_skips_malformed_lines(hist, tmp_path):
    path = tmp_path / "history.jsonl"
    path.write_text("not json\n{\"job\": \"x\", \"success\": true}\n")
    records = list(iter_runs(str(path)))
    assert len(records) == 1
    assert records[0]["job"] == "x"


def test_recent_runs_returns_last_n(hist):
    for i in range(15):
        append_run(hist, "myjob", success=(i % 3 != 0))
    runs = recent_runs(hist, "myjob", limit=5)
    assert len(runs) == 5


def test_recent_runs_empty_when_no_history(hist):
    assert recent_runs(hist, "ghost") == []


def test_failure_streak_all_failures(hist):
    for _ in range(4):
        append_run(hist, "job", success=False)
    assert failure_streak(hist, "job") == 4


def test_failure_streak_reset_by_success(hist):
    append_run(hist, "job", success=False)
    append_run(hist, "job", success=False)
    append_run(hist, "job", success=True)
    append_run(hist, "job", success=False)
    assert failure_streak(hist, "job") == 1


def test_failure_streak_zero_on_clean_history(hist):
    append_run(hist, "job", success=True)
    append_run(hist, "job", success=True)
    assert failure_streak(hist, "job") == 0


def test_record_contains_timestamp(hist):
    append_run(hist, "ts_job", success=True)
    records = list(iter_runs(hist, "ts_job"))
    assert "ts" in records[0]
    assert records[0]["ts"].endswith("+00:00") or "Z" in records[0]["ts"] or "T" in records[0]["ts"]
