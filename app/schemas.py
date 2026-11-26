"""数据结构：请求/响应的契约在这里定义，接口层与业务层共用。"""
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)   # 空输入在门口就被拒绝（第6章红灯用例驱动）
    history: list[ChatMessage] = []


class ChatReply(BaseModel):
    reply: str
    usage: dict = {}
    prompt_version: str = ""
