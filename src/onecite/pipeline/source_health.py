"""Per-source circuit breaker for live metadata lookups.

A source that keeps failing (timeouts, 5xx, hard rate limits) should not be
re-queried on every entry of a batch run: each attempt burns the full retry
budget and stalls the pipeline without producing candidates. The breaker
tracks consecutive terminal failures per source and, once a threshold is
reached, short-circuits further calls for a cooldown period. After the
cooldown one probe call is allowed through (half-open); success closes the
breaker, failure re-opens it for another cooldown.

Skipped sources are still disclosed in suggestion output (status
``skipped_unhealthy``) so a caller can see that the candidate list may be
incomplete — the breaker changes latency behavior, never disclosure.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict


class SourceCircuitBreaker:
    """Thread-safe consecutive-failure breaker keyed by source name."""

    def __init__(
        self,
        failure_threshold: int = 2,
        cooldown_seconds: float = 120.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._consecutive_failures: Dict[str, int] = {}
        self._opened_at: Dict[str, float] = {}
        self._half_open: Dict[str, bool] = {}

    def allow(self, source_name: str) -> bool:
        """Return whether *source_name* may be queried right now.

        While open, calls are refused until the cooldown elapses; the first
        call after the cooldown is allowed as a half-open probe.
        """
        with self._lock:
            opened_at = self._opened_at.get(source_name)
            if opened_at is None:
                return True
            if self._clock() - opened_at < self.cooldown_seconds:
                return False
            if self._half_open.get(source_name):
                # A probe is already in flight (or its outcome was never
                # reported); refuse concurrent probes.
                return False
            self._half_open[source_name] = True
            return True

    def record_success(self, source_name: str) -> None:
        with self._lock:
            self._consecutive_failures.pop(source_name, None)
            self._opened_at.pop(source_name, None)
            self._half_open.pop(source_name, None)

    def record_failure(self, source_name: str) -> None:
        with self._lock:
            count = self._consecutive_failures.get(source_name, 0) + 1
            self._consecutive_failures[source_name] = count
            was_probe = self._half_open.pop(source_name, False)
            if count >= self.failure_threshold or was_probe:
                self._opened_at[source_name] = self._clock()

    def is_open(self, source_name: str) -> bool:
        with self._lock:
            opened_at = self._opened_at.get(source_name)
            return opened_at is not None and self._clock() - opened_at < self.cooldown_seconds

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        """Return a copy of the breaker state for diagnostics."""
        with self._lock:
            return {
                source: {
                    "consecutive_failures": float(self._consecutive_failures.get(source, 0)),
                    "open_for_seconds": max(0.0, self._clock() - opened_at),
                }
                for source, opened_at in self._opened_at.items()
            }
