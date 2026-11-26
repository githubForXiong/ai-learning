"""流式接口测试：POST /chat/stream（SSE）。
核心差异：resp.json() 在这里完全失效——响应不是一段JSON，而是一串事件。
必须逐行解析 + 拼接 delta 还原全文，才能做内容断言。（PLAN: R7）"""
import json
import time

import pytest
import requests


def parse_sse(resp) -> tuple[str, bool, int]:
    """返回 (拼接后的完整回答, 是否收到[DONE], 收到的分块数)。"""
    deltas = []
    got_done = False
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload == "[DONE]":
            got_done = True
            continue
        deltas.append(json.loads(payload)["delta"])
    return "".join(deltas), got_done, len(deltas)


@pytest.mark.slow
@pytest.mark.needs_key
def test_stream_is_sse_and_reassembles(base_url):
    r = requests.post(f"{base_url}/chat/stream",
                      json={"message": "换货怎么操作？", "history": []},
                      stream=True, timeout=60)
    assert r.status_code == 200                                  # A
    assert r.headers["content-type"].startswith("text/event-stream")  # A：协议声明

    t0 = time.time()
    full, got_done, n_chunks = parse_sse(r)

    assert got_done, "流必须以 [DONE] 哨兵正常结束"               # A：协议完整性
    assert full != ""                                            # B
    assert n_chunks >= 2, "真流式应至少分多块到达"                 # B：防"假流式"(一次憋完)
    assert any(w in full for w in ("换货", "申请", "客服"))         # B：业务相关
    # 首块时延（D级统计的雏形，这里先做宽松约束；第8章正式建指标体系）
    assert time.time() - t0 < 30                                 # B


@pytest.mark.fast
def test_stream_upstream_failure_returns_502(badkey_base_url):
    """上游在推流开始前就失败 → 还能给出正确的 502（这是能测的部分）。"""
    # 用会走 LLM 的开放问题，避免被意图路由短路到 FAQ（那会是 200 而非 502）
    r = requests.post(f"{badkey_base_url}/chat/stream",
                      json={"message": "我遇到一个比较特殊的售后情况，想请你帮我分析一下"},
                      stream=True, timeout=30)
    assert r.status_code == 502                                  # A


@pytest.mark.slow
@pytest.mark.needs_key
def test_stream_no_done_sentinel_would_fail(base_url):
    """教学用例：演示'协议断言'的价值——若实现漏发[DONE]，前端会永远等待。
    这里对正常流验证哨兵存在（与第一条呼应，强调这是契约的一部分）。"""
    r = requests.post(f"{base_url}/chat/stream",
                      json={"message": "物流到哪了？", "history": []},
                      stream=True, timeout=60)
    raw_lines = [l for l in r.iter_lines(decode_unicode=True) if l]
    assert raw_lines[-1] == "data: [DONE]"                       # A：最后一个事件必须是哨兵
