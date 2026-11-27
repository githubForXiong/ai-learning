"""统一错误模型。

为什么不用裸 HTTPException：
- 前端/测试无法区分"上游超时"和"上游返回错误"；
- 错误信息没有机器可读的 code，只能靠人看文字。
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    code = "INTERNAL_ERROR"
    status = 500
    message = "服务内部错误"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)


class UpstreamError(AppError):
    code = "UPSTREAM_UNAVAILABLE"
    status = 502
    message = "大模型服务异常"


class LLMTimeoutError(UpstreamError):
    code = "UPSTREAM_TIMEOUT"
    message = "大模型服务超时"


class InputBlockedError(AppError):
    code = "INPUT_BLOCKED"
    status = 400
    message = "输入包含违规内容"


class AuthError(AppError):
    code = "UNAUTHORIZED"
    status = 401
    message = "缺少或无效的 API Key"


class RateLimitError(AppError):
    code = "RATE_LIMITED"
    status = 429
    message = "请求过于频繁"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
        )
