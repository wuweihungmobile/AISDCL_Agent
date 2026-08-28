#!/usr/bin/env python3
"""測試樹原始碼「Windows 磁碟機假路徑」自我檢測（R11 A1c；R11 複審 SD-2/ARCH-2 補強；
R12 ARCH-R12-4 掃描面擴大至四個測試樹）.

WHY：R11 真 Mac 首跑實證——測試裡把 D:/repo 這種磁碟機假路徑字串塞給 Path()，
它只在 Windows 是絕對路徑；POSIX 上 `repo_root / 絕對路徑` 的 pathlib join 會退化
成串接（D:/repo/D:/repo/…）、resolve 後恆不相等 → Windows 全綠、Mac/Linux 假紅
（test_check_hooks_liveness.py TestIsHooksEffective 兩案例實際紅過）。修法是改用
_platform_helpers.ABS_FAKE_REPO 平台中立常數；本測試機械掃描測試樹原始碼，
防未來有人複製舊 pattern 再踩一次。

R11 四方複審補強（SD-2/ARCH-2）：原 regex 只抓「Path( 後緊接引號＋大寫磁碟機
＋正斜線」單一形態——漏抓 r/f 等字串前綴變體、反斜線形態 X:\\、小寫磁碟機，
以及**裸字串**磁碟機路徑常數（原病灶正是不經 Path( 直呼的裸字串）。改為抓
「任意字串字面值以磁碟機路徑開頭」（引號後緊接單一字母＋冒號＋斜線或反斜線；
匹配起點是引號本身，故 r/f/b 前綴一律涵蓋）。並：
  (a) 每行先剝 `#` 註解尾再掃（註解舉例不誤報；heuristic 不解析字串內的 #，
      字串內含 # 且其後才出現磁碟機路徑的極端形態會漏掃，屬可接受取捨）；
  (b) 豁免顯式平台語意 PureWindowsPath(/PurePosixPath(（該行本來就是在寫
      特定平台路徑）與逐檔豁免清單 _ALLOWED（附 WHY）；
  (c) 支援行尾 `# platform-ok: <理由>` 豁免標記（合法命中須逐行附理由明示處置）。

R12 掃描面（ARCH-R12-4；DEF-101-149 病灶類別在其他測試樹此前零守門）：
  1. tools/tests/（本目錄，非遞迴——維持 R11 現狀）
  2. AISDLC_SDD/scripts/tests/（非遞迴）
  3. AutoClaude/tests/（**遞迴**，含 plugins/core/contract/… 子樹）
  4. LATEST 版 tools/fsm_runtime/tests/（遞迴；LATEST 以 scripts/sdd_version.py
     SSOT subprocess 解析——手法對齊 check_script_parity；解析失敗 fail-loud，
     不得靜默縮小掃描邊界。凍結版 v0.01~v0.2X 依鐵律不掃、也不可修）
"""
from __future__ import annotations

import ast
import functools
import io
import os
import re
import subprocess
import sys
import tempfile
import tokenize
import unittest
from collections.abc import Callable
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import NamedTuple

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

# 🔴 姊妹鎖（`test_subprocess_encoding_hygiene`）的三支下限帶純函式**直接取用、
# 不複製**。WHY：兩支鎖守的是同一件事「掃描面不得靜默腐化」，判準各寫一份就是兩個
# 會漂移的真相——本輪立案的形態正是「藥已開好，卻只餵給兩個病人中的一個」。
sys.path.insert(0, str(_TESTS_DIR))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
import git_paths  # noqa: E402  ← R81 XPL-S1-01：git 路徑列舉的唯一取數層
import sdd_latest  # noqa: E402
import test_subprocess_encoding_hygiene as _sister  # noqa: E402

# R85／A-3：單平台專屬外部執行檔的**詞彙表**是量測本身，唯一的家在這支 probe
# （檔內逐字：「這兩張表是判準本身。改它就是重新定義量測」）。本檔只當「門」，不留第二份。
import xplat_hazard_census as _CENSUS  # noqa: E402
from test_subprocess_encoding_hygiene import (  # noqa: E402
    repin_ceiling,
    suggested_floor,
    tree_count_verdict,
)

# 任意字串字面值以「單一字母磁碟機 + 冒號 + / 或 \」開頭即命中；
# 匹配起點為引號本身，r/f/b 等前綴與 Path( 包裹與否皆無關（裸字串同樣命中）。
_DRIVE_STR_RE = re.compile(r"""["'][A-Za-z]:[/\\]""")
# 逐檔豁免（repo 相對路徑 → WHY）。豁免檔案消失時 fail-loud（防清單腐化）。
_ALLOWED: dict[str, str] = {
    "tools/tests/_platform_helpers.py": (
        "平台中立常數的單一定義點（win32 分支本來就該寫磁碟機路徑）"
    ),
    "AutoClaude/tests/test_perception.py": (
        "Windows 專屬 perception/cmd-shim 的 mock 回傳值與純字串斷言，"
        "無 pathlib join 語意（R12 親讀 20 筆命中逐一核可，非 DEF-101-149 病灶）"
    ),
    "AutoClaude/tests/test_perception_platform_honesty.py": (
        "上一列 test_perception.py 的姊妹檔（R68 新增，測 cmd.exe 8191 字元硬上限守門）："
        "三筆命中皆為 _build_cmd_shim_line() 的輸入字串字面值，直接進字串長度計算、"
        "不進 pathlib join；且 cmd shim 本來就只在 Windows 成立，改平台中立常數即失去測意"
    ),
}
_OK_MARKER = "platform-ok:"
_EXPLICIT_PLATFORM = ("PureWindowsPath(", "PurePosixPath(")


def _latest_root() -> Path:
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。
    委派 tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    return sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")


def _latest_fsm_tests_dir() -> Path:
    """LATEST 版 fsm_runtime/tests。"""
    return _latest_root() / "tools" / "fsm_runtime" / "tests"


def _scan_roots() -> list[tuple[Path, bool, int]]:
    """（掃描根, 是否遞迴, 該樹檔數下限）清單；根缺席或**離開下限帶**由測試 fail-loud。

    per-tree 下限（R12 SD 一審 SD-3）：全域總數下限對「單樹靜默縮面」不敏感
    （如 LATEST 樹 rglob 被改 glob，總數 377→303 仍過全域 200）；逐樹釘選使任一
    樹縮面必紅。下限值一律＝落地當回合實測 × 0.95（`suggested_floor()`）、一律
    遞迴掃描、且與姊妹鎖 `test_subprocess_encoding_hygiene._scan_roots()` 逐檔對稱
    （由 `TestScanSurfaceParityWithSisterLock` 機械看守）。三項設計取捨的立案缺陷、
    實測數字與沿革全文搬至
    docs/06_quality/CrossPlatform_Guard_Line_History.md〈_scan_roots 三處修正 WHY〉節。
    """
    latest = _latest_root()
    return [
        # 🔴 護欄層重釘 R97 追加當輪由 85085→85394 新增 3 支鎖檔，`tools/tests`  round-label-ok
        # 實測 67 支越過腐化上界 66（`TestScanRootFloorBand` 開的藥：只還守得住
        # 79% 掃描面），依失敗訊息重釘 53 → 64。
        (_TESTS_DIR, True, 64),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts" / "tests", True, 28),
        (_REPO_ROOT / "AutoClaude" / "tests", True, 268),
        # LATEST fsm_runtime **整棵遞迴**（原本 tests/ 與頂層分兩列、頂層還是 flat
        # ⇒ `meta_halt/`／`modality/` 兩個子樹整組在射程外）。
        (latest / "tools" / "fsm_runtime", True, 158),
        # 🔴 R69（DEF-101-702／R68-34）：以上全是測試樹。於是「Windows 開發者把
        # `D:/…` 字面路徑寫進生產碼」這條路在 mac 側全套護欄全綠——掃描面與缺陷面
        # 錯位。R69 實測擴面後存量債為 0，屬零成本擴面：生產碼與測試碼受同一判準。
        (_REPO_ROOT / "AutoClaude" / "autoclaude", True, 194),
        (_REPO_ROOT / "AutoClaude" / "tools", True, 42),
        (_REPO_ROOT / "AutoClaude" / "scripts", True, 1),
        (_REPO_ROOT / "AutoClaude" / "alembic", True, 18),
        # `tools` 與 `.claude/hooks` 兩棵的下限刻意只認並行包動工前就存在的那些檔：
        # 把一個當下還在變動的量寫成常數，下一輪必然對不上。
        # R85／F1 重釘 17→27（腐化上界逐字要求；`tools/probe/guard_layer_dedup_census.py` 觸發）。
        (_REPO_ROOT / "tools", True, 27),
        (_REPO_ROOT / ".claude" / "hooks", True, 2),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts", True, 13),
        # R81 10→21（`quota_ledger.py`／`quota_limits.py` 落地）；R85／P12 21→30
        # （`unattended_authz.py` 落地）；R98 30→41（`quota_policy_env.py`／
        # `schedule_backend_calendar.py`／`sentinel_lifecycle_arm.py` 三支新子模組落地，
        # 本樹 43 支越過腐化上界 40，重釘理由與淨額詳見 `CrossPlatform_R98_Scan_Findings.md`）。
        (_REPO_ROOT / "tools" / "lib", True, 41),
        (latest / "tools" / "arch_fitness", True, 2),
        (latest / ".claude" / "hooks", True, 5),
    ]


def _scan_single_files() -> list[Path]:
    """樹機制掃不到的零散活躍 `.py`（逐檔具名，與姊妹鎖同一份清單）。

    不能把整個 `AISDLC_SDD/` 根樹納入——rglob 會誤掃凍結版 v0.01~v0.29。
    """
    return [
        _REPO_ROOT / "AISDLC_SDD" / "conftest.py",
        _latest_root() / "tools" / "__init__.py",
    ]


#: 零散單檔的檔數下限（等於清單長度：少一支＝有人刪了具名檔，必須是寫下來的動作）。
_SINGLE_FILE_FLOOR = 2
#: 零散單檔在下限帶訊息裡的標籤。
_SINGLE_UNIT_LABEL = "<零散單檔>"


def _scan_units() -> list[tuple[str, list[Path], int]]:
    """（標籤, 檔案清單, 檔數下限）——樹與零散單檔統一形狀，本檔五道判準共用。

    🔴 統一成一支的理由：本檔原有五個各自展開的掃描迴圈，每一個都自帶一份
    「列舉檔案 ＋ 判下限」的複本。擴掃描面時只改其中幾份，就是①那個缺口的
    製造方式；五份複本也讓「下限只有下界」這件事要修五次。
    """
    specs: list[tuple[Path, int, list[Path]]] = []
    for root, recursive, floor in _scan_roots():
        if not root.is_dir():
            raise AssertionError(f"掃描根缺席：{root}（邊界不得靜默縮小）")
        found = root.rglob("*.py") if recursive else root.glob("*.py")
        specs.append((root, floor, sorted(p for p in found
                                          if "__pycache__" not in p.parts)))
    roots = [root for root, _floor, _files in specs]
    units: list[tuple[str, list[Path], int]] = []
    for root, floor, files in specs:
        owned = [p for p in files if _owning_root(p, roots) == root]
        units.append((root.relative_to(_REPO_ROOT).as_posix(), owned, floor))
    singles = sorted(p for p in _scan_single_files() if p.is_file())
    units.append((_SINGLE_UNIT_LABEL, singles, _SINGLE_FILE_FLOOR))
    return units


def _owning_root(py: Path, roots: list[Path]) -> Path:
    """巢狀掃描根之間由**最長前綴**（最具體的那棵）認領該檔。

    order-independent：不靠清單順序決定歸屬，改清單順序不會讓某棵樹的下限
    突然對不上。這是「全部改遞迴」得以成立的前提——否則 `tools` 遞迴會把
    `tools/tests` 的 56 支再算一次，兩邊下限都失去意義。
    """
    return max((r for r in roots if r == py.parent or r in py.parents),
               key=lambda r: len(r.parts))


def floor_band_problems(counts: list[tuple[str, int, int]]) -> list[str]:
    """（標籤, 實測, 下限）逐筆過姊妹鎖的雙邊帶；回問題清單，空＝合格。

    純函式（紅綠由合成注入自證，見 `TestScanRootFloorBand`）。
    """
    return [
        verdict
        for label, actual, floor in counts
        if (verdict := tree_count_verdict(label, actual, floor)) is not None
    ]


def run_unit_scan(
    scanner: Callable[[str, str], tuple[list[str], list[str]]],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """對 `_scan_units()` 每一支檔跑 `scanner`；回 (違規, stale, parse 失敗, 下限帶)。

    🔴 早退不得遮蔽（Scan-H⑦）：單檔 parse 失敗只記一筆並續掃，下限帶在**全部**
    掃完之後才算——原本的寫法把下限斷言放在迴圈內，第一棵樹一失敗就同時吃掉
    「其他樹的下限」與「違規清單」兩份訊號，而失敗訊息只講第一棵樹。
    """
    offenders: list[str] = []
    stale: list[str] = []
    parse_failures: list[str] = []
    counts: list[tuple[str, int, int]] = []
    for label, files, floor in _scan_units():
        scanned = 0
        for py in files:
            rel = py.relative_to(_REPO_ROOT).as_posix()
            try:
                off, st = scanner(py.read_text(encoding="utf-8"), rel)
            except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
                parse_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
                continue
            offenders.extend(off)
            stale.extend(st)
            scanned += 1
        counts.append((label, scanned, floor))
    return offenders, stale, parse_failures, floor_band_problems(counts)


def scan_drive_literal(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale)。stale 恆空（本判準的標記不做 stale 偵測）。

    本輪抽出：第一道判準原本只有「吃 `Path`」的入口，於是它是本檔唯一無法用合成
    字串直接餵的判準——注入語料矩陣（`TestXplatInjectionMatrix`）需要對**每一道**
    判準問同一個問題，缺一個入口就等於那一格永遠量不到。
    """
    offenders: list[str] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _OK_MARKER in line:  # (c) 行尾豁免標記（附理由）
            continue
        code = line.split("#", 1)[0]  # (a) 剝註解尾（heuristic，見 docstring）
        if any(tok in code for tok in _EXPLICIT_PLATFORM):  # (b) 顯式平台語意
            continue
        if _DRIVE_STR_RE.search(code):
            offenders.append(f"{rel}:{lineno}: {line.strip()}")
    return offenders, []


def _scan_file(py: Path) -> list[str]:
    rel = py.relative_to(_REPO_ROOT).as_posix()
    return scan_drive_literal(py.read_text(encoding="utf-8"), rel)[0]


class TestPlatformNeutralPaths(unittest.TestCase):
    def test_no_windows_drive_fake_paths(self) -> None:
        offenders: list[str] = []
        counts: list[tuple[str, int, int]] = []
        for label, files, floor in _scan_units():
            tree_scanned = 0
            for py in files:
                if py.relative_to(_REPO_ROOT).as_posix() in _ALLOWED:
                    continue
                offenders.extend(_scan_file(py))
                tree_scanned += 1
            counts.append((label, tree_scanned, floor))
        self.assertEqual(
            offenders,
            [],
            "發現 Windows 磁碟機假路徑字面值（POSIX 上非絕對路徑 → join 語意分歧假紅）"
            "——請改用 tools/tests/_platform_helpers.ABS_FAKE_REPO；確屬合法用法時，"
            "改寫為顯式 PureWindowsPath(…) 或行尾加 `# platform-ok: <理由>` 豁免：\n"
            + "\n".join(offenders),
        )
        band = floor_band_problems(counts)
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    def test_allowed_exemptions_not_stale(self) -> None:
        """豁免清單防腐化：登記的檔案消失即紅（比照 parity 清單 stale 檢查）。"""
        for rel, why in _ALLOWED.items():
            self.assertTrue(
                (_REPO_ROOT / rel).is_file(),
                f"_ALLOWED 豁免 stale：{rel} 已不存在（WHY={why}）——請自清單移除",
            )


# ══════════════════════════════════════════════════════════════════════════════
# R60 round 3 — 測試不得把「樹內固定路徑」當可寫暫存區（QA-R60R3-01／ARCH-R60R3-05）
# ══════════════════════════════════════════════════════════════════════════════
# WHY 全文（缺陷本體／判準設計／誠實劃界）搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R60 round 3 tmpdir 判準 WHY〉節。
_TMPDIR_OK_MARKER = "tmpdir-ok:"
_WRITE_ATTRS = frozenset({"mkdir", "write_text", "write_bytes", "touch", "unlink", "rmdir"})
_SHUTIL_WRITE_FUNCS = frozenset({"rmtree", "copytree", "move"})
# 走 tempfile 的表達式一律放行（那正是本鎖要人改成的樣子）；`tmp_path`／`tmpdir` 是
# pytest 內建 fixture，語意同為行程獨立暫存目錄。
_TEMPFILE_MARKS = frozenset({
    "mkdtemp", "mkstemp", "TemporaryDirectory", "NamedTemporaryFile", "TemporaryFile",
    "gettempdir", "tmp_path", "tmpdir", "tmp_path_factory",
})


def _has_file_ref(node: ast.AST) -> bool:
    return any(isinstance(s, ast.Name) and s.id == "__file__" for s in ast.walk(node))


def _has_tempfile_ref(node: ast.AST) -> bool:
    for s in ast.walk(node):
        if isinstance(s, ast.Attribute) and s.attr in _TEMPFILE_MARKS:
            return True
        if isinstance(s, ast.Name) and s.id in _TEMPFILE_MARKS:
            return True
    return False


def _is_in_tree_seed(node: ast.AST) -> bool:
    """該表達式是否為「樹內固定路徑」的種子（由 `__file__` 推導且未走 tempfile）。"""
    return _has_file_ref(node) and not _has_tempfile_ref(node)


def _path_root_name(node: ast.AST) -> str | None:
    """取路徑表達式最左的名稱；`self.tmp / a / b` → `self.tmp`、`X / "y"` → `X`。"""
    cur: ast.AST = node
    for _ in range(40):  # 上界防病態巢狀導致無界迴圈
        if isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
            cur = cur.left
        elif isinstance(cur, ast.Attribute):
            if isinstance(cur.value, ast.Name):
                return f"self.{cur.attr}" if cur.value.id == "self" else cur.value.id
            cur = cur.value
        elif isinstance(cur, ast.Name):
            return cur.id
        elif isinstance(cur, ast.Call):
            if isinstance(cur.func, ast.Attribute):
                cur = cur.func.value        # x.resolve() → x
            elif cur.args:
                cur = cur.args[0]           # Path(x) → x
            else:
                return None
        elif isinstance(cur, ast.Subscript):
            cur = cur.value                 # parents[3] → parents
        else:
            return None
    return None


def _module_level_tree_names(tree: ast.Module) -> set[str]:
    """模組層被指派為樹內固定路徑的常數名（只看 top-level，不看函式內）。"""
    out: set[str] = set()
    for stmt in tree.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)) or stmt.value is None:
            continue
        if not _is_in_tree_seed(stmt.value):
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        out.update(t.id for t in targets if isinstance(t, ast.Name))
    return out


def _self_attr_tree_names(cls: ast.ClassDef) -> set[str]:
    """該 class 內被指派為樹內固定路徑的 `self.<attr>`（逐類獨立，不跨類污染）。"""
    out: set[str] = set()
    for node in ast.walk(cls):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            continue
        if not _is_in_tree_seed(node.value):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for t in targets:
            if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                    and t.value.id == "self"):
                out.add(f"self.{t.attr}")
    return out


def _tmpdir_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token 內的標記（字串字面值同形文字不誤判）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _TMPDIR_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_TMPDIR_OK_MARKER, 1)[1].strip()
    return markers


def _write_target(node: ast.Call) -> tuple[ast.AST, str] | None:
    """該呼叫若是寫入動作，回傳 (目標表達式, 動作描述)；否則 None。"""
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr in _WRITE_ATTRS:
            return func.value, f".{func.attr}()"
        if (func.attr in _SHUTIL_WRITE_FUNCS and isinstance(func.value, ast.Name)
                and func.value.id == "shutil" and node.args):
            return node.args[0], f"shutil.{func.attr}()"
        return None
    if isinstance(func, ast.Name) and func.id == "open" and node.args:
        mode = ""
        if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
            mode = str(node.args[1].value)
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = str(kw.value.value)
        if any(c in mode for c in "wax+"):
            return node.args[0], f"open(mode={mode!r})"
    return None


def scan_intree_tmpdir(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。

    stale＝標記存在但該行沒有被壓下的違規（含 WHY 留空）→ 必須清掉或補 WHY。
    這條自檢是本鎖不淪為「永久白名單」的唯一保障（R60 已有
    `_PENDING_MIGRATION_SITES` 掛 pending 名義卻刻意不加 stale 自檢的前科）。
    """
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _tmpdir_markers(source)
    module_names = _module_level_tree_names(tree)
    # (掃描節點, 該範圍可見的樹內固定路徑名稱)；class 各自帶自己的 self.<attr>
    scopes: list[tuple[ast.AST, set[str]]] = [(tree, module_names)]
    scopes.extend(
        (node, module_names | _self_attr_tree_names(node))
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    )

    offenders: dict[tuple[int, str], str] = {}
    used: set[int] = set()
    for scope_node, tracked in scopes:
        for node in ast.walk(scope_node):
            if not isinstance(node, ast.Call):
                continue
            hit = _write_target(node)
            if hit is None:
                continue
            target, op = hit
            if _has_tempfile_ref(target):
                continue
            if not (_has_file_ref(target) or _path_root_name(target) in tracked):
                continue
            if markers.get(node.lineno):
                used.add(node.lineno)
                continue
            expr = " ".join((ast.get_source_segment(source, target) or "?").split())[:70]
            offenders[(node.lineno, op)] = (
                f"{rel}:{node.lineno}: {op} 寫入樹內固定路徑 `{expr}`"
                "（並行兩行程必互踩 → 假紅；請改用 tempfile.mkdtemp()）"
            )
    stale = [
        f"{rel}:{lineno}: tmpdir-ok 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used
    ]
    return [offenders[k] for k in sorted(offenders)], stale


def _tmpdir_scan_roots() -> list[tuple[Path, bool, int]]:
    """（掃描根, 是否遞迴, 該樹檔數下限）；下限＝落地當回合實測 × 0.95。

    🔴 本輪重釘（與 `_scan_roots()` 同一筆缺陷的第二個病灶）：原下限是「首掃數打
    八折」的化石且**只有下界**。落地當回合實測三棵已越過腐化上界（56 對 44、
    282 對 223、54 對 43），也就是本判準的掃描面此前可以掉掉兩成而全綠。改用姊妹
    鎖的雙邊帶（`tree_count_verdict`）後，下限自己過期時會當場紅並印出該填的數字。

    🔴 掃描面比本檔第一道判準多一棵「**凍結基線 v0.01**」，這是刻意的，WHY：
      `AISDLC_SDD/scripts/ci-gate.sh` 的 `FROZEN_BASELINE="AISDLC_SDD_v0.01"` 是
      **雙軌閘門實際會執行的兩棵樹之一**（另一棵是 LATEST）。第一道判準（磁碟機假
      路徑）不掃凍結版是因為那是「不可修的舊碼」；但本判準守的是「閘門自己會不會
      假紅」——v0.01 的測試每次 ci-gate 都真的在跑，它踩到的並行假紅會直接讓閘門
      說謊。「不掃它」等於讓已修好的東西可以無聲退化回去。
      中間 28 版（v0.02~v0.29）不在此列：任何自動閘門都不執行它們（ADR-XPLAT-001
      §2 機械事實），且那 95 個同型站點依 Copy-on-Evolve 尚待裁決是否回補——
      把它們納進來會讓本鎖一上線就紅，而那紅燈反映的是待決策，不是新退化。
    """
    return [
        (_TESTS_DIR, False, 64),                                       # 實測 67
        (_REPO_ROOT / "AISDLC_SDD" / "scripts" / "tests", False, 28),  # 實測 29
        (_REPO_ROOT / "AutoClaude" / "tests", True, 268),              # 實測 282
        (_latest_fsm_tests_dir(), True, 74),                           # 實測 78
        (_REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01"                # 實測 54
         / "tools" / "fsm_runtime" / "tests", True, 51),
    ]


class TestNoInTreeWritableTmpDir(unittest.TestCase):
    """測試檔不得把 tracked 樹內固定路徑當可寫暫存區（見上方區段 WHY）。"""

    def test_no_test_writes_into_a_fixed_in_tree_path(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        counts: list[tuple[str, int, int]] = []
        for root, recursive, floor in _tmpdir_scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = sorted(root.rglob("*.py") if recursive else root.glob("*.py"))
            scanned = 0
            for py in files:
                rel = py.relative_to(_REPO_ROOT).as_posix()
                try:
                    off, st = scan_intree_tmpdir(py.read_text(encoding="utf-8"), rel)
                except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
                    parse_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
                    continue
                offenders.extend(off)
                stale.extend(st)
                scanned += 1
            counts.append((root.relative_to(_REPO_ROOT).as_posix(), scanned, floor))
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現測試寫入樹內固定路徑（兩行程並行時互刪 → 與被測邏輯無關的假紅）"
            "——請改用 tempfile.mkdtemp()＋tearDown shutil.rmtree(..., ignore_errors=True)；"
            f"確屬刻意者於該行行尾加 `# {_TMPDIR_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_TMPDIR_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        band = floor_band_problems(counts)
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以下以注入 fixture 自證判準紅綠（fixture 僅存在於 tmp，不留違規樣本於 repo）──

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_intree_tmpdir(source, "fixture_case.py")

    def test_injected_self_attr_offender_is_detected(self) -> None:
        """本缺陷的原形態（`self.tmp` ← 樹內固定路徑，setUp mkdir）必紅。"""
        off, stale = self._scan(
            "from pathlib import Path\n"
            "class T:\n"
            "    def setUp(self):\n"
            "        self.tmp = Path(__file__).resolve().parent / '_tmp_rules'\n"
            "        self.tmp.mkdir(parents=True, exist_ok=True)\n"
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn(".mkdir()", off[0])
        self.assertEqual(stale, [])

    def test_injected_module_const_offender_is_detected(self) -> None:
        """模組層常數形態（`OUT = Path(__file__).parent / 'x'` 後 write_text）必紅。"""
        off, _ = self._scan(
            "from pathlib import Path\n"
            "OUT = Path(__file__).parent / 'snapshots'\n"
            "def test_x():\n"
            "    (OUT / 'a.json').write_text('{}', encoding='utf-8')\n"
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn(".write_text()", off[0])

    def test_mkdtemp_form_is_accepted(self) -> None:
        """修法慣例（mkdtemp）必綠——否則本鎖會逼人改回舊寫法。"""
        off, stale = self._scan(
            "import shutil, tempfile\n"
            "from pathlib import Path\n"
            "class T:\n"
            "    def setUp(self):\n"
            "        self.tmp = Path(tempfile.mkdtemp(prefix='x_'))\n"
            "        self.tmp.mkdir(parents=True, exist_ok=True)\n"
            "    def tearDown(self):\n"
            "        shutil.rmtree(self.tmp, ignore_errors=True)\n"
        )
        self.assertEqual((off, stale), ([], []))

    def test_read_only_use_of_a_tree_path_is_not_flagged(self) -> None:
        """唯讀取樣本檔（fixtures）不得誤報——否則整棵測試樹都會紅。"""
        off, _ = self._scan(
            "from pathlib import Path\n"
            "FIXTURES = Path(__file__).parent / 'fixtures'\n"
            "def test_x():\n"
            "    assert (FIXTURES / 'a.yaml').read_text(encoding='utf-8')\n"
        )
        self.assertEqual(off, [])

    def test_local_variable_form_is_declared_out_of_scope(self) -> None:
        """劃界釘死：函式區域變數**不追**（見區段 WHY 的作用域碰撞前車之鑑）。

        這支測試存在的意義不是「保護這個行為」，而是讓射程邊界**被寫下來且可被看見**
        ——哪天有人要把區域變數納入，必須先來改掉這支測試，於是那個決定不會是靜默的。
        """
        off, _ = self._scan(
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[1]\n"
            "def test_x():\n"
            "    d = ROOT / 'build' / 'x'\n"
            "    d.mkdir(parents=True, exist_ok=True)\n"
        )
        self.assertEqual(off, [], "區域變數形態應在射程外——射程若被擴大請同步改本測試")

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        base = (
            "from pathlib import Path\n"
            "OUT = Path(__file__).parent / 'snapshots'\n"
            "def test_x():\n"
        )
        off, stale = self._scan(
            base + f"    OUT.mkdir(exist_ok=True)  # {_TMPDIR_OK_MARKER} golden 快照目錄\n")
        self.assertEqual((off, stale), ([], []), "附 WHY 的標記應壓下違規且不判 stale")

        off, stale = self._scan(
            base + f"    OUT.mkdir(exist_ok=True)  # {_TMPDIR_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertEqual(len(stale), 1, stale)
        self.assertIn("WHY 留空", stale[0])

        off, stale = self._scan(
            base + f"    assert OUT.exists()  # {_TMPDIR_OK_MARKER} 已改用 mkdtemp\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        self.assertIn("該行無被壓下的違規", stale[0])

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """標記只認 COMMENT token——字串字面值裡的同形文字不得當豁免用。"""
        off, _ = self._scan(
            "from pathlib import Path\n"
            "OUT = Path(__file__).parent / 'snapshots'\n"
            "def test_x():\n"
            f"    s = '# {_TMPDIR_OK_MARKER} 假裝豁免'\n"
            "    OUT.mkdir(exist_ok=True)\n"
        )
        self.assertEqual(len(off), 1, "字串裡的標記不得生效")

    def test_scan_surface_is_not_silently_empty(self) -> None:
        """反空轉：判準在真實檔案上跑得動且掃描根皆存在（防路徑寫錯靜默零違規）。"""
        roots = _tmpdir_scan_roots()
        self.assertGreaterEqual(len(roots), 5, "掃描根被刪列？")
        for root, _recursive, floor in roots:
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}")
            self.assertGreater(floor, 0, f"{root} 的下限不得為 0（等於沒有下限）")

    def test_detector_survives_a_real_file_roundtrip(self) -> None:
        """判準對「真的寫在磁碟上的檔」也成立（非只在字串 fixture 上成立）。"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fixture_case.py"
            p.write_text(
                "from pathlib import Path\n"
                "OUT = Path(__file__).parent / '_tmp_x'\n"
                "OUT.mkdir(exist_ok=True)\n",
                encoding="utf-8",
            )
            off, stale = scan_intree_tmpdir(p.read_text(encoding="utf-8"), "fixture_case.py")
        self.assertEqual(len(off), 1, off)
        self.assertEqual(stale, [])


# ══════════════════════════════════════════════════════════════════════════════
# R69 — 反方向：測試不得拿 POSIX 絕對路徑字面值去斷言 Path 產物
# ══════════════════════════════════════════════════════════════════════════════
# WHY 全文（缺陷本體／判準設計／誠實劃界）搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R69 反方向 POSIX 絕對路徑判準
# WHY〉節。
_POSIX_OK_MARKER = "posix-abs-ok:"
# 以單一 `/` 起頭、次字元非 `/`（排除 `//host` UNC 與註解式 `//`）非空白（排除純 "/"）。
_POSIX_ABS_RE = re.compile(r"^/(?![/\s])\S")


def _posix_abs_literal(node: ast.AST) -> bool:
    return (isinstance(node, ast.Constant) and isinstance(node.value, str)
            and bool(_POSIX_ABS_RE.match(node.value)))


def _posix_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token（字串字面值內的同形文字不當豁免）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _POSIX_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_POSIX_OK_MARKER, 1)[1].strip()
    return markers


def _literal_args(call: ast.Call) -> list[ast.Constant]:
    """該 assert 呼叫的引數中所有 POSIX 絕對路徑字面值（含容器內巢狀；跳過 f-string）。"""
    out: list[ast.Constant] = []
    stack: list[ast.AST] = list(call.args) + [kw.value for kw in call.keywords]
    while stack:
        node = stack.pop()
        if isinstance(node, ast.JoinedStr):  # f-string 整棵子樹跳過（見劃界）
            continue
        if _posix_abs_literal(node):
            out.append(node)  # type: ignore[arg-type]
            continue
        stack.extend(ast.iter_child_nodes(node))
    return out


def scan_posix_abs_asserts(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _posix_markers(source)
    offenders: dict[tuple[int, int], str] = {}
    used: set[int] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if not node.func.attr.startswith("assert"):
            continue
        for lit in _literal_args(node):
            # WHY 留空的標記不生效（truthiness 判斷，對齊 tmpdir 判準）
            hit_line = next((ln for ln in (lit.lineno, node.lineno) if markers.get(ln)), None)
            if hit_line is not None:
                used.add(hit_line)
                continue
            offenders[(lit.lineno, lit.col_offset)] = (
                f"{rel}:{lit.lineno}: {node.func.attr}(…) 的引數是 POSIX 絕對路徑字面值 "
                f"`{lit.value}`（比對對象若由 Path/os.fspath 算出，Windows 上會渲染成"
                "反斜線 ⇒ 字面值必然落空、Mac 全綠 Windows 假紅）"
            )
    stale = [
        f"{rel}:{lineno}: {_POSIX_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return [offenders[k] for k in sorted(offenders)], stale


class TestNoPosixAbsPathLiteralInAsserts(unittest.TestCase):
    """assert 引數不得寫死 POSIX 絕對路徑字面值（見上方區段 WHY）。"""

    def test_no_posix_abs_literal_asserted_against_path_output(self) -> None:
        offenders, stale, parse_failures, band = run_unit_scan(scan_posix_abs_asserts)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現 assert 拿 POSIX 絕對路徑字面值比對（Windows 上 Path 渲染成反斜線 ⇒ "
            "本機全綠、windows-compat-ci 假紅，R69 病灶實例）——請改成 "
            "`str(Path(<同一常數>))` 或 `PurePosixPath`／`as_posix()` 明示語意；"
            f"確屬刻意者於該行行尾加 `# {_POSIX_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_POSIX_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以下以注入 fixture 自證判準紅綠（fixture 僅存在於字串，不留違規樣本於 repo）──

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_posix_abs_asserts(source, "fixture_case.py")

    def test_injected_original_defect_shape_is_detected(self) -> None:
        """R69 病灶原形態（`assertIn("/elsewhere", printed)`）必紅。"""
        off, stale = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertIn("/elsewhere", printed, "須指出實際指向的路徑")\n'
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn("/elsewhere", off[0])  # posix-abs-ok: 判準自己的訊息字串，非 Path 產物
        self.assertIn("assertIn", off[0])
        self.assertEqual(stale, [])

    def test_fixed_shape_is_accepted(self) -> None:
        """修法慣例（`str(Path(常數))`）必綠——否則本鎖會逼人改回舊寫法。"""
        off, stale = self._scan(
            "from pathlib import Path\n"
            "class T:\n"
            '    _ELSEWHERE = "/elsewhere/AutoClaude/tools/run_local_nightly.sh"\n'
            "    def test_x(self):\n"
            "        self.assertIn(str(Path(self._ELSEWHERE)), printed)\n"
        )
        self.assertEqual((off, stale), ([], []))

    def test_literal_nested_in_a_container_is_detected(self) -> None:
        """容器內的字面值同樣是病灶（`assertEqual(x, ["/a/b"])`）。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertEqual(paths, ["/a/b", "rel/c"])\n'
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn("/a/b", off[0])  # posix-abs-ok: 同上，比對判準自己的訊息字串

    def test_fstring_message_fragment_is_not_flagged(self) -> None:
        """f-string 訊息片段不算字面值（實測 2 筆誤報的形狀；見劃界）。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertEqual(lower, 0, f"{parent}/archive/（小寫）復活了")\n'
        )
        self.assertEqual(off, [])

    def test_relative_and_bare_slash_are_not_flagged(self) -> None:
        """相對路徑與純 `/`／`//` 不在射程（前者無平台分歧，後者非路徑形狀）。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertIn("docs/04_planning", out)\n'
            '        self.assertEqual(sep, "/")\n'
            '        self.assertIn("// 註解", src)\n'
        )
        self.assertEqual(off, [])

    def test_bare_pytest_assert_is_declared_out_of_scope(self) -> None:
        """劃界釘死：**本判準（過寬近似）**對 pytest 裸 assert 不追（見區段 WHY 的
        44 筆實測噪音；R69 P1 複測為 41 筆，仍全數是 slash 指令／CLI 旗標／URL）。

        這支測試存在的意義不是保護此行為，而是讓射程邊界**被寫下且可被看見**——
        哪天要納入裸 assert，必須先來改掉這支測試，於是那個決定不會是靜默的。

        🔴 R69 P1 更新：裸 assert 並非整體無守——本檔**第四道判準**
        （`scan_path_str_identity`，見下方區段）以「同句語法可見 Path 產物」為窄化
        條件，**涵蓋裸 assert**且實測零誤報。此處放行的只是「無 Path 產物在場」的
        過寬形態。
        """
        off, _ = self._scan('def test_x():\n    assert "/elsewhere" in printed\n')
        self.assertEqual(off, [], "裸 assert 形態應在射程外——射程若擴大請同步改本測試")

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        head = "class T:\n    def test_x(self):\n"
        off, stale = self._scan(
            head + f'        self.assertIn("/proc/self", out)  # {_POSIX_OK_MARKER} Linux 專屬\n')
        self.assertEqual((off, stale), ([], []), "附 WHY 的標記應壓下違規且不判 stale")

        off, stale = self._scan(
            head + f'        self.assertIn("/proc/self", out)  # {_POSIX_OK_MARKER}\n')
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertIn("WHY 留空", stale[0])

        off, stale = self._scan(
            head + f'        self.assertIn("x", out)  # {_POSIX_OK_MARKER} 已改用 str(Path())\n')
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        self.assertIn("該行無被壓下的違規", stale[0])

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """標記只認 COMMENT token——字串字面值裡的同形文字不得當豁免用。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            f"        s = '# {_POSIX_OK_MARKER} 假裝豁免'\n"
            '        self.assertIn("/elsewhere", out)\n'
        )
        self.assertEqual(len(off), 1, "字串裡的標記不得生效")

    def test_detector_catches_the_pre_fix_form_of_the_real_file(self) -> None:
        """自我驗證（最重要的一支）：本鎖對**真實病灶檔案的修復前形態**必須紅。

        做法是把現行真檔的修復行「改寫回」R69 病灶當初的寫法再餵給判準——不查
        git（不能綁 HEAD：修復一 commit，綁 HEAD 的自證就會反過來變紅，等於埋定時
        炸彈；也不能綁固定 commit：淺 clone 取不到只能 skip＝在 CI 上空轉）。
        現行真檔同時必須是乾淨的，兩個方向一起鎖，本判準才不可能空轉。
        """
        real = _REPO_ROOT / "tools" / "tests" / "test_dev_start.py"
        src = real.read_text(encoding="utf-8")
        fixed_form = "self.assertIn(str(Path(self._ELSEWHERE)), printed,"
        self.assertIn(
            fixed_form, src,
            "R69 病灶的修復形態已不在 test_dev_start.py ⇒ 本自證失去對象——"
            "該處若被重寫，請同步更新這支測試指向新的修復形態，不要直接刪掉自證",
        )
        pre_fix = src.replace(fixed_form, 'self.assertIn("/elsewhere", printed,')
        off, _ = scan_posix_abs_asserts(pre_fix, "tools/tests/test_dev_start.py@修復前重建")
        self.assertTrue(
            any("/elsewhere" in o for o in off),  # posix-abs-ok: 比對判準訊息，非 Path 產物
            f"本鎖對修復前的真實病灶抓不到 ⇒ 判準空轉：{off}",
        )
        off_now, stale_now = scan_posix_abs_asserts(src, "tools/tests/test_dev_start.py")
        self.assertEqual((off_now, stale_now), ([], []), "現行真檔必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R69 — 第三道判準的姊妹：不得用 `mock.call` 物件的 repr 拼裝輸出再拿去斷言
# ══════════════════════════════════════════════════════════════════════════════
# WHY 全文（缺陷本體／判準設計／誠實劃界）搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R69 mock.call repr 判準 WHY〉節。
_CALLREPR_OK_MARKER = "call-repr-ok:"
_CALL_LIST_ATTRS = ("call_args_list", "mock_calls", "await_args_list")


def _callrepr_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token（對齊本檔其他判準）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _CALLREPR_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_CALLREPR_OK_MARKER, 1)[1].strip()
    return markers


def _bare_repr_uses(body: list[ast.AST], name: str) -> list[tuple[int, str]]:
    """`body` 子樹中把裸名 `name` 丟進 str()/repr()/f-string 的站點 [(行號, 形態)]。"""
    hits: list[tuple[int, str]] = []
    for root in body:
        for node in ast.walk(root):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("str", "repr")):
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id == name:
                        hits.append((node.lineno, f"{node.func.id}({name})"))
            elif (isinstance(node, ast.FormattedValue)
                  and isinstance(node.value, ast.Name) and node.value.id == name):
                hits.append((node.lineno, f'f"{{{name}}}"'))
    return hits


def _call_list_loops(tree: ast.AST):
    """產出 (迴圈變數名, 該迴圈的 body 子樹清單)——僅限迭代 mock 呼叫紀錄清單者。"""
    for node in ast.walk(tree):
        if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
            pairs = [(node.elt, node.generators)]
        elif isinstance(node, ast.DictComp):
            pairs = [(node.key, node.generators), (node.value, node.generators)]
        elif isinstance(node, ast.For):
            pairs = [(None, [ast.comprehension(target=node.target, iter=node.iter,
                                               ifs=[], is_async=0)])]
        else:
            continue
        for elt, comps in pairs:
            for comp in comps:
                if not (isinstance(comp.iter, ast.Attribute)
                        and comp.iter.attr in _CALL_LIST_ATTRS):
                    continue
                if not isinstance(comp.target, ast.Name):
                    continue
                body = [elt] if elt is not None else list(getattr(node, "body", []))
                yield comp.target.id, [b for b in body if b is not None]


def scan_call_obj_repr(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _callrepr_markers(source)
    offenders: dict[int, str] = {}
    used: set[int] = set()
    for name, body in _call_list_loops(tree):
        for lineno, shape in _bare_repr_uses(body, name):
            if markers.get(lineno):
                used.add(lineno)
                continue
            offenders[lineno] = (
                f"{rel}:{lineno}: `{shape}` 把 mock.call 物件整個 repr 掉"
                "（反斜線被轉義成 `\\\\`、換行變 `\\n` 字面 ⇒ 對路徑／多行文案的斷言"
                "在 Windows 必假紅）——請改取實際引數 `str(a) for c in … for a in c.args`"
            )
    stale = [
        f"{rel}:{lineno}: {_CALLREPR_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return [offenders[k] for k in sorted(offenders)], stale


class TestNoMockCallObjectRepr(unittest.TestCase):
    """拼裝斷言用輸出時不得 repr 整個 mock.call 物件（見上方區段 WHY）。"""

    def test_no_call_object_repr_used_to_build_asserted_output(self) -> None:
        offenders, stale, parse_failures, band = run_unit_scan(scan_call_obj_repr)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現以 mock.call 物件的 repr 拼裝斷言用輸出（R69 病灶家族，4 處實例）——"
            f"確屬刻意者於該行行尾加 `# {_CALLREPR_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_CALLREPR_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以注入 fixture 自證判準紅綠 ──────────────────────────────────────────

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_call_obj_repr(source, "fixture_case.py")

    def test_injected_original_defect_shape_is_detected(self) -> None:
        """病灶原形態（generator + `str(c)`）必紅。"""
        off, stale = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        printed = " ".join(str(c) for c in fake_print.call_args_list)\n'
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn("str(c)", off[0])
        self.assertEqual(stale, [])

    def test_listcomp_and_for_loop_and_fstring_forms_are_detected(self) -> None:
        """三種等價寫法（list comp／for 迴圈／f-string 內插）同樣是病灶。"""
        for src in (
            "class T:\n    def t(self):\n"
            "        calls = [str(c) for c in proc.stdin.write.call_args_list]\n",
            "class T:\n    def t(self):\n"
            "        for c in m.mock_calls:\n            out.append(repr(c))\n",
            "class T:\n    def t(self):\n"
            '        out = [f"{c}" for c in m.await_args_list]\n',
        ):
            with self.subTest(src=src):
                off, _ = self._scan(src)
                self.assertEqual(len(off), 1, off)

    def test_fixed_shape_is_accepted(self) -> None:
        """修法慣例（取 `.args` 實際引數）必綠——否則本鎖會逼人改回舊寫法。"""
        off, stale = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        printed = " ".join(str(a) for c in fake_print.call_args_list'
            " for a in c.args)\n"
            '        other = "\\n".join(str(c.args[0]) for c in mp.call_args_list if c.args)\n'
        )
        self.assertEqual((off, stale), ([], []))

    def test_unrelated_iterables_are_not_flagged(self) -> None:
        """只認 mock 呼叫紀錄清單——迭代一般序列的 `str(x)` 不在射程。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            "        joined = ' '.join(str(x) for x in some_list)\n"
        )
        self.assertEqual(off, [])

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        head = "class T:\n    def test_x(self):\n"
        line = "        calls = [str(c) for c in m.call_args_list]"
        off, stale = self._scan(f"{head}{line}  # {_CALLREPR_OK_MARKER} 只比對呼叫次數\n")
        self.assertEqual((off, stale), ([], []), "附 WHY 的標記應壓下違規且不判 stale")

        off, stale = self._scan(f"{head}{line}  # {_CALLREPR_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertIn("WHY 留空", stale[0])

        off, stale = self._scan(
            f"{head}        x = 1  # {_CALLREPR_OK_MARKER} 已改取 .args\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        self.assertIn("該行無被壓下的違規", stale[0])

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """標記只認 COMMENT token——字串字面值裡的同形文字不得當豁免用。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            f"        s = '# {_CALLREPR_OK_MARKER} 假裝豁免'\n"
            "        calls = [str(c) for c in m.call_args_list]\n"
        )
        self.assertEqual(len(off), 1, "字串裡的標記不得生效")

    def test_detector_catches_the_pre_fix_form_of_the_real_files(self) -> None:
        """自我驗證：對兩支真實病灶檔的**修復前形態**必須紅，現行真檔必須乾淨。

        做法與上一道判準相同——不查 git（綁 HEAD 會在修復 commit 後反過來變紅），
        而是把現行真檔的修復行改寫回病灶寫法再餵給判準。
        """
        cases = [
            ("tools/tests/test_dev_start.py",
             'str(a) for c in fake_print.call_args_list for a in c.args',
             'str(c) for c in fake_print.call_args_list'),
            ("AutoClaude/tests/test_perception.py",
             '[str(a) for c in proc.stdin.write.call_args_list for a in c.args]',
             '[str(c) for c in proc.stdin.write.call_args_list]'),
        ]
        for rel, fixed_form, pre_fix_form in cases:
            with self.subTest(rel=rel):
                src = (_REPO_ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(
                    fixed_form, src,
                    f"{rel} 的修復形態已不在檔內 ⇒ 本自證失去對象——該處若被重寫，"
                    "請同步更新這支測試指向新的修復形態，不要直接刪掉自證",
                )
                off, _ = scan_call_obj_repr(src.replace(fixed_form, pre_fix_form),
                                            f"{rel}@修復前重建")
                self.assertTrue(off, f"本鎖對 {rel} 修復前的病灶抓不到 ⇒ 判準空轉")
                off_now, stale_now = scan_call_obj_repr(src, rel)
                self.assertEqual((off_now, stale_now), ([], []), f"{rel} 現行必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R69 P1 — 第四道判準：Path 的平台相依字串化不得當「識別鍵／比對值」
# ══════════════════════════════════════════════════════════════════════════════
# WHY 全文（缺陷本體／判準設計／誠實劃界／實測取捨）搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R69 P1 Path 識別鍵判準 WHY〉節。
_PATHKEY_OK_MARKER = "path-key-ok:"
_PATH_CTORS = frozenset({"Path", "PurePath"})
_EXPLICIT_FLAVOUR_CTORS = frozenset({"PurePosixPath", "PosixPath",
                                     "PureWindowsPath", "WindowsPath"})
# 只認「唯 pathlib 才有」的屬性名，避免與一般物件的同名屬性碰撞。
_PATH_ATTRS = frozenset({
    "relative_to", "resolve", "with_suffix", "with_name", "with_stem",
    "joinpath", "expanduser", "iterdir", "rglob", "absolute",
})
# 路徑形狀字面值：至少一個 `/` 分隔的段落，各段僅 word/點/連字號；可有前導單一 `/`。
# （純 "/"、"//host" UNC、含空白的訊息文句一律不符。）
_PATH_LITERAL_RE = re.compile(r"^/?(?!/)[\w.\-]+(?:/[\w.\-]+)+$")


def _is_ctor(node: ast.AST, names: frozenset[str]) -> bool:
    return (isinstance(node, ast.Call)
            and ((isinstance(node.func, ast.Name) and node.func.id in names)
                 or (isinstance(node.func, ast.Attribute) and node.func.attr in names)))


def _is_path_expr(node: ast.AST) -> bool:
    """語法上可判定為 pathlib 產物（顯式平台 flavour 不算——見劃界）。"""
    for n in ast.walk(node):
        if _is_ctor(n, _EXPLICIT_FLAVOUR_CTORS):
            return False
        if _is_ctor(n, _PATH_CTORS):
            return True
        if isinstance(n, ast.Attribute) and n.attr in _PATH_ATTRS:
            return True
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "fspath"):
            return True
    return False


def _str_of_path(node: ast.AST) -> bool:
    """`str(<Path 產物>)` 形態。"""
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "str" and len(node.args) == 1
            and _is_path_expr(node.args[0]))


def _identity_key_positions(tree: ast.AST):
    """產出所有「被當識別鍵」的運算式節點（4a 的射程定義）。"""
    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript):
            yield n.slice
        elif isinstance(n, ast.Dict):
            yield from (k for k in n.keys if k is not None)
        elif isinstance(n, ast.Set):
            yield from n.elts
        elif isinstance(n, ast.DictComp):
            yield n.key
        elif isinstance(n, ast.SetComp):
            yield n.elt
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == "add" and len(n.args) == 1):
            yield n.args[0]


def _assert_payloads(tree: ast.AST):
    """產出每個斷言的「待檢運算式清單」——含 pytest 裸 assert 與 assert*() 呼叫。"""
    for n in ast.walk(tree):
        if isinstance(n, ast.Assert):
            yield [n.test]
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr.startswith("assert")):
            yield list(n.args) + [kw.value for kw in n.keywords]


def _literals_vs_path_expr(roots: list[ast.AST]) -> list[ast.Constant]:
    """該斷言若同時有「路徑形狀字面值」與「Path 產物」，回傳前者；否則空。"""
    lits: list[ast.Constant] = []
    pathy = False
    stack: list[ast.AST] = list(roots)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.JoinedStr):  # f-string 訊息片段不算字面值（沿用慣例）
            continue
        if _is_ctor(node, _PATH_CTORS | _EXPLICIT_FLAVOUR_CTORS):
            pathy = pathy or _is_ctor(node, _PATH_CTORS)
            stack.extend(kw.value for kw in node.keywords)  # 建構子引數＝輸入，不算比對值
            continue
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and _PATH_LITERAL_RE.match(node.value)):
            lits.append(node)
            continue
        if _is_path_expr(node):
            pathy = True
        stack.extend(ast.iter_child_nodes(node))
    return lits if pathy else []


def _pathkey_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token（對齊本檔其他判準）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _PATHKEY_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_PATHKEY_OK_MARKER, 1)[1].strip()
    return markers


def scan_path_str_identity(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _pathkey_markers(source)
    offenders: dict[tuple[int, int], str] = {}
    used: set[int] = set()

    def _record(node: ast.AST, msg: str) -> None:
        if markers.get(node.lineno):
            used.add(node.lineno)
            return
        offenders[(node.lineno, node.col_offset)] = f"{rel}:{node.lineno}: {msg}"

    for key in _identity_key_positions(tree):          # 4a 產出側
        if _str_of_path(key):
            _record(key, f"`{ast.unparse(key)}` 把 Path 以 str() 當識別鍵"
                         "（Windows 上鍵會是反斜線形態 ⇒ 對它的正斜線斷言在 Windows "
                         "落空／assertNotIn 恆真＝假鎖）——請改用 `.as_posix()`")
    for payload in _assert_payloads(tree):             # 4b 斷言側
        for lit in _literals_vs_path_expr(payload):
            _record(lit, f"斷言拿路徑字面值 `{lit.value}` 與同句的 Path 產物比對"
                         "（Windows 上 Path 渲染成反斜線 ⇒ 本機全綠、"
                         "windows-compat-ci 假紅）——請改用 `.as_posix()` 比對，"
                         "或把字面值換成 `str(Path(<同一常數>))`")
    stale = [
        f"{rel}:{lineno}: {_PATHKEY_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return [offenders[k] for k in sorted(offenders)], stale


class TestNoPlatformDependentPathStringIdentity(unittest.TestCase):
    """Path 的平台相依字串化不得當識別鍵／比對值（見上方區段 WHY）。"""

    def test_no_platform_dependent_path_string_identity(self) -> None:
        offenders, stale, parse_failures, band = run_unit_scan(scan_path_str_identity)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現 Path 的平台相依字串化被當識別鍵／比對值（R69 P1 病灶家族）——"
            f"確屬刻意者於該行行尾加 `# {_PATHKEY_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_PATHKEY_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以注入 fixture 自證判準紅綠 ──────────────────────────────────────────

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_path_str_identity(source, "fixture_case.py")

    def test_injected_original_defect_shape_is_detected(self) -> None:
        """R69 P1 病灶原形態（`out[str(p.relative_to(root))] = src`）必紅。"""
        off, stale = self._scan(
            "def f(path, root, src, out):\n"
            "    out[str(path.relative_to(root))] = src\n"
        )
        self.assertEqual(len(off), 1, off)
        self.assertIn("as_posix", off[0])
        self.assertEqual(stale, [])

    def test_other_identity_key_positions_are_detected(self) -> None:
        """dict/set 字面值、推導式鍵、`.add()` 都是同一個病的入口。"""
        for src in (
            "def f(p, root):\n    d = {str(p.relative_to(root)): 1}\n",
            "def f(p, root):\n    s = {str(p.resolve())}\n",
            "def f(ps, root):\n    d = {str(p.relative_to(root)): 1 for p in ps}\n",
            "def f(ps, root, seen):\n"
            "    for p in ps:\n        seen.add(str(p.relative_to(root)))\n",
        ):
            with self.subTest(src=src):
                off, _ = self._scan(src)
                self.assertEqual(len(off), 1, off)

    def test_fixed_shape_is_accepted(self) -> None:
        """修法慣例（`.as_posix()`）必綠——否則本鎖會逼人改回舊寫法。"""
        off, stale = self._scan(
            "def f(path, root, src, out):\n"
            "    out[path.relative_to(root).as_posix()] = src\n"
        )
        self.assertEqual((off, stale), ([], []))

    def test_relative_literal_vs_path_expr_in_assert_is_detected(self) -> None:
        """4b：相對路徑字面值 vs 同句 Path 產物——第三道判準結構上抓不到的形態。"""
        src = ("class T:\n"
               "    def test_x(self, p, root):\n"
               '        self.assertEqual(str(p.relative_to(root)), "tools/dev_start.py")\n')
        off, _ = self._scan(src)
        self.assertEqual(len(off), 1, off)
        # 註：本行自身不會被本判準命中——`off[0]` 非 Path 產物，窄化條件不成立
        self.assertIn("tools/dev_start.py", off[0])
        # 交叉驗證劃界：第三道判準（要求 `/` 開頭）對同一段必然沉默——這正是本判準存在的理由
        self.assertEqual(scan_posix_abs_asserts(src, "fixture_case.py")[0], [])

    def test_bare_pytest_assert_is_in_scope(self) -> None:
        """4b **涵蓋裸 assert**（第三道判準對它劃界在外；本判準以窄化條件補上）。"""
        off, _ = self._scan(
            "def test_x(p, root):\n"
            '    assert str(p.relative_to(root)) == "tools/dev_start.py"\n'
        )
        self.assertEqual(len(off), 1, off)

    def test_explicit_flavour_and_constructor_inputs_are_not_flagged(self) -> None:
        """兩條劃界的實掃對應站點必須綠（否則本鎖一上線就是誤報）。"""
        off, _ = self._scan(
            "def f(rel, bk, tree):\n"
            "    dirs = {str(PurePosixPath(rel).parent)}\n"
            '    assert bk.extract_widget_tree(Path("/nonexistent/a.png")) is tree\n'
        )
        self.assertEqual(off, [])

    def test_non_path_literals_are_not_flagged(self) -> None:
        """無 Path 產物在場的路徑形狀字面值不在射程（避免爆量誤報）。"""
        off, _ = self._scan(
            "class T:\n"
            "    def test_x(self):\n"
            '        self.assertIn("docs/04_planning", out)\n'
            '        assert "/compact" in cmd\n'
        )
        self.assertEqual(off, [])

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        head = "def f(path, root, src, out):\n"
        line = "    out[str(path.relative_to(root))] = src"
        off, stale = self._scan(f"{head}{line}  # {_PATHKEY_OK_MARKER} 鍵只餵給 Windows API\n")
        self.assertEqual((off, stale), ([], []), "附 WHY 的標記應壓下違規且不判 stale")

        off, stale = self._scan(f"{head}{line}  # {_PATHKEY_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertIn("WHY 留空", stale[0])

        off, stale = self._scan(f"{head}    x = 1  # {_PATHKEY_OK_MARKER} 已改用 as_posix\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        self.assertIn("該行無被壓下的違規", stale[0])

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """標記只認 COMMENT token——字串字面值裡的同形文字不得當豁免用。"""
        off, _ = self._scan(
            "def f(path, root, src, out):\n"
            f"    s = '# {_PATHKEY_OK_MARKER} 假裝豁免'\n"
            "    out[str(path.relative_to(root))] = src\n"
        )
        self.assertEqual(len(off), 1, "字串裡的標記不得生效")

    def test_detector_catches_the_pre_fix_form_of_the_real_file(self) -> None:
        """自我驗證（最重要的一支）：對**真實 P1 病灶檔的修復前形態**必須紅。

        做法沿用本檔慣例——不查 git（綁 HEAD 會在修復 commit 後反過來變紅），
        而是把現行真檔的修復行改寫回病灶寫法再餵給判準；現行真檔同時必須乾淨。
        """
        rel = "tools/tests/test_dev_start.py"
        src = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        fixed_form = "out[path.relative_to(_TOOLS_DIR.parent).as_posix()] = src"
        self.assertIn(
            fixed_form, src,
            f"R69 P1 的修復形態已不在 {rel} ⇒ 本自證失去對象——該處若被重寫，"
            "請同步更新這支測試指向新的修復形態，不要直接刪掉自證",
        )
        pre_fix = src.replace(
            fixed_form, "out[str(path.relative_to(_TOOLS_DIR.parent))] = src")
        off, _ = scan_path_str_identity(pre_fix, f"{rel}@修復前重建")
        self.assertTrue(off, f"本鎖對 {rel} 修復前的 P1 病灶抓不到 ⇒ 判準空轉")
        off_now, stale_now = scan_path_str_identity(src, rel)
        self.assertEqual((off_now, stale_now), ([], []), f"{rel} 現行必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R74 — 第五道判準：平台專屬環境變數的讀取必須帶平台守衛（PKG-4 C）
# ══════════════════════════════════════════════════════════════════════════════
# WHY 全文（缺陷本體／判準設計／誠實劃界）搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R74 PATHEXT 平台守衛判準 WHY〉節。
_PATHEXT_OK_MARKER = "pathext-ok:"
_PATHEXT_READ_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\$env:PATHEXT", re.IGNORECASE),  # pathext-ok: 偵測器自己的形態表（PowerShell）
    re.compile(r"""os\.environ\[\s*["']PATHEXT"""),          # Python 下標讀取
    re.compile(r"""os\.environ\.get\(\s*["']PATHEXT"""),     # Python .get 讀取
    re.compile(r"""["']PATHEXT["']\s+in\s+os\.environ"""),   # Python 存在性判斷
    re.compile(r"""getenv\(\s*["']PATHEXT"""),               # os.getenv / C 風格
    re.compile(r"\$\{?PATHEXT\}?"),                          # POSIX shell
)
# 平台守衛述詞：出現任一即視為該檔已在判平台。刻意含 PowerShell 與 Python 兩套——
# 同一個判準要能對兩種語言說話，否則「換語言寫同一個缺陷」又是一個免費的繞道。
_PLATFORM_GUARDS: tuple[str, ...] = (
    # Python
    'os.name == "nt"', "os.name == 'nt'",
    'sys.platform == "win32"', "sys.platform == 'win32'",
    'sys.platform.startswith("win")', "sys.platform.startswith('win')",
    'platform.system() == "Windows"', "platform.system() == 'Windows'",
    "is_windows()", "IS_WINDOWS", "_is_windows",
    # PowerShell
    "$IsWindows", "$isWindowsHost", "PSVersion.Major -lt 6",
    "[System.Environment]::OSVersion", "$env:OS -eq",
    # POSIX shell
    "uname -s", "OSTYPE",
)


def _pathext_markers(source: str, *, is_python: bool) -> dict[int, str]:
    """{行號: WHY}——行尾豁免標記。

    🔴 Python 檔一律走 `tokenize`（沿用本檔前四道判準的既有慣例）：**本判準的射程含
    偵測器自己**，而偵測器的原始碼必然多處逐字提到標記字串（常數定義、docstring 說明、
    測試訊息）。純逐行文字掃描會把那些提及都當成真的豁免標記，於是每一處都被判 stale
    並要求刪除——鎖因為「說明自己」而翻紅，是最沒有說服力的一種紅（同
    `test_dev_start.py::ps_code_only` 剝行尾註解的理由）。
    `.ps1`／`.sh` 不是 Python，`tokenize` 會拋錯，故退回逐行掃描並要求標記出現在 `#`
    **之後**（那兩種語言沒有 docstring，此近似足夠）。
    """
    markers: dict[int, str] = {}
    if is_python:
        try:
            for tok in tokenize.generate_tokens(io.StringIO(source).readline):
                if tok.type == tokenize.COMMENT and _PATHEXT_OK_MARKER in tok.string:
                    markers[tok.start[0]] = tok.string.split(_PATHEXT_OK_MARKER, 1)[1].strip()
            return markers
        except (tokenize.TokenError, IndentationError, SyntaxError):
            markers.clear()  # 壞檔退回逐行，掃描面不得靜默縮小
    for lineno, line in enumerate(source.splitlines(), 1):
        head, sep, tail = line.partition("#")
        if sep and _PATHEXT_OK_MARKER in tail:
            markers[lineno] = tail.split(_PATHEXT_OK_MARKER, 1)[1].strip()
    return markers


def scan_unguarded_pathext(
    source: str, rel: str, *, is_python: bool | None = None
) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    if is_python is None:
        is_python = rel.endswith(".py") or not rel.rpartition(".")[2]
    markers = _pathext_markers(source, is_python=is_python)
    lines = source.splitlines()
    guard_first_at: int | None = next(
        (n for n, line in enumerate(lines, 1) if any(g in line for g in _PLATFORM_GUARDS)),
        None,
    )
    offenders: list[str] = []
    used: set[int] = set()
    for lineno, line in enumerate(lines, 1):
        code = line.split("#", 1)[0]   # 剝行尾註解（heuristic，見區段劃界）
        if not any(rx.search(code) for rx in _PATHEXT_READ_RES):
            continue
        # 🔴 `used` 記在「這一行確實有讀取語法」之後、**與守衛判斷無關**：stale 的語意
        # 是「標記在、但這一行根本沒有要壓下的東西」。若把 `used` 記在守衛判斷之後，
        # 一支檔案只要在前面某處出現過守衛，其標記就會被判 stale 而要求刪除——刪掉之後
        # 那一行就只靠「檔案前面有守衛」這個寬判準撐著，鑑別力反而下降。
        if markers.get(lineno):
            used.add(lineno)
            continue
        if guard_first_at is not None and guard_first_at < lineno:
            continue
        offenders.append(
            f"{rel}:{lineno}: 讀取 PATHEXT 但該行之前全檔沒有任何平台守衛"
            f"（`{line.strip()[:70]}`）——PATHEXT 是 Windows-only 概念，POSIX 上不存在"
            "且執行檔不帶副檔名 ⇒ 依它過濾候選會把所有候選濾光（DEF-101-766 形態）"
        )
    stale = [
        f"{rel}:{lineno}: {_PATHEXT_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return offenders, stale


def _pathext_scan_files() -> list[Path]:
    """全庫（**遞迴**）`.py`／`.ps1`／`.psm1`／`.sh`，排除快取／venv／版控目錄。

    射程刻意是**全庫**而不是「幾棵樹」：本判準治的正是「鎖只圈一個站點」，若又挑幾棵
    樹來圈，下一次同型缺陷只要寫在第 N+1 棵樹裡就免費過關。凍結版 v0.01~v0.29 亦在
    射程內——它們不可**修**，但若其中有未守衛的 PATHEXT 讀取，那是必須被看見的事實，
    不是可以從掃描面移除的事實（真要處置時再走 Copy-on-Evolve 例外核准）。
    """
    skip_parts = {"__pycache__", ".git", ".venv", "venv", ".pytest_cache",
                  ".ruff_cache", ".mypy_cache", "node_modules"}
    out: list[Path] = []
    for suffix in ("*.py", "*.ps1", "*.psm1", "*.sh"):
        for p in _REPO_ROOT.rglob(suffix):
            if skip_parts & set(p.parts):
                continue
            out.append(p)
    return sorted(out)


class TestPathextReadsAreePlatformGuarded(unittest.TestCase):
    """PATHEXT 讀取必須帶平台守衛（見上方區段 WHY）。"""

    def test_no_unguarded_pathext_read_in_repo(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        scanned = 0
        for path in _pathext_scan_files():
            rel = path.relative_to(_REPO_ROOT).as_posix()
            off, st = scan_unguarded_pathext(
                path.read_text(encoding="utf-8-sig", errors="replace"), rel)
            offenders.extend(off)
            stale.extend(st)
            scanned += 1
        # 反空轉下限＝R74 實掃數打八折取整。射程若被縮小（改成幾棵樹、或漏了某個
        # 副檔名）必紅——「鎖只圈一個站點」正是本判準要治的病，不得原地復發。
        self.assertGreaterEqual(
            scanned, 1000, f"PATHEXT 掃描面只有 {scanned} 檔——射程疑似被縮小")
        self.assertEqual(
            offenders, [],
            "發現未帶平台守衛的 PATHEXT 讀取（DEF-101-766 形態；R74 把該缺陷的鎖從"
            "「一個站點」擴為全庫形態掃描）——請在讀取前先判平台，或於該行行尾加 "
            f"`# {_PATHEXT_OK_MARKER} <WHY>`：\n" + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_PATHEXT_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )

    # ── 以下以合成樣本自證判準紅綠（樣本只存在於字串，不留違規樣本於 repo）──

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_unguarded_pathext(source, "fixture_case")

    def test_injected_ps1_defect_shape_is_detected(self) -> None:
        """DEF-101-766 的原形態（.ps1 無條件照 PATHEXT 過濾）必紅。"""
        off, stale = self._scan(
            "function Resolve-NativeExecutable {\n"
            "  $exts = @($env:PATHEXT -split ';')\n"
            "  return $null\n"
            "}\n"
        )
        self.assertEqual(len(off), 1, off)
        self.assertEqual(stale, [])

    def test_injected_python_port_of_the_same_defect_is_detected(self) -> None:
        """🔴 換語言寫同一個缺陷也必紅——這正是「一個站點級鎖」抓不到的那條路。"""
        for sample in (
            'exts = os.environ["PATHEXT"].split(os.pathsep)\n',
            'exts = os.environ.get("PATHEXT", "").split(";")\n',
            'exts = os.getenv("PATHEXT", "").split(";")\n',
            'if "PATHEXT" in os.environ: pass\n',
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertEqual(len(off), 1, f"{sample!r} 漏抓：{off}")

    def test_injected_shell_port_is_detected(self) -> None:
        off, _ = self._scan('echo "$PATHEXT" | tr ";" "\\n"\n')
        self.assertEqual(len(off), 1, off)

    def test_guarded_form_is_accepted(self) -> None:
        """修法慣例（先判平台）必綠——否則本鎖會逼人改回舊寫法。"""
        for sample in (
            "if (-not $isWindowsHost) { return $candidate }\n"
            "$exts = @($env:PATHEXT -split ';')\n",
            'if os.name == "nt":\n    exts = os.environ["PATHEXT"].split(";")\n',
            'if sys.platform.startswith("win"):\n'
            '    exts = os.environ.get("PATHEXT", "")\n',
        ):
            with self.subTest(sample=sample):
                off, stale = self._scan(sample)
                self.assertEqual((off, stale), ([], []), f"{sample!r} 誤報")

    def test_guard_after_the_read_does_not_count(self) -> None:
        """守衛排在讀取**之後**不算——順序反了等於沒守（與 DEF-101-766 同型）。"""
        off, _ = self._scan(
            "$exts = @($env:PATHEXT -split ';')\n"
            "if (-not $isWindowsHost) { return $candidate }\n"
        )
        self.assertEqual(len(off), 1, off)

    def test_mentioning_pathext_in_prose_is_not_flagged(self) -> None:
        """對照組：註解／docstring 提到 PATHEXT 不算讀取（本 repo 有大量在地 WHY）。"""
        off, _ = self._scan(
            "# PATHEXT 是 Windows-only 概念，POSIX 上不存在\n"
            '"""這個函式不再依 PATHEXT 過濾候選。"""\n'
        )
        self.assertEqual(off, [])

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        off, stale = self._scan(
            f'exts = os.environ["PATHEXT"]  # {_PATHEXT_OK_MARKER} 僅供 Windows 分支使用\n')
        self.assertEqual((off, stale), ([], []))

        off, stale = self._scan(f'exts = os.environ["PATHEXT"]  # {_PATHEXT_OK_MARKER}\n')
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertEqual(len(stale), 1, stale)

        off, stale = self._scan(f"x = 1  # {_PATHEXT_OK_MARKER} 已改走平台守衛\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")

    def test_detector_catches_the_pre_fix_form_of_the_real_guard_ps1(self) -> None:
        """自我驗證（最重要的一支）：對**真實病灶檔的修復前形態**必須紅。

        沿用本檔慣例——不查 git（綁 HEAD 會在修復 commit 後反過來變紅），而是把現行
        真檔的短路整段移除再餵給判準；現行真檔同時必須乾淨，兩個方向一起鎖。
        """
        rel = "tools/lib/WindowsAppsGuard.ps1"
        src = (_REPO_ROOT / rel).read_text(encoding="utf-8-sig")
        guard_line = "if (-not $isWindowsHost)"
        self.assertIn(
            guard_line, src,
            f"{rel} 內找不到非 Windows 短路 `{guard_line}` ⇒ 本自證失去對象——"
            "該處若被重寫，請同步更新這支測試指向新的守衛形態，不要直接刪掉自證",
        )
        pre_fix = "\n".join(
            line for line in src.splitlines()
            if not any(g in line for g in _PLATFORM_GUARDS)
        )
        off, _ = scan_unguarded_pathext(pre_fix, f"{rel}@修復前重建")
        self.assertTrue(off, f"本鎖對 {rel} 修復前的病灶抓不到 ⇒ 判準空轉")
        off_now, stale_now = scan_unguarded_pathext(src, rel)
        self.assertEqual((off_now, stale_now), ([], []), f"{rel} 現行必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R74 — 第六道判準：平台專屬 skip 的**方向**與**標籤對稱性**（PKG-4 D‧E‧F）
# ══════════════════════════════════════════════════════════════════════════════
# WHY 放在本檔（不另開新檔，沿用本檔「跨平台寫法家族」的收納契約）：判準本體住在
# `tools/lib/windows_skip_tags.py`（供 `tools/run_root_unittests.py` 在閘門上消費
# rc），本節是它的**單元測試**——證明四格方向表算得對、證明 pytest 形態真的在射程內、
# 證明反方向棘輪不是空轉。沒有這一節，那些判準只有「repo 現況是綠的」這一個證據，
# 而綠可能只是因為它什麼都沒看見（本 repo 已有三次同型前例）。
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import windows_skip_tags as _wst  # noqa: E402


class TestSkipDirectionAndTagSymmetry(unittest.TestCase):
    """skip 方向判準的四格與雙向標籤（`windows_skip_tags`）。"""

    def _sites(self, src: str) -> list[_wst.SkipSite]:
        return _wst.skip_decorator_sites({"fixture_case.py": src})

    def test_pytest_skipif_form_is_in_scope(self) -> None:
        """🔴 PKG-4 D 的核心：同一個缺陷改寫成 pytest 形態必須仍被看見。

        意圖（Rule 9）：R72 的方向判準只走 `unittest` 的 decorator 且只讀位置引數的
        reason，於是每一個 `@pytest.mark.skipif(cond, reason=...)` 站點在抽取階段就被
        整個丟掉——連「未登記述詞」那道 fail-open 守衛都看不到它。一道只認一種測試
        框架的判準，對「換框架寫同一個缺陷」零防護。
        """
        sites = self._sites(
            "import pytest, sys\n"
            '@pytest.mark.skipif(sys.platform != "win32", reason="需要 Windows")\n'
            "def test_x(): pass\n"
        )
        self.assertEqual(len(sites), 1, sites)
        self.assertEqual(sites[0].decorator, "skipif")
        self.assertEqual(sites[0].reason, "需要 Windows")
        self.assertEqual(
            _wst.skipped_platform(sites[0]), "non-windows",
            "pytest 形態的方向判錯——`skipif(sys.platform != \"win32\")` 是在**非** "
            "Windows 上 skip（Windows 專屬測試）",
        )

    def test_module_level_pytestmark_and_alias_are_in_scope(self) -> None:
        """模組級 `pytestmark` 與「先存成常數再當 decorator」兩種寫法都在射程內。

        意圖：這兩種寫法的**射程比 decorator 大**（前者整檔 skip），漏掉它們等於在
        覆蓋面最大的那一種寫法上失明。本 repo 兩種都真的在用。
        """
        sites = self._sites(
            "import pytest, sys\n"
            'pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX 專屬")\n'
            '_ALIAS = pytest.mark.skipif(sys.platform != "win32", reason="Windows 專屬")\n'
        )
        by_target = {s.target: s for s in sites}
        self.assertEqual(sorted(by_target), ["_ALIAS", "pytestmark"], sites)
        self.assertEqual(_wst.skipped_platform(by_target["pytestmark"]), "windows")
        self.assertEqual(_wst.skipped_platform(by_target["_ALIAS"]), "non-windows")

    def test_direction_table_covers_all_four_cells(self) -> None:
        """四格方向表逐格斷言（極性 × 述詞在 Windows 上的值）。

        意圖：R72 只有一格（`skipUnless` × Windows 述詞），其餘三格靜默判不出方向。
        任何人把某一格拿掉，本支當場紅。
        """
        cases = {
            ('skipIf', 'os.name == "nt"'): "windows",
            ('skipIf', 'os.name != "nt"'): "non-windows",
            ('skipUnless', 'os.name == "nt"'): "non-windows",
            ('skipUnless', 'os.name != "nt"'): "windows",
        }
        for (deco, cond), want in cases.items():
            site = _wst.SkipSite("f.py", 1, "t", deco, cond, "r")
            with self.subTest(deco=deco, cond=cond):
                self.assertEqual(_wst.skipped_platform(site), want)

    def test_negated_predicate_does_not_invert_the_direction(self) -> None:
        """🔴 `not <Windows 述詞>` 不得被判成 Windows 述詞（R74 落地時實測的方向反轉）。

        意圖：兩極模型只問「條件文字裡有沒有 Windows 述詞」，於是
        `skipif(not _windows_pwsh_available())` 被判成「Windows 上會 skip」，而它的
        語意恰恰相反。**方向算反比判不出方向更糟**——它會要求作者貼上錯的標籤。
        """
        site = _wst.SkipSite("f.py", 1, "t", "skipif", "not _windows_pwsh_available()", "r")
        self.assertEqual(_wst.skipped_platform(site), "non-windows")
        self.assertEqual(
            _wst.skipped_platform(
                _wst.SkipSite("f.py", 1, "t", "skipif", "_windows_pwsh_available()", "r")),
            "windows",
        )

    def test_untagged_non_windows_side_is_reported(self) -> None:
        """反方向（POSIX 側）漏標必須被回報，且兩種標籤都算已標籤。"""
        src = (
            "import unittest, os, sys\n"
            '@unittest.skipIf(os.name == "nt", "POSIX 專屬")\n'
            "def test_a(): pass\n"
            f'@unittest.skipIf(os.name == "nt", "{_wst.POSIX_NATIVE_SKIP_TAG} POSIX 專屬")\n'
            "def test_b(): pass\n"
            f'@unittest.skipUnless(sys.platform == "darwin", "{_wst.MAC_NATIVE_SKIP_TAG} mac")\n'
            "def test_c(): pass\n"
        )
        offenders = _wst.untagged_non_windows_skip_decorators({"fixture_case.py": src})
        self.assertEqual(
            [label for label, _ in offenders], ["fixture_case.py:2 test_a"],
            f"反方向漏標判準不對（實得 {offenders!r}）——已帶 POSIX／MAC 標籤者不得再被點名",
        )

    def test_ratchet_flags_both_directions_of_drift(self) -> None:
        """棘輪對「新增未標籤」與「已補標未下修基線」兩向都說話（防基線腐化）。

        意圖：只擋「不得增加」的棘輪會腐化——補完標籤後基線留在舊值，鑑別力靜默歸零
        （`MIN_TESTS` 的註記逐字記載腐化 11 輪的後果）。故判準是**相等**。
        """
        baseline = dict(_wst._POSIX_TAG_RATCHET)
        self.assertEqual(
            _wst.posix_tag_ratchet_problems(baseline), [],
            "基線自己對自己都不相等——表壞了",
        )
        tree = next(iter(baseline))
        worse = {**baseline, tree: baseline[tree] + 1}
        self.assertTrue(_wst.posix_tag_ratchet_problems(worse), "新增未標籤站點沒被擋下")
        # 🔴 R79：「已補標未下修」這一向必須挑一個**基線 > 0** 的樹來扣。原本寫的是
        # `next(iter(baseline))` 再 `max(0, v - 1)`——當第一格剛好是 0 時，扣完等於沒扣，
        # 這半題結構上恆綠。它在 R79 當回合真的發生了：另一個包把 `tools/tests` 由 1
        # 下修為 0（一個正確的動作），這支鎖的鑑別力就在別人還債的那一刻靜默歸零。
        # 判準因此不再依賴「哪一格排第一」這種偶然事實。
        payable = [t for t, v in baseline.items() if v > 0]
        self.assertTrue(
            payable,
            "基線全格為 0 ⇒ 「已補標未下修」這一向無從施測。欠債真的清乾淨是好事，"
            "但這支鎖必須改成別的施測法（例如整格移除），不得留一題恆綠的斷言",
        )
        better = {**baseline, payable[0]: baseline[payable[0]] - 1}
        self.assertTrue(
            _wst.posix_tag_ratchet_problems(better),
            "補標後基線未下修卻放行——棘輪會就地腐化",
        )
        self.assertTrue(
            _wst.posix_tag_ratchet_problems({}), "掃描面整組消失竟放行——fail-open")

    # ══════════════════════════════════════════════════════════════════════════
    # R75：SD 追加①（複合布林方向）＋ QA-R74-02（63 筆對所有機械物隱形）的注入式鎖
    # ══════════════════════════════════════════════════════════════════════════

    def test_composite_boolean_condition_is_evaluated_not_guessed(self) -> None:
        """🔴 SD 追加①：複合布林條件不得以「字串比對挑一個 marker」猜方向。

        意圖（Rule 9）：R74 的判準是「依 marker 長度遞減排序取第一個命中」，於是
        `skipIf(sys.platform == 'win32' or sys.platform == 'darwin')` 取到較長的
        `darwin`（24 字 > 23 字）⇒ 判成 `non-windows`，而它**實際在 Windows 上會 skip**。
        方向算反正是該檔自承「比判不出方向更糟」的形態（它會要求作者貼上錯的標籤）。
        修法是真值運算（`or`／`and`／`not` 逐層求值），故本支逐格斷言真值表——包含
        「一個葉判得出、另一個判不出」的短路情形，那是純字串比對絕對做不到的。
        """
        cases = {
            "sys.platform == 'win32' or sys.platform == 'darwin'": True,
            "sys.platform == 'win32' and sys.platform != 'darwin'": True,
            "not (sys.platform == 'win32' or sys.platform == 'darwin')": False,
            "os.name == 'nt' or _brand_new_probe()": True,       # True or 未知 == True
            "os.name != 'nt' and _brand_new_probe()": False,     # False and 未知 == False
            "_brand_new_probe() or _other()": None,              # 兩葉皆未知 ⇒ 不猜
            "os.name == 'nt' and _brand_new_probe()": None,      # True and 未知 ⇒ 不猜
        }
        for cond, want in cases.items():
            with self.subTest(cond=cond):
                self.assertIs(
                    _wst._predicate_value_on_windows(cond), want,
                    f"{cond!r} 在 Windows 上的值應為 {want}",
                )
        # 端到端：SD 舉的那一筆必須歸到 `posix-only`（Windows 上會 skip），而不是反方向。
        site = _wst.SkipSite(
            "f.py", 1, "t", "skipIf", "sys.platform == 'win32' or sys.platform == 'darwin'", "r")
        self.assertEqual(_wst.skipped_platform(site), "windows")
        self.assertEqual(_wst.site_class(site), "posix-only")

    def test_every_site_lands_in_exactly_one_census_class(self) -> None:
        """🔴 QA-R74-02：每個站點都必須落在某一格 ⇒ 沒有站點能對所有機械物隱形。

        意圖：修前三棵活測試樹共 103 個 decorator 站點、其中 63 筆（61%）方向判不出來，
        而 docstring 宣稱承接它們的收口網對這 63 筆命中 0 ⇒ 兩道方向判準與收口網**全部
        看不到**。本支鎖「分類是全覆蓋的」：站點總數 ＝ 各類別數字之和，且
        `unclassified` 有明細可查。
        """
        src = (
            "import os, shutil, sys, unittest, pytest\n"
            '@unittest.skipUnless(os.name == "nt", "Windows 專屬")\n'
            "def test_a(): pass\n"
            '@unittest.skipIf(os.name == "nt", "POSIX 專屬")\n'
            "def test_b(): pass\n"
            '@unittest.skipUnless(shutil.which("git"), "需 git")\n'
            "def test_c(): pass\n"
            '@unittest.skipUnless(_BASH, "需 bash")\n'
            "def test_d(): pass\n"
            "class T(unittest.TestCase):\n"
            "    def test_e(self):\n"
            '        self.skipTest("函式體內 skip")\n'
        )
        sources = {"fixture_case.py": src}
        counts = _wst.site_class_counts(sources)
        self.assertEqual(
            counts,
            {"windows-only": 1, "posix-only": 1, "tool-absence": 2,
             "runtime-skipTest": 1, "unclassified": 0},
            f"分類全覆蓋性壞了（實得 {counts}）",
        )
        self.assertEqual(
            sum(counts.values()), len(_wst.skip_decorator_sites(sources)),
            "各類別之和 ≠ 站點總數 ⇒ 有站點沒被歸類（那就是隱形）",
        )

    def test_runtime_skiptest_form_is_in_scope(self) -> None:
        """🔴 QA-R74-02 第 3 點：函式體內的 `self.skipTest()` 此前完全在射程外。

        意圖：`_SKIP_CALL_SKIPS_WHEN_TRUE` 只認 decorator，於是「把條件寫在 `if` 裡再
        `self.skipTest(...)`」這種寫法連站點都抽不到（R75 實測 `tools/tests/` 有 10 筆）。
        它們沒有條件引數、方向天生判不出來——但「判不出來」不等於「可以隱形」。
        """
        sites = self._sites(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_x(self):\n"
            "        if not _HAS_TOOL:\n"
            '            self.skipTest("缺工具")\n'
        )
        self.assertEqual(len(sites), 1, sites)
        self.assertEqual(sites[0].decorator, "skipTest")
        self.assertEqual(sites[0].reason, "缺工具")
        self.assertEqual(sites[0].target, "test_x", "必須點名到那支測試")
        self.assertEqual(_wst.site_class(sites[0]), "runtime-skipTest")

    def test_unregistered_predicate_is_judged_per_leaf_not_whole_condition(self) -> None:
        """🔴 逐葉判「未登記」，不看整條條件（R75 落地時實測到假紅）。

        意圖：`os.name == "nt" and _real_pwsh7() is not None` 整條含 `nt` 字樣、整條方向
        判不出來，於是「整條」版判準把它報成「未登記的 Windows 述詞」——可它的兩個葉一個
        已登記、一個根本不像 Windows，**沒有任何述詞需要登記**，訊息給的修法是空的。
        逐葉之後假紅歸零，而真正的漏登記仍抓得到（下半段）。
        """
        self.assertEqual(
            _wst.suspect_unregistered_leaves('os.name == "nt" and _real_pwsh7() is not None'),
            [], "已登記葉 ＋ 非 Windows 葉的組合不得被報成漏登記",
        )
        self.assertEqual(
            _wst.suspect_unregistered_leaves("_brand_new_windows_probe()"),
            ["_brand_new_windows_probe()"], "真正的漏登記必須抓到",
        )
        # 端到端：前者歸 tool-absence（可見、可記帳），後者歸 unclassified（逐筆點名）。
        ok = _wst.SkipSite("f.py", 1, "t", "skipUnless",
                           'os.name == "nt" and _real_pwsh7() is not None', "r")
        bad = _wst.SkipSite("f.py", 2, "t", "skipUnless", "_brand_new_windows_probe()", "r")
        self.assertEqual(_wst.site_class(ok), "tool-absence")
        self.assertEqual(_wst.site_class(bad), "unclassified")

    def test_tree_floor_ratchet_flags_both_shrinkage_and_staleness(self) -> None:
        """🔴 SD 追加②要的**防腐機制**：下限過期本身必須是一筆 problem。

        意圖：下限只擋「縮面」時會單向腐化——樹長大、下限不動，鑑別力靜默歸零而沒有任何
        東西會說話（`MIN_TESTS` 腐化 11 輪就是這麼發生的）。下限的語意既然是「實測的
        八成」，那 `floor < actual × 0.8` 就該紅。
        """
        floors = dict(_wst._TREE_FILE_FLOORS)
        tree, floor = next(iter(floors.items()))
        # 對照組：實測恰為 floor/0.8 ⇒ 合格（下限剛好在設計比例上）。
        exact = int(floor / _wst.TREE_FLOOR_RATIO)
        self.assertEqual(
            _wst.tree_floor_problems({t: int(f / _wst.TREE_FLOOR_RATIO)
                                      for t, f in floors.items()}), [],
            "下限恰在設計比例上竟被判違規",
        )
        self.assertTrue(
            _wst.tree_floor_problems({**floors, tree: floor - 1}),
            "掃描面縮到下限以下沒被擋（原本就該有的那一向）",
        )
        stale = {t: int(f / _wst.TREE_FLOOR_RATIO) for t, f in floors.items()}
        stale[tree] = exact * 3
        problems = _wst.tree_floor_problems(stale)
        self.assertTrue(problems, "樹長大三倍、下限不動竟放行 ⇒ 下限會就地腐化")
        self.assertTrue(
            any("已過期" in p and tree in p for p in problems),
            f"訊息未指出是哪一棵樹的下限過期：{problems}",
        )
        self.assertTrue(_wst.tree_floor_problems({}), "掃描面整組消失竟放行——fail-open")

    def test_census_ratchet_flags_drift_in_both_directions(self) -> None:
        """普查棘輪對「新增」與「收斂後未下修」兩向都說話（同 `_POSIX_TAG_RATCHET` 政策）。"""
        baseline = {t: dict(c) for t, c in _wst._SITE_CLASS_CENSUS.items()}
        self.assertEqual(
            _wst.site_class_census_problems(baseline), [], "基線自己對自己不相等——表壞了")
        tree = next(iter(baseline))
        worse = {**baseline, tree: {**baseline[tree], "unclassified": 1}}
        better = {**baseline, tree: {**baseline[tree],
                                     "tool-absence": baseline[tree]["tool-absence"] - 1}}
        self.assertTrue(_wst.site_class_census_problems(worse), "新增 unclassified 沒被擋")
        self.assertTrue(
            _wst.site_class_census_problems(better), "收斂後未下修基線卻放行——會就地腐化")
        self.assertTrue(_wst.site_class_census_problems({}), "掃描面消失竟放行——fail-open")

    def test_scan_surface_spans_the_live_test_trees(self) -> None:
        """🔴 PKG-4 D 的射程面：判準必須看到全部活測試樹，不是只有一棵。

        意圖：R72 的射程只有 `tools/tests/`（實測 53 支檔），而 repo 活測試檔共 337 支
        ⇒ 84% 不在任何方向判準的射程內。射程若被縮回一棵樹，本支當場紅。
        本輪第四棵＝LATEST 版 `tools/fsm_runtime/tests`（此前整棵零覆蓋，該樹的 4 個
        skip 站點對所有機械物隱形）；版本目錄名以「LATEST」正規化，升版不失效。
        """
        latest_name = _latest_root().name
        trees = _wst.scan_tree_sources(_REPO_ROOT, _TESTS_DIR, "test_*.py")
        self.assertEqual(
            sorted(t.replace(latest_name, "LATEST") for t in trees),
            ["AISDLC_SDD/LATEST/tools/fsm_runtime/tests",
             "AISDLC_SDD/scripts/tests", "AutoClaude/tests", "tools/tests"],
            f"掃描面的樹清單不對（實得 {sorted(trees)}）",
        )
        for tree, sources in trees.items():
            floor = _wst._TREE_FILE_FLOORS[tree]
            self.assertGreaterEqual(
                len(sources), floor,
                f"{tree} 掃到 {len(sources)} 支 < 下限 {floor}——該樹掃描面疑似縮小",
            )


# ══════════════════════════════════════════════════════════════════════════════
# R76 — 第七道判準：文字讀寫必須指名 encoding（PKG-E 標的三；R76-09）
# ══════════════════════════════════════════════════════════════════════════════
# WHY 全文（缺陷本體／判準設計／誠實劃界／標記命名理由）搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R76 文字編碼判準 WHY〉節。
_ENCODING_OK_MARKER = "file-encoding-ok:"
#: 標記比對的邊界（前面不得是字母／數字／連字號）：與姊妹檔 `_marker_lines` 同一條，
#: 讓「某標記內含另一標記」這種形態不會被互相認領。`TestEncodingMarkersDoNotCollide`
#: 常駐守著編碼家族三個豁免標記彼此不認領。
#: 🔴 本區塊的註解**刻意不逐字寫出任何一個編碼家族標記字串**（連姊妹檔的也不行）：
#:   `#` 註解是 COMMENT token，兩支掃描器的取標記函式都只認 COMMENT ⇒ 在註解裡「提到」
#:   一個標記，與「登記」一個標記在機器眼中完全同形，當場多一筆 `標記 stale` 紅。
#:   R76 首版修法就是這樣把姊妹檔弄紅的（本檔 :2047 上方已為自家標記寫過同一條理由，
#:   卻只戒了自己那一個字串）。要引述標記字串，寫進 docstring／字串字面值（STRING token）。
_ENCODING_MARKER_RE = re.compile(r"(?<![\w-])" + re.escape(_ENCODING_OK_MARKER))
_TEXT_RW_ATTRS = frozenset({"read_text", "write_text"})
#: encoding 的**位置引數**索引（呼叫形態 → 索引）。四種形態的簽名各不相同：
#: `open(file, mode, buffering, encoding)`／`Path.open(mode, buffering, encoding)`／
#: `Path.read_text(encoding, errors)`／`Path.write_text(data, encoding, errors)`。
_ENC_POS = {"open": 3, "path_open": 2, "read_text": 0, "write_text": 1}
#: mode 的位置引數索引（只有兩種 open 形態有 mode）。
_MODE_POS = {"open": 1, "path_open": 0}
_NON_TEXT_OPEN_OWNERS = frozenset({
    "os", "gzip", "bz2", "lzma", "tarfile", "zipfile", "socket", "webbrowser",
    "shelve", "dbm", "sqlite3",
})


def _encoding_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——行尾豁免標記（只認 COMMENT token，理由同 `_pathext_markers`）。

    本判準的射程含偵測器自己，而偵測器原始碼必然多處逐字提到標記字串（常數、docstring、
    測試訊息）。純文字掃描會把那些提及都當成真標記並判 stale ⇒ 鎖因為「說明自己」而翻紅。
    """
    markers: dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type != tokenize.COMMENT:
                continue
            found = _ENCODING_MARKER_RE.search(tok.string)
            if found:
                markers[tok.start[0]] = tok.string[found.end():].strip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        markers.clear()          # 壞檔退回空集合；掃描面本身不縮小（下方 ast.parse 亦會失敗）
    return markers


def _call_kind(call: ast.Call) -> str | None:
    """呼叫形態分類；不在射程內回 None。"""
    f = call.func
    if isinstance(f, ast.Name):
        return "open" if f.id == "open" else None
    if not isinstance(f, ast.Attribute):
        return None
    if f.attr in _TEXT_RW_ATTRS:
        return f.attr
    if f.attr != "open":
        return None
    owner = f.value
    name = owner.id if isinstance(owner, ast.Name) else (
        owner.attr if isinstance(owner, ast.Attribute) else "")
    return None if name in _NON_TEXT_OPEN_OWNERS else "path_open"


def _binary_or_unknown_mode(call: ast.Call, kind: str) -> bool:
    """mode 帶 `b`（二進位）或 mode 是非字面值（判不出來）⇒ 出射程。"""
    pos = _MODE_POS.get(kind)
    if pos is None:
        return False                       # read_text/write_text 恆為文字
    mode: ast.AST | None = None
    if len(call.args) > pos:
        mode = call.args[pos]
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = kw.value
    if mode is None:
        return False                       # 省略 mode ＝ 預設 "r" ＝ 文字
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return "b" in mode.value
    return True                            # 非字面值：見上方劃界，刻意出射程


def _declares_encoding(call: ast.Call, kind: str) -> bool:
    if any(kw.arg == "encoding" for kw in call.keywords):
        return True
    if any(kw.arg is None for kw in call.keywords):
        return True                        # `**kwargs` 轉發：判不出來，見劃界
    return len(call.args) > _ENC_POS[kind]


def scan_missing_encoding(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    markers = _encoding_markers(source)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], []
    offenders: list[str] = []
    used: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kind = _call_kind(node)
        if kind is None or _binary_or_unknown_mode(node, kind) or _declares_encoding(node, kind):
            continue
        # `used` 記在「這一行確實有違規」之後（同第五道判準的 WHY）：stale 的語意是
        # 「標記在、但這一行根本沒有要壓下的東西」。
        if markers.get(node.lineno):
            used.add(node.lineno)
            continue
        shown = "open()" if kind in ("open", "path_open") else f".{kind}()"
        offenders.append(
            f"{rel}:{node.lineno}: {shown} 未指名 encoding ⇒ 用本機 locale 預設編碼"
            "（mac=UTF-8 恆綠／zh-TW Windows=cp950，讀到非 Big5 字元即 UnicodeDecodeError）"
        )
    stale = [
        f"{rel}:{lineno}: {_ENCODING_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return offenders, stale


def _encoding_scan_files() -> list[Path]:
    """射程＝本檔共用的 `_scan_units()`（測試樹 ＋ 生產碼樹 ＋ 零散單檔）。

    刻意**共用**同一組掃描單位而不另列一份：兩份清單就是兩個會漂移的真相，而
    `_scan_units()` 已有逐單位檔數的雙邊帶在守「靜默縮面」與「下限自己過期」。
    """
    out: list[Path] = []
    for _label, files, _floor in _scan_units():
        out.extend(files)
    return sorted(set(out))


#: 🔴 **shrink-only 存量棘輪 — 承接輪次＝下一輪**（帳本 `DEF-101-845`；此處刻意**不寫死輪號**
#: ——寫死會在下一輪開始時當場過期，而且會被 `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`
#: 判成「程式碼自稱的輪號超前帳本當前輪」。落地當下的所有權只到本檔＋另四支，
#: 下列每一支都在別的包手上，當輪修改必然互踩）。語意與 `_POSIX_TAG_RATCHET` 同族：
#:   · 任何一支的違規數**變多**、或出現不在表上的檔 ⇒ 紅（新缺陷不得混進存量）。
#:   · 任何一支**變少**（含修光）⇒ 也紅，訊息會指名要把本表下修——**只准往下改**。
#: 這不是「凍結成永遠綠」：兩個方向都會響，而且表一空掉這道鎖就升級為零容忍。
#: 承接動作：逐支補 `encoding="utf-8"`（讀 `.md`／log 一律 UTF-8），每修好一支就把
#: 該列從本表刪掉；全部清空後把本表留成空 dict（空 dict ＝ 零容忍，不要連常數一起刪）。
#: 🔴 **本表釘的是「每支檔幾筆」而不是行號**：R76 落地當回合實測，並行包在 `test_perception.py`
#: 上游插了幾行、違規行號由 434 漂到 437 而筆數不變——釘行號的表會在別人動別的東西時假紅。
#: 🔴 **收輪時看到本鎖紅、訊息說「請把棘輪同步下修」＝正常且正確**（不是本包留下的破口）：
#: R76 是多包並行輪，別的包順手補了 `encoding=` 就會讓某一列變小（落地當回合就發生過一次：
#: `tools/tests/test_doc_loc_baseline_freshness_r60.py` 由 1 → 0，該列已據實移除）。照訊息
#: 印出的實得值下修即可，**不要**改成 `<=` 之類的單邊判準——那正是「凍結成永遠綠」的入口。
_ENCODING_DEBT_RATCHET: dict[str, int] = {
    "AutoClaude/tests/test_evaluator_kill_tree.py": 2,
    "AutoClaude/tests/test_perception.py": 4,
    "AutoClaude/tests/tools/test_run_act_core.py": 3,
}


class TestTextIoDeclaresEncoding(unittest.TestCase):
    """文字讀寫必須指名 encoding（見上方區段 WHY）。"""

    @staticmethod
    def _scan_repo() -> tuple[dict[str, int], list[str], list[str], int]:
        per_file: dict[str, int] = {}
        stale: list[str] = []
        detail: list[str] = []
        scanned = 0
        for path in _encoding_scan_files():
            rel = path.relative_to(_REPO_ROOT).as_posix()
            off, st = scan_missing_encoding(
                path.read_text(encoding="utf-8-sig", errors="replace"), rel)
            if off:
                per_file[rel] = len(off)
                detail.extend(off)
            stale.extend(st)
            scanned += 1
        return per_file, stale, detail, scanned

    def test_debt_ratchet_is_exact_and_shrink_only(self) -> None:
        per_file, stale, detail, scanned = self._scan_repo()
        # 反空轉下限＝落地當回合實測 × 0.95（本輪由「打八折的化石 648」重釘），
        # 並套與各掃描單位同一條腐化上界——單邊下限必然腐化，見 `_scan_roots` WHY。
        surface = tree_count_verdict("encoding 掃描面", scanned, 812)
        self.assertIsNone(surface, surface or "")
        self.assertEqual(
            stale, [],
            f"{_ENCODING_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale))
        grew = {
            rel: (n, _ENCODING_DEBT_RATCHET.get(rel, 0))
            for rel, n in sorted(per_file.items())
            if n > _ENCODING_DEBT_RATCHET.get(rel, 0)
        }
        self.assertEqual(
            grew, {},
            "新增（或增加）未指名 encoding 的文字讀寫——**不得調高棘輪**，請補上 "
            f"`encoding=\"utf-8\"`，或於該行行尾加標記（`{_ENCODING_OK_MARKER}` ＋ WHY）：\n"
            + "\n".join(detail),
        )
        shrank = {
            rel: (per_file.get(rel, 0), frozen)
            for rel, frozen in sorted(_ENCODING_DEBT_RATCHET.items())
            if per_file.get(rel, 0) < frozen
        }
        self.assertEqual(
            shrank, {},
            "存量已被修掉（實得, 棘輪）如上 ⇒ 請把 `_ENCODING_DEBT_RATCHET` 同步下修。"
            "棘輪只准往下改；不下修的話下一次退化會被舊值遮住",
        )

    # ── 以下以合成樣本自證判準紅綠（樣本只存在於字串，不留違規樣本於 repo）──

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_missing_encoding(source, "fixture_case")

    def test_injected_missing_encoding_shapes_are_detected(self) -> None:
        """三種文字 I/O 形態各自漏 encoding 都必紅。"""
        for sample in (
            "text = path.read_text()\n",
            'path.write_text("x")\n',
            'with open(path) as fh:\n    pass\n',
            'with path.open("w") as fh:\n    pass\n',
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertEqual(len(off), 1, f"{sample!r} 漏抓：{off}")

    def test_declared_encoding_is_accepted(self) -> None:
        """修法慣例必綠——否則本鎖會逼人改回舊寫法。關鍵字與位置引數兩種都要接受。"""
        for sample in (
            'text = path.read_text(encoding="utf-8")\n',
            'text = path.read_text("utf-8")\n',
            'path.write_text("x", encoding="utf-8")\n',
            'path.write_text("x", "utf-8")\n',
            'with open(path, "r", encoding="utf-8") as fh:\n    pass\n',
            'with path.open("w", encoding="utf-8") as fh:\n    pass\n',
            "def wrap(p, **kw):\n    return p.read_text(**kw)\n",
        ):
            with self.subTest(sample=sample):
                off, stale = self._scan(sample)
                self.assertEqual((off, stale), ([], []), f"{sample!r} 誤報")

    def test_binary_and_non_pathlib_open_are_out_of_scope(self) -> None:
        """對照組：二進位模式與 `os.open` 等非文字 I/O 不得誤報（假紅會逼人關掉整條鎖）。"""
        for sample in (
            'with path.open("rb") as fh:\n    pass\n',
            'with open(path, "wb") as fh:\n    pass\n',
            'fd = os.open(path, os.O_RDONLY)\n',
            'with gzip.open(path) as fh:\n    pass\n',
            "data = path.read_bytes()\n",
            "path.write_bytes(b'x')\n",
            "with open(path, mode_var) as fh:\n    pass\n",
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertEqual(off, [], f"{sample!r} 誤報：{off}")

    def test_marker_suppresses_and_missing_violation_makes_it_stale(self) -> None:
        """豁免標記能壓下違規；標記在、違規不在（或 WHY 留空）→ stale 必紅。"""
        off, stale = self._scan(
            f'text = path.read_text()  # {_ENCODING_OK_MARKER} 讀的是自己剛寫的純 ASCII\n')
        self.assertEqual((off, stale), ([], []))

        off, stale = self._scan(f"text = path.read_text()  # {_ENCODING_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")
        self.assertEqual(len(stale), 1, stale)

        off, stale = self._scan(f"x = 1  # {_ENCODING_OK_MARKER} 已補上 encoding\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")

    def test_marker_inside_a_string_literal_is_not_honoured(self) -> None:
        """字串裡出現標記字樣不算豁免（否則寫一句說明就能買到免檢）。"""
        off, _ = self._scan(
            f'MSG = "{_ENCODING_OK_MARKER} 說明文字"\ntext = path.read_text()\n')
        self.assertEqual(len(off), 1, off)

    def test_detector_catches_the_pre_fix_form_of_a_real_file(self) -> None:
        """自我驗證（最重要的一支）：對**真實檔案的修復前形態**必須紅。

        沿用本檔慣例——不查 git（綁 HEAD 會在修復 commit 後反過來變紅），而是把現行真檔
        的 `encoding=` 拿掉再餵給判準；現行真檔同時必須乾淨，兩個方向一起鎖。
        取樣 `tools/check_gha_action_versions.py`＝R76-09 點名的代表站點。
        """
        rel = "tools/check_gha_action_versions.py"
        src = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        fixed_form = 'path.read_text(encoding="utf-8")'
        self.assertIn(
            fixed_form, src,
            f"{rel} 內找不到 `{fixed_form}` ⇒ 本自證失去對象——該處若被重寫，請同步更新"
            "這支測試指向新的取樣站點，不要直接刪掉自證",
        )
        pre_fix = src.replace(fixed_form, "path.read_text()")
        off, _ = scan_missing_encoding(pre_fix, f"{rel}@修復前重建")
        self.assertTrue(off, f"本鎖對 {rel} 修復前的形態抓不到 ⇒ 判準空轉")
        off_now, stale_now = scan_missing_encoding(src, rel)
        self.assertEqual((off_now, stale_now), ([], []), f"{rel} 現行必須已無此病灶")


# ══════════════════════════════════════════════════════════════════════════════
# R76 複審 ARCH-01：豁免標記**不得跨判準互相認領**（本輪自造死結的根治面）
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體與判準全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R76 複審 ARCH-01 標記互斥 WHY〉節。
#: 豁免標記常數的形態：模組層 `_XXX = "<slug>-ok:"`。
_MARKER_CONST_RE = re.compile(
    r'^(_[A-Z0-9_]+)\s*(?::\s*str\s*)?=\s*"([a-z0-9][a-z0-9-]*-ok:)"\s*$', re.MULTILINE)


def collect_exemption_markers() -> dict[str, set[str]]:
    """{標記字串: {"<檔名>::<常數名>", …}}——現查 `tools/tests/*.py` 的所有豁免標記。

    現查而非寫死清單：寫死的在「新增一支掃描器」那天靜默縮面，而那正是本鎖要防的事。
    """
    found: dict[str, set[str]] = {}
    for path in sorted((_REPO_ROOT / "tools" / "tests").glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for const, value in _MARKER_CONST_RE.findall(text):
            found.setdefault(value, set()).add(f"{path.name}::{const}")
    return found


class TestEncodingMarkersDoNotCollide(unittest.TestCase):
    """豁免標記彼此不得互相認領（跨判準、跨檔）。"""

    def test_no_two_files_share_the_same_marker_string(self) -> None:
        """判準是**跨檔**共用，不是「任何共用」——這條界線是實測收斂出來的。

        `test_adr_xplat001_c1c2_lock.py` 的 SC-4／SC-9 **刻意**共用同一個
        `stale-premise-ok:`（該檔 `sc9_…` 的 docstring 逐字寫「豁免沿用 SC-4 的…」，
        且死信偵測的 `consumed` 集合把它算成同一個），那是**同一位擁有者**在同一份檔裡
        自己看得到的設計；把它判紅只會是自製誤報。真正會出事的是**跨檔**：兩支互不知情
        的掃描器各有一套 stale 偵測，其中一方的合法豁免就是另一方的紅——ARCH-01 那筆
        逃出去的縫正是這一格。

        誠實劃界：同檔內共用仍可能出錯（若該檔沒把 stale 偵測接起來），本條抓不到。
        """
        markers = collect_exemption_markers()
        self.assertGreaterEqual(
            len(markers), 10,
            f"只掃到 {len(markers)} 個豁免標記常數 ⇒ 射程疑似被縮小（形態改了？）")
        shared = {
            value: sorted(sites)
            for value, sites in sorted(markers.items())
            if len({s.split("::")[0] for s in sites}) > 1
        }
        self.assertEqual(
            shared, {},
            "以下豁免標記字串被 ≥2 **支檔**的判準共用 ⇒ 其中一方的**合法**豁免會在另一方"
            "變成一筆 `標記 stale` 紅（訊息還會說「該行無被壓下的違規」，對那一行是誤導）。"
            "處置：給每道判準取專屬主題名，比照 `pathext-ok:`／`tmpdir-ok:`：\n"
            f"{shared}",
        )

    @staticmethod
    def _claims(owner: str, other: str) -> bool:
        """`owner` 的邊界正則會不會把一行合法的 `other` 豁免認領走。"""
        pattern = re.compile(r"(?<![\w-])" + re.escape(owner))
        return pattern.search(f"# {other} 某個合法 WHY") is not None

    def test_markers_do_not_claim_each_other_under_the_boundary_regex(self) -> None:
        """縱深防禦：即使字串不同，含包關係也不得讓一個標記被兩個判準認領。

        判準沿用兩支掃描器實際在用的那條邊界正則；本測試對**全庫每一對**標記檢查，
        不是只驗手上這幾個（那正是姊妹檔那支鎖的射程缺口）。

        🔴 先自證判準有鑑別力再掃 repo：現行標記形態（`<slug>-ok:`，尾端有冒號）結構上
        不可能互為前綴，所以 repo 掃描那一半**今天必然全過**。只斷言「全過」的鎖看起來
        跟一個壞掉的鎖一模一樣——故先餵一對真的會互相認領的合成標記，確認它會抓到。
        """
        self.assertTrue(
            self._claims("tmpdir-ok:", "tmpdir-ok:extra"),
            "判準對一對明顯互相認領的標記都抓不到 ⇒ 下面那半是恆真的假綠")
        self.assertFalse(
            self._claims("encoding-ok:", "child-encoding-ok:"),
            "判準把既有的合法含包關係誤判成認領 ⇒ 會對現況製造假紅")
        markers = sorted(collect_exemption_markers())
        for owner in markers:
            for other in markers:
                if other == owner:
                    continue
                with self.subTest(owner=owner, other=other):
                    self.assertFalse(
                        self._claims(owner, other),
                        f"`{owner}` 的判準會把一行合法的 `{other}` 豁免認領走 ⇒ 跨鎖假紅",
                    )

    def test_the_three_encoding_family_markers_are_mutually_exclusive(self) -> None:
        """具名回歸（ARCH-01 的原案）：三個 `*encoding-ok:` 逐一互不認領。

        直接用**本檔真正在跑的**取標記函式，不是另寫一份等價實作——後者只會證明
        我重寫的那份是對的。
        """
        subprocess_marker, child_marker = "encoding-ok:", "child-encoding-ok:"
        self.assertNotEqual(
            _ENCODING_OK_MARKER, subprocess_marker,
            "file-IO 判準與 subprocess 判準一的標記又撞回同一字串")
        for foreign in (subprocess_marker, child_marker):
            with self.subTest(foreign=foreign):
                self.assertEqual(
                    _encoding_markers(f"x = 1  # {foreign} 走系統碼頁\n"), {},
                    f"本判準把 `{foreign}` 的合法豁免認領走了")


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 — 掃描面對稱鎖 ＋ 下限雙邊帶自證（缺陷本體見 `_scan_roots()` 的 ① ②）
# ══════════════════════════════════════════════════════════════════════════════
class TestScanSurfaceParityWithSisterLock(unittest.TestCase):
    """本檔與姊妹鎖的掃描面必須逐檔對得起來（擴一邊沒擴另一邊即紅）。

    WHY 這道鎖非有不可：兩支鎖各自維護一份樹清單，而「擴掃描面」是一個**逐鎖**
    發生的動作。本輪實測到的落差是 44 支 active `.py`，且缺口正好蓋住整層 hook
    ——沒有任何機械物會在落差出現的當回合說話，兩份清單只會愈走愈遠。
    判準取**集合相等**而非「本檔 ⊇ 姊妹鎖」：後者允許本檔單向長大，於是下一次
    輪到姊妹鎖漏掉東西時同樣沒人說話（單邊判準必然腐化，與下限那筆同型）。
    """

    @staticmethod
    def _sister_files() -> set[Path]:
        files: set[Path] = set()
        for root, _floor in _sister._scan_roots():
            if not root.is_dir():
                continue
            files.update(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
        files.update(p for p in _sister._scan_single_files() if p.is_file())
        return files

    def _own_files(self) -> set[Path]:
        return {p for _label, files, _floor in _scan_units() for p in files}

    def test_the_two_locks_see_exactly_the_same_python_files(self) -> None:
        mine, sister = self._own_files(), self._sister_files()
        only_sister = sorted(p.relative_to(_REPO_ROOT).as_posix() for p in sister - mine)
        only_mine = sorted(p.relative_to(_REPO_ROOT).as_posix() for p in mine - sister)
        self.assertEqual(
            (only_sister, only_mine), ([], []),
            "兩支姊妹平台鎖的掃描面已分岔——只有一邊看得到的檔就是「同一種缺陷換棵樹"
            "寫就免費過關」的那個縫。修法＝把缺的樹補進 `_scan_roots()`／"
            "`_scan_single_files()`（兩邊都要），不要縮小另一邊來湊相等。\n"
            f"只有姊妹鎖看得到：{only_sister}\n只有本檔看得到：{only_mine}",
        )

    def test_the_surface_is_not_trivially_small(self) -> None:
        """反空轉：兩邊同時崩塌成空集合時「相等」也會成立，故另釘絕對量。"""
        verdict = tree_count_verdict("兩鎖共同掃描面", len(self._own_files()), 812)
        self.assertIsNone(verdict, verdict or "")


class TestScanRootFloorBand(unittest.TestCase):
    """下限帶的紅綠自證（雙向）＋ 每個釘下去的下限都必須對當下實測成立。"""

    def test_the_band_is_red_in_both_directions(self) -> None:
        """人為**壓低**實測值與**抬高**實測值，兩個方向都必須轉紅。

        單邊下限只在往下掉時說話——這正是本輪立案的形態（實測 `tools/tests`
        floor=10／actual=56 ⇒ 可靜默蒸發 82% 掃描面而全綠）。
        """
        floor = 53
        shrink = floor_band_problems([("tools/tests", 10, floor)])
        self.assertEqual(len(shrink), 1, "壓低實測值竟未轉紅 ⇒ 下界那一半沒有牙")
        self.assertIn("疑似縮小", shrink[0])
        rot = floor_band_problems([("tools/tests", repin_ceiling(floor) + 1, floor)])
        self.assertEqual(len(rot), 1, "抬高實測值竟未轉紅 ⇒ 上界那一半沒有牙")
        self.assertIn("腐化上界", rot[0])
        self.assertIn(str(suggested_floor(repin_ceiling(floor) + 1)), rot[0],
                      "訊息必須直接給出該重釘的數字，否則「該重釘」只是一句期許")
        inside = floor_band_problems([
            ("tools/tests", floor, floor),
            ("tools/tests", repin_ceiling(floor), floor),
            ("tools/tests", 56, floor),
        ])
        self.assertEqual(inside, [], f"帶內組合被誤判為紅：{inside}")

    def test_every_pinned_floor_is_inside_its_own_band_right_now(self) -> None:
        """設定面複本：即使正職判準因別的原因沒跑，下限本身仍被量。"""
        counts = [(label, len(files), floor) for label, files, floor in _scan_units()]
        problems = floor_band_problems(counts)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_tmpdir_floors_are_inside_their_band_too(self) -> None:
        """第二道判準的掃描根用的是另一份清單，同樣受雙邊帶管轄。"""
        counts = []
        for root, recursive, floor in _tmpdir_scan_roots():
            found = root.rglob("*.py") if recursive else root.glob("*.py")
            n = len([p for p in found if "__pycache__" not in p.parts])
            counts.append((root.relative_to(_REPO_ROOT).as_posix(), n, floor))
        problems = floor_band_problems(counts)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_single_file_unit_is_pinned_by_name(self) -> None:
        """零散單檔清單釘選：刪一列即該檔靜默出界（同樹清單防護語意）。"""
        latest_name = _latest_root().name
        rels = {
            f.relative_to(_REPO_ROOT).as_posix().replace(latest_name, "LATEST")
            for f in _scan_single_files()
        }
        self.assertEqual(
            rels,
            {"AISDLC_SDD/conftest.py", "AISDLC_SDD/LATEST/tools/__init__.py"},
        )
        self.assertEqual(_SINGLE_FILE_FLOOR, len(_scan_single_files()),
                         "單檔下限與清單長度脫鉤 ⇒ 刪一列不會紅")


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 — 第六道判準：對面平台專屬 API 必須帶平台守衛
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體與判準設計全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈第六道判準（平台專屬 API
# 守衛）WHY〉節。
_XPLAT_OK_MARKER = "xplat-ok:"
#: POSIX 專屬模組（Windows 上 import 即 ModuleNotFoundError）。
_POSIX_ONLY_MODULES = frozenset({"pwd", "grp", "fcntl", "termios", "resource"})
#: Windows 專屬模組（POSIX 上 import 即 ModuleNotFoundError）。
_WINDOWS_ONLY_MODULES = frozenset({"winreg", "msvcrt", "_winapi"})
#: `os.<名字>`：POSIX 專屬（Windows 上該屬性不存在）。
_POSIX_ONLY_OS_ATTRS = frozenset({
    "fork", "forkpty", "killpg", "getuid", "geteuid", "getgid", "getegid",
    "getlogin", "setsid", "chown", "uname", "getpgid", "symlink",
})
#: `os.<名字>`：Windows 專屬。
_WINDOWS_ONLY_OS_ATTRS = frozenset({"startfile", "O_BINARY", "O_NOINHERIT"})
#: `signal.<名字>`：POSIX 專屬訊號**與函式**。
#: 🔴 R81（XPL-S1-05）由 5 個擴到現值：舊表只有 `SIGKILL/SIGUSR1/SIGUSR2/SIGHUP/SIGQUIT`，
#: 而 POSIX 訊號家族約 20 個，缺的正好包含最常被誤用的 `SIGALRM`／`signal.alarm`（Windows
#: 兩者皆無）與 `SIGPIPE`（本 repo 自己有一支 `test_pre_commit_dispatcher_sigpipe.py`
#: 在處理這個主題）。**函式名一起收**：`alarm`／`setitimer` 這些在 Windows 上同樣不存在，
#: 而舊表只收常數 ⇒ 「`hasattr(signal, "SIGALRM")` 探測過、卻用 `signal.alarm()`」這個
#: 最常見的正確寫法與最常見的錯誤寫法，在舊判準眼中長得一模一樣（都不在表上）。
_POSIX_ONLY_SIGNALS = frozenset({
    "SIGKILL", "SIGUSR1", "SIGUSR2", "SIGHUP", "SIGQUIT",
    "SIGALRM", "SIGPIPE", "SIGCHLD", "SIGCONT", "SIGSTOP", "SIGTSTP",
    "SIGWINCH", "SIGBUS", "SIGTRAP", "SIGPROF", "SIGVTALRM", "SIGXCPU", "SIGXFSZ",
    "alarm", "setitimer", "getitimer", "pthread_kill", "sigwait", "pause",
    "siginterrupt", "sigtimedwait", "sigpending",
})
#: `signal.<名字>`：Windows 專屬（POSIX 上不存在 ⇒ AttributeError）。
_WINDOWS_ONLY_SIGNALS = frozenset({"CTRL_C_EVENT", "CTRL_BREAK_EVENT"})
#: `ctypes.<名字>`：Windows 專屬（macOS/Linux 的 `ctypes` 上這些屬性根本不存在）。
#: 🔴 R81（XPL-S1-04）：舊判準把 owner 寫成 `owner == "os"` / `owner == "signal"` 兩個
#: 字串逐一列舉，代價是**新增一個 owner 就整片失明，而且失明是靜默的**——掃描器照跑、
#: 照綠、照回報命中數，只是那一族從來不在分母裡。實測反證：合成片段裡 3 個
#: `ctypes.windll` 餵給 `_foreign_api_uses()` 回傳的是空的，同一支對 `os.startfile`
#: 卻正常命中 ⇒ 掃描器本身沒壞，是詞彙表缺這一族。
_WINDOWS_ONLY_CTYPES_ATTRS = frozenset({
    "windll", "oledll", "WinDLL", "OleDLL", "WINFUNCTYPE", "WinError",
    "FormatError", "GetLastError", "get_last_error", "set_last_error",
})
#: `subprocess.<名字>`：Windows 專屬旗標／結構（POSIX 上不存在）。
#: 🔴 R81（XPL-S1-03）**這一族才是 `creationflags=`／`startupinfo=` 真正的危害面**。
#: 那兩個 kwarg 本身不是危害——`Popen` 只在**值為真**時才 raise，而 repo 現行 11 個
#: `creationflags=` 站點一律傳 `NO_WINDOW`（`getattr(subprocess, "CREATE_NO_WINDOW", 0)`
#: 兜底，POSIX 取 0＝不觸發 raise）＝**正解**。把 kwarg 本身判成違規會讓那 11 個正確
#: 站點當場全紅，而假紅會逼下一輪把整條鎖關掉（同本檔第五道判準的取捨）。
#: 真正「Windows 上寫得出來、mac 上必炸」的形態是**直接取用這些常數**
#: （`creationflags=subprocess.CREATE_NO_WINDOW` ⇒ POSIX 上 AttributeError），
#: 落地當回合實測存量 **0 站點** ⇒ 這一格立的是門，不是清存量（同〈鐵律三〉表上
#: `Get-Command` 解析那一列已被接受的形狀）。
_WINDOWS_ONLY_SUBPROCESS_ATTRS = frozenset({
    "CREATE_NEW_CONSOLE", "CREATE_NEW_PROCESS_GROUP", "CREATE_NO_WINDOW",
    "CREATE_BREAKAWAY_FROM_JOB", "CREATE_DEFAULT_ERROR_MODE", "DETACHED_PROCESS",
    "STARTUPINFO", "STARTF_USESHOWWINDOW", "STARTF_USESTDHANDLES",
    "ABOVE_NORMAL_PRIORITY_CLASS", "BELOW_NORMAL_PRIORITY_CLASS",
    "HIGH_PRIORITY_CLASS", "IDLE_PRIORITY_CLASS", "NORMAL_PRIORITY_CLASS",
    "REALTIME_PRIORITY_CLASS", "SW_HIDE",
})
#: **表驅動的 owner 判準**（R81 XPL-S1-04）：`{owner: {attr: 方向}}`。
#: 新增一族＝在這裡多一列，不必再去改 `_foreign_api_uses()` 的 if-elif 鏈——而那條鏈
#: 正是「漏一族沒人知道」的結構性成因。表的**規模**另有後設鎖看守（見
#: `TestForeignApiVocabularyOnlyGrows`：owner 數與 attr 數只准上升）。
_FOREIGN_ATTR_TABLE: dict[str, dict[str, str]] = {
    "os": {
        **{attr: "POSIX-only" for attr in _POSIX_ONLY_OS_ATTRS},
        **{attr: "Windows-only" for attr in _WINDOWS_ONLY_OS_ATTRS},
    },
    "signal": {
        **{attr: "POSIX-only" for attr in _POSIX_ONLY_SIGNALS},
        **{attr: "Windows-only" for attr in _WINDOWS_ONLY_SIGNALS},
    },
    "ctypes": {attr: "Windows-only" for attr in _WINDOWS_ONLY_CTYPES_ATTRS},
    "subprocess": {attr: "Windows-only" for attr in _WINDOWS_ONLY_SUBPROCESS_ATTRS},
}
#: 只在 Windows 支援的 `Popen` kwarg。**值為 0／None 時 `Popen` 不 raise**，故判準只認
#: 「靜態就看得出非零」的字面值（見 `_WINDOWS_ONLY_SUBPROCESS_ATTRS` 的 WHY）。
_WINDOWS_ONLY_POPEN_KWARGS = frozenset({"creationflags", "startupinfo"})


def _xplat_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——只認 COMMENT token（字串內同形文字不得當豁免用）。"""
    markers: dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT and _XPLAT_OK_MARKER in tok.string:
                markers[tok.start[0]] = tok.string.split(_XPLAT_OK_MARKER, 1)[1].strip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        markers.clear()
    return markers


def _statically_nonzero(value: ast.AST) -> bool:
    """這個運算式**靜態就看得出**在任何平台都非零／非 None 嗎？

    只認字面值（`ast.Constant`）。刻意不做名稱追蹤：`creationflags=NO_WINDOW` 這種
    模組常數的值住在別的檔（`getattr(subprocess, "CREATE_NO_WINDOW", 0)`），跨檔解析
    是另一個量級的工程，而漏判的代價只是「少抓一種」，誤判的代價是 11 筆假紅。
    真正會炸的直接寫法（`creationflags=subprocess.CREATE_NO_WINDOW`）由
    `_WINDOWS_ONLY_SUBPROCESS_ATTRS` 那一族從**屬性取用**那一側抓，不重複判。
    """
    return isinstance(value, ast.Constant) and bool(value.value)


def _capability_flag_names(tree: ast.AST) -> set[str]:
    """被 `hasattr(...)` 的結果綁定過的變數名（`has_alarm = hasattr(signal, "SIGALRM")`）。

    🔴 R81（XPL-S1-05 的配套）：擴充訊號詞彙表之後，LATEST 框架版兩支 hook 的
    `signal.alarm(...)` 會冒出 4 筆違規——而那 4 個站點**寫得是對的**：
    `has_alarm = hasattr(signal, "SIGALRM")` ➜ `if has_alarm:` ➜ POSIX 路徑，`else:`
    走 ThreadPoolExecutor。既有的 `_capability_probed()` 只赦免「被探測的**那個名字**」
    （SIGALRM），赦免不到同一族的兄弟函式（alarm）；既有的四種守衛也罩不住，因為
    `has_alarm` 不是平台判定符號。⇒ 不補這一條就是拿 4 筆假紅去換一道新門，而假紅
    會逼下一輪把整條鎖關掉。這一條認的是**真實且正確的既存寫法**，不是為了通過而放水。
    """
    flags: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                and value.func.id == "hasattr"):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                flags.add(target.id)
    return flags


def _capability_probed(tree: ast.AST) -> set[str]:
    """`hasattr(<任何東西>, "<名字>")` 探測過的名字＝作者已明示這是可選能力。"""
    probed: set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "hasattr" and len(node.args) == 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)):
            probed.add(node.args[1].value)
    return probed


def _foreign_api_uses(
    tree: ast.AST, probed: set[str]
) -> list[tuple[ast.AST, int, str, str]]:
    """(節點, 行號, 方向, 說明)——AST 上所有單平台專屬 symbol 的使用點。

    🔴 R79：回傳**節點本體**而不只行號。站點級守衛判定必須沿 AST 祖先鏈往上走；
    只有行號時，能做的最多是「整檔有沒有出現守衛字樣」那種檔案級近似——而那正是
    本輪修掉的缺陷（同一組 5 筆注入只抓到 1 筆）。
    """
    found: list[tuple[ast.AST, int, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _POSIX_ONLY_MODULES:
                    found.append((node, node.lineno, "POSIX-only", f"import {top}"))
                elif top in _WINDOWS_ONLY_MODULES:
                    found.append((node, node.lineno, "Windows-only", f"import {top}"))
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top in _POSIX_ONLY_MODULES:
                found.append((node, node.lineno, "POSIX-only", f"from {top} import …"))
            elif top in _WINDOWS_ONLY_MODULES:
                found.append((node, node.lineno, "Windows-only", f"from {top} import …"))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            owner, attr = node.value.id, node.attr
            if attr in probed:
                continue
            side = _FOREIGN_ATTR_TABLE.get(owner, {}).get(attr)
            if side:
                found.append((node, node.lineno, side, f"{owner}.{attr}"))
        elif isinstance(node, ast.keyword) and node.arg == "preexec_fn":
            found.append((node, node.lineno, "POSIX-only", "preexec_fn=（Windows 不支援）"))
        elif (isinstance(node, ast.keyword) and node.arg in _WINDOWS_ONLY_POPEN_KWARGS
              and _statically_nonzero(node.value)):
            found.append((node, node.lineno, "Windows-only",
                          f"{node.arg}=<非零字面值>（POSIX 的 Popen 直接 ValueError）"))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr in {"set_start_method", "get_context"}
              and node.args and isinstance(node.args[0], ast.Constant)
              and node.args[0].value in {"fork", "forkserver"}):
            found.append((node, node.lineno, "POSIX-only",
                          f"{node.func.attr}('{node.args[0].value}')"))
    return found


# ── 站點級守衛（R79 修 P1：檔案級＋純文字特赦的鑑別力只有 20%）─────────────────
# 新判準只問一句：**這個使用點在語法上被平台守衛罩住了嗎**。四種罩法（皆 repo 既存
# 真實寫法）＝ enclosing-if（祖先鏈的 If/IfExp/While 在判平台）／early-return-guard
# （同 block、排在其前且帶走控制流的 `if <守衛>: … return`）／guarded-decorator
# （含**同檔基底類別**的平台守衛 decorator）／try-capability（handler 捕 ImportError
# 族＝作者明示可選能力）。舊判準三個結構性後果（檔案級整檔赦免／純文字後門／不看
# 作用域）與「刻意不做方向判定」的劃界，全文搬至
# CrossPlatform_Guard_Line_History.md〈站點級守衛四種罩法 WHY〉節。
#: 平台守衛在 **AST** 上的形狀：只認「決定平台的**程式碼符號**」。
#: 為何不沿用 `_PLATFORM_GUARDS`（行文字 SSOT）做比對：那份清單是給**行掃描**用的，
#: 在 AST 上照用會把 `if "IS_WINDOWS" in env:`／`if "OSTYPE" in line:` 這種**字串**
#: 判成守衛——正是本輪要修的後門。兩者不得漂移這件事由
#: `test_text_guard_ssot_is_fully_recognised_by_the_ast_predicate` 機械釘住。
_PLATFORM_DECIDING_SYMBOLS: tuple[str, ...] = (
    "sys.platform", "os.name", "platform.system", "os.uname",
    "is_windows", "is_macos", "is_posix",
    "IS_WINDOWS", "IS_MACOS", "_is_windows",
)
#: `_PLATFORM_GUARDS` 內「碰巧也是合法 Python 運算式、但語意屬別的語言」的項。
#: 釘住它＝新增任何 Python 側守衛字樣而忘了教 AST 判準時，上面那支鎖會紅。
_NON_PYTHON_GUARD_TOKENS: frozenset[str] = frozenset({"uname -s", "OSTYPE"})
#: 「對面平台上這個 symbol 根本不存在」會拋的例外——捕它＝作者明示可選能力。
_CAPABILITY_EXC_NAMES: frozenset[str] = frozenset(
    {"ImportError", "ModuleNotFoundError", "AttributeError"})
_BLOCK_FIELDS: tuple[str, ...] = ("body", "orelse", "finalbody")


def _dotted_name(node: ast.AST) -> str | None:
    """`a.b.c` 形態的節點還原成字串；不是 Name/Attribute 鏈則回 None。"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def is_platform_guard_expr(test: ast.AST) -> bool:
    """這個運算式是不是在**判平台**？只認程式碼符號，字串／註解一律不算。"""
    for sub in ast.walk(test):
        dotted = _dotted_name(sub)
        if dotted and any(
            dotted == sym or dotted.endswith("." + sym)
            for sym in _PLATFORM_DECIDING_SYMBOLS
        ):
            return True
    return False


#: 「呼叫它＝控制流離開這個 block」的呼叫。R85 補上 skip 家族：`self.skipTest()` 與
#: `pytest.skip()` 內部就是 `raise SkipTest`，控制流**真的**離開——舊判準只認語法上的
#: `Return`／`Raise`，於是 `if os.name != "nt": self.skipTest(…)` 這個 repo 內的標準
#: 測試守衛形態被判成「沒有早退」。那是**述詞與現實不符**，不是放寬（實測：補上後
#: `_FOREIGN_API_SCOPE_DEBT` 一格都沒動，5 → 5）。
_FLOW_EXIT_CALLS = frozenset({
    "sys.exit", "os._exit", "exit", "quit",
    "self.skipTest", "skipTest", "pytest.skip", "unittest.skip",
})


def _flow_terminates(stmts: list[ast.stmt]) -> bool:
    """這個 block 的尾巴有沒有把控制流帶走（早退守衛成立的前提）。"""
    if not stmts:
        return False
    last = stmts[-1]
    if isinstance(last, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
        return True
    if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
        return _dotted_name(last.value.func) in _FLOW_EXIT_CALLS
    return False


def _try_catches_capability(node: ast.Try) -> bool:
    for handler in node.handlers:
        if handler.type is None:
            continue
        exprs = (handler.type.elts if isinstance(handler.type, ast.Tuple)
                 else [handler.type])
        for exc in exprs:
            name = (_dotted_name(exc) or "").rsplit(".", 1)[-1]
            if name in _CAPABILITY_EXC_NAMES:
                return True
    return False


def _ast_scope_index(tree: ast.AST) -> tuple[dict, dict, dict]:
    """回 (parent, slot, classes)：slot[child] = (owner, field, index)。"""
    parent: dict = {}
    slot: dict = {}
    classes: dict[str, ast.ClassDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes[node.name] = node
        for field in _BLOCK_FIELDS:
            seq = getattr(node, field, None)
            if isinstance(seq, list):
                for index, child in enumerate(seq):
                    if isinstance(child, ast.AST):
                        slot[child] = (node, field, index)
        for child in ast.iter_child_nodes(node):
            parent[child] = node
    return parent, slot, classes


def guard_alias_names(tree: ast.AST) -> frozenset[str]:
    """模組層 `NAME = <帶平台判定的運算式>` 的那些 NAME（R85）。

    🔴 立案是實測的假紅：`AutoClaude/tests/tools/test_run_local_nightly_static.py` 把
    `_WIN_NATIVE_ONLY = pytest.mark.skipif(platform.system() != "Windows", …)` 綁在模組層，
    測試只寫 `@_WIN_NATIVE_ONLY`。decorator 節點是一個裸 `Name`，`is_platform_guard_expr`
    在它身上看不到任何平台符號 ⇒ 整批被判成沒守衛。這是**述詞看不見一層間接**，
    不是那些檔真的沒守衛。
    """
    return frozenset(
        target.id
        for node in getattr(tree, "body", [])
        if isinstance(node, ast.Assign) and is_platform_guard_expr(node.value)
        for target in node.targets if isinstance(target, ast.Name))


def _decorated_by_platform_guard(
    node: ast.AST, classes: dict[str, ast.ClassDef], seen: set | None = None,
    aliases: frozenset[str] = frozenset(),
) -> bool:
    """def/class 自己或（同檔）任一祖先類別帶平台守衛 decorator。

    基底類別要跟著看，否則 `@unittest.skipUnless(sys.platform == "darwin", …)`
    放在共用夾具基底、子類別只寫測試（本 repo 的既有寫法）會被整批誤判。
    `aliases`＝`guard_alias_names()` 的結果（預設空 ⇒ 既有呼叫端行為逐字不變）。
    """
    for dec in getattr(node, "decorator_list", []):
        if is_platform_guard_expr(dec):
            return True
        dotted = _dotted_name(dec) or ""
        if aliases and (dotted in aliases or dotted.split(".")[0] in aliases):
            return True
    if not isinstance(node, ast.ClassDef):
        return False
    seen = set() if seen is None else seen
    for base in node.bases:
        dotted = _dotted_name(base)
        base_node = classes.get(dotted.rsplit(".", 1)[-1]) if dotted else None
        if base_node is not None and base_node not in seen:
            seen.add(base_node)
            if _decorated_by_platform_guard(base_node, classes, seen, aliases):
                return True
    return False


def _references_capability_flag(test: ast.AST, flags: frozenset[str] | set[str]) -> bool:
    """這個 `if` 的條件是不是在讀一個由 `hasattr(...)` 綁出來的能力旗標？"""
    return any(isinstance(sub, ast.Name) and sub.id in flags for sub in ast.walk(test))


def guard_scope_for(
    node: ast.AST, parent: dict, slot: dict, classes: dict,
    capability_flags: frozenset[str] | set[str] = frozenset(),
    aliases: frozenset[str] = frozenset(),
) -> str | None:
    """該使用點被哪一種**站點級**守衛罩住；None＝一種都沒有（＝違規）。

    `capability_flags`（R81）＝第五種罩法「capability-flag-guard」的輸入，見
    `_capability_flag_names()`。預設空集合 ⇒ 既有呼叫端行為逐字不變。
    """
    cur = node
    while cur in parent:
        owner = parent[cur]
        if (isinstance(owner, (ast.If, ast.IfExp, ast.While))
                and is_platform_guard_expr(owner.test)):
            return "enclosing-if"
        if (isinstance(owner, (ast.If, ast.IfExp, ast.While)) and capability_flags
                and _references_capability_flag(owner.test, capability_flags)):
            return "capability-flag-guard"
        if (isinstance(owner, ast.Try) and any(cur is s for s in owner.body)
                and _try_catches_capability(owner)):
            return "try-capability"
        if (isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and _decorated_by_platform_guard(owner, classes, aliases=aliases)):
            return "guarded-decorator"
        position = slot.get(cur)
        if position is not None:
            blk_owner, field, index = position
            for prev in getattr(blk_owner, field)[:index]:
                if (isinstance(prev, ast.If) and is_platform_guard_expr(prev.test)
                        and (_flow_terminates(prev.body) or _flow_terminates(prev.orelse))):
                    return "early-return-guard"
        cur = owner
    return None


# ── R85／A-3：單平台專屬**外部執行檔**的 argv[0] 字面 ────────────────────────
# 上面那個判準的詞彙表收的是 **Python 符號**，「送給 OS 的外部程式名」只是一個
# `ast.Constant` 字串 ⇒ 那一族從來不在分母裡（失明是靜默的）。🔴 詞彙表刻意不在這裡
# 再寫一份：唯一的家＝`tools/probe/xplat_hazard_census.py`，本檔只提供「門」。
# 🔴 transitive 可達性（深度上界 3＝實測值）是本族**必要條件**、且**只**用在本族，
# 不回頭套到上面那個符號判準（那張債表是雙向精確比對，套過去會把登記過的債靜默抹掉）
# ——P7 逐筆實測、3 筆假紅普查與 `_FOREIGN_API_SCOPE_DEBT` 互斥理由全文搬至
# CrossPlatform_Guard_Line_History.md〈外部執行檔 argv[0] transitive WHY〉節。
_EXE_ARGV_TRANSITIVE_DEPTH = 3


def _enclosing_func(node: ast.AST, parent: dict) -> ast.AST | None:
    cur = node
    while cur in parent:
        cur = parent[cur]
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
    return None


def _call_sites(tree: ast.AST, name: str, inside: ast.AST) -> list[ast.Call]:
    """全檔對 `name` 的呼叫節點，**排除** `inside` 自己體內的（遞迴呼叫不算外部呼叫端）。"""
    banned = set(ast.walk(inside))
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and n not in banned
            and ((isinstance(n.func, ast.Name) and n.func.id == name)
                 or (isinstance(n.func, ast.Attribute) and n.func.attr == name))]


def guard_scope_transitive(node, tree, parent, slot, classes, flags, aliases,
                           depth: int = _EXE_ARGV_TRANSITIVE_DEPTH,
                           seen: frozenset = frozenset()) -> str | None:
    """站點級守衛，找不到時再問「包住它的函式的**每一個**呼叫端是不是都被守住」。

    `all(...)` 而不是 `any(...)` 是關鍵：只要有一個呼叫端沒被守住，那條路就會在對面
    平台上真的走到 ⇒ 不成立。沒有任何呼叫端（`sites` 為空）也不成立——那代表它是別處
    import 進去用的，靜態上證不出來，而「證不出來」必須落在紅的那一側。
    """
    direct = guard_scope_for(node, parent, slot, classes, flags, aliases)
    if direct or depth <= 0:
        return direct
    func = _enclosing_func(node, parent)
    if func is None or func in seen:
        return None
    sites = _call_sites(tree, func.name, func)
    return (f"transitive-callsite-guard(via {func.name})" if sites and all(
        guard_scope_transitive(s, tree, parent, slot, classes, flags, aliases,
                               depth - 1, seen | {func}) for s in sites) else None)


def scan_foreign_exe_argv(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], []
    uses: list[tuple[ast.Call, int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _CENSUS._is_subprocess_call(node):
            continue
        for exe in _CENSUS._argv0_literals(node):
            base = PurePosixPath(exe.replace("\\", "/")).name.lower()
            side = ("Windows-only" if base in _CENSUS._WIN_ONLY_EXE
                    else "POSIX-only" if base in _CENSUS._POSIX_ONLY_EXE else None)
            if side:
                uses.append((node, node.lineno, side, base))
    if not uses:
        return [], []
    markers = _xplat_markers(source)
    parent, slot, classes = _ast_scope_index(tree)
    flags, aliases = _capability_flag_names(tree), guard_alias_names(tree)
    offenders = []
    for node, lineno, side, token in sorted(uses, key=lambda u: (u[1], u[3])):
        if markers.get(lineno) or guard_scope_transitive(
                node, tree, parent, slot, classes, flags, aliases):
            continue
        offenders.append(
            f"{rel}:{lineno}: argv[0] 是 {side} 的外部執行檔 `{token}`，而這個**使用點**"
            "既不在任何平台守衛的作用域內，包住它的函式也不是「每一個呼叫端都被守住」"
            "——對面平台上它不是「行為不同」而是 FileNotFoundError（Windows 側為 "
            "WinError 2/193）。修法：加作用域內守衛、讓呼叫端全數帶守衛，"
            f"或於該行行尾加 `# {_XPLAT_OK_MARKER} <WHY>`")
    return offenders, []


def scan_foreign_platform_api(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], []
    markers = _xplat_markers(source)
    uses = _foreign_api_uses(tree, _capability_probed(tree))
    grouped: dict[tuple[int, str, str], list[ast.AST]] = {}
    for node, lineno, side, what in uses:
        grouped.setdefault((lineno, side, what), []).append(node)
    # 索引只在真有使用點時才建（掃描面 800+ 檔，絕大多數一個使用點都沒有）。
    parent, slot, classes = _ast_scope_index(tree) if grouped else ({}, {}, {})
    flags = _capability_flag_names(tree) if grouped else set()
    offenders: list[str] = []
    used: set[int] = set()
    for (lineno, side, what), nodes in sorted(grouped.items()):
        if markers.get(lineno):
            used.add(lineno)
            continue
        # 同一 (行, 方向, 說明) 有多個節點時，只要**其中一個**沒被罩住就算違規——
        # 取第一個判會讓「同行兩處、一處有守衛」把另一處免費藏起來。
        if all(guard_scope_for(n, parent, slot, classes, flags) for n in nodes):
            continue
        offenders.append(
            f"{rel}:{lineno}: 使用 {side} 的 `{what}`，但這個**使用點**不在任何平台"
            "守衛的作用域內（可接受的四種：包住它的 if 判平台／同 block 排在它之前的"
            "早退守衛／所在 def-class 帶平台守衛 decorator／try 捕 ImportError 類）"
            "——對面平台上它不是「行為不同」而是「直接炸掉」（缺屬性／ImportError）"
        )
    stale = [
        f"{rel}:{lineno}: {_XPLAT_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return offenders, stale


#: 站點級判準上線當回合的**存量**：檔案級特赦收成作用域級之後，仍未被任何作用域
#: 守衛罩住的使用點數，逐檔精確計數。
#: 判準是**雙向精確比對**：多一筆紅（新增了未守衛的使用點）、少一筆也紅（債已還，
#: 請把數字改小）——只准降不准升的單邊寫法會讓這張表變成一張永久保護傘。
#: 合法出口只有兩條：① 把站點改成作用域內守衛；② 該行行尾加 `_XPLAT_OK_MARKER` 標記。
#: （本註解刻意不寫出那個標記的字面值——本檔自己也在掃描面內，寫出來就會被
#:   `_xplat_markers()` 當成一個真的豁免標記而判 stale。）
#: 🔴 表列債的逐筆沿革——R79 誠實劃界（`tools/dev_start.py` 訊號 handler 不屬包所有權、
#:   只登記不代改）與 R81（XPL-S1-04）詞彙表補 `ctypes.*` 後 4→5 的逐點實測（9 站點
#:   8 個被既有作用域守衛罩住、`:1051` 安全性寄託呼叫端）——
#:   全文搬至 CrossPlatform_Guard_Line_History.md〈作用域級存量債表沿革〉節。
_FOREIGN_API_SCOPE_DEBT: dict[str, int] = {
    "tools/dev_start.py": 5,
}


#: 本判準上線當回合的**存量**：全庫 24 筆 exe-argv 命中，逐筆比對五種站點級罩法
#: ＋ transitive 可達性後，未被罩住者 **0 筆**（假紅 0、存量 0）⇒ 這是一支**純寫入面**
#: 判準（與大表「`Get-Command` 解析」那一格同形：存量 0 時缺的一直是「下一個人寫出來時
#: 當場紅」的門，而不是數今天有幾筆）。判準與上面那張債表相同是**雙向精確比對**。
_FOREIGN_EXE_ARGV_DEBT: dict[str, int] = {}


class TestForeignExecutableArgvIsGuarded(unittest.TestCase):
    """單平台專屬**外部執行檔** argv[0]（R85／A-3，見上方區段 WHY）。"""

    def test_no_unguarded_foreign_executable(self) -> None:
        offenders, _stale, parse_failures, band = run_unit_scan(scan_foreign_exe_argv)
        self.assertEqual(parse_failures, [], "掃描面不得靜默縮小：\n" + "\n".join(parse_failures))
        actual: dict[str, int] = {}
        for line in offenders:
            rel = line.split(":", 1)[0]
            actual[rel] = actual.get(rel, 0) + 1
        self.assertEqual(
            actual, dict(_FOREIGN_EXE_ARGV_DEBT),
            "多一筆＝新增了未守衛的單平台外部執行檔；少一筆＝債已還請把數字改小：\n"
            + "\n".join(offenders))
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    def _scan(self, source: str) -> list[str]:
        return scan_foreign_exe_argv(source, _INJECTION_TARGET_REL)[0]

    def test_the_criterion_detects_both_directions(self) -> None:
        """紅：兩個方向的裸站點都要抓到（只抓一邊＝另一邊恆綠）。"""
        for sample, side in (
            ('def f():\n    subprocess.run(["powershell.exe", "-c", "x"])\n', "Windows-only"),
            ('def f():\n    subprocess.run(["osascript", "-e", "x"])\n', "POSIX-only"),
            ('def f():\n    subprocess.Popen("taskkill")\n', "Windows-only"),
        ):
            with self.subTest(sample=sample):
                off = self._scan(sample)
                self.assertTrue(off, f"{sample!r} 漏抓 ⇒ 這一族仍失明")
                self.assertIn(side, off[0])

    def test_two_sided_executables_are_not_flagged(self) -> None:
        """綠：兩個平台都有的執行檔一律不判——判它就是滿螢幕假紅。"""
        for exe in ("git", "python", "node", "docker"):
            with self.subTest(exe=exe):
                self.assertEqual(self._scan(f'def f():\n    subprocess.run(["{exe}"])\n'), [])

    def test_every_site_level_guard_shape_is_accepted(self) -> None:
        """綠：repo 內既存的四種站點級寫法（誤紅任一種，這道鎖活不過一輪）。"""
        for label, sample in (
            ("enclosing-if", 'def f():\n    if os.name == "nt":\n'
                             '        subprocess.run(["taskkill"])\n'),
            ("early-return-guard", 'def f():\n    if os.name != "nt":\n        return\n'
                                   '    subprocess.run(["taskkill"])\n'),
            ("early-return-guard/skipTest", 'def f(self):\n    if os.name != "nt":\n'
                                            '        self.skipTest("win only")\n'
                                            '    subprocess.run(["taskkill"])\n'),
            ("decorator alias（模組層綁定）",
             'W = pytest.mark.skipif(platform.system() != "Windows", reason="x")\n\n'
             '@W\ndef f():\n    subprocess.run(["taskkill"])\n'),
        ):
            with self.subTest(label):
                self.assertEqual(self._scan(sample), [], f"{label} 被誤判成沒守衛")

    def test_transitive_reachability_is_all_not_any(self) -> None:
        """🔴 本族的核心：跨層 helper 的守衛在**呼叫端**，而判準必須是 all 不是 any。

        三向都驗——只驗綠的那一向時，把 `all` 寫成 `any`（或乾脆恆真）照樣全綠。
        """
        helper = 'def _run():\n    subprocess.run(["powershell.exe"])\n\n'
        self.assertEqual(
            self._scan(helper + 'def a():\n    if os.name == "nt":\n        _run()\n'),
            [], "唯一呼叫端有守衛，卻仍判紅 ⇒ transitive 可達性沒有生效")
        self.assertTrue(
            self._scan(helper + 'def a():\n    if os.name == "nt":\n        _run()\n\n'
                       "def b():\n    _run()\n"),
            "有一個呼叫端**沒有**守衛卻放行 ⇒ 判準是 any 不是 all，那條路在對面平台會真的走到")
        self.assertTrue(
            self._scan(helper), "一個呼叫端都沒有（別處 import 去用）卻放行 ⇒ "
                                "「證不出來」被讀成了「安全」")

    def test_depth_is_bounded_and_the_bound_is_honest(self) -> None:
        """深度上界必須真的是上界：超過它就不再放行（否則「上界」只是註解）。"""
        chain = 'def h0():\n    subprocess.run(["powershell.exe"])\n\n'
        for i in range(1, _EXE_ARGV_TRANSITIVE_DEPTH + 2):
            chain += f"def h{i}():\n    h{i - 1}()\n\n"
        top = _EXE_ARGV_TRANSITIVE_DEPTH + 1
        self.assertTrue(
            self._scan(chain + f'def top():\n    if os.name == "nt":\n        h{top}()\n'),
            f"鏈長 {top} > 上界 {_EXE_ARGV_TRANSITIVE_DEPTH} 卻放行 ⇒ 上界沒有生效")


class TestForeignPlatformApiIsGuarded(unittest.TestCase):
    """對面平台專屬 API 必須帶平台守衛（見上方區段 WHY）。"""

    def test_no_unguarded_foreign_platform_api(self) -> None:
        offenders, stale, parse_failures, band = run_unit_scan(scan_foreign_platform_api)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        actual: dict[str, int] = {}
        for line in offenders:
            rel = line.split(":", 1)[0]
            actual[rel] = actual.get(rel, 0) + 1
        unregistered = [o for o in offenders
                        if o.split(":", 1)[0] not in _FOREIGN_API_SCOPE_DEBT]
        self.assertEqual(
            unregistered, [],
            "發現未守衛的單平台專屬 API——請加**作用域內**平台守衛、改用 `hasattr` "
            f"明示可選能力，或於該行行尾加 `# {_XPLAT_OK_MARKER} <WHY>`：\n"
            + "\n".join(unregistered),
        )
        self.assertEqual(
            actual, dict(_FOREIGN_API_SCOPE_DEBT),
            "`_FOREIGN_API_SCOPE_DEBT` 與實測不符。多一筆＝新增了未守衛的使用點；"
            "少一筆＝債已還請把數字改小（不改的話這張表會變成永久保護傘，"
            "下一筆新違規會被舊值遮住）：\n" + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_XPLAT_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )
        self.assertEqual(band, [], "掃描面下限帶：\n" + "\n".join(band))

    # ── 以合成樣本自證判準紅綠（樣本只存在於字串，不留違規樣本於 repo）──────

    def _scan(self, source: str) -> tuple[list[str], list[str]]:
        return scan_foreign_platform_api(source, _INJECTION_TARGET_REL)

    def test_each_whitelisted_symbol_family_is_detected(self) -> None:
        for sample in (
            "import pwd\n",
            "import winreg\n",
            "def f():\n    return os.fork()\n",
            "def f(p):\n    os.killpg(p, signal.SIGKILL)\n",
            "def f(p):\n    os.startfile(p)\n",
            "def f(c):\n    subprocess.run(c, preexec_fn=None)\n",
            'def f(mp):\n    mp.set_start_method("fork")\n',
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertTrue(off, f"{sample!r} 漏抓 ⇒ 白名單那一半沒有牙")

    def test_a_guard_before_the_use_is_accepted(self) -> None:
        """修法慣例必綠——否則本鎖會逼人把守衛拿掉。"""
        for sample in (
            'import sys\nif sys.platform == "win32":\n    import winreg\n',
            'def f():\n    if os.name == "nt":\n        return None\n    return os.fork()\n',
            'def f():\n    if hasattr(os, "geteuid"):\n        return os.geteuid()\n'
            "    return 0\n",
        ):
            with self.subTest(sample=sample):
                off, stale = self._scan(sample)
                self.assertEqual((off, stale), ([], []), f"{sample!r} 誤報")

    # ── R81 XPL-S1-03/04/05：新補的三族詞彙，逐族紅綠自證 ──────────────────────

    def test_the_ctypes_windows_family_is_detected(self) -> None:
        """XPL-S1-04：`ctypes.*` 這一族在舊判準下是**整片失明**（合成 3 筆命中 0）。"""
        for sample in (
            "def f():\n    return ctypes.windll.kernel32\n",
            "def f():\n    return ctypes.WinDLL('x')\n",
            "def f():\n    return ctypes.FormatError()\n",
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertTrue(off, f"{sample!r} 漏抓 ⇒ ctypes 這一族仍失明")
                self.assertIn("Windows-only", off[0])

    def test_the_ctypes_family_accepts_the_existing_correct_shape(self) -> None:
        """反誤紅：repo 現行 8/9 個站點的守衛形態不得轉紅。"""
        off, stale = self._scan(
            "def f():\n    if platform_utils.is_windows():\n"
            "        return ctypes.windll.kernel32\n    return None\n")
        self.assertEqual((off, stale), ([], []))

    def test_the_subprocess_windows_flag_family_is_detected(self) -> None:
        """XPL-S1-03：`creationflags=subprocess.CREATE_NO_WINDOW` ＝該筆逐字描述的
        「下一個人會寫出來、mac 上當場 ValueError」形態，必須紅。"""
        for sample in (
            "def f(c):\n    subprocess.run(c, creationflags=subprocess.CREATE_NO_WINDOW)\n",
            "def f(c):\n    subprocess.Popen(c, startupinfo=subprocess.STARTUPINFO())\n",
            "def f(c):\n    subprocess.Popen(c, creationflags=8)\n",
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertTrue(off, f"{sample!r} 漏抓 ⇒ Windows 專屬 Popen 旗標無門")

    def test_the_capability_degrading_creationflags_shape_stays_green(self) -> None:
        """反誤紅（本判準的**取捨本體**）：repo 現行 11 個 `creationflags=` 站點一律傳
        `getattr` 兜底出來的模組常數，POSIX 上取 0＝`Popen` 不 raise＝**正解**。
        判準若把 kwarg 本身判紅，這 11 筆會當場全紅，而假紅會逼下一輪關掉整條鎖。"""
        for sample in (
            "def f(c):\n    subprocess.run(c, creationflags=NO_WINDOW)\n",
            "def f(c):\n    subprocess.run(c, creationflags=guard.NO_WINDOW)\n",
            "def f(c):\n    subprocess.run(c, creationflags=0)\n",
        ):
            with self.subTest(sample=sample):
                off, stale = self._scan(sample)
                self.assertEqual((off, stale), ([], []), f"{sample!r} 誤報")

    def test_the_widened_signal_family_is_detected(self) -> None:
        """XPL-S1-05：`SIGALRM`／`alarm`／`SIGPIPE` 舊表全在表外。"""
        for sample in (
            "def f():\n    signal.alarm(2)\n",
            "def f():\n    signal.signal(signal.SIGALRM, h)\n",
            "def f():\n    signal.signal(signal.SIGPIPE, signal.SIG_DFL)\n",
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertTrue(off, f"{sample!r} 漏抓 ⇒ 訊號詞彙表仍缺這一族")

    def test_the_hasattr_flag_guard_shape_is_accepted(self) -> None:
        """反誤紅：LATEST 框架版兩支 hook 的**正確**寫法（`has_alarm = hasattr(...)`
        ➜ `if has_alarm:`）不得轉紅——不然這道門是拿 4 筆假紅換來的。"""
        off, stale = self._scan(
            "def f():\n"
            '    has_alarm = hasattr(signal, "SIGALRM")\n'
            "    if has_alarm:\n"
            "        signal.signal(signal.SIGALRM, h)\n"
            "        signal.alarm(2)\n"
            "    else:\n"
            "        run_with_threadpool()\n"
        )
        self.assertEqual((off, stale), ([], []))

    def test_the_hasattr_flag_guard_does_not_absolve_unrelated_ifs(self) -> None:
        """鑑別力：沒有 `hasattr` 綁定的旗標名不得白白赦免（否則任何 `if x:` 都是後門）。"""
        off, _ = self._scan(
            "def f():\n    has_alarm = True\n    if has_alarm:\n        signal.alarm(2)\n")
        self.assertEqual(len(off), 1, off)

    def test_a_guard_after_the_use_does_not_count(self) -> None:
        """守衛排在使用之後不算（DEF-101-766 的形態，沿用第五道判準的順序語意）。"""
        off, _ = self._scan(
            'def f():\n    pid = os.fork()\n    if os.name == "nt":\n'
            "        return None\n    return pid\n"
        )
        self.assertEqual(len(off), 1, off)

    def test_mentions_in_comments_and_docstrings_are_not_uses(self) -> None:
        """對照組：註解／docstring 提到這些名字不算使用（假紅會逼人關掉整條鎖）。"""
        for sample in (
            "# 這裡本來想用 os.fork()，改走 subprocess\nx = 1\n",
            '"""說明：POSIX 上是 os.killpg + signal.SIGKILL。"""\nx = 1\n',
            'MSG = "import pwd 在 Windows 上會 ImportError"\n',
        ):
            with self.subTest(sample=sample):
                off, _ = self._scan(sample)
                self.assertEqual(off, [], f"{sample!r} 誤報：{off}")

    def test_marker_suppresses_and_a_dangling_marker_is_stale(self) -> None:
        off, stale = self._scan(
            f"def f():\n    return os.fork()  # {_XPLAT_OK_MARKER} 只在 POSIX 分支呼叫\n")
        self.assertEqual((off, stale), ([], []))
        off, stale = self._scan(f"x = 1  # {_XPLAT_OK_MARKER} 已改走 subprocess\n")
        self.assertEqual(off, [])
        self.assertEqual(len(stale), 1, "違規已消失的標記必須被指名刪除")
        off, stale = self._scan(f"def f():\n    return os.fork()  # {_XPLAT_OK_MARKER}\n")
        self.assertEqual(len(off), 1, "WHY 留空的標記不得生效")

    # ── R79：站點級特赦的紅綠自證（舊判準在這幾題上的實測值逐題記在斷言訊息裡）──

    #: 5 筆彼此獨立的違規，刻意分散在 4 個函式：`import pwd`／`os.killpg`／
    #: `signal.SIGKILL`／`os.getuid`／`os.fork`。
    _FIVE_VIOLATIONS = (
        "import pwd\n"
        "\n"
        "\n"
        "def kill(pgid):\n"
        "    os.killpg(pgid, signal.SIGKILL)\n"
        "\n"
        "\n"
        "def who():\n"
        "    return os.getuid()\n"
        "\n"
        "\n"
        "def spawn():\n"
        "    return os.fork()\n"
    )
    #: 與那 5 筆違規**完全無關**的一段守衛（隔壁函式），舊判準會拿它特赦整檔。
    _UNRELATED_GUARD = (
        "def unrelated():\n"
        '    if sys.platform == "win32":\n'
        "        return 1\n"
        "    return 0\n"
        "\n"
        "\n"
    )

    def test_an_unrelated_guard_elsewhere_no_longer_amnesties_the_whole_file(self) -> None:
        """情境 A：隔壁函式的守衛不得赦免整檔（舊判準此題只抓到 1/5）。"""
        head, _, tail = self._FIVE_VIOLATIONS.partition("\n\n\n")
        sample = head + "\n\n\n" + self._UNRELATED_GUARD + tail
        off, _ = self._scan(sample)
        self.assertEqual(
            len(off), 5,
            "同一組 5 筆違規只抓到部分 ⇒ 檔案級特赦仍在（舊判準實測 1/5）：\n"
            + "\n".join(off),
        )

    def test_the_same_five_violations_without_any_guard(self) -> None:
        """情境 B：對照組——沒有那段無關守衛時本來就該是 5/5。"""
        off, _ = self._scan(self._FIVE_VIOLATIONS)
        self.assertEqual(len(off), 5, "\n".join(off))

    def test_a_guard_phrase_inside_a_string_constant_is_not_a_guard(self) -> None:
        """情境 C：守衛字樣只出現在字串常數裡（舊判準此題 0/1）。"""
        off, _ = self._scan(
            'MSG = "設定 os.name == \'nt\' 時走另一條路"\n'
            "\n"
            "\n"
            "def spawn():\n"
            "    return os.fork()\n"
        )
        self.assertEqual(len(off), 1, f"字串常數不得構成守衛：{off}")

    def test_a_string_operand_inside_an_if_test_is_not_a_guard(self) -> None:
        """`if "IS_WINDOWS" in env:` 不是在判平台——這是文字比對留下的最後一個後門。"""
        off, _ = self._scan(
            'def f(env):\n    if "IS_WINDOWS" in env:\n        return os.fork()\n'
            "    return 0\n"
        )
        self.assertEqual(len(off), 1, f"字串運算元不得構成守衛：{off}")

    def test_each_accepted_scope_form_is_green(self) -> None:
        """四種罩法逐一必綠——任何一種掉了，repo 內既有的合法寫法會整批假紅。"""
        for label, sample in (
            ("enclosing-if",
             'def f():\n    if os.name != "nt":\n        return os.fork()\n    return 0\n'),
            ("early-return-guard",
             "def f(pid):\n    if platform_utils.is_windows():\n        return None\n"
             "    return os.getpgid(pid)\n"),
            ("guarded-decorator",
             '@unittest.skipIf(sys.platform == "win32", "POSIX only")\n'
             "class T:\n    def t(self):\n        return os.fork()\n"),
            ("inherited-decorator",
             '@unittest.skipUnless(sys.platform == "darwin", "mac only")\n'
             "class Base:\n    pass\n"
             "\n"
             "\n"
             "class T(Base):\n    def t(self):\n        return os.getuid()\n"),
            ("try-capability",
             "try:\n    import pwd\nexcept ImportError:\n    pwd = None\n"),
        ):
            with self.subTest(scope=label):
                off, _ = self._scan(sample)
                self.assertEqual(off, [], f"{label} 誤報：{off}")

    def test_a_terminating_guard_is_required_for_the_early_return_form(self) -> None:
        """早退守衛必須真的早退：`if is_windows(): pass` 罩不住後面的 POSIX 碼。"""
        off, _ = self._scan(
            "def f(pid):\n    if platform_utils.is_windows():\n        pass\n"
            "    return os.getpgid(pid)\n"
        )
        self.assertEqual(len(off), 1, f"沒有帶走控制流的 if 不算守衛：{off}")

    def test_text_guard_ssot_is_fully_recognised_by_the_ast_predicate(self) -> None:
        """鎖的鎖：`_PLATFORM_GUARDS` 的 Python 側每一項都必須被 AST 判準認得。

        兩份知識（行文字 SSOT ／ AST 符號表）不得單向漂移——有人往
        `_PLATFORM_GUARDS` 補一個新的 Python 守衛字樣卻忘了教 AST 判準時，
        那個字樣在本判準上會靜默失效（＝合法寫法假紅）。這裡把「解析得動、
        但 AST 判準不認」的集合精確釘死在已知的非 Python 項上。
        """
        unrecognised = set()
        for token in _PLATFORM_GUARDS:
            try:
                expr = ast.parse(token, mode="eval").body
            except SyntaxError:
                continue          # PowerShell／shell 專屬字樣，本判準射程外
            if not is_platform_guard_expr(expr):
                unrecognised.add(token)
        self.assertEqual(
            unrecognised, set(_NON_PYTHON_GUARD_TOKENS),
            "`_PLATFORM_GUARDS` 與 `_PLATFORM_DECIDING_SYMBOLS` 漂移了："
            f"{sorted(unrecognised)}",
        )

    def test_the_debt_table_only_names_files_that_exist(self) -> None:
        """存量債表不得指向幽靈檔（否則那一格永遠是 0，等同一張空白支票）。"""
        missing = [rel for rel in _FOREIGN_API_SCOPE_DEBT
                   if not (_REPO_ROOT / rel).is_file()]
        self.assertEqual(missing, [], f"債表指向不存在的檔：{missing}")


# ══════════════════════════════════════════════════════════════════════════════
# R79（D-ps1eol）— **工作樹**行尾閘：`.ps1` 必為 CRLF、`.sh` 必為 LF
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體與判準設計全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R79 工作樹行尾閘 WHY〉節。
_GITATTRIBUTES_PATH = _REPO_ROOT / ".gitattributes"
#: `*.<suffix>  <attrs>` 形態的宣告行（`#` 註解行不匹配；`* text=auto eol=lf` 這種
#: 無副檔名的兜底規則也不匹配——它涵蓋全庫，不是「腳本行尾」這個主題）。
_EOL_DECL_RE = re.compile(r"^\s*\*(\.[A-Za-z0-9]+)\s+([^#\n]*)", re.M)
#: LF 側刻意**不**全收（誠實劃界，不是漏看）：根 `.gitattributes` 對 `.py`／`.md`／
#: `.yaml` 等也宣告 `eol=lf`，全收會把本閘的主題從「腳本行尾」擴成「全庫文字檔行尾」
#: ——當回合實測全庫有五位數支檔案的工作樹行尾與宣告不符，絕大多數落在 AISDLC_SDD
#: 凍結版樹（Copy-on-Evolve 禁改面）。本閘的主題是腳本，故 LF 側只收 shell 腳本族；
#: 但**值仍向 `.gitattributes` 取**，本檔不寫死 `lf` 這兩個字。
_EOL_LF_SCOPE: tuple[str, ...] = (".sh", ".bash")


def declared_eol(gitattributes_text: str) -> dict[str, str]:
    """`.gitattributes` 裡每一條 `*.<副檔名> … eol=<lf|crlf>` 宣告。純函式。"""
    out: dict[str, str] = {}
    for suffix, attrs in _EOL_DECL_RE.findall(gitattributes_text):
        match = re.search(r"\beol=(lf|crlf)\b", attrs)
        if match:
            out[suffix.lower()] = match.group(1)
    return out


def worktree_eol_policy(declared: dict[str, str]) -> dict[str, str]:
    """本閘的政策映射＝**現查值**（見上方 WHY）。

    CRLF 側**全收**：`eol=crlf` 在本 repo 就是「Windows-only 腳本族」的同義詞，
    新增一個（例如日後的 `.cmd`）自動進射程，不需要有人記得同步第二份表。
    LF 側只收 `_EOL_LF_SCOPE`，理由見該常數。
    """
    policy = {suffix: eol for suffix, eol in declared.items() if eol == "crlf"}
    policy.update({s: declared[s] for s in _EOL_LF_SCOPE if s in declared})
    return policy


if not _GITATTRIBUTES_PATH.is_file():                  # fail-loud：沒有 SSOT 就沒有政策
    raise AssertionError(f"找不到 {_GITATTRIBUTES_PATH}——行尾政策的唯一真相源缺席")
_WORKTREE_EOL_POLICY: dict[str, str] = worktree_eol_policy(
    declared_eol(_GITATTRIBUTES_PATH.read_text(encoding="utf-8")))
#: 反空轉下限（**逐副檔名**，R79 收輪實測 `.ps1` 136 支／`.sh` 168 支，取約八折）。
#: 🔴 為何不是一個總數（R79 四方複審 SD nonblocking）：單一總數吃得下「某一個副檔名
#: 整片消失」——`.ps1` 全滅而 `.sh` 還在時，總數照樣過關，而那正是這道閘要抓的形態。
#: 只登記**現存母體夠大**的副檔名；`.psm1`／`.psd1`／`.cmd`／`.bat` 現況零支，
#: 給它們一個 0 下限等於沒登記，故刻意不入表（入表與否由下面的判準機械對帳）。
_WORKTREE_EOL_FLOORS: dict[str, int] = {".ps1": 108, ".sh": 134}


class EolRecord(NamedTuple):
    """`git ls-files --eol` 的一列。三欄分屬**兩個不同的平面**，別混用（R82）：

    `index`＝blob 的行尾（content-addressed ⇒ 每台機器同一個值，**會跨平台傳染**）；
    `worktree`＝這一棵 checkout 的位元組（機器狀態，隨 checkout 歷史走，不傳染）。
    """

    path: str
    index: str
    worktree: str
    attr: str


def parse_ls_files_eol_records(stdout: str) -> list[EolRecord]:
    """`git ls-files --eol` 的輸出 → 逐列三欄。純函式，供紅綠自證共用。

    格式（當回合實測逐字）：`i/lf    w/crlf  attr/text eol=crlf    \t<path>`
    ——三個欄位以**空白**右補、彼此不以 tab 分隔，整行只有**一個** tab 且它就在
    路徑前面。`attr/` 欄本身含空白（`text eol=crlf`），所以不能用空白切欄。
    """
    rows: list[EolRecord] = []
    for line in stdout.splitlines():
        head, sep, path = line.partition("\t")
        if not sep or not path.strip():
            continue
        index, worktree = (re.search(rf"\b{col}/(\S*)", head) for col in "iw")
        rows.append(EolRecord(path.strip(), index.group(1) if index else "",
                              worktree.group(1) if worktree else "",
                              head.partition("attr/")[2].strip()))
    return rows


def parse_ls_files_eol(stdout: str) -> list[tuple[str, str]]:
    """（工作樹欄的薄取用）`[(路徑, 工作樹行尾)]`——解析知識只有上面那**一個**家。"""
    return [(r.path, r.worktree) for r in parse_ls_files_eol_records(stdout)]


def path_suffix(path: str) -> str:
    """repo 相對路徑的小寫副檔名（含點）。無副檔名回空字串。"""
    name = path.rsplit("/", 1)[-1]
    return "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""


def worktree_eol_problems(rows: list[tuple[str, str]]) -> list[str]:
    """逐列過政策表；回問題清單，空＝合格。純函式（紅綠由合成注入自證）。"""
    problems: list[str] = []
    for path, worktree in rows:
        want = _WORKTREE_EOL_POLICY.get(path_suffix(path))
        if want is None:
            continue
        if worktree in {want, "none"}:   # none＝空檔／無換行，無從違反
            continue
        problems.append(
            f"{path}: 工作樹行尾為 `{worktree or '未知'}`，政策要求 `{want}`"
            f"（.gitattributes 已宣告；index 側因 checkin 正規化恆為 lf，"
            "故只有工作樹這一欄看得到這種漂移）"
        )
    return problems


class TestWorktreeEolMatchesPolicy(unittest.TestCase):
    """工作樹行尾必須符合 `.gitattributes` 宣告（見上方區段 WHY）。"""

    @staticmethod
    def _ls_files_eol() -> str:
        proc = git_paths.run(
            _REPO_ROOT, "ls-files", "--eol", "--",
            *(f"*{suffix}" for suffix in sorted(_WORKTREE_EOL_POLICY)),
            timeout=120,
        )
        if proc.returncode != 0:                      # 取數管道壞掉不得靜默變成「零違規」
            raise AssertionError(
                f"git ls-files --eol 失敗（rc={proc.returncode}；stderr="
                f"{proc.stderr.strip()!r}）——本閘的輸入沒了，不是「沒有違規」"
            )
        return proc.stdout

    def test_tracked_scripts_have_the_declared_worktree_eol(self) -> None:
        rows = parse_ls_files_eol(self._ls_files_eol())
        seen = {suffix: 0 for suffix in _WORKTREE_EOL_FLOORS}
        for path, _worktree in rows:
            suffix = path_suffix(path)
            if suffix in seen:
                seen[suffix] += 1
        for suffix, floor in _WORKTREE_EOL_FLOORS.items():
            self.assertGreaterEqual(
                seen[suffix], floor,
                f"`{suffix}` 的行尾掃描面只有 {seen[suffix]} 支（下限 {floor}）——該副檔名的"
                "射程疑似被縮小。🔴 下限刻意**逐副檔名**：一個吃得下整體的總數，會讓"
                "「某一個副檔名整片消失、另一個還在」照樣過關，而那正是本閘要抓的形態",
            )
        problems = worktree_eol_problems(rows)
        self.assertEqual(
            problems, [],
            "工作樹行尾與政策不符。🔴 `git status` 對這種漂移**結構上看不見**"
            "（兩側套同一份正規化規則），`git add` 之後連唯一的幽靈 `M` 列都會消失；"
            "修法：讓 PostToolUse 的 `AutoClaude/tools/hooks/check_ps1_encoding.py` "
            "再跑一次（`.ps1` 方向），或以正確行尾重存：\n" + "\n".join(problems),
        )

    # ── 紅綠自證（合成列，不動磁碟）────────────────────────────────────────────

    def test_the_parser_reads_the_worktree_column_not_the_index_column(self) -> None:
        """最關鍵的一題：讀錯欄位會讓整條閘門恆綠（index 側 `.ps1` 恆為 lf）。"""
        line = "i/lf    w/crlf  attr/text eol=crlf    \ttools/x.ps1"
        self.assertEqual(parse_ls_files_eol(line), [("tools/x.ps1", "crlf")])
        self.assertEqual(worktree_eol_problems(parse_ls_files_eol(line)), [])

    def test_an_lf_ps1_and_a_crlf_sh_both_turn_red(self) -> None:
        for path, worktree in (("tools/a.ps1", "lf"), ("tools/b.psm1", "mixed"),
                               ("tools/c.sh", "crlf"), ("tools/d.bash", "mixed")):
            with self.subTest(path=path):
                self.assertEqual(
                    len(worktree_eol_problems([(path, worktree)])), 1,
                    f"{path} 的 `w/{worktree}` 沒被判紅 ⇒ 該方向零鑑別力")

    def test_out_of_scope_suffixes_and_empty_files_are_green(self) -> None:
        """假紅會逼下一輪把整條閘關掉：政策外副檔名與空檔一律放行。"""
        self.assertEqual(worktree_eol_problems([("docs/a.md", "lf")]), [])
        self.assertEqual(worktree_eol_problems([("tools/a.py", "crlf")]), [])
        self.assertEqual(worktree_eol_problems([("tools/empty.ps1", "none")]), [])

    def test_the_policy_table_covers_both_directions(self) -> None:
        """政策表不得只剩一個方向——單向表會讓「對稱」這個設計意圖靜默消失。"""
        self.assertEqual(set(_WORKTREE_EOL_POLICY.values()), {"crlf", "lf"})
        self.assertIn(".ps1", _WORKTREE_EOL_POLICY)
        self.assertIn(".sh", _WORKTREE_EOL_POLICY)


class TestWorktreeEolPolicyIsMeasuredFromGitattributes(unittest.TestCase):
    """政策映射必須是 `.gitattributes` 的**現查值**，不是抄本（R79 四方複審 SD）。

    被守的缺陷：R79 落地的版本是一份手抄表，且**在落地當下就已經不完整**——同樣宣告
    `eol=crlf` 的 `.cmd`／`.bat` 不在表裡。這一類漏看用「再讀一次表」永遠找不出來，
    因為漏掉的那一格在表裡不存在；唯一有效的判準是拿它去跟真正的持有者對帳。
    """

    def setUp(self) -> None:
        self.declared = declared_eol(
            _GITATTRIBUTES_PATH.read_text(encoding="utf-8"))

    def test_the_parser_really_reads_the_current_gitattributes(self) -> None:
        """自錨：解析器垮掉（正則寫壞／檔案改名）時，下面每一條都會變成「對空氣全綠」。"""
        self.assertGreaterEqual(
            len(self.declared), 10,
            f"只解析出 {len(self.declared)} 條 eol 宣告 ⇒ 解析器疑似失效：{self.declared}")
        for suffix, eol in ((".ps1", "crlf"), (".sh", "lf"), (".cmd", "crlf")):
            self.assertEqual(self.declared.get(suffix), eol,
                             f"`.gitattributes` 對 {suffix} 的宣告解析成 "
                             f"{self.declared.get(suffix)!r}（預期 {eol!r}）")

    def test_every_crlf_declaration_is_in_scope(self) -> None:
        """缺陷本體那一向：`.gitattributes` 宣告 `eol=crlf` 的每一格都必須在射程內。

        R79 落地時漏掉的 `.cmd`／`.bat` 就是被這一向抓到的。
        """
        crlf = {s for s, e in self.declared.items() if e == "crlf"}
        self.assertEqual(
            sorted(crlf - set(_WORKTREE_EOL_POLICY)), [],
            "這些副檔名在 `.gitattributes` 宣告了 CRLF，卻不在本閘射程內 ⇒ 它們的工作樹"
            "行尾漂移**沒有任何人看得見**（`git status` 對這種漂移結構上盲）",
        )

    def test_every_policy_cell_equals_the_declaration(self) -> None:
        """反向：表內每一格的值都必須等於 `.gitattributes` 的宣告（不得自行改值）。"""
        mismatched = {
            suffix: (eol, self.declared.get(suffix))
            for suffix, eol in _WORKTREE_EOL_POLICY.items()
            if self.declared.get(suffix) != eol
        }
        self.assertEqual(mismatched, {}, f"政策與宣告不一致（本閘值, 宣告值）：{mismatched}")

    def test_the_policy_follows_the_declaration_instead_of_a_copy(self) -> None:
        """判準自證：換一份 `.gitattributes` 進去，映射必須跟著動。

        少了這一支，上面兩條在「政策其實是寫死的、只是剛好與現況相符」時仍全綠——
        那正是本 finding 的原始狀態（表與宣告當時對得上，只是少了兩格）。
        """
        fake = ("* text=auto eol=lf\n"
                "# *.ignored text eol=crlf   ← 註解行不得被讀成宣告\n"
                "*.sh   text eol=crlf\n"
                "*.zzz  text eol=crlf\n"
                "*.py   text eol=lf\n")
        policy = worktree_eol_policy(declared_eol(fake))
        self.assertEqual(policy.get(".sh"), "crlf",
                         "LF 側的值也必須取自宣告，不得寫死 ⇒ 這一格證明它不是抄本")
        self.assertEqual(policy.get(".zzz"), "crlf",
                         "新宣告的 CRLF 副檔名沒有自動進射程 ⇒ 又需要有人記得同步第二份表")
        self.assertNotIn(".ignored", policy, "註解行被讀成宣告")
        self.assertNotIn(".py", policy,
                         "LF 側不得全收（見 `_EOL_LF_SCOPE`：全收會把主題擴成全庫文字檔）")
        # 反向的代價要說清楚：把 `.ps1` 宣告成 LF，它會整個**掉出**射程（不是變成 LF 政策）
        # ——這正是上面 `test_the_two_p0_directions_are_pinned` 那道止血點在守的事。
        dropped = worktree_eol_policy(declared_eol("*.ps1 text eol=lf\n"))
        self.assertNotIn(".ps1", dropped)

    def test_the_two_p0_directions_are_pinned(self) -> None:
        """現查式 SSOT 的代價是「來源被改壞就跟著壞」——這一支是它的止血點。

        `.sh` 被改成 CRLF 在 Docker／act 內會 `$'\\r': command not found`（取證紀律 #8），
        `.ps1` 缺 CRLF 則是本閘立案的理由。這兩格無論 `.gitattributes` 怎麼寫都不准翻。
        """
        self.assertEqual(_WORKTREE_EOL_POLICY.get(".ps1"), "crlf")
        self.assertEqual(_WORKTREE_EOL_POLICY.get(".sh"), "lf")

    def test_every_floor_names_a_suffix_in_scope(self) -> None:
        """逐副檔名下限不得指向射程外的副檔名（那種下限永遠是 0 支、等於沒有）。"""
        orphan = sorted(set(_WORKTREE_EOL_FLOORS) - set(_WORKTREE_EOL_POLICY))
        self.assertEqual(orphan, [], f"下限表指向射程外的副檔名：{orphan}")

    def test_the_ps1_hooks_private_crlf_targets_match_the_declaration(self) -> None:
        """DEF-101-950：hook 側（check_ps1_encoding.py）私藏的 CRLF 知識對 SSOT 對帳。

        本閘政策值自 R79 起已現查 `.gitattributes`（上方 `worktree_eol_policy`），字面
        複本只剩 hook 那一家（`PS_SUFFIXES` ＋ 位元組展開，屬實作細節可留——R80 證據檔
        S5-09 裁決）；本格把殘餘的那一家釘回 SSOT：hook 正規化成 CRLF 的每個副檔名，
        都必須在 `.gitattributes` 逐字宣告 `eol=crlf`，兩家從此不可能靜默漂移。
        """
        hook = (_REPO_ROOT / "AutoClaude" / "tools" / "hooks" / "check_ps1_encoding.py")
        mo = re.search(r"^PS_SUFFIXES\s*=\s*\{([^}]*)\}",
                       hook.read_text(encoding="utf-8"), re.M)
        self.assertIsNotNone(mo, "hook 的 PS_SUFFIXES 常數消失／改形 ⇒ 對帳基底失效")
        targets = set(re.findall(r'"(\.[a-z0-9]+)"', mo.group(1)))
        self.assertGreaterEqual(len(targets), 3, f"抽到的 hook 射程可疑地小：{targets}")
        undeclared = {s: self.declared.get(s) for s in sorted(targets)
                      if self.declared.get(s) != "crlf"}
        self.assertEqual(undeclared, {},
                         "hook 會把這些副檔名就地改寫成 CRLF，但 `.gitattributes` 並未"
                         f"如此宣告（宣告值）：{undeclared}——兩家字面已漂移（DEF-101-950）")


# ══════════════════════════════════════════════════════════════════════════════
# R79（S-xplat）— 「別人開著這個檔」在 Windows 會炸掉的**目錄項原語**
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體與誠實劃界全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R79 Windows 目錄項原語 WHY〉節。
#: 原語 → 本機實測到的 winerror（值為 None＝本輪未逐一實測，僅登記形態）。
_WINDOWS_OPEN_FILE_HOSTILE_PRIMITIVES: dict[str, int | None] = {
    "os.replace": 5,     # 覆寫「被開著」的目的檔（本節主角，R79 首次登記）
    "os.unlink": 32,     # 既有知識（DEF-101 系列已登記的那一個）
    "os.rename": None,
    "os.renames": None,
    "shutil.move": None,
    "shutil.rmtree": None,
}
#: 走 AST 抓得到的**檔案系統**目錄項原語（`shutil.rmtree`／`os.unlink` 屬刪除語意，
#: 已由既有知識覆蓋，本掃描只管「覆寫既有目的檔」這一族，避免與既有鎖射程重疊）。
_DIRENT_PRIMITIVES: frozenset[str] = frozenset(
    {"os.replace", "os.rename", "os.renames", "shutil.move"})
#: `<x>.replace(<單一引數>)`／`<x>.rename(...)` 這種 Path 方法形態的**排除**清單：
#: 這幾個模組的同名函式與檔案系統無關，納入即假紅（`dataclasses.replace(obj)` 實測
#: 會被單純的「1 個引數」啟發式命中）。
_NON_PATH_REPLACE_OWNERS: frozenset[str] = frozenset({"dataclasses", "attr", "attrs", "copy"})
#: 存量：**live 樹**內未處置 `PermissionError`／`OSError` 的站點數。
#: 判準是雙向精確比對（同本檔其餘欠債表的理由）。
#: 🔴 掃描面刻意不含凍結版 v0.01~v0.29，兩個理由缺一不可：① Copy-on-Evolve 禁改
#:   凍結版，那裡結構上不會出現「新寫的」違規，掃它得不到可行動的訊號；② 當回合
#:   實測含凍結版時整支測試要 **133 秒**（凍結版 1,131 筆是同一批程式碼被複製 29 次），
#:   而護欄層的執行時間本身已是本輪一筆獨立 finding。凍結版的那 1,131 筆是**已量到、
#:   刻意不進帳**的事實，不是沒看見。
#: DEF-200-202 四方複審修復窗口：`QuotaGateIsWiredToTheBurnPathTest` 新增回歸測試
#: 多用了一次既有 fixture 慣用句式 `<Path>.replace(qg.quota_cache_path())`
#: （同檔既有測試已大量使用同一句式，未另立新形態）。
_DIRENT_UNGUARDED_DEBT: dict[str, int] = {"live": 42}


def dirent_primitive_sites(source: str, rel: str) -> list[tuple[str, int, str, bool]]:
    """(檔, 行號, 原語, 是否已處置 PermissionError/OSError)。純函式，供紅綠自證共用。"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    parent, _slot, _classes = _ast_scope_index(tree)
    out: list[tuple[str, int, str, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted_name(node.func)
        if name is None:
            continue
        if name in _DIRENT_PRIMITIVES:
            label = name
        elif (name.rsplit(".", 1)[-1] in {"replace", "rename"}
              and len(node.args) == 1 and not node.keywords
              and name.rsplit(".", 1)[0] not in _NON_PATH_REPLACE_OWNERS
              and "." in name):
            label = f"Path.{name.rsplit('.', 1)[-1]}"
        else:
            continue
        handled = False
        cur: ast.AST = node
        while cur in parent:
            owner = parent[cur]
            if isinstance(owner, ast.Try):
                for handler in owner.handlers:
                    text = ast.unparse(handler.type) if handler.type else ""
                    if "PermissionError" in text or "OSError" in text:
                        handled = True
            cur = owner
        out.append((rel, node.lineno, label, handled))
    return out


# ── R81 XPL-S1-04：詞彙表本身的後設鎖（手抄封閉清單只准長大）───────────────────
#: 落地當回合的實測規模。判準是**單邊**（只准上升）而非精確比對：新增一族／補齊一個
#: 家族是隨時該做的事，不該逼人回來改常數；但**縮表**必須被看見——把一個 attr 從表上
#: 拿掉，掃描器會照跑、照綠、照回報命中數，只是那一族從此不在分母裡（XPL-S1-04 的
#: 缺陷本體就是這個形狀，而它靜靜活了很多輪）。
#: 落地當回合實測：owners=4（os／signal／ctypes／subprocess）、attrs=71
#: （16／29／10／16）。下限逐字取實測值＝零餘裕，縮一個就紅。
_FOREIGN_VOCAB_FLOOR_OWNERS = 4
_FOREIGN_VOCAB_FLOOR_ATTRS = 71


class TestForeignApiVocabularyOnlyGrows(unittest.TestCase):
    """手抄封閉清單的後設鎖：owner 數與 attr 數只准上升（覆蓋率棘輪同精神）。"""

    def test_the_owner_table_never_shrinks(self) -> None:
        owners = sorted(_FOREIGN_ATTR_TABLE)
        attrs = sum(len(v) for v in _FOREIGN_ATTR_TABLE.values())
        self.assertGreaterEqual(
            len(owners), _FOREIGN_VOCAB_FLOOR_OWNERS,
            f"owner 少了（現有 {owners}）——拿掉一族不會有任何東西轉紅，"
            "那正是本鎖存在的理由。刻意縮表請連同下限一起改並寫明 WHY")
        self.assertGreaterEqual(
            attrs, _FOREIGN_VOCAB_FLOOR_ATTRS,
            f"詞彙表 attr 數 {attrs} < 下限 {_FOREIGN_VOCAB_FLOOR_ATTRS} ⇒ 掃描面靜默縮小")

    def test_every_owner_has_at_least_one_entry_and_a_legal_direction(self) -> None:
        """反空殼：登記了 owner 卻是空 dict ＝分母 +1、鑑別力 0。"""
        for owner, table in sorted(_FOREIGN_ATTR_TABLE.items()):
            with self.subTest(owner=owner):
                self.assertTrue(table, f"{owner} 的 attr 表是空的 ⇒ 空殼登記")
                self.assertEqual(
                    {side for side in table.values()} - {"POSIX-only", "Windows-only"},
                    set(), f"{owner} 有不合法的方向字串（只認兩種）")

    def test_each_owner_family_actually_fires(self) -> None:
        """反空殼之二：每一族都要能用一段合成程式碼真的打中（登記 ≠ 有牙）。"""
        for owner, table in sorted(_FOREIGN_ATTR_TABLE.items()):
            attr = sorted(table)[0]
            with self.subTest(owner=owner, attr=attr):
                off, _ = scan_foreign_platform_api(
                    f"def f():\n    return {owner}.{attr}\n", _INJECTION_TARGET_REL)
                self.assertTrue(off, f"{owner}.{attr} 登記了卻打不中 ⇒ 空殼")


# ══════════════════════════════════════════════════════════════════════════════
# R79（S-xplat）— exec bit：Windows 上唯一還看得見的那個管道＝**git 索引模式**
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R79 exec bit 索引模式判準
# WHY〉節。
_INDEX_MODE_EXEC = "100755"
#: 文件裡「教人裸跑」的形態：行首或空白後的 `./<path>.sh`（反引號／程式碼區塊皆同）。
_BARE_SH_INVOCATION_RE = re.compile(r"(?<![\w./-])\./([A-Za-z0-9_./-]+\.sh)\b")
#: 存量欠債：**凍結版**（v0.01~v0.29）`tools/README.md` 內教人裸跑、而標的索引模式
#: 不是 100755 的站點數。R79 實測 30 支 README × 3 行＝90，其中 LATEST 那一支
#: （3 筆）於本輪修掉 ⇒ 29 × 3 = 87 留在凍結版。
#: 🔴 為何只修 LATEST：Copy-on-Evolve 政策禁止改凍結版（歷來三次例外都經掌舵者
#:   明文核准）。這 87 筆是**可見的欠債**，不是豁免。
#: 判準是**雙向精確比對**：多一筆＝新增了同型缺陷；少一筆＝有人動了凍結版
#: （那本身就是需要被看見的事件），兩向都必須有人回來改這個數字。
_BARE_SH_DOC_DEBT_FROZEN = 87


def index_modes(repo_root: Path) -> dict[str, str]:
    """`git ls-files -s` → {repo 相對路徑: 模式}。空 dict ＝取數管道壞掉。"""
    proc = git_paths.run(repo_root, "ls-files", "-s")
    if proc.returncode != 0:
        return {}
    modes: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        head, sep, path = line.partition("\t")
        if sep and head.split():
            modes[path.strip()] = head.split()[0]
    return modes


def resolve_doc_script(doc_rel: str, script_rel: str, tracked: set[str]) -> str | None:
    """把文件裡的 `./x.sh` 對應到一支 tracked 檔；對應不到回 None（＝不判）。

    刻意只判「對應得到 repo 內真實檔案」的站點：範本／情境樣稿裡大量出現的
    `./scripts/deploy/xxx.sh` 講的是**讀者自己專案**的腳本，判它們是假紅，而假紅
    會逼下一輪把整條鎖關掉（本檔既有判準一貫的取捨）。
    """
    parts = doc_rel.split("/")
    candidates = ["/".join(parts[:-1] + [script_rel]) if len(parts) > 1 else script_rel,
                  script_rel]
    candidates += ["/".join(parts[:i]) + "/" + script_rel for i in range(len(parts) - 1, 0, -1)]
    for cand in candidates:
        cand = cand.replace("//", "/")
        if cand in tracked:
            return cand
    return None


#: 🔴 DEF-101-205（R80 落地）：ONBOARDING §6「執行權限政策」那句散文即 SSOT，本正則把
#: 「755 入庫」範圍的那一段切出來。刻意**不**在程式裡另寫一份清單——那就是本 repo 反覆在
#: 治的「同一份知識住兩個家、只有一個家被改」（判例 DEF-101-778）。切段而非掃全句是必要的：
#: 同一句後半段還寫著「其他 `.sh` 工具…索引 644」，把整句的反引號都收進來會把 644 那一組
#: 也算成 755 白名單，判準當場失去鑑別力。錨定在 `範圍＝**…**` 這個**粗體跨度**而不是
#: 「到下一個『；其他』為止」：落地時實測後者會多吃到緊接在後的 rationale 括號，把
#: `/bin/bash`（那裡在解釋 plist 以誰為執行檔）誤收成一個 755 白名單項。
_EXEC_SCOPE_PROSE_RE = re.compile(r"「755 入庫」範圍＝\*\*(?P<scope>.*?)\*\*")


def exec_bit_prose_scope(onboarding_text: str) -> tuple[tuple[str, ...], str | None]:
    """從 ONBOARDING §6 政策句抽出「允許 100755」的路徑 token；抽不到回 `((), 說明)`。

    抽不到一律 fail-loud：靜默退回空集合會讓下面的雙向比對變成「每一支 755 都違規」
    （一次全紅），靜默放行則讓整道鎖蒸發——兩種都是壞的失敗模式（手法比照
    `tools/check_defect_log_crossref.py::_prose_status_first_words`）。

    🔴 反引號一律以**成對切分**取（`split("`")[1::2]`）而不是用正則抓
    `` `([^`]*/[^`]*)` ``：後者落地時實測會把「上一個 code span 的收尾反引號」跟
    「下一個的起始反引號」配成一對，於是兩個 token 之間那段散文（只要含一個 `/`）
    被當成一個路徑 token 收進白名單。奇數個反引號＝散文寫壞，同樣 fail-loud。
    """
    m = _EXEC_SCOPE_PROSE_RE.search(onboarding_text)
    if m is None:
        return (), (
            "ONBOARDING.md 抽不到「「755 入庫」範圍＝**…**」那個粗體跨度 —— exec bit 政策"
            "的權威散文不存在或被改寫，本判準便無從綁定。請在 §6「執行權限政策」條目補回"
            "該句式，或同步 _EXEC_SCOPE_PROSE_RE 的抽取樣式"
        )
    parts = m.group("scope").split("`")
    if len(parts) % 2 == 0:
        return (), (
            "ONBOARDING §6「755 入庫」範圍那段的反引號**數量為奇數**（未成對）⇒ 無法"
            "可靠切出 code span。請把該段的反引號補成對"
        )
    return tuple(dict.fromkeys(t for t in parts[1::2] if "/" in t)), None


def exec_bit_scope_problems(
    modes: dict[str, str], scope: tuple[str, ...]
) -> list[str]:
    """雙向比對：索引 100755 的集合 ↔ 散文具名的 755 範圍（純函式，可構造輸入驗牙）。

    兩向缺一都不成鎖：
      · 只判①（每支 755 都落在範圍內）⇒ 散文可以無限放寬，多寫幾個目錄就永遠綠。
      · 只判②（每個 token 都真的有 755）⇒ 範圍外冒出一支新 755 一句話都不會說，
        而那正是 `DEF-101-205` 原本擔心的「漂移無訊號」。
    """
    execs = sorted(p for p, mode in modes.items() if mode == _INDEX_MODE_EXEC)
    problems: list[str] = []

    def _covered(path: str) -> bool:
        return any(
            path.startswith(tok) if tok.endswith("/") else path == tok for tok in scope
        )

    for path in execs:
        if not _covered(path):
            problems.append(
                f"{path}：索引模式 100755，但不落在 ONBOARDING §6 政策句具名的範圍內"
                f"（現行範圍＝{list(scope)}）。二擇一：① 這支本來就不該帶 exec bit ⇒ "
                f"`git update-index --chmod=-x {path}`；② 它確實需要 exec bit ⇒ 先去改"
                f"**散文**（ONBOARDING §6 那一句才是 SSOT），本判準會自動跟上"
            )
    for tok in scope:
        if not any(
            (p.startswith(tok) if tok.endswith("/") else p == tok) for p in execs
        ):
            problems.append(
                f"{tok}：ONBOARDING §6 政策句把它列進「755 入庫」範圍，但索引裡該處"
                f"**一支 100755 都沒有** ⇒ 散文已過期。請把它從政策句移除"
                f"（留著就是日後無聲把 755 加回去的額度）"
            )
    return problems


def bare_sh_doc_offenders(
    docs: dict[str, str], modes: dict[str, str]
) -> list[tuple[str, int, str]]:
    """(文件, 行號, 標的) —— 文件教人裸跑、而標的索引模式不是 100755 的站點。"""
    tracked = set(modes)
    out: list[tuple[str, int, str]] = []
    for doc_rel, text in docs.items():
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in _BARE_SH_INVOCATION_RE.finditer(line):
                target = resolve_doc_script(doc_rel, match.group(1), tracked)
                if target is not None and modes[target] != _INDEX_MODE_EXEC:
                    out.append((doc_rel, lineno, target))
    return out


@functools.lru_cache(maxsize=1)
def _live_sdd_prefix() -> str:
    """`AISDLC_SDD/<LATEST>/`——**快取**：`_latest_root()` 走 subprocess 解析 SSOT，
    逐檔呼叫會讓全庫掃描從數十秒暴增到數分鐘（本輪實測踩過一次）。"""
    return f"AISDLC_SDD/{_latest_root().name}/"


def _is_frozen_sdd_path(rel: str) -> bool:
    """凍結版 SDD 樹（v0.01~v0.NN，LATEST 除外）——Copy-on-Evolve 禁改的那一批。"""
    return rel.startswith("AISDLC_SDD/AISDLC_SDD_v0.") and not rel.startswith(
        _live_sdd_prefix())


class TestDirEntryPrimitivesAreAccountedFor(unittest.TestCase):
    """目錄項原語在 Windows 的「檔案被開著」落差（見上方區段 WHY）。"""

    def test_the_platform_gap_is_real_and_re_measurable(self) -> None:
        """兩個平台各自斷言自己那一半——刻意**不用 skip**：這一題在 POSIX 上不是
        「跳過」，而是「必須成功」，那正是落差本身。（用 skipUnless 會讓 POSIX 側
        一格覆蓋都沒有，也會多一個 skip 站點要進別包的普查表。）
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = Path(tmpdir) / "ledger.yaml"
            src = Path(tmpdir) / "ledger.yaml.tmp"
            dst.write_text("old\n", encoding="utf-8")
            src.write_text("new\n", encoding="utf-8")
            with open(dst, encoding="utf-8"):        # 第三方**純讀者**持有 handle
                if sys.platform == "win32":
                    with self.assertRaises(PermissionError) as ctx:
                        os.replace(src, dst)
                    self.assertEqual(
                        ctx.exception.winerror,
                        _WINDOWS_OPEN_FILE_HOSTILE_PRIMITIVES["os.replace"],
                        "winerror 變了 ⇒ 上表登記的實測值已過期，請重新量並改表")
                else:
                    os.replace(src, dst)            # POSIX：恆成功，這就是落差
                    self.assertEqual(dst.read_text(encoding="utf-8"), "new\n")

    def test_the_primitive_inventory_covers_both_known_error_codes(self) -> None:
        """「換一個原語連錯誤碼都換了」這句話必須留在可查的形態裡。"""
        codes = {k: v for k, v in _WINDOWS_OPEN_FILE_HOSTILE_PRIMITIVES.items()
                 if v is not None}
        self.assertEqual(codes, {"os.replace": 5, "os.unlink": 32})
        self.assertTrue(_DIRENT_PRIMITIVES <= set(_WINDOWS_OPEN_FILE_HOSTILE_PRIMITIVES),
                        "掃描面出現了清單沒登記的原語 ⇒ 兩處會漂移")

    def test_unguarded_site_census_matches_the_ledger(self) -> None:
        skip_parts = {"__pycache__", ".git", ".venv", "venv", ".pytest_cache",
                      ".ruff_cache", ".mypy_cache", "node_modules"}
        # 🔴 R79 收斂包：**虛擬環境改以 `pyvenv.cfg` 這個標記偵測，不靠目錄名**。
        # 修前實況（當回合實測）：本掃描面是檔案系統 rglob，而排除清單只列了 `.venv`／`venv`
        # 兩個**我們剛好想得到的名字**；收斂包為了回填 ONBOARDING 快照建了一個叫
        # `cleanvenv` 的乾淨環境（gitignored、政策上就是該建的），這道普查的實測值當場由
        # 41 跳到 58 而閘門轉紅。也就是說這個數字是「這台機器上剛好有哪幾個 venv」的函數
        # ——換一台機器、換一個名字就換一個答案，而它被拿來當**雙向精確比對**的基準。
        # `pyvenv.cfg` 是 PEP 405 定義的 venv 根標記，與命名無關，也不必逐檔問 git。
        skip_roots = {
            cfg.parent for cfg in _REPO_ROOT.glob("*/pyvenv.cfg")
        } | {cfg.parent for cfg in _REPO_ROOT.glob("*/*/pyvenv.cfg")}
        census = {"live": 0}
        scanned = 0
        for py in _REPO_ROOT.rglob("*.py"):
            if skip_parts & set(py.parts):
                continue
            if any(root in py.parents for root in skip_roots):
                continue
            if _is_frozen_sdd_path(py.relative_to(_REPO_ROOT).as_posix()):
                continue
            scanned += 1
            data = py.read_bytes()
            # 先以 bytes 快篩再 AST 解析：全庫 .py 一次全解析實測要數分鐘，而帶這幾個
            # 名字的檔只有極少數。快篩的字面值是**必要條件**（AST 上的呼叫必然寫得出
            # 這個名字），不會讓射程縮小。
            if not any(tok in data for tok in (b"replace(", b"rename(", b"move(")):
                continue
            rel = py.relative_to(_REPO_ROOT).as_posix()
            for _rel, _ln, _prim, handled in dirent_primitive_sites(
                    data.decode("utf-8", errors="replace"), rel):
                if not handled:
                    census["live"] += 1
        self.assertGreaterEqual(
            scanned, 780,   # R79 實測 867 支 live `.py`（全庫 5,478 支裡其餘皆在凍結版）
            f"掃描面只有 {scanned} 支 .py——射程疑似被縮小（凍結版排除是刻意的，"
            "live 樹被排掉不是）")
        self.assertEqual(
            census, dict(_DIRENT_UNGUARDED_DEBT),
            "未處置站點數與帳不符。多一筆＝新增了一個在 Windows 上會被『別人開著這個"
            "檔』炸掉、且沒有任何處置的站點；少一筆＝有人修掉了，請把數字改小："
            f"實測 {census}",
        )

    # ── 紅綠自證（合成樣本）────────────────────────────────────────────────────

    def test_an_unhandled_replace_is_reported_and_a_handled_one_is_not(self) -> None:
        bare = "def f(tmp, path):\n    os.replace(tmp, path)\n"
        self.assertEqual(dirent_primitive_sites(bare, "x.py"),
                         [("x.py", 2, "os.replace", False)])
        handled = ("def f(tmp, path):\n    try:\n        os.replace(tmp, path)\n"
                   "    except PermissionError:\n        pass\n")
        self.assertEqual(dirent_primitive_sites(handled, "x.py"),
                         [("x.py", 3, "os.replace", True)])

    def test_a_timeouterror_only_handler_does_not_count_as_handling(self) -> None:
        """實際站點的形狀：包住它的 try 只捕 file_lock 的 TimeoutError。"""
        source = ("def f(tmp, path):\n    try:\n        os.replace(tmp, path)\n"
                  "    except TimeoutError:\n        pass\n")
        self.assertEqual(dirent_primitive_sites(source, "x.py")[0][3], False)

    def test_non_filesystem_replace_lookalikes_are_not_counted(self) -> None:
        """假紅會逼下一輪把整條鎖關掉：`dataclasses.replace(obj)` 與字串 replace 不算。"""
        for source in ("import dataclasses\n\n\ndef f(o):\n    return dataclasses.replace(o)\n",
                       'def f(s):\n    return s.replace("a", "b")\n'):
            with self.subTest(source=source):
                self.assertEqual(dirent_primitive_sites(source, "x.py"), [])

    def test_path_method_form_is_in_scope(self) -> None:
        """`tmp.replace(path)`（pathlib 形態）是本 repo 最常見的寫法，不得漏掃。"""
        self.assertEqual(
            dirent_primitive_sites("def f(tmp, path):\n    tmp.replace(path)\n", "x.py"),
            [("x.py", 2, "Path.replace", False)])


class TestExecBitIsGovernedViaTheGitIndex(unittest.TestCase):
    """exec bit 治理：只讀 git 索引模式（見上方區段 WHY）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.modes = index_modes(_REPO_ROOT)

    def test_the_index_mode_channel_is_alive(self) -> None:
        """取數管道自證：壞掉時回空 dict，而空 dict 會讓下面兩題結構上恆綠。"""
        self.assertGreaterEqual(
            len(self.modes), 20000,
            f"`git ls-files -s` 只回 {len(self.modes)} 列——取數管道壞掉，"
            "本節其餘判準全部失去意義")
        self.assertIn(
            _INDEX_MODE_EXEC, set(self.modes.values()),
            "全 repo 一支 100755 都沒有 ⇒ 判準的『正例』側無從成立")

    def test_the_index_exec_set_matches_the_onboarding_policy_sentence(self) -> None:
        """🔴 DEF-101-205 自訂的解鎖條件本體（R80 落地）。

        該列自 R14 起 open 逾五十輪，逐字寫著解鎖條件＝「以 `git ls-files -s` 取出 mode
        `100755` 的檔案集合，與 `ONBOARDING.md` §6 執行權限政策句具名的 755 清單逐項互比
        （散文即 SSOT），不符即 rc=1」。**取數管道早就有了**（本類別 R79 落地時就在讀
        `git ls-files -s`），缺的一直是這一項比對——所以政策句與索引之間的漂移到今天為止
        一個訊號都沒有。

        Rule 9（為何這件事重要，而不只是「模式好看」）：exec bit 這一維在 Windows 上
        **結構性不可見**（本機 `core.filemode=false`，模式從不出現在 `git status`／
        `git diff`／任何 pre-commit 掃描裡），於是「哪支檔可以帶 755」這件事在本平台上
        只剩散文在守。散文不會轉紅。
        """
        scope, problem = exec_bit_prose_scope(
            (_REPO_ROOT / "ONBOARDING.md").read_text(encoding="utf-8")
        )
        self.assertIsNone(problem, problem)
        self.assertGreaterEqual(
            len(scope), 2,
            f"政策句只抽到 {list(scope)} —— 少於兩個 token 幾乎必然是抽取樣式壞掉，"
            "而不是政策真的縮到這麼小")
        self.assertEqual(exec_bit_scope_problems(self.modes, scope), [],
                         "\n".join(exec_bit_scope_problems(self.modes, scope)))

    def test_the_exec_scope_criterion_is_red_in_both_directions(self) -> None:
        """紅綠自證（合成輸入，不碰磁碟）：兩向各證一次，缺一向就不是雙向鎖。"""
        scope = ("tools/git-hooks/", "AutoClaude/tools/run_local_nightly.sh")
        green = {
            "tools/git-hooks/pre-push": _INDEX_MODE_EXEC,
            "AutoClaude/tools/run_local_nightly.sh": _INDEX_MODE_EXEC,
            "tools/x.sh": "100644",
        }
        self.assertEqual(exec_bit_scope_problems(green, scope), [])
        # 向①：範圍外冒出一支新的 100755。
        rogue = dict(green, **{"tools/x.sh": _INDEX_MODE_EXEC})
        self.assertEqual(len(exec_bit_scope_problems(rogue, scope)), 1)
        # 向②：散文列了一個「已經沒有任何 755」的住所 ⇒ 過期，必須被要求刪掉。
        self.assertEqual(
            len(exec_bit_scope_problems(green, (*scope, "AISDLC_SDD/.githooks/"))), 1)

    def test_the_prose_extractor_fails_loud_instead_of_silently_allowing(self) -> None:
        """散文被改寫時必須 fail-loud——靜默回空集合＝整道鎖蒸發（軟出口）。"""
        scope, problem = exec_bit_prose_scope("完全沒有那句政策的文件內容")
        self.assertEqual(scope, ())
        self.assertIsNotNone(problem)
        # 切段是必要的：不切段就會把同一句後半「其他 `.sh` 工具…索引 644」也收進白名單。
        scope, problem = exec_bit_prose_scope(
            "「755 入庫」範圍＝**`a/b/`**；其他 `c/d.sh` 工具一律索引 644")
        self.assertIsNone(problem)
        self.assertEqual(scope, ("a/b/",))
        # 成對切分：兩個 token 之間那段含 `/` 的散文**不得**被配成第三個 token。
        scope, problem = exec_bit_prose_scope(
            "「755 入庫」範圍＝**`a/b/` 由 x 執行、`bash` 呼叫 e/f 者除外＋`c/d.sh`**")
        self.assertIsNone(problem)
        self.assertEqual(scope, ("a/b/", "c/d.sh"))
        # 反引號未成對 ⇒ fail-loud，不得靜默給出一組看似合理的 token。
        scope, problem = exec_bit_prose_scope("「755 入庫」範圍＝**`a/b/ 忘了收尾**")
        self.assertEqual(scope, ())
        self.assertIsNotNone(problem)

    def test_docs_that_teach_bare_sh_invocation_point_at_executable_files(self) -> None:
        docs: dict[str, str] = {}
        for rel in self.modes:
            if not rel.lower().endswith(".md"):
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            data = path.read_bytes()
            if b"./" not in data or b".sh" not in data:  # 先以 bytes 快篩再解碼
                continue
            docs[rel] = data.decode("utf-8", errors="replace")
        offenders = bare_sh_doc_offenders(docs, self.modes)
        live = [o for o in offenders if not _is_frozen_sdd_path(o[0])]
        frozen = [o for o in offenders if _is_frozen_sdd_path(o[0])]
        self.assertEqual(
            [f"{d}:{n} -> {t}" for d, n, t in live], [],
            "文件教 mac/Linux 使用者裸跑一支索引模式不是 100755 的腳本 ⇒ 對方一 clone "
            "就 `Permission denied`（rc=126），而 Windows 側因 core.filemode=false "
            "永遠看不到這件事。修法：把 `./x.sh` 改寫成 `bash x.sh`（與同批文件其餘"
            "各處一致），或以 `git update-index --chmod=+x` 把該檔改成 100755：\n"
            + "\n".join(f"{d}:{n} -> {t}" for d, n, t in live),
        )
        self.assertEqual(
            len(frozen), _BARE_SH_DOC_DEBT_FROZEN,
            f"凍結版存量由 {_BARE_SH_DOC_DEBT_FROZEN} 變成 {len(frozen)}。"
            "多一筆＝新增同型缺陷；少一筆＝有人動了 Copy-on-Evolve 禁改的凍結版"
            "（那本身就是必須被看見的事件）。兩向都請回來改這個數字並說明理由。",
        )

    def test_executable_shell_scripts_start_with_a_shebang_and_carry_no_bom(self) -> None:
        """`[ -x ]` 在 Windows 的 Git Bash 上是**檔首內容猜測**（當回合實測：加 BOM
        即由 EXECUTABLE 翻成 NOT-EXEC，且 `chmod +x` 動不了它）⇒ 檔首多任何位元組，
        dispatcher 那道 `if [ -x "$target" ]` 就靜默 exit 0，整條 hook 鏈無聲失效。
        這是那條治理鏈在 Windows 側唯一還測得到的一半。
        """
        problems: list[str] = []
        for rel, mode in sorted(self.modes.items()):
            if mode != _INDEX_MODE_EXEC:
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            # 刻意不寫 `[:N]`：寫死的切片長度默默假設「我要看的東西一定在前 N 個
            # 位元組內」，而 `startswith` 本來就只比對前綴、不需要那個假設
            # （`test_archive_defect_log.py::TestNoAssertionSamplesALiveDocumentWholesale`
            #  在守這條紀律，R79 收斂包實測它會對 `[:4]` 轉紅）。
            head = path.read_bytes()
            if head.startswith(b"\xef\xbb\xbf"):
                problems.append(f"{rel}: 檔首有 UTF-8 BOM ⇒ Git Bash 的 `[ -x ]` 判為 NOT-EXEC")
            elif not head.startswith(b"#!"):
                problems.append(f"{rel}: 索引模式 100755 但檔首不是 `#!` ⇒ 同上")
        self.assertEqual(problems, [], "\n".join(problems))

    # ── 紅綠自證（合成輸入，不動磁碟）──────────────────────────────────────────

    def test_a_doc_pointing_at_a_100644_script_is_flagged(self) -> None:
        docs = {"tools/README.md": "跑 `./tools/x.sh -d ~/p` 即可\n"}
        modes = {"tools/README.md": "100644", "tools/x.sh": "100644"}
        self.assertEqual(bare_sh_doc_offenders(docs, modes),
                         [("tools/README.md", 1, "tools/x.sh")])
        modes["tools/x.sh"] = _INDEX_MODE_EXEC
        self.assertEqual(bare_sh_doc_offenders(docs, modes), [])

    def test_the_repo_approved_form_bash_x_sh_is_not_flagged(self) -> None:
        """對照組：`bash x.sh` 不需要 exec bit，判它是假紅。"""
        docs = {"a.md": "跑 `bash tools/x.sh` 即可\n"}
        self.assertEqual(bare_sh_doc_offenders(docs, {"a.md": "100644",
                                                      "tools/x.sh": "100644"}), [])

    def test_scripts_outside_the_repo_are_not_judged(self) -> None:
        """範本／樣稿講的是讀者自己專案的腳本，對應不到 tracked 檔 ⇒ 不判。"""
        docs = {"a.md": "./scripts/deploy/deploy-all.sh production\n"}
        self.assertEqual(bare_sh_doc_offenders(docs, {"a.md": "100644"}), [])

    def test_the_frozen_predicate_actually_separates_the_two_groups(self) -> None:
        latest = _latest_root().name
        self.assertTrue(_is_frozen_sdd_path("AISDLC_SDD/AISDLC_SDD_v0.01/tools/README.md"))
        self.assertFalse(_is_frozen_sdd_path(f"AISDLC_SDD/{latest}/tools/README.md"))
        self.assertFalse(_is_frozen_sdd_path("tools/README.md"))


#: `.editorconfig` 的 `.ps1` 區塊自述的機械執行者 → 它必須真的在談的主題關鍵詞。
#: 只斷言「檔案存在」抓不到「檔案在、但守的是別的東西」（R75 判過的形態：當時
#: 具名的是一支只管 BOM 的鎖，卻被寫在「行尾」那一列）。
_EDITORCONFIG_PS1_ENFORCERS: dict[str, tuple[str, ...]] = {
    "AutoClaude/tools/hooks/check_ps1_encoding.py": ("\\r\\n", "PS_SUFFIXES", "BOM"),
    "tools/tests/test_platform_neutral_paths.py": ("ls-files", "--eol", "crlf"),
    "tools/tests/test_ps1_bom.py": ("BOM", ".ps1"),
}


class TestEditorconfigPs1BlockNamesItsEnforcers(unittest.TestCase):
    """`.editorconfig` 的 `.ps1` 區塊不得是純裝飾——它自述的執行者必須真的在。

    缺陷本體（R79／D-ps1eol #32）：`end_of_line = crlf` 與 `charset = utf-8-bom`
    這兩行被三份文件各自宣告，而實際寫檔的工具兩項都不遵守；讀到任何一份的人都會
    合理推論「這件事有人在管」。R79 補上執行者之後，這支鎖負責讓那份自述**不能
    無聲過期**：具名檔被改名／刪掉／換成守別的主題的東西，都會在這裡紅。
    """

    _EDITORCONFIG = _REPO_ROOT / ".editorconfig"

    def test_the_ps1_block_declares_crlf_and_bom(self) -> None:
        text = self._EDITORCONFIG.read_text(encoding="utf-8")
        self.assertIn("[*.{ps1,psm1,psd1}]", text, "`.ps1` 區塊不見了")
        block = text.split("[*.{ps1,psm1,psd1}]", 1)[1].split("\n[", 1)[0]
        self.assertIn("end_of_line = crlf", block)
        self.assertIn("charset = utf-8-bom", block)

    def test_every_named_enforcer_exists_and_guards_its_topic(self) -> None:
        text = self._EDITORCONFIG.read_text(encoding="utf-8")
        problems: list[str] = []
        for rel, keywords in _EDITORCONFIG_PS1_ENFORCERS.items():
            if rel not in text:
                problems.append(f"{rel}：`.editorconfig` 已不再指名它——兩邊必須同步")
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                problems.append(f"{rel}：`.editorconfig` 指名了一個不存在的執行者（幽靈機械物）")
                continue
            body = path.read_text(encoding="utf-8", errors="replace")
            missing = [k for k in keywords if k not in body]
            if missing:
                problems.append(
                    f"{rel}：檔案在，但內容沒有在談它被指派的主題（缺 {missing}）"
                    "——「檔案存在」是必要條件不是充分條件")
        self.assertEqual(problems, [], "\n".join(problems))


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 — 雙向注入語料矩陣（M5 的可重跑載具；此前語料零落點、結構上不可逐輪比較）
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈雙向注入語料矩陣 WHY〉節。
_INJECTION_TARGET_REL = "AutoClaude/autoclaude/infra/adapters/injected_probe.py"
#: 本檔自身也在掃描面內，故語料中會被**行掃描型**判準命中的字面值一律拆寫。
_DRIVE_FRAG = "D" + ":/repo/out"
_PATHEXT_FRAG = "PATH" + "EXT"


def _injection_criteria() -> dict[str, Callable[[str, str], tuple[list[str], list[str]]]]:
    """本檔全部判準的統一入口——語料逐題過**每一道**，不是只過一道。

    🔴 R85／ARCH-02：這句話在 R85-P12 之後有一段時間是**假的**。當時 AST 對帳實測
    「12 定義 / 8 接線」——`scan_foreign_exe_argv`（P12 同輪新增）與另外三道從未被接進來。
    後果不是「少擋一點」而是**方向相反**：M5 注入矩陣量到的攔截率會低報，而低報會讓
    下一輪去補一道已經存在的判準（同 R80 對「大小寫敏感度」那一格低報分子的判決）。
    實測直呼 `scan_foreign_exe_argv` 對 b8／b11 兩題 HIT，而表上兩題都記著 False。
    本輪把**全部 12 道**接齊；另三道對現行語料零命中（實測），接進來是為了讓上面那句
    宣稱不再需要人記得去維護——分母由函式定義本身決定，不是由這張手抄清單決定。
    """
    return {
        "drive-literal": scan_drive_literal,
        "intree-tmpdir": scan_intree_tmpdir,
        "posix-abs-assert": scan_posix_abs_asserts,
        "call-obj-repr": scan_call_obj_repr,
        "path-str-identity": scan_path_str_identity,
        "pathext-guard": scan_unguarded_pathext,
        "text-io-encoding": scan_missing_encoding,
        "foreign-platform-api": scan_foreign_platform_api,
        "foreign-exe-argv": scan_foreign_exe_argv,
        "naive-timestamp": scan_naive_timestamp_persist,
        "ps-platform-sites": scan_ps_platform_sites,
        "git-path-enumeration": scan_git_path_enumeration,
    }


#: (題號, 方向, 語料, 目前是否至少被一道判準攔下)
_XPLAT_INJECTION_CORPUS: tuple[tuple[str, str, str, bool], ...] = (
    # ── 方向甲：在 mac 上寫得出來、到 Windows 會壞 ──────────────────────────
    ("a1-posix-sep-concat", "mac→Win",
     'def f(root, name):\n    return root + "/" + name\n', False),
    ("a2-tmp-hardcode", "mac→Win",
     'OUT = "/tmp/autoclaude.log"\n', False),
    ("a3-getlogin", "mac→Win",
     "def f():\n    return os.getlogin()\n", True),
    ("a4-pwd-module", "mac→Win",
     "import pwd\n\n\ndef f(uid):\n    return pwd.getpwuid(uid).pw_name\n", True),
    ("a5-chmod-exec", "mac→Win",
     "def f(p):\n    os.chmod(p, 0o755)\n", False),
    ("a6-fork", "mac→Win",
     "def f():\n    return os.fork()\n", True),
    ("a7-killpg-sigkill", "mac→Win",
     "def f(pgid):\n    os.killpg(pgid, signal.SIGKILL)\n", True),
    ("a8-shebang-exec", "mac→Win",
     'def f(sub):\n    return sub.run(["./tools/local_ci_gate.sh"])\n', False),
    ("a9-lf-only-write", "mac→Win",
     'def f(p, body):\n    p.write_text(body, encoding="utf-8")\n', False),
    ("a10-symlink", "mac→Win",
     "def f(src, dst):\n    os.symlink(src, dst)\n", True),
    # ── 方向乙：在 Windows 上寫得出來、到 mac 會壞 ──────────────────────────
    ("b1-drive-literal", "Win→mac", f'ROOT = "{_DRIVE_FRAG}"\n', True),
    ("b2-backslash-join", "Win→mac",
     'def f(root, name):\n    return root + "\\\\" + name\n', False),
    ("b3-pathext", "Win→mac",
     f'def f():\n    return os.environ["{_PATHEXT_FRAG}"].split(";")\n', True),
    ("b4-exe-suffix", "Win→mac",
     'def f(name):\n    return name + ".exe"\n', False),
    ("b5-cp950-encoding", "Win→mac",
     'def f(p):\n    return p.read_text(encoding="cp950")\n', False),
    ("b6-no-encoding", "Win→mac",
     "def f(p):\n    return p.read_text()\n", True),
    ("b7-winreg", "Win→mac",
     "import winreg\n\n\ndef f():\n    return winreg.HKEY_LOCAL_MACHINE\n", True),
    # b8／b11 由 False 轉 True＝R85／ARCH-02 把 `scan_foreign_exe_argv` 接進統一入口。
    ("b8-schtasks", "Win→mac",
     'def f(sub):\n    return sub.run(["schtasks", "/query"], check=False)\n', True),
    ("b9-startfile", "Win→mac", "def f(p):\n    os.startfile(p)\n", True),
    ("b10-case-insensitive", "Win→mac",
     'def f(a, b):\n    return a.lower() == b.lower()\n', False),
    ("b11-powershell-shell", "Win→mac",
     'def f(sub, c):\n    return sub.run(["powershell.exe", "-Command", c],\n'
     "                   capture_output=True, text=True)\n", True),
    ("b12-msvcrt", "Win→mac",
     "import msvcrt\n\n\ndef f():\n    return msvcrt.getch()\n", True),
)


def live_interception() -> dict[str, tuple[int, int]]:
    """兩個方向各自的 `(攔截數, 題數)` **現場實算值**——M5 那個數字的唯一權威來源。

    抽成公開函式的理由（R78 ARCH-05）：M5 的攔截率此前只以散文寫在三份治理文件裡，
    而三處全部停在**修復前**的值（同一個 commit 落地的第六道判準已經把數字推上去，
    文件卻低報自己的成果）。文件低報看似無害，代價在下一輪：下一位讀者拿載具一跑，
    會看到「一輪暴衝」而去找一個不存在的原因。數字從此**只准由本函式產生**，
    文件寫指令不寫數字（同 M1 那一列 `[Scan-H triplet]` 的手法）。
    """
    totals: dict[str, list[int]] = {}
    for _case_id, direction, source, _expected in _XPLAT_INJECTION_CORPUS:
        slot = totals.setdefault(direction, [0, 0])
        slot[1] += 1
        if injection_hits(source):
            slot[0] += 1
    return {d: (v[0], v[1]) for d, v in totals.items()}


def injection_hits(source: str) -> list[str]:
    """語料被哪幾道判準攔下（排序後的判準名清單）。純函式，供矩陣與統計共用。"""
    hits: list[str] = []
    for name, scanner in _injection_criteria().items():
        try:
            offenders, _stale = scanner(source, _INJECTION_TARGET_REL)
        except (SyntaxError, ValueError):
            continue
        if offenders:
            hits.append(name)
    return sorted(hits)


class TestXplatInjectionMatrix(unittest.TestCase):
    """雙向注入語料矩陣——M5 那個數字的唯一落點。"""

    @classmethod
    def setUpClass(cls) -> None:
        # 報表行刻意全 ASCII（同 `[Scan-H triplet]` 的理由：消費者含 codepage 950 的排程環境）。
        # 這一行就是 M5「不寫死數字、指向載具」的那個載具出口。
        live = live_interception()
        cls.live = live
        print("[Xplat injection matrix] " + " ".join(
            f"{d.replace('→', '2')}={hit}/{total}" for d, (hit, total) in sorted(live.items())
        ))

    def test_every_sample_matches_its_recorded_verdict(self) -> None:
        drift: list[str] = []
        for case_id, direction, source, expected in _XPLAT_INJECTION_CORPUS:
            hits = injection_hits(source)
            if bool(hits) != expected:
                verb = "現在攔得到了（請把該題改成 True）" if hits else "現在攔不到了（判準退化）"
                drift.append(f"{case_id}［{direction}］{verb}；命中判準={hits}")
        self.assertEqual(
            drift, [],
            "注入語料矩陣與釘住的判決不符。兩個方向都必須回來改這張表——"
            "「進步沒有被記錄」就是下一輪又要重新發明語料的起點：\n" + "\n".join(drift),
        )

    def test_the_corpus_covers_both_directions_and_is_not_shrinking(self) -> None:
        """語料本身不得縮水（`每輪強制抽換 ≥2 題防過擬合` 的前提是題數不掉）。"""
        directions = {d for _c, d, _s, _e in _XPLAT_INJECTION_CORPUS}
        self.assertEqual(directions, {"mac→Win", "Win→mac"})
        self.assertGreaterEqual(len(_XPLAT_INJECTION_CORPUS), 22, "語料題數縮水")
        ids = [c for c, _d, _s, _e in _XPLAT_INJECTION_CORPUS]
        self.assertEqual(len(ids), len(set(ids)), "題號重複 ⇒ 逐題比較會對錯位")

    def test_the_interception_rate_only_improves(self) -> None:
        """逐輪可比的那個數字：兩個方向各自的攔截數，只准上升。

        釘的是**當回合實測**：下面 `floors` 那兩個數字**就是**那份實測，本 docstring
        刻意不再抄一份（R78 ARCH-05：M5 的攔截率此前散在三份文件裡各抄一份，三處全部
        停在修復前的值）。想知道現值就跑本測試——`setUpClass` 會印 `[Xplat injection
        matrix]`。R77 動工前 mac→Win 那一格是零：整類對面平台專屬 API 此前無任何判準。
        """
        floors = {"mac→Win": 5, "Win→mac": 8}   # R85／ARCH-02：6→8（exe-argv 判準接線）
        caught = {d: hit for d, (hit, _total) in live_interception().items()}
        for direction, floor in floors.items():
            with self.subTest(direction=direction):
                self.assertGreaterEqual(
                    caught[direction], floor,
                    f"{direction} 攔截數由 {floor} 掉到 {caught[direction]} ⇒ 判準退化",
                )
                self.assertEqual(
                    caught[direction], floor,
                    f"{direction} 攔截數由 {floor} 升到 {caught[direction]}——"
                    "請把本表的下限同步上修，否則下一次退化會被舊值遮住",
                )
        self.assertEqual(
            _encoding_markers(f"x = 1  # {_ENCODING_OK_MARKER} 自家 WHY\n"),
            {1: "自家 WHY"}, "本判準認不出自己的標記 ⇒ 上一條變成恆真的假綠")


# ══════════════════════════════════════════════════════════════════════════════
# R80（包 B / S4）— 跨平台危害類：訂正兩筆假事實 ＋ 三個新家族上鎖
# ══════════════════════════════════════════════════════════════════════════════
# 本段處理的四件事（S4-01～S4-08）全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R80 鐵律三對照表訂正 WHY〉節。


# ── 共用：tracked 檔案的行尾三欄（現查一次）───────────────────────────────────
# R82 訂正本段量測面（選錯平面／blob 與工作樹兩個平面分治）全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R82 行尾量測面訂正 WHY〉節。
@functools.lru_cache(maxsize=1)
def tracked_eol_records() -> tuple[EolRecord, ...]:
    """全庫 tracked 檔的行尾三欄。取數管道壞掉即 fail-loud。

    與 `TestWorktreeEolMatchesPolicy._ls_files_eol()` 的差別：那一支只問政策表內那幾個
    副檔名（`--` pathspec 過濾），本支要**全庫**——③ 的規模判斷不能只看腳本族。
    """
    proc = git_paths.run(_REPO_ROOT, "ls-files", "--eol")
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files --eol 失敗（rc={proc.returncode}；stderr={proc.stderr.strip()!r}）"
            "——本段每一道判準的輸入沒了，不是「沒有違規」")
    return tuple(parse_ls_files_eol_records(proc.stdout))


@functools.lru_cache(maxsize=1)
def tracked_eol_rows() -> tuple[tuple[str, str], ...]:
    """`(路徑, 工作樹行尾)`——`tracked_eol_records()` 的工作樹欄投影（平面②的輸入）。"""
    return tuple((r.path, r.worktree) for r in tracked_eol_records())


#: blob 側「已正規化」的合法值：`lf`＝checkin 正規化做過了；`none`＝無換行；
#: `-text`＝二進位（git 不轉換，行尾無從談起）。其餘（`crlf`／`mixed`）＝正規化被繞過。
#: 空字串**刻意不在**這一集合裡：那代表解析壞掉，而 fail-open 比違規本身更貴。
_NORMALIZED_BLOB_EOL = frozenset({"lf", "none", "-text"})


def blob_eol_offenders(records: tuple[EolRecord, ...]) -> list[str]:
    """blob 內容仍帶 CR 的 tracked 檔——**會跨平台傳染**的那一半（見上方探針 A）。

    為何 `eol=lf` 與 `eol=crlf` 兩族共用**同一條**判準（＝為何不需要平台欄）：`text`
    屬性的 checkin 正規化一律把 blob 存成 LF，`eol=crlf` 只作用在 checkout（本 repo
    136 支 `.ps1` 當回合實測正是 `i/lf w/crlf`）⇒「blob 必須已正規化」對兩族同時成立。
    這也是它可以零容忍的原因：今天全庫 `i/crlf` 與 `i/mixed` 各 0 支，兩平台同值。
    """
    return sorted(r.path for r in records if r.index not in _NORMALIZED_BLOB_EOL)


def eol_drift_rows(
    rows: tuple[tuple[str, str], ...], declared: dict[str, str]
) -> tuple[list[str], list[str]]:
    """`(凍結面漂移, 活躍面漂移)`——工作樹行尾 ≠ `.gitattributes` 宣告的 tracked 檔。

    `none`（空檔／無換行）不算漂移：無從違反。分帳用本檔既有的 `_is_frozen_sdd_path`
    （LATEST **不算**凍結——它是活躍面，Copy-on-Evolve 只凍結歷史版）。
    """
    frozen_side: list[str] = []
    active_side: list[str] = []
    for path, worktree in rows:
        want = declared.get(path_suffix(path))
        if want is None or worktree in (want, "none", ""):
            continue
        (frozen_side if _is_frozen_sdd_path(path) else active_side).append(path)
    return frozen_side, active_side


def debt_band_verdict(label: str, actual: int, ceiling: int) -> str | None:
    """欠債的**雙邊帶**：超過上限＝新增漂移；掉太多＝該重釘。`None`＝在帶內。

    🔴 為何不用「雙向精確比對」（本檔其餘欠債釘子的慣例）：那個慣例成立的前提是欠債面
    **只有登記者會動**（凍結版文件、具名站點集合）。本判準的欠債面是數百支活躍原始碼的
    行尾，任何一個並行工作包用工具覆寫一支檔就會讓它 -1 ⇒ 精確比對會把「別人順手修好
    一支」判成紅燈，而假紅的下場一律是整道鎖被關掉。下界因此帶 slack；但 slack 是
    **有界**的（≥8 或上限的七分之一），大規模清理仍必須回來重釘，欠債不會靜靜地停在
    一個早就過期的數字上。
    """
    if actual > ceiling:
        return (f"{label}：實測 {actual} 超過欠債上限 {ceiling} ⇒ **新增**了行尾漂移。"
                "修法不是把上限調高——以宣告的行尾重存那幾支檔（`.py` 是 LF）")
    floor = ceiling - max(8, ceiling // 7)
    if actual < floor:
        # R82 訂正訊息：本判準現在會在**乾淨的樹上**看到小數字（見 `checkout_local_debt_
        # verdict`），舊訊息只寫「欠債已清掉」會把「新冒出來的漂移」誤導成「該重釘」。
        return (f"{label}：實測 {actual} 落在 0 與重釘下界 {floor} 之間（上限 {ceiling}）"
                f"⇒ 兩種讀法都要有人動作：(a) 本來乾淨的樹上冒出了 {actual} 支漂移，"
                f"請以宣告的行尾重存它們；(b) 存量真的被清掉一大截，請把上限重釘為 "
                f"{actual}，否則下一次退化會被舊值遮住")
    return None


def checkout_local_debt_verdict(label: str, actual: int, ceiling: int) -> str | None:
    """**機器狀態**版的欠債判準：`0` 一律綠，其餘走 `debt_band_verdict` 的雙邊帶。

    🔴 0 為何要單獨開一格（R82；這正是本段判準在 mac 上必紅的成因）：工作樹行尾是
    「這一棵 checkout 的歷史」，全新 clone 在**任何平台**都是 0（見上方探針 B 及其
    `core.autocrlf=true` 對照組）。舊判準把某一台機器的存量當成**下界**，於是一棵乾淨
    的樹被判成「欠債清掉了、請重釘為 0」——而照它的指示重釘，就是把紅原封不動搬到對面
    平台。0 是這個量的**理想值**不是異常值，故不觸發重釘；0 以外的任何值仍要落在帶內
    ⇒ 乾淨的樹上冒出 1 支漂移照樣紅（下界的 slack 是留給並行工作包順手改到存量的，
    而 0 這一側沒有存量可被順手改，所以那裡不需要、也不該有 slack）。
    """
    return None if actual == 0 else debt_band_verdict(label, actual, ceiling)


# ── ②③ 活躍面原始碼行尾止血 ───────────────────────────────────────────────────
#: 本判準的射程：**活躍面**（非凍結 SDD 版）的 `.py`。
#: 刻意不擴到 `.md`／`.yaml`：本表這一列的主題是「原始碼行尾」，而 `.md` 的 CRLF 不會
#: 讓任何東西跑不起來——擴大主題會讓欠債數字失去可讀性，也讓止血點失焦。
_ACTIVE_SOURCE_EOL_SUFFIX = ".py"
#: 🔴 下面兩個數字是**平面②（本機工作樹）**的上界，語意自 R82 起精確化為「R80 落地那台
#: 機器上的陳舊 checkout 存量」——**不是**「Windows 欄的值」，也不是任何平台常數（同一
#: 台 Windows 重新 clone 就是 0；見上方探針 B 的對照組）。因此它們只當**上界**用：
#: 超過＝新增漂移（紅）；0＝乾淨 checkout（綠，任何平台都達得到）；兩者之間＝雙邊帶。
#: 平台中立的那道零容忍閘門在平面①（`blob_eol_offenders`），兩平台讀到同一個答案。
_ACTIVE_PY_EOL_DEBT_CEILING = 220
#: 凍結面（v0.01~v0.29）`.py` 工作樹行尾漂移的同款上界。Copy-on-Evolve 禁改；
#: 這個數字的用途是讓「為什麼不一次全轉 LF」變成可查的量，而不是散文。
_FROZEN_PY_EOL_DEBT_CEILING = 3956


class TestActiveSourceEolIsRatchetedSeparatelyFromTheFrozenSurface(unittest.TestCase):
    """活躍面 `.py` 行尾止血 ＋ 凍結面誠實登記（見本段 WHY ②③）。

    這一列此前在鐵律三對照表上寫「無機械物」——**不真**。機械物一直都在
    （`TestWorktreeEolMatchesPolicy`），只是 `_EOL_LF_SCOPE` 把射程窄化成 `.sh`／`.bash`，
    而且該類的 `test_the_policy_follows_the_declaration_instead_of_a_copy` 還有一條
    `assertNotIn(".py", policy)` 把「`.py` 必須被放行」釘成契約。本類別是那一格的牙齒：
    **不動那道腳本閘的射程**（擴進去會讓它一上線就吃四千筆凍結面欠債而必被關掉），
    改以獨立射程承接 `.py`，並把凍結／活躍分開記帳。
    """

    def _declared(self) -> dict[str, str]:
        return declared_eol(_GITATTRIBUTES_PATH.read_text(encoding="utf-8"))

    def test_no_tracked_blob_carries_a_carriage_return(self) -> None:
        """①（R82 新增）：**平台中立**的那道閘門——每台機器讀到同一個答案。

        這是三支判準裡唯一「在 mac 上做的判斷，對 Windows 也逐字成立」的一條：blob 是
        content-addressed，`git clone` 不會改它。一支 blob 帶了 CR，**每一個** clone
        （含 `core.autocrlf=true` 的 Windows clone）都會拿到 CR ⇒ POSIX 上 shebang 檔
        rc=127、`.sh` 噴 `$'\\r'`。零容忍：今天全庫 0 支，沒有存量要辯護。
        """
        records = tracked_eol_records()
        self.assertGreater(len(records), 20000,
                           f"tracked 列數異常少（{len(records)}）⇒ 取數管道疑似壞掉")
        offenders = blob_eol_offenders(records)
        self.assertEqual(
            offenders, [],
            "以下 tracked 檔的 **blob** 行尾未正規化（`i/crlf`／`i/mixed`），"
            "或 `i/` 欄根本解析不出來。前者會隨 clone 傳到每一台機器、每一個平台；"
            "修法＝`git add --renormalize <檔>` 後 commit：\n" + "\n".join(offenders[:40]),
        )

    def test_active_surface_python_eol_does_not_grow(self) -> None:
        """②：本機工作樹的健康度。0 或帶內皆綠，新增漂移必紅（見上方平面②的 WHY）。"""
        rows = tracked_eol_rows()
        self.assertGreater(len(rows), 20000,
                           f"tracked 列數異常少（{len(rows)}）⇒ 取數管道疑似壞掉")
        declared = self._declared()
        self.assertEqual(declared.get(_ACTIVE_SOURCE_EOL_SUFFIX), "lf",
                         "`.gitattributes` 對 .py 的宣告變了 ⇒ 本判準的前提要重新確認")
        frozen_side, active_side = eol_drift_rows(rows, declared)
        active_py = [p for p in active_side if p.endswith(_ACTIVE_SOURCE_EOL_SUFFIX)]
        frozen_py = [p for p in frozen_side if p.endswith(_ACTIVE_SOURCE_EOL_SUFFIX)]
        problems = [
            v for v in (
                checkout_local_debt_verdict("活躍面 .py 工作樹行尾漂移", len(active_py),
                                            _ACTIVE_PY_EOL_DEBT_CEILING),
                checkout_local_debt_verdict("凍結面 .py 工作樹行尾漂移", len(frozen_py),
                                            _FROZEN_PY_EOL_DEBT_CEILING),
            ) if v is not None
        ]
        self.assertEqual(
            problems, [],
            "🔴 `git status` 對這種漂移**結構上看不見**（checkin 正規化只作用於 index，"
            "兩側套同一份規則）；CI 也看不見（`actions/checkout` 必定重新 smudge）。"
            "唯一看得見的是本機工作樹這一欄：\n" + "\n".join(problems)
            + f"\n（現值：活躍 {len(active_py)} 支、凍結 {len(frozen_py)} 支）",
        )

    def test_the_repo_wide_scale_is_measured_not_quoted(self) -> None:
        """③：規模是量出來的——而反空轉的載體換成了**在兩個平台都非零**的正控。

        🔴 R82 訂正：原版斷言「全庫工作樹漂移 > 0」，那個斷言的前提是「跑它的機器帶著
        陳舊 checkout」，在乾淨的樹（每一台 mac、每一個新 clone，含 Windows）上結構性
        為 0 ⇒ 它量到的是機器，不是 repo。**意圖保留**（取數管道壞掉不得靜默回 0），
        載體換成 `.ps1`：該族宣告 `eol=crlf`，任何平台 checkout 都是 CRLF，所以
        「`w/` 欄讀不到任何 crlf」只可能是解析壞了。比例那一半只在真有漂移時才問。
        """
        records = tracked_eol_records()
        self.assertGreater(
            sum(1 for r in records if r.worktree == "crlf"), 0,
            "`w/` 欄一支 crlf 都讀不到 ⇒ 解析管道壞了（`.ps1` 族宣告 eol=crlf，"
            "任何平台的 checkout 都必須是 CRLF），不是「沒有 CRLF」")
        self.assertTrue(
            all(r.index for r in records),
            "`i/` 欄有列解析不出來 ⇒ 平面①的零容忍判準會對那幾列恆綠（fail-open）")
        frozen_side, active_side = eol_drift_rows(
            tuple((r.path, r.worktree) for r in records), self._declared())
        total = len(frozen_side) + len(active_side)
        if total == 0:
            # 乾淨 checkout：「凍結面該不該就地轉 LF」這個修法問題不存在。此時仍要問一件
            # 平面②推導不出來的事——`eol=crlf` 那一族即使 blob 帶 CR 也不會算成工作樹
            # 漂移（checkout 本來就給 CRLF），所以零漂移**不蘊含**零 blob 汙染。
            self.assertEqual(blob_eol_offenders(records), [],
                             "工作樹零漂移但 blob 仍帶 CR ⇒ 平面①才是這一輪的主戰場")
            return
        ratio = len(frozen_side) / total
        self.assertGreater(
            ratio, 0.8,
            f"凍結面佔比掉到 {ratio:.2%}（凍結 {len(frozen_side)}／活躍 {len(active_side)}"
            f"／全庫 {total}）⇒ 主要漂移已在可改的活躍面，"
            "「分開處置」這個修法前提不再成立，請重新裁決",
        )

    def test_the_narrowing_constant_is_still_the_reason_this_class_exists(self) -> None:
        """自錨：哪天有人把 `.py` 補進 `_EOL_LF_SCOPE`，本類別就重複了、該被刪。

        沒有這一條，兩道射程會靜靜地重疊，而重疊的鎖只有在其中一道紅的時候才會被發現。
        """
        self.assertNotIn(
            _ACTIVE_SOURCE_EOL_SUFFIX, _EOL_LF_SCOPE,
            "`.py` 已進入 `_EOL_LF_SCOPE` ⇒ 腳本閘已承接這個副檔名，"
            "請刪掉本類別（並確認它承接時有處理凍結面約四千支欠債）")

    def test_the_band_has_teeth_in_both_directions(self) -> None:
        """判準自證（合成值，不動磁碟）：兩個方向都要判得出來。"""
        self.assertIsNone(debt_band_verdict("x", 220, 220))
        self.assertIn("新增", debt_band_verdict("x", 221, 220) or "")
        self.assertIn("重釘", debt_band_verdict("x", 100, 220) or "")
        # slack 有下界：小欠債面掉 1 支不該逼人重釘（否則並行工作包一動就紅）
        self.assertIsNone(debt_band_verdict("x", 9, 10))

    def test_a_clean_checkout_is_green_but_one_stray_file_is_not(self) -> None:
        """②的紅綠自證（R82 的修法本體）：0 綠、1 紅、上界內綠、上界外紅。

        中間那一條是這次修法**不是**「把常數改成 mac 量到的 0」的證據：真的把下界重釘
        成 0，Windows 那台帶著存量的樹會在 220 這一格轉紅；真的只放行 0，乾淨的樹上冒
        出一支 CRLF 又會靜靜地過。四個點合起來才是「兩平台各自都有牙」。
        """
        self.assertIsNone(checkout_local_debt_verdict("x", 0, 220))     # 乾淨 checkout
        self.assertIn("(a)", checkout_local_debt_verdict("x", 1, 220) or "")  # 乾淨樹冒新漂移
        self.assertIsNone(checkout_local_debt_verdict("x", 220, 220))   # 陳舊樹的存量
        self.assertIn("新增", checkout_local_debt_verdict("x", 221, 220) or "")

    def test_the_blob_criterion_is_not_vacuous(self) -> None:
        """①的紅綠自證（合成列，不動磁碟）：只放行已正規化的 blob。

        含一條 fail-open 的反向釘：`i/` 欄解析不出來（空字串）必須算違規——否則哪天
        `git ls-files --eol` 換了輸出格式，這道零容忍閘門會在「零命中」下全綠。
        """
        def rec(index: str) -> EolRecord:
            return EolRecord("x.py", index, "lf", "text eol=lf")
        self.assertEqual(blob_eol_offenders((rec("lf"), rec("none"), rec("-text"))), [])
        for bad in ("crlf", "mixed", ""):
            with self.subTest(index=bad):
                self.assertEqual(blob_eol_offenders((rec(bad),)), ["x.py"])
        # 解析層自證：`i/` 與 `w/` 不得互串（兩欄語意完全不同，串了就是量錯平面）
        line = "i/crlf  w/lf    attr/text eol=lf      \ttools/x.py\n"
        self.assertEqual(parse_ls_files_eol_records(line),
                         [EolRecord("tools/x.py", "crlf", "lf", "text eol=lf")])


# ── ④-a shebang ⇒ 必須是 LF ──────────────────────────────────────────────────
# 缺陷本體與 R82 量測面兩層設計全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R82 shebang×CRLF 判準 WHY〉節。
#: 活躍面（含 LATEST）在**帶著陳舊 checkout 的那台機器**上仍成立的站點。上界語意見上。
_SHEBANG_NON_LF_ACTIVE_DEBT: dict[str, str] = {
    "AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/arch_fitness.py": (
        "LATEST 版（非凍結、可改）。修法＝以 LF 重存該檔；未於本輪動手的理由是它不在"
        "本包的檔案所有權內，已列入交棒"
    ),
}
#: 凍結面（v0.01~v0.29）同型站點數的**上界**——Copy-on-Evolve 禁改，只登記不判。
_SHEBANG_NON_LF_FROZEN_DEBT = 29


def _starts_with_shebang(path: Path) -> bool:
    """**工作樹那一份**的首兩個位元組是不是 `#!`。

    🔴 這一支只該用在「問題本身就問工作樹位元組」的地方（＝`shebang_non_lf_sites`：
    行尾漂移是 checkout 的性質）。凡是要主張「這個答案換一台機器也成立」的judgement，
    一律改問 `_blob_starts_with_shebang()`——本函式對「index 有、工作樹沒有」（稀疏
    checkout／`GIT_INDEX_FILE` 注入）回 `False`，那是**機器狀態**而不是檔案的性質。
    """
    try:
        with path.open("rb") as handle:
            return handle.readline(256).startswith(b"#!")
    except OSError:
        return False


def _blob_starts_with_shebang(repo_root: Path, rel: str) -> bool:
    """**blob**（index 那一份）的首兩個位元組是不是 `#!`——機器中立的那個答案。

    🔴 為何非得跟工作樹版分家（當回合注入實測抓到的 fail-open）：以 `GIT_INDEX_FILE`
    注入一支汙染 blob、而工作樹沒有對應檔案時，讀工作樹的版本 `open()` 失敗 ⇒ 靜默
    判成「不是 shebang 檔」而放行。稀疏 checkout 與 index 有／工作樹沒有的狀態都會走到
    那一支，且失效是**無聲**的。blob 由 `git clone` 逐位元組複製 ⇒ 每台機器同一個答案。
    """
    proc = git_paths.run(repo_root, "cat-file", "blob", f":{rel}")
    return proc.returncode == 0 and proc.stdout.startswith("#!")


def shebang_blob_sites(records: tuple[EolRecord, ...], repo_root: Path) -> list[str]:
    """blob 帶 CR **且**首行是 `#!` 的 tracked 檔——會跨平台傳染的那一半。

    候選面先由 `i/` 欄收斂（今天 0 支）再逐支問 blob：全庫 27k 支都 `git cat-file`
    是分鐘級，而帶 CR 的 blob 本來就是要判零的那一族，所以這個代價是有界的。
    shebang 刻意向 **blob** 問而不是向工作樹那一份問，理由見 `_blob_starts_with_shebang`。
    """
    return sorted(
        record.path for record in records
        if record.index not in _NORMALIZED_BLOB_EOL
        and _blob_starts_with_shebang(repo_root, record.path)
    )


def shebang_non_lf_sites(
    rows: tuple[tuple[str, str], ...], repo_root: Path
) -> tuple[list[str], list[str]]:
    """`(凍結面, 活躍面)`——首行是 `#!` 而工作樹行尾不是 LF 的 tracked 檔。

    讀**位元組**而非文字：這一題問的就是位元組（`\\r` 有沒有黏在直譯器名後面），
    以 text mode 讀會被 universal newlines 就地吃掉，判準會恆綠。
    """
    frozen_side: list[str] = []
    active_side: list[str] = []
    for path, worktree in rows:
        if worktree in ("lf", "none", "") or not _starts_with_shebang(repo_root / path):
            continue
        (frozen_side if _is_frozen_sdd_path(path) else active_side).append(path)
    return frozen_side, active_side


class TestShebangImpliesLfLineEndings(unittest.TestCase):
    """`#!` ＋ 非 LF ＝ POSIX 上 `env: '…\\r': No such file or directory`（見上方 WHY）。"""

    def test_no_tracked_blob_pairs_a_shebang_with_a_carriage_return(self) -> None:
        """①-shebang（R82 新增）：平台中立、零容忍、雙向精確。

        這一條在 mac 上判出來的結果對 Windows 逐字成立，反之亦然——因為它問的是 blob，
        而 blob 不隨 checkout 變。它才是「exec bit 被補對那天會不會炸」真正的守門者。
        """
        self.assertEqual(
            shebang_blob_sites(tracked_eol_records(), _REPO_ROOT), [],
            "以下 tracked 檔的 blob 同時具備 `#!` 與 CR ⇒ 每一個 clone（含 Windows）"
            "都會拿到它，POSIX 上 `./<檔>` 必 rc=127（`env: '…\\r'`）。"
            "修法＝`git add --renormalize <檔>` 後 commit",
        )

    def test_no_new_shebang_file_carries_a_non_lf_line_ending(self) -> None:
        """②-shebang：本機工作樹側 ⇒ **子集合**語意（見上方 R82 訂正段）。"""
        frozen_side, active_side = shebang_non_lf_sites(tracked_eol_rows(), _REPO_ROOT)
        self.assertEqual(
            sorted(set(active_side) - set(_SHEBANG_NON_LF_ACTIVE_DEBT)), [],
            "活躍面冒出登記外的 shebang×非 LF 站點＝**新增**的同型缺陷，"
            "請以 LF 重存該檔（`git add --renormalize` 只修 blob，修不了工作樹）",
        )
        self.assertLessEqual(
            len(frozen_side), _SHEBANG_NON_LF_FROZEN_DEBT,
            f"凍結面同型站點由上界 {_SHEBANG_NON_LF_FROZEN_DEBT} 漲到 {len(frozen_side)}"
            "——凍結面理應不動；若是 LATEST 版號推進造成整批位移，請重釘這個上界",
        )

    def test_every_registered_debt_entry_still_has_a_platform_neutral_reason(self) -> None:
        """子集合語意的補救：登記的每一筆，其**理由**必須仍然成立。

        沒有這一條，`_SHEBANG_NON_LF_ACTIVE_DEBT` 就會靠慣性活著——檔案被刪、被改名、
        或 shebang 被拿掉之後，子集合判準永遠不會說話。三個條件全部是**機器中立**的
        （tracked／宣告 eol=lf／**blob** 首行 `#!`），所以這一條在 mac 與 Windows 上
        同樣有牙。

        🔴 第三個條件刻意向 **blob** 問而不是向工作樹問（R82 複驗補正）：本條的失敗訊息
        叫人「把該筆自欠債表刪掉」，而工作樹版對「index 有、工作樹沒有」（稀疏 checkout）
        回 `False` ⇒ 那會是一個**假紅，且它建議的動作會就地縮小掃描面**——被刪掉的那一筆
        正是 Windows 那台仍然成立的欠債。縮面的表徵是「看起來更乾淨」，沒有人會發現。
        """
        tracked = {r.path: r for r in tracked_eol_records()}
        declared = declared_eol(_GITATTRIBUTES_PATH.read_text(encoding="utf-8"))
        stale: list[str] = []
        for rel in _SHEBANG_NON_LF_ACTIVE_DEBT:
            record = tracked.get(rel)
            if record is None:
                stale.append(f"{rel}：已不是 tracked 檔")
            elif declared.get(path_suffix(rel)) != "lf":
                stale.append(f"{rel}：`.gitattributes` 已不再對它宣告 eol=lf")
            elif not _blob_starts_with_shebang(_REPO_ROOT, rel):
                stale.append(f"{rel}：blob 首行已不是 `#!` ⇒ 這一族的危害對它不成立")
        self.assertEqual(stale, [],
                         "登記理由已消失，請把該筆自欠債表刪掉：\n" + "\n".join(stale))

    def test_the_two_shebang_readers_diverge_exactly_on_the_machine_state_case(self) -> None:
        """自證：`_blob_starts_with_shebang` 與 `_starts_with_shebang` 不是同義詞。

        本檔把 shebang 的判讀拆成 blob 版與工作樹版，理由是「index 有、工作樹沒有」時
        兩者答案不同——若哪天有人把其中一支改成轉呼另一支（看起來像去重），這條拆分就
        白做了，而**兩個消費端都會靜默失去它要的那個語意**。所以在真的 git repo 上把
        那個分歧點造出來：兩者必須一個 True、一個 False。

        刻意用臨時 repo 而不是本 repo：本 repo 的工作樹是完整的，這個分歧點在這裡
        造不出來——「在本機重現不了」不是跳過的理由，是換一個造得出來的量測面的理由。
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for argv in (("init", "-q", "."), ("config", "user.email", "t@t"),
                         ("config", "user.name", "t")):
                self.assertEqual(git_paths.run(root, *argv).returncode, 0)
            probe = root / "probe.py"
            probe.write_bytes(b"#!/usr/bin/env python3\nprint(1)\n")
            self.assertEqual(git_paths.run(root, "add", "probe.py").returncode, 0)
            self.assertTrue(_starts_with_shebang(probe), "前提：工作樹版此刻看得到 shebang")
            self.assertTrue(_blob_starts_with_shebang(root, "probe.py"),
                            "前提：blob 版此刻也看得到 shebang")
            probe.unlink()  # ＝稀疏 checkout／index 有而工作樹沒有的那個狀態
            self.assertFalse(_starts_with_shebang(probe),
                             "工作樹版在檔案不存在時必須回 False——那正是它的 fail-open")
            self.assertTrue(
                _blob_starts_with_shebang(root, "probe.py"),
                "blob 版被工作樹的缺席影響到了 ⇒ 它已不是機器中立的答案，"
                "而所有靠它主張『這一條在另一個平台同樣有牙』的判準都跟著變成假話")

    def test_the_criterion_reads_bytes_not_decoded_text(self) -> None:
        """判準自證：真的寫一支 CRLF shebang 檔，確認在位元組層看得到 `\\r`。

        不是為了測作業系統，是為了證明**這個判準讀的是位元組**——以 text mode 讀會被
        universal newlines 吃掉 `\\r`，判準會恆綠而沒有任何人發現。
        """
        with tempfile.TemporaryDirectory() as td:
            probe = Path(td) / "probe.py"
            probe.write_bytes(b"#!/usr/bin/env python3\r\nprint(1)\r\n")
            with probe.open("rb") as handle:
                raw = handle.readline(256)
            text_head = probe.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(raw.startswith(b"#!"))
        self.assertTrue(raw.rstrip(b"\n").endswith(b"\r"),
                        "位元組層看不到 \\r ⇒ 本判準讀錯了層，會對整類缺陷恆綠")
        self.assertFalse(text_head.endswith("\r"),
                         "text mode 竟然留住了 \\r？那本註記的理由要重寫")

    def test_the_exec_bit_coincidence_is_named_not_relied_on(self) -> None:
        """今天沒炸的理由（索引模式不是 100755）必須是**可查的量**，不是口頭安慰。

        哪天 exec bit 被補對——那是正確的修法——這一條會紅，而它紅的意思是「另一半還沒
        修」。這正是本判準存在的理由：兩個各自正確的動作合起來會炸。
        """
        modes = index_modes(_REPO_ROOT)
        self.assertTrue(modes, "git ls-files -s 取數失敗 ⇒ 本條無從判定")
        frozen_side, active_side = shebang_non_lf_sites(tracked_eol_rows(), _REPO_ROOT)
        # R82：兩個平面一起收。只收工作樹側的話，這一條在乾淨的樹上（mac、任何新 clone）
        # 掃描面是空集合＝恆綠；blob 側那一半才是換台機器也還在的那一組。
        candidates = frozen_side + active_side + shebang_blob_sites(
            tracked_eol_records(), _REPO_ROOT)
        executable = [p for p in sorted(set(candidates))
                      if modes.get(p) == _INDEX_MODE_EXEC]
        self.assertEqual(
            executable, [],
            "以下檔案同時具備 shebang、非 LF 行尾、100755 索引模式 ⇒ 三個條件到齊，"
            "mac/Linux 上 `./<檔>` 必 rc=127（`env: '…\\r'`）。行尾與 exec bit 兩半"
            "任一半修好都不夠：\n" + "\n".join(executable),
        )


# ── ④-b naive 本地時間戳被持久化 ─────────────────────────────────────────────
# 缺陷本體與誠實劃界全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈naive 本地時間戳判準 WHY〉節。
_NAIVE_TS_OK_MARKER = "naive-ts-ok:"
_NAIVE_NOW_FUNCS = frozenset({"now", "utcnow"})


def _is_naive_now_call(node: ast.AST) -> bool:
    """`datetime.now()`／`datetime.datetime.now()`／`utcnow()`，且**未傳任何 tz**。"""
    if not (isinstance(node, ast.Call) and not node.args and not node.keywords):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in _NAIVE_NOW_FUNCS:
        return True
    return isinstance(func, ast.Name) and func.id in _NAIVE_NOW_FUNCS


def _naive_ts_markers(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token（字串字面值內的同形文字不當豁免）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _NAIVE_TS_OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_NAIVE_TS_OK_MARKER, 1)[1].strip()
    return markers


def scan_naive_timestamp_persist(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)。"""
    tree = ast.parse(source)
    markers = _naive_ts_markers(source)
    offenders: dict[int, str] = {}
    used: set[int] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "isoformat" or not _is_naive_now_call(node.func.value):
            continue
        if markers.get(node.lineno):
            used.add(node.lineno)
            continue
        offenders[node.lineno] = (
            f"{rel}:{node.lineno}: `now().isoformat()` 產出**不帶 offset** 的本地時間字串"
            "（存進 checkpoint／YAML 後讀回相減，跨 DST 切換整整差 3600 秒且完全靜默）"
            "——請改 `datetime.now().astimezone().isoformat()` 或 `datetime.now(UTC)`"
        )
    stale = [
        f"{rel}:{lineno}: {_NAIVE_TS_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return [offenders[k] for k in sorted(offenders)], stale


def _is_test_file(rel: str) -> bool:
    parts = rel.split("/")
    return "tests" in parts or parts[-1].startswith("test_")


#: 具名欠債：今天仍在產出 naive ISO 字串的**生產**站點。逐筆寫明它餵給誰，讓「這一筆
#: 到底會不會害到人」是可讀的，而不是一個數字。雙向精確比對。
_NAIVE_TS_PERSIST_DEBT: dict[str, str] = {
    "AutoClaude/autoclaude/infra/repositories/file_state_repository.py": (
        "checkpoint.saved_at 與 schedule_resume 的 naive ISO。R81 訂正此列的因果："
        "讀側已於 R81 收斂成單一時鐘 utils/resume_clock.py（跟著輸入的 tzinfo 走），"
        "naive 與 aware 兩種形態都算得對 ⇒ 這一筆今天算得**對**，殘留的曝險只剩"
        "跨 DST：naive 字串本身無法表達寫入當下的 offset。危害更大的是反向那一半"
        "（產出 aware、消費端只吃 naive），本掃描器對它結構上失明——它只認"
        "`datetime.now()` 這種產出面形狀，看不到消費端。守那一半的是行為判準："
        "tests/contract/test_state_repository_contract.py::"
        "IStateRepositoryContract::test_scheduled_resume_is_readable_by_the_consumer"
        "（File／InMemory／Pg 三後端對稱）"
    ),
    "AutoClaude/autoclaude/infra/repositories/file_playbook_repository.py": (
        "playbook 快照時間戳；目前只做顯示與排序，同 offset 內排序不受影響"
    ),
    "AutoClaude/tools/pg_dump_to_yaml.py": (
        "dump metadata 的 started_at／finished_at（兩筆），只做人讀"
    ),
    "AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/arch_fitness.py": (
        "arch-fitness 報告的 timestamp 欄，只做人讀"
    ),
    ".claude/hooks/context_budget_guard.py": (
        "額度哨兵的武裝 log 行，只做人讀取證；但它是**跨時區可攜性**最差的一種"
        "——log 的讀者不一定在同一個 offset 下"
    ),
    # 🔴 以下七筆的處置說明刻意**不逐筆宣稱讀側行為**：本輪只逐檔確認了「產出端確實是
    # naive ISO」，沒有逐筆追讀側的消費者。寫「只做顯示」而沒真的追過，就是憑推測寫下
    # 一個看起來像結論的東西——那正是本 repo 反覆記載的失誤形態。逐筆追讀側列為交棒。
    "AutoClaude/autoclaude/infra/repositories/in_memory_playbook_repository.py":
        "與 file_playbook_repository 同形（記憶體後端）；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/infra/repositories/in_memory_state_repository.py":
        "與 file_state_repository 同形（記憶體後端）；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/models/escalation.py":
        "ESCALATION 事件時間戳；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/plugins/sdd_governance_plugin.py":
        "SDD 治理事件時間戳；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/utils/checkpoint_manager.py":
        "checkpoint 時間戳——與 file_state_repository 同一條恢復路徑，優先度同高",
    "AutoClaude/autoclaude/utils/notifier.py":
        "通知訊息時間戳；讀側未逐一追，見上方註記",
    "AutoClaude/autoclaude/utils/token_tracker.py":
        "token 用量紀錄時間戳；讀側未逐一追，見上方註記",
}


class TestNaiveLocalTimestampsAreNotPersisted(unittest.TestCase):
    """不帶 offset 的本地時間戳不得進持久層（見上方 WHY）。"""

    def test_no_new_site_persists_a_naive_local_timestamp(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        hit_files: set[str] = set()
        scanned = 0
        for _label, files, _floor in _scan_units():
            for py in files:
                rel = py.relative_to(_REPO_ROOT).as_posix()
                if _is_test_file(rel):
                    continue
                try:
                    off, st = scan_naive_timestamp_persist(
                        py.read_text(encoding="utf-8"), rel)
                except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
                    parse_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
                    continue
                scanned += 1
                stale.extend(st)
                if off:
                    hit_files.add(rel)
                    if rel not in _NAIVE_TS_PERSIST_DEBT:
                        offenders.extend(off)
        self.assertEqual(
            parse_failures, [],
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures))
        self.assertGreater(scanned, 300, f"只掃到 {scanned} 支非測試 .py ⇒ 掃描面疑似縮小")
        self.assertEqual(
            offenders, [],
            "新增了 naive 本地時間戳持久化站點（現行欠債見 `_NAIVE_TS_PERSIST_DEBT`）：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            sorted(hit_files), sorted(_NAIVE_TS_PERSIST_DEBT),
            "欠債清單與實況不符：少掉的表示已修好（請自清單刪除，欠債不得靠慣性活著），"
            "多出來的表示新增了同型站點",
        )
        self.assertEqual(stale, [],
                         f"{_NAIVE_TS_OK_MARKER} 標記 stale：\n" + "\n".join(stale))

    def test_the_dst_gap_is_reproducible_without_touching_the_system_clock(self) -> None:
        """🔴 這一條是本判準的**理由本身**：跨 DST 的 naive 相減會差整整 3600 秒。

        本機時區 Asia/Taipei 不實施 DST ⇒ 這個缺陷在本機結構上重現不了。

        🔴 **不用 `zoneinfo.ZoneInfo("America/New_York")`**（第一版就是那樣寫的，當回合
        實測 `ZoneInfoNotFoundError`）：Windows 沒有系統 tz 資料庫，`zoneinfo` 要靠
        `tzdata` 這個**選配**套件，而本 repo 沒有裝它 ⇒ 那種寫法會讓這條在 Windows 上
        變成 ERROR、在 mac/Linux 上通過。本判準在守的就是「單平台判準不可無條件外推」，
        它自己第一版卻正是那個形態。改用固定 offset 直接構造 fall-back 的兩個瞬間：
        EDT(-04:00) 的 01:30 與 EST(-05:00) 的 01:30 相差正好一小時，而**丟掉 offset
        之後兩者完全相同**——這就是 DST 落回那一小時的全部語意，且零外部相依。
        """
        from datetime import datetime as _dt  # noqa: PLC0415
        from datetime import timedelta as _td  # noqa: PLC0415
        from datetime import timezone as _tz  # noqa: PLC0415

        # 2024-11-03 美東 fall back：01:30 出現兩次，先 EDT(-4) 後 EST(-5)。
        before = _dt(2024, 11, 3, 1, 30, tzinfo=_tz(-_td(hours=4)))
        after = _dt(2024, 11, 3, 1, 30, tzinfo=_tz(-_td(hours=5)))
        self.assertEqual((after - before).total_seconds(), 3600.0,
                         "帶 tz 的兩個時刻相減應為 3600 秒（真實經過的時間）")
        # 這就是 `.isoformat()` 沒有 offset 時，存檔／讀回之後剩下的東西：
        naive_before = before.replace(tzinfo=None)
        naive_after = after.replace(tzinfo=None)
        self.assertEqual(naive_before.isoformat(), naive_after.isoformat(),
                         "兩個相差一小時的時刻，naive ISO 字串**完全相同** ⇒ 資訊已遺失")
        self.assertEqual(
            (naive_after - naive_before).total_seconds(), 0.0,
            "naive 相減得到 0 秒（真實是 3600 秒）——Kernel 會據此提早一小時恢復")
        # 反向自證：修法慣例（帶 offset）把資訊留住，round-trip 後仍算得出 3600 秒
        self.assertNotEqual(before.isoformat(), after.isoformat())
        self.assertEqual(
            (_dt.fromisoformat(after.isoformat())
             - _dt.fromisoformat(before.isoformat())).total_seconds(),
            3600.0, "帶 offset 的 ISO 字串 round-trip 後仍算得出 3600 秒 ⇒ 修法真的有效")

    def test_the_criterion_has_teeth_and_does_not_overreach(self) -> None:
        """判準紅綠自證（合成字串，不留違規樣本於 repo）。"""
        red, stale = scan_naive_timestamp_persist(
            "from datetime import datetime\n"
            "def f():\n"
            "    return datetime.now().isoformat(timespec='seconds')\n", "fixture.py")
        self.assertEqual(len(red), 1, red)
        self.assertEqual(stale, [])
        for green in (
            "from datetime import datetime\n"
            "def f():\n    return datetime.now().astimezone().isoformat()\n",
            "from datetime import datetime, UTC\n"
            "def f():\n    return datetime.now(UTC).isoformat()\n",
            "from datetime import datetime\n"
            "def f():\n    return datetime.now()\n",
        ):
            with self.subTest(green=green.splitlines()[-1].strip()):
                self.assertEqual(scan_naive_timestamp_persist(green, "fixture.py")[0], [])
        marked, stale = scan_naive_timestamp_persist(
            "from datetime import datetime\n"
            "def f():\n"
            f"    return datetime.now().isoformat()  # {_NAIVE_TS_OK_MARKER} 純顯示\n",
            "fixture.py")
        self.assertEqual((marked, stale), ([], []))
        blank, stale = scan_naive_timestamp_persist(
            "from datetime import datetime\n"
            "def f():\n"
            f"    return datetime.now().isoformat()  # {_NAIVE_TS_OK_MARKER}\n",
            "fixture.py")
        self.assertEqual(len(blank), 1, "WHY 留空的標記不得生效")
        self.assertEqual(len(stale), 1, stale)


# ── ④-c PowerShell 站點級：Windows 專屬 `$env:` 與 `bash` 解析 ────────────────
# 缺陷本體（S4-04／S4-05）與誠實劃界全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈PowerShell 站點級判準 WHY〉節。
_PS_SITE_OK_MARKER = "ps-xplat-ok:"
#: 讀取（非賦值）Windows 專屬暫存目錄變數。`(?!\s*=)` 排除 `$env:TEMP = …` 的設定形態。
_WINDOWS_ONLY_ENV_READ_RE = re.compile(r"\$env:(TEMP|TMP)\b(?!\s*=)", re.IGNORECASE)
#: 裸解析 `bash`。唯一合法的家是下面那支 SSOT。
_BASH_RESOLUTION_RE = re.compile(
    r"Get-Command\s+['\"]?bash(?:\.exe)?['\"]?(?![\w.-])", re.IGNORECASE)
_BASH_RESOLUTION_SSOT = "tools/lib/Find-GitBash.ps1"
#: 具名欠債：今天仍直接讀 `$env:TEMP`／`$env:TMP` 的活躍 PowerShell 腳本。雙向精確比對。
_WINDOWS_ONLY_ENV_DEBT: dict[str, str] = {
    "tools/windows_smoke_local.ps1": (
        "Windows 專用（檔內自帶 MSYS 守衛與 PS 5.1 引擎守衛，在 POSIX 上本來就不執行）"
        "——保留現狀，但仍登記，避免它被當成「這種寫法沒問題」的樣板"
    ),
    "AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.ps1": (
        "🔴 真曝險：框架發給使用者的安裝腳本，在 macOS/Linux 的 PS Core 上 "
        "`Join-Path $env:TEMP …` 直接拋 null 綁定例外。修法＝"
        "`[System.IO.Path]::GetTempPath()`。不在本包的檔案所有權內，已列入交棒"
    ),
}


def _active_ps_scripts() -> list[str]:
    """活躍面（非凍結 SDD 版）tracked PowerShell 腳本的 repo 相對路徑。"""
    return sorted(
        path for path, _eol in tracked_eol_rows()
        if path.lower().endswith((".ps1", ".psm1", ".psd1"))
        and not _is_frozen_sdd_path(path)
    )


def scan_ps_platform_sites(source: str, rel: str) -> tuple[list[str], list[str]]:
    """`(env 讀取站點, bash 裸解析站點)`——皆為 `rel:行號: 原行`。

    逐行剝 `#` 註解尾再判（與本檔第一道判準同一個 heuristic 與同一組取捨）；
    行尾 `# ps-xplat-ok: <WHY>` 豁免。
    """
    env_sites: list[str] = []
    bash_sites: list[str] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _PS_SITE_OK_MARKER in line:
            continue
        code = line.split("#", 1)[0]
        if _WINDOWS_ONLY_ENV_READ_RE.search(code):
            env_sites.append(f"{rel}:{lineno}: {line.strip()[:110]}")
        if _BASH_RESOLUTION_RE.search(code):
            bash_sites.append(f"{rel}:{lineno}: {line.strip()[:110]}")
    return env_sites, bash_sites


class TestPowerShellPlatformSensitiveSites(unittest.TestCase):
    """PowerShell 側的站點級跨平台判準（見上方 WHY）。"""

    def _scan_all(self) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        env_by_file: dict[str, list[str]] = {}
        bash_by_file: dict[str, list[str]] = {}
        scripts = _active_ps_scripts()
        # 下限＝落地當回合實測 20 支的八折。全庫 `.ps1` 有一百多支，但絕大多數住在凍結版
        # SDD 樹（本判準刻意不掃：Copy-on-Evolve 禁改，判了也只能開白名單）。
        self.assertGreater(len(scripts), 15,
                           f"活躍 PowerShell 腳本只掃到 {len(scripts)} 支 ⇒ 掃描面疑似縮小")
        for rel in scripts:
            source = (_REPO_ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")
            env_sites, bash_sites = scan_ps_platform_sites(source, rel)
            if env_sites:
                env_by_file[rel] = env_sites
            if bash_sites:
                bash_by_file[rel] = bash_sites
        return env_by_file, bash_by_file

    def test_windows_only_temp_env_reads_are_all_accounted_for(self) -> None:
        env_by_file, _bash = self._scan_all()
        self.assertEqual(
            sorted(env_by_file), sorted(_WINDOWS_ONLY_ENV_DEBT),
            "`$env:TEMP`／`$env:TMP` 讀取站點與登記不符。多出來的是**新增**曝險"
            "（macOS/Linux 的 PS Core 上這兩個變數不存在，`Join-Path $env:TEMP …` 會直接"
            "拋 null 綁定例外）——請改用 `[System.IO.Path]::GetTempPath()`；少掉的表示"
            "已修好，請自 `_WINDOWS_ONLY_ENV_DEBT` 刪除。\n"
            + "\n".join(s for sites in env_by_file.values() for s in sites),
        )

    def test_bash_is_only_resolved_through_the_ssot(self) -> None:
        _env, bash_by_file = self._scan_all()
        offenders = {rel: sites for rel, sites in bash_by_file.items()
                     if rel != _BASH_RESOLUTION_SSOT}
        self.assertEqual(
            offenders, {},
            f"裸 `Get-Command bash` 只能出現在 `{_BASH_RESOLUTION_SSOT}`（唯一 SSOT，含"
            " system32／WSL 佔位版逐段排除）。本機實測裸解析拿到的是 WSL 佔位版，且反斜線"
            "路徑的分隔符會被吃掉（DEF-101-617/618）。請改用該 SSOT：\n"
            + "\n".join(f"{rel}: {sites}" for rel, sites in offenders.items()),
        )

    def test_the_ssot_itself_is_still_the_one_doing_the_resolution(self) -> None:
        """反空轉：SSOT 自己必須仍然命中，否則上一條是在對空集合宣布勝利。"""
        _env, bash_by_file = self._scan_all()
        self.assertIn(
            _BASH_RESOLUTION_SSOT, bash_by_file,
            f"{_BASH_RESOLUTION_SSOT} 內找不到 `Get-Command bash` ⇒ 要嘛 SSOT 換了實作"
            "（請把本判準的錨改掉），要嘛正則失效而整條判準已對全庫恆綠")

    def test_the_two_criteria_have_teeth(self) -> None:
        """判準紅綠自證（合成字串）。"""
        env_sites, bash_sites = scan_ps_platform_sites(
            "$tmp = Join-Path $env:TEMP 'x'\n"
            "$b = Get-Command bash -ErrorAction SilentlyContinue\n", "fixture.ps1")
        self.assertEqual((len(env_sites), len(bash_sites)), (1, 1))
        # 賦值不是讀取；`$env:TEMPDIR` 不是 TEMP；註解行與豁免標記行都不算
        clean, clean_bash = scan_ps_platform_sites(
            "$env:TEMP = 'tmpdir'\n"
            "$v = $env:TEMPDIR\n"
            "# $tmp = Join-Path $env:TEMP 'x'\n"
            f"$t = $env:TEMP  # {_PS_SITE_OK_MARKER} 合成豁免樣本\n"
            "$g = Get-Command bashful\n", "fixture.ps1")
        self.assertEqual((clean, clean_bash), ([], []))


# ══════════════════════════════════════════════════════════════════════════════
# R80（包 B / S4-01）— 鐵律三對照表：「無機械物」必須是**可證偽**的宣稱
# ══════════════════════════════════════════════════════════════════════════════
# 缺陷本體與判準設計全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈鐵律三無機械物證偽判準 WHY〉節。
_IRON_LAW3_MECHANISM_HOMES: tuple[str, ...] = (
    "tools/*.py", "tools/lib/*.py", "tools/tests/*.py", "tools/probe/*.py",
    ".claude/hooks/*.py", "AutoClaude/tools/hooks/*.py", "AutoClaude/tests/*.py",
)
#: 定義行／模組層常數名（機械物的識別字住所）。
_MECHANISM_DEF_RE = re.compile(
    r"^\s*(?:async\s+)?(?:def|class)\s+(\w+)|^(_?[A-Z][A-Z0-9_]{2,})\s*[:=]")
#: {表上的觸發項關鍵字: (證偽 token, {已審視並判定不算的檔案: 為什麼不算})}
#: 🔴 這張表與 CLAUDE.md 那張表**雙向**綁死（見下方兩條判準）：表上多一列「無機械物」
#: 卻沒登記探針 → 紅（不得靠新增一列來閃過證偽）；登記了探針而表上那列已補上機械物
#: → 紅（stale，考察軌跡不得靠慣性活著）。
_IRON_LAW3_UNCOVERED_EVIDENCE: dict[str, tuple[tuple[str, ...], dict[str, str]]] = {
    "副檔名判斷": (("副檔名", "file_extension", "extension_branch", "exe_suffix"), {}),
    # 🔴 R85：`shell=True` 那一格**已補上機械物**（`AutoClaude/tests/execution/
    # test_shell_portability_contract_r85.py`），依本表下方的 stale 判準，探針必須隨之移除
    # ——「考察軌跡不得靠慣性活著」。它原本登記的兩筆「已審視並判定不算」（kill-tree 那支
    # 守逾時回收、console-spawn 那兩支守 Windows 彈窗）判讀**至今仍成立**，移除的理由不是
    # 它們被推翻，而是本表只服務「自陳沒有掃描器」的列。
}
#: 已知正例：本判準若對它失明，整條就是裝飾品。這組 token 指向的正是 S4-01 那一格
#: 被填錯的機械物本體（NTFS 大小寫碰撞鍵）。
_IRON_LAW3_KNOWN_POSITIVE_TOKENS: tuple[str, ...] = ("collision", "casefold", "大小寫")
_IRON_LAW3_KNOWN_POSITIVE_FILE = "tools/check_ntfs_paths.py"


def mechanism_definition_names(repo_root: Path) -> list[tuple[str, int, str]]:
    """機械物住所內所有 `(檔案, 行號, 識別字)`。現查，不寫死清單。"""
    out: list[tuple[str, int, str]] = []
    for glob in _IRON_LAW3_MECHANISM_HOMES:
        for path in sorted(repo_root.glob(glob)):
            rel = path.relative_to(repo_root).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), start=1):
                match = _MECHANISM_DEF_RE.match(line)
                if match:
                    out.append((rel, lineno, match.group(1) or match.group(2)))
    return out


def falsifying_hits(
    names: list[tuple[str, int, str]], tokens: tuple[str, ...], considered: dict[str, str]
) -> list[str]:
    """回傳「反證」清單：命中 token 且不在已審視檔案內的識別字。"""
    lowered = tuple(t.lower() for t in tokens)
    return [
        f"{rel}:{lineno}: `{name}`"
        for rel, lineno, name in names
        if rel not in considered and any(t in name.lower() for t in lowered)
    ]


class TestIronLaw3NoMechanismClaimsAreFalsifiable(unittest.TestCase):
    """鐵律三對照表的每一格「無機械物」都必須經得起證偽（見上方 WHY）。"""

    @staticmethod
    def _table_rows() -> list[list[str]]:
        import test_doc_loc_baseline_freshness_r60 as _acct  # noqa: PLC0415
        return _acct.iron_law3_trigger_rows(
            (_REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8-sig"))

    def _uncovered_first_cells(self) -> list[str]:
        return [cells[0] for cells in self._table_rows() if "無機械物" in cells[1]]

    def test_the_probe_has_discriminating_power_on_a_known_positive(self) -> None:
        """自錨（先看這一條）：拿 S4-01 那格真實存在的機械物餵進去，必須被找出來。

        少了這一條，下面兩條在「識別字掃描其實壞掉、永遠回空」時仍然全綠——而那正是
        本檔一貫在防的「靜默縮面」。
        """
        names = mechanism_definition_names(_REPO_ROOT)
        self.assertGreater(len(names), 800,
                           f"機械物住所只抽到 {len(names)} 個識別字 ⇒ 掃描面疑似壞掉")
        hits = falsifying_hits(names, _IRON_LAW3_KNOWN_POSITIVE_TOKENS, {})
        self.assertTrue(
            any(h.startswith(_IRON_LAW3_KNOWN_POSITIVE_FILE + ":") for h in hits),
            f"已知正例（{_IRON_LAW3_KNOWN_POSITIVE_FILE} 的大小寫碰撞鍵）沒被找出來 ⇒ "
            f"本判準對「表說沒有、實際有」這個方向是裝飾品。現有命中：{hits[:10]}")

    def test_every_no_mechanism_row_survives_its_own_falsification_probe(self) -> None:
        """缺陷本體那一向：宣稱「無機械物」而其實有 ⇒ 紅。"""
        names = mechanism_definition_names(_REPO_ROOT)
        problems: list[str] = []
        for cell in self._uncovered_first_cells():
            keys = [k for k in _IRON_LAW3_UNCOVERED_EVIDENCE if k in cell]
            if not keys:
                problems.append(
                    f"「{cell}」列自陳無機械物，卻沒有登記證偽探針 ⇒ 這一格的宣稱不可被"
                    "反駁。請在 `_IRON_LAW3_UNCOVERED_EVIDENCE` 補一組 token"
                    "（新增一列來閃過證偽是本判準第一個要擋的動作）")
                continue
            for key in keys:
                tokens, considered = _IRON_LAW3_UNCOVERED_EVIDENCE[key]
                hits = falsifying_hits(names, tokens, considered)
                if hits:
                    problems.append(
                        f"「{cell}」列自陳無機械物，但機械物住所裡有識別字命中 {tokens}："
                        f"{hits[:6]} ⇒ 要嘛它其實有人在守（請改機械物欄，分子 +1），"
                        "要嘛那幾支守的是別的主題（請寫進 "
                        "`_IRON_LAW3_UNCOVERED_EVIDENCE` 的已審視清單並寫明為什麼不算）")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_the_evidence_registry_does_not_rot(self) -> None:
        """反向：登記了探針、表上那列卻已經有機械物（或整列不見了）⇒ stale。"""
        uncovered = self._uncovered_first_cells()
        self.assertTrue(uncovered, "表上一列『無機械物』都沒有？請確認表頭與解析仍相符")
        stale = [key for key in _IRON_LAW3_UNCOVERED_EVIDENCE
                 if not any(key in cell for cell in uncovered)]
        self.assertEqual(
            stale, [],
            f"這些證偽探針已 stale（表上對應列已補機械物或已被刪）：{stale}"
            "——請一併刪除，考察軌跡不得靠慣性活著")
        for key, (tokens, considered) in _IRON_LAW3_UNCOVERED_EVIDENCE.items():
            self.assertTrue(tokens, f"「{key}」的 token 是空的 ⇒ 探針恆不命中＝假綠")
            for rel, why in considered.items():
                self.assertTrue(
                    (_REPO_ROOT / rel).is_file(),
                    f"「{key}」的已審視檔案 {rel} 已不存在（WHY={why}）⇒ 請自清單移除")
                self.assertGreater(len(why), 10, f"{rel} 的『為什麼不算』寫得太短")

    def test_the_probe_would_catch_a_freshly_planted_mechanism(self) -> None:
        """注入自證：合成一個「表說沒有、其實有」的狀態，必須紅。"""
        names = [("tools/pretend_scanner.py", 12, "scan_file_extension_platform_branch")]
        self.assertTrue(
            falsifying_hits(names, ("file_extension",), {}),
            "新植入的機械物沒被找出來 ⇒ 低報分子那一向仍然失明")
        self.assertEqual(
            falsifying_hits(names, ("file_extension",),
                            {"tools/pretend_scanner.py": "已審視：守的是別的主題"}),
            [], "已審視清單沒有生效 ⇒ 這道鎖無法容納「同關鍵字、不同主題」而必被關掉")


# ══════════════════════════════════════════════════════════════════════════════
# R81（包 G）— 兩個「今天存量是 0／已清空、缺的是門」的跨平台危害類
# ══════════════════════════════════════════════════════════════════════════════
# 兩者共同性質與缺陷本體全文搬至
# docs/06_quality/CrossPlatform_Guard_Line_History.md〈R81 包 G 路徑列舉排序鍵判準
# WHY〉節。

_QUOTEPATH_SAFE_TOKENS = ("core.quotepath=false", "-z")
#: 行尾豁免標記。本區塊的 `#` 註解**刻意不逐字寫出它**——`#` 是 COMMENT token，而取標記
#: 的函式只認 COMMENT ⇒ 在註解裡「提到」與「登記」在機器眼中同形（同本檔編碼家族已
#: 踩過的坑）。要引述請寫進 docstring 或字串字面值。
_QUOTEPATH_OK_MARKER = "quotepath-ok:"
_QUOTEPATH_MARKER_RE = re.compile(r"(?<![\w-])" + re.escape(_QUOTEPATH_OK_MARKER))
#: 會**列舉路徑**的 git 子指令。`diff` 另需 `--name-only`／`--name-status` 才算列舉。
_GIT_PATH_ENUM_SUBCMDS = ("ls-files", "ls-tree")
_GIT_DIFF_NAME_FLAGS = ("--name-only", "--name-status")
_GIT_ENUM_EXTS = (".py", ".sh", ".bash", ".yml", ".yaml")
_FROZEN_SDD_RE = re.compile(r"^AISDLC_SDD/AISDLC_SDD_v0\.(?:0[1-9]|1\d|2\d)/")


def _quotepath_markers(source: str, *, is_python: bool) -> dict[int, str]:
    """{行號: WHY}——`.py` 只認 COMMENT token，其餘檔型（`.sh`／`.yml`）走行掃描。

    🔴 `.py` 非走 tokenize 不可：本判準的射程含**它自己**，而偵測器原始碼必然多處逐字
    提到標記字串（常數定義、docstring、紅綠自證的合成樣本）。落地當回合實測，行掃描版
    當場把常數定義那一行判成一個真標記並回報 stale ⇒ 鎖因為「說明自己」而翻紅
    （本檔編碼家族的 `_encoding_markers` 為同一個理由早就走 tokenize）。
    """
    markers: dict[int, str] = {}
    if is_python:
        try:
            for tok in tokenize.generate_tokens(io.StringIO(source).readline):
                if tok.type != tokenize.COMMENT:
                    continue
                found = _QUOTEPATH_MARKER_RE.search(tok.string)
                if found:
                    markers[tok.start[0]] = tok.string[found.end():].strip()
        except (tokenize.TokenError, IndentationError, SyntaxError):
            markers.clear()
        return markers
    for lineno, line in enumerate(source.splitlines(), 1):
        comment = line.split("#", 1)[1] if "#" in line else ""
        found = _QUOTEPATH_MARKER_RE.search(comment)
        if found:
            markers[lineno] = comment[found.end():].strip()
    return markers


def _argv_string_consts(node: ast.List | ast.Tuple) -> list[str]:
    return [e.value for e in node.elts
            if isinstance(e, ast.Constant) and isinstance(e.value, str)]


def argv_enumerates_git_paths(consts: list[str]) -> bool:
    """這串 argv 是不是「叫 git 列舉路徑」？（純函式，供紅綠自證直接餵）"""
    low = [c.lower() for c in consts]
    if not any(c == "git" or c.endswith("/git") or c.endswith("git.exe") for c in low):
        return False
    if any(c in _GIT_PATH_ENUM_SUBCMDS for c in low):
        return True
    return "diff" in low and any(f in low for f in _GIT_DIFF_NAME_FLAGS)


def argv_is_quotepath_safe(consts: list[str]) -> bool:
    """帶了 `-c core.quotepath=false`（大小寫不拘）或 `-z` 就算安全。"""
    low = [c.lower() for c in consts]
    return any(tok in c for c in low for tok in _QUOTEPATH_SAFE_TOKENS)


def scan_git_path_enumeration(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)。

    `.py` 走 AST（只認 list／tuple 字面 argv——那是本 repo 全部 git 呼叫的形態，
    而散文裡提到 `git ls-files` 的行有上百處，行掃描會全部誤報）；
    其餘檔型走剝註解後的行掃描。
    """
    markers = _quotepath_markers(source, is_python=rel.endswith(".py"))
    offenders: list[str] = []
    used: set[int] = set()
    if rel.endswith(".py"):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return [], []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple)):
                continue
            consts = _argv_string_consts(node)
            if not argv_enumerates_git_paths(consts) or argv_is_quotepath_safe(consts):
                continue
            span = range(node.lineno, (node.end_lineno or node.lineno) + 1)
            marked = next((ln for ln in span if markers.get(ln)), None)
            if marked is not None:
                used.add(marked)
                continue
            offenders.append(
                f"{rel}:{node.lineno}: `git {' '.join(consts[:6])}…` 列舉路徑卻沒帶 "
                "`-c core.quotepath=false`（也沒用 `-z`）⇒ 非 ASCII 路徑會回 C-quoted "
                "形態，消費端拿到的是打不開的字串，掃描面**靜默縮小**")
    else:
        for lineno, line in enumerate(source.splitlines(), 1):
            code = line.split("#", 1)[0]
            if not re.search(r"(?<![\w-])git\b", code):
                continue
            enumerates = bool(re.search(r"\b(?:ls-files|ls-tree)\b", code)) or (
                re.search(r"\bdiff\b", code) and re.search(r"--name-(?:only|status)", code))
            if not enumerates:
                continue
            if re.search(r"quotepath\s*=\s*false", code, re.I) or re.search(
                    r"(?<![\w-])-z(?![\w-])", code):
                continue
            if markers.get(lineno):
                used.add(lineno)
                continue
            offenders.append(
                f"{rel}:{lineno}: git 路徑列舉未帶 `-c core.quotepath=false`／`-z`："
                f"{code.strip()[:100]}")
    stale = [
        f"{rel}:{lineno}: {_QUOTEPATH_OK_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
        for lineno, why in sorted(markers.items())
        if lineno not in used or not why
    ]
    return offenders, stale


def _git_enum_scan_files() -> list[str]:
    """掃描面＝active（非凍結版）tracked 的 `.py`／`.sh`／`.yml` 家族。

    取數自己走 `git_paths`（不然本判準的掃描面會被它正在防的那個缺陷咬到）。
    """
    tracked = git_paths.ls_files(_REPO_ROOT)
    if not tracked:
        raise AssertionError(
            "`git ls-files` 回空 ⇒ 取數管道壞掉，本判準的結論無效（不是「零違規」）")
    return sorted(rel for rel in tracked
                  if rel.endswith(_GIT_ENUM_EXTS) and not _FROZEN_SDD_RE.match(rel))


#: 🔴 存量登記（落地當回合：15 個違規站點修到剩 3 個，散在下列 2 支檔）。
#: 判準是**雙向**的：出現不在表上的檔＝紅（新站點漏帶旗標）；表上的檔已經不再違規＝
#: 也紅（債還了請把列刪掉，不刪的話下一筆新違規會被舊列遮住）。
#: 兩列都不是「懶得修」，是**修了會弄壞別的東西**——這正是本表要讓人看見的東西。
_GIT_QUOTEPATH_DEBT: dict[str, str] = {
    "AutoClaude/autoclaude/decision/prompt_builder.py": (
        "`git diff --name-only HEAD`（:136）。不在本包所有權內（AutoClaude/autoclaude/**）"
        "故不代改；危害面是 prompt 裡的『這次改了哪些檔』清單會對非 ASCII 檔名失真，"
        "不影響閘門正確性 ⇒ 列為可見欠債而非阻塞"
    ),
    "AISDLC_SDD/AISDLC_SDD_v0.30/.github/workflows/hub-push.yml": (
        "`git diff --name-only`（:75／:215 兩處）。**刻意不改**：`tools/check_gha_action_"
        "versions.py` 檔頭逐字記載『各版此檔為同一 git blob』是一個目前可機械核對的"
        "不變量，只改 LATEST 這一份會讓它首次分裂，而那個決定的擁有者是 AISDLC_SDD "
        "凍結／LATEST 政策側，不是本包。要修就得 30 版一起改（＝打破 Copy-on-Evolve）"
    ),
}


class TestGitPathEnumerationIsQuotepathSafe(unittest.TestCase):
    """git 路徑列舉必須關掉 C-quoted 輸出（見上方區段 WHY ①）。"""

    @classmethod
    def _scan_repo(cls) -> tuple[dict[str, list[str]], list[str], int]:
        per_file: dict[str, list[str]] = {}
        stale: list[str] = []
        rels = _git_enum_scan_files()
        for rel in rels:
            path = _REPO_ROOT / rel
            try:
                source = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            off, st = scan_git_path_enumeration(source, rel)
            if off:
                per_file.setdefault(rel, []).extend(off)
            stale.extend(st)
        return per_file, stale, len(rels)

    def test_new_git_path_enumeration_sites_declare_quotepath(self) -> None:
        per_file, stale, scanned = self._scan_repo()
        self.assertGreater(
            scanned, 900,
            f"掃描面只有 {scanned} 支檔 ⇒ 疑似靜默縮面（落地當回合實測 >1,100）")
        unregistered = sorted(rel for rel in per_file if rel not in _GIT_QUOTEPATH_DEBT)
        self.assertEqual(
            unregistered, [],
            "以下檔案新增了未關引號化的 git 路徑列舉——請改走 `tools/lib/git_paths.py`"
            f"（或自己補 `-c core.quotepath=false`／`-z`），刻意為之則於該行行尾加標記"
            f"（`{_QUOTEPATH_OK_MARKER}` ＋ WHY）：\n"
            + "\n".join(line for rel in unregistered for line in per_file[rel]))
        settled = sorted(rel for rel in _GIT_QUOTEPATH_DEBT if rel not in per_file)
        self.assertEqual(
            settled, [],
            f"這些欠債已經還了：{settled} ⇒ 請把它們從 `_GIT_QUOTEPATH_DEBT` 刪掉。"
            "不刪的話這張表會變成永久保護傘，下一筆新違規會被舊列遮住")
        self.assertEqual(
            stale, [],
            f"{_QUOTEPATH_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale))

    # ── 紅綠自證：合成注入（不留違規樣本於 repo）──────────────────────────────

    def test_injected_unsafe_argv_is_detected(self) -> None:
        for rel, source in (
            ("probe.py", 'subprocess.run(["git", "-C", root, "ls-files", "-s"])\n'),
            ("probe.py", 'run(["git", "diff", "--name-only", "HEAD"])\n'),
            ("probe.py", 'run(("git", "ls-tree", "-r", "HEAD"))\n'),
            ("probe.sh", 'files="$(git ls-files -- "*.py")"\n'),
            ("probe.yml", "        run: git diff --name-only HEAD > out.txt\n"),
        ):
            with self.subTest(rel=rel, source=source):
                off, stale = scan_git_path_enumeration(source, rel)
                self.assertTrue(off, f"{source!r} 漏抓 ⇒ 本判準無牙")
                self.assertEqual(stale, [])

    def test_the_safe_forms_stay_green(self) -> None:
        for rel, source in (
            ("probe.py",
             'run(["git", "-C", root, "-c", "core.quotepath=false", "ls-files"])\n'),
            ("probe.py", 'run(["git", "-c", "core.quotePath=false", "ls-files"])\n'),
            ("probe.py", 'run(["git", "ls-files", "-z"])\n'),
            ("probe.py", 'run(["git", "-C", root, "status", "--porcelain"])\n'),
            ("probe.py", "proc = git_paths.run(root, 'ls-files', '-s')\n"),
            ("probe.sh", 'git -c core.quotePath=false ls-files --eol\n'),
            ("probe.yml", "        run: git ls-files -z | xargs -0 wc -l\n"),
        ):
            with self.subTest(rel=rel, source=source):
                off, stale = scan_git_path_enumeration(source, rel)
                self.assertEqual((off, stale), ([], []), f"{source!r} 誤報")

    def test_prose_mentions_are_not_uses(self) -> None:
        """`.py` 走 AST ⇒ 散文提到 `git ls-files` 不算使用（全庫實測上百處）。"""
        off, stale = scan_git_path_enumeration(
            '"""掃描面以 git ls-files 取得，git diff --name-only 亦同。"""\n'
            "# 註解裡的 git ls-files 也不算\n", "probe.py")
        self.assertEqual((off, stale), ([], []))

    def test_the_line_tail_marker_suppresses_and_rots_loudly(self) -> None:
        marked = ('run(["git", "ls-files"])  # ' + _QUOTEPATH_OK_MARKER
                  + " 對照組刻意打開引號化\n")
        self.assertEqual(scan_git_path_enumeration(marked, "probe.py"), ([], []))
        empty_why = 'run(["git", "ls-files"])  # ' + _QUOTEPATH_OK_MARKER + "\n"
        off, stale = scan_git_path_enumeration(empty_why, "probe.py")
        self.assertTrue(off, "WHY 留空的標記不得有豁免力")
        self.assertTrue(stale, "WHY 留空必須另列 stale")
        orphan = "x = 1  # " + _QUOTEPATH_OK_MARKER + " 已改寫後忘了拆標記\n"
        self.assertTrue(scan_git_path_enumeration(orphan, "probe.py")[1], "孤兒標記未判 stale")

    def test_the_hazard_is_reproducible_here_without_relying_on_dot_git_config(self) -> None:
        """🔴 判準的**前提**必須在本機就能證實，而不是引述別台機器的行為。

        本 repo 的 `.git/config` 帶著 `core.quotepath=false`（未追蹤、不隨 repo 走），
        所以直接對本 repo 取數是看不到危害的——那正是這個缺陷藏了很多輪的原因。
        這裡改在**臨時 repo** 裡以 `-c core.quotepath=true` 明文構造對照組：
        同一個檔名在兩種設定下取回的字串不同，且引號化那一版 `is_file()` 為 False。
        臨時 repo 讓本測試在 mac／Linux／fresh clone 上結論一致（不依賴任何本機設定）。
        """
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            init = subprocess.run(["git", "init", "-q", str(repo)],
                                  capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            self.assertEqual(init.returncode, 0, f"git init 失敗：{init.stderr}")
            target = repo / "非ASCII路徑.md"
            target.write_text("x\n", encoding="utf-8")
            add = subprocess.run(["git", "-C", str(repo), "add", "-A"],
                                 capture_output=True, text=True,
                                 encoding="utf-8", errors="replace")
            self.assertEqual(add.returncode, 0, f"git add 失敗：{add.stderr}")

            def listing(quotepath: str) -> list[str]:
                argv = ["git", "-C", str(repo),  # quotepath-ok: 對照組必須能明文打開引號化
                        "-c", f"core.quotepath={quotepath}", "ls-files"]
                proc = subprocess.run(
                    argv, capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                return [ln for ln in proc.stdout.splitlines() if ln]

            quoted, plain = listing("true"), listing("false")
            self.assertNotEqual(
                quoted, plain,
                "非 ASCII 路徑在 quotepath=true／false 下取回同一個字串 ⇒ 本判準的前提"
                "在這個 git 版本上不成立，請重新確認（不要因為它綠了就當它有效）")
            self.assertTrue(quoted[0].startswith('"'), f"預期 C-quoted 形態，實得 {quoted[0]!r}")
            self.assertFalse(
                (repo / quoted[0]).is_file(),
                "C-quoted key 竟然打得開？那本判準守的東西就不存在，請重查")
            self.assertTrue((repo / plain[0]).is_file(), "關掉引號化後應該拿得到真實檔案")
            # 取數層 SSOT 走的就是安全那一版。
            self.assertEqual(git_paths.ls_files(repo), plain)
            self.assertIn("core.quotepath=false", git_paths.git_argv(repo, "ls-files"))


# ── XPL-S1-06：排序鍵餵進 digest 時必須平台中立 ────────────────────────────────
_PATH_PRODUCER_ATTRS = frozenset({"glob", "rglob", "iterdir"})


def digest_sort_problems(source: str, rel: str) -> list[str]:
    """`for … in sorted(<glob/rglob/iterdir>)` 且迴圈體餵 digest，卻沒帶 `key=`。"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.AsyncFor)):
            continue
        it = node.iter
        if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                and it.func.id == "sorted" and it.args):
            continue
        if any(kw.arg == "key" for kw in it.keywords):
            continue
        produces_paths = any(
            isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
            and sub.func.attr in _PATH_PRODUCER_ATTRS for sub in ast.walk(it.args[0]))
        feeds_digest = any(
            isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == "update" for sub in ast.walk(node))
        if produces_paths and feeds_digest:
            problems.append(
                f"{rel}:{node.lineno}: `sorted(<路徑產生器>)` 未帶 `key=`，而排序結果"
                "直接餵進 digest ⇒ 這個雜湊是**平台相依**的（Windows case-fold／POSIX "
                "原字元序）。請改 `key=lambda p: p.relative_to(root).as_posix()`")
    return problems


class TestDigestSortKeyIsPlatformNeutral(unittest.TestCase):
    """排序影響雜湊時，排序鍵必須平台中立（見上方區段 WHY ②）。"""

    def test_the_ordering_hazard_is_real_and_machine_independent(self) -> None:
        """機制自證：同一批檔名在兩種 flavour 下排序結果不同（不依賴當前平台）。"""
        sample = ["README.md", "readme_extra.md", "Test_A.py", "test_b.py"]
        self.assertNotEqual(
            sorted(sample, key=PureWindowsPath), sorted(sample, key=PurePosixPath),
            "兩種 flavour 排出同樣的順序 ⇒ 本判準的前提在這個 Python 版本上不成立")

    def test_no_digest_fed_sort_lacks_an_explicit_key(self) -> None:
        problems: list[str] = []
        scanned = 0
        for path in _encoding_scan_files():
            rel = path.relative_to(_REPO_ROOT).as_posix()
            problems.extend(digest_sort_problems(
                path.read_text(encoding="utf-8-sig", errors="replace"), rel))
            scanned += 1
        self.assertGreater(scanned, 700, f"掃描面只有 {scanned} 支 ⇒ 疑似縮面")
        self.assertEqual(
            problems, [],
            "以下站點的雜湊會隨平台改變（`DEF-101-613` 只關了行尾那一個入口，"
            "排序是第二個）：\n" + "\n".join(problems))

    def test_injected_digest_sort_without_key_is_detected(self) -> None:
        off = digest_sort_problems(
            "def f(root):\n"
            "    d = hashlib.sha256()\n"
            "    for p in sorted(root.glob('**/*.py')):\n"
            "        d.update(p.read_bytes())\n", "probe.py")
        self.assertEqual(len(off), 1, off)

    def test_the_fixed_form_and_unrelated_sorts_stay_green(self) -> None:
        for source in (
            # 正解：明示平台中立的鍵
            "def f(root):\n"
            "    d = hashlib.sha256()\n"
            "    for p in sorted(root.glob('*.py'), key=lambda q: q.as_posix()):\n"
            "        d.update(p.read_bytes())\n",
            # 排序但不餵 digest（148 筆存量的絕大多數就是這種，不得誤報）
            "def f(root):\n    for p in sorted(root.glob('*.py')):\n        print(p)\n",
            # 餵 digest 但不是排序路徑
            "def f(items):\n"
            "    d = hashlib.sha256()\n"
            "    for x in sorted(items):\n        d.update(x)\n",
        ):
            with self.subTest(source=source):
                self.assertEqual(digest_sort_problems(source, "probe.py"), [], source)


if __name__ == "__main__":
    # R78：本檔被當 entry point 直接起（M5 的載具出口就在 TestXplatInjectionMatrix
    # 的 setUpClass），而檔內多處印中文 ⇒ `test_subprocess_encoding_hygiene` 判準要求
    # 入口點自帶 UTF-8 stdio 保護（非 CJK locale 逃脫成 \uXXXX、非 UTF-8 locale 亂碼、
    # stdout 更是 errors='strict' 直接崩潰）。用唯一實作而非就地 reconfigure，理由同
    # `test_adr_xplat001_c1c2_lock.py` 檔尾：後者會讓 stdio 複本棘輪 +1。
    # 放在 `__main__` 內 ⇒ 被當測試模組 import 時不付這個副作用代價。
    sys.path.insert(0, str(_REPO_ROOT / "tools"))
    import _stdio_utf8  # noqa: F401
    unittest.main()
