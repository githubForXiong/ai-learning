"""会话存储单元测试（零成本）：TTL、滑动窗口、会话隔离、副本安全。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.store import SessionStore   # noqa: E402

pytestmark = pytest.mark.fast


class FakeClock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def make_store(ttl=1800, max_messages=20):
    clock = FakeClock()
    return SessionStore(ttl=ttl, max_messages=max_messages, clock=clock), clock


def test_append_and_get_in_order():
    store, _ = make_store()
    store.append("s1", "user", "第一问")
    store.append("s1", "assistant", "第一答")
    assert store.get("s1") == [
        {"role": "user", "content": "第一问"},
        {"role": "assistant", "content": "第一答"},
    ]


def test_sessions_are_isolated():
    store, _ = make_store()
    store.append("s1", "user", "A")
    store.append("s2", "user", "B")
    assert store.get("s1")[0]["content"] == "A"
    assert store.get("s2")[0]["content"] == "B"
    assert store.get("unknown") == []


def test_expired_session_is_dropped():
    store, clock = make_store(ttl=60)
    store.append("s1", "user", "旧消息")
    clock.advance(61)
    assert store.get("s1") == []


def test_ttl_refreshed_on_new_message():
    store, clock = make_store(ttl=60)
    store.append("s1", "user", "一")
    clock.advance(50)
    store.append("s1", "assistant", "二")   # 刷新时间
    clock.advance(50)
    assert len(store.get("s1")) == 2        # 距最后一条仅 50s，未过期


def test_max_messages_trims_oldest():
    store, _ = make_store(max_messages=4)
    for i in range(6):
        store.append("s1", "user", f"第{i}条")
    messages = store.get("s1")
    assert len(messages) == 4
    assert messages[0]["content"] == "第2条"   # 前两条被裁掉


def test_get_returns_copy():
    """防止调用方修改返回值污染存储（真实项目里踩过的坑）。"""
    store, _ = make_store()
    store.append("s1", "user", "原文")
    got = store.get("s1")
    got[0]["content"] = "被篡改"
    assert store.get("s1")[0]["content"] == "原文"
