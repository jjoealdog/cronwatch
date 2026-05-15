"""Job execution tracker — records last run times and detects missed runs."""

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from cronwatch.config import JobConfig

logger = logging.getLogger(__name__)


@dataclass
class JobState:
    job_name: str
    last_run_at: Optional[float] = None  # unix timestamp
    last_exit_code: Optional[int] = None
    consecutive_failures: int = 0
    last_alert_at: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "JobState":
        return cls(**data)


class JobTracker:
    """Persists and queries job state from a JSON state file."""

    def __init__(self, state_file: str = "/var/lib/cronwatch/state.json"):
        self.state_file = Path(state_file)
        self._state: dict[str, JobState] = {}
        self._load()

    def _load(self) -> None:
        if not self.state_file.exists():
            logger.debug("No state file found at %s, starting fresh.", self.state_file)
            return
        try:
            raw = json.loads(self.state_file.read_text())
            self._state = {k: JobState.from_dict(v) for k, v in raw.items()}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load state file: %s", exc)

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({k: v.to_dict() for k, v in self._state.items()}, indent=2))
        tmp.replace(self.state_file)

    def get(self, job_name: str) -> JobState:
        return self._state.setdefault(job_name, JobState(job_name=job_name))

    def record_run(self, job_name: str, exit_code: int) -> JobState:
        state = self.get(job_name)
        state.last_run_at = time.time()
        state.last_exit_code = exit_code
        if exit_code != 0:
            state.consecutive_failures += 1
        else:
            state.consecutive_failures = 0
        self._save()
        return state

    def is_overdue(self, job: JobConfig) -> bool:
        """Return True if the job hasn't run within its expected interval."""
        state = self.get(job.name)
        if state.last_run_at is None:
            return False  # never seen — can't judge yet
        elapsed = time.time() - state.last_run_at
        return elapsed > job.expected_interval_seconds

    def mark_alerted(self, job_name: str) -> None:
        self.get(job_name).last_alert_at = time.time()
        self._save()
