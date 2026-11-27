"""服务端会话存储。

为什么 history 不能只放前端：
1. 前端可篡改（伪造"AI 说过的话"来诱导回答）；
2. 换设备/刷新就丢；
3. 无法做超时、转人工、审计。

实现要点：TTL 过期 + 条数上限（滑动窗口），每会话独立。
"""
import time
from dataclasses import dataclass, field


@dataclass
class _Session:
    messages: list[dict] = field(default_factory=list)
    updated_at: float = 0.0


class SessionStore:
    def __init__(self, ttl: int = 1800, max_messages: int = 20, clock=time.time):
        self._ttl = ttl
        self._max = max_messages
        self._clock = clock
        self._data: dict[str, _Session] = {}

    def _purge(self, now: float) -> None:
        expired = [sid for sid, s in self._data.items() if now - s.updated_at > self._ttl]
        for sid in expired:
            del self._data[sid]

    def get(self, session_id: str) -> list[dict]:
        now = self._clock()
        self._purge(now)
        session = self._data.get(session_id)
        # 注意：list() 只是浅拷贝，内层 dict 仍共享 → 必须逐条 dict() 复制
        return [dict(m) for m in session.messages] if session else []

    def append(self, session_id: str, role: str, content: str) -> None:
        now = self._clock()
        self._purge(now)
        session = self._data.setdefault(session_id, _Session(updated_at=now))
        session.messages.append({"role": role, "content": content})
        session.messages = session.messages[-self._max:]   # 只保留最近 N 条
        session.updated_at = now

    def clear(self, session_id: str) -> None:
        self._data.pop(session_id, None)
