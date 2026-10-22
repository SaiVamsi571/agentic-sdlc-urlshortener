"""
Thread-Safe In-Memory LRU Cache with TTL Expiration.
Minimizes database query load for popular redirect short codes.
"""
import threading
import time
from collections import OrderedDict
from typing import Any, Optional, Tuple

class LRUTTLCache:
    def __init__(self, max_size: int = 10000, default_ttl_seconds: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict() # key -> (value, expiry_timestamp)
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            value, expiry = self._cache[key]
            if time.time() > expiry:
                # Evict expired entry
                del self._cache[key]
                self.misses += 1
                return None

            # Move to MRU position
            self._cache.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry = time.time() + ttl

        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.max_size:
                # Evict LRU item (first in OrderedDict)
                self._cache.popitem(last=False)

            self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return round((self.hits / total) * 100.0, 2) if total > 0 else 0.0
