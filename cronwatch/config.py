"""Configuration loading and validation for cronwatch."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class AlertConfig:
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    on_failure: bool = True
    on_missed: bool = True


@dataclass
class JobConfig:
    name: str
    schedule: str  # cron expression, e.g. "0 * * * *"
    expected_interval_seconds: int = 3600
    alert_after_failures: int = 1
    command: Optional[str] = None
    alert: Optional[AlertConfig] = None


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    default_alert: Optional[AlertConfig] = None
    state_file: str = "/var/lib/cronwatch/state.json"
    log_level: str = "INFO"
    check_interval_seconds: int = 60


def _parse_alert(data: dict) -> AlertConfig:
    return AlertConfig(
        email=data.get("email"),
        webhook_url=data.get("webhook_url"),
        on_failure=data.get("on_failure", True),
        on_missed=data.get("on_missed", True),
    )


def _parse_job(data: dict) -> JobConfig:
    alert = _parse_alert(data["alert"]) if "alert" in data else None
    return JobConfig(
        name=data["name"],
        schedule=data["schedule"],
        expected_interval_seconds=data.get("expected_interval_seconds", 3600),
        alert_after_failures=data.get("alert_after_failures", 1),
        command=data.get("command"),
        alert=alert,
    )


def load_config(path: str) -> CronwatchConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with config_path.open() as fh:
        raw = yaml.safe_load(fh) or {}

    default_alert = _parse_alert(raw["default_alert"]) if "default_alert" in raw else None
    jobs = [_parse_job(j) for j in raw.get("jobs", [])]

    return CronwatchConfig(
        jobs=jobs,
        default_alert=default_alert,
        state_file=raw.get("state_file", "/var/lib/cronwatch/state.json"),
        log_level=raw.get("log_level", "INFO"),
        check_interval_seconds=raw.get("check_interval_seconds", 60),
    )
