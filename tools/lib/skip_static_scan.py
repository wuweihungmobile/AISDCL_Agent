#!/usr/bin/env python3
"""職責②：讀**原始碼 AST**，抽 skip 站點、判方向、分類（不執行任何測試）。

與職責④（`skip_runtime_report`，讀 `unittest.TestResult`）互補：runtime 面只在**非**
Windows 上說話（在 Windows 上照掃必然假紅，見該模組），本面不看當前平台 ⇒ 三個平台
都說話，補上 runtime 面在 Windows 的早退。

政策常數一律取自 `skip_tag_policy`（職責①），本模組**不得**自帶第二份字面值。
關鍵詞面／標籤面刻意以**參數注入**（`hints`／`tag`／`tags`）：`tools/lib/windows_skip_tags.py`
的 facade 會把它自己命名空間裡的常數傳進來，讓既有
`mock.patch.object(windows_skip_tags, "_WINDOWS_LIKE_SKIP_HINTS", …)` 這類測試注入照樣
生效（那是 `tools/tests/test_run_root_unittests.py` 明文鎖住的契約：換掉共用關鍵詞面後
判定必須跟著變，否則就是「靜態掃描抄了一份自己的字面關鍵詞」）。
"""
from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from typing import NamedTuple

from skip_tag_policy import (
    _PREDICATE_WINDOWS_VALUE,
    _WINDOWS_LIKE_SKIP_HINTS,
    _WINDOWS_PREDICATE_SUSPECT_RE,
    NON_WINDOWS_SKIP_TAGS,
    TOOL_ABSENCE_SKIP_TAG,
    WINDOWS_NATIVE_SKIP_TAG,
)


class SkipSite(NamedTuple):
    """原始碼裡的一個 skip 站點（靜態抽取，未執行任何測試）。"""

    file: str        # 相對掃描根的檔名
    lineno: int      # 站點所在行
    target: str      # 被裝飾的 class／function 名
    decorator: str   # "skipUnless"／"skipIf"／"skipif"／"skipTest"
    condition: str   # 條件表達式的原始碼文字（判方向用；`skipTest` 為 "" 或外層 if）
    reason: str      # skip reason 的字面字串

    def label(self) -> str:
        return f"{self.file}:{self.lineno} {self.target}"


# skip 機制的呼叫名 → 「條件為真時是否 skip」。
#   `skipIf`／pytest 的 `skipif`：條件為真 ⇒ skip。
#   `skipUnless`：條件為真 ⇒ **不** skip。
# 🔴 R74 把 pytest 形態納入（PKG-4 D）：R72 建立的方向感知判準只認 `unittest` 的
# decorator，實測「同一個缺陷改寫成 `@pytest.mark.skipif(...)` 即零訊號」。
_SKIP_CALL_SKIPS_WHEN_TRUE: dict[str, bool] = {
    "skipIf": True,
    "skipif": True,       # pytest.mark.skipif（reason 走 keyword，見 `_skip_reason_of`）
    "skipUnless": False,
}

#: 🔴 R75 新增（QA-R74-02 第 3 點）：函式體內的 `self.skipTest(reason)`。
#: 它**沒有條件引數**（條件寫在外層 `if`，或根本是無條件 skip），故方向天生判不出來
#: ——但「判不出來」不等於「可以隱形」。納入抽取面後它會被歸入 `runtime-skipTest`
#: 類別並進入普查棘輪，數字因此可被稽核。
_RUNTIME_SKIP_CALL = "skipTest"

#: 站點分類（`site_class()` 的值域）。每個被抽到的站點必落在其中恰一格。
SITE_CLASS_WINDOWS_ONLY = "windows-only"        # 非 Windows 才 skip（Windows 專屬測試）
SITE_CLASS_POSIX_ONLY = "posix-only"            # Windows 才 skip（POSIX 專屬測試）
SITE_CLASS_TOOL_ABSENCE = "tool-absence"        # 缺工具／缺環境才 skip，與平台無關
SITE_CLASS_RUNTIME_SKIPTEST = "runtime-skipTest"  # 函式體內 skipTest，無條件引數
SITE_CLASS_UNCLASSIFIED = "unclassified"        # 以上皆非 ⇒ 必須被逐筆點名
SITE_CLASSES: tuple[str, ...] = (
    SITE_CLASS_WINDOWS_ONLY, SITE_CLASS_POSIX_ONLY, SITE_CLASS_TOOL_ABSENCE,
    SITE_CLASS_RUNTIME_SKIPTEST, SITE_CLASS_UNCLASSIFIED,
)


def _call_name(func: ast.AST) -> str:
    return str(getattr(func, "attr", None) or getattr(func, "id", None) or "")


def _skip_reason_of(call: ast.Call) -> str | None:
    """取 skip 的 reason 字面字串；取不到（變數／f-string／`.format()`）回 None。

    `unittest` 把 reason 放在**位置引數**、pytest 放在 **`reason=` keyword**——
    R72 版只讀 `args[1]`，於是每一個 pytest 站點都在 `len(deco.args) < 2` 那行被
    整個丟掉（連「未登記述詞」的漏登記守衛都看不到它）。兩種形態都要認。
    """
    candidates: list[ast.AST] = list(call.args[1:2])
    for kw in call.keywords:
        if kw.arg == "reason":
            candidates = [kw.value]
    if not candidates:
        return None
    try:
        reason = ast.literal_eval(candidates[0])
    except Exception:  # noqa: BLE001 — 非字面值一律略過，見 docstring
        return None
    return reason if isinstance(reason, str) else None


def _enclosing_target(tree: ast.Module, node: ast.AST) -> str:
    """`node` 最近的外層 class／function 名；模組層 skip 則回賦值目標名或 `<module>`。

    WHY 不只走 `decorator_list`（R74）：本 repo 實際存在三種等價寫法——直接當
    decorator、先存成模組常數再當 decorator（`_WINDOWS_PATHEXT_SKIP = pytest.mark.
    skipif(...)`）、以及模組級 `pytestmark = pytest.mark.skipif(...)`（整檔 skip，
    覆蓋面最大的那一種）。只走 decorator_list 會漏掉後兩種。
    """
    best: tuple[int, str] | None = None
    for parent in ast.walk(tree):
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end = getattr(parent, "end_lineno", None) or parent.lineno
            # 🔴 起點必須含 decorator 行：`FunctionDef.lineno` 指的是 `def` 那一行，
            # **不含** decorator，於是 decorator 上的 skip 呼叫（最常見的形態）落在
            # 區間外、被歸成 `<module>`——訊息會指不到那支測試。
            start = min([parent.lineno, *(d.lineno for d in parent.decorator_list)])
            if start <= node.lineno <= end:
                if best is None or start > best[0]:
                    best = (start, parent.name)
    if best is not None:
        return best[1]
    for stmt in ast.walk(tree):
        if isinstance(stmt, ast.Assign) and stmt.value is node:
            names = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
            if names:
                return names[0]
    return "<module>"


def skip_decorator_sites(sources: Mapping[str, str]) -> list[SkipSite]:
    """純函式（無 I/O 副作用）：從 `{檔名: 原始碼}` 抽出所有 reason 為**字面字串**的
    skip 站點（含 R75 起納入的函式體內 `self.skipTest(...)`）。

    reason 取不到字面值時**略過而不猜**——本掃描判的是「寫在原始碼裡的那串話」，取不到
    就沒有可判的東西。這是刻意的判準邊界，不是遺漏：那類站點的可見度仍由 runtime 的
    `report_all_skips` 承接。

    名稱沿用 `skip_decorator_sites`（大量既有引用與訊息文字指向它）；R75 起它同時含
    `skipTest` 這個**非** decorator 的形態，`decorator` 欄記其呼叫名以便對回原始碼。
    """
    sites: list[SkipSite] = []
    for name, src in sorted(sources.items()):
        tree = ast.parse(src, filename=name)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            kind = _call_name(node.func)
            if kind in _SKIP_CALL_SKIPS_WHEN_TRUE:
                reason = _skip_reason_of(node)
                condition = ast.get_source_segment(src, node.args[0]) or ""
            elif kind == _RUNTIME_SKIP_CALL:
                # `self.skipTest(reason)`：第一個引數就是 reason，沒有條件引數。
                try:
                    literal = ast.literal_eval(node.args[0])
                except Exception:  # noqa: BLE001
                    literal = None
                reason = literal if isinstance(literal, str) else None
                condition = ""
            else:
                continue
            if reason is None:
                continue
            sites.append(SkipSite(
                file=name,
                lineno=node.lineno,
                target=_enclosing_target(tree, node),
                decorator=kind,
                condition=condition,
                reason=reason,
            ))
    return sorted(sites, key=lambda s: (s.file, s.lineno))


def _leaf_value_on_windows(text: str) -> bool | None:
    """單一葉節點述詞在 Windows 上的值；判不出回 `None`。

    以**集合**語意比對而非「長度序取第一個命中」（R75／SD 追加①）：同一段文字若同時
    命中值相反的 marker，長度序會挑一個出來當答案 ＝ 猜；集合語意則明確回 `None`。
    現存 marker 之間不存在「值相反且互為子串」的配對，故正常情況只會命中一種值。
    """
    values = {value for marker, value in _PREDICATE_WINDOWS_VALUE.items() if marker in text}
    return values.pop() if len(values) == 1 else None


def _expr_value_on_windows(node: ast.AST, source: str) -> bool | None:
    """AST 真值運算：`not`／`or`／`and` 逐層求值，葉節點查登記表。

    🔴 這是 SD 追加①的正解。純字串比對對複合條件會算出**反方向**：
    `sys.platform == 'win32' or sys.platform == 'darwin'` 在 Windows 上為真（會 skip），
    但字串比對取到 `darwin` 那一個 marker 就判成 False。改成真值運算後，
    `True or <任何值>` 短路為 True、`False and <任何值>` 短路為 False，
    連「一個葉判得出、另一個判不出」的混合情形都能給出正確答案。
    """
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        inner = _expr_value_on_windows(node.operand, source)
        return None if inner is None else not inner
    if isinstance(node, ast.BoolOp):
        values = [_expr_value_on_windows(v, source) for v in node.values]
        if isinstance(node.op, ast.Or):
            if any(v is True for v in values):
                return True                                  # True or 未知 == True
            return False if all(v is False for v in values) else None
        if any(v is False for v in values):
            return False                                     # False and 未知 == False
        return True if all(v is True for v in values) else None
    return _leaf_value_on_windows(ast.get_source_segment(source, node) or "")


def _predicate_value_on_windows(condition: str) -> bool | None:
    """該述詞在 **Windows 上** 求值為 True／False；判不出方向則 `None`。

    🔴 R75 訂正原 docstring 的假宣稱（QA-R74-02 第 2 點）：原文逐字寫「未登記則 None
    （fail-open，由 `unregistered_windows_like_predicates` 收口）」。那句話**與實測不符**
    ——QA 當回合量到三棵活測試樹共 103 個站點、其中 63 筆回 `None`，而那支收口網對這
    63 筆**命中 0**（它的粗網只認 `windows|win32|nt|darwin`，而這些述詞長得像 `_BASH`／
    `_ZSH is None`／`shutil.which("git")`）。宣稱有人承接、實際無人承接，比明說沒人承接
    更糟：它讓複審者不再追查。
    現況（不抄錄原句，寫現在為真的事）：`None` 的站點由 `site_class()` 歸入
    `tool-absence`（環境／工具探針）或 `unclassified`（真的判不出），兩者**都**進
    `site_class_census()` 的棘輪；`unclassified` 另外逐筆點名。`unregistered_windows_
    like_predicates` 的射程仍只是「條件文字看起來像 Windows 述詞卻未登記」那一小類，
    不再被宣稱為 `None` 的通用收口。
    """
    text = condition.strip()
    if not text:
        return None
    try:
        expr = ast.parse(text, mode="eval").body
    except SyntaxError:
        return _leaf_value_on_windows(text)
    return _expr_value_on_windows(expr, text)


def _is_windows_predicate(condition: str) -> bool:
    """「這個述詞的方向判得出來嗎」——`unregistered_*` 的「已登記」判準。

    名稱沿用 R72（大量既有引用與訊息文字指向它）；語意自 R74 起是「已登記」而非
    「指向 Windows」，因為登記表同時容納兩種值。
    """
    return _predicate_value_on_windows(condition) is not None


def _leaf_nodes(node: ast.AST) -> list[ast.AST]:
    """把布林樹攤平成葉節點清單（`or`／`and`／`not` 以外的每個子表達式）。"""
    if isinstance(node, ast.BoolOp):
        return [leaf for v in node.values for leaf in _leaf_nodes(v)]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _leaf_nodes(node.operand)
    return [node]


def suspect_unregistered_leaves(condition: str) -> list[str]:
    """條件中「**看起來像** Windows 述詞、卻不在登記表」的葉節點源碼（R75）。

    🔴 為何必須逐葉看、不能看整條條件（R75 落地時當場實測到假紅）：
    `os.name == "nt" and _real_pwsh7() is not None` 整條含 `nt` 字樣、而整條的方向確實
    判不出來（`True and <機器相依>`），於是「整條」版判準把它報成「未登記的 Windows
    述詞」——可是它的兩個葉一個已登記、一個根本不像 Windows，**沒有任何述詞需要登記**，
    訊息給的修法是空的。逐葉看之後這筆歸零，而真正的漏登記（某個新寫法的 Windows 述詞）
    仍然抓得到。
    """
    text = condition.strip()
    if not text:
        return []
    try:
        expr = ast.parse(text, mode="eval").body
    except SyntaxError:
        leaves = [text]
    else:
        leaves = [ast.get_source_segment(text, leaf) or "" for leaf in _leaf_nodes(expr)]
    return sorted(
        {
            seg for seg in leaves
            if seg and _WINDOWS_PREDICATE_SUSPECT_RE.search(seg)
            and _leaf_value_on_windows(seg) is None
        }
    )


def is_tool_probe(site: SkipSite) -> bool:
    """這個站點是否屬「環境／工具缺席型」（R75／QA-R74-02）。

    判準是**結構性**的（不是關鍵詞表，理由見 `skip_tag_policy` 對應段落）：方向判不出來、
    且條件裡沒有任何「像 Windows 述詞卻未登記」的葉 ⇒ 它的值取決於**這台機器裝了什麼**
    （`shutil.which(...)`／`_BASH`／`any_engine_available()`／`_PG_REAL_ENABLED` …），
    不是平台常數。硬判方向一定是錯的，但它們是真實的覆蓋損失來源，必須可見、可記帳。
    """
    return (
        site.decorator != _RUNTIME_SKIP_CALL
        and skipped_platform(site) is None
        and not suspect_unregistered_leaves(site.condition)
    )


def skipped_platform(site: SkipSite) -> str | None:
    """這個站點**在哪個平台上會被 skip**：`"windows"`／`"non-windows"`／None（判不出）。

    方向＝「述詞在 Windows 上的值」×「這個 skip 機制是條件為真時 skip 還是為假時
    skip」。這是 R72 方向感知判準的完整化：R72 只有「skipUnless × 是 Windows 述詞」
    一格，其餘三格靜默判不出方向。
    """
    value_on_windows = _predicate_value_on_windows(site.condition)
    if value_on_windows is None:
        return None
    skips_when_true = _SKIP_CALL_SKIPS_WHEN_TRUE.get(site.decorator)
    if skips_when_true is None:
        return None
    return "windows" if value_on_windows == skips_when_true else "non-windows"


def site_class(site: SkipSite) -> str:
    """站點分類（R75／QA-R74-02）：每個站點必落在 `SITE_CLASSES` 恰一格。

    分類順序（先方向、後探針）刻意如此：方向判得出來時它就是平台語意，即使條件裡
    順便探了個工具（例：`skipUnless(sys.platform == "win32" and shutil.which("pwsh"))`
    ——那仍然是 Windows 專屬測試）。反過來若先看探針，這類站點會被誤歸成 tool-absence
    而失去它該有的標籤要求。
    """
    if site.decorator == _RUNTIME_SKIP_CALL:
        return SITE_CLASS_RUNTIME_SKIPTEST
    direction = skipped_platform(site)
    if direction == "non-windows":
        return SITE_CLASS_WINDOWS_ONLY
    if direction == "windows":
        return SITE_CLASS_POSIX_ONLY
    if is_tool_probe(site):
        return SITE_CLASS_TOOL_ABSENCE
    return SITE_CLASS_UNCLASSIFIED


def site_class_counts(sources: Mapping[str, str]) -> dict[str, int]:
    """`{類別: 站點數}`——**每一格都出現**（含 0），否則「某類別歸零」與「該類別忘了
    被統計」在基線表上長得一樣。"""
    counts = dict.fromkeys(SITE_CLASSES, 0)
    for site in skip_decorator_sites(sources):
        counts[site_class(site)] += 1
    return counts


def unclassified_sites(sources: Mapping[str, str]) -> list[tuple[str, str, str]]:
    """`unclassified` 站點逐筆點名 `(站點, decorator, 條件源碼)`。

    普查表只給數字，數字對不上時得知道是**哪幾筆**；這支就是那個明細。
    """
    return site_class_detail(sources, SITE_CLASS_UNCLASSIFIED)


def untagged_windows_skip_decorators(
    sources: Mapping[str, str],
    *,
    hints: Sequence[str] = _WINDOWS_LIKE_SKIP_HINTS,
    tag: str = WINDOWS_NATIVE_SKIP_TAG,
) -> list[tuple[str, str, str]]:
    """純函式：靜態找出「該帶 `[WINDOWS-NATIVE-ONLY]` 而沒帶」的 skip 站點。

    回傳 `(站點, 命中的關鍵詞, reason)`，形狀刻意與 runtime 的
    `untagged_windows_like_skips` 一致（同一個判準的兩種載具，訊息與讀法可共用）。

    判準三條同時成立才算違規：
      ① 分類為 `windows-only`（方向＝非 Windows 才 skip）；
      ② reason 命中 `hints`——講的確實是 Windows 語意；
      ③ reason 未帶 `tag`。
    `posix-only`（Windows 才 skip）**不**在射程內——那類 reason 幾乎必然提到 Windows，
    照掃就是 runtime 那道鎖在 Windows 上早退所要避開的假紅。

    為何**不**另設具名豁免面：三條判準合起來已等同「這支測試只在原生 Windows 才有驗證
    價值」的定義本身，偽陽性空間近乎為零；先開一個沒有已知用例的逃生門，只會多一個
    沒人看守的靜默出口。
    """
    out: list[tuple[str, str, str]] = []
    for site in skip_decorator_sites(sources):
        if site_class(site) != SITE_CLASS_WINDOWS_ONLY or tag in site.reason:
            continue
        lowered = site.reason.lower()
        hit = next((kw for kw in hints if kw in lowered), None)
        if hit is not None:
            out.append((site.label(), hit, site.reason))
    return sorted(out)


def untagged_non_windows_skip_decorators(
    sources: Mapping[str, str],
    *,
    tags: Sequence[str] = NON_WINDOWS_SKIP_TAGS,
) -> list[tuple[str, str]]:
    """純函式：靜態找出「在 Windows 上會 skip、卻沒標明是哪一側覆蓋損失」的站點。

    回傳 `(站點, reason)`。這是 `untagged_windows_skip_decorators` 的**對稱物**
    （R74／PKG-4 E‧F）。

    🔴 判準刻意**不**加關鍵詞條件（與 Windows 側的取捨差異）：Windows 側要求 reason 命中
    關鍵詞才判違規，是因為那一側的動機是「reason 講的明明是 Windows 語意卻沒帶標籤」。
    本側的動機不同——複審者的問題是「在 Windows 上跑掉的這一批，哪幾筆是真的少驗了
    東西」，而**方向本身就是判準**。加關鍵詞只會讓「reason 寫得含糊」變成免責條款。
    """
    return sorted(
        (site.label(), site.reason)
        for site in skip_decorator_sites(sources)
        if site_class(site) == SITE_CLASS_POSIX_ONLY
        and not any(t in site.reason for t in tags)
    )


def untagged_tool_absence_sites(
    sources: Mapping[str, str], *, tag: str = TOOL_ABSENCE_SKIP_TAG
) -> list[tuple[str, str]]:
    """純函式（R75）：`tool-absence` 站點中未帶 `[TOOL-ABSENCE]` 標籤者。

    刻意**不接上閘門的 rc**（只提供給普查與報表）：存量 60 餘筆分散在三棵樹、絕大多數
    不在單一包的檔案所有權內，一上線就判紅＝並行包互踩假紅。它們的「不隱形」由
    `site_class_census` 的棘輪保證；本支是要補標時的清單來源。
    """
    return sorted(
        (site.label(), site.reason)
        for site in skip_decorator_sites(sources)
        if site_class(site) == SITE_CLASS_TOOL_ABSENCE and tag not in site.reason
    )


def site_class_detail(sources: Mapping[str, str], wanted: str) -> list[tuple[str, str, str]]:
    """某一類別的站點明細 `(站點, decorator, 條件源碼)`——普查數字對不上時查是哪幾筆。"""
    return sorted(
        (site.label(), site.decorator, site.condition)
        for site in skip_decorator_sites(sources)
        if site_class(site) == wanted
    )


def unregistered_windows_like_predicates(
    sources: Mapping[str, str],
) -> list[tuple[str, str]]:
    """純函式：條件文字**看起來像** Windows 述詞、卻判不出方向的站點。回傳 `(站點, 條件)`。

    射程誠實劃界（R75）：它只認「**某個葉節點**的文字有 `windows`／`win32`／`nt`／
    `darwin` 字樣、而那個葉不在登記表」那一小類，**不是** `_predicate_value_on_windows`
    回 `None` 的通用收口（原 docstring 曾如此宣稱，實測對 63 筆環境探針型命中 0）。
    通用收口是 `site_class_counts` 的普查。逐葉而非整條的理由見 `suspect_unregistered_leaves`。
    """
    return sorted(
        (site.label(), ", ".join(suspects))
        for site in skip_decorator_sites(sources)
        if (suspects := suspect_unregistered_leaves(site.condition))
    )
