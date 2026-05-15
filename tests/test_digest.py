"""Tests for cronwatch.digest."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.digest import DigestScheduler, build_digest_subject, send_digest
from cronwatch.tracker import JobTracker


@pytest.fixture()
def alert_cfg() -> AlertConfig:
    return AlertConfig(recipients=["ops@example.com"])


@pytest.fixture()
def cfg(alert_cfg: AlertConfig) -> CronwatchConfig:
    job = JobConfig(name="backup", schedule="0 2 * * *")
    return CronwatchConfig(alert=alert_cfg, jobs=[job])


@pytest.fixture()
def tracker() -> JobTracker:
    return JobTracker()


@pytest.fixture()
def alert_fn():
    return MagicMock()


_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_build_digest_subject_contains_timestamp():
    subject = build_digest_subject(MagicMock(), now=_NOW)
    assert "2024-06-15 12:00 UTC" in subject
    assert "cronwatch" in subject


def test_send_digest_no_jobs_returns_false(alert_fn):
    empty_cfg = CronwatchConfig(
        alert=AlertConfig(recipients=["a@b.com"]), jobs=[]
    )
    result = send_digest(empty_cfg, JobTracker(), alert_fn)
    assert result is False
    alert_fn.assert_not_called()


def test_send_digest_calls_alert_fn(cfg, tracker, alert_fn):
    with patch("cronwatch.digest.full_report", return_value="report body") as mock_report:
        result = send_digest(cfg, tracker, alert_fn, now=_NOW)

    assert result is True
    alert_fn.assert_called_once()
    subject, body = alert_fn.call_args[0]
    assert "cronwatch" in subject
    assert body == "report body"
    mock_report.assert_called_once_with(cfg, tracker, history_dir="history")


def test_digest_scheduler_sends_on_first_call(cfg, tracker, alert_fn):
    ds = DigestScheduler(cfg, tracker, alert_fn, interval_seconds=3600)
    with patch("cronwatch.digest.full_report", return_value="r"):
        result = ds.run_once(now=_NOW)
    assert result is True
    alert_fn.assert_called_once()


def test_digest_scheduler_skips_before_interval(cfg, tracker, alert_fn):
    ds = DigestScheduler(cfg, tracker, alert_fn, interval_seconds=3600)
    t1 = _NOW
    t2 = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc)  # +30 min

    with patch("cronwatch.digest.full_report", return_value="r"):
        ds.run_once(now=t1)   # first send
        result = ds.run_once(now=t2)  # too soon

    assert result is False
    assert alert_fn.call_count == 1


def test_digest_scheduler_sends_after_interval(cfg, tracker, alert_fn):
    ds = DigestScheduler(cfg, tracker, alert_fn, interval_seconds=3600)
    t1 = _NOW
    t2 = datetime(2024, 6, 15, 13, 1, 0, tzinfo=timezone.utc)  # +61 min

    with patch("cronwatch.digest.full_report", return_value="r"):
        ds.run_once(now=t1)
        result = ds.run_once(now=t2)

    assert result is True
    assert alert_fn.call_count == 2
