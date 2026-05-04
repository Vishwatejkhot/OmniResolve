import asyncio
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable

import tenacity

@dataclass
class TokenBucket:
    capacity: float
    refill_rate: float
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def __post_init__(self):
        self._tokens = self.capacity
        self._last_refill = time.monotonic()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last_refill = now
            if self._tokens < tokens:
                wait = (tokens - self._tokens) / self.refill_rate
                await asyncio.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= tokens

_anthropic_bucket = TokenBucket(capacity=50, refill_rate=50 / 60)
_neo4j_bucket = TokenBucket(capacity=100, refill_rate=100 / 60)

def with_anthropic_rate_limit(fn: Callable) -> Callable:
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        await _anthropic_bucket.acquire()
        return await fn(*args, **kwargs)
    return wrapper

def with_neo4j_rate_limit(fn: Callable) -> Callable:
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        await _neo4j_bucket.acquire()
        return await fn(*args, **kwargs)
    return wrapper

def with_retry(
    max_attempts: int = 4,
    wait_min: float = 1.0,
    wait_max: float = 60.0,
    reraise: bool = True,
):
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        @tenacity.retry(
            stop=tenacity.stop_after_attempt(max_attempts),
            wait=tenacity.wait_exponential_jitter(initial=wait_min, max=wait_max),
            reraise=reraise,
        )
        async def wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)
        return wrapper
    return decorator
