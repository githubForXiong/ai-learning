"""RAG 服务（旁路）：检索 → 拼上下文 → 调同一个 LLM 客户端。

与原 /chat 完全隔离：
- 原路径不检索、不改动；
- 本路径只新增，便于 A/B 对比"有无知识"的回答差异。
"""
from app.config import Settings, get_settings
from app.llm import LLMClient
from app.retrieval import retrieve

RAG_SYSTEM_PROMPT = """你是电商客服小D。请严格依据【资料】回答，规则：
1) 只能用资料中的信息作答，不得编造政策、时效、金额；
2) 资料不足以回答时，明确说"暂未查到相关规定"，并建议转人工；
3) 回答简洁、直接、专业。

【资料】
{context}
"""

NO_DOC_REPLY = "暂未查到相关售后政策，建议您回复「人工」转接客服核实。"


class RagService:
    def __init__(self, llm: LLMClient, settings: Settings | None = None):
        self.llm = llm
        self.settings = settings or get_settings()

    def reply(self, message: str, history: list[dict] | None = None) -> dict:
        docs = retrieve(message, top_k=3)

        if not docs:
            return {
                "reply": NO_DOC_REPLY,
                "sources": [],
                "usage": {},
                "prompt_version": self.settings.prompt_version,
                "route": "rag",
            }

        context = "\n".join(
            f"[{i + 1}]《{d['title']}》{d['content']}" for i, d in enumerate(docs)
        )
        messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT.format(context=context)},
            *(history or []),
            {"role": "user", "content": message},
        ]
        result = self.llm.complete(messages)
        return {
            "reply": result.content,
            "sources": [d["id"] for d in docs],       # 可追溯：这次引用了哪几篇
            "usage": result.usage,
            "prompt_version": self.settings.prompt_version,
            "route": "rag",
        }
