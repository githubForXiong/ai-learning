"""L1 单元测试：build_payload 拼装逻辑。
特点：不起服务器、不调大模型、零成本、完全确定 —— 断言全部用 A 级（精确）。
对应测试计划：分层 L1，风险 R5（上下文错乱）。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

pytestmark = pytest.mark.fast   # 整层归入快速层

from app.main import build_payload, ChatRequest, SYSTEM_PROMPT, MAX_HISTORY


def make_history(n: int):
    return [{"role": "user", "content": f"第{i}问"} for i in range(n)]


class TestBuildPayload:
    def test_messages_order_system_first_user_last(self):
        """messages 必须以 system 开头、本轮 user 结尾。"""
        req = ChatRequest(message="能退款吗", history=[])
        msgs = build_payload(req)["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[-1] == {"role": "user", "content": "能退款吗"}
        assert len(msgs) == 2  # 无历史时只有 system + 本轮

    def test_history_appended_in_order(self):
        """有历史时：system + 历史(按序) + 本轮user。"""
        history = make_history(3)
        req = ChatRequest(message="新问题", history=history)
        msgs = build_payload(req)["messages"]
        assert len(msgs) == 1 + 3 + 1
        assert msgs[1]["content"] == "第0问"   # 历史保持原顺序
        assert msgs[3]["content"] == "第2问"
        assert msgs[-1]["content"] == "新问题"

    def test_history_trimmed_to_max(self):
        """滑动窗口：12条历史只保留最后10条（边界值：正好卡在 MAX_HISTORY 线上）。"""
        history = make_history(12)
        req = ChatRequest(message="新问题", history=history)
        msgs = build_payload(req)["messages"]
        assert len(msgs) == 1 + MAX_HISTORY + 1
        assert msgs[1]["content"] == "第2问"   # 第0、1条应被裁掉
        assert msgs[2]["content"] == "第3问"

    def test_exactly_max_history_not_trimmed(self):
        """边界值：正好10条 → 一条不裁。"""
        req = ChatRequest(message="新问题", history=make_history(MAX_HISTORY))
        msgs = build_payload(req)["messages"]
        assert len(msgs) == 1 + MAX_HISTORY + 1
        assert msgs[1]["content"] == "第0问"

    def test_fixed_params(self):
        """模型参数是配置，也要有回归保护（改 temperature 应是有意识的决定）。"""
        req = ChatRequest(message="x", history=[])
        payload = build_payload(req)
        assert payload["model"] == "deepseek-chat"
        assert payload["temperature"] == 0.3
        assert payload["max_tokens"] == 500
        assert payload["stream"] is False
        assert payload["messages"][0]["content"] == SYSTEM_PROMPT
