"""重构带来的最大收益：业务层可用 FakeLLM 零成本测试。

不启服务器、不发网络请求、不消耗 token、结果完全确定。
深化收益：可以精确断言"发给模型的 messages 长什么样"，以及异常如何向上传播。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.chat_service import ChatService          # noqa: E402
from app.config import Settings                   # noqa: E402
from app.errors import UpstreamError              # noqa: E402
from app.llm import LLMResult                     # noqa: E402
from app.schemas import ChatRequest               # noqa: E402

pytestmark = pytest.mark.fast

SETTINGS = Settings(api_key="fake-key-for-test")

# 会走 LLM 的开放问题（长度>15、不含 FAQ 关键词），否则会被意图路由短路
LLM_MSG = "我遇到一个比较特殊的售后情况，想请你帮我分析一下"


class FakeLLM:
    """假大脑：返回固定内容，并记录收到的 messages 供断言。"""

    def __init__(self, content="可以申请退款。", deltas=("可以", "申请", "退款。")):
        self.content = content
        self.deltas = deltas
        self.calls: list[list[dict]] = []

    def complete(self, messages):
        self.calls.append(messages)
        return LLMResult(content=self.content, usage={"total_tokens": 12})

    def stream(self, messages):
        self.calls.append(messages)
        deltas = self.deltas

        def gen():
            yield from deltas

        return gen()


class BrokenLLM:
    def complete(self, messages):
        raise UpstreamError("上游返回 401")

    def stream(self, messages):
        raise UpstreamError("上游返回 401")


def test_reply_contract_and_payload_wiring():
    llm = FakeLLM()
    out = ChatService(llm, SETTINGS).reply(ChatRequest(message=LLM_MSG))

    assert out.reply == "可以申请退款。"
    assert out.usage["total_tokens"] == 12
    assert out.prompt_version == SETTINGS.prompt_version

    sent = llm.calls[0]
    assert sent[0]["role"] == "system"                       # 人设必须在最前
    assert sent[-1] == {"role": "user", "content": LLM_MSG}  # 本轮问题在最后


def test_system_prompt_is_configurable():
    """人设来自配置而不是硬编码 → 换 prompt 不需要改业务代码。"""
    custom = Settings(api_key="fake", system_prompt="你是严格的测试人设")
    llm = FakeLLM()
    ChatService(llm, custom).reply(ChatRequest(message=LLM_MSG))
    assert llm.calls[0][0]["content"] == "你是严格的测试人设"


def test_stream_frames_are_well_formed():
    svc = ChatService(FakeLLM(deltas=("退", "款")), SETTINGS)
    frames = list(svc.stream(ChatRequest(message=LLM_MSG)))

    assert frames[-1] == "data: [DONE]\n\n"     # 协议以哨兵结束
    assert all(f.startswith("data: ") and f.endswith("\n\n") for f in frames)
    assert '"退"' in "".join(frames) and '"款"' in "".join(frames)


def test_upstream_error_propagates():
    svc = ChatService(BrokenLLM(), SETTINGS)
    with pytest.raises(UpstreamError):
        svc.reply(ChatRequest(message=LLM_MSG))
