"""安全设施：限流器（令牌用滑动窗口实现，够用且好测）。"""
import time
from collections import deque

from app.errors import RateLimitError


class RateLimiter:
    """每分钟最多 N 次。limit<=0 表示不限制。"""

    def __init__(self, limit_per_min: int, clock=time.time):
        self._limit = limit_per_min
        self._clock = clock
        self._hits: dict[str, deque] = {}

    def allow(self, identity: str) -> bool:
        if self._limit <= 0:
            return True
        now = self._clock()
        hits = self._hits.setdefault(identity, deque())
        while hits and now - hits[0] >= 60:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True

    def check(self, identity: str) -> None:
        if not self.allow(identity):
            raise RateLimitError(f"请求过于频繁，请稍后再试（每分钟上限 {self._limit} 次）")
