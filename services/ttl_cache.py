from __future__ import annotations

import threading
import time
from typing import Any


class TtlCache:
    """In-process cache. Every entry expires. A missing key and an expired key both return None."""

    def __init__(self) -> None:
        self._values: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            found = self._values.get(key)
            if found is None:
                return None
            expires_at, value = found
            if expires_at <= now:
                del self._values[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        expires_at = time.monotonic() + ttl_seconds
        with self._lock:
            self._values[key] = (expires_at, value)

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            stale = [key for key in self._values if key.startswith(prefix)]
            for key in stale:
                del self._values[key]
            return len(stale)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


inventory_cache = TtlCache()
