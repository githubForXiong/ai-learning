import os
import subprocess
import sys
import time

import pytest
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
GOOD_BASE = "http://127.0.0.1:8123"
BAD_BASE = "http://127.0.0.1:8124"


def _start(port: int, api_key: str) -> subprocess.Popen:
    env = dict(os.environ)
    env["DEEPSEEK_API_KEY"] = api_key
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _wait_ready(base: str, timeout: float = 20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(base + "/", timeout=1).status_code == 200:
                return
        except requests.ConnectionError:
            time.sleep(0.3)
    raise RuntimeError(f"服务未能在 {timeout}s 内就绪: {base}")


@pytest.fixture(scope="session")
def base_url():
    """正常服务器：使用 .env 里的真实 Key。"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    assert key, "请先 source .env 再运行测试（export DEEPSEEK_API_KEY=...）"
    p = _start(8123, key)
    _wait_ready(GOOD_BASE)
    yield GOOD_BASE
    p.terminate()


@pytest.fixture(scope="session")
def badkey_base_url():
    """坏 Key 服务器：上游必然 401，用来真实触发 502 分支。"""
    p = _start(8124, "sk-invalid-for-testing")
    _wait_ready(BAD_BASE)
    yield BAD_BASE
    p.terminate()
