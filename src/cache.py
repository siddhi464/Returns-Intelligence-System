from __future__ import annotations
import threading
import time
from typing import Any


class MemoryCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            exp, val = item
            if exp < now:
                self._store.pop(key, None)
                return None
            return val

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        exp = time.time() + float(ttl_seconds)
        with self._lock:
            self._store[key] = (exp, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)


_CACHE: MemoryCache | None = None


def get_cache() -> MemoryCache:
    global _CACHE
    if _CACHE is None:
        _CACHE = MemoryCache()
    return _CACHE
