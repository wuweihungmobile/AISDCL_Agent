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
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
import tomllib
import unicodedata
import unittest
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


def _scan_roots() -> list[tuple[Path, int]]:
    """（掃描根, 該樹檔數下限）清單；根缺席或低於下限由測試 fail-loud。

    per-tree 下限（對齊 test_platform_neutral_paths SD-3 慣例）：逐樹釘選使任一樹
    縮面必紅、不被他樹總量掩蓋。下限＝2026-07-19 首跑實掃數（23/46/200/272/31/162）
    打八折取整，隨基線上修。R13 一審 ARCH-R13-REV-5 補納四個小樹（.claude/hooks／
    AutoClaude/scripts／AutoClaude/alembic／LATEST .claude/hooks——其中
    AutoClaude/scripts 正是 DEF-101-178 實證的 R12 清查漏網目錄），納管當下
    實掃 1/1/19/5、同法打八折（最低 1）。樹清單本體由
    TestScanRootsConfigPinning 釘選，防「刪清單一列」整樹靜默出界（QA-R13-2 同構）。"""
    latest = _latest_root()
    return [
        (_REPO_ROOT / "tools", 18),
        (_REPO_ROOT / "AutoClaude" / "tools", 36),
        (_REPO_ROOT / "AutoClaude" / "autoclaude", 160),
        (_REPO_ROOT / "AutoClaude" / "tests", 217),
        (_REPO_ROOT / "AutoClaude" / "scripts", 1),
        (_REPO_ROOT / "AutoClaude" / "alembic", 15),
        (_REPO_ROOT / ".claude" / "hooks", 1),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts", 24),
        (latest / "tools" / "fsm_runtime", 129),
        # R14 SCAN-PY-1：LATEST tools/ 下 fsm_runtime 之外唯一 Python 樹——現況零
        # subprocess 站點（arch_fitness.py 明文「不執行 shell」），納管防未來引入
        # 漏網（升版由 _latest_root() 動態跟隨）。實掃 2 檔（__init__ + 本體），下限 1。
        (latest / "tools" / "arch_fitness", 1),
        (latest / ".claude" / "hooks", 4),
    ]


# R14 SCAN-PY-2：樹清單外的零散活躍 .py 以顯式單檔清單納管（目錄機制掃不到、
# 又不能把整個 AISDLC_SDD/ 根樹納入——rglob 會誤掃凍結版 v0.01~v0.29）。
# 清單由 TestScanRootsConfigPinning 一併釘選。R14 一審（SD-R14-REV-3＋ARCH-R14-REV-4
# 獨立交叉發現）以 `git ls-files '*.py'` 全列舉打破「唯一漏網」宣稱，補齊為 3 檔；
# tmp_lint_check.py 為 tracked 暫存殘留（2026-06-12 入庫、命名即臨時檔），去留另裁決
# ——刪檔時 pinning 紅燈會提醒同步本清單。
def _scan_single_files() -> list[Path]:
    return [
        _REPO_ROOT / "AISDLC_SDD" / "conftest.py",
        _REPO_ROOT / "AutoClaude" / "tmp_lint_check.py",
        _latest_root() / "tools" / "__init__.py",
    ]


def _call_tail_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _marker_lines(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token 內的標記（字串字面值同形文字不誤判）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _OK_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_OK_MARKER, 1)[1].strip()
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


class TestSubprocessEncodingHygiene(unittest.TestCase):
    def test_repo_trees_have_no_unencoded_text_subprocess(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        for root, floor in _scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = sorted(root.rglob("*.py"))
            # per-tree 下限釘選：單樹縮面必紅
            self.assertGreaterEqual(
                len(files), floor,
                f"{root} 掃描檔數 {len(files)} < 下限 {floor}——該樹掃描面疑似縮小",
            )
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
                "AutoClaude/tmp_lint_check.py",
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

    def test_the_e501_waiver_carries_an_expiry_date(self) -> None:
        """帶到期日的豁免才不會腐化成永久豁免（同 `ci_liveness` 的 `WAIVER_UNTIL` 體例）。"""
        text = _RUFF_TOML.read_text(encoding="utf-8")
        self.assertRegex(
            text, r"到期日：\d{4}-\d{2}-\d{2}",
            "tools/ruff.toml 的 E501 存量債豁免已不帶到期日 —— 無到期日的豁免＝永久豁免",
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
                "[TOOL-MISSING] ruff 不在 PATH——本道要驗的是 ruff **自己**的設定解析結果，"
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
