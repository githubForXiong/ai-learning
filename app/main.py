import json
import os

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="AI客服教材")

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

SYSTEM_PROMPT = (
    "你是电商客服小D。规则："
    "1) 只回答售后相关问题（退款、换货、物流、质量问题）；"
    "2) 与售后无关的话题，礼貌拒绝并引导回售后问题；"
    "3) 不编造公司政策，不确定的信息引导用户联系人工客服。"
)

MAX_HISTORY = 10  # 滑动窗口：最多带上最近10条历史

HEADERS = {
    "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY', '')}",
    "Content-Type": "application/json",
}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)   # 修复R4：空输入不进大模型（第6章红灯用例驱动）
    history: list[ChatMessage] = []


def build_payload(body: ChatRequest, stream: bool = False) -> dict:
    """把 人设 + 裁剪后的历史 + 本次提问 拼成大模型要的 messages 数组。"""
    trimmed = [m.model_dump() for m in body.history[-MAX_HISTORY:]]
    return {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *trimmed,
            {"role": "user", "content": body.message},
        ],
        "temperature": 0.3,
        "max_tokens": 500,
        "stream": stream,
    }


@app.post("/chat")
def chat(body: ChatRequest):
    resp = requests.post(DEEPSEEK_URL, headers=HEADERS,
                         json=build_payload(body), timeout=30)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="大模型服务异常")
    data = resp.json()
    return {
        "reply": data["choices"][0]["message"]["content"],
        "usage": data["usage"],
    }


@app.post("/chat/stream")
def chat_stream(body: ChatRequest):
    resp = requests.post(DEEPSEEK_URL, headers=HEADERS,
                         json=build_payload(body, stream=True),
                         stream=True, timeout=60)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="大模型服务异常")

    def event_gen():
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            payload_str = line[len("data: "):]
            if payload_str == "[DONE]":   # 上游结束哨兵：不能 json.loads，直接停
                break
            payload = json.loads(payload_str)
            if payload.get("object") == "chat.completion.chunk":
                delta = payload["choices"][0]["delta"].get("content", "")
                if delta:
                    yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/")
def home():
    return FileResponse("app/static/index.html")
