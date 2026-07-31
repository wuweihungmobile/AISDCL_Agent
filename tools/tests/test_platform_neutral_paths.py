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
import io
import re
import sys
import tempfile
import tokenize
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402

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
}
_OK_MARKER = "platform-ok:"
_EXPLICIT_PLATFORM = ("PureWindowsPath(", "PurePosixPath(")


def _latest_fsm_tests_dir() -> Path:
    """LATEST 版 fsm_runtime/tests（sdd_version.py SSOT；解析失敗即 AssertionError）。
    委派 tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    latest_root = sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")
    return latest_root / "tools" / "fsm_runtime" / "tests"


def _scan_roots() -> list[tuple[Path, bool, int]]:
    """（掃描根, 是否遞迴, 該樹檔數下限）清單；根缺席或低於下限由測試 fail-loud。

    per-tree 下限（R12 SD 一審 SD-3）：全域總數下限對「單樹靜默縮面」不敏感
    （如 LATEST 樹 rglob 被改 glob，總數 377→303 仍過全域 200）；逐樹釘選使任一
    樹縮面必紅。下限＝2026-07-18 實測實掃數（13/19/271/74；AutoClaude 樹總檔 272
    扣除 _ALLOWED 豁免 1 檔——斷言對象為排除豁免後的實掃數）打八折取整，隨基線上修。"""
    return [
        (_TESTS_DIR, False, 10),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts" / "tests", False, 15),
        (_REPO_ROOT / "AutoClaude" / "tests", True, 217),
        (_latest_fsm_tests_dir(), True, 59),
    ]


def _scan_file(py: Path) -> list[str]:
    offenders: list[str] = []
    rel = py.relative_to(_REPO_ROOT).as_posix()
    for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), start=1):
        if _OK_MARKER in line:  # (c) 行尾豁免標記（附理由）
            continue
        code = line.split("#", 1)[0]  # (a) 剝註解尾（heuristic，見 docstring）
        if any(tok in code for tok in _EXPLICIT_PLATFORM):  # (b) 顯式平台語意
            continue
        if _DRIVE_STR_RE.search(code):
            offenders.append(f"{rel}:{lineno}: {line.strip()}")
    return offenders


class TestPlatformNeutralPaths(unittest.TestCase):
    def test_no_windows_drive_fake_paths(self) -> None:
        offenders: list[str] = []
        for root, recursive, floor in _scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = root.rglob("*.py") if recursive else root.glob("*.py")
            tree_scanned = 0
            for py in sorted(files):
                if py.relative_to(_REPO_ROOT).as_posix() in _ALLOWED:
                    continue
                offenders.extend(_scan_file(py))
                tree_scanned += 1
            # per-tree 下限釘選（SD-3）：單樹縮面必紅，不被他樹總量掩蓋
            self.assertGreaterEqual(
                tree_scanned, floor,
                f"{root} 掃描檔數 {tree_scanned} < 下限 {floor}——該樹掃描面疑似縮小",
            )
        self.assertEqual(
            offenders,
            [],
            "發現 Windows 磁碟機假路徑字面值（POSIX 上非絕對路徑 → join 語意分歧假紅）"
            "——請改用 tools/tests/_platform_helpers.ABS_FAKE_REPO；確屬合法用法時，"
            "改寫為顯式 PureWindowsPath(…) 或行尾加 `# platform-ok: <理由>` 豁免：\n"
            + "\n".join(offenders),
        )

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
# WHY（這是本檔第二道判準，與磁碟機假路徑正交，但同屬「測試原始碼的路徑寫法」家族，
# 故共用本檔的掃描根／豁免／stale 慣例，不另開新檔）：
#   `tools/fsm_runtime/tests/test_slv_generator.py` 的四個測試類把暫存規則目錄寫死成
#   `Path(__file__).resolve().parent / "_tmp_*"`——**tracked 樹內的共用固定路徑**，且
#   `setUp` 清空它、`tearDown` `rmdir` 它。兩個行程同時跑（並行四方複審／並行閘門／
#   CI 與地端同時跑）必互刪，產生與被測邏輯無關的假紅：
#     · `FileNotFoundError: ..._tmp_rules\SLV-900.yaml.lock`（QA 實測，並行 2/2 重現）
#     · `PermissionError: [WinError 32] ..._tmp_rules\SLV-900.yaml`（integration_gate 實測）
#     · `FileNotFoundError: [WinError 2] ..._tmp_imm_rules\SLV-910.yaml.tmp`（ARCH 實測）
#   隔離重跑必綠 ⇒ 長期被誤讀成 flaky。本鎖把「別再這樣寫」變成機械事實。
#   修法慣例＝`tempfile.mkdtemp()`（根治：兩行程拿到不同目錄）；只加
#   `unlink(missing_ok=True)` **不算**修好——那只讓競態不拋例外，資料仍互相污染。
#
# 判準（AST，非行級 regex）：對「寫入類呼叫」的目標表達式判斷它是否指向樹內固定路徑：
#   寫入動作＝`.mkdir/.write_text/.write_bytes/.touch/.unlink/.rmdir`、
#             `shutil.rmtree/copytree/move(<目標>)`、`open(<目標>, 'w'|'a'|'x'|'+')`。
#   「樹內固定路徑」＝該表達式自身含 `__file__`，或其最左名稱是**模組層常數**／
#   **同一個 class 內的 `self.<attr>`**，而該名稱曾被指派為含 `__file__` 的表達式。
#
# 🔴 刻意劃界（誠實記錄，勿超譯）：
#   ❌ **函式區域變數不追**。這不是偷懶，是為了避開一個已知會誤報的形態：本鎖的原型
#      掃描器做了跨作用域的別名傳遞，於是
#      `tools/tests/test_git_hooks_install_common.py` 內同名的 `hooks_dir`（第 152 行是
#      `_REPO_ROOT` 衍生，第 45／176 行卻是 tempdir 衍生）被整支污染成假陽性。同型病灶
#      在本 repo 已有前科（R46 `build_alias_map` 的函式→ClassDef 作用域碰撞）。
#      模組常數與 `self.<attr>` 兩種形態就足以涵蓋本缺陷家族的全部已知站點。
#   ❌ 路徑「當引數交給生產碼、由生產碼去寫」的形態不追（如 `rules_dir=self.tmp`）——
#      靜態無法判定被呼叫端是否真的寫入；實掃證實 `project_root=FIXTURE_ROOT`
#      （multimodal_validator，全檔零寫入）正是這種唯讀傳遞，追了就是假陽性。
#      本缺陷家族在此形態下仍會被 `.mkdir()` 那一半抓到，鑑別力不因此喪失。
#   ❌ `str.replace` 等與 `Path` 同名的方法刻意不納入寫入動作集合（實掃三處皆假陽性）。
#   ❌ **凍結版 v0.02~v0.29 不在掃描面**（見 `_tmpdir_scan_roots` 的 WHY）——那 95 個
#      同型站點確實存在且**未修**，是待裁決項，不是本鎖宣稱乾淨的區域。
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
    """（掃描根, 是否遞迴, 該樹檔數下限）；下限＝2026-07-29 實掃數打八折取整。

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
        (_TESTS_DIR, False, 44),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts" / "tests", False, 22),
        (_REPO_ROOT / "AutoClaude" / "tests", True, 223),
        (_latest_fsm_tests_dir(), True, 63),
        (_REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01"
         / "tools" / "fsm_runtime" / "tests", True, 43),
    ]


class TestNoInTreeWritableTmpDir(unittest.TestCase):
    """測試檔不得把 tracked 樹內固定路徑當可寫暫存區（見上方區段 WHY）。"""

    def test_no_test_writes_into_a_fixed_in_tree_path(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
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
            self.assertGreaterEqual(
                scanned, floor,
                f"{root} 掃描檔數 {scanned} < 下限 {floor}——該樹掃描面疑似縮小",
            )
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


if __name__ == "__main__":
    unittest.main()
