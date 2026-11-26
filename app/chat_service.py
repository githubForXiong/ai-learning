"""业务层：只负责"拼 payload / 调 LLM / 组装响应"，不关心 HTTP 细节。

依赖注入的是 LLMClient 协议，而不是具体的 DeepSeekClient——
所以测试里可以塞一个 FakeLLM，一行网络请求都不发。
"""
import json

from app.config import Settings, get_settings
from app.llm import LLMClient
from app.schemas import ChatReply, ChatRequest


def build_payload(body: ChatRequest, settings: Settings, stream: bool = False) -> dict:
    """人设 + 滑动窗口裁剪后的历史 + 本轮提问。纯函数，单元测试直接断言。"""
    trimmed = [m.model_dump() for m in body.history[-settings.max_history:]]
    return {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": settings.system_prompt},
            *trimmed,
            {"role": "user", "content": body.message},
        ],
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "stream": stream,
    }


def encode_sse(delta: str) -> str:
    """把一段增量编码成 SSE 帧。前端按空行切分，这里的格式就是契约。"""
    return f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"


class ChatService:
    def __init__(self, llm: LLMClient, settings: Settings | None = None):
        self.llm = llm
        self.settings = settings or get_settings()

    def reply(self, body: ChatRequest) -> ChatReply:
        payload = build_payload(body, self.settings)
        result = self.llm.complete(payload["messages"])
        return ChatReply(
            reply=result.content,
            usage=result.usage,
            prompt_version=self.settings.prompt_version,
        )

    def stream(self, body: ChatRequest):
        payload = build_payload(body, self.settings, stream=True)
        # 立即取到上游流（鉴权/连不通会在此抛错，接口层还能返回 502）
        deltas = self.llm.stream(payload["messages"])

        def frames():
            for delta in deltas:
                yield encode_sse(delta)
            yield "data: [DONE]\n\n"

        return frames()
