import os

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="AI客服教材")

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

SYSTEM_PROMPT = "你是电商客服小D，只回答售后相关问题（退款、换货、物流等），其他话题请礼貌拒绝。"


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(body: ChatRequest):
    resp = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY', '')}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": body.message},
            ],
            "temperature": 0.3,
            "max_tokens": 500,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="大模型服务异常")
    data = resp.json()
    return {
        "reply": data["choices"][0]["message"]["content"],
        "usage": data["usage"],
    }


@app.get("/")
def home():
    return FileResponse("app/static/index.html")
