"""Alert escalation policy: send to different targets based on failure streak."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwatch.config import AlertConfig, JobConfig


@dataclass
class EscalationLevel:
    """A single escalation tier."""
    min_failures: int          # trigger when streak >= this value
    alert_config: AlertConfig  # override alert target for this level
    label: str = ""            # human-readable name, e.g. "critical"


@dataclass
class EscalationPolicy:
    """Ordered list of escalation levels (lowest min_failures first)."""
    levels: List[EscalationLevel] = field(default_factory=list)

    def resolve(self, failure_streak: int) -> Optional[EscalationLevel]:
        """Return the highest applicable level for the given streak, or None."""
        matched: Optional[EscalationLevel] = None
        for level in sorted(self.levels, key=lambda l: l.min_failures):
            if failure_streak >= level.min_failures:
                matched = level
        return matched


def build_escalation_alert_fn(
    policy: EscalationPolicy,
    base_alert_fn: Callable[[str, str, AlertConfig], bool],
    get_streak: Callable[[str], int],
) -> Callable[[str, str, AlertConfig], bool]:
    """Wrap *base_alert_fn* so that the AlertConfig is replaced when an
    escalation level matches the current failure streak for the job.

    *get_streak* is a callable that accepts a job name and returns the
    current consecutive-failure count.
    """

    def _alert(job_name: str, message: str, cfg: AlertConfig) -> bool:
        streak = get_streak(job_name)
        level = policy.resolve(streak)
        effective_cfg = level.alert_config if level is not None else cfg
        prefix = f"[{level.label.upper()}] " if (level and level.label) else ""
        return base_alert_fn(job_name, f"{prefix}{message}", effective_cfg)

    return _alert


def parse_escalation_policy(raw: list) -> EscalationPolicy:
    """Build an EscalationPolicy from a list of dicts (as loaded from YAML).

    Each dict must have:
      - min_failures (int)
      - label (str, optional)
      - alert: same structure as a top-level alert config block
    """
    from cronwatch.config import _parse_alert  # local import to avoid cycles

    levels: List[EscalationLevel] = []
    for entry in raw or []:
        alert_cfg = _parse_alert(entry.get("alert", {}))
        levels.append(
            EscalationLevel(
                min_failures=int(entry.get("min_failures", 1)),
                alert_config=alert_cfg,
                label=str(entry.get("label", "")),
            )
        )
    return EscalationPolicy(levels=levels)
