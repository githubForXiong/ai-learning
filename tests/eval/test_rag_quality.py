"""L5 RAG 效果评估：检索召回（确定性）+ 忠实度（LLM 裁判）。

对照业界框架（ragas / deepeval）的指标映射：
- context_recall      ← 本文件的 test_sources_recall（已在单元层用 Top-1/Top-3 更严格地覆盖）
- faithfulness        ← 本文件的 test_faithfulness（judge_faithfulness）

为什么不直接 pip 装 ragas：它依赖 langchain 全家桶，体量大且对 Python 3.14 兼容性不稳。
本文件的判分接口刻意做成"问题 + 资料 + 回答"三件套，形状与 ragas 一致，工作里可无缝替换。
"""
import json
import pathlib
import sys

import pytest
import requests

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))

from judge import judge_faithfulness           # noqa: E402
from app.retrieval import retrieve             # noqa: E402

pytestmark = [pytest.mark.eval, pytest.mark.slow, pytest.mark.needs_key]

THRESHOLDS = {
    "faithful_rate": 0.8,     # 忠实度达标率 >= 80%
}


@pytest.fixture(scope="module")
def dataset():
    with open(HERE / "dataset_rag.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def answers(base_url, dataset):
    out = []
    for case in dataset:
        r = requests.post(f"{base_url}/chat/rag",
                          json={"message": case["query"]}, timeout=60)
        assert r.status_code == 200, f"{case['id']} 请求失败: {r.status_code}"
        out.append({"case": case, "body": r.json()})
    return out


def test_sources_recall(answers):
    """引用的文档里必须包含期望文档（可追溯性的最低要求）。"""
    failures = []
    for item in answers:
        expected = item["case"]["expect_doc"]
        if expected not in item["body"]["sources"]:
            failures.append(f"{item['case']['id']} 期望引用 {expected}，实际 {item['body']['sources']}")
    assert not failures, "\n".join(failures)


def test_answers_hit_key_facts(answers):
    """B 级约束：关键事实必须以某种措辞出现（不能答得跑题）。"""
    failures = []
    for item in answers:
        reply = item["body"]["reply"]
        if not any(k in reply for k in item["case"]["must_contain"]):
            failures.append(f"{item['case']['id']} 未包含 {item['case']['must_contain']}: {reply[:50]}")
    assert not failures, "\n".join(failures)


def test_faithfulness(answers, capsys):
    results = []
    for item in answers:
        question = item["case"]["query"]
        docs = retrieve(question, top_k=3)
        context = "\n".join(f"《{d['title']}》{d['content']}" for d in docs)
        verdict = judge_faithfulness(question, context, item["body"]["reply"])
        results.append({**item, "verdict": verdict})

    rate = sum(1 for r in results if r["verdict"]["faithful"]) / len(results)

    with capsys.disabled():
        print("\n" + "=" * 68)
        print(f"{'ID':<6}{'问题':<14}{'引用':<22}{'忠实':<6}理由")
        print("-" * 68)
        for r in results:
            v = r["verdict"]
            print(f"{r['case']['id']:<6}{r['case']['query']:<14}"
                  f"{','.join(r['body']['sources'])[:20]:<22}"
                  f"{str(v['faithful']):<6}{v['reason'][:24]}")
        print("-" * 68)
        print(f"忠实度达标率 {rate:.0%}（阈值 {THRESHOLDS['faithful_rate']:.0%}）")
        print("=" * 68)

    assert rate >= THRESHOLDS["faithful_rate"], f"忠实度不足: {rate:.0%}"
