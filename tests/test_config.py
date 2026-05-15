"""Tests for cronwatch configuration loading."""

import os
import pytest
import tempfile
import yaml

from cronwatch.config import load_config, CronwatchConfig, JobConfig, AlertConfig


MINIMAL_CONFIG = {
    "jobs": [
        {
            "name": "test_job",
            "schedule": "* * * * *",
            "command": "/bin/true",
        }
    ]
}

FULL_CONFIG = {
    "log_file": "/tmp/cronwatch.log",
    "state_dir": "/tmp/cronwatch",
    "check_interval": 30,
    "alerts": {
        "email": "admin@example.com",
        "slack_webhook": "https://hooks.slack.com/xxx",
        "smtp_host": "mail.example.com",
        "smtp_port": 587,
        "smtp_from": "cron@example.com",
    },
    "jobs": [
        {
            "name": "job_one",
            "schedule": "0 * * * *",
            "command": "/bin/job1.sh",
            "timeout": 120,
            "alert_on_failure": True,
            "alert_on_missed": False,
            "notify": ["dev@example.com"],
        }
    ],
}


@pytest.fixture
def config_file(tmp_path):
    def _write(data):
        p = tmp_path / "cronwatch.yaml"
        p.write_text(yaml.dump(data))
        return str(p)
    return _write


def test_load_minimal_config(config_file):
    cfg = load_config(config_file(MINIMAL_CONFIG))
    assert isinstance(cfg, CronwatchConfig)
    assert len(cfg.jobs) == 1
    assert cfg.jobs[0].name == "test_job"
    assert cfg.jobs[0].timeout == 3600  # default
    assert cfg.check_interval == 60    # default


def test_load_full_config(config_file):
    cfg = load_config(config_file(FULL_CONFIG))
    assert cfg.log_file == "/tmp/cronwatch.log"
    assert cfg.check_interval == 30
    assert cfg.alerts.email == "admin@example.com"
    assert cfg.alerts.smtp_port == 587
    assert cfg.jobs[0].timeout == 120
    assert cfg.jobs[0].alert_on_missed is False
    assert "dev@example.com" in cfg.jobs[0].notify


def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/cronwatch.yaml")


def test_empty_config_file(config_file):
    p = config_file({})
    # overwrite with truly empty file
    with open(p, "w") as f:
        f.write("")
    cfg = load_config(p)
    assert cfg.jobs == []
    assert cfg.alerts.email is None


def test_job_defaults(config_file):
    cfg = load_config(config_file(MINIMAL_CONFIG))
    job = cfg.jobs[0]
    assert job.alert_on_failure is True
    assert job.alert_on_missed is True
    assert job.notify == []
