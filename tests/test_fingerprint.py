"""Tests for cronwatch.fingerprint."""

from __future__ import annotations

import json
import os
import time

import pytest

from cronwatch.fingerprint import FingerprintStore, make_fingerprint


# ---------------------------------------------------------------------------
# make_fingerprint
# ---------------------------------------------------------------------------

def test_make_fingerprint_is_deterministic():
    a = make_fingerprint("backup", "failed")
    b = make_fingerprint("backup", "failed")
    assert a == b


def test_make_fingerprint_differs_by_job():
    assert make_fingerprint("job_a", "failed") != make_fingerprint("job_b", "failed")


def test_make_fingerprint_differs_by_reason():
    assert make_fingerprint("job", "failed") != make_fingerprint("job", "missed")


def test_make_fingerprint_is_hex_string():
    fp = make_fingerprint("job", "reason")
    assert isinstance(fp, str)
    int(fp, 16)  # should not raise


# ---------------------------------------------------------------------------
# FingerprintStore
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    return FingerprintStore(str(tmp_path / "fp.json"), ttl_seconds=60.0)


def test_new_store_not_seen(store):
    assert not store.is_seen("abc123")


def test_mark_seen_makes_it_seen(store):
    fp = make_fingerprint("job", "failed")
    store.mark_seen(fp)
    assert store.is_seen(fp)


def test_mark_seen_persists_to_disk(tmp_path):
    path = str(tmp_path / "fp.json")
    s1 = FingerprintStore(path, ttl_seconds=60.0)
    fp = make_fingerprint("job", "failed")
    s1.mark_seen(fp)

    s2 = FingerprintStore(path, ttl_seconds=60.0)
    assert s2.is_seen(fp)


def test_expired_fingerprint_is_not_seen(tmp_path, monkeypatch):
    path = str(tmp_path / "fp.json")
    store = FingerprintStore(path, ttl_seconds=1.0)
    fp = make_fingerprint("job", "failed")
    store.mark_seen(fp)

    # Advance time beyond TTL
    import cronwatch.fingerprint as mod
    monkeypatch.setattr(mod, "_now", lambda: time.time() + 10)
    assert not store.is_seen(fp)


def test_clear_empties_store(store):
    fp = make_fingerprint("job", "failed")
    store.mark_seen(fp)
    store.clear()
    assert store.seen_count() == 0
    assert not store.is_seen(fp)


def test_seen_count_reflects_active_entries(store):
    store.mark_seen(make_fingerprint("a", "fail"))
    store.mark_seen(make_fingerprint("b", "miss"))
    assert store.seen_count() == 2
