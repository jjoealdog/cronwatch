"""Tests for cronwatch.retention pruning helpers."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cronwatch.retention import prune_by_age, prune_by_count, prune_job


JOB = "backup"


@pytest.fixture()
def hist(tmp_path):
    return str(tmp_path)


def _write_runs(hist_dir: str, job: str, entries: list[dict]) -> None:
    path = Path(hist_dir) / f"{job}.jsonl"
    with open(path, "w") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


def _ts(days_ago: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


def _read_runs(hist_dir: str, job: str) -> list[dict]:
    from cronwatch.history import iter_runs
    return list(iter_runs(hist_dir, job))


# ---------------------------------------------------------------------------

def test_prune_by_age_removes_old_entries(hist):
    entries = [
        {"timestamp": _ts(10), "status": "success"},
        {"timestamp": _ts(5), "status": "success"},
        {"timestamp": _ts(1), "status": "success"},
    ]
    _write_runs(hist, JOB, entries)

    removed = prune_by_age(hist, JOB, max_age_days=7)

    assert removed == 1
    remaining = _read_runs(hist, JOB)
    assert len(remaining) == 2
    assert all(r["timestamp"] in (_ts(5), _ts(1)) for r in remaining)


def test_prune_by_age_nothing_to_remove(hist):
    entries = [{"timestamp": _ts(1), "status": "success"}]
    _write_runs(hist, JOB, entries)

    removed = prune_by_age(hist, JOB, max_age_days=30)

    assert removed == 0
    assert len(_read_runs(hist, JOB)) == 1


def test_prune_by_count_keeps_most_recent(hist):
    entries = [
        {"timestamp": _ts(9), "status": "success"},
        {"timestamp": _ts(6), "status": "success"},
        {"timestamp": _ts(3), "status": "failure"},
        {"timestamp": _ts(1), "status": "success"},
    ]
    _write_runs(hist, JOB, entries)

    removed = prune_by_count(hist, JOB, max_count=2)

    assert removed == 2
    remaining = _read_runs(hist, JOB)
    assert len(remaining) == 2
    assert remaining[-1]["timestamp"] == _ts(1)


def test_prune_by_count_no_op_when_under_limit(hist):
    entries = [{"timestamp": _ts(1), "status": "success"}]
    _write_runs(hist, JOB, entries)

    removed = prune_by_count(hist, JOB, max_count=10)

    assert removed == 0


def test_prune_job_combines_both_strategies(hist):
    entries = [
        {"timestamp": _ts(20), "status": "success"},
        {"timestamp": _ts(10), "status": "success"},
        {"timestamp": _ts(2), "status": "success"},
        {"timestamp": _ts(1), "status": "failure"},
    ]
    _write_runs(hist, JOB, entries)

    result = prune_job(hist, JOB, max_age_days=15, max_count=1)

    assert result["job"] == JOB
    assert result["removed_by_age"] == 1   # entry at day 20
    assert result["removed_by_count"] == 2  # keeps only 1 of the remaining 3
    assert len(_read_runs(hist, JOB)) == 1


def test_prune_missing_history_file_is_safe(hist):
    removed = prune_by_age(hist, "nonexistent", max_age_days=7)
    assert removed == 0
