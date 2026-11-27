"""业务层：先审核、再路由、最后才调模型。

调用顺序很重要：
1. 内容审核（最便宜，且必须在花钱之前）
2. 意图路由（订单/FAQ/转人工 → 直接答，不烧 token）
3. 兜底才交给 LLM
4. 输出脱敏（PII 不落前端）
5. 会话落库（session_id 模式下由服务端记住这轮问答）
"""
import json

from app.config import Settings, get_settings
from app.errors import AppError
from app.llm import LLMClient
from app.moderation import check_input, mask_output
from app.router import route
from app.schemas import ChatReply, ChatRequest
from app.store import SessionStore

FAQ_CHUNK_SIZE = 12   # 直答也走流式：按固定长度切块，前端渲染逻辑无需区分来源


def _as_dict(message) -> dict:
    return message.model_dump() if hasattr(message, "model_dump") else dict(message)


def build_payload(body: ChatRequest, settings: Settings, stream: bool = False,
                  history: list | None = None) -> dict:
    """人设 + 滑动窗口裁剪后的历史 + 本轮提问。纯函数，单元测试直接断言。

    history 显式传入时优先使用（会话取自服务端，而不是客户端自称的历史）。
    """
    source = body.history if history is None else history
    trimmed = [_as_dict(m) for m in source[-settings.max_history:]]
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
    def __init__(self, llm: LLMClient, settings: Settings | None = None,
                 store: SessionStore | None = None):
        self.llm = llm
        self.settings = settings or get_settings()
        self.store = store or SessionStore(
            ttl=self.settings.session_ttl,
            max_messages=self.settings.session_max_messages,
        )

    # ---- 会话 ----

    def _effective_history(self, body: ChatRequest) -> list[dict]:
        """有 session_id 时以服务端为准：客户端传来的 history 一律忽略（防篡改）。"""
        if body.session_id:
            return self.store.get(body.session_id)
        return [_as_dict(m) for m in body.history]

    def _remember(self, body: ChatRequest, reply: str) -> None:
        if not body.session_id:
            return
        self.store.append(body.session_id, "user", body.message)
        self.store.append(body.session_id, "assistant", reply)

    # ---- 主流程 ----

    def _decide(self, body: ChatRequest, history: list[dict]) -> tuple[str, str | None]:
        check_input(body.message)                      # 违规输入直接 400，不花钱
        return route(body.message, history)

    def reply(self, body: ChatRequest) -> ChatReply:
        history = self._effective_history(body)
        kind, canned = self._decide(body, history)

        if canned is not None:
            text = mask_output(canned)
            self._remember(body, text)
            return ChatReply(
                reply=text, usage={},
                prompt_version=self.settings.prompt_version,
                route=kind, session_id=body.session_id,
            )

        payload = build_payload(body, self.settings, history=history)
        result = self.llm.complete(payload["messages"])
        text = mask_output(result.content)
        self._remember(body, text)
        return ChatReply(
            reply=text, usage=result.usage,
            prompt_version=self.settings.prompt_version,
            route=kind, session_id=body.session_id,
        )

    def stream(self, body: ChatRequest):
        history = self._effective_history(body)
        kind, canned = self._decide(body, history)

        if canned is not None:
            text = mask_output(canned)

            def canned_frames():
                for i in range(0, len(text), FAQ_CHUNK_SIZE):
                    yield encode_sse(text[i:i + FAQ_CHUNK_SIZE])
                yield "data: [DONE]\n\n"

            self._remember(body, text)
            return canned_frames()

        payload = build_payload(body, self.settings, stream=True, history=history)
        # 立即取到上游流（鉴权/连不通会在此抛错，接口层还能返回 502）
        deltas = self.llm.stream(payload["messages"])

        def frames():
            collected = []
            for delta in deltas:
                collected.append(delta)
                yield encode_sse(delta)
            yield "data: [DONE]\n\n"
            self._remember(body, "".join(collected))

        return frames()


__all__ = ["ChatService", "build_payload", "encode_sse", "AppError"]
