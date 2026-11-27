"""接口层：只做路由注册、鉴权/限流、中间件、健康检查，业务在 chat_service 里。

create_app(llm=..., settings=...) 是给测试用的注入口：
可以塞 FakeLLM 与自定义配置，起一个"假大脑 + 指定安全策略"的服务。
"""
import logging
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.chat_service import ChatService
from app.config import Settings, get_settings
from app.errors import AuthError, register_error_handlers
from app.llm import DeepSeekClient
from app.schemas import ChatReply, ChatRequest
from app.security import RateLimiter
from app.store import SessionStore

logger = logging.getLogger("ai_kf")


def create_app(llm=None, settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    store = SessionStore(ttl=settings.session_ttl,
                         max_messages=settings.session_max_messages)
    service = ChatService(llm or DeepSeekClient(settings), settings, store=store)
    limiter = RateLimiter(settings.rate_limit_per_min)

    app = FastAPI(title="AI客服教材", version="0.7")
    register_error_handlers(app)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    def guard(request: Request) -> None:
        """鉴权 + 限流。默认关闭（配置全 0/False 时是空操作），不影响本地开发。"""
        key = request.headers.get("X-API-Key", "")
        if settings.require_auth and key not in settings.api_keys:
            raise AuthError()
        identity = key or (request.client.host if request.client else "anon")
        limiter.check(identity)

    @app.get("/healthz")
    def healthz():
        # 探活接口：不调大模型、不鉴权，用于部署编排与冒烟检查
        return {"status": "ok", "prompt_version": settings.prompt_version}

    @app.post("/chat", response_model=ChatReply, dependencies=[Depends(guard)])
    def chat(body: ChatRequest):
        return service.reply(body)

    @app.post("/chat/stream", dependencies=[Depends(guard)])
    def chat_stream(body: ChatRequest):
        return StreamingResponse(service.stream(body), media_type="text/event-stream")

    @app.get("/")
    def home():
        return FileResponse("app/static/index.html")

    return app


app = create_app()
