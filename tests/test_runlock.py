"""Tests for cronwatch.runlock and cronwatch.runlock_integration."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwatch import runlock
from cronwatch.runlock_integration import RunLockIntegration


@pytest.fixture()
def lock_dir(tmp_path: Path) -> Path:
    return tmp_path / "locks"


# ---------------------------------------------------------------------------
# runlock module
# ---------------------------------------------------------------------------


def test_acquire_creates_lock_file(lock_dir):
    assert runlock.acquire(lock_dir, "backup") is True
    assert _lock_path(lock_dir, "backup").exists()


def test_acquire_returns_false_for_live_duplicate(lock_dir):
    runlock.acquire(lock_dir, "backup", pid=os.getpid())
    assert runlock.acquire(lock_dir, "backup", pid=os.getpid()) is False


def test_acquire_clears_stale_lock(lock_dir):
    # Use a pid that is guaranteed dead (pid 1 won't raise, so use a bogus one)
    with patch.object(runlock, "_pid_alive", return_value=False):
        runlock.acquire(lock_dir, "backup", pid=99999)
        # Stale — second acquire should succeed
        assert runlock.acquire(lock_dir, "backup", pid=os.getpid()) is True


def test_release_removes_lock_file(lock_dir):
    runlock.acquire(lock_dir, "backup")
    assert runlock.release(lock_dir, "backup") is True
    assert not _lock_path(lock_dir, "backup").exists()


def test_release_returns_false_when_no_lock(lock_dir):
    assert runlock.release(lock_dir, "nonexistent") is False


def test_is_locked_true_for_live_lock(lock_dir):
    runlock.acquire(lock_dir, "myjob", pid=os.getpid())
    assert runlock.is_locked(lock_dir, "myjob") is True


def test_is_locked_false_after_release(lock_dir):
    runlock.acquire(lock_dir, "myjob")
    runlock.release(lock_dir, "myjob")
    assert runlock.is_locked(lock_dir, "myjob") is False


def test_lock_info_returns_metadata(lock_dir):
    runlock.acquire(lock_dir, "myjob", pid=42)
    info = runlock.lock_info(lock_dir, "myjob")
    assert info is not None
    assert info["job"] == "myjob"
    assert info["pid"] == 42


def test_lock_info_returns_none_when_absent(lock_dir):
    assert runlock.lock_info(lock_dir, "ghost") is None


# ---------------------------------------------------------------------------
# RunLockIntegration
# ---------------------------------------------------------------------------


def test_integration_acquire_success_no_alert(lock_dir):
    alerts = []
    rli = RunLockIntegration(lock_dir, lambda j, m: alerts.append((j, m)))
    assert rli.try_acquire("job1") is True
    assert alerts == []


def test_integration_duplicate_fires_alert(lock_dir):
    alerts = []
    rli = RunLockIntegration(lock_dir, lambda j, m: alerts.append((j, m)))
    rli.try_acquire("job1", pid=os.getpid())
    result = rli.try_acquire("job1", pid=os.getpid())
    assert result is False
    assert rli.duplicate_count == 1
    assert any("job1" in j for j, _ in alerts)


def test_integration_no_alert_when_disabled(lock_dir):
    alerts = []
    rli = RunLockIntegration(
        lock_dir,
        lambda j, m: alerts.append((j, m)),
        alert_on_duplicate=False,
    )
    rli.try_acquire("job2", pid=os.getpid())
    rli.try_acquire("job2", pid=os.getpid())
    assert alerts == []
    assert rli.duplicate_count == 1


def test_integration_reset_counters(lock_dir):
    alerts = []
    rli = RunLockIntegration(lock_dir, lambda j, m: alerts.append((j, m)))
    rli.try_acquire("job3", pid=os.getpid())
    rli.try_acquire("job3", pid=os.getpid())
    rli.reset_counters()
    assert rli.duplicate_count == 0


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _lock_path(lock_dir: Path, job_name: str) -> Path:
    return lock_dir / f"{job_name}.lock"
