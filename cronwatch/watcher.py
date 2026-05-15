"""File-based watcher that tails a log file and detects cron job completion markers."""

import re
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Callable

# Lines written by cron wrappers typically look like:
# [CRONWATCH] job=backup status=success duration=12.4
_MARKER_RE = re.compile(
    r"\[CRONWATCH\]\s+job=(?P<job>\S+)\s+status=(?P<status>success|failure)\s+duration=(?P<duration>[\d.]+)"
)


@dataclass
class MarkerEvent:
    job_name: str
    success: bool
    duration_seconds: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def parse_marker_line(line: str) -> Optional[MarkerEvent]:
    """Return a MarkerEvent if *line* contains a cronwatch marker, else None."""
    m = _MARKER_RE.search(line)
    if m is None:
        return None
    return MarkerEvent(
        job_name=m.group("job"),
        success=m.group("status") == "success",
        duration_seconds=float(m.group("duration")),
    )


class LogWatcher:
    """Tail a log file and invoke *callback* for every marker event found."""

    def __init__(self, log_path: str, callback: Callable[[MarkerEvent], None]) -> None:
        self.log_path = log_path
        self.callback = callback
        self._offset: int = 0

    def _seek_to_end(self) -> None:
        """On first call, skip existing content so we only react to new lines."""
        if os.path.exists(self.log_path):
            self._offset = os.path.getsize(self.log_path)

    def poll(self) -> int:
        """Read any new lines since last poll. Returns number of events fired."""
        if not os.path.exists(self.log_path):
            return 0

        fired = 0
        with open(self.log_path, "r", errors="replace") as fh:
            fh.seek(self._offset)
            for line in fh:
                event = parse_marker_line(line)
                if event is not None:
                    self.callback(event)
                    fired += 1
            self._offset = fh.tell()
        return fired

    def reset(self) -> None:
        """Reset offset to end of current file (skip existing content)."""
        self._offset = 0
        self._seek_to_end()
