"""Simple in-memory metrics collector for cronwatch."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class JobMetrics:
    job_name: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_run_ts: Optional[float] = None
    last_duration_seconds: Optional[float] = None
    durations: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> Optional[float]:
        if self.total_runs == 0:
            return None
        return self.successful_runs / self.total_runs

    @property
    def avg_duration(self) -> Optional[float]:
        if not self.durations:
            return None
        return sum(self.durations) / len(self.durations)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "last_run_ts": self.last_run_ts,
            "last_duration_seconds": self.last_duration_seconds,
            "success_rate": self.success_rate,
            "avg_duration": self.avg_duration,
        }


class MetricsCollector:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobMetrics] = {}
        self._start_times: Dict[str, float] = {}

    def _get_or_create(self, job_name: str) -> JobMetrics:
        if job_name not in self._jobs:
            self._jobs[job_name] = JobMetrics(job_name=job_name)
        return self._jobs[job_name]

    def record_start(self, job_name: str) -> None:
        self._start_times[job_name] = time.monotonic()

    def record_end(self, job_name: str, success: bool) -> None:
        m = self._get_or_create(job_name)
        m.total_runs += 1
        m.last_run_ts = time.time()
        if success:
            m.successful_runs += 1
        else:
            m.failed_runs += 1
        start = self._start_times.pop(job_name, None)
        if start is not None:
            duration = time.monotonic() - start
            m.last_duration_seconds = duration
            m.durations.append(duration)
            if len(m.durations) > 100:
                m.durations = m.durations[-100:]

    def get(self, job_name: str) -> Optional[JobMetrics]:
        return self._jobs.get(job_name)

    def all_metrics(self) -> List[dict]:
        return [m.to_dict() for m in self._jobs.values()]

    def reset(self, job_name: str) -> None:
        self._jobs.pop(job_name, None)
        self._start_times.pop(job_name, None)
