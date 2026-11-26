"""业务层：先审核、再路由、最后才调模型。

调用顺序很重要：
1. 内容审核（最便宜，且必须在花钱之前）
2. 意图路由（订单/FAQ/转人工 → 直接答，不烧 token）
3. 兜底才交给 LLM
4. 输出脱敏（PII 不落前端）
"""
import json

from app.config import Settings, get_settings
from app.errors import AppError
from app.llm import LLMClient
from app.moderation import check_input, mask_output
from app.router import route
from app.schemas import ChatReply, ChatRequest

FAQ_CHUNK_SIZE = 12   # 直答也走流式：按固定长度切块，前端渲染逻辑无需区分来源


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

    def _decide(self, body: ChatRequest) -> tuple[str, str | None]:
        check_input(body.message)                      # 违规输入直接 400，不花钱
        return route(body.message, body.history)

    def reply(self, body: ChatRequest) -> ChatReply:
        kind, canned = self._decide(body)
        if canned is not None:
            return ChatReply(
                reply=mask_output(canned),
                usage={},
                prompt_version=self.settings.prompt_version,
                route=kind,
            )

        payload = build_payload(body, self.settings)
        result = self.llm.complete(payload["messages"])
        return ChatReply(
            reply=mask_output(result.content),
            usage=result.usage,
            prompt_version=self.settings.prompt_version,
            route=kind,
        )

    def stream(self, body: ChatRequest):
        kind, canned = self._decide(body)

        if canned is not None:
            text = mask_output(canned)

            def canned_frames():
                for i in range(0, len(text), FAQ_CHUNK_SIZE):
                    yield encode_sse(text[i:i + FAQ_CHUNK_SIZE])
                yield "data: [DONE]\n\n"

            return canned_frames()

        payload = build_payload(body, self.settings, stream=True)
        # 立即取到上游流（鉴权/连不通会在此抛错，接口层还能返回 502）
        deltas = self.llm.stream(payload["messages"])

        def frames():
            for delta in deltas:
                yield encode_sse(delta)
            yield "data: [DONE]\n\n"

        return frames()


__all__ = ["ChatService", "build_payload", "encode_sse", "AppError"]
