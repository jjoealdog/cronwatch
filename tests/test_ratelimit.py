"""Tests for cronwatch.ratelimit."""

import time
import pytest
from pathlib import Path
from unittest.mock import patch

from cronwatch.ratelimit import RateLimitEntry, RateLimiter


@pytest.fixture
def limiter(tmp_path):
    return RateLimiter(
        state_path=tmp_path / "ratelimit.json",
        default_window=60,
        default_max=3,
    )


def test_new_limiter_allows_alert(limiter):
    assert limiter.check_and_record("backup") is True


def test_under_limit_allows_multiple_alerts(limiter):
    assert limiter.check_and_record("backup") is True
    assert limiter.check_and_record("backup") is True
    assert limiter.check_and_record("backup") is True


def test_exceeding_limit_suppresses_alert(limiter):
    limiter.check_and_record("backup")
    limiter.check_and_record("backup")
    limiter.check_and_record("backup")
    # 4th alert should be suppressed
    assert limiter.check_and_record("backup") is False


def test_different_jobs_are_independent(limiter):
    limiter.check_and_record("job_a")
    limiter.check_and_record("job_a")
    limiter.check_and_record("job_a")
    # job_a is now limited, but job_b should not be
    assert limiter.check_and_record("job_b") is True


def test_reset_clears_timestamps(limiter):
    limiter.check_and_record("backup")
    limiter.check_and_record("backup")
    limiter.check_and_record("backup")
    limiter.reset("backup")
    assert limiter.check_and_record("backup") is True


def test_expired_timestamps_are_pruned():
    entry = RateLimitEntry("job", window_seconds=1, max_alerts=2)
    old_time = time.time() - 10
    entry.timestamps = [old_time, old_time]
    # Old timestamps should be pruned, so not limited
    assert entry.is_limited() is False


def test_state_persists_across_instances(tmp_path):
    path = tmp_path / "rl.json"
    l1 = RateLimiter(state_path=path, default_window=60, default_max=2)
    l1.check_and_record("myjob")
    l1.check_and_record("myjob")

    l2 = RateLimiter(state_path=path, default_window=60, default_max=2)
    assert l2.check_and_record("myjob") is False


def test_no_path_does_not_persist():
    l = RateLimiter(state_path=None, default_window=60, default_max=2)
    l.check_and_record("job")
    l.check_and_record("job")
    # Should still work in memory
    assert l.check_and_record("job") is False


def test_malformed_state_file_is_ignored(tmp_path):
    path = tmp_path / "rl.json"
    path.write_text("not valid json")
    l = RateLimiter(state_path=path, default_window=60, default_max=3)
    assert l.check_and_record("job") is True
