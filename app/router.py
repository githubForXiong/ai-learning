"""意图路由：决定一次请求走哪条业务路径。

真实客服系统的第一道分流就在这里——大量问题根本不该进大模型：
- 订单/物流这类"查数据"的问题 → 查工具，答案必须准确
- 高频 FAQ → 直答，省钱且稳定
- 明确要人工 → 建工单
- 其余（开放问题、多轮追问）→ 交给 LLM

这层是纯函数 + 内存数据，因此可以被精确单测，不花一分钱。
"""
import json
import re
import secrets
from pathlib import Path

from app.orders import lookup_order

FAQ_PATH = Path(__file__).parent / "kb" / "faq.json"
FAQ: list[dict] = json.loads(FAQ_PATH.read_text(encoding="utf-8"))

HUMAN_KEYWORDS = ("人工", "投诉", "转人工", "客服电话")
# 订单号固定 8 位；注意别和 11 位手机号撞车（否则会把手机号当订单号查）
ORDER_NO_RE = re.compile(r"(?<!\d)(\d{8})(?!\d)")

# 只有"首轮 + 短问题"才走 FAQ 直答：
# 长问题往往包含多个诉求，直答会答非所问；多轮追问必须结合上下文。
FAQ_MAX_LEN = 15


class Route:
    LLM = "llm"
    FAQ = "faq"
    ORDER = "order"
    HUMAN = "human"


def _new_ticket() -> str:
    return "T" + secrets.token_hex(3).upper()


def match_faq(message: str) -> dict | None:
    if len(message) > FAQ_MAX_LEN:
        return None
    for item in FAQ:
        if any(k in message for k in item["keywords"]):
            return item
    return None


def route(message: str, history: list) -> tuple[str, str | None]:
    """返回 (路径名, 直答内容)。直答为 None 表示交给 LLM。"""
    if any(k in message for k in HUMAN_KEYWORDS):
        ticket = _new_ticket()
        return Route.HUMAN, (
            f"已为您转接人工客服，工单号 {ticket}，工作时间内 5 分钟内响应。"
        )

    m = ORDER_NO_RE.search(message)
    if m:
        order_no = m.group(1)
        info = lookup_order(order_no)
        if info:
            return Route.ORDER, info
        return Route.ORDER, f"未查询到订单 {order_no}，请核对订单号，或回复「人工」转接客服。"

    if not history:
        faq = match_faq(message)
        if faq:
            return Route.FAQ, faq["answer"]

    return Route.LLM, None
