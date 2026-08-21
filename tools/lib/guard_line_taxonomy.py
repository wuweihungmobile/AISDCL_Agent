#!/usr/bin/env python3
"""護欄層「行的種類」分類器（ADR-XPLAT-012 條文一／二落地，Phase 1 觀察模式）。

把一支 `.py` 檔的每一行分成三桶——敘事（narrative）／斷言（assertion）／空白
（blank）——三桶互斥、聯集覆蓋全檔，供 `AutoClaude/tools/check_loc_budget.py
--json` 的並存欄位消費。**只印不擋**：本檔不判定 rc、不進 violations，Phase 2
若要切換為阻斷須另走複審（該 ADR 條文五 §6）。

不做的事：本檔不判斷「該不該收斂」，那是政策層的事，住
`tools/lib/guard_bucket_policy.py`（ADR-XPLAT-012 條文七：兩者管轄面實測交集為
0——本檔的軸是「行的種類」，`guard_bucket_policy` 的軸是「內容的守備標的」）。

判準摘要（全文見 ADR 條文一／二）：
  · 敘事＝docstring／裸字串（`ast.Expr(ast.Constant(str))`）涵蓋的非空白實體行
    ∪ tokenize 的整行 `#` 註解（`#` 前全為空白，行尾附掛註解不算）。
  · 強制歸斷言（優先序最高，條文一 §2）：shebang（首行 `#!`）、PEP 263 編碼
    宣告（前兩行）、`ASSERTION_PRAGMA_COMMENTS` 封閉表。
  · 讀檔一律 `utf-8-sig`；`ast.parse()` 失敗即標記 `unparseable`、不中止呼叫端
    的逐檔迴圈（條文一 §4）。
"""
from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path

#: 條文一 §2：封閉表，禁止擴表為開放式判準。與條文三的 `NARRATIVE_LEDGER_NAMES`
#: 擴表治理是兩件事，刻意不共用機制——那張表管「事先核准可算敘事」，本表管
#: 「一定不算敘事」，兩個治理方向相反，混用會讓語意對撞。
ASSERTION_PRAGMA_COMMENTS: tuple[str, ...] = ("# noqa", "# type: ignore", "# pragma: no cover")


def _is_pep263_line(line: str) -> bool:
    """PEP 263：`# -*- coding: xxx -*-` 或簡式 `# coding: xxx`，僅前兩行有效。"""
    s = line.strip()
    return s.startswith("#") and ("coding:" in s or "coding=" in s)


def _matches_pragma(comment_text: str) -> bool:
    normalized = comment_text.replace(" ", "")
    return any(normalized.startswith(p.replace(" ", "")) for p in ASSERTION_PRAGMA_COMMENTS)


def _string_expr_ranges(tree: ast.AST) -> list[tuple[int, int]]:
    """docstring／裸字串涵蓋的 `(起始行, 結束行)` 清單。

    刻意不用 `ast.get_docstring()`：那只認每個 body 的**第一個**元素，會漏掉
    條文二 §2 要求的「非傳統位置裸字串仍算敘事」（例如函式中段插入的說明字串）。
    直接掃全樹的 `Expr(Constant(str))` 節點同時涵蓋兩種情形。
    """
    return [
        (node.lineno, getattr(node, "end_lineno", node.lineno))
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ]


def classify_lines(source: str) -> tuple[set[int], set[int], set[int]]:
    """回傳 `(narrative, assertion, blank)`，1-indexed 行號，三者互斥、聯集＝全檔。

    `ast.parse()` 失敗時原樣拋出 `SyntaxError`——「跳過並標記」是呼叫端
    `classify_file()` 的責任（條文一 §4），本函式不吞例外，避免把「解析失敗」
    與「解析成功但零敘事」混成同一種回傳值。
    """
    lines = source.splitlines()
    total = len(lines)
    blank = {i for i, ln in enumerate(lines, start=1) if ln.strip() == ""}

    tree = ast.parse(source)
    narrative: set[int] = set()
    for start, end in _string_expr_ranges(tree):
        for ln in range(start, min(end, total) + 1):
            if ln not in blank:
                narrative.add(ln)

    forced_assertion: set[int] = set()
    if total >= 1 and lines[0].startswith("#!"):
        forced_assertion.add(1)
    for ln in (1, 2):
        if ln <= total and _is_pep263_line(lines[ln - 1]):
            forced_assertion.add(ln)

    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type != tokenize.COMMENT:
                continue
            lineno = tok.start[0]
            if lineno in blank or lineno > total:
                continue
            if _matches_pragma(tok.string):
                forced_assertion.add(lineno)
                continue
            if tok.line[: tok.start[1]].strip() == "":
                narrative.add(lineno)
    except tokenize.TokenizeError:
        # ast.parse() 已成功，tokenize 在此失敗屬理論邊界；敘事退化為只有 docstring
        # 判定，不中止（同條文一 §4「跳過並標記」的精神，此處是子步驟層級）。
        pass

    narrative -= forced_assertion
    assertion = {i for i in range(1, total + 1) if i not in blank and i not in narrative}
    return narrative, assertion, blank


@dataclass(frozen=True)
class FileTaxonomy:
    """單檔分類快照：三桶行數 ＋ 是否因解析失敗被跳過。"""

    narrative: int
    assertion: int
    blank: int
    unparseable: bool


def classify_file(path: Path) -> FileTaxonomy:
    """讀檔＋分類入口（條文一 §4）：`utf-8-sig` 解碼與 `ast.parse` 失敗一律「跳過並
    標記」——回傳零計數＋`unparseable=True`，讓呼叫端的逐檔迴圈不中止。
    """
    try:
        source = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return FileTaxonomy(0, 0, 0, unparseable=True)
    try:
        narrative, assertion, blank = classify_lines(source)
    except SyntaxError:
        return FileTaxonomy(0, 0, 0, unparseable=True)
    return FileTaxonomy(len(narrative), len(assertion), len(blank), unparseable=False)
