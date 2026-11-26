# AI 客服机器人学习项目

## 背景与目标

- 学习者：软件测试工程师，有开发经验，AI 应用测试入门阶段。
- 目标：通过亲手搭建一个**最小可用的 AI 客服应用**（教材），理解 AI 应用的完整流程与技术链路，
  最终掌握 **AI 客服自动化测试脚本**的编写（重点）。
- 两部分定位：
  1. **AI 客服应用**（教材）：最小结构、最简输入输出的 Web 应用即可，为测试部分服务。
  2. **AI 客服自动化测试**（重点）：接口层测试 + Web E2E 测试 + AI 效果评估测试。

## 应用架构（v0.5，第 9 章后重构）

```
app/
├── config.py        配置层：Settings(dataclass)、人设+版本号、窗口上限
├── errors.py        错误模型：AppError / UpstreamError / LLMTimeoutError + 统一 handler
├── schemas.py       数据契约：ChatMessage / ChatRequest / ChatReply
├── llm.py           LLM 客户端：LLMClient 协议 + DeepSeekClient（SSE 解析在此）
├── chat_service.py  业务层：build_payload（纯函数）/ ChatService.reply / .stream
├── main.py          接口层：create_app(llm=...) 工厂、request_id 中间件、/healthz、路由
└── static/index.html 前端
```

设计原则：**业务只依赖 LLMClient 协议**，测试注入 FakeLLM 即可零成本、零网络验证业务逻辑。
`create_app(llm=FakeLLM())` 可起一个"假大脑"服务器。

## 技术选型

| 层 | 选择 | 理由 |
|---|---|---|
| 后端 | Python + FastAPI | AI 领域最主流生态 |
| 前端 | 单个 HTML 聊天页 | 最小结构，够用即可 |
| 大模型 | DeepSeek API（兼容 OpenAI 格式） | 性价比高、文档简洁、教程最多 |
| 接口测试 | pytest + requests | Python 测试标准组合 |
| E2E 测试 | Playwright (Python) | 主流 Web 自动化框架 |
| 效果评估 | 评测集 + LLM-as-Judge | AI 应用特有的测试方式 |

## 项目约定

- 直接在 `main` 分支开发并推送，无需分支 + PR（main 未开启分支保护）。
- 远程仓库：https://github.com/githubForXiong/ai-learning
- 教学形式：对话讲解为主，讲义沉淀到 `docs/` 目录，换设备 clone 后可复习。
- 教学风格：面向入门小白，举例解释概念，章节之间强衔接。

## 学习路线

见 [docs/curriculum.md](docs/curriculum.md)（带进度打卡）。

## 目录结构

```
├── PROMPT.md        ← 新对话接续入口（背景+规则+进度），换设备先读这个
├── ai-learning.md   ← 本文件：项目总览
├── app/             ← 第一部分：AI 客服应用（教材，随教学逐章生成）
├── tests/           ← 第二部分：自动化测试（重点，第 5 章起逐章生成）
└── docs/
    ├── curriculum.md    ← 教学大纲 + 进度复选框
    └── lessons/         ← 每章讲义 + 追问记录
```

## 进度记录

- 2026-11-25：云端环境验证通过；确定技术选型与学习路线。
- 2026-11-25：**第 1 章完成**（全景链路，讲义 ch01）；搭建目录骨架 app/、tests/、docs/lessons/；
  创建 PROMPT.md 接续机制；大纲改为进度打卡制。
- 2026-11-25：**第 2 章完成**（直连 DeepSeek 脚本跑通，状态码 200，Key 存于 .env 已 gitignore；
  追问：max_tokens 与上下文窗口区别）。
- 2026-11-25：**第 3 章完成**（FastAPI 后端 + 单页前端跑通，被测系统成型；
  发现"空输入未被拒绝"的真实缺陷，留作第 6 章测试驱动修复）。
- 2026-11-25：**第 4 章完成**（多轮上下文+人设安全边界+流式SSE，实跑三项验证通过；
  第一部分收官，被测系统完整成型）。
- 2026-11-25：讨论决定新增**第 10 章《迷你 RAG 及其测试》（必修）**——因学习者工作中被测
  的 AI 客服带知识库检索；主线 9 章不动，RAG 放最后进阶。
- 2026-11-25：**第 5 章完成**（对比实验证实非确定性+幻觉；提出"隔离不确定"方法论与 A/B/C/D
  断言分级；产出 tests/PLAN.md 测试计划）。
- 2026-11-25：**第 6 章完成**（16 条接口/单元/流式用例全绿；两次红灯：空输入缺陷修复、
  测试主动抓出 SSE 流截断 P0 bug）。
- 2026-11-26：**第 7 章完成**（Playwright E2E 6 条用例全绿，含"流式逐字渲染"与"浏览器内历史"；
  全套 22 条通过。踩坑：CDN 需换国内镜像、Linux 缺系统库需 install-deps）。
- 2026-11-26：**第 8 章完成**（12 条评测集 + LLM-as-Judge；平均 4.75~4.92 分、拒答 100%、
  幻觉 0；全套 25 条通过）。
- 2026-11-26：**第 9 章完成**（pytest markers 分层、无 Key 自动跳过、GitHub Actions
  提交触发+每日评估；主线 9 章收官）。
- 2026-11-26：**应用分层重构（v0.5）**——config/errors/schemas/llm/chat_service/main 六层；
  业务与 LLM 解耦，新增 FakeLLM 零成本用例 4 条；全套 26 条通过。
- 下一步：第 10 章《迷你 RAG：知识库检索 + 检索与忠实度测试》（工作强相关，必修）。
