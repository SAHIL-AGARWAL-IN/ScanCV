import hashlib
import time
from typing import Any, Dict, Optional

# In-memory LRU-like cache with TTL
_CACHE: Dict[str, Dict[str, Any]] = {}
_MAX_ENTRIES = 200
_TTL_SECONDS = 3600 * 24  # 24 hours


def get_cache_key(file_bytes: bytes, job_description: str = "") -> str:
    hasher = hashlib.sha256()
    hasher.update(file_bytes)
    hasher.update(job_description.strip().encode("utf-8"))
    return hasher.hexdigest()


def get_cached_analysis(cache_key: str) -> Optional[Dict[str, Any]]:
    entry = _CACHE.get(cache_key)
    if not entry:
        return None

    if time.time() - entry["timestamp"] > _TTL_SECONDS:
        _CACHE.pop(cache_key, None)
        return None

    return entry["data"]


def set_cached_analysis(cache_key: str, data: Dict[str, Any]) -> None:
    if len(_CACHE) >= _MAX_ENTRIES:
        # Remove oldest 20% of entries
        sorted_keys = sorted(_CACHE.keys(), key=lambda k: _CACHE[k]["timestamp"])
        for k in sorted_keys[: max(1, _MAX_ENTRIES // 5)]:
            _CACHE.pop(k, None)

    _CACHE[cache_key] = {
        "timestamp": time.time(),
        "data": data,
    }


def clear_cache() -> None:
    _CACHE.clear()
