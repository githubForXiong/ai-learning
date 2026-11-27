# PROMPT — 新对话接续指南

> **用法**：在任何新对话 / 新电脑里，把这个文件（或直接说"读仓库根目录的 PROMPT.md"）交给 AI，
> AI 按本文件即可完全理解项目背景、当前进度和下一步，无需重新解释。
> **AI 请注意**：读完本文件后，请先向学习者确认"从哪个章节继续"，再继续教学。

## 你是谁、你在学什么（背景）

- 学习者：软件测试工程师，有开发经验，AI 应用测试入门阶段。
- 终极目标：掌握 **AI 客服的自动化测试脚本编写**。
- 路径：亲手搭一个**最小 AI 客服 Web 应用**（只是教材），理解 AI 应用完整流程与技术链路，
  然后对它做三层自动化测试（重点）：接口层、Web E2E、AI 效果评估。

## 教学规则（AI 必须遵守）

1. **教学优先于实现**：目标是教会学习者，不是把项目做完。代码是教材，进度以学会为准。
2. **面向小白讲法**：说话简单易懂，不怕详细就怕简短难懂；每个新概念必须配例子，禁止只抛概念不解释。
3. **章节强衔接**：引入新知识时回链前面章节，预告它在后面章节的用途。
4. **讲义留存**：每章讲义 + 学习者当章追问的 Q&A，实时写入 `docs/lessons/chNN-*.md`（追加"追问记录"小节）。
5. **进度打勾**：每完成一章，更新 `docs/curriculum.md` 的复选框，并 commit + push。
6. **节奏由学习者控制**：学习者说"继续"才进下一章；说"懂了/跳过"可加速。
7. **双端同步纪律（本地+云端都要有变更）**：每次云端产生变更（章节、追问记录、代码修复），
   AI 必须当场 commit+push，并在回复末尾提醒学习者本地 `git pull`；
   学习者说"本地改了"时，AI 先 `git pull` 再继续干活；
   沙箱若被重置（表现为文件丢失/在 trae/agent 分支），先 `git fetch && git checkout main && git pull` 恢复。

## 技术决策（已定，勿重新讨论）

| 项 | 决定 |
|---|---|
| 语言/后端 | Python + FastAPI |
| 前端 | 单个 HTML 聊天页（最小结构） |
| 大模型 | DeepSeek API（OpenAI 兼容格式），学习者自行注册拿 Key |
| 接口测试 | pytest + requests |
| E2E 测试 | Playwright (Python) |
| 效果评估 | 评测集 + LLM-as-Judge |
| 分支策略 | 直接在 main 开发推送，无 PR 流程 |
| 远程仓库 | https://github.com/githubForXiong/ai-learning |
| 备份拓扑 | 三点同步：云端沙箱 ↔ GitHub ↔ 学习者本地克隆（多台机器，路径不限） |

## 目录结构与各文件用途

```
/workspace
├── PROMPT.md                  ← 本文件：新对话接续入口（背景+规则+进度入口）
├── ai-learning.md             ← 项目总览：背景、目标、技术选型、约定
├── app/                       ← AI 客服应用（v0.5 已分层重构）
│   ├── config.py              ← 配置：Settings/人设+版本号/窗口上限
│   ├── errors.py              ← 统一错误模型（code/message/request_id）
│   ├── schemas.py             ← 数据契约 ChatMessage/ChatRequest/ChatReply
│   ├── llm.py                 ← LLMClient 协议 + DeepSeekClient（SSE 解析）
│   ├── chat_service.py        ← 业务编排：审核 → 路由 → LLM → 脱敏
│   ├── router.py              ← 意图路由：faq/order/human/llm（首轮+短问题才 FAQ）
│   ├── orders.py              ← 订单查询（模拟工具调用）
│   ├── moderation.py          ← 输入违规拦截 + 手机号/身份证脱敏
│   ├── store.py               ← 服务端会话存储（TTL + 滑动窗口，返回深拷贝）
│   ├── security.py            ← 限流器（每分钟滑动窗口）
│   ├── kb/faq.json            ← 8 条 FAQ 直答库
│   ├── main.py                ← 接口：create_app(llm=...) 工厂、中间件、/healthz、路由
│   ├── static/index.html      ← 聊天前端
│   └── requirements.txt       ← requests + fastapi + uvicorn
├── tests/                     ← 第二部分：自动化测试（重点，第5章起逐章填充）
│   └── README.md              ← 各章将产出：test_api/、test_e2e/、eval/、CI、RAG测试
└── docs/
    ├── curriculum.md          ← 教学大纲（带复选框，完成一章打一个勾）
    └── lessons/               ← 每章一个讲义（ch01~ch04 已存在，含追问记录）
```

## 当前进度（AI 读这里判断下一步）

- 大纲：见 `docs/curriculum.md`，**第 1~10 章全部完成**（含 RAG 进阶）。
- **下一步可选方向**（学习者未定，勿自行开工）：
  1. 按"生产化清单"补工程化：respx Mock、jsonschema 契约、pytest-html/allure 报告、
     coverage 门禁、POM + 参数化整改；
  2. 重写第 1~9 章讲义为"问题→推演→方案对比→动手→迁移"的新教学模板；
  3. 接入 ragas/deepeval 替换轻量裁判（需先验证 Python 3.14 兼容性）；
  4. 功能扩展：多租户知识库、工具调用改为真正的 function calling、转人工回执闭环。
- **v0.5 分层重构** + **v0.6 业务能力扩展** 已完成：
  - v0.5：业务与 LLM 客户端解耦（`create_app(llm=FakeLLM())`）、统一错误体、`/healthz`、request_id
  - v0.6：意图路由（faq/order/human/llm）、8 条 FAQ 直答、订单查询、转人工工单、输入审核、PII 脱敏
  - v0.7：服务端会话（`session_id`，忽略客户端 history 防篡改）、鉴权（`REQUIRE_AUTH`+`API_KEYS`）、
    限流（`RATE_LIMIT_PER_MIN`）；三开关默认关闭，不影响本地开发
  - v0.8：旁路 RAG（`POST /chat/rag`，`/chat` 不动）；10 篇政策文档 + bigram 检索；
    召回 10 组 param 用例、忠实度裁判
  - 测试 78 条全绿（fast 69 + slow 9），另有 6 条 eval 默认排除
  - 注意：FAQ 直答改变了部分回答来源，**eval 评测集需重跑并重定基线阈值**
- 待补（生产化清单，按需推进）：服务端会话存储、重试/退避/限流、结构化日志、
  jsonschema 契约校验、respx Mock、pytest-html/allure 报告、coverage 门禁、
  POM + parametrize、ragas/deepeval 替代手搓裁判。
- 测试体系现状：
  - `pytest` 默认跑 26 条（fast 17 + slow 9），排除 eval；
  - `pytest -m fast` 17 条（无 Key 也能跑）；`pytest -m eval -s` 跑评估（约24次调用）；
  - 无 Key 时 needs_key 用例自动 skip（conftest 钩子），不会红；
  - CI：`.github/workflows/ci.yml`（push 触发）、`nightly.yml`（每日 02:00 北京时间跑 eval）。
- 环境坑位备忘（沙箱重置后常遇到）：需重装 `fastapi uvicorn playwright`；
  Chromium 走镜像 `PLAYWRIGHT_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/playwright`；
  Linux 缺库执行 `playwright install-deps chromium`。
- 测试基础设施现状：`pytest tests/` 一键跑全套；`tests/conftest.py` 起两台服务器
  （8123 正常 / 8124 坏Key 触发 502）。运行前需 `source .env`。
- 第 6 章已修复两处缺陷：空输入未拒绝（Field min_length=1）、SSE 流截断
  （event_gen 对上游 [DONE] 哨兵误用 json.loads）。
- 测试计划要点（写代码前先读）：`tests/PLAN.md` 的 R1~R9 风险、A/B/C/D 断言分级、
  用例模板 7 字段。
- 被测系统现状：`app/main.py` 提供 `POST /chat`（非流式，接口测试靶子）、
  `POST /chat/stream`（SSE 流式）、`GET /`（聊天页）；人设=电商客服小D，只答售后；
  `API Key` 在 `.env`（已 gitignore，若沙箱重置需向学习者重取）。
- 已知留白（教学刻意保留）：空输入未拒绝、流中途失败无错误信号——第 6 章用例素材。

## 工作场景对齐（影响优先级）

学习者工作中要测的 AI 客服**带知识库/RAG 检索**，因此：
- 第 8 章效果评估要重点讲"忠实度/有据可依"；
- **第 10 章《迷你 RAG 及其测试》是必修**（不是选修）：检索环节确定性可精确断言，
  生成环节非确定性用 LLM-as-Judge——正好演示"隔离确定与不确定"方法论。

## 给学习者的话

换设备只需两步：`git clone https://github.com/githubForXiong/ai-learning` →
对新对话说："读 PROMPT.md，我们继续这个项目"。

## 本地备份与同步约定（双端一致：本地+云端+GitHub 三处同步）

- 学习者在多台本地机器（家里/公司，路径不同且无需记录）各有一份克隆；git 同步只认远程 URL。
- **AI 无法直接写学习者的本地**：云端变更由 AI push 到 GitHub，学习者本地自行 `git pull`；
  学习者本地改动自行 `git pull → 改 → commit → push`，然后告知云端"本地推了变更"，AI pull 后继续。
  AI 的职责是"每次变更必 push + 回复末尾提醒 pull"。
- **目标：任何变更最终三处一致**。机制：变更方 commit+push，另一方 pull。
- 日常节奏：
  - 云端每章/每次追问记录结束 → AI push → 回复末尾提醒学习者"本地执行 git pull"；
  - 学习者本地改动（练代码/记笔记）→ 本地 `git pull` → 改 → `git add . && git commit -m "..." && git push`
    → 回云端说"我本地推了变更"，AI `git pull` 后再继续。
- 冲突预防：不双端同时编辑同一文件；本地动手前先 pull。
- 本地运行需自建 `.env`（`DEEPSEEK_API_KEY=sk-...`，不进仓库）+ `pip install -r app/requirements.txt`。
- 家里网络不稳：push 尽量交给云端做；本地 pull 失败可重试，不阻塞学习。
