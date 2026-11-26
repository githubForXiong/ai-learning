# 第 9 章 综合实战与 CI：把测试跑起来、跑起来不停

> 本章目标：让 25 条测试从"我手动敲命令"变成"机器自动跑"。
> 三个关键词：**分层、无人值守、密钥安全**。

## 1. 为什么必须分层：成本/速度/稳定性三角

| 层 | 条数 | 耗时 | 成本 | 稳定性 | 跑多久一次 |
|---|---|---|---|---|---|
| 快速层 fast（单元+契约+页面契约） | 13 | ~11s | 0 元 | 高 | 每次提交 |
| 慢速层 slow（真实调用+E2E 交互） | 9 | ~17s | 几分钱 | 中 | 每次提交/合并前 |
| 评估层 eval（12条×2次调用） | 3 | ~25s | 几分钱/次 | 中低 | **每天一次（nightly）** |

**核心原则**：**贵的、慢的、易 flaky 的，降低频率**。
如果评估层挂在每次提交上，一天推 20 次就烧 20 倍的钱，而且它一抖动就堵住所有人。

## 2. 分层怎么实现：pytest markers

`pytest.ini`：
```ini
markers =
    fast: 无真实模型调用，每次提交都跑
    slow: 需要真实模型调用
    needs_key: 依赖有效 Key，无 Key 自动跳过
    eval: 评估层，默认不跑
addopts = -m "not eval" -q      # 默认排除评估层
```

用法：
```bash
pytest                      # 22 条（fast+slow），跳过 eval
pytest -m fast              # 13 条，1 分钟内给结论
pytest -m "fast or slow"    # 手动指定组合
pytest -m eval -s           # 只跑评估，-s 才看得到报告表
pytest -m "not slow"        # 只要快的
```

**为什么用 marker 而不是拆目录**：目录决定"在哪"，marker 决定"属于哪类"。
同一个文件里的用例可以分属不同层（比如 `test_chat_api.py` 里 4 条 fast、4 条 slow），
**按成本/稳定性分类比按文件分类更贴近真实需要**。

## 3. 无 Key 时怎么办：自动跳过而不是失败

真实场景：开源项目里别人 fork 你的仓库提 PR，**拿不到你的 secret**。
如果测试直接红，所有人都无法合代码。做法是在 `tests/conftest.py` 加钩子：

```python
def pytest_collection_modifyitems(config, items):
    if os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return                          # 有 Key，正常跑
    skip = pytest.mark.skip(reason="未设置 DEEPSEEK_API_KEY，跳过需要真实模型调用的用例")
    for item in items:
        if "needs_key" in item.keywords:
            item.add_marker(skip)
```

**实测效果**：
```
无 Key：13 passed, 9 skipped, 3 deselected
有 Key：22 passed, 3 deselected
```
跳过（skipped）是**显式声明的"没测"**，和失败（failed）语义完全不同——
**红代表"有问题"，黄代表"没条件测"，绝不能混为一谈**。

## 4. GitHub Actions：把命令搬到云上

### `ci.yml`（提交触发）
```yaml
on:
  push: { branches: [main] }
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r app/requirements.txt -r tests/requirements.txt
      - run: python -m playwright install --with-deps chromium
      - run: pytest -m fast          # 先给结论：1 分钟
      - env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: pytest                  # 再跑完整层
```

设计要点：
1. **快层先跑**：开发者在 1 分钟内知道"基础有没有坏"，不用等完整层；
2. **secret 只通过 `${{ secrets.XXX }}` 注入**，绝不写进代码或日志；
3. `--with-deps` 一次性装好 Chromium 依赖（对应第 7 章我们手动踩的那个坑）；
4. 失败时上传日志 artifact，方便事后定位。

### `nightly.yml`（定时触发）
```yaml
on:
  schedule:
    - cron: "0 18 * * *"     # UTC 18 点 = 北京时间凌晨 2 点
  workflow_dispatch:          # 也支持手动点一下
```

要点：
- **cron 用 UTC**，要换算时区（新手最常错的地方）；
- 评估层用 `| tee eval-report.txt` 落盘，再上传 artifact——**分数要能回看趋势**；
- `set -o pipefail`：否则 `tee` 会把失败吞掉，pipeline 永远显示成功。

## 5. 密钥安全：三条铁律

1. **Key 永远不进仓库**：`.env` + `.gitignore`（第 2 章就做了）；
2. **CI 里只走 secrets**：`${{ secrets.DEEPSEEK_API_KEY }}`，GitHub 会自动打码；
3. **fork PR 拿不到 secret**：所以 `needs_key` 自动跳过不是"偷懒"，是**必须**的设计。

## 6. 实跑结果（本章验证）

| 场景 | 命令 | 结果 |
|---|---|---|
| 无 Key，只跑快层 | `pytest -m fast` | 13 passed, 12 deselected |
| 无 Key，默认全跑 | `pytest` | 13 passed, 9 skipped, 3 deselected |
| 有 Key，默认全跑 | `pytest` | 22 passed, 3 deselected |
| 评估层收集 | `pytest -m eval --collect-only -q` | 3 条（不执行，省钱） |

## 7. 工作里最容易踩的五个坑

1. **`addopts` 覆盖**：命令行 `-m eval` 会覆盖 ini 里的 `-m "not eval"`（后写的赢）。
   如果命令没生效，先 `pytest --collect-only -q` 看实际收集了什么。
2. **CI 里 flaky 用例**：第 7 章那条流式采样最容易抖。对策：单独标记、允许重试
   （`pytest-rerunfailures`），或移出阻塞门禁——**别让一条不稳的用例挡住整个团队**。
3. **secret 拼错名字**：`DEEPSEEK_API_KEY` 一个字符不对，CI 里就是"全跳过"，
   看起来绿了，其实什么都没测。**看 skipped 数量**是重要习惯。
4. **cron 时区**：所有 schedule 都是 UTC。
5. **没跑就等于没测**：本地 `-m "not eval"` 之外，要记得 nightly 真的在跑——
   去 Actions 页面看绿色勾，别假设它工作。

## 8. 到这里，测试体系闭环了

```
写代码 → push
  ├─ CI 快层（13条，1分钟）→ 立刻反馈
  ├─ CI 完整层（22条）→ 合并前把关
  └─ 每天 02:00 → 评估层（12条评测集）→ 质量趋势
```

## 9. 下一章预告

主线 9 章到此完成。第 10 章是**工作强相关的必修**：
给客服挂上迷你 RAG（知识库检索），然后补两类测试——
**检索召回测试**（确定性，可精确断言）和**忠实度测试**（回答是否基于检索文档，LLM-as-Judge）。

## 追问记录

（本章暂无追问。后续学习者的提问与解答会追加到这里。）
