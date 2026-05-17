"""Tests for cronwatch.routing and cronwatch.routing_integration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatch.routing import AlertRouter, Route
from cronwatch.routing_integration import build_router


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _fn(returns=True):
    m = MagicMock(return_value=returns)
    return m


# ---------------------------------------------------------------------------
# Route.matches
# ---------------------------------------------------------------------------

def test_route_matches_wildcard_pattern():
    r = Route(name="r", job_patterns=["backup_*"], tags=[], alert_fn=_fn())
    assert r.matches("backup_daily")
    assert not r.matches("report_daily")


def test_route_matches_exact_pattern():
    r = Route(name="r", job_patterns=["nightly"], tags=[], alert_fn=_fn())
    assert r.matches("nightly")
    assert not r.matches("nightly_extra")


def test_route_no_patterns_matches_any_job():
    r = Route(name="r", job_patterns=[], tags=[], alert_fn=_fn())
    assert r.matches("anything")


def test_route_tag_filter_requires_matching_tag():
    r = Route(name="r", job_patterns=[], tags=["critical"], alert_fn=_fn())
    assert r.matches("job", job_tags=["critical", "prod"])
    assert not r.matches("job", job_tags=["dev"])
    assert not r.matches("job", job_tags=[])


def test_route_tag_match_is_case_insensitive():
    r = Route(name="r", job_patterns=[], tags=["Critical"], alert_fn=_fn())
    assert r.matches("job", job_tags=["critical"])


# ---------------------------------------------------------------------------
# AlertRouter
# ---------------------------------------------------------------------------

def test_router_dispatches_to_matching_route():
    fn = _fn()
    route = Route(name="r", job_patterns=["myjob"], tags=[], alert_fn=fn)
    router = AlertRouter(routes=[route])
    result = router.alert("myjob", "failed", "oh no")
    assert result is True
    fn.assert_called_once_with("myjob", "failed", "oh no")


def test_router_falls_back_to_default_when_no_match():
    default = _fn()
    router = AlertRouter(default_fn=default)
    result = router.alert("unknown_job", "failed", "msg")
    assert result is True
    default.assert_called_once()


def test_router_drops_when_no_match_and_no_default():
    router = AlertRouter()
    result = router.alert("job", "reason", "msg")
    assert result is False
    assert router.dropped == 1


def test_router_dispatches_to_multiple_matching_routes():
    fn1, fn2 = _fn(), _fn()
    r1 = Route(name="r1", job_patterns=["job"], tags=[], alert_fn=fn1)
    r2 = Route(name="r2", job_patterns=["job"], tags=[], alert_fn=fn2)
    router = AlertRouter(routes=[r1, r2])
    router.alert("job", "r", "m")
    fn1.assert_called_once()
    fn2.assert_called_once()


def test_router_tracks_delivered_and_dropped():
    fn_ok = _fn(True)
    fn_fail = _fn(False)
    r1 = Route(name="r1", job_patterns=["a"], tags=[], alert_fn=fn_ok)
    r2 = Route(name="r2", job_patterns=["a"], tags=[], alert_fn=fn_fail)
    router = AlertRouter(routes=[r1, r2])
    router.alert("a", "r", "m")
    assert router.delivered == 1
    assert router.dropped == 1


def test_router_reset_counters():
    fn = _fn()
    router = AlertRouter(routes=[Route("r", ["j"], [], fn)])
    router.alert("j", "r", "m")
    router.reset_counters()
    assert router.delivered == 0
    assert router.dropped == 0


# ---------------------------------------------------------------------------
# build_router integration helper
# ---------------------------------------------------------------------------

def test_build_router_creates_routes_from_specs():
    fn = _fn()
    named = {"email": fn}
    specs = [{"name": "critical-route", "job_patterns": ["backup_*"], "tags": [], "alert": "email"}]
    router = build_router(named, specs)
    result = router.alert("backup_daily", "failed", "msg")
    assert result is True
    fn.assert_called_once()


def test_build_router_skips_unknown_alert_fn(caplog):
    specs = [{"name": "bad", "job_patterns": ["*"], "alert": "nonexistent"}]
    router = build_router({}, specs)
    # no routes added — falls through to no-default drop
    result = router.alert("job", "r", "m")
    assert result is False
