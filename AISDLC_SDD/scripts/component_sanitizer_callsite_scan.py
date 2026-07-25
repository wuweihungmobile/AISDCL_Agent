"""共用 AST 靜態掃描器：偵測「組檔名時漏接 `_sanitize_component()` 淨化」的呼叫點
（R41 Architect 架構最佳化建立；R46 抽為共用層 + 補兩個已知盲區，DEF-101-378）。

沿革：本掃描邏輯原本內嵌在
`AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_sanitize_component_call_site_lock.py`，
只掃 LATEST 一個版本目錄。R46 比照 R45 `component_sanitizer.py`（淨化函式本身的
共享層）同一手法，把「掃描邏輯」也抽成共用層——原因同構：29 個凍結版本從建立
以來從未被這支 AST 掃描器檢查過（該測試檔案本身也不存在於 v0.01~v0.29 任何一
版），導致 `path_cost.py::_write_milestone()` 這個 R39 就在 LATEST 修好、但從未
回補進凍結版本的漏洞完全沒有機械訊號能發現（見 DEF-101-379）。抽出本檔後：
  - `AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_sanitize_component_call_site_lock.py`
    改為 import 本檔（不再維護自己的一份重複實作），繼續守 LATEST 未來新增呼叫點。
  - `AISDLC_SDD/scripts/tests/test_sanitize_component_callsite_frozen_versions.py`
    （新檔）用本檔對 v0.01~v0.30 全部 30 個版本做「唯讀掃描」。

Copy-on-Evolve 邊界說明：鐵律禁止的是「原地修改凍結版本的檔案內容」，不是禁止
「從外部讀取/掃描凍結版本的檔案」——本檔對凍結版本只讀不寫，不牴觸該鐵律
（先例：`tools/tests/test_windowsapps_guard_cross_consistency.py` 本就對全 repo
含凍結版本路徑做唯讀掃描）。

方法論（沿用 R41~R45，R46 新增第 7 條）：
  1. `_FROZEN_RISKY_NAMES`：已知需淨化的外部風險識別字，**凍結快照**（非即時
     自舉——見 R41 QA 一審發現：即時自舉對僅有單一呼叫點的識別字完全失效，
     唯一淨化呼叫點被誤刪時該識別字會同時從風險名單消失）。
  2. `_ADDITIONAL_RISKY_NAMES`：極少數透過委派 wrapper（如
     `production_monitor.py::_sanitize_nfr_id()`）間接淨化、無法被自舉機制
     偵測到的名稱，逐一人工核實後登記。
  3. `_GENERIC_STOPWORDS`：排除過於通用、容易在無關情境命中造成誤判的通用
     wrapper 參數名。
  4. 對每個 f-string（`JoinedStr`），若其字面結尾符合檔名副檔名樣式，視為
     『組檔名』情境；其中任何 `FormattedValue` 若是裸引用風險名單內的識別字
     （未包在 `_sanitize_component(...)` 呼叫內），即列為 offender。
  5. 同款規則亦套用到三種非 f-string 組檔名寫法：`+` 字串串接鏈、`%` 格式化、
     `.format()` 呼叫；`_raw_risky_reference` 亦涵蓋 `ast.Subscript`。
  6. 【R41 QA 一審修正】`_FROZEN_RISKY_NAMES` 凍結為固定快照、不隨目前程式碼
     即時變動；新呼叫點若引入全新識別字名稱，由
     `test_live_bootstrap_is_subset_of_frozen_list` 偵測。
  7. 【R46 新增，DEF-101-378】`_raw_risky_reference` 遞迴拆解 `ast.BoolOp`
     （`a or b` 型退回預設值寫法）與 `ast.IfExp`（`a if a else "default"` 同款
     姊妹寫法），並支援有界別名追蹤（`build_alias_map`：同一**作用域**內
     `Name = Name` / `Name = Attribute` 零轉換直接賦值鏈，最多解 5 層＋環偵測，
     寧可多幾個假陽性逼人工補 `_KNOWN_EXEMPTIONS` 理由，也不漏放；`find_offenders`
     逐作用域〔模組頂層 + 每個函式 + 每個類別，含巢狀，見 `_all_scope_nodes`〕
     獨立呼叫，避免不同函式/類別內同名變數各自的別名判斷互相碰撞——後者
     〔ClassDef 邊界〕為 R46 SD 二審 bug-injection 補上，見 §邊界清單）。

方法論邊界（誠實記載，非本掃描器涵蓋範圍——R46 僅修復 BoolOp/IfExp 與別名兩項，
下列三項仍是已知盲點，比照 Rule 2 比例原則不強修，留待出現真實呼叫點再評估）：
  - 巢狀 f-string（`f"{f'{rule_id}'}.yaml"`）——`_joinedstr_looks_like_filename`
    只掃外層 `JoinedStr` 直接子節點。
  - pathlib `/` 運算子鏈（`out_dir / rule_id / "leaf.yaml"`）——`_binop_add_leaves`
    只認 `ast.Add`，無 `ast.Div` 分支。
  - `str.join()`（`"-".join([..., rule_id]) + ".yaml"`）——`_format_call_operands`
    只認 `.format` 這一個方法名稱。
  - 透過 `globals()["_sanitize_component"](...)` 動態呼叫派送淨化，AST 靜態掃描
    無法辨識呼叫目標。
  - 別名追蹤僅限「零轉換直接賦值」（`Name = Name`/`Name = Attribute`），不追蹤
    任何運算（字串串接、函式呼叫、`.format()` 內部結果等）造成的別名。
  - 樣板字面值若被抽成模組層具名常數再引用（`_TEMPLATE = "...%s.yaml"` 後
    `_TEMPLATE % rule_id`），`_mod_format_operands`/`_format_call_operands`
    要求樣板緊鄰運算子（`ast.Constant`），具名常數引用不在掃描範圍內。
  - 【R46 SD 二審發現，記載為新盲點】別名追蹤是**逐作用域**（模組頂層／每個
    函式／每個類別，各自獨立，見方法論⑦與 `_all_scope_nodes`），不追蹤跨作用域
    的別名可見性：(a) 模組層級的別名賦值（`x = rule_id`）若在某個函式內部才被
    引用（`def emit(): return f"{x}.yaml"`），該函式作用域看不到模組層級的
    `direct` 表，不會被抓到；(b) 巢狀函式（closure）引用外層函式作用域內建立的
    別名，同樣因為各自作用域獨立而看不到。這是刻意選擇的有界設計（避免建置
    完整的 Python 詞法作用域鏈/nonlocal-global 語意解析，超出比例原則）。本檔
    是本輪新建的共用工具（非凍結版本內容），不涉及 Copy-on-Evolve 例外機制；
    誠實記載為已知限制，留待實際掃描（`test_sanitize_component_callsite_
    frozen_versions.py` 對全部版本的定期跑）出現真實呼叫點命中此限制時再評估
    是否需要補上跨作用域追蹤（R46 SA 三審修正：初版誤把「Copy-on-Evolve 例外」
    這個管制凍結版本內容修改的機制，錯誤地套用到本檔這種非凍結版本的共用
    工具身上）。
"""
from __future__ import annotations

import ast
from pathlib import Path

_FILENAME_SUFFIXES = (".yaml", ".yml", ".md", ".json")

# 已知需淨化的外部風險識別字——凍結快照，不隨目前程式碼即時變動（見方法論⑥）。
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

# (相對檔名, 識別字名稱) → 決策理由；每筆例外都必須附人工審查過的理由，不可空白
# 放行。以「檔名」而非「(版本, 檔名)」為鍵，因為同名檔案在 30 個版本間逐字相同
# （Copy-on-Evolve 逐版複製），例外理由對全部版本同等成立（Architect R46 架構
# 複審驗證：`slv_generator.py` 的 fpl_id allow-list 保護在 v0.29 與 v0.30 逐字相同）。
_KNOWN_EXEMPTIONS: dict[tuple[str, str], str] = {
    ("slv_generator.py", "fpl_id"): (
        "_fpl_path() 於使用前已用 FPL_ID_RE.match(fpl_id) 做 allow-list 格式驗證"
        "（不符即 raise ValueError 中止，見同檔函式本體），效果等同 "
        "_sanitize_component() 的 deny-list 淨化——機制不同（allow-list vs "
        "deny-list）但同樣阻擋路徑分隔符/路徑穿越，Architect R41 架構複審判定"
        "非漏洞，登記為已知等效防護。"
    ),
}


def iter_module_files(root_dir: Path) -> list[Path]:
    """遞迴列舉 `root_dir`（某版本的 `tools/fsm_runtime/`）全部生產程式碼 .py
    檔案（排除 tests/、__pycache__、__init__.py）。"""
    return sorted(
        p for p in root_dir.rglob("*.py")
        if p.name != "__init__.py"
        and "__pycache__" not in p.parts
        and "tests" not in p.parts
    )


def parse_all(files: list[Path]) -> dict[Path, ast.Module]:
    return {p: ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in files}


def live_bootstrapped_names(trees: dict[Path, ast.Module]) -> frozenset[str]:
    """即時掃描目前程式碼內所有 `_sanitize_component(X)` 呼叫的識別字名稱。
    僅用於『凍結清單新鮮度』檢查，**不**用於實際 offender 掃描（見方法論⑥）。"""
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


def risky_identifier_names() -> frozenset[str]:
    """offender 掃描實際使用的風險名單：凍結快照 ∪ 補充清單（皆人工核實過），
    不隨呼叫點增減即時變動。"""
    return frozenset((_FROZEN_RISKY_NAMES | _ADDITIONAL_RISKY_NAMES) - _GENERIC_STOPWORDS)


_SCOPE_BOUNDARY_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _direct_children_in_scope(scope_node: ast.AST):
    """遞迴 yield `scope_node` **自己作用域**內的所有節點（含巢狀 if/for/try/with
    等控制流——那些不是獨立的 Python 作用域），但**不**降階進入巢狀函式定義
    （`FunctionDef`/`AsyncFunctionDef`）或**類別定義**（`ClassDef`）的 body——
    那些是各自獨立的作用域，由呼叫端對它們各自獨立呼叫本函式（見
    `_all_scope_nodes`）。巢狀節點本身仍會被 yield 一次（供辨識該處有一個子
    作用域），只是不繼續探入其 body。

    R46 SD 二審修正：初版只把 `FunctionDef`/`AsyncFunctionDef` 當邊界，遺漏
    `ClassDef`——class body 內的屬性賦值會被當成外層（模組或外層函式）作用域
    的一部分繼續收集，導致與 R46 SD 一審同款的跨作用域同名變數碰撞（只是把
    「函式 vs 函式」換成「class body vs 外層模組層級」），可能讓 class body 內
    真正未淨化的別名被外層同名安全賦值蓋掉而漏放，直接推翻本次修復宣稱已解決
    的問題類別。"""
    for child in ast.iter_child_nodes(scope_node):
        yield child
        if isinstance(child, _SCOPE_BOUNDARY_TYPES):
            continue
        yield from _direct_children_in_scope(child)


def _all_scope_nodes(tree: ast.Module) -> list[ast.AST]:
    """列舉一個檔案內全部獨立作用域節點：模組本身（頂層陳述式）＋ 全部函式定義
    （含巢狀函式，各自獨立）＋ 全部類別定義（含巢狀類別，各自獨立；R46 SD 二審
    新增，見 `_direct_children_in_scope` docstring）。"""
    scopes: list[ast.AST] = [tree]
    for node in ast.walk(tree):
        if isinstance(node, _SCOPE_BOUNDARY_TYPES):
            scopes.append(node)
    return scopes


def build_alias_map(scope_node: ast.AST, risky_names: frozenset[str]) -> dict[str, str]:
    """R46 新增（DEF-101-378 盲區②）：`scope_node` 自己作用域內（不含巢狀函式
    body，見 `_direct_children_in_scope`）的零轉換直接別名賦值追蹤
    （`Name = Name` / `Name = Attribute`），最多解 5 層＋環偵測。刻意保守：
    寧可多幾個假陽性（逼人工於 `_KNOWN_EXEMPTIONS` 補理由），也不要漏放
    （見模組 docstring 方法論⑦）。回傳 {別名: 原始風險識別字}。

    R46 SD 一審修正：初版對整個檔案用單一 flat dict（`ast.walk(tree)` 攤平，
    不分函式作用域），導致不同函式內同名變數各自的別名判斷互相碰撞——後解析
    到的函式賦值會覆蓋先前函式的判斷結果，可能造成假陽性（安全用法被誤判）或
    更嚴重的假陰性（真正未淨化的別名被後面函式的同名安全賦值蓋掉而漏放，違反
    本函式自身「寧可假陽性也不漏放」的設計宣稱）。改為呼叫端對每個作用域節點
    （`_all_scope_nodes`）各自呼叫本函式，作用域之間互不干擾。"""
    direct: dict[str, str] = {}
    for node in _direct_children_in_scope(scope_node):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                if isinstance(node.value, ast.Name):
                    direct[target.id] = node.value.id
                elif isinstance(node.value, ast.Attribute):
                    direct[target.id] = node.value.attr

    resolved: dict[str, str] = {}
    for name in direct:
        seen = {name}
        current = name
        for _ in range(5):
            source = direct.get(current)
            if source is None:
                break
            if source in risky_names:
                resolved[name] = source
                break
            if source in seen:
                break
            seen.add(source)
            current = source
    return resolved


def joinedstr_looks_like_filename(node: ast.JoinedStr) -> bool:
    """f-string 字面結尾若符合已知副檔名樣式，視為『組檔名』情境。"""
    tail = ""
    for part in node.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            tail = part.value
    return tail.endswith(_FILENAME_SUFFIXES)


def binop_add_leaves(node: ast.expr) -> list[ast.expr] | None:
    """攤平 `+` 字串串接鏈為葉節點列表（左到右）；鏈中出現非 `Add` 運算子則回傳
    `None`（代表這不是單純字串串接，不在本檢查涵蓋範圍內）。"""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = binop_add_leaves(node.left)
        right = binop_add_leaves(node.right)
        if left is None or right is None:
            return None
        return left + right
    return [node]


def leaves_look_like_filename(leaves: list[ast.expr]) -> bool:
    """`+` 串接鏈的葉節點中，只要任一常數字面值結尾符合已知副檔名樣式，視為
    『組檔名』情境（不要求一定是最後一個葉節點，串接順序不影響判斷）。"""
    return any(
        isinstance(leaf, ast.Constant) and isinstance(leaf.value, str)
        and leaf.value.endswith(_FILENAME_SUFFIXES)
        for leaf in leaves
    )


def mod_format_operands(node: ast.BinOp) -> tuple[str, list[ast.expr]] | None:
    """`"...%s..." % (x, y)` 或 `"...%s..." % x` 這類 `%` 格式化；回傳
    (左側字面樣板, 右側運算元列表)，非此樣式回傳 `None`。"""
    if not isinstance(node.op, ast.Mod):
        return None
    if not (isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)):
        return None
    operands = list(node.right.elts) if isinstance(node.right, ast.Tuple) else [node.right]
    return node.left.value, operands


def format_call_operands(node: ast.Call) -> tuple[str, list[ast.expr]] | None:
    """`"...".format(x, y=z)` 這類呼叫；回傳 (模板字面值, 所有位置+關鍵字引數)，
    非此樣式回傳 `None`。"""
    if not (isinstance(node.func, ast.Attribute) and node.func.attr == "format"):
        return None
    template = node.func.value
    if not (isinstance(template, ast.Constant) and isinstance(template.value, str)):
        return None
    operands = list(node.args) + [kw.value for kw in node.keywords]
    return template.value, operands


def raw_risky_reference(
    expr: ast.expr,
    risky_names: frozenset[str],
    alias_map: dict[str, str] | None = None,
) -> str | None:
    """若表達式是裸引用某風險識別字（未包在 `_sanitize_component(...)` 呼叫
    內），回傳該識別字名稱；否則回傳 `None`。涵蓋 `Name`／`Attribute`／
    `Subscript`（如 `record["rule_id"]`），R46 新增 `BoolOp`／`IfExp` 遞迴拆解
    與（透過 `alias_map`）別名解析（見模組 docstring 方法論⑦）。"""
    if isinstance(expr, ast.Name):
        if expr.id in risky_names:
            return expr.id
        if alias_map and expr.id in alias_map:
            return alias_map[expr.id]
        return None
    if isinstance(expr, ast.Attribute) and expr.attr in risky_names:
        return expr.attr
    if isinstance(expr, ast.Subscript):
        key = expr.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value in risky_names:
            return key.value
        return None
    if isinstance(expr, ast.BoolOp):
        for operand in expr.values:
            found = raw_risky_reference(operand, risky_names, alias_map)
            if found is not None:
                return found
        return None
    if isinstance(expr, ast.IfExp):
        for branch in (expr.body, expr.orelse):
            found = raw_risky_reference(branch, risky_names, alias_map)
            if found is not None:
                return found
        return None
    return None


def find_offenders(files: list[Path]) -> list[str]:
    """對給定的檔案清單掃描全部 offender（裸用風險識別字組檔名、未經
    `_sanitize_component()` 淨化的呼叫點），套用 `_KNOWN_EXEMPTIONS` 排除已核實
    的等效防護。回傳格式化的 offender 描述字串列表（空列表＝乾淨）。"""
    trees = parse_all(files)
    risky_names = risky_identifier_names()
    offenders: list[str] = []

    def _record(path: Path, lineno: object, risky_name: str) -> None:
        if (path.name, risky_name) in _KNOWN_EXEMPTIONS:
            return
        offenders.append(
            f"{path}:{lineno} 裸用識別字 `{risky_name}`"
            "（模組內已知需經 _sanitize_component() 淨化）"
        )

    for path, tree in trees.items():
        # R46 SD 一二審修正：逐作用域（模組頂層 + 每個函式 + 每個類別，含巢狀）獨立掃描，
        # 避免不同函式內同名變數的別名判斷互相碰撞（見 build_alias_map docstring）。
        for scope in _all_scope_nodes(tree):
            alias_map = build_alias_map(scope, risky_names)
            for node in _direct_children_in_scope(scope):
                if isinstance(node, ast.JoinedStr) and joinedstr_looks_like_filename(node):
                    for value in node.values:
                        if not isinstance(value, ast.FormattedValue):
                            continue
                        risky_name = raw_risky_reference(value.value, risky_names, alias_map)
                        if risky_name is not None:
                            _record(path, getattr(value, "lineno", "?"), risky_name)
                elif isinstance(node, ast.BinOp):
                    mod_operands = mod_format_operands(node)
                    if mod_operands is not None:
                        template, operands = mod_operands
                        if template.endswith(_FILENAME_SUFFIXES):
                            for operand in operands:
                                risky_name = raw_risky_reference(operand, risky_names, alias_map)
                                if risky_name is not None:
                                    _record(path, getattr(node, "lineno", "?"), risky_name)
                        continue
                    leaves = binop_add_leaves(node)
                    if leaves is not None and leaves_look_like_filename(leaves):
                        for leaf in leaves:
                            risky_name = raw_risky_reference(leaf, risky_names, alias_map)
                            if risky_name is not None:
                                _record(path, getattr(node, "lineno", "?"), risky_name)
                elif isinstance(node, ast.Call):
                    format_operands = format_call_operands(node)
                    if format_operands is not None:
                        template, operands = format_operands
                        if template.endswith(_FILENAME_SUFFIXES):
                            for operand in operands:
                                risky_name = raw_risky_reference(operand, risky_names, alias_map)
                                if risky_name is not None:
                                    _record(path, getattr(node, "lineno", "?"), risky_name)

    return offenders
