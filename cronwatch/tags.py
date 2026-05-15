"""Tag-based filtering for cron jobs.

Allows jobs to be grouped and filtered by arbitrary string tags,
enabling selective alerting, reporting, and silencing.
"""

from __future__ import annotations

from typing import Iterable


def jobs_with_tag(jobs: Iterable, tag: str) -> list:
    """Return jobs whose tag list contains *tag* (case-insensitive)."""
    tag_lower = tag.strip().lower()
    return [
        job for job in jobs
        if tag_lower in [t.lower() for t in getattr(job, "tags", [])]
    ]


def jobs_without_tag(jobs: Iterable, tag: str) -> list:
    """Return jobs that do NOT carry *tag*."""
    tag_lower = tag.strip().lower()
    return [
        job for job in jobs
        if tag_lower not in [t.lower() for t in getattr(job, "tags", [])]
    ]


def all_tags(jobs: Iterable) -> set[str]:
    """Return the union of all tags across every job."""
    result: set[str] = set()
    for job in jobs:
        result.update(t.lower() for t in getattr(job, "tags", []))
    return result


def filter_jobs(jobs: Iterable, include: list[str] | None = None,
                exclude: list[str] | None = None) -> list:
    """Filter *jobs* by include/exclude tag lists.

    If *include* is given, only jobs carrying at least one of those tags
    are kept.  *exclude* then removes any job carrying any of those tags.
    """
    result = list(jobs)
    if include:
        include_lower = {t.lower() for t in include}
        result = [
            j for j in result
            if include_lower & {t.lower() for t in getattr(j, "tags", [])}
        ]
    if exclude:
        exclude_lower = {t.lower() for t in exclude}
        result = [
            j for j in result
            if not (exclude_lower & {t.lower() for t in getattr(j, "tags", [])})
        ]
    return result
