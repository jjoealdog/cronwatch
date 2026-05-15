"""Configuration loading and dataclasses for cronwatch."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


@dataclass
class AlertConfig:
    email: List[str] = field(default_factory=list)
    smtp_host: Optional[str] = None
    smtp_port: int = 25
    smtp_from: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = False
    # how many consecutive failures before alerting
    failure_threshold: int = 1


@dataclass
class JobConfig:
    name: str
    schedule: str  # cron expression
    command: Optional[str] = None
    max_duration: Optional[int] = None  # seconds
    alert: Optional[AlertConfig] = None


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    default_alert: Optional[AlertConfig] = None
    state_file: str = "/var/lib/cronwatch/state.json"
    check_interval: int = 60  # seconds


def _parse_alert(data: dict) -> AlertConfig:
    return AlertConfig(
        email=data.get("email", []),
        smtp_host=data.get("smtp_host"),
        smtp_port=int(data.get("smtp_port", 25)),
        smtp_from=data.get("smtp_from"),
        smtp_user=data.get("smtp_user"),
        smtp_password=data.get("smtp_password"),
        smtp_tls=bool(data.get("smtp_tls", False)),
        failure_threshold=int(data.get("failure_threshold", 1)),
    )


def _parse_job(data: dict) -> JobConfig:
    alert = _parse_alert(data["alert"]) if "alert" in data else None
    return JobConfig(
        name=data["name"],
        schedule=data["schedule"],
        command=data.get("command"),
        max_duration=data.get("max_duration"),
        alert=alert,
    )


def load_config(path: str) -> CronwatchConfig:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    default_alert = _parse_alert(raw["default_alert"]) if "default_alert" in raw else None
    jobs = [_parse_job(j) for j in raw.get("jobs", [])]

    return CronwatchConfig(
        jobs=jobs,
        default_alert=default_alert,
        state_file=raw.get("state_file", "/var/lib/cronwatch/state.json"),
        check_interval=int(raw.get("check_interval", 60)),
    )
