"""Wrap an alert function so duplicate alerts (by fingerprint) are suppressed."""

from __future__ import annotations

from typing import Any, Callable, Optional

from cronwatch.fingerprint import FingerprintStore, make_fingerprint


class FingerprintedAlerter:
    """Suppress repeated alerts whose content fingerprint has already been seen."""

    def __init__(
        self,
        inner: Callable[..., bool],
        store: FingerprintStore,
    ) -> None:
        self._inner = inner
        self._store = store
        self.suppressed_count: int = 0
        self.delivered_count: int = 0

    def alert(
        self,
        job_name: str,
        reason: str,
        extra: Optional[Any] = None,
        **kwargs: Any,
    ) -> bool:
        fp = make_fingerprint(job_name, reason)
        if self._store.is_seen(fp):
            self.suppressed_count += 1
            return False
        result = self._inner(job_name, reason, **kwargs)
        if result:
            self._store.mark_seen(fp)
            self.delivered_count += 1
        return result

    def reset(self) -> None:
        """Reset the delivered/suppressed counters (does not clear the fingerprint store)."""
        self.suppressed_count = 0
        self.delivered_count = 0

    def stats(self) -> dict[str, int]:
        """Return a snapshot of the current delivery and suppression counts."""
        return {
            "delivered": self.delivered_count,
            "suppressed": self.suppressed_count,
            "total": self.delivered_count + self.suppressed_count,
        }

    def __call__(self, job_name: str, reason: str, **kwargs: Any) -> bool:
        return self.alert(job_name, reason, **kwargs)


def build_fingerprint_alert_fn(
    inner: Callable[..., bool],
    state_file: str,
    ttl_seconds: float = 3600.0,
) -> FingerprintedAlerter:
    store = FingerprintStore(state_file, ttl_seconds=ttl_seconds)
    return FingerprintedAlerter(inner, store)
