"""Tests for cronwatch.silencer."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.silencer import Silencer, SilenceEntry


def _utc(**kwargs) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**kwargs)


@pytest.fixture
def silencer(tmp_path: Path) -> Silencer:
    return Silencer(state_path=tmp_path / "silences.json")


def test_new_silencer_has_no_active_silences(silencer: Silencer):
    assert silencer.active_silences() == []


def test_silence_makes_job_silenced(silencer: Silencer):
    silencer.silence("backup", until=_utc(hours=1), reason="maintenance")
    assert silencer.is_silenced("backup")


def test_expired_silence_is_not_active(silencer: Silencer):
    silencer.silence("backup", until=_utc(seconds=-1))
    assert not silencer.is_silenced("backup")


def test_unsilence_removes_entry(silencer: Silencer):
    silencer.silence("backup", until=_utc(hours=1))
    removed = silencer.unsilence("backup")
    assert removed is True
    assert not silencer.is_silenced("backup")


def test_unsilence_nonexistent_returns_false(silencer: Silencer):
    assert silencer.unsilence("ghost") is False


def test_purge_expired_removes_old_entries(silencer: Silencer):
    silencer.silence("old_job", until=_utc(seconds=-5))
    silencer.silence("active_job", until=_utc(hours=1))
    removed = silencer.purge_expired()
    assert removed == 1
    assert not silencer.is_silenced("old_job")
    assert silencer.is_silenced("active_job")


def test_silences_persist_across_instances(tmp_path: Path):
    path = tmp_path / "silences.json"
    s1 = Silencer(state_path=path)
    s1.silence("nightly", until=_utc(hours=2), reason="deploy")

    s2 = Silencer(state_path=path)
    assert s2.is_silenced("nightly")
    assert s2.active_silences()[0].reason == "deploy"


def test_active_silences_excludes_expired(silencer: Silencer):
    silencer.silence("a", until=_utc(hours=1))
    silencer.silence("b", until=_utc(seconds=-1))
    active = silencer.active_silences()
    assert len(active) == 1
    assert active[0].job_name == "a"


def test_silence_entry_roundtrip():
    entry = SilenceEntry(
        job_name="etl",
        until=_utc(hours=3),
        reason="testing",
    )
    restored = SilenceEntry.from_dict(entry.to_dict())
    assert restored.job_name == entry.job_name
    assert restored.reason == entry.reason
    assert abs((restored.until - entry.until).total_seconds()) < 1
