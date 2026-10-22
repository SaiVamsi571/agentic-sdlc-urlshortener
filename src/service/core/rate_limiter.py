"""
Sliding-Window In-Memory Rate Limiter.
Enforces requests-per-minute limits per client IP to mitigate denial-of-service and brute-force scans.
"""

from __future__ import annotations
import threading
import time
from collections import defaultdict, deque
from typing import Dict, Tuple

class SlidingWindowRateLimiter:
    def __init__(self, default_limit: int = 60, window_seconds: int = 60):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, deque] = defaultdict(deque) # client_key -> deque of timestamps
        self._lock = threading.RLock()

    def is_allowed(self, client_key: str, limit: int | None = None) -> Tuple[bool, int, float]:
        """
        Evaluates whether a request from client_key is allowed.
        Returns:
            (allowed: bool, remaining_requests: int, reset_in_seconds: float)
        """
        max_requests = limit if limit is not None else self.default_limit
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[client_key]
            
            # Evict timestamps older than sliding window
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            current_count = len(timestamps)
            if current_count >= max_requests:
                oldest = timestamps[0]
                reset_in = max(0.0, round((oldest + self.window_seconds) - now, 1))
                return False, 0, reset_in

            timestamps.append(now)
            remaining = max(0, max_requests - (current_count + 1))
            return True, remaining, float(self.window_seconds)

    def reset(self, client_key: str | None = None) -> None:
        with self._lock:
            if client_key:
                self._requests.pop(client_key, None)
            else:
                self._requests.clear()
