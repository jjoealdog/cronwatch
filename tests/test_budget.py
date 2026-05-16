"""Tests for cronwatch.budget."""
import time
from pathlib import Path

import pytest

from cronwatch.budget import AlertBudget, BudgetEntry


@pytest.fixture
def budget(tmp_path):
    return AlertBudget(state_file=tmp_path / "budget.json", window_seconds=60, max_alerts=3)


def test_new_budget_not_exhausted(budget):
    assert not budget.is_exhausted("job_a")


def test_remaining_starts_at_max(budget):
    assert budget.remaining("job_a") == 3


def test_record_decrements_remaining(budget):
    budget.record("job_a")
    assert budget.remaining("job_a") == 2


def test_exhausted_after_max_records(budget):
    for _ in range(3):
        budget.record("job_a")
    assert budget.is_exhausted("job_a")


def test_remaining_zero_when_exhausted(budget):
    for _ in range(3):
        budget.record("job_a")
    assert budget.remaining("job_a") == 0


def test_different_jobs_are_independent(budget):
    for _ in range(3):
        budget.record("job_a")
    assert not budget.is_exhausted("job_b")


def test_reset_clears_budget(budget):
    for _ in range(3):
        budget.record("job_a")
    budget.reset("job_a")
    assert not budget.is_exhausted("job_a")
    assert budget.remaining("job_a") == 3


def test_state_persists_across_instances(tmp_path):
    path = tmp_path / "budget.json"
    b1 = AlertBudget(state_file=path, window_seconds=60, max_alerts=3)
    b1.record("job_a")
    b1.record("job_a")

    b2 = AlertBudget(state_file=path, window_seconds=60, max_alerts=3)
    assert b2.remaining("job_a") == 1


def test_old_timestamps_are_pruned():
    entry = BudgetEntry(job="x", window_seconds=1, max_alerts=2)
    entry.timestamps.append(time.time() - 10)  # expired
    assert not entry.is_exhausted()
    assert entry.remaining() == 2


def test_entry_roundtrip():
    entry = BudgetEntry(job="y", window_seconds=300, max_alerts=5, timestamps=[1.0, 2.0])
    restored = BudgetEntry.from_dict(entry.to_dict())
    assert restored.job == "y"
    assert restored.window_seconds == 300
    assert restored.max_alerts == 5
    assert restored.timestamps == [1.0, 2.0]
