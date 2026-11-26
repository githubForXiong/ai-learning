"""内容安全：输入拦截 + 输出脱敏。

为什么放在业务层最前面：审核必须在"花钱调模型之前"，
否则既浪费 token，也可能把违规内容送进上游。
"""
import re

from app.errors import InputBlockedError

BLOCK_WORDS = ("炸弹", "赌博", "色情", "自杀")

PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
ID_CARD_RE = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")


def check_input(text: str) -> None:
    for word in BLOCK_WORDS:
        if word in text:
            raise InputBlockedError(f"输入包含违规内容：{word}")


def mask_output(text: str) -> str:
    """对手机号、身份证号做掩码，避免 PII 直接落进日志/前端。"""
    text = PHONE_RE.sub(lambda m: m.group(1)[:3] + "****" + m.group(1)[7:], text)
    text = ID_CARD_RE.sub(lambda m: m.group(1)[:4] + "**********" + m.group(1)[-4:], text)
    return text
