"""Tests for cronwatch.healthcheck."""

import json
import time
import urllib.request
from urllib.error import HTTPError

import pytest

from cronwatch.healthcheck import HealthCheckServer


@pytest.fixture()
def server():
    """Start a healthcheck server on an ephemeral-ish port and tear it down."""
    status_data = {"jobs": 3, "failures": 0}
    srv = HealthCheckServer(status_fn=lambda: status_data, host="127.0.0.1", port=19876)
    srv.start()
    # give the thread a moment to bind
    time.sleep(0.05)
    yield srv, status_data
    srv.stop()


def _get(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status, json.loads(resp.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_health_endpoint_returns_ok(server):
    srv, _ = server
    code, body = _get(f"{srv.url}/health")
    assert code == 200
    assert body == {"status": "ok"}


def test_status_endpoint_returns_status_fn_data(server):
    srv, status_data = server
    code, body = _get(f"{srv.url}/status")
    assert code == 200
    assert body["jobs"] == 3
    assert body["failures"] == 0


def test_unknown_path_returns_404(server):
    srv, _ = server
    code, body = _get(f"{srv.url}/nonexistent")
    assert code == 404
    assert "error" in body


def test_url_property(server):
    srv, _ = server
    assert srv.url == "http://127.0.0.1:19876"


def test_stop_is_idempotent():
    """Calling stop on a not-yet-started server should not raise."""
    srv = HealthCheckServer(status_fn=lambda: {}, port=19877)
    srv.stop()  # should be a no-op


def test_status_reflects_live_data():
    """status_fn is called on each request so data can change dynamically."""
    counter = {"n": 0}

    def dynamic_status():
        counter["n"] += 1
        return {"calls": counter["n"]}

    srv = HealthCheckServer(status_fn=dynamic_status, host="127.0.0.1", port=19878)
    srv.start()
    time.sleep(0.05)
    try:
        _, body1 = _get(f"{srv.url}/status")
        _, body2 = _get(f"{srv.url}/status")
        assert body2["calls"] > body1["calls"]
    finally:
        srv.stop()
