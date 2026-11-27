"""检索层：关键词 bigram 打分（不引入向量库）。

为什么先不用 embedding：
1. 10 篇文档规模下，bigram 交集的排序已经够准；
2. 检索确定性 → 可以被精确断言（这是本章测试的核心优势）；
3. 少一个外部依赖与一笔额外成本。

真实系统上量后再换向量检索，但"召回是否命中"的测试思路完全一致。
"""
import json
import re
from pathlib import Path

DOCS_PATH = Path(__file__).parent / "kb" / "policies.json"
DOCS: list[dict] = json.loads(DOCS_PATH.read_text(encoding="utf-8"))

_PUNCT = re.compile(r"[\s，。、；：？！“”‘’（）()《》【】,.!?:;\"'\-]+")


def bigrams(text: str) -> set[str]:
    clean = _PUNCT.sub("", text)
    if len(clean) < 2:
        return {clean} if clean else set()
    return {clean[i:i + 2] for i in range(len(clean) - 1)}


_INDEX = [(bigrams(d["title"] + d["content"]), d) for d in DOCS]


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """返回按相关度降序的文档（含 score）；无命中返回空列表。

    排序规则：得分降序，同分按 id 字典序 —— 保证结果完全确定，可被测试断言。
    """
    q = bigrams(query)
    if not q:
        return []

    scored = []
    for grams, doc in _INDEX:
        score = len(q & grams)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [{**doc, "score": score} for score, doc in scored[:top_k]]
