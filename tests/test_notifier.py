"""Tests for cronwatch.notifier."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import AlertConfig
from cronwatch.notifier import log_alert, send_email_alert


@pytest.fixture()
def alert_cfg():
    return AlertConfig(
        email=["ops@example.com"],
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_from="cronwatch@example.com",
        smtp_tls=True,
    )


def test_send_email_no_recipients_returns_false():
    cfg = AlertConfig(email=[])
    result = send_email_alert(cfg, "backup", "failed")
    assert result is False


def test_send_email_success(alert_cfg):
    mock_server = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        result = send_email_alert(alert_cfg, "backup", "missed run", details="last seen 2h ago")

    assert result is True


def test_send_email_uses_starttls_when_configured(alert_cfg):
    mock_server = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        send_email_alert(alert_cfg, "backup", "failed")

    mock_server.starttls.assert_called_once()


def test_send_email_no_tls_skips_starttls():
    cfg = AlertConfig(email=["ops@example.com"], smtp_tls=False)
    mock_server = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        send_email_alert(cfg, "backup", "failed")

    mock_server.starttls.assert_not_called()


def test_send_email_smtp_error_returns_false(alert_cfg):
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("connection refused")):
        result = send_email_alert(alert_cfg, "backup", "failed")

    assert result is False


def test_send_email_connects_to_configured_host_and_port(alert_cfg):
    """Verify that send_email_alert passes the configured smtp_host and smtp_port to SMTP."""
    mock_server = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        send_email_alert(alert_cfg, "backup", "failed")

    mock_smtp_cls.assert_called_once_with("smtp.example.com", 587)


def test_log_alert_does_not_raise(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="cronwatch.notifier"):
        log_alert("my_job", "missed run", details="expected at 02:00")

    assert "my_job" in caplog.text
    assert "missed run" in caplog.text
