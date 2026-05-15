"""Integrates webhook delivery into the cronwatch alert pipeline."""

from __future__ import annotations

import logging
from typing import Callable

from cronwatch.config import AlertConfig
from cronwatch.webhook import send_webhook

log = logging.getLogger(__name__)


class WebhookAlerter:
    """Wraps *send_webhook* as a drop-in alert callable.

    Usage::

        alerter = WebhookAlerter(alert_cfg)
        alerter.alert("backup", "failure", "exit code 1")
    """

    def __init__(self, cfg: AlertConfig) -> None:
        self._cfg = cfg
        self.delivery_count: int = 0
        self.failure_count: int = 0

    # Compatible with the generic ``alert_fn(job, event, detail)`` signature
    # used throughout cronwatch.
    def alert(self, job_name: str, event: str, detail: str) -> bool:
        ok = send_webhook(self._cfg, job_name, event, detail)
        if ok:
            self.delivery_count += 1
        else:
            self.failure_count += 1
        return ok

    def reset_counters(self) -> None:
        self.delivery_count = 0
        self.failure_count = 0


def build_webhook_alert_fn(
    cfg: AlertConfig,
) -> Callable[[str, str, str], bool]:
    """Return a plain function that delivers webhook alerts."""
    alerter = WebhookAlerter(cfg)
    return alerter.alert
