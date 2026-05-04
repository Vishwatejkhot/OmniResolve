import hashlib
import json
import os
from functools import wraps
from typing import Any, Callable

import diskcache

_CACHE_DIR = os.getenv("DISKCACHE_DIR", ".cache/omni_resolve")
_TTL = 60 * 60 * 24

_cache = diskcache.Cache(_CACHE_DIR)

def make_key(*args, **kwargs) -> str:
    payload = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()

def get(key: str) -> Any | None:
    return _cache.get(key)

def set(key: str, value: Any, ttl: int = _TTL) -> None:
    _cache.set(key, value, expire=ttl)

def delete(key: str) -> None:
    _cache.delete(key)

def cached(ttl: int = _TTL):
    def decorator(fn: Callable) -> Callable:
        import asyncio

        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            key = make_key(fn.__qualname__, *args, **kwargs)
            hit = get(key)
            if hit is not None:
                return hit
            result = await fn(*args, **kwargs)
            set(key, result, ttl)
            return result

        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            key = make_key(fn.__qualname__, *args, **kwargs)
            hit = get(key)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            set(key, result, ttl)
            return result

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper

    return decorator
