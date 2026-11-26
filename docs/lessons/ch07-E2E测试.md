# 第 7 章 Web E2E 测试：Playwright 模拟真实用户聊天

> 本章目标：换一个视角——不再从网络打接口，而是**真的开一个浏览器**，像用户一样输入、点击、看回答。
> 核心难点：流式回答"什么时候才能断言"。

## 1. E2E 和接口测试到底差在哪

| | 第6章 接口测试 | 本章 E2E 测试 |
|---|---|---|
| 视角 | 服务器/开发者 | 用户 |
| 入口 | 直接 POST /chat | 打开网页 → 点按钮 |
| 覆盖 | 契约、状态码、字段 | 整条链路：页面渲染 → fetch → 后端 → 大模型 → 逐字显示 |
| 测不到 | **页面是否真的显示了** | 内部字段结构、边界码 |
| 能测到 | 接口逻辑 | **前端历史管理、按钮状态、流式渲染** |
| 速度/成本 | 秒级、便宜 | 慢、贵、易 flaky（UI 测试的老毛病） |

一句话：**接口测试证明"服务对"，E2E 证明"用户能用"。** 两者互补，不能互相替代。

## 2. 两个 E2E 独有、接口测试完全测不到的点

1. **前端内存里的 history**：多轮对话的历史存在浏览器的 JS 变量里，
   接口测试只能手工构造 history 发过去；E2E 里用户连续提问，前端自动攒——
   这条链路只有 E2E 能验证（`test_multi_turn_history_lives_in_browser`）。
2. **流式渲染过程**：接口测试只能看到"分块数据"，E2E 能看到"文字一点点长在屏幕上"
   （`test_streaming_renders_progressively`）。

## 3. 环境准备（本章踩过的坑，都写在这）

```bash
pip install playwright
# 国内网络必须用镜像，否则下载卡死：
PLAYWRIGHT_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/playwright python3 -m playwright install chromium
# Linux 还缺系统库（libatk 等）：
python3 -m playwright install-deps chromium
```

Windows 本机一般不需要 install-deps；macOS 也不需要。

## 4. 代码结构：两个 fixture + 6 条用例

```python
@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()      # 会话级：只启动一次浏览器
        yield b
        b.close()

@pytest.fixture()
def page(browser, base_url):
    ctx = browser.new_context()      # 每条用例一个"无痕窗口"
    pg = ctx.new_page()
    pg.goto(base_url)
    yield pg
    ctx.close()
```

**为什么两层 fixture**：浏览器启动 1~2 秒（贵，session 级复用）；
而浏览器上下文（context）隔离 cookie/localStorage/JS 变量（便宜，每条用例新建）——
**这正是 E2E 用例互不污染的关键**。如果所有用例共用一个 page，
第一条用例攒下的 history 会污染第二条。

## 5. 定位器：用 id，别用样式

```python
page.locator("#input")     # 输入框
page.locator("#send")      # 发送按钮
page.locator(".msg.user")  # 用户气泡
page.locator(".msg.bot")   # 机器人气泡（多个时用 .last）
```

**原则**：定位器要稳定。用 `#id` 最好，其次是语义化的 class；
**最忌讳**用 `div:nth-child(3) > span` 这种"结构位置"定位——页面改个布局就全崩。
这也是给开发提的需求：**关键元素要有稳定的 id**（测试友好性设计）。

## 6. 本章核心：流式回答的等待策略

这是全课程最容易写出 **flaky 用例**的地方。三种做法对比：

| 做法 | 代码 | 评价 |
|---|---|---|
| ❌ 固定等待 | `page.wait_for_timeout(5000)` | 慢（永远等满 5 秒）+ 不可靠（网络慢时 5 秒不够） |
| ❌ 立刻断言 | 点完就 `inner_text()` | 必然拿到空字符串或半句话 |
| ✅ **等结束信号** | `expect(page.locator("#send")).to_be_enabled(timeout=60000)` | 正解 |

**为什么"按钮恢复可点"是最好的信号**：前端在 `finally` 块里恢复按钮，
无论成功、失败、超时都会执行——它精确等价于"这次请求彻底结束了"。
**这是从代码里找"天然的完成信号"，而不是靠猜时间。**

### Playwright 的自动等待（auto-waiting）
`expect(...).to_have_text(...)` / `to_be_visible()` 会自动轮询直到超时，
不需要你写 `sleep`。这是 Playwright 相比 Selenium 最大的体验提升。

## 7. 6 条用例逐个说

| 用例 | 级别 | 作用 |
|---|---|---|
| `test_page_loads` | A | 页面契约：标题、输入框、placeholder、按钮文案与可用态 |
| `test_empty_input_does_not_send` | A | 空输入点发送不产生气泡（负向断言） |
| `test_whitespace_input_does_not_send` | A | 纯空格也被 trim 掉 |
| `test_full_chat_roundtrip` | A+B | 完整闭环：用户气泡 → 输入框清空 → 等结束 → 断言回答 |
| `test_streaming_renders_progressively` | B | **采样文本长度序列，证明"真流式"** |
| `test_multi_turn_history_lives_in_browser` | B | 两轮对话，第二轮省略主语仍能答对 → 前端历史生效 |

### 负向断言为什么要等 800ms
`test_empty_input_does_not_send` 断言"气泡数量不变"——**负向断言没有事件可等**
（你不能等一个"什么都没发生"）。所以必须等一小段时间确认"确实没发生"。
800ms 是常见折中：太短会漏判，太长拖慢整套。

### 流式证明的关键代码
```python
lengths = []
while time.time() < deadline:
    lengths.append(len(bot.inner_text()))          # 每 40ms 采样一次
    if page.locator("#send").is_enabled(): break   # 结束
    page.wait_for_timeout(40)
final = bot.inner_text()
assert any(a < b for a, b in zip(lengths, lengths[1:]))       # ① 有过增长
assert any(0 < x < len(final) for x in lengths)               # ② 采到过半截状态
```
**诚实说明**：这是全课程最可能 flaky 的一条——如果回答快到 40ms 内结束，
采不到中间态。真实项目里这类用例应标记为"非阻塞"（`@pytest.mark.flaky`
或独立的 nightly 套件），别让它挡住每次提交。

### 真实采样数据（一次实测）
```
(0ms,0) (56ms,0) (109ms,0) (159ms,0) (211ms,0) (268ms,0)
(316ms,0) (367ms,0) (414ms,0) (462ms,2) (509ms,2) (558ms,3)
(607ms,16) (657ms,37) (705ms,52) (753ms,58) ... 最终 382（共 38 次采样）
```
两个信息：
- **前 ~460ms 长度全为 0** = 首字延迟（TTFT, Time To First Token）。这段时间用户在等，
  是体验指标，第 8 章会统计。
- **之后阶梯式增长** 2→3→16→37→52→58… = 真正的增量渲染。

### `any(a < b for a, b in zip(...))` 怎么读
`zip(lengths, lengths[1:])` 把序列错位配对：`[(0,0),(0,2),(2,3),(3,16)...]`，
再逐对比较 `a < b`。只要存在一对"后一个比前一个大"，就说明观察到过增长。
`any(...)` = "任意一对满足即可"。

### 为什么还要第二条断言（`0 < x < len(final)`）
只有 ① 的话有漏洞：**假流式**（后端憋完整段再返回）会产生 `[0,0,...,0,382]`，
`0 < 382` 照样成立，用例误绿。② 要求采到"非空且短于最终答案"的中间态
（如 16、37、52），**假流式永远不会有这种状态**，才真正证明是逐块渲染。
这是本章"断言要能区分错误实现"的典型例子。

## 8. 实跑结果

```
tests/test_e2e/test_chat_ui.py  6 passed in 10.30s
全套：22 passed in 17.01s   （16 接口/单元 + 6 E2E）
```

本章环境踩坑记录（对本地复现很有用）：
1. 官方 CDN 被墙 → 换 `registry.npmmirror.com` 镜像；
2. Linux 缺 `libatk-1.0.so.0` → `playwright install-deps chromium`；
3. 沙箱重置会丢 pip 包 → 重装 `fastapi uvicorn playwright`。

## 9. 为第 8 章铺垫

到这里，**能用精确断言测的都测完了**：单元、接口、E2E。但还剩一个大问题没解决——
"这个回答到底好不好？"（有没有幻觉、有没有越界、语气对不对）。
E2E 只能断言"有回答、非空、沾边"，**质量本身没法用 `assert` 表达**。
这就是第 8 章《AI 效果评估》要解决的事。

## 追问记录

### Q1：流式输出是怎么判断的？循环往 lengths 里 append 当前文本长度，之后呢？

**答**：循环每 40ms 读一次"此刻屏幕上的文字长度"，记入 `lengths`；
按钮恢复可点就跳出。跳出后：
1. `final = bot.inner_text()` 拿最终全文；
2. 断言 `len(final) > 20`：回答真的生成了；
3. 断言 `len(lengths) >= 3`：采样次数够，否则无从判断；
4. 断言 `any(a < b for a,b in zip(lengths, lengths[1:]))`：观察到过"变长"；
5. 断言 `any(0 < x < len(final) for x in lengths)`：采到过"半截状态"——
   这条才真正排除"假流式"（一次性返回只会是 `[0,...,0,382]`）。

实测采样：前 460ms 全 0（首字延迟 TTFT），之后 2→3→16→37→52→58…→382，共 38 次。
"0 的一段"=在等首字，"阶梯上升的一段"=边生成边渲染，两者合起来就是流式的指纹。

**注意点**：`inner_text()` 每次要跨进程取 DOM，40ms 是"采样够密"与"不拖慢用例"的折中；
这类用例天然易 flaky，应放非阻塞套件。
