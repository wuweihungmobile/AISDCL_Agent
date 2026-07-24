"""fsm_runtime 模組內「已知外部風險 ID」全站淨化涵蓋率鎖 — R41 Architect 架構最佳化。

背景（架構層系統性缺陷偵測，非逐行找 bug）：R37 為 WindowsApps guard 建了
repo-wide 前瞻防增生鎖（DEF-101-331，見 tools/tests/test_windowsapps_guard_
cross_consistency.py::TestNoOrphanWindowsAppsImplementation），把「同一缺陷類別
在不同呼叫點反覆復發、只能逐一補洞」的架構缺口物理消滅。但 `_sanitize_component()`
（本模組淨化外部風險字串當檔名片段的 SSOT，定義於 state_loader.py）的呼叫點漏接，
是同構的另一個反覆復發缺陷類別（DEF-101-219 → DEF-101-295 → DEF-101-324/335
〔碰撞變體〕→ DEF-101-327〔P0！hub_sync.py::diff() 未淨化 rule_id，真實可利用
路徑穿越/任意檔案讀取〕→ DEF-101-328〔counterfactual_replay.py 同款漏洞〕→
DEF-101-334〔測試鑑別力補強〕），過去 7+ 輪皆是「Scan 掃到才補」的點狀修復，
從未有對稱的 repo-wide 前瞻鎖——與 WindowsApps 類別在 R37 之前的狀態完全同構。
本檔補上對稱鎖，讓「新呼叫點忘記淨化」這個根因無法再逃過機械守門，不必等下一輪
人工 Scan 掃到才發現。

方法論：
  1. `_FROZEN_RISKY_NAMES`：已知需淨化的外部風險識別字，**凍結快照**（非即時
     自舉——見下方 R41 QA 一審發現的重大修正理由）。
  2. `_ADDITIONAL_RISKY_NAMES`：極少數透過委派 wrapper（如
     `production_monitor.py::_sanitize_nfr_id()`）間接淨化、無法被自舉機制
     偵測到的名稱，逐一人工核實後登記（目前僅 `nfr_id` 一例，見該函式 R38
     docstring：委派 `state_loader._sanitize_component()` 做核心淨化）。
  3. `_GENERIC_STOPWORDS`：排除過於通用、容易在無關情境命中造成誤判的通用
     wrapper 參數名（如 `_sanitize_nfr_id(text: Any)` 的 `text`）——這類名稱
     本身不具備『外部風險 ID』語意，只是委派函式的通用形參名。
  4. 對每個 f-string（`JoinedStr`），若其字面結尾符合檔名副檔名樣式
     （`.yaml`/`.yml`/`.md`/`.json`），視為『組檔名』情境；其中任何 `FormattedValue`
     若是裸引用風險名單內的識別字（未包在 `_sanitize_component(...)` 呼叫內），
     即列為 offender。
  5. 同款規則亦套用到三種非 f-string 組檔名寫法（R41 四方複審 SD 一審對抗式
     bug-injection 找到的真實偵測覆蓋率缺口，非刻意規避才觸發，屬日常寫法，
     故補齊而非僅記載為邊界）：`+` 字串串接鏈（`"..." + rule_id + ".yaml"`）、
     `%` 格式化（`"...%s.yaml" % rule_id`）、`.format()` 呼叫
     （`"...{}.yaml".format(rule_id)`）；並將 `_raw_risky_reference` 擴充涵蓋
     `ast.Subscript`（如 `record["rule_id"]` 以字串鍵取值後裸組檔名）。
  6. 【R41 QA 一審重大修正】`_FROZEN_RISKY_NAMES` 凍結為固定快照、不隨目前
     程式碼即時變動：若採用「即時」自舉（每次都從當前程式碼重新掃描哪些
     識別字仍被 `_sanitize_component()` 呼叫），移除某識別字**唯一**的呼叫點
     時，該識別字會同時從風險名單消失，讓 offender 掃描找不到裸用可比對而
     巧合通過——這正是 DEF-101-219/295/324/327/328 這類缺陷實際發生過的回歸
     模式（唯一淨化呼叫點被誤刪）。QA 實測驗證：目前 9 個風險識別字中有 6 個
     （`app_id`/`classification`/`divergence_kind`/`fpl_id`/`subagent`/
     `track_id`）僅有單一呼叫點，即時自舉版本對這 6 個完全失效。改為凍結快照
     後，即使唯一呼叫點被刪，該識別字仍留在風險名單內，裸用仍會被抓到。新增
     呼叫點若引入全新識別字名稱，由 `test_live_bootstrap_is_subset_of_frozen_
     list` 偵測「有新名稱冒出但未登記」，要求人工核實後手動加入
     `_FROZEN_RISKY_NAMES`（同 `_KNOWN_EXEMPTIONS`/`_ADDITIONAL_RISKY_NAMES`
     的人工把關模式，非自動腐化）。

方法論邊界（誠實記載，同 WindowsApps 鎖 docstring 先例，非本測試涵蓋範圍）：
  - 本檢查是逐檔 AST 靜態掃描，非真正的資料流（taint）分析，無法判斷一個識別字
    的『值』是否真的來自不可信外部輸入——只能判斷『名稱』是否曾在別處被視為
    需淨化。內部產生的序號式 ID（如 `int_id`/`dis_id`/`exp_id`/`qid`/`spl_id`/
    `slv_id`，皆為 `_next_xxx_id()` 序號+日期組成，非外部輸入、從未流經
    `_sanitize_component()`）天然落在風險名單之外，這是自舉機制的正確副作用，
    不是遺漏。
  - 若某識別字被重新命名為完全不同的變數名後才組檔名（如 `x = ac_id` 再用
    `{x}`），本檢查不會追蹤此重新指派，屬已知盲點（同 WindowsApps 鎖不追蹤
    here-string 跨行狀態的方法論邊界同級）。
  - 透過 `globals()["_sanitize_component"](...)` 這類動態／間接呼叫派送淨化，
    AST 靜態掃描無法辨識呼叫目標，屬已知盲點（R41 SD 一審構造驗證：全 repo
    現況零實例採此寫法，非立即可利用，僅記載方法論邊界）。
  - `_KNOWN_EXEMPTIONS` 內的例外皆為人工逐一核實過有等效防護機制（非空白放行），
    附決策理由；例外清單本身有防腐化測試守著（見下方
    `test_known_exemptions_still_referenced`），但該測試僅驗證『登記例外的檔案
    仍存在』，不驗證『理由中宣稱的等效防護程式碼片段仍在該檔案內』——若日後
    等效防護被悄悄移除，本鎖不會示警，屬已知盲點（R41 Architect 複審發現，
    與 WindowsApps 鎖例外清單同級風險，判斷比例：目前僅 1 筆例外、變更需經
    人工 PR review 才會發生，暫不建置額外機械交叉驗證）。
  - `_iter_module_files()` 用 `rglob("*.py")` 遞迴掃描 `tools/fsm_runtime/` 全部
    「生產程式碼」子目錄（含 `modality/`/`formal/`/`meta_halt/`/`templates/`
    等，明確排除 `tests/`），R41 Architect 複審 bug-injection 證實先前版本用
    非遞迴 `glob("*.py")` 只掃頂層、遺漏子目錄的真實涵蓋率破口，本輪已修正為
    遞迴掃描；`tests/` 目錄排除在外，因其內容為測試固定裝置/對抗式驗證程式碼，
    非本鎖意圖守護的生產組檔名路徑。
  - `_mod_format_operands()`／`_format_call_operands()` 要求樣板字面值須直接
    緊鄰 `%`／`.format()` 運算子（`ast.Constant`）；若樣板字串被抽成模組層具名
    常數再引用（如 `_TEMPLATE = "...%s.yaml"` 後 `_TEMPLATE % rule_id`），
    `node.left`/`node.func.value` 會是 `ast.Name` 而非 `ast.Constant`，本檢查
    會跳過、不掃描（R41 SD 二審構造驗證：全 repo 現況零實例採此寫法，非立即
    可利用）。`+` 串接不受此限（葉節點列表掃描不要求樣板緊鄰運算子）。修復
    需額外靜態追蹤具名常數的字面值綁定，複雜度上升且無現存真實呼叫點，
    比照 R40 WindowsApps guard 判例（具體案例收斂、假設性更深繞過記載不強修）
    處理：僅記載為已知盲點，留待下輪若出現真實呼叫點再評估修復。
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

_FSM_RUNTIME_DIR = Path(__file__).resolve().parent.parent
_FILENAME_SUFFIXES = (".yaml", ".yml", ".md", ".json")

# 已知需淨化的外部風險識別字——凍結快照，不隨目前程式碼即時變動（見頂部
# docstring 方法論⑥／R41 QA 一審發現：即時自舉對僅有單一呼叫點的識別字完全
# 失效）。新增呼叫點若引入全新名稱，由 test_live_bootstrap_is_subset_of_frozen_
# list 提醒人工核實後手動加入本清單。
_FROZEN_RISKY_NAMES: frozenset[str] = frozenset({
    "ac_id", "app_id", "classification", "divergence_kind", "fpl_id",
    "project", "rule_id", "subagent", "track_id",
})

# 委派 wrapper 間接淨化、自舉機制偵測不到的識別字名稱（人工核實後登記，附出處）。
_ADDITIONAL_RISKY_NAMES: frozenset[str] = frozenset({
    "nfr_id",  # production_monitor.py::_sanitize_nfr_id() 委派 _sanitize_component()
})

# 過於通用的委派 wrapper 形參名，本身不具「外部風險 ID」語意，排除以降低誤判面。
_GENERIC_STOPWORDS: frozenset[str] = frozenset({"text", "value", "name", "path", "content", "data"})

# (相對檔名, 識別字名稱) → 決策理由；每筆例外都必須附人工審查過的理由，不可空白放行。
_KNOWN_EXEMPTIONS: dict[tuple[str, str], str] = {
    ("slv_generator.py", "fpl_id"): (
        "_fpl_path() 於使用前已用 FPL_ID_RE.match(fpl_id) 做 allow-list 格式驗證"
        "（不符即 raise ValueError 中止，見同檔函式本體），效果等同 "
        "_sanitize_component() 的 deny-list 淨化——機制不同（allow-list vs "
        "deny-list）但同樣阻擋路徑分隔符/路徑穿越，Architect R41 架構複審判定"
        "非漏洞，登記為已知等效防護。"
    ),
}


def _iter_module_files() -> list[Path]:
    """遞迴列舉本模組全部生產程式碼 .py 檔案（排除 tests/、__pycache__、
    __init__.py）——見頂部 docstring 方法論邊界最後一條。"""
    return sorted(
        p for p in _FSM_RUNTIME_DIR.rglob("*.py")
        if p.name != "__init__.py"
        and "__pycache__" not in p.parts
        and "tests" not in p.parts
    )


def _parse_all(files: list[Path]) -> dict[Path, ast.Module]:
    return {p: ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in files}


def _live_bootstrapped_names(trees: dict[Path, ast.Module]) -> frozenset[str]:
    """即時掃描目前程式碼內所有 `_sanitize_component(X)` 呼叫的識別字名稱。
    僅用於『凍結清單新鮮度』檢查（見 test_live_bootstrap_is_subset_of_frozen_
    list），**不**用於實際 offender 掃描——那一律用凍結快照
    `_FROZEN_RISKY_NAMES`（見頂部 docstring 方法論⑥）。"""
    names: set[str] = set()
    for tree in trees.values():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_sanitize_component"
                and node.args
            ):
                arg = node.args[0]
                if isinstance(arg, ast.Name):
                    names.add(arg.id)
                elif isinstance(arg, ast.Attribute):
                    names.add(arg.attr)
    return frozenset(names - _GENERIC_STOPWORDS)


def _risky_identifier_names() -> frozenset[str]:
    """offender 掃描實際使用的風險名單：凍結快照 ∪ 補充清單（皆人工核實過），
    不隨呼叫點增減即時變動（見頂部 docstring 方法論⑥／R41 QA 一審發現）。"""
    return frozenset((_FROZEN_RISKY_NAMES | _ADDITIONAL_RISKY_NAMES) - _GENERIC_STOPWORDS)


def _joinedstr_looks_like_filename(node: ast.JoinedStr) -> bool:
    """f-string 字面結尾若符合已知副檔名樣式，視為『組檔名』情境。"""
    tail = ""
    for part in node.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            tail = part.value
    return tail.endswith(_FILENAME_SUFFIXES)


def _binop_add_leaves(node: ast.expr) -> list[ast.expr] | None:
    """攤平 `+` 字串串接鏈為葉節點列表（左到右）；鏈中出現非 `Add` 運算子則回傳
    `None`（代表這不是單純字串串接，不在本檢查涵蓋範圍內）。"""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _binop_add_leaves(node.left)
        right = _binop_add_leaves(node.right)
        if left is None or right is None:
            return None
        return left + right
    return [node]


def _leaves_look_like_filename(leaves: list[ast.expr]) -> bool:
    """`+` 串接鏈的葉節點中，只要任一常數字面值結尾符合已知副檔名樣式，視為
    『組檔名』情境（不要求一定是最後一個葉節點，串接順序不影響判斷）。"""
    return any(
        isinstance(leaf, ast.Constant) and isinstance(leaf.value, str)
        and leaf.value.endswith(_FILENAME_SUFFIXES)
        for leaf in leaves
    )


def _mod_format_operands(node: ast.BinOp) -> tuple[str, list[ast.expr]] | None:
    """`"...%s..." % (x, y)` 或 `"...%s..." % x` 這類 `%` 格式化；回傳
    (左側字面樣板, 右側運算元列表)，非此樣式回傳 `None`。"""
    if not isinstance(node.op, ast.Mod):
        return None
    if not (isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)):
        return None
    operands = list(node.right.elts) if isinstance(node.right, ast.Tuple) else [node.right]
    return node.left.value, operands


def _format_call_operands(node: ast.Call) -> tuple[str, list[ast.expr]] | None:
    """`"...".format(x, y=z)` 這類呼叫；回傳 (模板字面值, 所有位置+關鍵字引數)，
    非此樣式回傳 `None`。"""
    if not (isinstance(node.func, ast.Attribute) and node.func.attr == "format"):
        return None
    template = node.func.value
    if not (isinstance(template, ast.Constant) and isinstance(template.value, str)):
        return None
    operands = list(node.args) + [kw.value for kw in node.keywords]
    return template.value, operands


def _raw_risky_reference(expr: ast.expr, risky_names: frozenset[str]) -> str | None:
    """若表達式是裸引用某風險識別字（未包在 _sanitize_component(...) 呼叫內），
    回傳該識別字名稱；否則回傳 None。涵蓋 `Name`／`Attribute`／`Subscript`
    （如 `record["rule_id"]` 以字串鍵取值，見頂部 docstring 方法論⑤）。"""
    if isinstance(expr, ast.Name) and expr.id in risky_names:
        return expr.id
    if isinstance(expr, ast.Attribute) and expr.attr in risky_names:
        return expr.attr
    if isinstance(expr, ast.Subscript):
        key = expr.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value in risky_names:
            return key.value
    return None


class TestSanitizeComponentCallSiteCoverage(unittest.TestCase):
    """repo-wide 前瞻防增生鎖——任何新增（或既有漏網）的組檔名呼叫點，只要用了
    模組內已知需淨化的識別字名稱卻未經 `_sanitize_component()`，就逃不過本測試
    （手法對稱套用 R40 `TestNoOrphanWindowsAppsImplementation` 的「repo-wide 掃描 +
    凍結/例外清單」模式到 `_sanitize_component()` 這個不同的 SSOT）。"""

    def test_all_filename_fstrings_sanitize_known_risky_identifiers(self) -> None:
        files = _iter_module_files()
        trees = _parse_all(files)
        risky_names = _risky_identifier_names()
        self.assertTrue(risky_names, "風險名單為空——凍結清單可能被誤清空，檢查 _FROZEN_RISKY_NAMES")

        offenders: list[str] = []

        def _record(path: Path, lineno: object, risky_name: str) -> None:
            if (path.name, risky_name) in _KNOWN_EXEMPTIONS:
                return
            offenders.append(
                f"{path.name}:{lineno} 裸用識別字 `{risky_name}`"
                "（模組內已知需經 _sanitize_component() 淨化）"
            )

        for path, tree in trees.items():
            for node in ast.walk(tree):
                if isinstance(node, ast.JoinedStr) and _joinedstr_looks_like_filename(node):
                    for value in node.values:
                        if not isinstance(value, ast.FormattedValue):
                            continue
                        risky_name = _raw_risky_reference(value.value, risky_names)
                        if risky_name is not None:
                            _record(path, getattr(value, "lineno", "?"), risky_name)
                elif isinstance(node, ast.BinOp):
                    mod_operands = _mod_format_operands(node)
                    if mod_operands is not None:
                        template, operands = mod_operands
                        if template.endswith(_FILENAME_SUFFIXES):
                            for operand in operands:
                                risky_name = _raw_risky_reference(operand, risky_names)
                                if risky_name is not None:
                                    _record(path, getattr(node, "lineno", "?"), risky_name)
                        continue
                    leaves = _binop_add_leaves(node)
                    if leaves is not None and _leaves_look_like_filename(leaves):
                        for leaf in leaves:
                            risky_name = _raw_risky_reference(leaf, risky_names)
                            if risky_name is not None:
                                _record(path, getattr(node, "lineno", "?"), risky_name)
                elif isinstance(node, ast.Call):
                    format_operands = _format_call_operands(node)
                    if format_operands is not None:
                        template, operands = format_operands
                        if template.endswith(_FILENAME_SUFFIXES):
                            for operand in operands:
                                risky_name = _raw_risky_reference(operand, risky_names)
                                if risky_name is not None:
                                    _record(path, getattr(node, "lineno", "?"), risky_name)

        self.assertEqual(
            offenders, [],
            "發現組檔名時漏接 _sanitize_component() 的已知風險識別字，疑似 "
            f"DEF-101-219/295/324/327/328 類別復發：{offenders}——新呼叫點請 "
            "import state_loader._sanitize_component 後包裝，或若確認已有等效"
            "防護，於本檔 _KNOWN_EXEMPTIONS 登記並附決策理由。",
        )

    def test_live_bootstrap_is_subset_of_frozen_list(self) -> None:
        """凍結清單新鮮度檢查（R41 QA 一審發現後新增，非阻擋機制本體）：若目前
        程式碼冒出全新識別字名稱呼叫 `_sanitize_component()`（凍結清單裡沒有），
        提醒人工核實後手動登記進 `_FROZEN_RISKY_NAMES`——防止凍結清單本身腐化、
        跟不上新呼叫點引入的新風險名稱。"""
        files = _iter_module_files()
        trees = _parse_all(files)
        live_names = _live_bootstrapped_names(trees)
        unknown = live_names - _FROZEN_RISKY_NAMES - _ADDITIONAL_RISKY_NAMES
        self.assertEqual(
            unknown, set(),
            "發現新識別字呼叫 _sanitize_component() 但未登記進 _FROZEN_RISKY_NAMES："
            f"{unknown}——人工核實此為外部風險字串後，加入 _FROZEN_RISKY_NAMES。",
        )

    def test_known_exemptions_still_referenced(self) -> None:
        """例外清單防腐化：登記例外的檔案須仍存在，避免『檔案已刪除/改名但例外
        仍宣稱豁免』的假綠洞（同 WindowsApps 鎖 test_known_call_sites_still_exist
        同一防腐化手法）。"""
        for (filename, _identifier), _reason in _KNOWN_EXEMPTIONS.items():
            self.assertTrue(
                (_FSM_RUNTIME_DIR / filename).is_file(),
                f"已登記例外的檔案遺失：{filename}",
            )

    def test_additional_risky_names_still_have_wrapper(self) -> None:
        """`_ADDITIONAL_RISKY_NAMES` 防腐化：登記的補充名稱須仍能在模組內某個
        呼叫 `_sanitize_component()` 的委派 wrapper 函式中找到同名形參，避免
        wrapper 被刪除/改名後補充清單仍宣稱涵蓋的假綠洞。"""
        files = _iter_module_files()
        trees = _parse_all(files)
        wrapper_param_names: set[str] = set()
        for tree in trees.values():
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                calls_sanitize = any(
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == "_sanitize_component"
                    for inner in ast.walk(node)
                )
                if calls_sanitize:
                    wrapper_param_names.update(a.arg for a in node.args.args)

        for name in _ADDITIONAL_RISKY_NAMES:
            self.assertIn(
                name, wrapper_param_names,
                f"`_ADDITIONAL_RISKY_NAMES` 登記的 `{name}` 已找不到對應的委派 "
                "wrapper 函式形參，登記可能已腐化，須重新核實或移除",
            )


if __name__ == "__main__":
    unittest.main()
