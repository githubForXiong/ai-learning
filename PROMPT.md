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
| 备份拓扑 | 三点备份：云端沙箱 ↔ GitHub ↔ 学习者本地克隆（`E:\vibe coding\ai-learning`） |

## 目录结构与各文件用途

```
/workspace
├── PROMPT.md                  ← 本文件：新对话接续入口（背景+规则+进度入口）
├── ai-learning.md             ← 项目总览：背景、目标、技术选型、约定
├── app/                       ← 第一部分：AI 客服应用（教材，第2~4章已完成）
│   ├── hello_deepseek.py      ← 第2章：命令行直连大模型脚本
│   ├── main.py                ← 第3~4章：FastAPI 后端（/chat、/chat/stream、/）
│   ├── static/index.html      ← 聊天前端（history 自存 + SSE 逐字渲染）
│   └── requirements.txt       ← requests + fastapi + uvicorn
├── tests/                     ← 第二部分：自动化测试（重点，第5章起逐章填充）
│   └── README.md              ← 各章将产出：test_api/、test_e2e/、eval/、CI、RAG测试
└── docs/
    ├── curriculum.md          ← 教学大纲（带复选框，完成一章打一个勾）
    └── lessons/               ← 每章一个讲义（ch01~ch04 已存在，含追问记录）
```

## 当前进度（AI 读这里判断下一步）

- 大纲：见 `docs/curriculum.md`，已打勾到 **第 6 章**（接口测试套件已建，16 条用例全绿）。
- **下一步 = 第 7 章《Web E2E 测试：Playwright 模拟真实用户聊天》**，要点：
  1. 安装 Playwright(Python) 与浏览器内核；
  2. 覆盖"打开页面 → 输入 → 发送 → 逐字渲染 → 回答完成"闭环；
  3. 重点：流式输出的等待策略（等 [DONE]/按钮恢复再断言全文）、定位器与断言；
  4. 讲义写入 `docs/lessons/ch07-E2E测试.md`。
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

- 本地克隆（多台机器，路径因机器而异，git 同步只认远程 URL 不认路径）：
  - 公司：`E:\vibe coding\ai-learning`（已建）
  - 家里：路径待学习者补充
- **AI 无法直接写学习者的本地**：云端变更由 AI push 到 GitHub，学习者本地自行 `git pull`；
  AI 的职责是"每次变更必 push + 回复末尾提醒 pull"。
- **目标：任何变更最终三处一致**。机制：变更方 commit+push，另一方 pull。
- 日常节奏：
  - 云端每章/每次追问记录结束 → AI push → 回复末尾提醒学习者"本地执行 git pull"；
  - 学习者本地改动（练代码/记笔记）→ 本地 `git pull` → 改 → `git add . && git commit -m "..." && git push`
    → 回云端说"我本地推了变更"，AI `git pull` 后再继续。
- 冲突预防：不双端同时编辑同一文件；本地动手前先 pull。
- 本地运行需自建 `.env`（`DEEPSEEK_API_KEY=sk-...`，不进仓库）+ `pip install -r app/requirements.txt`。
- 家里网络不稳：push 尽量交给云端做；本地 pull 失败可重试，不阻塞学习。
