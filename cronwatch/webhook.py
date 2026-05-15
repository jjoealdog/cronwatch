"""Webhook alert delivery for cronwatch."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from cronwatch.config import AlertConfig

log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 10


def _build_payload(job_name: str, event: str, detail: str) -> dict[str, Any]:
    return {
        "source": "cronwatch",
        "job": job_name,
        "event": event,
        "detail": detail,
    }


def send_webhook(
    cfg: AlertConfig,
    job_name: str,
    event: str,
    detail: str,
    *,
    timeout: int = _DEFAULT_TIMEOUT,
) -> bool:
    """POST a JSON payload to every webhook URL in *cfg*.

    Returns True if at least one delivery succeeded.
    """
    urls: list[str] = getattr(cfg, "webhook_urls", []) or []
    if not urls:
        log.debug("No webhook URLs configured – skipping")
        return False

    payload = json.dumps(_build_payload(job_name, event, detail)).encode()
    headers = {"Content-Type": "application/json"}
    success = False

    for url in urls:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                status = resp.status
            log.info("Webhook delivered to %s (HTTP %s)", url, status)
            success = True
        except urllib.error.URLError as exc:
            log.warning("Webhook delivery failed for %s: %s", url, exc)

    return success
