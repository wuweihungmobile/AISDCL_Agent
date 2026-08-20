#!/usr/bin/env python3
"""subprocess `text=True` 無 `encoding` 站點機械守門（R13 ARCH-R13-2；DEF-101-121 家族）。

WHY：`subprocess.run(..., text=True)` 未指定 `encoding` 時採 locale 預設編碼——
Windows 主控台常為 cp950/cp1252，子行程輸出 UTF-8（emoji／中文）即 UnicodeDecodeError
或亂碼假紅；Mac/Linux 全綠、Windows 才炸（DEF-101-121 家族 R11~R13 三輪抓漏均有
漏網樹）。修法慣例＝補 `encoding="utf-8", errors="replace"`。本測試以 AST 機械掃描
六棵樹原始碼，防未來複製舊 pattern 再踩一次（手法鏡射 test_platform_neutral_paths.py）。

AST 判準（非行級 regex；heuristic 邊界如下，均為刻意取捨）：
  - `ast.Call` 且 func 尾名 ∈ {run, Popen, check_output, check_call, call}
    （尾名比對會涵蓋非 subprocess 的同名方法，但違規另須帶 text/universal_newlines
    keyword，實務上為 subprocess 專屬簽名，誤報率極低；真誤報以行尾標記豁免）；
  - keywords 含 `text=True` 或 `universal_newlines=True`（僅 `ast.Constant` 值為
    True 才算；動態值 `text=var` 不追——無法靜態判定，屬 heuristic 邊界）；
  - 含 `**kwargs` 雙星展開的呼叫不追（encoding 可能藏於 dict，同屬動態邊界）；
  - `from subprocess import run as sp_run` 型**別名匯入**的裸呼叫不追（尾名＝
    別名、不在集合內——SD-R13-5a 劃界；六樹以 AST 探針實掃零站點，R13 Python
    掃描亦證 active 面無別名繞道寫法）；
  - `encoding=None` 顯式傳入視同已帶 encoding 而放行（實際仍走 locale 預設——
    SD-R13-5b 劃界；六樹實掃零站點；此寫法本身即明示意圖，不宜機械斷罪）；
  - 且無 `encoding` keyword → 違規。

豁免機制：違規呼叫「起始行」（node.lineno）行尾加註 `# encoding-ok: <WHY>`（WHY
必填）。標記以 tokenize COMMENT token 辨識——字串字面值內的同形文字（如本檔
fixture）不會誤判為標記。stale 自檢：登記了標記但該行掃不到被壓下的違規（呼叫已
補 encoding／已刪除／標記放錯行）→ fail-loud，防豁免清單腐化。

掃描樹（全部遞迴，計十樹）：根 tools/ 與 .claude/hooks/、AutoClaude/ 四樹
（tools／autoclaude 生產碼／tests／scripts）＋alembic/、AISDLC_SDD/scripts/
（含 tests）、LATEST 版 tools/fsm_runtime/ 與 .claude/hooks/（LATEST 以
scripts/sdd_version.py SSOT subprocess 解析——手法對齊
test_platform_neutral_paths；解析失敗 fail-loud，不得靜默縮小掃描邊界。凍結版
v0.01~v0.2X 依鐵律不掃、也不可修）。per-tree 掃描檔數下限釘選防單樹靜默縮面；
無法 parse 的 .py 一律 fail-loud（掃不到＝守門面縮小，不得靜默跳過）。
"""
from __future__ import annotations

import ast
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
import tomllib
import unicodedata
import unittest
from datetime import date
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402

_FUNC_TAILS = frozenset({"run", "Popen", "check_output", "check_call", "call"})
_FLAG_KWARGS = ("text", "universal_newlines")
_OK_MARKER = "encoding-ok:"


def _latest_root() -> Path:
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。委派
    tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    return sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")


# ── per-tree 檔數下限的「腐化偵測帶」（R75／DEF-101-800）────────────────────
# 🔴 缺陷本體：下限原本是**單邊**的，而單邊下限只會腐化——樹會長大、下限不會，
# 於是它實際守住的比例逐年下滑。R75 QA 實測：`tools` 樹 files=81 對 floor=18
# ⇒ 掉掉 63/81（78%）掃描面仍然全綠，而那個 18 的來源是 2026-07-19 首掃數
# 打八折，中間 R74 又是新增檔案最多的一輪。**「掃描面靜默縮小必紅」這個存在
# 理由當時已經不成立**，鎖還在，牙掉了。
#
# 機制（刻意不外接基線同步器）：改成**雙邊帶**。
#   · 低於下限 ⇒ 縮面（原意，不變）；
#   · 高於「下限 ＋ 成長餘裕」⇒ **下限自己過時**，當場紅並在訊息裡直接給出該填的
#     數字。腐化從此不是「等某人有空注意到」，而是一個會自己敲門的機械事件。
# 為何不掛 `tools/sync_onboarding_baselines.py`：那條路要改 ONBOARDING §7 表格與
# 產生器兩處（另有 owner），而它治的是「數字要跟著實測走」；本缺陷治的是「數字
# **可以**不跟著實測走多遠」——後者只需要一個上界，而上界就地可判、零跨檔耦合。
#: 下限＝實測 × 0.95（四捨五入）：容許少量檔案被合併／刪除而不必動下限。
_SHRINK_SLACK = 0.05
#: 實測 > 下限 × 1.25 ⇒ 判定下限腐化。取 25% 是讓「一輪正常增檔」不用重釘、
#: 「累積數輪的漂移」一定會被逼著重釘（R75 那筆是 350%，任何合理閾值都會抓到）。
_REPIN_HEADROOM = 0.25
#: 小樹的絕對餘裕：百分比在 1~5 檔的樹上失效（floor=2 的 25% 是 0 檔）。
_REPIN_MIN_HEADROOM = 10


def repin_ceiling(floor: int) -> int:
    """下限 `floor` 的腐化上界——實測超過它就必須重釘。"""
    return max(floor + _REPIN_MIN_HEADROOM, int(floor * (1 + _REPIN_HEADROOM)))


def suggested_floor(actual: int) -> int:
    """依實測值算出該釘的下限（重釘時直接照抄，不必再想公式）。"""
    return max(1, round(actual * (1 - _SHRINK_SLACK)))


def tree_count_verdict(label: str, actual: int, floor: int) -> str | None:
    """`None`＝在帶內；回字串＝失效理由（純函式，紅綠由合成注入自證）。"""
    if actual < floor:
        return (f"{label} 掃描檔數 {actual} < 下限 {floor}——該樹掃描面疑似縮小"
                "（檔案被刪／被移出樹／glob 被改窄）")
    ceiling = repin_ceiling(floor)
    if actual > ceiling:
        return (f"{label} 掃描檔數 {actual} 已超過下限 {floor} 的腐化上界 {ceiling}"
                f"——這個下限只還守得住 {floor / actual:.0%} 的掃描面，"
                f"請把它重釘為 {suggested_floor(actual)}。"
                "單邊下限必然腐化：R75 實測過 files=81 對 floor=18 的狀態，"
                "當時容許 78% 掃描面靜默蒸發而全綠")
    return None


def _scan_roots() -> list[tuple[Path, int]]:
    """（掃描根, 該樹檔數下限）清單；根缺席或**離開下限帶**由測試 fail-loud。

    per-tree 下限（對齊 test_platform_neutral_paths SD-3 慣例）：逐樹釘選使任一樹
    縮面必紅、不被他樹總量掩蓋。R13 一審 ARCH-R13-REV-5 補納四個小樹
    （.claude/hooks／AutoClaude/scripts／AutoClaude/alembic／LATEST .claude/hooks
    ——其中 AutoClaude/scripts 正是 DEF-101-178 實證的 R12 清查漏網目錄）。
    樹清單本體由 TestScanRootsConfigPinning 釘選，防「刪清單一列」整樹靜默出界
    （QA-R13-2 同構）。

    🔴 下限值＝**R75 當回合實測 × 0.95**（見 `suggested_floor()`），不再是
    2026-07-19 首掃數打八折的化石。實測值（2026-08-04，本機）：
    81／43／204／282／1／19／2／43／166／2／5。上界機制見 `tree_count_verdict()`
    ——下限與實測拉開太遠時它自己會紅，所以這一串數字不會再默默腐化。"""
    latest = _latest_root()
    return [
        # 🔴 R80 收尾單人窗口重釘 77 → 92（**方向是收緊**：下限拉高＝要求更大的掃描面）。
        # 觸發＝本輪三支護欄層檔的判準本體下沉 `tools/lib/`（DEF-101-957／958），`tools` 樹
        # 由 95 支長到 97 支，而 77 這個下限只還守得住 79% 的掃描面 ⇒ `tree_count_verdict()`
        # 的腐化上界當場紅並直接給出該填的數字（92 ＝ 97 × 0.95），本列照填、不做加減推算。
        # 🔴 R83 收輪單人窗口重釘 92 → 110（**方向是收緊**，同上一段語意）。觸發＝本輪
        # 並行包在 `tools` 樹下新增四支檔（`tools/lib/schedule_backend.py` ＋ 三支回歸鎖
        # `tools/tests/test_block_destructive_git_r83.py`／`test_mac_endurance_r83.py`／
        # `test_skip_discoverability_r83.py`），該樹由 112 支長到 116 支，92 這個下限只
        # 還守得住 79% 的掃描面 ⇒ `tree_count_verdict()` 的腐化上界（115）當場紅並直接
        # 給出該填的數字（110 ＝ 116 × 0.95），本列照填、不做加減推算。
        # 🔴 R97 追加當輪重釘 110 → 131（**方向是收緊**，同上一段語意）。觸發＝本輪
        # 新增 `tools/lib/worktree_paths.py`／`tools/lib/ledger_staleness.py`／
        # `tools/lib/failure_log_rotation.py` 三支模組，該樹由 130 支長到 138 支，
        # 110 這個下限只還守得住 80% 的掃描面 ⇒ `tree_count_verdict()` 的腐化上界
        # （137）當場紅並直接給出該填的數字（131 ＝ 138 × 0.95），本列照填、不做加減推算。
        (_REPO_ROOT / "tools", 131),
        (_REPO_ROOT / "AutoClaude" / "tools", 41),
        (_REPO_ROOT / "AutoClaude" / "autoclaude", 194),
        (_REPO_ROOT / "AutoClaude" / "tests", 268),
        (_REPO_ROOT / "AutoClaude" / "scripts", 1),
        (_REPO_ROOT / "AutoClaude" / "alembic", 18),
        (_REPO_ROOT / ".claude" / "hooks", 2),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts", 41),
        (latest / "tools" / "fsm_runtime", 158),
        # R14 SCAN-PY-1：LATEST tools/ 下 fsm_runtime 之外唯一 Python 樹——現況零
        # subprocess 站點（arch_fitness.py 明文「不執行 shell」），納管防未來引入
        # 漏網（升版由 _latest_root() 動態跟隨）。實掃 2 檔（__init__ + 本體）。
        (latest / "tools" / "arch_fitness", 2),
        (latest / ".claude" / "hooks", 5),
    ]


# R14 SCAN-PY-2：樹清單外的零散活躍 .py 以顯式單檔清單納管（目錄機制掃不到、
# 又不能把整個 AISDLC_SDD/ 根樹納入——rglob 會誤掃凍結版 v0.01~v0.29）。
# 清單由 TestScanRootsConfigPinning 一併釘選。R14 一審（SD-R14-REV-3＋ARCH-R14-REV-4
# 獨立交叉發現）以 `git ls-files '*.py'` 全列舉打破「唯一漏網」宣稱，補齊為 3 檔；
# R75 裁決並執行：`AutoClaude/tmp_lint_check.py`（2026-06-12 入庫的 tracked 暫存殘留，
# 內容＝重跑 `lint-imports` CLI 已有的行為）依「暫存檔直接刪」慣例 `git rm`，故從本清單
# 顯式除名。設計如預期運作——刪檔當回合本模組 1 failure + 2 errors，訊息逐字要求
# 「邊界不得靜默縮小」，於是縮面必須是**寫下來的動作**而不是靜默發生。
def _scan_single_files() -> list[Path]:
    return [
        _REPO_ROOT / "AISDLC_SDD" / "conftest.py",
        _latest_root() / "tools" / "__init__.py",
    ]


def _call_tail_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _marker_lines(source: str, marker: str = _OK_MARKER) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token 內的標記（字串字面值同形文字不誤判）。

    比對刻意帶「前面不得是字母/數字/連字號」的邊界：判準二的標記
    `child-encoding-ok:` 內含判準一的 `encoding-ok:`，裸子字串比對會讓一個標記
    同時被兩個判準認領，於是判準一那邊當場多出一筆 stale（該行對它沒有違規）。
    """
    pattern = re.compile(r"(?<![\w-])" + re.escape(marker))
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type != tokenize.COMMENT:
            continue
        found = pattern.search(tok.string)
        if found:
            markers[tok.start[0]] = tok.string[found.end():].strip()
    return markers


def scan_source(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。

    stale＝標記存在但該行沒有被壓下的違規（含 WHY 留空）→ 必須清掉或補 WHY。
    """
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _marker_lines(source)
    used: set[int] = set()
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_tail_name(node.func) not in _FUNC_TAILS:
            continue
        kwargs = {k.arg: k.value for k in node.keywords if k.arg is not None}
        if any(k.arg is None for k in node.keywords):  # **kwargs 動態展開不追
            continue
        flag = next(
            (
                name
                for name in _FLAG_KWARGS
                if isinstance(kwargs.get(name), ast.Constant)
                and kwargs[name].value is True
            ),
            None,
        )
        if flag is None or "encoding" in kwargs:
            continue
        if node.lineno in markers and markers[node.lineno]:
            used.add(node.lineno)
            continue
        offenders.append(
            f"{rel}:{node.lineno}: {flag}=True 無 encoding"
            f"（請補 encoding=\"utf-8\", errors=\"replace\"）"
        )
    stale = [
        f"{rel}:{lineno}: encoding-ok 標記 stale（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used
    ]
    return offenders, stale


def scan_files(files: list[Path], repo_root: Path) -> tuple[list[str], list[str], list[str]]:
    """回傳 (offenders, stale_markers, parse_failures)——parse 失敗一律列報不靜默跳過。"""
    offenders: list[str] = []
    stale: list[str] = []
    parse_failures: list[str] = []
    for py in files:
        rel = py.relative_to(repo_root).as_posix()
        try:
            off, st = scan_source(py.read_text(encoding="utf-8"), rel)
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            parse_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
            continue
        offenders.extend(off)
        stale.extend(st)
    return offenders, stale, parse_failures


# ══════════════════════════════════════════════════════════════════════════
# 判準二：**child 編碼**方向（R74／DEF-101-789）
# ══════════════════════════════════════════════════════════════════════════
# 本檔原有的判準只守「parent 解碼」一半：`text=True` 要不要帶 `encoding`。
# 出事那一行 `subprocess.run(cmd, …, text=True, encoding="utf-8",
# errors="replace")` 對它**百分之百合規**，卻仍在 GitHub windows-latest 上紅——
# 因為 parent 宣告以 UTF-8 解碼時，沒有任何東西保證 **child 以 UTF-8 編碼**：
# child 是一支 Python 腳本，它的 stdout/stderr 編碼由 locale 決定，`sys.stderr`
# 的預設 `errors` 還是 `backslashreplace`，於是
#   · locale 表達不了 CJK（en-US ＝ cp1252）→ 輸出變 `\uXXXX` 逃脫字面；
#   · locale 表達得了但非 UTF-8（zh-TW ＝ cp950）→ parent 讀到亂碼。
# 兩者都不是「亂碼而已」：對 stdout 而言預設 `errors` 是 **strict**，同一條件下
# 是直接 UnicodeEncodeError 崩潰。**同一份知識在樹裡活了很久、只守了一個方向。**
#
# 判準（刻意與判準一同一種豁免體例，只是標記字樣不同）：
#   - 呼叫的 argv 第一個元素是 `sys.executable`（＝以當前直譯器起 Python child）；
#     argv 允許**一跳變數解析**（`cmd = [sys.executable, …]` 之後才 `run(cmd, …)`）
#     ——只認字面 argv 的版本會漏掉出事那一筆，這條不是可選的；
#   - argv 中第一個非旗標元素能被**靜態解析**成 repo 內實存的 `.py`；
#   - 該 `.py` 必須帶 UTF-8 stdio 保護，三種形態皆算（缺任一種都會誤判：
#     `import _stdio_utf8`（根 tools/ 慣例）／`init_utf8_streams`
#     （`AutoClaude/tools/hooks/*` 走 `from platform_utils import …` 的形態）／
#     就地 `.reconfigure(encoding=`（AutoClaude/tools/ 與 .claude/hooks/ 慣例）／
#     `force_utf8_stdio(`（`AISDLC_SDD/scripts/` 島的委派入口，住
#     `rfc_lifecycle_lint.py`——該島因跨子專案 import 隔離搆不到根層
#     `tools/_stdio_utf8.py`，故島內自留唯一一份實作））。
#
# 🔴 R84：第四種形態是**委派**而非新實作，與第二種（`init_utf8_streams`）同型——
# 不加它，`test_platform_utils_dedup` 的 per-tree shrink-only 棘輪（島內行內複本
# 只准變少）與本判準會互相抵觸：要收斂就必然要有人改成呼叫委派，而委派名不被認得
# 就當場被本判準判成「無保護」。兩鎖同時成立的唯一形狀就是讓本表認得委派名。
# 這不是放寬——被認的仍必須是**真的會 reconfigure** 的呼叫（未 import 即 NameError，
# 失敗是響的），與第二種形態的強度逐字相同。
#
# 刻意的 heuristic 邊界（都是「不追」而非「放行」，且以下限釘選防靜默縮面）：
#   - `-m pytest` / `-c <code>` 這類旗標形態不追：child 不是 repo 內某支 .py；
#   - 路徑靜態解析不出來（函式參數、tempfile 產生的探針）不追；
#   - 不看 parent 有沒有 `text=True`：child 對 stdout 的預設 errors 是 strict，
#     parent 收 bytes 也一樣會撞上 child 端崩潰，所以要求與 parent 模式無關。
_PROTECTION_MARKS = (
    "import _stdio_utf8", "init_utf8_streams", ".reconfigure(encoding=",
    "force_utf8_stdio(",
)
_CHILD_OK_MARKER = "child-encoding-ok:"

#: 靜態路徑解析的跳數上限（`str(_HOOK)` → `_HOOK` → `_REPO_ROOT / …` →
#: `Path(__file__).resolve().parents[2]` 實測需 8 跳；留一倍餘裕）。
_RESOLVE_DEPTH = 16


def _assign_map(scope: ast.AST) -> dict[str, list[ast.expr]]:
    """`scope` 內（不跨函式／類別邊界）的 `name = expr` 表，一名可多式。"""
    out: dict[str, list[ast.expr]] = {}

    def rec(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef, ast.Lambda)):
                continue  # 內層自己的 scope，由 _calls_with_scopes 另建
            if isinstance(child, ast.Assign):
                for tgt in child.targets:
                    if isinstance(tgt, ast.Name):
                        out.setdefault(tgt.id, []).append(child.value)
            elif (isinstance(child, ast.AnnAssign)
                  and isinstance(child.target, ast.Name) and child.value):
                out.setdefault(child.target.id, []).append(child.value)
            rec(child)

    rec(scope)
    return out


def _calls_with_scopes(tree: ast.AST) -> list[tuple[ast.Call, list[dict]]]:
    """每個 `ast.Call` 配上「由內而外」的 assigns 鏈（詞法作用域近似）。"""
    found: list[tuple[ast.Call, list[dict]]] = []

    def visit(node: ast.AST, chain: list[dict]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef, ast.Lambda)):
                visit(child, [_assign_map(child), *chain])
                continue
            if isinstance(child, ast.Call):
                found.append((child, chain))
            visit(child, chain)

    visit(tree, [_assign_map(tree)])
    return found


def _lookup(name: str, scopes: list[dict]) -> list[ast.expr]:
    for scope in scopes:
        if name in scope:
            return scope[name]  # 最內層命中即停（外層同名不再混入）
    return []


def _static_path(
    expr: ast.expr, scopes: list[dict], self_path: Path, depth: int = 0
) -> Path | None:
    """把運算式靜態解析成絕對路徑；解析不出來回 `None`（＝不追，非放行）。

    支援的形態刻意只有 repo 內實際用到的那幾種：`Path(__file__)`／`.resolve()`／
    `.parent`／`.parents[N]`／`/ "字面"`／`str(...)`／單純的名字綁定。
    """
    if depth > _RESOLVE_DEPTH:
        return None
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        cand = Path(expr.value)
        return cand if cand.is_absolute() else None
    if isinstance(expr, ast.Name):
        for value in _lookup(expr.id, scopes):
            got = _static_path(value, scopes, self_path, depth + 1)
            if got is not None:
                return got
        return None
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
        base = _static_path(expr.left, scopes, self_path, depth + 1)
        right = expr.right
        if base is None or not (isinstance(right, ast.Constant)
                                and isinstance(right.value, str)):
            return None
        return base / right.value
    if isinstance(expr, ast.Call):
        tail = _call_tail_name(expr.func)
        if tail in ("resolve", "absolute") and isinstance(expr.func, ast.Attribute):
            return _static_path(expr.func.value, scopes, self_path, depth + 1)
        if tail == "Path" and expr.args:
            first = expr.args[0]
            if isinstance(first, ast.Name) and first.id == "__file__":
                return self_path
            return _static_path(first, scopes, self_path, depth + 1)
        if tail in ("str", "fspath") and expr.args:
            return _static_path(expr.args[0], scopes, self_path, depth + 1)
        return None
    if isinstance(expr, ast.Attribute) and expr.attr == "parent":
        base = _static_path(expr.value, scopes, self_path, depth + 1)
        return base.parent if base is not None else None
    if isinstance(expr, ast.Subscript):
        inner = expr.value
        if (isinstance(inner, ast.Attribute) and inner.attr == "parents"
                and isinstance(expr.slice, ast.Constant)
                and isinstance(expr.slice.value, int)):
            base = _static_path(inner.value, scopes, self_path, depth + 1)
            if base is None:
                return None
            try:
                return base.parents[expr.slice.value]
            except IndexError:
                return None
    return None


def _argv_variants(call: ast.Call, scopes: list[dict]) -> list[list[ast.expr]]:
    """呼叫的 argv 候選清單；`run(cmd, …)` 走一跳變數解析（同名多式全取）。"""
    if not call.args:
        return []
    first = call.args[0]
    if isinstance(first, ast.List):
        return [list(first.elts)]
    if isinstance(first, ast.Name):
        return [list(v.elts) for v in _lookup(first.id, scopes)
                if isinstance(v, ast.List)]
    return []


def _is_sys_executable(expr: ast.expr) -> bool:
    return (isinstance(expr, ast.Attribute) and expr.attr == "executable"
            and isinstance(expr.value, ast.Name) and expr.value.id == "sys")


#: tokenize 分類上「不是程式碼」的 token：註解與字串字面（含 3.12+ 的 f-string 分段）。
#: 以 `getattr` 取值是為了跨 Python 版本——3.11 沒有 FSTRING_* 這組 token。
_NON_CODE_TOKENS = frozenset(
    {tokenize.COMMENT, tokenize.STRING}
    | {tt for tt in (getattr(tokenize, name, None) for name in
                     ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"))
       if tt is not None}
)


def code_only(source: str) -> str:
    """把註解與字串字面**塗白成等寬空白**後的原始碼（行號與欄位皆不位移）。

    🔴 為何非要塗白（R75／DEF-101-801）：本判準原本是**整檔子字串比對**，於是
    一行註解 `# init_utf8_streams` 就能讓一支毫無保護的檔案被判為「有保護」。
    QA 以同樣手法複算過本輪納管的 child，14/14 命中皆落在真實程式碼 ⇒ 現況沒有
    實例在濫用，屬**潛在缺口**。但這個缺口的形狀是「假綠」，而假綠一旦發生就
    沒有任何訊號——本檔另一道判準（`_marker_lines`）早就只認 COMMENT token、
    刻意不用裸子字串，同一份謹慎沒有套到這裡來。

    tokenize 失敗（壞檔／怪編碼）時回空字串＝**視為無保護**：方向刻意選紅不選綠，
    判準的存在理由就是防假綠。掃描面內的檔另有 `ast.parse` 的 fail-loud 會先叫。
    """
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return ""
    grid = [list(line) for line in source.splitlines(keepends=True)]
    for tok in toks:
        if tok.type not in _NON_CODE_TOKENS:
            continue
        (row1, col1), (row2, col2) = tok.start, tok.end
        for row in range(row1, min(row2, len(grid)) + 1):
            line = grid[row - 1]
            lo = col1 if row == row1 else 0
            hi = col2 if row == row2 else len(line)
            for col in range(lo, min(hi, len(line))):
                if line[col] != "\n":
                    line[col] = " "
    return "".join("".join(line) for line in grid)


def has_utf8_stdio_protection(source: str) -> bool:
    """三種保護形態任一即算——只認前兩種會誤判 `.reconfigure` 派的檔案。

    比對面是 `code_only(source)`：註解、docstring、**被註解掉的程式碼**都不算保護
    （見 `code_only` 的 WHY）。
    """
    code = code_only(source)
    return any(mark in code for mark in _PROTECTION_MARKS)


def scan_child_encoding(
    source: str, rel: str, self_path: Path, repo_root: Path
) -> tuple[list[str], list[str], int]:
    """回 (offenders, stale_markers, 納管站點數)。納管數供下限釘選用。"""
    tree = ast.parse(source)
    markers = _marker_lines(source, _CHILD_OK_MARKER)
    used: set[int] = set()
    offenders: list[str] = []
    in_scope = 0
    for call, scopes in _calls_with_scopes(tree):
        if _call_tail_name(call.func) not in _FUNC_TAILS:
            continue
        variants = [elts for elts in _argv_variants(call, scopes)
                    if elts and _is_sys_executable(elts[0])]
        if not variants:
            continue
        targets: list[Path] = []
        for elts in variants:
            for element in elts[1:]:
                if (isinstance(element, ast.Constant)
                        and isinstance(element.value, str)
                        and element.value.startswith("-")):
                    break  # 旗標形態（-m／-c）：child 不是 repo 內某支 .py
                got = _static_path(element, scopes, self_path)
                if got is not None and got.suffix == ".py" and got.is_file():
                    targets.append(got)
                break  # 只看第一個非旗標位置＝腳本位
        seen: set[Path] = set()
        for target in targets:
            if target in seen:
                continue
            seen.add(target)
            in_scope += 1
            if has_utf8_stdio_protection(target.read_text(encoding="utf-8")):
                continue
            if call.lineno in markers and markers[call.lineno]:
                used.add(call.lineno)
                continue
            try:
                shown = target.relative_to(repo_root).as_posix()
            except ValueError:  # repo 外的路徑：原樣印出，仍列報
                shown = str(target)
            offenders.append(
                f"{rel}:{call.lineno}: 起 Python child `{shown}`，"
                f"但該檔無 UTF-8 stdio 保護（child 端編碼由 locale 決定："
                f"非 CJK locale 逃脫成 \\uXXXX、非 UTF-8 locale 給亂碼、"
                f"stdout 更是 errors='strict' 直接崩潰）"
            )
    stale = [
        f"{rel}:{lineno}: {_CHILD_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used
    ]
    return offenders, stale, in_scope


def scan_files_child_encoding(
    files: list[Path], repo_root: Path
) -> tuple[list[str], list[str], list[str], int]:
    offenders: list[str] = []
    stale: list[str] = []
    parse_failures: list[str] = []
    in_scope = 0
    for py in files:
        rel = py.relative_to(repo_root).as_posix()
        try:
            off, st, cnt = scan_child_encoding(
                py.read_text(encoding="utf-8"), rel, py, repo_root
            )
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            parse_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
            continue
        offenders.extend(off)
        stale.extend(st)
        in_scope += cnt
    return offenders, stale, parse_failures, in_scope


#: 納管站點數下限。為何非有不可：本判準的射程取決於「靜態路徑解析得出來幾筆」，
#: 而那是實作細節——有人把解析器改弱一點，offenders 一樣是 0，鎖卻靜默變成擺設。
#: 同 per-tree 檔數下限的語意，只是這裡守的是「解析力」而非「檔數」。
#:
#: 🔴 R75：值改為當回合實測 × 0.95（`suggested_floor`），並**套同一條腐化上界**
#: （`tree_count_verdict`）——原值 20 是 26 筆打八折＝per-tree 下限腐化成 18 vs 81 的同一個
#: 算法。上界讓它不必靠人記得（R89：35→45＝實測 47×0.95；**收緊不是放寬**）。
_CHILD_SITE_FLOOR = 45


class TestSubprocessEncodingHygiene(unittest.TestCase):
    def test_repo_trees_have_no_unencoded_text_subprocess(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        for root, floor in _scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = sorted(root.rglob("*.py"))
            # per-tree 下限帶：單樹縮面必紅；下限離實測太遠（＝腐化）也必紅
            verdict = tree_count_verdict(str(root), len(files), floor)
            self.assertIsNone(verdict, verdict or "")
            off, st, pf = scan_files(files, _REPO_ROOT)
            offenders.extend(off)
            stale.extend(st)
            parse_failures.extend(pf)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小，請修檔或排除於樹外：\n"
            + "\n".join(parse_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現 subprocess text=True 無 encoding 站點（Windows locale 碼頁下"
            "讀 UTF-8 子行程輸出會 UnicodeDecodeError/亂碼）——請補 "
            'encoding="utf-8", errors="replace"；確屬刻意用預設編碼時，'
            "於呼叫起始行行尾加 `# encoding-ok: <WHY>` 豁免：\n" + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            "encoding-ok 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )

    def test_single_file_sites_have_no_unencoded_text_subprocess(self) -> None:
        """R14 SCAN-PY-2：樹清單外零散活躍 .py 的單檔納管（同判準同豁免機制）。"""
        files = _scan_single_files()
        for f in files:
            self.assertTrue(f.is_file(), f"單檔掃描目標缺席：{f}（邊界不得靜默縮小）")
        off, st, pf = scan_files(sorted(files), _REPO_ROOT)
        self.assertEqual(pf, [], "單檔掃描 parse 失敗：\n" + "\n".join(pf))
        self.assertEqual(off, [], "單檔掃描發現無 encoding 站點：\n" + "\n".join(off))
        self.assertEqual(st, [], "單檔掃描豁免標記 stale：\n" + "\n".join(st))

    # ── 以下以注入 fixture 自證判準紅綠（fixture 僅存在於 tmp，不留違規樣本於 repo）──

    def _scan_fixture(self, source: str) -> tuple[list[str], list[str], list[str]]:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "fixture_case.py").write_text(source, encoding="utf-8")
            return scan_files(sorted(root.rglob("*.py")), root)

    def test_injected_violation_is_detected(self) -> None:
        """假違規 fixture 必紅（text=True 與 universal_newlines=True 兩形態）。"""
        off, stale, pf = self._scan_fixture(
            "import subprocess\n"
            "subprocess.run(['x'], capture_output=True, text=True)\n"
            "subprocess.check_output(['x'], universal_newlines=True)\n"
        )
        self.assertEqual(pf, [])
        self.assertEqual(len(off), 2, off)
        self.assertIn("fixture_case.py:2: text=True 無 encoding", off[0])
        self.assertIn("fixture_case.py:3: universal_newlines=True 無 encoding", off[1])
        self.assertEqual(stale, [])

    def test_compliant_and_dynamic_sites_are_green(self) -> None:
        """已補 encoding／動態值 text=var／**kwargs 展開＝不判違規（heuristic 邊界）。"""
        off, stale, pf = self._scan_fixture(
            "import subprocess\n"
            "subprocess.run(['x'], text=True, encoding='utf-8', errors='replace')\n"
            "flag = True\n"
            "subprocess.run(['x'], text=flag)\n"
            "kw = {'encoding': 'utf-8'}\n"
            "subprocess.run(['x'], text=True, **kw)\n"
        )
        self.assertEqual((off, stale, pf), ([], [], []))

    def test_encoding_ok_marker_suppresses_violation(self) -> None:
        """行尾豁免標記（附 WHY）＝綠，且不判 stale。"""
        off, stale, pf = self._scan_fixture(
            "import subprocess\n"
            "subprocess.run(  # encoding-ok: 子行程輸出為系統碼頁（刻意用預設）\n"
            "    ['x'], text=True)\n"
        )
        self.assertEqual((off, stale, pf), ([], [], []))

    def test_stale_or_empty_why_marker_fails(self) -> None:
        """標記 stale（該行無被壓下的違規）或 WHY 留空 → fail-loud 防腐化。"""
        off, stale, pf = self._scan_fixture(
            "import subprocess\n"
            "subprocess.run(  # encoding-ok: 已補 encoding 後忘了拆標記\n"
            "    ['x'], text=True, encoding='utf-8')\n"
            "subprocess.run(  # encoding-ok:\n"
            "    ['x'], text=True)\n"
        )
        self.assertEqual(pf, [])
        # WHY 留空的標記不具豁免力：該違規仍列報
        self.assertEqual(len(off), 1, off)
        self.assertIn("fixture_case.py:4", off[0])
        self.assertEqual(len(stale), 2, stale)
        self.assertIn("fixture_case.py:2", stale[0])
        self.assertIn("該行無被壓下的違規", stale[0])
        self.assertIn("fixture_case.py:4", stale[1])
        self.assertIn("WHY 留空", stale[1])

    def test_parse_failure_is_fail_loud(self) -> None:
        """無法 parse 的檔案列入 parse_failures（不得靜默縮面）。"""
        off, stale, pf = self._scan_fixture("def broken(:\n")
        self.assertEqual((off, stale), ([], []))
        self.assertEqual(len(pf), 1, pf)
        self.assertIn("SyntaxError", pf[0])


class TestChildEncodingHygiene(unittest.TestCase):
    """判準二：起 Python child 的呼叫，child 自己必須有 UTF-8 stdio 保護。

    WHY 這道到 R74 才出現：判準一（parent 解碼）2026-07-19 就上線了，而出事那一行
    對它完全合規——`text=True` 有 `encoding="utf-8"`、有 `errors="replace"`。
    repo 只守了一半，另一半連判準都沒有，於是 `.claude/hooks/block_bash_on_windows.py`
    在無保護狀態下漂了一整輪，直到 GitHub windows-latest（en-US ＝ cp1252）把
    整段中文指引印成 `\\uXXXX` 才被看見（DEF-101-789）。
    """

    def test_python_child_targets_have_utf8_stdio_protection(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        in_scope = 0
        for root, _floor in _scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            off, st, pf, cnt = scan_files_child_encoding(
                sorted(root.rglob("*.py")), _REPO_ROOT
            )
            offenders.extend(off)
            stale.extend(st)
            parse_failures.extend(pf)
            in_scope += cnt
        off_s, st_s, pf_s, cnt_s = scan_files_child_encoding(
            sorted(_scan_single_files()), _REPO_ROOT
        )
        offenders.extend(off_s)
        stale.extend(st_s)
        parse_failures.extend(pf_s)
        in_scope += cnt_s
        self.assertEqual(parse_failures, [],
                         "以下 .py 無法 parse：\n" + "\n".join(parse_failures))
        self.assertEqual(
            offenders, [],
            "發現「起 Python child、但 child 無 UTF-8 stdio 保護」的站點——"
            "請在 child 那支檔加上保護（`import _stdio_utf8` / "
            "`init_utf8_streams` / 就地 `.reconfigure(encoding=`）；"
            "確屬刻意（child 只印 ASCII）時於呼叫起始行行尾加 "
            f"`# {_CHILD_OK_MARKER} <WHY>` 豁免：\n" + "\n".join(offenders),
        )
        self.assertEqual(stale, [],
                         f"{_CHILD_OK_MARKER} 豁免標記 stale：\n" + "\n".join(stale))
        verdict = tree_count_verdict("child 編碼判準納管站點數", in_scope,
                                     _CHILD_SITE_FLOOR)
        self.assertIsNone(
            verdict,
            f"{verdict}\n（低於下限＝靜態路徑解析力變弱，offenders 一樣會是 0、"
            "鎖卻靜默變擺設；高於上界＝下限已腐化，照訊息重釘 _CHILD_SITE_FLOOR）",
        )

    # ── 判準紅綠自證（fixture 全落在 tmp，repo 內不留違規樣本）──────────────

    def _fixture(self, caller: str, child: str) -> tuple[list[str], list[str], int]:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "child_case.py").write_text(child, encoding="utf-8")
            (root / "caller_case.py").write_text(caller, encoding="utf-8")
            off, stale, pf, cnt = scan_files_child_encoding(
                [root / "caller_case.py"], root
            )
            self.assertEqual(pf, [])
            return off, stale, cnt

    _UNPROTECTED = "print('中文')\n"
    _CALL_LITERAL = (
        "import subprocess, sys\n"
        "from pathlib import Path\n"
        "_ROOT = Path(__file__).resolve().parent\n"
        "subprocess.run([sys.executable, str(_ROOT / 'child_case.py')],\n"
        "               text=True, encoding='utf-8')\n"
    )
    #: 出事那一筆的形態：argv 先進變數，`run()` 只看到一個名字。
    _CALL_ONE_HOP = (
        "import subprocess, sys\n"
        "from pathlib import Path\n"
        "_ROOT = Path(__file__).resolve().parent\n"
        "_CHILD = _ROOT / 'child_case.py'\n"
        "def go(flag):\n"
        "    if flag:\n"
        "        cmd = [sys.executable, str(_CHILD)]\n"
        "    else:\n"
        "        cmd = [sys.executable, '-c', 'pass']\n"
        "    return subprocess.run(cmd, text=True, encoding='utf-8')\n"
    )

    def test_unprotected_child_is_detected_via_literal_argv(self) -> None:
        off, stale, cnt = self._fixture(self._CALL_LITERAL, self._UNPROTECTED)
        self.assertEqual(len(off), 1, off)
        self.assertIn("caller_case.py:4", off[0])
        self.assertEqual((stale, cnt), ([], 1))

    def test_unprotected_child_is_detected_through_one_hop_variable(self) -> None:
        """**這條不是可選的**：只認字面 argv 的版本會漏掉 R74 出事那一筆。"""
        off, stale, cnt = self._fixture(self._CALL_ONE_HOP, self._UNPROTECTED)
        self.assertEqual(len(off), 1, off)
        self.assertIn("caller_case.py:10", off[0])
        self.assertEqual((stale, cnt), ([], 1))

    def test_each_protection_form_is_recognised(self) -> None:
        """三種保護形態都要認：只認前兩種會誤判 `.reconfigure` 派的檔案
        （`AutoClaude/tools/hooks/check_lang.py` 走
        `from platform_utils import init_utf8_streams`，只認 `import _stdio_utf8`
        則會把它誤判成無保護）。"""
        for guard in (
            "import _stdio_utf8  # noqa: F401 \nprint('中文')\n",
            "from platform_utils import init_utf8_streams\nprint('中文')\n",
            "import sys\nsys.stdout.reconfigure(encoding='utf-8')\nprint('中文')\n",
        ):
            with self.subTest(guard=guard.splitlines()[0]):
                off, stale, cnt = self._fixture(self._CALL_ONE_HOP, guard)
                self.assertEqual((off, stale, cnt), ([], [], 1))

    #: 保護字樣只出現在「不是程式碼」的位置的四種形態（R75／DEF-101-801）。
    #: 刻意不含 `sys.std{out,err}.reconfigure(` 字面：`test_platform_utils_dedup.py` 的
    #: `_FROZEN_INLINE_STDIO_SITES` 把本檔的該形態命中數凍結在 1，多寫一處即紅。
    #: （R75 訂正：本行原本逐字寫出了那個字面，於是自己就是那「多寫的一處」、把上述棘輪
    #:  弄紅——與 R73「訂正註記逐字引述＝製造新事實」同型，改用第 820 行同樣的非字面寫法。）
    _FAKE_PROTECTION = (
        ("行註解", "# init_utf8_streams\nprint('中文')\n"),
        ("docstring", '"""本檔應該 import _stdio_utf8（TODO）。"""\nprint(\'中文\')\n'),
        ("被註解掉的程式碼",
         "# from platform_utils import init_utf8_streams\n"
         "# init_utf8_streams()\nprint('中文')\n"),
        ("字串常數", "_TODO = 'import _stdio_utf8'\nprint('中文')\n"),
    )

    def test_protection_marks_outside_real_code_do_not_count(self) -> None:
        """保護字樣落在註解／docstring／被註解掉的程式碼／字串常數 ⇒ **無保護**。

        WHY 這條是必要的（DEF-101-801）：判準原本是整檔子字串比對，上面任一種形態
        都能讓一支毫無保護的 child 被判成合規——而「合規」在本判準裡就是綠燈，
        沒有第二個訊號。本檔另一道判準（`_marker_lines`）早就只認 COMMENT token，
        同一份謹慎沒有套過來。
        """
        for label, child in self._FAKE_PROTECTION:
            with self.subTest(form=label):
                self.assertFalse(
                    has_utf8_stdio_protection(child),
                    f"{label} 內的保護字樣被當成真的保護了（整檔子字串比對的病）",
                )
                off, stale, cnt = self._fixture(self._CALL_ONE_HOP, child)
                self.assertEqual(len(off), 1, f"{label}：應判違規，實得 {off}")
                self.assertEqual((stale, cnt), ([], 1))

    def test_code_only_blanks_non_code_without_shifting_line_numbers(self) -> None:
        """塗白必須**等寬**：行號／欄位一位移，`_marker_lines` 與 offender 行號就對不上。"""
        source = "x = 1  # init_utf8_streams\ny = '''import _stdio_utf8\n多行'''\nz = 2\n"
        blanked = code_only(source)
        self.assertEqual(len(blanked.splitlines()), len(source.splitlines()))
        for before, after in zip(source.splitlines(), blanked.splitlines()):
            self.assertEqual(len(before), len(after))
        self.assertNotIn("init_utf8_streams", blanked)
        self.assertNotIn("_stdio_utf8", blanked)
        self.assertIn("x = 1", blanked)
        self.assertIn("z = 2", blanked)

    def test_real_code_protection_survives_the_blanking(self) -> None:
        """反向：真實程式碼的三種保護形態塗白後仍在（判準不得因塗白變成恆假）。

        第三種形態以 `_PROTECTION_MARKS` 拼出而不寫字面：
        `test_platform_utils_dedup.py::_FROZEN_INLINE_STDIO_SITES` 把本檔的
        `std{out,err}.reconfigure(` 命中數凍結在 1（既有 fixture 那處），
        多寫一處字面就會讓那道棘輪翻紅。
        """
        for guard in (
            "import _stdio_utf8  # noqa: F401 \n",
            "from platform_utils import init_utf8_streams\ninit_utf8_streams()\n",
            "import sys\nsys.stdout" + _PROTECTION_MARKS[2] + "'utf-8')\n",
        ):
            with self.subTest(guard=guard.splitlines()[0]):
                self.assertTrue(has_utf8_stdio_protection(guard))

    def test_unparseable_child_is_treated_as_unprotected(self) -> None:
        """tokenize 不了的 child ⇒ 判無保護（方向選紅不選綠）。"""
        self.assertFalse(has_utf8_stdio_protection("def broken(:\n"))
        self.assertEqual(code_only("def broken(:\n"), "")

    def test_flag_forms_and_unresolvable_paths_are_out_of_scope(self) -> None:
        """`-m` / `-c` 與解析不出來的路徑：不納管（劃界，非放行）。"""
        caller = (
            "import subprocess, sys\n"
            "def go(script):\n"
            "    subprocess.run([sys.executable, '-m', 'pytest'], text=True,\n"
            "                   encoding='utf-8')\n"
            "    subprocess.run([sys.executable, str(script)], text=True,\n"
            "                   encoding='utf-8')\n"
        )
        off, stale, cnt = self._fixture(caller, self._UNPROTECTED)
        self.assertEqual((off, stale, cnt), ([], [], 0))

    def test_child_encoding_ok_marker_suppresses_and_stale_fails(self) -> None:
        marked = self._CALL_LITERAL.replace(
            "subprocess.run([sys.executable",
            f"subprocess.run(  # {_CHILD_OK_MARKER} child 只印 ASCII\n"
            "               [sys.executable",
        )
        off, stale, cnt = self._fixture(marked, self._UNPROTECTED)
        self.assertEqual((off, stale, cnt), ([], [], 1))
        # 同一個標記掛在已有保護的 child 上 ⇒ stale（防豁免清單腐化）
        off2, stale2, _ = self._fixture(
            marked, "import _stdio_utf8  # noqa: F401 \nprint('中文')\n"
        )
        self.assertEqual(off2, [])
        self.assertEqual(len(stale2), 1, stale2)
        self.assertIn("該行無被壓下的違規", stale2[0])

    def test_the_two_criteria_markers_do_not_claim_each_other(self) -> None:
        """`child-encoding-ok:` 內含 `encoding-ok:`——裸子字串比對會讓判準一
        對同一行多出一筆 stale。兩個標記必須各自只被自己的判準認領。"""
        line = f"x = 1  # {_CHILD_OK_MARKER} 只印 ASCII\n"
        self.assertEqual(_marker_lines(line, _OK_MARKER), {})
        self.assertEqual(_marker_lines(line, _CHILD_OK_MARKER), {1: "只印 ASCII"})
        plain = f"y = 2  # {_OK_MARKER} 走系統碼頁\n"
        self.assertEqual(_marker_lines(plain, _OK_MARKER), {1: "走系統碼頁"})
        self.assertEqual(_marker_lines(plain, _CHILD_OK_MARKER), {})


# ══════════════════════════════════════════════════════════════════════════
# 判準三：**入口點自保**（R74／DEF-101-789 的同類站點）
# ══════════════════════════════════════════════════════════════════════════
# 判準二守的是「別人起的 child」；同一個缺陷還有另一面：一支會被當成獨立行程執行、
# 且會印非 ASCII 的入口點，不論誰起它都該自己有保護。這道把那一面也納管。
#
# 🔴 為何附一份**具名豁免清單**而不是「掃到就修」：`DEF-101-757` 明文禁止把
# 「已知的鎖射程缺口」只以劃界結案。本輪實掃 11 筆，其中 9 筆**本包無權就地修**，
# 逐筆理由見 `_ENTRY_WAIVER_REASONS`。把它們寫成一份會被機械檢查的清單，效果與
# 「靜默不管」完全不同：新出現的同類站點會紅、清單只准變短、而清單裡的檔案一旦被
# 修好就會因 stale 檢查逼人把它移出清單。
_ENTRY_WAIVER_REASONS = {
    # 帶存量 ruff 債：pre-commit 的 ruff 掃**整檔**，動這些檔就得在同一個 commit
    # 內清掉與本題無關的 lint 債（實測 16 筆，多為中文註解 E501，修法須逐支評估）。
    "ruff-debt": "帶存量 ruff 債，pre-commit 掃整檔 → 需連帶清無關 lint 債",
    # AISDLC_SDD 任何版本（含 LATEST）依 Copy-on-Evolve 不得由護欄層順手改。
    "copy-on-evolve": "AISDLC_SDD 版本樹，需該子專案授權面處置",
    # 測試檔／測試 fixture：實際載具是 tools/run_root_unittests.py（已有保護）或
    # pytest；逐支測試檔複製同一段保護＝把同一份知識抄上百次。
    "carrier-protected": "由已有保護的載具行程起，保護屬載具而非本檔",
}

#: {repo 相對路徑（LATEST 版名正規化）: 理由鍵}。**只准變短**。
_ENTRY_WAIVERS = {
    "AutoClaude/tools/_backfill_emit_real.py": "ruff-debt",
    "AutoClaude/tools/mutation_baseline_lock.py": "ruff-debt",
    "AutoClaude/tools/perf_baseline_lock.py": "ruff-debt",
    "AutoClaude/tools/setup_pg_runtime_role.py": "ruff-debt",
    "AISDLC_SDD/LATEST/tools/fsm_runtime/chaos_runner.py": "copy-on-evolve",
    "AISDLC_SDD/LATEST/tools/fsm_runtime/closure_evidence.py": "copy-on-evolve",
    "AISDLC_SDD/LATEST/tools/fsm_runtime/render_topology_dashboard.py":
        "copy-on-evolve",
    "tools/tests/test_workflow_permission_concurrency_lock.py":
        "carrier-protected",
    "AutoClaude/tests/fixtures/dummy_cli.py": "carrier-protected",
}
_ENTRY_WAIVER_CEILING = 9  # shrink-only：落地當下 9 筆


def _module_str_consts(tree: ast.Module) -> dict[str, str]:
    """模組層 `NAME = "字串"` 表（`sys.stderr.write(_GUIDANCE)` 這種一跳形態）。"""
    out: dict[str, str] = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    out[tgt.id] = node.value.value
    return out


def nonascii_console_lines(source: str) -> list[int]:
    """印非 ASCII 到 stdout/stderr 的呼叫起始行（`print` 與 `sys.std*.write`）。"""
    tree = ast.parse(source)
    consts = _module_str_consts(tree)
    hits: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = _call_tail_name(func) or ""
        if name == "write":
            if not (isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr in ("stdout", "stderr")):
                continue
        elif name != "print":
            continue
        for sub in ast.walk(node):
            text: str | None = None
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                text = sub.value
            elif isinstance(sub, ast.Name):
                text = consts.get(sub.id)
            if text and any(ord(char) > 127 for char in text):
                hits.add(node.lineno)
                break
    return sorted(hits)


def is_entry_point(source: str) -> bool:
    """有 `__main__` 守衛＝會被當成獨立行程執行。

    🔴 這裡**刻意不塗白**（與 `has_utf8_stdio_protection` 相反）：比對樣本本身含
    字串字面 `"__main__"`，塗白後會恆為 False。方向也是對的——註解掉的 `__main__`
    守衛會讓本判準過度納管（偏紅、要人補保護或列豁免），不會產生假綠。
    """
    return ('__name__ == "__main__"' in source
            or "__name__ == '__main__'" in source)


def scan_entry_points(
    files: list[Path], repo_root: Path, latest_name: str
) -> tuple[list[str], list[str]]:
    """回 (offenders, stale_waivers)：未豁免的違規／已不再違規的豁免項。"""
    offenders: list[str] = []
    still_offending: set[str] = set()
    for py in files:
        source = py.read_text(encoding="utf-8")
        if not is_entry_point(source) or has_utf8_stdio_protection(source):
            continue
        lines = nonascii_console_lines(source)
        if not lines:
            continue
        rel = py.relative_to(repo_root).as_posix().replace(latest_name, "LATEST")
        if rel in _ENTRY_WAIVERS:
            still_offending.add(rel)
            continue
        offenders.append(
            f"{rel}:{lines[0]}: 入口點印非 ASCII 但無 UTF-8 stdio 保護"
            f"（共 {len(lines)} 處）"
        )
    stale = [
        f"{rel}: 已不再違規（或檔案已移除），請把它從 _ENTRY_WAIVERS 移出"
        for rel in _ENTRY_WAIVERS
        if rel not in still_offending
    ]
    return offenders, stale


class TestEntryPointStdioProtection(unittest.TestCase):
    """入口點印非 ASCII ⇒ 必須自帶 UTF-8 stdio 保護（判準三）。"""

    def _all_files(self) -> list[Path]:
        files: list[Path] = []
        for root, _floor in _scan_roots():
            files += sorted(root.rglob("*.py"))
        return files + sorted(_scan_single_files())

    def test_entry_points_printing_non_ascii_are_protected(self) -> None:
        offenders, stale = scan_entry_points(
            self._all_files(), _REPO_ROOT, _latest_root().name
        )
        self.assertEqual(
            offenders, [],
            "以下入口點會印非 ASCII 卻無 UTF-8 stdio 保護（非 UTF-8 locale 下 "
            "stdout 直接 UnicodeEncodeError、stderr 印成 \\uXXXX）——請於 main() "
            "開頭加保護，或在 _ENTRY_WAIVERS 具名列入並附既有理由鍵：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            "_ENTRY_WAIVERS 有 stale 項（防豁免清單腐化）：\n" + "\n".join(stale),
        )

    def test_waiver_list_only_shrinks_and_every_entry_has_a_known_reason(self) -> None:
        self.assertLessEqual(
            len(_ENTRY_WAIVERS), _ENTRY_WAIVER_CEILING,
            f"_ENTRY_WAIVERS 由 {_ENTRY_WAIVER_CEILING} 增至 {len(_ENTRY_WAIVERS)}"
            "——本清單只准變短；新站點請就地修而不是加豁免",
        )
        unknown = {rel: why for rel, why in _ENTRY_WAIVERS.items()
                   if why not in _ENTRY_WAIVER_REASONS}
        self.assertEqual(unknown, {}, f"豁免理由鍵不在既有分類內：{unknown}")

    def test_criterion_red_green_on_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bad = root / "bad_entry.py"
            bad.write_text(
                "print('中文')\nif __name__ == '__main__':\n    pass\n",
                encoding="utf-8",
            )
            off, _ = scan_entry_points([bad], root, "LATEST")
            self.assertEqual(len(off), 1, off)
            self.assertIn("bad_entry.py:1", off[0])
            good = root / "good_entry.py"
            good.write_text(
                "import _stdio_utf8  # noqa: F401 \nprint('中文')\n"
                "if __name__ == '__main__':\n    pass\n",
                encoding="utf-8",
            )
            self.assertEqual(scan_entry_points([good], root, "LATEST")[0], [])
            ascii_only = root / "ascii_entry.py"
            ascii_only.write_text(
                "print('plain')\nif __name__ == '__main__':\n    pass\n",
                encoding="utf-8",
            )
            self.assertEqual(scan_entry_points([ascii_only], root, "LATEST")[0], [])

    def test_one_hop_module_constant_is_resolved(self) -> None:
        """`sys.stderr.write(_GUIDANCE)` 形態必須認得——R74 出事的那支 hook 正是
        這種寫法，只認字面引數的掃描器會漏掉它。"""
        source = (
            "import sys\n"
            "_MSG = '已禁用'\n"
            "sys.stderr.write(_MSG)\n"
            "if __name__ == '__main__':\n    pass\n"
        )
        self.assertEqual(nonascii_console_lines(source), [3])


# ══════════════════════════════════════════════════════════════════════════
# 判準四：**production 的 hook 呼叫形態**（R75／DEF-101-802）
# ══════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體：判準二只認「argv 第一個非旗標元素能解析成 repo 內某支 .py」的形態，
# `-m`／`-c` 明文不追（見該處劃界，那個劃界本身沒錯）。而 `.claude/settings.json`
# 註冊 hook 用的**正是** `python -c "...runpy.run_path(p)..."` ＋ 把腳本路徑當成
# 給 `-c` 程式碼的引數——判準二對它結構性全盲。
#
# 後果是：R74 那筆 P0（`block_bash_on_windows.py` 的中文指引在 cp1252 下降解成
# `\uXXXX`）之所以被 child 編碼判準覆蓋到，**唯一原因**是
# `tools/tests/test_check_hooks_liveness.py` 這支**測試**恰好用
# `[sys.executable, str(_HOOK)]` 直接執行形態起它（R75 QA 突變時 offender 訊息
# 逐字指向該行）。那一行改寫成 `-c`、或改用別的起法，判準就**靜默失去 production
# 唯一的那個站點**——而 production 一直都是 `-c` 形態，從來沒進過射程。
#
# 「量測載具只認棄用路徑的 marker、production 走另一條路所以真跑恆 0」是本 repo
# 已有前例的缺陷形態（DEF-76-001）。本判準把 production 的**註冊表自己**當成掃描
# 面：settings.json 內每一支被註冊的 hook 腳本都要有 UTF-8 stdio 保護，與誰在測
# 試裡怎麼起它完全無關。
_SETTINGS_JSON = _REPO_ROOT / ".claude" / "settings.json"

def hook_command_scripts(settings: dict) -> list[tuple[str, str]]:
    """`settings` 內每個 hook 條目**實際會跑到**的腳本 → [(事件名, repo 相對 posix 路徑)]。

    🔴 **R80：本函式此前只讀 `command` 字串，而那個假設已經被推翻。** Claude Code 的
    hook 條目有兩種形態，腳本路徑住在不同欄位：shell form 在 `command` 裡，exec form
    （帶 `args`，Windows 上不經 `bash.exe`＝不閃 console 視窗）則**結構性地搬到
    `args`**。R80 把根 `.claude/settings.json` 轉成 exec form 之後實測：本函式掃出來的
    腳本集合由 6 支變成 1 支（只剩啟動器自己）。

    後果**不是**「這道鎖會紅」，是它會**恆綠**——分母掃出 0 支 ⇒ 沒有東西可違反，
    rc 與「正確地全部通過」一模一樣。本檔判準四、
    `test_doc_loc_baseline_freshness_r60.registered_hook_basenames`（經本函式）
    都建立在這個分母上。⇒ 解析邏輯已收進唯一真相源 `tools/lib/hook_wiring.py`，
    兩種形態都認得；本函式只保留呼叫端介面（回傳形狀逐字不變）。
    """
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
    import hook_wiring  # noqa: PLC0415

    return hook_wiring.settings_targets(settings)


def scan_hook_command_children(
    settings: dict, repo_root: Path
) -> tuple[list[str], list[str], int]:
    """回 (offenders, missing, 納管腳本數)——腳本去重後計數。

    `missing`＝註冊了卻不存在的腳本。settings.json 明載「目標腳本缺檔＝fail-open
    exit 0」，那是**執行期**刻意的 P0 防護（hook 缺檔不該把所有工具鎖死）；但
    「註冊表指向一支不存在的腳本」在**靜態**上就是一道靜默死掉的 hook，兩件事不同。
    """
    offenders: list[str] = []
    missing: list[str] = []
    seen: set[str] = set()
    for event, rel in hook_command_scripts(settings):
        if rel in seen:
            continue
        seen.add(rel)
        script = repo_root / rel
        if not script.is_file():
            missing.append(f"{event} 註冊了不存在的腳本 {rel}（hook 靜默失效）")
            continue
        if has_utf8_stdio_protection(script.read_text(encoding="utf-8")):
            continue
        offenders.append(
            f"{rel}（由 .claude/settings.json 的 {event} 以 `python -c` ＋ "
            "runpy 形態起）無 UTF-8 stdio 保護——hook 的輸出是使用者唯一看得到的"
            "指引，非 UTF-8 locale 下 stderr 會逃脫成 \\uXXXX、stdout 直接"
            "UnicodeEncodeError（DEF-101-789 逐字重現於 GitHub windows-latest）"
        )
    return offenders, missing, len(seen)


#: 註冊腳本數下限（同 `tree_count_verdict` 的雙邊帶）。值＝R75 實測去重 4 支
#: （sdd_hook_router／block_bash_on_windows／check_ps1_encoding／check_sh_eol）
#: × 0.95。低於下限＝有 hook 被拔掉或正則失效；高於上界＝下限過時要重釘。
_HOOK_SCRIPT_FLOOR = 4

#: R74 那筆 P0 的站點。判準四必須**自己**罩得住它，不靠任何測試檔碰巧用了
#: 直接執行形態（那正是本判準存在的理由）。
_R74_P0_HOOK_REL = ".claude/hooks/block_bash_on_windows.py"


class TestRegisteredHookScriptsAreInChildEncodingScope(unittest.TestCase):
    """判準四：`.claude/settings.json` 註冊的 hook 腳本必須自帶 UTF-8 stdio 保護。"""

    def _real_settings(self) -> dict:
        self.assertTrue(_SETTINGS_JSON.is_file(), f"找不到 {_SETTINGS_JSON}")
        return json.loads(_SETTINGS_JSON.read_text(encoding="utf-8"))

    def test_every_registered_hook_script_is_protected(self) -> None:
        offenders, missing, count = scan_hook_command_children(
            self._real_settings(), _REPO_ROOT
        )
        self.assertEqual(missing, [], "\n".join(missing))
        self.assertEqual(
            offenders, [],
            "以下 production hook 腳本無 UTF-8 stdio 保護（請在該檔加 "
            "`import _stdio_utf8` / `init_utf8_streams` / 就地 reconfigure）：\n"
            + "\n".join(offenders),
        )
        verdict = tree_count_verdict("settings.json 註冊 hook 腳本數", count,
                                     _HOOK_SCRIPT_FLOOR)
        self.assertIsNone(verdict, verdict or "")

    def test_the_r74_p0_site_is_in_scope_without_help_from_any_test_file(self) -> None:
        """R74 P0 的那支 hook 必須經 **production 註冊表**進入射程。

        WHY 這條要單獨具名：它此前進入 child 編碼判準的唯一途徑是
        `tools/tests/test_check_hooks_liveness.py` 用直接執行形態起它——一支測試的
        寫法決定了另一道鎖的射程，改寫那行就靜默失去站點。本斷言只讀
        `.claude/settings.json`，與任何測試檔怎麼寫完全無關。
        """
        scripts = {rel for _event, rel in hook_command_scripts(self._real_settings())}
        self.assertIn(
            _R74_P0_HOOK_REL, scripts,
            f"{_R74_P0_HOOK_REL} 不在 settings.json 的 hook 佈線掃描結果內 ⇒ "
            "判準四對 R74 P0 站點失去射程（hook 被拔掉，或條目形態變了而 "
            "`tools/lib/hook_wiring.hook_entry_targets()` 撈不到路徑——R80 實測過"
            "後者：shell form 轉 exec form 時腳本路徑會從 command 搬進 args）。"
            "實得：" + repr(sorted(scripts)),
        )

    def test_the_scan_survives_the_exec_form_conversion(self) -> None:
        """🔴 R80 注入自證：**在轉換後的 settings 上**，這道鎖必須仍然抓得到違規。

        WHY 這條非有不可：exec form 把腳本路徑從 `command` 搬進 `args`，而失明的
        表徵是**恆綠**（分母掃出 0 支 ⇒ 沒有東西可違反），與「正確地全部通過」在 rc
        上無法區分。所以「轉換後 rc=0」證明不了任何事——必須證明「轉換後把註冊拿掉
        會轉紅」。

        注入用**真實檔案的內容**在記憶體裡動手（不寫磁碟）：合成 settings 證明不了
        判準對 repo 現況有牙，而真的改磁碟上的 settings.json 會影響同一棵樹上其他
        agent 的每一次工具呼叫（該檔記載過 hook 誤觸 deny 的 P0）。
        """
        real = self._real_settings()
        self.assertIn(
            _R74_P0_HOOK_REL,
            {rel for _e, rel in hook_command_scripts(real)},
            "控制組：真實 settings 應該掃得到那支 hook",
        )
        stripped = json.loads(json.dumps(real))
        for _event, entries in (stripped.get("hooks") or {}).items():
            for entry in entries or []:
                entry["hooks"] = [
                    hook for hook in entry.get("hooks") or []
                    if _R74_P0_HOOK_REL not in json.dumps(hook, ensure_ascii=False)
                ]
        self.assertNotIn(
            _R74_P0_HOOK_REL,
            {rel for _e, rel in hook_command_scripts(stripped)},
            "把該 hook 的註冊整條拿掉之後掃描結果竟然沒變 ⇒ 這道鎖是空轉的"
            "（正是 exec form 轉換若沒同步解析面時的樣子）",
        )
        self.assertTrue(
            has_utf8_stdio_protection(
                (_REPO_ROOT / _R74_P0_HOOK_REL).read_text(encoding="utf-8")
            ),
            f"{_R74_P0_HOOK_REL} 失去 UTF-8 stdio 保護＝R74 P0 復發",
        )

    # ── 判準紅綠自證：用**真實 production command 字樣**驅動，不用簡化版 ──────

    def _settings_with(self, script_rel: str) -> dict:
        """把真實 settings.json 裡起 R74 P0 那支 hook 的**整個條目**取來，只把腳本
        路徑換掉——這樣 fixture 驗的就是 production 當下的佈線形態本身，而不是一個
        我自己寫得比較好認的簡化字串。

        🔴 R80 訂正：此處原本硬斷言 production 是 `-c` ＋ runpy 形態（shell form）。
        那兩行斷言把 fixture 綁死在**一種**形態上，於是 exec form 轉換會讓這支自證
        直接 fail——而它要證的東西（判準能不能認出無保護的腳本）與形態無關。改成
        逐字搬真實條目、只換路徑，並以 `hook_entry_targets()` 回頭驗「真的換成功了」，
        形態變更不再需要動這裡。
        """
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
        import hook_wiring  # noqa: PLC0415

        real = json.loads(_SETTINGS_JSON.read_text(encoding="utf-8"))
        for _event, entries in (real.get("hooks") or {}).items():
            for entry in entries:
                for hook in entry.get("hooks") or []:
                    if _R74_P0_HOOK_REL not in hook_wiring.hook_entry_targets(hook):
                        continue
                    swapped = json.loads(
                        json.dumps(hook, ensure_ascii=False).replace(
                            _R74_P0_HOOK_REL, script_rel))
                    self.assertIn(
                        script_rel, hook_wiring.hook_entry_targets(swapped),
                        "fixture 換路徑後解析不到新路徑 ⇒ 這個 fixture 本身壞掉了")
                    return {"hooks": {"PreToolUse": [{
                        "matcher": "Bash", "hooks": [swapped]}]}}
        self.fail(f"真實 settings.json 內找不到會跑到 {_R74_P0_HOOK_REL} 的條目")

    def test_criterion_red_green_on_the_real_production_command_form(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "hooks").mkdir()
            target = root / "hooks" / "probe_hook.py"
            settings = self._settings_with("hooks/probe_hook.py")

            target.write_text("print('中文')\n", encoding="utf-8")
            offenders, missing, count = scan_hook_command_children(settings, root)
            self.assertEqual((missing, count), ([], 1))
            self.assertEqual(len(offenders), 1, offenders)
            self.assertIn("hooks/probe_hook.py", offenders[0])

            target.write_text("import _stdio_utf8  # noqa: F401 \nprint('中文')\n",
                              encoding="utf-8")
            self.assertEqual(scan_hook_command_children(settings, root)[0], [])

            # 只有註解寫著保護字樣 ⇒ 仍必須是紅（與判準二共用 code_only）
            target.write_text("# init_utf8_streams\nprint('中文')\n", encoding="utf-8")
            self.assertEqual(len(scan_hook_command_children(settings, root)[0]), 1)

            target.unlink()
            self.assertEqual(len(scan_hook_command_children(settings, root)[1]), 1)

    def test_the_floor_band_is_wired_to_the_same_criterion(self) -> None:
        """下限帶自證：註冊腳本被拔到只剩 1 支 ⇒ 紅（不靠 repo 現況剛好有幾支）。"""
        verdict = tree_count_verdict("settings.json 註冊 hook 腳本數", 1,
                                     _HOOK_SCRIPT_FLOOR)
        self.assertIsNotNone(verdict)
        self.assertIn("疑似縮小", verdict or "")


class TestScanRootsConfigPinning(unittest.TestCase):
    """守門自身樹清單釘選（QA-R13-2 同構延伸；手法同 parity test_tools_lib_in_scan_dirs）。

    WHY：per-tree 下限只防「樹內縮檔數」，不防「整樹自 _scan_roots 刪列」——
    刪一列即整樹靜默出界、零機械訊號。LATEST 版名以「LATEST」正規化，升版不失效
    （鍵風格對齊 parity 的 LATEST/tools/… 慣例）。樹清單有意變更時須連同本案改。
    """

    def test_scan_roots_pinned(self) -> None:
        latest_name = _latest_root().name
        rels = {
            root.relative_to(_REPO_ROOT).as_posix().replace(latest_name, "LATEST")
            for root, _floor in _scan_roots()
        }
        self.assertEqual(
            rels,
            {
                "tools",
                ".claude/hooks",
                "AutoClaude/tools",
                "AutoClaude/autoclaude",
                "AutoClaude/tests",
                "AutoClaude/scripts",
                "AutoClaude/alembic",
                "AISDLC_SDD/scripts",
                "AISDLC_SDD/LATEST/tools/fsm_runtime",
                "AISDLC_SDD/LATEST/tools/arch_fitness",
                "AISDLC_SDD/LATEST/.claude/hooks",
            },
        )

    def test_the_floor_band_catches_both_shrink_and_rot(self) -> None:
        """下限帶紅綠自證（R75／DEF-101-800）——**含 QA 實測到的那個腐化狀態**。

        `(files=81, floor=18)` 是 R75 QA 在本檔量到的真實數字：可以掉掉 63/81
        掃描面仍全綠。舊判準（單邊 `assertGreaterEqual`）對它是綠的，新判準必須紅，
        而且要在訊息裡直接給出該重釘的數字——否則「腐化了要重釘」只是一句期許。
        """
        rot = tree_count_verdict("tools", 81, 18)
        self.assertIsNotNone(rot, "QA 實測的腐化狀態（81 vs 18）竟被判為合格")
        self.assertIn("腐化上界", rot or "")
        self.assertIn(str(suggested_floor(81)), rot or "", "訊息須直接給出該填的數字")
        # 縮面（原意）仍必須紅
        shrink = tree_count_verdict("tools", 10, 77)
        self.assertIsNotNone(shrink)
        self.assertIn("疑似縮小", shrink or "")
        # 帶內＝綠：等於下限、等於上界、以及當回合實測值
        for actual, floor in ((77, 77), (repin_ceiling(77), 77), (81, 77)):
            self.assertIsNone(tree_count_verdict("tools", actual, floor),
                              f"帶內組合 ({actual}, {floor}) 被誤判為紅")

    def test_every_pinned_floor_is_inside_its_own_band(self) -> None:
        """釘下去的每個下限都必須對**當下實測**成立（含上界）——這是防「重釘時
        只改一棵樹、其他棵繼續腐化」。正職那道測試逐樹跑同一判準，本案是它的
        設定面複本：即使正職因別的原因被 skip，下限本身仍被量。"""
        stale: list[str] = []
        for root, floor in _scan_roots():
            if not root.is_dir():
                continue
            verdict = tree_count_verdict(
                root.relative_to(_REPO_ROOT).as_posix(),
                len(sorted(root.rglob("*.py"))), floor,
            )
            if verdict:
                stale.append(verdict)
        self.assertEqual(stale, [], "\n".join(stale))

    def test_scan_single_files_pinned(self) -> None:
        """R14 SCAN-PY-2：單檔清單釘選——刪一列即該檔靜默出界，同樹清單防護語意。
        LATEST 版名正規化，升版不失效（同樹清單慣例）。"""
        latest_name = _latest_root().name
        rels = {
            f.relative_to(_REPO_ROOT).as_posix().replace(latest_name, "LATEST")
            for f in _scan_single_files()
        }
        self.assertEqual(
            rels,
            {
                "AISDLC_SDD/conftest.py",
                "AISDLC_SDD/LATEST/tools/__init__.py",
            },
        )


# ---------------------------------------------------------------- 根層 lint 政策（R69 P3）
_RUFF_TOML = _REPO_ROOT / "tools" / "ruff.toml"
_AUTOCLAUDE_PYPROJECT = _REPO_ROOT / "AutoClaude" / "pyproject.toml"

#: `tools/tests/` 的 E501 存量債上限（**shrink-only 棘輪**，只准往下改）。
#:
#: 值＝R69 P3 落地當下的實測筆數，量法見 `_overlong_line_count()`。**刻意不是 ruff 的
#: 精確複本**：ruff 對「超限段落拆不開」的行（長 URL／單一 token）另有豁免，本量法沒有，
#: 因此本值是 ruff E501 筆數的**超集**（實測 ruff 側較小）。債務天花板取超集是安全方向
#: ——它只會把「多寫一行過長的行」更早攔下，不會放行。
_E501_DEBT_CEILING = 139


def _overlong_line_count(root: Path) -> int:
    """`root` 底下所有 `.py` 中「顯示寬度 > line-length」的行數。

    寬度依 East Asian Width 計（W/F 佔 2 欄），與 ruff 的 E501 同一種量法——本 repo 的
    註解與斷言訊息幾乎全是中文，用 `len()` 量會低估近一半（實測 141 vs 89）。
    """
    limit = _ruff_config()["line-length"]
    total = 0
    for path in sorted(root.rglob("*.py")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in line) > limit:
                total += 1
    return total


def _ruff_config() -> dict:
    return tomllib.loads(_RUFF_TOML.read_text(encoding="utf-8"))


_E501_EXPIRY_RE = re.compile(r"到期日：(\d{4})-(\d{2})-(\d{2})")

#: 一次續期的最長視窗（天）。原始視窗是三個月，留一點餘裕到約四個月；上限存在的
#: 唯一理由與 `root-infra-ci.yml` 的 `MAX_WAIVER_DAYS` 相同——杜絕「填 2099」把
#: 帶到期日的豁免變成變相永久停用。
_E501_WAIVER_MAX_DAYS = 120


def e501_waiver_verdict(text: str, today: date) -> str | None:
    """`None`＝豁免仍有效；回字串＝失效理由（純函式，日期由呼叫端注入）。"""
    found = _E501_EXPIRY_RE.search(text)
    if not found:
        return ("tools/ruff.toml 的 E501 存量債豁免沒有到期日 —— "
                "無到期日的豁免＝永久豁免")
    try:
        deadline = date(int(found[1]), int(found[2]), int(found[3]))
    except ValueError as exc:
        return (f"到期日 {found[0]!r} 無法解析為合法日期（{exc}）—— "
                "豁免設定壞掉時一律 fail-loud，不得靜默當成「沒有豁免」或「永久豁免」")
    if deadline < today:
        return (f"tools/ruff.toml 的 E501 存量債豁免已到期（{deadline}，今日 {today}）"
                " —— 二擇一：清完 tools/tests/ 的過長行並刪掉 "
                "[lint.per-file-ignores] 的 `tests/*.py`，或在缺陷帳本具名續期"
                "（附當時實際筆數趨勢）後把本檔的到期日往後改。不得靜默沿用")
    if (deadline - today).days > _E501_WAIVER_MAX_DAYS:
        return (f"到期日 {deadline} 距今 {(deadline - today).days} 天，超過"
                f"單次續期上限 {_E501_WAIVER_MAX_DAYS} 天 —— 上限存在的唯一理由"
                "就是杜絕「填一個很遠的日期」把帶到期日的豁免變成永久停用")
    return None


class TestRootToolsLintPolicy(unittest.TestCase):
    """根層護欄層的 ruff 設定必須存在、與 AutoClaude 側同步，且它的豁免不得靜默長大。

    WHY（R68-38）：本 repo 此前**全 monorepo 只有一份 ruff 設定**（`AutoClaude/pyproject.toml`），
    而 ruff 是「由每個檔往上找最近的設定檔」——根層 `tools/` 上方一路到 repo 根都沒有任何
    ruff 設定，於是 `ruff check tools/` 套的是 ruff 出廠預設，印出的 `All checks passed!`
    是**假綠**：換上本 repo 自己宣告的規則集當場 199 筆。本類把那份設定釘成有消費者的東西。
    """

    def test_root_tools_has_its_own_ruff_config(self) -> None:
        self.assertTrue(
            _RUFF_TOML.is_file(),
            f"{_RUFF_TOML.name} 不存在 ⇒ 根層護欄層又回到「套 ruff 出廠預設」的假綠狀態",
        )

    def test_rule_set_is_identical_to_the_autoclaude_side(self) -> None:
        """規則集**逐字**對齊 AutoClaude；兩邊各走各的門檻就是下一次漂移。"""
        root = _ruff_config()
        ac = tomllib.loads(_AUTOCLAUDE_PYPROJECT.read_text(encoding="utf-8"))["tool"]["ruff"]
        self.assertEqual(
            root["lint"]["select"], ac["lint"]["select"],
            "根層 tools/ruff.toml 的 select 與 AutoClaude/pyproject.toml 不同步 —— "
            "同一批人、同一種程式碼不該被兩套規則管；要改請兩邊一起改",
        )
        self.assertEqual(root["line-length"], ac["line-length"])
        self.assertEqual(root["target-version"], ac["target-version"])

    def test_e501_debt_only_shrinks(self) -> None:
        """存量債棘輪：`tools/tests/` 的過長行數只准往下改。

        為何非有這道不可：`[lint.per-file-ignores]` 一旦掛上，ruff 對該類違規就完全閉嘴
        ——沒有棘輪的豁免會靜默長大，最後變成「整包 noqa」的另一種寫法。
        """
        actual = _overlong_line_count(_TESTS_DIR)
        self.assertLessEqual(
            actual, _E501_DEBT_CEILING,
            f"tools/tests/ 的過長行由 {_E501_DEBT_CEILING} 增至 {actual} —— "
            f"本棘輪只准往下改。新寫的行請自行折行（既有債另有到期日，見 tools/ruff.toml）",
        )

    def test_the_e501_waiver_expiry_is_actually_enforced(self) -> None:
        """到期日必須**真的會到期**（R74 訂正）。

        原版只用 regex 驗「有沒有 `到期日：YYYY-MM-DD` 這串字樣」，於是那個日期
        永遠不會生效——而 `tools/ruff.toml` 逐字宣告「到期時二擇一…不得靜默沿用」、
        本測試的 docstring 又宣稱與會比日期的 `WAIVER_UNTIL` 同體例。**宣稱與實作
        不符的鎖比沒有鎖更糟**（同一個類別裡已經有過一次同型訂正：另一道的斷言曾是
        恆真式子而 docstring 宣稱以 ruff 實跑驗證）。現在改成真的比日期。
        """
        verdict = e501_waiver_verdict(_RUFF_TOML.read_text(encoding="utf-8"),
                                      date.today())
        self.assertIsNone(verdict, verdict or "")

    def test_the_expiry_criterion_is_red_when_it_should_be(self) -> None:
        """判準自證：四種輸入的紅綠（不靠 repo 現況剛好是哪一天）。"""
        ok = "# 到期日：2026-11-02（自 R69 P3 落地日起三個月）\n"
        today = date(2026, 8, 4)
        self.assertIsNone(e501_waiver_verdict(ok, today))
        # 已過期 → 阻斷自動恢復
        self.assertIn("已到期", e501_waiver_verdict(ok, date(2026, 11, 3)) or "")
        # 沒有到期日 → 永久豁免
        self.assertIn("沒有到期日", e501_waiver_verdict("# 條 2：E501\n", today) or "")
        # 「填一個很遠的日期」＝變相永久停用
        self.assertIn(
            "上限",
            e501_waiver_verdict("# 到期日：2099-01-01\n", today) or "",
        )
        # 日期字樣在但不是合法日期 → fail-loud，不得靜默當成「沒有豁免」
        self.assertIn(
            "無法解析",
            e501_waiver_verdict("# 到期日：2026-02-30\n", today) or "",
        )

    def test_the_config_actually_covers_the_root_tools_tree(self) -> None:
        """反空轉：設定檔必須真的**罩得住**根層 tools/ 樹（不是放在某個沒人走到的角落）。

        以 ruff 自己的解析結果為準——`ruff check --show-settings <本樹任一支檔>` 印出的
        `Settings path` 必須就是 `tools/ruff.toml`、`linter.rules.enabled` 必須含 E501、
        `linter.line_length` 必須等於本檔宣告值。**不能**靠讀 toml 自我確認：這一整類缺陷
        的形狀就是「檔案內容正確、但 ruff 的向上尋找根本走不到它」，讀 toml 對此恆真。

        R69 訂正（SA 實測）：本測試原本的斷言是 `_overlong_line_count(...) >= 0` ——
        一個**恆真**式子，而 docstring 卻宣稱「以 `ruff check --show-settings` 驗證」。
        宣稱與實作不符的鎖比沒有鎖更糟：它讓人以為這條路已經被守住了。
        """
        ruff = shutil.which("ruff")
        if ruff is None:
            self.skipTest(
                "[TOOL-ABSENCE] ruff 不在 PATH——本道要驗的是 ruff **自己**的設定解析結果，"
                "沒有 ruff 就無從驗起。刻意 skip 而非靜默通過：假綠正是本道要治的病"
            )
        probe = Path(__file__).resolve()  # tools/tests/ 底下任一支檔＝本檔自己
        proc = subprocess.run(
            [ruff, "check", "--show-settings", str(probe)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(_REPO_ROOT), check=False,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"`ruff check --show-settings` 非零退出（rc={proc.returncode}）：\n{proc.stderr}",
        )
        out = proc.stdout
        m = re.search(r'^Settings path: "(.+)"$', out, re.MULTILINE)
        self.assertIsNotNone(
            m, "`--show-settings` 輸出沒有 `Settings path:` 行——ruff 對本樹**找不到任何**"
               "設定檔（＝退回出廠預設，正是本道要抓的假綠；R69 實測：把 tools/ruff.toml "
               "移走即重現此訊息），或 ruff 輸出格式改變。兩種都不得以寬鬆比對繞過")
        self.assertEqual(
            Path(m.group(1)).resolve(), _RUFF_TOML.resolve(),
            f"ruff 對 {probe} 解析到的設定檔是 {m.group(1)}，不是 {_RUFF_TOML} ⇒ 本樹套的是"
            f"別人的設定或出廠預設，`tools/ruff.toml` 是一份沒有射程的擺設",
        )
        enabled = re.search(r"^linter\.rules\.enabled = \[\n(.*?)^\]$", out,
                            re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(enabled, "`--show-settings` 輸出沒有 `linter.rules.enabled` 區塊")
        self.assertIn(
            "line-too-long (E501)", enabled.group(1),
            "ruff 實際啟用的規則集不含 E501 —— 出廠預設 select 就不含它，"
            "這正是「`All checks passed!` 是假綠」的成因",
        )
        self.assertRegex(
            out, rf"(?m)^linter\.line_length = {_ruff_config()['line-length']}$",
            f"ruff 實際採用的 line_length 不是 tools/ruff.toml 宣告的 "
            f"{_ruff_config()['line-length']}",
        )


if __name__ == "__main__":
    unittest.main()
