"""检索召回测试：纯确定性、零成本、可精确断言。

这是 RAG 测试里最"像传统测试"的部分：
检索结果完全由算法与文档决定，没有随机性，所以可以直接断言"问 X 必须命中文档 Y"。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.retrieval import retrieve   # noqa: E402

pytestmark = pytest.mark.fast

# (问题, 期望命中文档, 说明)
CASES = [
    ("退款多久能到账", "refund", "退款时效"),
    ("换货流程是什么", "exchange", "换货步骤"),
    ("物流三天没更新", "shipping", "物流停滞"),
    ("运费谁承担", "quality", "质量问题运费"),
    ("保修期多久", "warranty", "保修年限"),
    ("发票怎么开", "invoice", "开票入口"),
    ("取消订单", "cancel", "未发货取消"),
    ("七天无理由退货", "return7", "无理由规则"),
    ("转人工客服", "human", "转人工"),
    ("生鲜腐坏怎么处理", "special", "特殊商品"),
]


@pytest.mark.parametrize("query,expected_doc,desc", CASES, ids=[c[2] for c in CASES])
def test_top1_hits_expected_document(query, expected_doc, desc):
    """准确率（Top-1）：最常见的召回问题就出在"问 A 召回 B"。"""
    docs = retrieve(query)
    assert docs, f"{query!r} 未召回任何文档"
    assert docs[0]["id"] == expected_doc, f"Top-1 错误：期望 {expected_doc}，实际 {docs[0]['id']}"


@pytest.mark.parametrize("query,expected_doc,desc", CASES, ids=[c[2] for c in CASES])
def test_recall_at_3(query, expected_doc, desc):
    """召回率（Top-3）：实际系统里只要在候选集里，重排/LLM 还有机会用上。"""
    ids = [d["id"] for d in retrieve(query, top_k=3)]
    assert expected_doc in ids, f"{query!r} 的 Top-3 未包含 {expected_doc}，实际 {ids}"


def test_unrelated_query_returns_empty():
    """没有相关知识时应返回空，而不是硬凑一篇（否则会诱发胡编）。"""
    assert retrieve("今天天气怎么样") == []


def test_empty_query_returns_empty():
    assert retrieve("") == []


def test_retrieval_is_deterministic():
    """检索必须确定：同输入同输出，否则无法作为回归基线。"""
    a = retrieve("退款多久能到账")
    b = retrieve("退款多久能到账")
    assert [d["id"] for d in a] == [d["id"] for d in b]
    assert [d["score"] for d in a] == [d["score"] for d in b]


def test_results_sorted_by_score_desc():
    docs = retrieve("退款到账时间", top_k=3)
    scores = [d["score"] for d in docs]
    assert scores == sorted(scores, reverse=True)
