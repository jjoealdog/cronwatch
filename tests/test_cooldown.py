"""Tests for cronwatch.cooldown and cronwatch.cooldown_integration."""

import time
import pytest
from pathlib import Path

from cronwatch.cooldown import AlertCooldown, CooldownEntry
from cronwatch.cooldown_integration import CooldownAlerter, build_cooldown_alert_fn


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "cooldown.json"


@pytest.fixture
def cooldown(state_file):
    return AlertCooldown(state_file, default_window=60)


# --- CooldownEntry unit tests ---

def test_entry_is_cooling_within_window():
    now = time.time()
    entry = CooldownEntry(last_alerted=now - 10, window_seconds=60)
    assert entry.is_cooling(now=now) is True


def test_entry_not_cooling_after_window():
    now = time.time()
    entry = CooldownEntry(last_alerted=now - 120, window_seconds=60)
    assert entry.is_cooling(now=now) is False


def test_entry_roundtrip():
    entry = CooldownEntry(last_alerted=1234567890.0, window_seconds=300)
    restored = CooldownEntry.from_dict(entry.to_dict())
    assert restored.last_alerted == entry.last_alerted
    assert restored.window_seconds == entry.window_seconds


# --- AlertCooldown tests ---

def test_new_cooldown_not_cooling(cooldown):
    assert cooldown.is_cooling("backup") is False


def test_record_alert_makes_job_cooling(cooldown):
    now = time.time()
    cooldown.record_alert("backup", now=now)
    assert cooldown.is_cooling("backup", now=now) is True


def test_cooling_expires_after_window(cooldown):
    now = time.time()
    cooldown.record_alert("backup", window_seconds=30, now=now - 60)
    assert cooldown.is_cooling("backup", now=now) is False


def test_reset_clears_cooldown(cooldown):
    now = time.time()
    cooldown.record_alert("backup", now=now)
    cooldown.reset("backup")
    assert cooldown.is_cooling("backup", now=now) is False


def test_remaining_returns_positive_while_cooling(cooldown):
    now = time.time()
    cooldown.record_alert("backup", window_seconds=60, now=now)
    r = cooldown.remaining("backup", now=now)
    assert 0 < r <= 60


def test_remaining_returns_zero_when_not_cooling(cooldown):
    assert cooldown.remaining("nojob") == 0.0


def test_state_persists_across_instances(state_file):
    now = time.time()
    c1 = AlertCooldown(state_file, default_window=60)
    c1.record_alert("myjob", now=now)
    c2 = AlertCooldown(state_file, default_window=60)
    assert c2.is_cooling("myjob", now=now) is True


# --- CooldownAlerter integration tests ---

def test_alerter_delivers_first_alert(state_file):
    fn = lambda job, reason: True
    alerter = CooldownAlerter(fn, state_file, default_window=60)
    result = alerter.alert("job1", "failed")
    assert result is True
    assert alerter.delivered_count == 1
    assert alerter.suppressed_count == 0


def test_alerter_suppresses_second_alert(state_file):
    fn = lambda job, reason: True
    alerter = CooldownAlerter(fn, state_file, default_window=300)
    alerter.alert("job1", "failed")
    result = alerter.alert("job1", "failed again")
    assert result is False
    assert alerter.suppressed_count == 1


def test_alerter_reset_allows_next_alert(state_file):
    fn = lambda job, reason: True
    alerter = CooldownAlerter(fn, state_file, default_window=300)
    alerter.alert("job1", "failed")
    alerter.reset("job1")
    result = alerter.alert("job1", "failed again")
    assert result is True
    assert alerter.delivered_count == 2


def test_build_cooldown_alert_fn_returns_callable(state_file):
    fn = lambda job, reason: True
    alerter = build_cooldown_alert_fn(fn, state_file)
    assert callable(alerter)
