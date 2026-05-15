"""Tests for cronwatch.webhook."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import AlertConfig
from cronwatch.webhook import _build_payload, send_webhook


@pytest.fixture()
def alert_cfg() -> AlertConfig:
    return AlertConfig(
        from_addr="cw@example.com",
        smtp_host="localhost",
        smtp_port=25,
        webhook_urls=["https://hooks.example.com/test"],
    )


def test_build_payload_keys():
    p = _build_payload("myjob", "failure", "exit 1")
    assert p["source"] == "cronwatch"
    assert p["job"] == "myjob"
    assert p["event"] == "failure"
    assert p["detail"] == "exit 1"


def test_send_webhook_no_urls_returns_false():
    cfg = AlertConfig(from_addr="x@x.com", smtp_host="localhost", smtp_port=25)
    assert send_webhook(cfg, "job", "failure", "detail") is False


def test_send_webhook_success(alert_cfg):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200

    with patch("cronwatch.webhook.urllib.request.urlopen", return_value=mock_resp) as mock_open:
        result = send_webhook(alert_cfg, "backup", "failure", "exit 1")

    assert result is True
    mock_open.assert_called_once()
    req = mock_open.call_args[0][0]
    body = json.loads(req.data)
    assert body["job"] == "backup"


def test_send_webhook_url_error_returns_false(alert_cfg):
    import urllib.error

    with patch(
        "cronwatch.webhook.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        result = send_webhook(alert_cfg, "backup", "failure", "exit 1")

    assert result is False


def test_send_webhook_partial_success():
    """If one URL fails and another succeeds, overall result is True."""
    import urllib.error

    cfg = AlertConfig(
        from_addr="x@x.com",
        smtp_host="localhost",
        smtp_port=25,
        webhook_urls=["https://bad.example.com", "https://good.example.com"],
    )

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200

    call_count = 0

    def _side_effect(req, timeout):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise urllib.error.URLError("bad")
        return mock_resp

    with patch("cronwatch.webhook.urllib.request.urlopen", side_effect=_side_effect):
        result = send_webhook(cfg, "job", "missed", "no marker")

    assert result is True
    assert call_count == 2
