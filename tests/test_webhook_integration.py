"""Tests for cronwatch.webhook_integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cronwatch.config import AlertConfig
from cronwatch.webhook_integration import WebhookAlerter, build_webhook_alert_fn


@pytest.fixture()
def cfg() -> AlertConfig:
    return AlertConfig(
        from_addr="cw@example.com",
        smtp_host="localhost",
        smtp_port=25,
        webhook_urls=["https://hooks.example.com/test"],
    )


def test_alerter_increments_delivery_count_on_success(cfg):
    alerter = WebhookAlerter(cfg)
    with patch("cronwatch.webhook_integration.send_webhook", return_value=True):
        alerter.alert("job", "failure", "detail")
    assert alerter.delivery_count == 1
    assert alerter.failure_count == 0


def test_alerter_increments_failure_count_on_error(cfg):
    alerter = WebhookAlerter(cfg)
    with patch("cronwatch.webhook_integration.send_webhook", return_value=False):
        alerter.alert("job", "failure", "detail")
    assert alerter.failure_count == 1
    assert alerter.delivery_count == 0


def test_reset_counters(cfg):
    alerter = WebhookAlerter(cfg)
    with patch("cronwatch.webhook_integration.send_webhook", return_value=True):
        alerter.alert("job", "failure", "detail")
    alerter.reset_counters()
    assert alerter.delivery_count == 0
    assert alerter.failure_count == 0


def test_build_webhook_alert_fn_returns_callable(cfg):
    fn = build_webhook_alert_fn(cfg)
    assert callable(fn)


def test_build_webhook_alert_fn_delivers(cfg):
    fn = build_webhook_alert_fn(cfg)
    with patch("cronwatch.webhook_integration.send_webhook", return_value=True) as mock_send:
        result = fn("myjob", "missed", "overdue by 10 min")
    assert result is True
    mock_send.assert_called_once_with(cfg, "myjob", "missed", "overdue by 10 min")
