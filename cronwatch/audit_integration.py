"""Thin integration layer — wires audit logging into scheduler / CLI events."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from cronwatch.audit import record_event


class AuditHook:
    """Wraps an alert callable and records every alert attempt in the audit log."""

    def __init__(
        self,
        inner_alert_fn: Callable[[str, str, str], bool],
        audit_path: Path | None = None,
        actor: str = "cronwatch",
    ) -> None:
        self._inner = inner_alert_fn
        self._path = audit_path
        self._actor = actor

    def alert(self, job_name: str, subject: str, body: str) -> bool:
        delivered = self._inner(job_name, subject, body)
        status = "delivered" if delivered else "failed"
        record_event(
            event_type="alert",
            detail=f"job={job_name!r} subject={subject!r} status={status}",
            path=self._path,
            actor=self._actor,
        )
        return delivered

    def __call__(self, job_name: str, subject: str, body: str) -> bool:
        return self.alert(job_name, subject, body)


def record_config_loaded(config_path: str, audit_path: Path | None = None) -> None:
    record_event(
        event_type="config_loaded",
        detail=f"path={config_path!r}",
        path=audit_path,
    )


def record_daemon_start(audit_path: Path | None = None) -> None:
    record_event(event_type="daemon_start", detail="cronwatch daemon started", path=audit_path)


def record_daemon_stop(audit_path: Path | None = None) -> None:
    record_event(event_type="daemon_stop", detail="cronwatch daemon stopped", path=audit_path)


def record_silence(job_name: str, duration_s: int, audit_path: Path | None = None) -> None:
    record_event(
        event_type="silence",
        detail=f"job={job_name!r} duration_s={duration_s}",
        path=audit_path,
    )
