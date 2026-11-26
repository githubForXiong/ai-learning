"""订单查询（模拟后端）。

真实系统这里是「工具调用」：LLM 决定要不要查、带什么参数，
由服务端去调订单中心。本项目用内存字典模拟，重点是把"查订单"这条
业务链路做出来，让测试能覆盖"回答是否基于订单真实数据"。
"""

ORDERS: dict[str, dict] = {
    "20240001": {
        "status": "已签收",
        "item": "轻跑运动鞋 42码",
        "signed_days_ago": 2,
        "refundable": True,
    },
    "20240002": {
        "status": "运输中",
        "item": "蓝牙耳机",
        "carrier": "顺丰",
        "last_update": "上海转运中心，3 天前",
        "refundable": False,
    },
    "20240003": {
        "status": "待发货",
        "item": "保温杯 500ml",
        "refundable": True,
    },
}


def lookup_order(order_no: str) -> str | None:
    """查到就返回一段可直接展示的事实描述，查不到返回 None。"""
    info = ORDERS.get(order_no)
    if not info:
        return None

    if info["status"] == "运输中":
        return (
            f"订单 {order_no}：{info['item']}正在运输中，承运商{info['carrier']}，"
            f"最新轨迹：{info['last_update']}。若 24 小时仍无更新，可为您催件。"
        )
    if info["status"] == "待发货":
        return f"订单 {order_no}：{info['item']}待发货，可在订单页直接取消并原路退款。"
    return (
        f"订单 {order_no}：{info['item']}已签收 {info['signed_days_ago']} 天，"
        f"在 7 天无理由期内，可申请退货或换货。"
    )
