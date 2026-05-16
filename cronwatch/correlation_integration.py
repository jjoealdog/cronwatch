"""Integration layer: wrap an alert function with correlation buffering."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from cronwatch.correlation import AlertCorrelator


class CorrelatedAlerter:
    """
    Buffers alert calls into correlation groups and flushes them
    as a single grouped notification.

    Usage::

        alerter = CorrelatedAlerter(alert_fn, window=30)
        alerter.ingest("backup", "exit code 1")
        alerter.ingest("sync", "exit code 1")
        alerter.flush()  # sends one combined alert
    """

    def __init__(
        self,
        alert_fn: Callable[[str, str], None],
        window: float = 60.0,
        state_file: Optional[Path] = None,
        group_key: str = "default",
    ) -> None:
        self._alert_fn = alert_fn
        self._group_key = group_key
        self._correlator = AlertCorrelator(state_file=state_file, window=window)

    def ingest(self, job_name: str, reason: str) -> None:
        """Buffer an alert for later grouped delivery."""
        self._correlator.ingest(job_name, reason, group_key=self._group_key)

    def flush(self) -> int:
        """Flush all pending groups; returns number of alerts sent."""
        return self._correlator.flush(self._alert_fn)

    def pending_count(self) -> int:
        """Number of active correlation groups not yet flushed."""
        return self._correlator.group_count()

    def reset(self) -> None:
        """Clear all buffered groups without sending."""
        self._correlator._groups.clear()
        self._correlator._save()


def build_correlated_alert_fn(
    alert_fn: Callable[[str, str], None],
    window: float = 60.0,
    state_file: Optional[Path] = None,
    group_key: str = "default",
    auto_flush: bool = True,
) -> Callable[[str, str], None]:
    """
    Return a drop-in alert function that ingests into a correlator.
    If *auto_flush* is True the group is flushed immediately (pass-through
    with grouping metadata).  Set to False to manage flushing manually.
    """
    alerter = CorrelatedAlerter(
        alert_fn, window=window, state_file=state_file, group_key=group_key
    )

    def _alert(job_name: str, reason: str) -> None:
        alerter.ingest(job_name, reason)
        if auto_flush:
            alerter.flush()

    _alert._alerter = alerter  # type: ignore[attr-defined]
    return _alert
