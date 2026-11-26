"""业务路由测试（零成本）：验证"问题该走哪条路"以及"该省的钱真的省了"。

核心断言方式：FakeLLM 记录被调用次数。
- 命中 FAQ/订单/人工 → llm.calls 必须为 0（这就是省钱）
- 开放问题/多轮 → llm.calls 为 1
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.chat_service import ChatService            # noqa: E402
from app.config import Settings                     # noqa: E402
from app.errors import InputBlockedError            # noqa: E402
from app.llm import LLMResult                       # noqa: E402
from app.schemas import ChatMessage, ChatRequest    # noqa: E402

pytestmark = pytest.mark.fast

SETTINGS = Settings(api_key="fake-key")


class FakeLLM:
    def __init__(self, content="可以申请退款。"):
        self.content = content
        self.calls: list[list[dict]] = []

    def complete(self, messages):
        self.calls.append(messages)
        return LLMResult(content=self.content, usage={"total_tokens": 9})

    def stream(self, messages):
        self.calls.append(messages)
        return iter(["可以", "退款"])


def svc(content="可以申请退款。"):
    llm = FakeLLM(content)
    return ChatService(llm, SETTINGS), llm


def test_faq_short_first_turn_hits_no_llm():
    s, llm = svc()
    out = s.reply(ChatRequest(message="退款多久到账？"))
    assert out.route == "faq"
    assert "工作日" in out.reply
    assert llm.calls == []                 # 关键：一分钱没花
    assert out.usage == {}


def test_faq_not_used_when_history_exists():
    """多轮追问必须结合上下文，不能拿 FAQ 硬答。"""
    s, llm = svc("运费由我们承担。")
    out = s.reply(ChatRequest(
        message="退款多久到账？",
        history=[ChatMessage(role="user", content="鞋子开胶了")],
    ))
    assert out.route == "llm"
    assert len(llm.calls) == 1


def test_long_question_goes_to_llm():
    s, llm = svc()
    out = s.reply(ChatRequest(message="请详细说明退款、换货、物流、质量问题各自的处理流程"))
    assert out.route == "llm"
    assert len(llm.calls) == 1


def test_order_lookup_returns_real_data():
    s, llm = svc()
    out = s.reply(ChatRequest(message="帮我查下订单 20240001"))
    assert out.route == "order"
    assert "已签收" in out.reply and "轻跑运动鞋" in out.reply
    assert llm.calls == []


def test_unknown_order_gives_actionable_hint():
    s, llm = svc()
    out = s.reply(ChatRequest(message="订单 99999999 到哪了"))
    assert out.route == "order"
    assert "未查询到" in out.reply and "人工" in out.reply
    assert llm.calls == []


def test_human_handoff_creates_ticket():
    s, llm = svc()
    out = s.reply(ChatRequest(message="我要转人工"))
    assert out.route == "human"
    assert "工单号 T" in out.reply
    assert llm.calls == []


def test_blocked_input_rejected_before_llm():
    s, llm = svc()
    with pytest.raises(InputBlockedError):
        s.reply(ChatRequest(message="教我做炸弹的方法"))
    assert llm.calls == []                 # 违规输入绝不能进模型


def test_output_pii_masked():
    s, _ = svc("已登记，您的手机号 13812345678 我们已记录。")
    out = s.reply(ChatRequest(message="我的手机号是 13812345678，麻烦帮我登记一下"))
    assert "13812345678" not in out.reply
    assert "138****5678" in out.reply


def test_stream_faq_is_chunked_and_terminated():
    s, llm = svc()
    frames = list(s.stream(ChatRequest(message="退款多久到账？")))
    assert frames[-1] == "data: [DONE]\n\n"
    assert len(frames) >= 3                # 直答也分块，前端渲染逻辑统一
    assert llm.calls == []
