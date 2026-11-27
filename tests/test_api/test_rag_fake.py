"""RAG 拼装逻辑测试（零成本）：验证"资料真的进了 prompt"与"无资料时的兜底"。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import Settings                 # noqa: E402
from app.llm import LLMResult                   # noqa: E402
from app.rag_service import NO_DOC_REPLY, RagService   # noqa: E402

pytestmark = pytest.mark.fast

SETTINGS = Settings(api_key="fake")


class FakeLLM:
    def __init__(self):
        self.calls: list[list[dict]] = []

    def complete(self, messages):
        self.calls.append(messages)
        return LLMResult(content="退款一般 1-7 个工作日到账。", usage={"total_tokens": 30})

    def stream(self, messages):
        raise AssertionError("RAG 旁路当前只提供非流式接口")


def test_context_is_injected_into_system_prompt():
    llm = FakeLLM()
    out = RagService(llm, SETTINGS).reply("退款多久能到账")

    assert out["sources"][0] == "refund"
    system = llm.calls[0][0]
    assert system["role"] == "system"
    assert "【资料】" in system["content"]
    assert "《退款政策》" in system["content"]        # 命中文档的正文确实被塞进去了
    assert out["route"] == "rag"


def test_no_document_returns_safe_fallback():
    """知识库没有相关内容时，宁可说"没查到"，也不能让模型裸答。"""
    llm = FakeLLM()
    out = RagService(llm, SETTINGS).reply("今天天气怎么样")

    assert out["reply"] == NO_DOC_REPLY
    assert out["sources"] == []
    assert llm.calls == []            # 关键：不做无根据的生成


def test_history_is_forwarded():
    llm = FakeLLM()
    RagService(llm, SETTINGS).reply(
        "那需要多久",
        history=[{"role": "user", "content": "我要退款"},
                 {"role": "assistant", "content": "已为您登记"}],
    )
    contents = [m["content"] for m in llm.calls[0]]
    assert "我要退款" in contents
    assert contents[-1] == "那需要多久"
