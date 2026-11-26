"""L3 Web E2E 测试：用 Playwright 扮演"坐在浏览器前的真实用户"。

与第6章接口测试的本质区别：
- 接口测试：直接发 HTTP，验证契约。测不到"用户看得见的东西"。
- E2E 测试：真的开浏览器、点按钮、看页面。测的是"整条链路端到端可用"。

本章两个技术难点：
1. 流式回答的等待策略——回答是"长出来的"，不能立刻断言全文；
2. 前端内存里的 history——这个状态只存在于浏览器里，接口测试根本碰不到。

运行前提：source .env 后 pytest tests/test_e2e -v
"""
import time

import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.fixture(scope="session")
def browser():
    """整个会话只启动一次浏览器（启动成本高，别每条用例都开）。"""
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture()
def page(browser, base_url):
    """每条用例一个干净的浏览器上下文：相当于"新开一个无痕窗口"，
    互不共享 localStorage / history，用例之间完全隔离。"""
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.goto(base_url)          # base_url 已由 conftest 保证服务就绪
    yield pg
    ctx.close()


# ---------------- A级：页面契约（不调大模型，秒级） ----------------

def test_page_loads(page):
    """打开首页：标题、输入框、按钮都在，且按钮可用。"""
    expect(page.locator("h2")).to_have_text("AI客服小D")
    expect(page.locator("#input")).to_be_visible()
    expect(page.locator("#input")).to_have_attribute("placeholder", "请输入您的售后问题…")
    expect(page.locator("#send")).to_have_text("发送")
    expect(page.locator("#send")).to_be_enabled()


def test_empty_input_does_not_send(page):
    """空输入点发送：不应该产生任何气泡（前端 return 掉）。

    注意：这里用"计数不变"做负向断言，必须等一小段时间，
    因为负向断言没有"事件"可以等。800ms 是 E2E 负向断言的常见折中。
    """
    before = page.locator(".msg").count()
    page.click("#send")
    page.wait_for_timeout(800)
    assert page.locator(".msg").count() == before


def test_whitespace_input_does_not_send(page):
    """纯空格也应被前端 trim 掉。"""
    page.fill("#input", "   ")
    before = page.locator(".msg").count()
    page.click("#send")
    page.wait_for_timeout(800)
    assert page.locator(".msg").count() == before


# ---------------- B级：完整闭环（真实调用） ----------------

def test_full_chat_roundtrip(page):
    """用户视角的完整闭环：输入 → 点击 → 用户气泡 → AI 回答 → 按钮恢复。"""
    page.fill("#input", "退款多久到账？")
    page.click("#send")

    # 1) 用户气泡立刻出现，内容一致（A级）
    expect(page.locator(".msg.user").last).to_have_text("退款多久到账？")
    # 2) 输入框被清空（A级）
    expect(page.locator("#input")).to_have_value("")

    # 3) ★ 流式等待策略：不 sleep，而是等"结束信号"——发送按钮恢复可点
    #    这个信号由前端 finally 块保证，比任何固定 sleep 都可靠。
    expect(page.locator("#send")).to_be_enabled(timeout=60000)

    # 4) 此时才能断言全文（B级）
    final = page.locator(".msg.bot").last.inner_text()
    assert len(final) > 5, f"回答过短: {final!r}"
    assert any(w in final for w in ("退款", "工作日", "到账", "银行", "渠道", "客服")), \
        f"回答与退款无关: {final[:60]}"


def test_streaming_renders_progressively(page):
    """证明"真流式"：回答文字是逐步长出来的，而不是最后一次性出现。

    做法：点击后每 40ms 采样一次气泡文本长度，记录长度序列。
    ⚠️ 这是全课程最容易 flaky 的一条用例：若回答极快(<40ms)就结束，
       可能采不到中间态。真实工作中应放宽断言或标记为"非阻塞用例"。
    """
    page.fill("#input", "请详细说明退款、换货、物流、质量问题各自的处理流程")
    page.click("#send")

    bot = page.locator(".msg.bot").last
    lengths = []
    deadline = time.time() + 60
    while time.time() < deadline:
        lengths.append(len(bot.inner_text()))
        if page.locator("#send").is_enabled():   # 流结束
            break
        page.wait_for_timeout(40)

    final = bot.inner_text()
    assert len(final) > 20, f"回答过短，可能请求失败: {final!r}"
    assert len(lengths) >= 2, f"采样太少，无法判断流式: {lengths}"
    assert any(a < b for a, b in zip(lengths, lengths[1:])), \
        f"未观察到增量渲染（可能是假流式）: {lengths[:10]}..."


def test_multi_turn_history_lives_in_browser(page):
    """E2E 才能覆盖的点：多轮 history 保存在浏览器内存里。
    第6章接口测试必须手工构造 history；这里用户只管连续提问，前端自动攒历史。
    """
    # 第一轮：交代商品与问题
    page.fill("#input", "我买的鞋子开胶了")
    page.click("#send")
    expect(page.locator("#send")).to_be_enabled(timeout=60000)

    # 第二轮：省略主语追问，考验前端是否把历史带上了
    page.fill("#input", "那运费谁出？")
    page.click("#send")
    expect(page.locator("#send")).to_be_enabled(timeout=60000)

    bots = page.locator(".msg.bot")
    assert bots.count() == 2, "应有两轮回答"
    last = bots.last.inner_text()
    assert any(w in last for w in ("运费", "承担", "报销", "垫付", "质量问题")), \
        f"第二轮回答没体现上下文: {last[:80]}"
