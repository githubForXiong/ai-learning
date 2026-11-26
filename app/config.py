"""配置层：所有可调参数集中此处，由环境变量驱动，便于测试替换与版本追溯。"""
import os
from dataclasses import dataclass

SYSTEM_PROMPT = (
    "你是电商客服小D。规则："
    "1) 只回答售后相关问题（退款、换货、物流、质量问题）；"
    "2) 与售后无关的话题，礼貌拒绝并引导回售后问题；"
    "3) 不编造公司政策，不确定的信息引导用户联系人工客服。"
)

# prompt 是核心资产，必须有版本号：改人设要能被追踪（详见第8章评估门禁）
SYSTEM_PROMPT_VERSION = "2026-11-26.v1"

# 滑动窗口上限：最多携带最近多少条历史
MAX_HISTORY = 10


@dataclass(frozen=True)
class Settings:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.3
    max_tokens: int = 500
    timeout: float = 30.0
    max_history: int = MAX_HISTORY
    system_prompt: str = SYSTEM_PROMPT
    prompt_version: str = SYSTEM_PROMPT_VERSION


def get_settings() -> Settings:
    """从环境变量构建配置。测试可传入自定义 Settings，无需环境变量。"""
    return Settings(api_key=os.environ.get("DEEPSEEK_API_KEY", ""))
