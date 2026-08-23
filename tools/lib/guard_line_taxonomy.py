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
  · 強制歸斷言（ADR-XPLAT-013 M1）：同一行還有**別的** statement 起點的行——
    `""; x = 1` 這種裸字串前綴會讓整行落進字串節點的 `(lineno, end_lineno)` 而免費，
    是與 docstring↔`#` 同型、且更寬的套利門（實測 −43.4%）。見 `_shared_code_lines()`。
  · 讀檔一律 `utf-8-sig`；`ast.parse()` 失敗即標記 `unparseable`、不中止呼叫端
    的逐檔迴圈（條文一 §4）。
"""
from __future__ import annotations

import ast
import io
import tokenize
from collections.abc import Iterable
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


def _string_expr_nodes(tree: ast.AST) -> list[ast.Expr]:
    """docstring／裸字串的 `Expr(Constant(str))` 節點清單。

    刻意不用 `ast.get_docstring()`：那只認每個 body 的**第一個**元素，會漏掉
    條文二 §2 要求的「非傳統位置裸字串仍算敘事」（例如函式中段插入的說明字串）。
    直接掃全樹的 `Expr(Constant(str))` 節點同時涵蓋兩種情形。
    """
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ]


def _shared_code_lines(tree: ast.AST, string_exprs: Iterable[ast.Expr]) -> set[int]:
    """「同一行還有別的 statement 起點」的行號（ADR-XPLAT-013 M1 的門）。

    🔴 為什麼非有這一格不可（複審實測的套利門）：`Expr(Constant(str))` 的
    `(lineno, end_lineno)` 涵蓋整個**物理行**，於是在任一行前面加一個裸字串 ＋ 分號
    （`""; x = 1`）就能把該行整行判成敘事 ⇒ **免費**。實測在真的受計價檔上機械套用
    （raw 行數與每一個 AST 邏輯節點皆逐字不變）：`.claude/hooks/block_destructive_git.py`
    的 `assertion` 由 558 掉到 316（−43.4%）。舊判準對這招是**懲罰**的（`#` 前綴會被
    `; ` 破壞而失去免費資格），新判準若不補這一格就變成**獎勵** ⇒ 門不是關掉，是搬家
    並變寬。唯一擋得住它的 ruff E702 在 `.claude/hooks/` 沒有任何閘門，不能當依靠。

    判準＝「**別人的** statement 起點」：字串本身那些 `Expr` 節點的 `lineno` 要排除，
    否則每個 docstring 的第一行都會被自己打成斷言（整批假紅）。刻意只看 `lineno` 而不看
    `end_lineno` 涵蓋面——`ast.stmt` 的 span 會**包住自己的 body**（`FunctionDef` 的
    span 涵蓋它的 docstring），看涵蓋面等於把所有函式／類別的 docstring 全部沒收。
    只看起點的殘留形態（把語句拆成多物理行、再在最後一行綴 `; ""`）實測是**收支平衡**
    而非套利：綴出來的那一行免費，但拆行時多出來的物理行本身就是斷言，淨額為 0。
    """
    owned = {id(node) for node in string_exprs}
    return {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.stmt) and id(node) not in owned
    }


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
    string_exprs = _string_expr_nodes(tree)
    shared = _shared_code_lines(tree, string_exprs)
    narrative: set[int] = set()
    for node in string_exprs:
        end = getattr(node, "end_lineno", node.lineno)
        for ln in range(node.lineno, min(end, total) + 1):
            if ln not in blank and ln not in shared:
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
