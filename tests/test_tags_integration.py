"""Tests for cronwatch.tags_integration."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from cronwatch.tags_integration import TagFilteredAlerter, build_tag_alert_fn


def _job(name: str, tags: list[str]):
    return SimpleNamespace(name=name, tags=tags)


JOBS = [
    _job("backup", ["critical", "nightly"]),
    _job("report", ["nightly", "reporting"]),
    _job("cleanup", ["maintenance"]),
]


def test_alert_passes_through_when_no_filters():
    fn = MagicMock()
    alerter = TagFilteredAlerter(fn, JOBS)
    alerter("backup", "failed")
    fn.assert_called_once_with("backup", "failed")
    assert alerter.delivered == 1
    assert alerter.suppressed == 0


def test_alert_suppressed_when_job_excluded():
    fn = MagicMock()
    alerter = TagFilteredAlerter(fn, JOBS, exclude=["maintenance"])
    alerter("cleanup", "failed")
    fn.assert_not_called()
    assert alerter.suppressed == 1
    assert alerter.delivered == 0


def test_alert_passes_when_job_included():
    fn = MagicMock()
    alerter = TagFilteredAlerter(fn, JOBS, include=["critical"])
    alerter("backup", "failed")
    fn.assert_called_once()
    assert alerter.delivered == 1


def test_alert_suppressed_when_job_not_in_include():
    fn = MagicMock()
    alerter = TagFilteredAlerter(fn, JOBS, include=["critical"])
    alerter("report", "failed")  # report is nightly/reporting, not critical
    fn.assert_not_called()
    assert alerter.suppressed == 1


def test_unknown_job_passes_through():
    """Jobs not in the list are never silently dropped."""
    fn = MagicMock()
    alerter = TagFilteredAlerter(fn, JOBS, include=["critical"])
    alerter("unknown-job", "oops")
    fn.assert_called_once_with("unknown-job", "oops")
    assert alerter.delivered == 1


def test_build_tag_alert_fn_returns_alerter():
    fn = MagicMock()
    alerter = build_tag_alert_fn(fn, JOBS, include=["nightly"])
    assert isinstance(alerter, TagFilteredAlerter)
    alerter("backup", "msg")
    fn.assert_called_once()
