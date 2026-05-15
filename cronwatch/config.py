"""Configuration loader for cronwatch."""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    command: str
    timeout: int = 3600
    alert_on_failure: bool = True
    alert_on_missed: bool = True
    notify: List[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    email: Optional[str] = None
    slack_webhook: Optional[str] = None
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_from: str = "cronwatch@localhost"


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    log_file: str = "/var/log/cronwatch.log"
    state_dir: str = "/var/lib/cronwatch"
    check_interval: int = 60


def load_config(path: str) -> CronwatchConfig:
    """Load and parse configuration from a YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raw = {}

    alert_raw = raw.get("alerts", {})
    alerts = AlertConfig(
        email=alert_raw.get("email"),
        slack_webhook=alert_raw.get("slack_webhook"),
        smtp_host=alert_raw.get("smtp_host", "localhost"),
        smtp_port=alert_raw.get("smtp_port", 25),
        smtp_from=alert_raw.get("smtp_from", "cronwatch@localhost"),
    )

    jobs = []
    for job_raw in raw.get("jobs", []):
        jobs.append(JobConfig(
            name=job_raw["name"],
            schedule=job_raw["schedule"],
            command=job_raw["command"],
            timeout=job_raw.get("timeout", 3600),
            alert_on_failure=job_raw.get("alert_on_failure", True),
            alert_on_missed=job_raw.get("alert_on_missed", True),
            notify=job_raw.get("notify", []),
        ))

    return CronwatchConfig(
        jobs=jobs,
        alerts=alerts,
        log_file=raw.get("log_file", "/var/log/cronwatch.log"),
        state_dir=raw.get("state_dir", "/var/lib/cronwatch"),
        check_interval=raw.get("check_interval", 60),
    )
