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


# ══════════════════════════════════════════════════════════════════════════════
# R74 — 第五道判準：平台專屬環境變數的讀取必須帶平台守衛（PKG-4 C）
# ══════════════════════════════════════════════════════════════════════════════
# WHY（本檔第五道判準；與前四道同屬「跨平台寫法」家族，故沿用本檔的掃描根／豁免／
# stale 慣例，不另開新檔——R73 的 `_FROZEN_GUARD_FILE_COUNT` 明文要求新增鎖併入既有檔）：
#   `DEF-101-766` 的病灶是 `WindowsAppsGuard.ps1::Resolve-NativeExecutable` **無條件**
#   照 `$env:PATHEXT` 過濾候選——PATHEXT 是 Windows-only 概念，PS Core 跑在
#   macOS/Linux 上該變數不存在、POSIX 執行檔又不帶副檔名 ⇒ 每個候選都被淘汰 ⇒
#   函式恆回 `$null` ⇒ macos-compat-ci 與 root-infra-ci(ubuntu) 必紅。
#
#   🔴 R74 要治的不是那個缺陷（R71 已修），而是**它的鎖只圈一個站點**：修復當時建的鎖
#   （`tools/tests/test_dev_start.py::TestResolveNativeExecutable*`）綁死在那一支
#   `.ps1` 的那一個函式上——換一支檔案、換一種語言（Python 的
#   `os.environ["PATHEXT"]`）寫同一個缺陷，全 repo 零掃描。這是 `DEF-101-757`／
#   `DEF-101-777` 判過的同一件事（已知的鎖射程缺口不得只以劃界結案），而本 repo 已經
#   為它付過三次代價。故本判準改成**形態掃描**：不問「哪一支檔案」，只問
#   「這一處讀 PATHEXT 的程式碼，有沒有先確認自己在 Windows 上」。
#
# 判準（逐行文字，射程含 `.py`／`.ps1`／`.psm1`／`.sh`）：
#   讀取形態＝`$env:PATHEXT`（PowerShell）／`PATHEXT` 出現在 `os.environ`、`getenv`
#   同一行（Python）／`$PATHEXT`（shell）。
#   「有守衛」＝同一個檔案內、該行**之前**出現過平台守衛述詞（見 `_PLATFORM_GUARDS`）。
#
# 🔴 刻意劃界（誠實記錄，勿超譯）：
#   ❌ **只看「之前出現過」，不做控制流分析**。靜態判不出守衛是否真的支配該行（R71 的
#      `DEF-101-766` 正是「守衛存在但排在過濾之後」）。那一半由既有的**順序鎖**
#      （`test_dev_start.py::TestResolveNativeExecutableShortCircuitOrder`）承接——
#      兩道鎖的射程刻意不同：本鎖問「有沒有」（廣、全庫），順序鎖問「排對了沒」
#      （窄、逐站點）。把兩者混成一道會兩頭都做不好。
#   ❌ **註解與 docstring 內提到 PATHEXT 不算讀取**（本 repo 有大量在地 WHY 逐字提到
#      它）。做法＝掃描前先剝行尾 `#` 之後的部分（heuristic，沿用本檔第一道判準
#      `_scan_file` 的既有取捨：不解析字串內的 `#`，代價是「字串內含 `#` 且其後才出現
#      讀取語法」會漏掃）。判準另要求出現**真正的讀取語法**，不只是出現這個字。
#   ❌ **注入／設定（`mock.patch.dict(os.environ, {"PATHEXT": …})`）不算讀取**。
#      實測本 repo 有這種站點（`tools/tests/test_bash_probe_spec_contract.py`），
#      它是在替被測碼**佈置**環境，本身不依賴本機平台。故 Python 側的形態刻意寫得窄
#      （下標／`.get`／`in`／`getenv` 四種真讀取），不用「同一行出現 os.environ」這種
#      寬判準——寬判準製造的假紅會逼下一輪的人把整條鎖關掉。
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
        better = {**baseline, tree: max(0, baseline[tree] - 1)}
        self.assertTrue(_wst.posix_tag_ratchet_problems(worse), "新增未標籤站點沒被擋下")
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

    def test_scan_surface_spans_the_three_live_test_trees(self) -> None:
        """🔴 PKG-4 D 的射程面：判準必須看到三棵活測試樹，不是只有一棵。

        意圖：R72 的射程只有 `tools/tests/`（實測 53 支檔），而 repo 活測試檔共 337 支
        ⇒ 84% 不在任何方向判準的射程內。射程若被縮回一棵樹，本支當場紅。
        """
        trees = _wst.scan_tree_sources(_REPO_ROOT, _TESTS_DIR, "test_*.py")
        self.assertEqual(
            sorted(trees),
            ["AISDLC_SDD/scripts/tests", "AutoClaude/tests", "tools/tests"],
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
# WHY（沿用本檔的掃描根／標記／stale 慣例，不另開新檔——`_FROZEN_GUARD_FILE_COUNT`
# 明文要求新增鎖併入既有檔）：
#   `Path.read_text()`／`write_text()`／`open()` 不帶 `encoding=` 時，用的是**本機
#   locale 預設編碼**。mac 上那是 UTF-8，所以在 mac 寫、在 mac 跑，永遠是綠的；
#   同一行程式碼在 zh-TW Windows 上是 cp950，讀到任何非 Big5 字元就 `UnicodeDecodeError`。
#   這是「mac→Windows 落差」最典型的一整類缺陷，而 R76 掃描實測它**零靜態掃描器**。
#
# 🔴 更麻煩的是它連**執行期**都看不見：根 `.claude/settings.json` 設了 `PYTHONUTF8=1`，
#   於是 agent 驅動的開發迴圈裡每一支 python 都跑在 UTF-8 模式下、這類缺陷在本機一次
#   都不會現形（而另有一道鎖在強制那個值存在）。把區分本機與雲端的變數全域正規化掉，
#   結果就是**唯一能看見它的環境被關掉了** ⇒ 只剩靜態判準這一條路。
#
# 判準（AST，非逐行文字）：
#   · `<expr>.read_text(...)`／`<expr>.write_text(...)` — 恆為文字 I/O，必須有 encoding。
#   · `open(...)`（builtin 形態）與 `<expr>.open(...)`（pathlib 形態）— mode 帶 `b`
#     即二進位，出射程；其餘要求 encoding。
#   · encoding 可以是關鍵字，也可以是**位置引數**（四種呼叫形態的位置各不相同，見
#     `_ENC_POS`）——只認關鍵字會對合法寫法製造假紅。
#   · 行尾 `<標記> <WHY>` 豁免（標記字串見 `_ENCODING_OK_MARKER`）＋ stale 自檢：
#     標記在而違規不在（或 WHY 留空）即紅，防清單腐化。
#
# 🔴 刻意劃界（誠實記錄，勿超譯）：
#   ❌ **mode 是非字面值運算式時出射程**（`open(p, mode_var)`）——靜態判不出它是不是
#      二進位，硬判會製造假紅。實測本 repo 現況零此形態；這是**已知可繞道**，不是沒想到。
#   ❌ **`**kwargs` 轉發視為已帶 encoding**（同樣判不出來，且該形態通常是包裝函式）。
#   ❌ **非 pathlib 的 `.open(`**（`os.open` 連 encoding 參數都沒有、`gzip`/`tarfile`/
#      `zipfile` 預設二進位）由 `_NON_TEXT_OPEN_OWNERS` 排除。R76 落地前實測：不排除
#      的話光 `os.open` 就製造 5 筆假紅，而寬判準製造的假紅會逼下一輪把整條鎖關掉
#      （同第五道判準對 `mock.patch.dict` 的取捨）。
#   ❌ **`errors=` 不在本判準射程內**（那是另一個軸，不混進來）。
#
# 🔴 標記字串為何取專屬主題名（值見下方常數；本註解刻意不逐字寫出它——寫出來就會被
#   自己的取標記函式當成一個真標記而判 stale，同 `_encoding_markers` docstring 的理由）：
#   R76 落地首版與 `tools/tests/test_subprocess_encoding_hygiene.py`
#   的判準一 `_OK_MARKER` **逐字相同**，而兩支掃描器的掃描面是包含關係（本判準 810 檔
#   全在對方 854 檔之內）⇒ 任一方的**合法**豁免會在另一方變成一筆 `標記 stale` 紅，
#   而那筆紅的訊息還寫著「該行無被壓下的違規」（對他那一行是誤導）。兩支的錯誤訊息都
#   主動教人加這個標記，所以第一個照做的人就會踩到。這正是本輪 PKG-0 在拆的「兩道鎖的
#   合法動作互為對方違規」死結，不可在同一輪又造一個。命名比照同檔既有的
#   `_PATHEXT_OK_MARKER`／`_TMPDIR_OK_MARKER`：**每道判準取專屬主題名**。
#   另：比對改用邊界正則（同姊妹檔 `_marker_lines`），裸子字串比對是縱深防禦缺的那一層
#   ——未來若再出現含本標記為子字串的第三個標記，改名這一層就擋不住了。
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
    """射程＝本檔第一道判準的 `_scan_roots()`（四棵測試樹 ＋ 生產碼樹）。

    刻意**共用**同一組掃描根而不另列一份：兩份清單就是兩個會漂移的真相，而
    `_scan_roots()` 已有逐樹檔數下限在守「靜默縮面」。
    """
    out: list[Path] = []
    for root, recursive, _floor in _scan_roots():
        if not root.is_dir():
            continue
        for p in (root.rglob("*.py") if recursive else root.glob("*.py")):
            if "__pycache__" in p.parts:
                continue
            out.append(p)
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
        # 反空轉下限＝R76 實掃數打八折取整；射程若被縮小必紅。
        self.assertGreaterEqual(
            scanned, 648, f"encoding 掃描面只有 {scanned} 檔——射程疑似被縮小")
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
# 缺陷本體（實測重現，非理論）：新落地的 file-IO 判準，其標記字串與
# `test_subprocess_encoding_hygiene.py` 判準一的 `_OK_MARKER` **逐字相同**（值不在此
# 逐字引述，理由見 :2048 那段），而兩者掃描面是包含關係 ⇒ 一個**合法**的 subprocess
# 豁免會在 file-IO 這邊多出一筆 `標記 stale`，反向亦然。兩支的錯誤訊息都主動教人加該
# 標記，所以第一個照訊息辦事的人就會撞上一筆指著自己剛加的合法豁免的紅——正是本輪
# PKG-0 在拆的那種死結。
#
# 這道鎖守的是**根因而非個案**：全庫每一個「行尾 `<slug>-ok:` 豁免標記」常數都必須
# 是各判準專屬的，且彼此不得互相認領。姊妹檔已有一支同型鎖
# （`test_the_two_criteria_markers_do_not_claim_each_other`），但它只驗自己那兩個，
# 對**跨檔**碰撞零射程——那個縫就是這次逃出去的地方。
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
        self.assertEqual(
            _encoding_markers(f"x = 1  # {_ENCODING_OK_MARKER} 自家 WHY\n"),
            {1: "自家 WHY"}, "本判準認不出自己的標記 ⇒ 上一條變成恆真的假綠")


if __name__ == "__main__":
    unittest.main()
