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

## 目录结构与各文件用途

```
/workspace
├── PROMPT.md                  ← 本文件：新对话接续入口（背景+规则+进度入口）
├── ai-learning.md             ← 项目总览：背景、目标、技术选型、约定
├── app/                       ← 第一部分：AI 客服应用（教材）
│   └── README.md              ← 目录占位说明；第 2~4 章逐章填充代码
│   （未来内容：main.py FastAPI 后端、static/index.html 聊天页、requirements.txt）
├── tests/                     ← 第二部分：自动化测试（重点）
│   └── README.md              ← 目录占位说明；第 6~9 章逐章填充脚本
│   （未来内容：test_api/ 接口测试、test_e2e/ Playwright 脚本、eval/ 效果评估）
└── docs/
    ├── curriculum.md          ← 教学大纲（带复选框，完成一章打一个勾）
    └── lessons/               ← 每章一个讲义文档
        └── ch01-链路全景.md    ← 第1章讲义+追问记录（后续章节依次新增 ch02、ch03…）
```

## 当前进度（AI 读这里判断下一步）

- 大纲：见 `docs/curriculum.md`，已打勾到 **第 1 章**。
- **下一步 = 第 2 章《第一次调用 DeepSeek》**，要点：
  1. 带学习者注册 DeepSeek、获取 API Key；
  2. 在 `app/` 写 20 行 Python 脚本直连大模型；
  3. 逐字段拆解请求/响应 JSON（messages 角色、temperature、token 用量）；
  4. 讲义写入 `docs/lessons/ch02-第一次调用大模型.md`。

## 给学习者的话

换设备只需两步：`git clone https://github.com/githubForXiong/ai-learning` →
对新对话说："读 PROMPT.md，我们继续这个项目"。
