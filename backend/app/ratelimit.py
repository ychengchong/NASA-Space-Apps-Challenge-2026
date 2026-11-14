"""Per-address request limits (spec 8 "Limits" and spec 11 "Security and privacy").

Counts live in memory, so a restart resets them. The daily AI cap is kept in SQLite instead.
"""

import threading
import time
from collections import deque
from collections.abc import Callable

WINDOW_SECONDS = 60.0


class RateLimiter:
    """Allows at most `limit_per_minute` events per key in any sliding 60-second window."""

    def __init__(self, limit_per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = limit_per_minute
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record an event for `key` and return True; return False if the key is over its limit."""
        now = self._clock()
        with self._lock:
            self._forget_idle_keys(now)
            events = self._events.setdefault(key, deque())
            while events and now - events[0] >= WINDOW_SECONDS:
                events.popleft()
            if len(events) >= self._limit:
                return False
            events.append(now)
            return True

    def _forget_idle_keys(self, now: float) -> None:
        idle = [
            key
            for key, events in self._events.items()
            if not events or now - events[-1] >= WINDOW_SECONDS
        ]
        for key in idle:
            del self._events[key]
