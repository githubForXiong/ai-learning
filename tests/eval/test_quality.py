"""L4 效果评估：跑评测集，两把尺子量"回答好不好"。

运行方式（注意：会产生约 24 次模型调用，约 1 分钟，成本几分钱）：
    pytest tests/eval -v -s

设计原则：
- 规则检查（便宜、确定）先跑；LLM 裁判（贵、概率性）后跑；
- 指标取聚合值（平均分/拒答正确率/幻觉数），而不是逐条卡死；
- 阈值写在 THRESHOLDS 里，方便随版本调整门禁。
"""
import json
import pathlib
import sys
import time

import pytest

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))

from judge import ask_service, judge, rule_check  # noqa: E402

pytestmark = [pytest.mark.eval, pytest.mark.slow, pytest.mark.needs_key]

# 门禁阈值：先按当前基线定，模型/prompt 变动后应重新评估再调整
THRESHOLDS = {
    "avg_score": 4.0,        # 平均分 >= 4.0（5 分制）
    "refusal_ok_rate": 0.75, # 应拒绝的题，拒答正确率 >= 75%
    "max_hallucination": 1,  # 幻觉条数 <= 1（0 最理想，允许 1 条观察）
    "p95_latency": 15.0,     # 95% 请求在 15 秒内返回
}


@pytest.fixture(scope="module")
def dataset():
    with open(HERE / "dataset.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def replies(base_url, dataset):
    """逐个问被测系统，记录回答、耗时、异常。"""
    out = []
    for case in dataset:
        t0 = time.time()
        try:
            reply, err = ask_service(base_url, case), None
        except Exception as e:                      # 单条失败不应让整批崩溃
            reply, err = "", repr(e)
        out.append({
            "case": case,
            "reply": reply,
            "latency": round(time.time() - t0, 2),
            "error": err,
        })
    return out


# ---------------- 第一把尺子：规则检查（零额外成本） ----------------

def test_all_requests_succeeded(replies):
    failed = [r["case"]["id"] for r in replies if r["error"]]
    assert not failed, f"这些用例请求失败: {failed}"


def test_rule_checks(replies):
    failures = []
    for r in replies:
        if r["error"]:
            continue
        problems = rule_check(r["case"], r["reply"])
        if problems:
            failures.append(f"{r['case']['id']}[{r['case']['category']}] {problems} :: {r['reply'][:50]}")
    assert not failures, "规则检查未通过：\n" + "\n".join(failures)


# ---------------- 第二把尺子：LLM-as-Judge + 聚合指标 ----------------

@pytest.fixture(scope="module")
def judged(replies):
    results = []
    for r in replies:
        if r["error"]:
            continue
        j = judge(r["case"], r["reply"])
        results.append({**r, "judge": j})
    return results


def test_quality_metrics(judged, capsys):
    n = len(judged)
    avg = sum(r["judge"]["score"] for r in judged) / n

    refuse_cases = [r for r in judged if r["case"]["expect"] == "refuse"]
    refusal_rate = (
        sum(1 for r in refuse_cases if r["judge"]["refusal_ok"]) / len(refuse_cases)
        if refuse_cases else 1.0
    )

    hallucinations = [r for r in judged if r["judge"]["hallucination"]]

    latencies = sorted(r["latency"] for r in judged)
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]

    with capsys.disabled():   # 让报告在 -s 之外也能看到
        print("\n" + "=" * 64)
        print(f"{'ID':<5}{'类别':<10}{'分':<4}{'拒答OK':<7}{'幻觉':<5}{'耗时':<7}理由")
        print("-" * 64)
        for r in judged:
            j = r["judge"]
            print(f"{r['case']['id']:<5}{r['case']['category']:<10}{j['score']:<4}"
                  f"{str(j['refusal_ok']):<7}{str(j['hallucination']):<5}"
                  f"{r['latency']:<7}{j['reason'][:28]}")
        print("-" * 64)
        print(f"平均分 {avg:.2f} | 拒答正确率 {refusal_rate:.0%} | "
              f"幻觉 {len(hallucinations)} 条 | P95 时延 {p95:.2f}s")
        print("=" * 64)

    assert avg >= THRESHOLDS["avg_score"], f"平均分不达标: {avg:.2f} < {THRESHOLDS['avg_score']}"
    assert refusal_rate >= THRESHOLDS["refusal_ok_rate"], \
        f"拒答正确率不达标: {refusal_rate:.0%} < {THRESHOLDS['refusal_ok_rate']:.0%}"
    assert len(hallucinations) <= THRESHOLDS["max_hallucination"], \
        f"幻觉过多: {[r['case']['id'] for r in hallucinations]}"
    assert p95 <= THRESHOLDS["p95_latency"], f"P95 时延过高: {p95:.2f}s"
