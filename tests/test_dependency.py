"""Tests for cronwatch.dependency and cronwatch.dependency_integration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatch.dependency import (
    DependencyGraph,
    blocking_dependencies,
    build_graph,
)
from cronwatch.dependency_integration import (
    DependencyAwareChecker,
    build_dependency_alert_fn,
)


# ---------------------------------------------------------------------------
# DependencyGraph unit tests
# ---------------------------------------------------------------------------

def test_empty_graph_has_no_deps():
    g = DependencyGraph()
    assert g.dependencies_of("job_a") == []


def test_add_and_retrieve_deps():
    g = DependencyGraph()
    g.add("job_b", ["job_a"])
    assert g.dependencies_of("job_b") == ["job_a"]


def test_all_jobs_includes_both_sides():
    g = DependencyGraph()
    g.add("job_b", ["job_a"])
    assert {"job_a", "job_b"} == g.all_jobs()


def test_no_cycle_in_linear_chain():
    g = DependencyGraph()
    g.add("b", ["a"])
    g.add("c", ["b"])
    assert not g.has_cycle()


def test_cycle_detected():
    g = DependencyGraph()
    g.add("a", ["b"])
    g.add("b", ["a"])
    assert g.has_cycle()


def test_blocking_dependencies_returns_unmet():
    g = DependencyGraph()
    g.add("job_b", ["job_a", "job_c"])
    blocked = blocking_dependencies("job_b", g, successful_jobs={"job_a"})
    assert blocked == ["job_c"]


def test_blocking_dependencies_empty_when_all_met():
    g = DependencyGraph()
    g.add("job_b", ["job_a"])
    assert blocking_dependencies("job_b", g, successful_jobs={"job_a"}) == []


# ---------------------------------------------------------------------------
# build_graph
# ---------------------------------------------------------------------------

def test_build_graph_from_config():
    job_a = MagicMock(name="job_a", spec=["name", "depends_on"])
    job_a.name = "job_a"
    job_a.depends_on = []

    job_b = MagicMock(name="job_b", spec=["name", "depends_on"])
    job_b.name = "job_b"
    job_b.depends_on = ["job_a"]

    cfg = MagicMock()
    cfg.jobs = [job_a, job_b]

    graph = build_graph(cfg)
    assert graph.dependencies_of("job_b") == ["job_a"]
    assert graph.dependencies_of("job_a") == []


# ---------------------------------------------------------------------------
# DependencyAwareChecker
# ---------------------------------------------------------------------------

@pytest.fixture()
def _setup():
    job_a = MagicMock(spec=["name", "depends_on"])
    job_a.name = "job_a"
    job_a.depends_on = []

    job_b = MagicMock(spec=["name", "depends_on"])
    job_b.name = "job_b"
    job_b.depends_on = ["job_a"]

    cfg = MagicMock()
    cfg.jobs = [job_a, job_b]

    state_ok = MagicMock(last_status="success")
    state_fail = MagicMock(last_status="failure")

    tracker = MagicMock()
    tracker.get = lambda name: state_ok if name == "job_a" else state_fail

    alert_fn = MagicMock()
    return cfg, tracker, alert_fn


def test_alert_fires_when_deps_satisfied(_setup):
    cfg, tracker, alert_fn = _setup
    checker = DependencyAwareChecker(cfg, tracker, alert_fn)
    checker.alert("job_b", "missed run")
    alert_fn.assert_called_once_with("job_b", "missed run")


def test_alert_suppressed_when_dep_not_succeeded(_setup):
    cfg, tracker, alert_fn = _setup
    # make job_a unsuccessful
    tracker.get = lambda name: MagicMock(last_status="failure")
    checker = DependencyAwareChecker(cfg, tracker, alert_fn)
    checker.alert("job_b", "missed run")
    alert_fn.assert_not_called()


def test_build_dependency_alert_fn_returns_callable(_setup):
    cfg, tracker, alert_fn = _setup
    fn = build_dependency_alert_fn(cfg, tracker, alert_fn)
    assert callable(fn)
