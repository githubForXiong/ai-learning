"""数据结构：请求/响应的契约在这里定义，接口层与业务层共用。"""
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)   # 空输入在门口就被拒绝（第6章红灯用例驱动）
    history: list[ChatMessage] = []      # 兼容模式：调用方自带历史（旧客户端）
    session_id: str | None = None        # 推荐模式：历史存服务端，客户端只带 id


class ChatReply(BaseModel):
    reply: str
    usage: dict = {}
    prompt_version: str = ""
    # 可观测性：这次回答走了哪条路径（llm / faq / order / human）
    route: str = "llm"
    session_id: str | None = None


class RagReply(BaseModel):
    reply: str
    sources: list[str] = []      # 引用了哪些知识库文档（可追溯）
    usage: dict = {}
    prompt_version: str = ""
    route: str = "rag"
