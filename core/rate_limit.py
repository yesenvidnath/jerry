"""Per-user token bucket rate limiter."""

from dataclasses import dataclass
import math
from threading import Lock
import time

from core.config import settings


@dataclass
class Bucket:
    tokens: float
    updated_at: float


class TokenBucketLimiter:
    def __init__(self, capacity: int, refill_per_minute: float, max_users: int = 10_000) -> None:
        self.capacity = max(1, capacity)
        self.refill_per_second = max(0.1, refill_per_minute) / 60.0
        self.max_users = max_users
        self._buckets: dict[str, Bucket] = {}
        self._lock = Lock()

    def consume(self, user_id: str, cost: float = 1.0) -> tuple[bool, float, float]:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(user_id)
            if bucket is None:
                bucket = Bucket(tokens=float(self.capacity), updated_at=now)
                self._buckets[user_id] = bucket
            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(float(self.capacity), bucket.tokens + elapsed * self.refill_per_second)
            bucket.updated_at = now
            if bucket.tokens >= cost:
                bucket.tokens -= cost
                remaining = bucket.tokens
                allowed, retry_after = True, 0.0
            else:
                missing = cost - bucket.tokens
                allowed = False
                retry_after = missing / self.refill_per_second
                remaining = bucket.tokens
            if len(self._buckets) > self.max_users:
                cutoff = now - (self.capacity / self.refill_per_second * 2)
                stale = [key for key, value in self._buckets.items() if value.updated_at < cutoff]
                for key in stale:
                    self._buckets.pop(key, None)
                while len(self._buckets) > self.max_users:
                    self._buckets.pop(next(iter(self._buckets)))
            return allowed, math.ceil(retry_after), remaining


limiter = TokenBucketLimiter(settings.rate_limit_capacity, settings.rate_limit_refill_per_minute)
