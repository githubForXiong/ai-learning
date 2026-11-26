"""L2 接口测试：POST /chat 的契约、校验与异常分支。
断言级别标注见 tests/PLAN.md 第4节（A硬/B约束/C软/D统计）。
真实调用用例：test_normal / test_context / test_long_input 共3次，成本可忽略。"""
import pytest
import requests


# ---------- A级：契约与校验（不花钱，进不到大模型） ----------

@pytest.mark.fast
def test_missing_message_field_returns_422(base_url):
    """缺字段 → pydantic 拦截（PLAN: R4）。"""
    r = requests.post(f"{base_url}/chat", json={}, timeout=10)
    assert r.status_code == 422                      # A
    assert "message" in r.text                       # A：错误信息应指出是哪个字段


@pytest.mark.fast
def test_message_wrong_type_returns_422(base_url):
    """类型错 → 同样拦截。"""
    r = requests.post(f"{base_url}/chat", json={"message": 123}, timeout=10)
    assert r.status_code == 422                      # A


@pytest.mark.fast
def test_empty_message_should_be_rejected(base_url):
    """★ 先红后绿用例：第3章发现的缺陷——空输入不该被转发给大模型（浪费钱+行为不当）。
    期望：4xx 拒绝。当前实现：200 + AI热情回复 → 本用例应当失败(红)。"""
    r = requests.post(f"{base_url}/chat", json={"message": ""}, timeout=30)
    assert r.status_code in (400, 422), \
        f"空输入应被拒绝，实际返回 {r.status_code}（说明请求被打到了大模型）"


# ---------- A级：上游故障分支（用坏Key服务器真实触发，不mock） ----------

@pytest.mark.fast
def test_upstream_failure_returns_502(badkey_base_url):
    """Key无效 → 上游401 → 我们应转成502并带detail（PLAN: R3）。"""
    r = requests.post(f"{badkey_base_url}/chat",
                      json={"message": "能退款吗"}, timeout=30)
    assert r.status_code == 502                      # A
    body = r.json()
    assert body["error"]["code"] == "UPSTREAM_UNAVAILABLE"   # A：机器可读的错误码
    assert body["error"]["request_id"]                       # A：可追溯


# ---------- B级：真实调用（内容不确定，只断言结构与约束） ----------

@pytest.fixture(scope="module")
def normal_answer(base_url):
    """正常问题只调一次，多条断言复用（省钱+减少flaky面）。"""
    r = requests.post(f"{base_url}/chat",
                      json={"message": "退款多久到账？", "history": []}, timeout=60)
    assert r.status_code == 200
    return r.json()


@pytest.mark.slow
@pytest.mark.needs_key
def test_normal_question_structure(normal_answer):
    assert normal_answer["reply"] != ""              # B：非空
    assert len(normal_answer["reply"]) < 3000        # B：长度上界
    assert normal_answer["usage"]["total_tokens"] > 0  # B


@pytest.mark.slow
@pytest.mark.needs_key
def test_normal_question_business_relevance(normal_answer):
    """B级约束断言：业务词命中（允许措辞不同，但必须'在说退款这事'）。"""
    assert any(w in normal_answer["reply"] for w in ("退款", "工作日", "到账", "银行", "渠道"))


@pytest.mark.slow
@pytest.mark.needs_key
def test_context_followup(base_url):
    """R5：带上下文追问——省略主语也能答对主题（内容不断言，行为断言）。"""
    history = [
        {"role": "user", "content": "我买的鞋子开胶了"},
        {"role": "assistant", "content": "质量问题可以申请退款或换货。"},
    ]
    r = requests.post(f"{base_url}/chat",
                      json={"message": "那运费谁出？", "history": history}, timeout=60)
    assert r.status_code == 200
    reply = r.json()["reply"]
    assert reply != ""
    assert any(w in reply for w in ("运费", "承担", "报销", "垫付"))  # B：说明它真用上了上下文


@pytest.mark.slow
@pytest.mark.needs_key
def test_long_input_no_crash(base_url):
    """R4边界：2000字输入不应500崩溃（接受或拒绝都算通过，崩溃才算失败）。"""
    r = requests.post(f"{base_url}/chat",
                      json={"message": "退款" * 1000}, timeout=60)
    assert r.status_code in (200, 400, 422, 502)     # A：不许出现500
    assert r.status_code != 500
