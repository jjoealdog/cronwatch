"""Tests for cronwatch.circuit_breaker."""

import json
import time
from pathlib import Path

import pytest

from cronwatch.circuit_breaker import CircuitBreaker, _CLOSED, _OPEN, _HALF_OPEN


@pytest.fixture
def cb(tmp_path):
    return CircuitBreaker(
        state_file=tmp_path / "cb.json",
        failure_threshold=3,
        recovery_timeout=60.0,
    )


def test_new_breaker_is_closed(cb):
    assert cb.state("email") == _CLOSED
    assert not cb.is_open("email")


def test_failures_below_threshold_stay_closed(cb):
    cb.record_failure("email")
    cb.record_failure("email")
    assert cb.state("email") == _CLOSED
    assert not cb.is_open("email")


def test_failures_at_threshold_open_circuit(cb):
    for _ in range(3):
        cb.record_failure("email")
    assert cb.state("email") == _OPEN
    assert cb.is_open("email")


def test_success_resets_failure_count(cb):
    cb.record_failure("email")
    cb.record_failure("email")
    cb.record_success("email")
    assert cb.state("email") == _CLOSED
    assert cb._entry("email").failure_count == 0


def test_different_channels_are_independent(cb):
    for _ in range(3):
        cb.record_failure("email")
    assert cb.is_open("email")
    assert not cb.is_open("slack")


def test_open_circuit_transitions_to_half_open_after_timeout(tmp_path):
    cb = CircuitBreaker(
        state_file=tmp_path / "cb.json",
        failure_threshold=2,
        recovery_timeout=0.05,
    )
    cb.record_failure("email")
    cb.record_failure("email")
    assert cb.is_open("email")
    time.sleep(0.1)
    assert not cb.is_open("email")
    assert cb.state("email") == _HALF_OPEN


def test_state_persisted_to_file(tmp_path):
    path = tmp_path / "cb.json"
    cb1 = CircuitBreaker(state_file=path, failure_threshold=2)
    cb1.record_failure("email")
    cb1.record_failure("email")

    cb2 = CircuitBreaker(state_file=path, failure_threshold=2)
    assert cb2.is_open("email")


def test_reset_clears_channel(cb):
    for _ in range(3):
        cb.record_failure("email")
    cb.reset("email")
    assert cb.state("email") == _CLOSED
    assert not cb.is_open("email")


def test_corrupt_state_file_handled_gracefully(tmp_path):
    path = tmp_path / "cb.json"
    path.write_text("not json")
    cb = CircuitBreaker(state_file=path, failure_threshold=2)
    assert cb.state("email") == _CLOSED
