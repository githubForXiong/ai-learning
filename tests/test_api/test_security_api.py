"""鉴权与限流的接口级测试（用 FAQ 问题，不消耗模型调用）。

为什么单独起服务器：认证/限流是"应用级开关"，只能通过真实配置启动来验证。
"""
import pytest
import requests

pytestmark = pytest.mark.fast

FAQ_MSG = "退款多久到账？"     # 命中 FAQ 直答，零成本


def test_missing_api_key_rejected(auth_base_url):
    r = requests.post(f"{auth_base_url}/chat", json={"message": FAQ_MSG}, timeout=10)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_wrong_api_key_rejected(auth_base_url):
    r = requests.post(f"{auth_base_url}/chat", json={"message": FAQ_MSG},
                      headers={"X-API-Key": "wrong"}, timeout=10)
    assert r.status_code == 401


def test_valid_api_key_allowed(auth_base_url):
    r = requests.post(f"{auth_base_url}/chat", json={"message": FAQ_MSG},
                      headers={"X-API-Key": "secret-key"}, timeout=10)
    assert r.status_code == 200
    assert r.json()["route"] == "faq"


def test_healthz_is_public(auth_base_url):
    """探活不能要鉴权，否则编排系统探不到（常见事故）。"""
    assert requests.get(f"{auth_base_url}/healthz", timeout=10).status_code == 200


def test_rate_limit_returns_429(limited_base_url):
    headers = {"X-API-Key": "rate-test"}
    first = requests.post(f"{limited_base_url}/chat", json={"message": FAQ_MSG},
                          headers=headers, timeout=10)
    second = requests.post(f"{limited_base_url}/chat", json={"message": FAQ_MSG},
                           headers=headers, timeout=10)
    third = requests.post(f"{limited_base_url}/chat", json={"message": FAQ_MSG},
                          headers=headers, timeout=10)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "RATE_LIMITED"
