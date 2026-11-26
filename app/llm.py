"""LLM 客户端层：业务只依赖 LLMClient 协议，测试可注入 Fake 实现。

这是整个重构最关键的一处"接缝"：
- 生产：DeepSeekClient 走真实 HTTP
- 测试：FakeLLM 零成本、确定性返回
没有这层，所有用例都只能打真网络。
"""
import json
from dataclasses import dataclass
from typing import Iterator, Protocol

import requests

from app.config import Settings
from app.errors import LLMTimeoutError, UpstreamError


@dataclass
class LLMResult:
    content: str
    usage: dict


class LLMClient(Protocol):
    def complete(self, messages: list[dict]) -> LLMResult: ...
    def stream(self, messages: list[dict]) -> Iterator[str]: ...


class DeepSeekClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, messages: list[dict], stream: bool) -> dict:
        return {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "stream": stream,
        }

    def _post(self, messages: list[dict], stream: bool):
        try:
            return requests.post(
                f"{self.settings.base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, stream),
                timeout=self.settings.timeout,
                stream=stream,
            )
        except requests.Timeout as e:
            raise LLMTimeoutError() from e
        except requests.RequestException as e:
            raise UpstreamError(f"连接大模型失败: {e.__class__.__name__}") from e

    def complete(self, messages: list[dict]) -> LLMResult:
        resp = self._post(messages, stream=False)
        if resp.status_code != 200:
            raise UpstreamError(f"上游返回 {resp.status_code}")
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise UpstreamError("上游响应缺少 choices/message") from e
        if not content:
            raise UpstreamError("上游返回空回答")
        return LLMResult(content=content, usage=data.get("usage", {}))

    def stream(self, messages: list[dict]) -> Iterator[str]:
        # 注意：这里是"立即发请求"再返回生成器。
        # 若写成生成器函数，异常要等第一次迭代才抛出，状态码已锁定 200 —— 502 就测不出来了。
        resp = self._post(messages, stream=True)
        if resp.status_code != 200:
            raise UpstreamError(f"上游返回 {resp.status_code}")
        return self._iter_deltas(resp)

    @staticmethod
    def _iter_deltas(resp) -> Iterator[str]:
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            payload = line[len("data: "):]
            if payload == "[DONE]":      # 上游哨兵不是 JSON，必须特判
                break
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue                  # 单块坏数据不应打断整个流
            choices = obj.get("choices") or [{}]
            delta = (choices[0].get("delta") or {}).get("content", "")
            if delta:
                yield delta
