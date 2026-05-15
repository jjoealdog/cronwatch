"""Tests for cronwatch.tags."""

import pytest
from types import SimpleNamespace

from cronwatch.tags import (
    jobs_with_tag,
    jobs_without_tag,
    all_tags,
    filter_jobs,
)


def _job(name: str, tags: list[str]):
    return SimpleNamespace(name=name, tags=tags)


JOBS = [
    _job("backup", ["critical", "nightly"]),
    _job("report", ["nightly", "reporting"]),
    _job("cleanup", ["maintenance"]),
    _job("ping", []),
]


def test_jobs_with_tag_returns_matching():
    result = jobs_with_tag(JOBS, "nightly")
    assert {j.name for j in result} == {"backup", "report"}


def test_jobs_with_tag_case_insensitive():
    result = jobs_with_tag(JOBS, "CRITICAL")
    assert len(result) == 1
    assert result[0].name == "backup"


def test_jobs_without_tag_excludes_matching():
    result = jobs_without_tag(JOBS, "nightly")
    assert {j.name for j in result} == {"cleanup", "ping"}


def test_all_tags_union():
    tags = all_tags(JOBS)
    assert tags == {"critical", "nightly", "reporting", "maintenance"}


def test_all_tags_empty_jobs():
    assert all_tags([]) == set()


def test_filter_jobs_include_only():
    result = filter_jobs(JOBS, include=["critical"])
    assert [j.name for j in result] == ["backup"]


def test_filter_jobs_exclude_only():
    result = filter_jobs(JOBS, exclude=["nightly"])
    assert {j.name for j in result} == {"cleanup", "ping"}


def test_filter_jobs_include_and_exclude():
    # include nightly, then exclude reporting → only backup
    result = filter_jobs(JOBS, include=["nightly"], exclude=["reporting"])
    assert [j.name for j in result] == ["backup"]


def test_filter_jobs_no_filters_returns_all():
    result = filter_jobs(JOBS)
    assert len(result) == len(JOBS)


def test_filter_jobs_no_match_returns_empty():
    result = filter_jobs(JOBS, include=["nonexistent"])
    assert result == []
