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
    "AutoClaude/tests/test_perception_platform_honesty.py": (
        "上一列 test_perception.py 的姊妹檔（R68 新增，測 cmd.exe 8191 字元硬上限守門）："
        "三筆命中皆為 _build_cmd_shim_line() 的輸入字串字面值，直接進字串長度計算、"
        "不進 pathlib join；且 cmd shim 本來就只在 Windows 成立，改平台中立常數即失去測意"
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
        # 🔴 R69（DEF-101-702／R68-34）：以上四棵**全是測試樹**。於是「Windows 開發者把
        # `D:/…` 字面路徑寫進生產碼」這條路在 mac 側全套護欄全綠——掃描面與缺陷面錯位。
        # R69 實測擴面後存量債為 0（原缺陷報告點名的 `_conditional_evaluator.py` 現已無
        # 命中），屬零成本擴面：現在起生產碼與測試碼受同一判準。
        # 下限＝R69 實測（203/37/16/1/14/4/79）打八折取整，隨基線上修。
        (_REPO_ROOT / "AutoClaude" / "autoclaude", True, 162),
        (_REPO_ROOT / "AutoClaude" / "tools", False, 29),
        (_REPO_ROOT / "tools", False, 12),
        (_REPO_ROOT / ".claude" / "hooks", False, 1),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts", False, 11),
        (_REPO_ROOT / "tools" / "lib", False, 3),
        # fsm_runtime 頂層（非遞迴）——其 tests/ 子樹已由上方第 4 棵覆蓋，不重複掃。
        (_latest_fsm_tests_dir().parent, False, 63),
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


# ══════════════════════════════════════════════════════════════════════════════
# R69 — 反方向：測試不得拿 POSIX 絕對路徑字面值去斷言 Path 產物
# ══════════════════════════════════════════════════════════════════════════════
# WHY（本檔第三道判準；與第一道判準是**同一個病的兩個方向**）：
#   第一道守「Windows 磁碟機字面值 → Mac 假紅」，但反方向此前**零守門**：
#   `tools/tests/test_dev_start.py:2959` 寫
#       self.assertIn("/elsewhere", printed)
#   而 `printed` 的來源是生產碼把一個 `Path` 內插進訊息字串。`Path` 的 `str()`
#   在 Windows 是 `\elsewhere\AutoClaude\…`，POSIX 字面值必然落空 →
#   **Mac/Linux 全綠、windows-compat-ci 假紅**（R68 `375f291` 實紅，run 30720156050；
#   同 commit 前一版 `24c5f34` 為 success，故確定是新增測試帶進來的病，不是環境）。
#   本輪本機無 Windows 真機 ⇒ 這種病只能靠雲端 CI 才發現，一次來回數十分鐘；本鎖把它
#   拉到 macOS 本機的 `python tools/run_root_unittests.py` 就抓到。
#   修法慣例＝把字面值換成 `str(Path(<同一個字面值常數>))`（兩平台各自正規化後比對，
#   斷言強度不降反升——鎖的是**整條路徑**而非片段），或改用 `PurePosixPath`／
#   `as_posix()` 明示語意。
#
# 判準（AST）：`*.assert*(…)` 呼叫的引數（含 keyword 值、含巢狀於 list/tuple/set/dict
#   內的元素）出現 **POSIX 絕對路徑字面值**（以單一 `/` 開頭、次字元非 `/` 非空白）。
#
# 🔴 刻意劃界（誠實記錄，勿超譯 — 沿用本檔既有慣例）：
#   ❌ **不做值流分析**。「比對對象是不是 Path 產物」靜態不可判定：病灶站點的
#      `printed` 是由 helper method 回傳的區域變數，任何合理的 Path-來源推導都追不到它
#      （實測：以「名稱曾被指派為含 Path(/resolve()/os.fspath 的運算式」為條件時，
#      本病灶站點**漏抓**）。故採「assert 家族引數出現 POSIX 絕對路徑字面值」這個
#      過寬近似——代價由下面兩條劃界壓到實測零誤報。
#   ❌ **pytest 裸 `assert` 形態不在射程**。實測四棵樹裸 assert 命中 44 筆，絕大多數
#      不是路徑（`/compact` 是 Claude Code slash 指令、`/T` `/F` `/PID` 是 tasklist 欄位、
#      `/api/config/schema` 是 URL path、`/tmp/x.yaml` 是從未 Path 化的假字串）。納入
#      即等於一上線就要開 40 餘筆白名單——那會讓本鎖淪為永久白名單，反而失去鑑別力。
#      unittest 形態涵蓋四棵樹的實際病灶家族（實掃：修前 1 筆＝真陽性、修後 0 筆）。
#   ❌ **f-string 片段不算字面值**。`f"{parent}/archive/（小寫）復活了"` 這種訊息文字
#      被 AST 拆成 Constant，形狀與路徑字面值無法區分（實測 2 筆皆為訊息文字誤報）；
#      JoinedStr 內的 Constant 一律不計。
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
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        for root, recursive, floor in _scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = sorted(root.rglob("*.py") if recursive else root.glob("*.py"))
            scanned = 0
            for py in files:
                rel = py.relative_to(_REPO_ROOT).as_posix()
                try:
                    off, st = scan_posix_abs_asserts(py.read_text(encoding="utf-8"), rel)
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
# WHY（與上一道判準是**同一個病的另一個入口**）：
#   上一道守「斷言側寫死 POSIX 字面值」，但病也可以從**被斷言的那一側**進來：
#       printed = " ".join(str(c) for c in fake_print.call_args_list)   # ← c 是 mock.call
#   `str(mock.call(x))` 走的是 `repr`，於是字串裡的反斜線被轉義成 `\\`、換行變成
#   `\n` 兩個字元。Windows 上生產碼印出的 `Path` 是 `\elsewhere\AutoClaude\…`，
#   拼進 repr 後變成 `\\elsewhere\\AutoClaude\\…` ⇒ 任何對路徑（或多行文案）的
#   `assertIn` 在 Windows 必然落空、Mac/Linux 全綠。實測（R69）：
#       str(mock.call(r"…\elsewhere\AutoClaude\…"))
#         → call('… \\elsewhere\\AutoClaude\\…')      ← 斷言 False
#       " ".join(str(a) for a in c.args)
#         → … \elsewhere\AutoClaude\…                 ← 斷言 True
#   A1 只修了 `test_dev_start.py` 的一處，姊妹站點（同檔 2656、
#   `AutoClaude/tests/test_perception.py` 三處）仍是舊寫法且零守門 ⇒ 本判準補上。
#   修法慣例：`str(a) for c in <mock>.call_args_list for a in c.args`（取實際引數）。
#
# 判準（AST）：迭代 `*.call_args_list` / `*.mock_calls` / `*.await_args_list` 的
#   comprehension 或 for 迴圈，其迴圈變數（`mock.call` 物件）被 `str()`／`repr()`／
#   f-string 內插**整個物件**。取 `.args` / `.kwargs` / `.args[0]` 的形態不在射程
#   （那正是修法本身）。
#
# 🔴 刻意劃界（誠實記錄）：
#   ❌ 不追「先把 call_args_list 指派給區域變數、再於另一處迭代」的跨陳述式形態
#      —— 那需要值流分析（同上一道判準的劃界理由）。實掃四棵樹＋生產碼樹此形態 0 筆，
#      納入的成本大於收益；哪天出現，靠 windows-compat-ci 兜底。
#   ❌ 不追 `assertIn(x, str(mock_obj.mock_calls))` 這種「整個 list 直接 repr」形態
#      —— 實掃 0 筆；同理留給 CI 兜底。射程若擴大，請同步改本區段測試。
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
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        for root, recursive, floor in _scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = sorted(root.rglob("*.py") if recursive else root.glob("*.py"))
            scanned = 0
            for py in files:
                rel = py.relative_to(_REPO_ROOT).as_posix()
                try:
                    off, st = scan_call_obj_repr(py.read_text(encoding="utf-8"), rel)
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
            "發現以 mock.call 物件的 repr 拼裝斷言用輸出（R69 病灶家族，4 處實例）——"
            f"確屬刻意者於該行行尾加 `# {_CALLREPR_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_CALLREPR_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )

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
# WHY（本判準是為了補上第三道判準結構性抓不到的洞——那個洞正好放走了一個 P1）：
#   `tools/tests/test_dev_start.py` 的 `_scoped_sources()` 曾寫
#       out[str(path.relative_to(_TOOLS_DIR.parent))] = src        # ← 產出側
#       ...
#       self.assertIn("tools/dev_start.py", scoped)                 # ← 斷言側
#       self.assertNotIn("tools/lib/ci_liveness.py", scoped)        # ← 斷言側
#   `str(PurePath)` 在 Windows 渲染成 `tools\dev_start.py`。於是 Windows 上：
#     · `assertIn` 必然落空 ⇒ **windows-compat-ci 再度轉紅**（Mac/Linux 全綠）；
#     · `assertNotIn` 更糟——它**恆真通過**，而它正是「ci_liveness 不得進入
#       下限版 prelude 射程」那道鎖本身 ⇒ Windows 側整條變成**假鎖**。
#   實測重現（ntpath 語意注入真實測試類）：
#       AssertionError: 'tools/dev_start.py' not found in
#       {'tools\\bootstrap_core.py': ...}
#   第三道判準抓不到它，原因是**結構性**的：它的正則要求字面值以 `/` 開頭，
#   而這裡的字面值是**相對路徑**（`tools/dev_start.py`）。
#
# 為什麼不是把第三道判準的正則放寬到相對路徑就好：
#   相對路徑形狀的字面值在四棵測試樹＋生產碼樹極為普遍（`docs/04_planning`、
#   URL path、套件名 `a/b`…），過寬近似在此形態下會爆量誤報。故本判準改採
#   **窄化條件**：必須有「語法上可判定的 Path 產物」在場。分兩個入口：
#
#   (4a) 產出側：`str(<Path 產物>)` 被當成**識別鍵**——dict 下標／dict/set 字面值
#        或推導式的鍵／`.add(...)`。這正是上面病灶的**源頭**那一行。修法＝
#        `.as_posix()`（或 `PurePosixPath`），兩平台同鍵。
#   (4b) 斷言側：同一個斷言（**含 pytest 裸 `assert`**）裡同時出現「路徑形狀字面值
#        （絕對或相對）」與「語法可見的 Path 產物」。修法＝`as_posix()` 或
#        `str(Path(<同一字面值>))`。
#
# 🔴 刻意劃界（誠實記錄，勿超譯）：
#   ❌ **4b 仍不做值流分析**。上面病灶的斷言側（`assertIn("tools/dev_start.py",
#      scoped)`）中 `scoped` 的 Path 血統藏在 helper method 裡，4b **抓不到它**；
#      該站點是由 4a 從產出側抓住的。兩個入口互補，但都不宣稱涵蓋「Path 血統
#      隔了任意層呼叫」的形態——那需要跨程序值流，本檔一貫不做。
#   ❌ **`PurePosixPath`／`PosixPath`／`PureWindowsPath` 產物不算違規**（顯式平台
#      語意，對齊本檔第一道判準的 `_EXPLICIT_PLATFORM` 慣例）。實掃唯一因此排除的
#      站點：`test_windowsapps_guard_bash_parity.py` 的
#      `str(PurePosixPath(rel).parent)`——恆為正斜線，本來就中立。
#   ❌ **`list.append(str(<Path>))` 不算識別鍵**（識別鍵＝下標／dict-set 鍵／`.add`）。
#      實掃全庫此形態 3 筆，皆只流向失敗訊息文字或與 `[]` 比對（`dev_start.py:812`
#      清理報告、`test_sanitize_component_frozen_sdd_versions_lock.py` 兩處、
#      `hub_sync.py:517` 鏡像檔清單），**下游無正斜線字面值斷言** ⇒ 今日無分歧，
#      故不納入以免把「顯示用字串」也一併判違規。若哪天有人拿它去比對字面值，
#      4b 會從斷言側接住（前提是 Path 血統在同句可見）。
#   ❌ **路徑建構子的引數不算「比對值」**（`Path("/nonexistent/a.png")`）。pathlib
#      會正規化輸入，那是路徑**輸入**不是平台相依**輸出**；不排除的話
#      `test_multimodal_validator.py` 的兩筆立刻變誤報（實測）。
#
# 📏 「擴到 pytest 裸 assert」的實測取捨（終審 P2 #7 指名項；此處誠實劃界）：
#   十一棵掃描根共 **9705** 個裸 `assert`。若把第三道判準（過寬近似）直接套上去，
#   命中 **41** 筆，逐筆親讀後**全部是噪音**（`/compact` slash 指令、`/T` `/F` `/PID`
#   tasklist 旗標、`/api/config/schema` URL、`/tmp/x.yaml` 從未 Path 化的假字串）
#   ⇒ 一上線就得開 41 筆白名單，鎖即淪為白名單，故**維持不擴**。
#   改以本判準的窄化條件（同句 Path 產物在場）套用裸 assert：實測命中 **0** 筆
#   ⇒ 零存量債、零誤報的擴面。**結論**：裸 assert 自此在射程內，但只在「Path 產物
#   語法可見」時；「純字面值 vs 不可見血統」的裸 assert 仍在射程外，靠
#   windows-compat-ci 兜底。宣稱到此為止，不多一分。
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
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        for root, recursive, floor in _scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = sorted(root.rglob("*.py") if recursive else root.glob("*.py"))
            scanned = 0
            for py in files:
                rel = py.relative_to(_REPO_ROOT).as_posix()
                try:
                    off, st = scan_path_str_identity(py.read_text(encoding="utf-8"), rel)
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
            "發現 Path 的平台相依字串化被當識別鍵／比對值（R69 P1 病灶家族）——"
            f"確屬刻意者於該行行尾加 `# {_PATHKEY_OK_MARKER} <WHY>` 豁免：\n"
            + "\n".join(offenders),
        )
        self.assertEqual(
            stale, [],
            f"{_PATHKEY_OK_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )

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


if __name__ == "__main__":
    unittest.main()
