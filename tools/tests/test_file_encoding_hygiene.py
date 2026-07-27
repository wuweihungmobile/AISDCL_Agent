#!/usr/bin/env python3
"""檔案讀寫端漏 `encoding=` 站點機械守門（DEF-101-506 同型家族：「綠得沒有鑑別力」）。

WHY（與 stdio 端互補的另一半）：本 repo 的 Claude Code session 透過
`.claude/settings.json` 的 `env.PYTHONUTF8=1` 把 UTF-8 mode 注入**所有**子行程，
故 session 內每一次驗證都是 UTF-8 mode；但真實使用者雙擊開 Windows PowerShell 5.1
直接跑腳本時沒有這個變數，`locale.getpreferredencoding(False)` 即回系統 ACP
（本機實測 cp950）。於是任何依賴 locale 預設編碼的退化「在 session 內永遠不會翻紅」
——與 DEF-101-506 認定的缺陷完全同型。`TestLocaleDefaultEncodingHazardIsReal`
以移除 PYTHONUTF8 的真子行程證明該危害為真（非推論），本檔的存在前提由它守住：
前提若哪天不成立（Python 改預設），該案會自己翻紅要求改寫本檔。

分工：stdio／子行程輸出端由 test_subprocess_encoding_hygiene.py 守（marker
`encoding-ok:`）；本檔守**檔案讀寫端**（marker `fileio-encoding-waiver:`）。兩個
marker 刻意互不為子字串——J 包的 stale 自檢會把「掃不到對應違規的 marker」判紅，
若兩者互含即會跨檔互相誤判為 stale。此互斥由
`TestMarkerNamespaceDoesNotCollideWithSubprocessScanner` 機械鎖住。

掃描判準（AST，非行級 regex；以下 heuristic 邊界均為刻意取捨）：
  - **家族與 mode 參數位置**逐一分派（第一版探針正是在這裡誤判：`os.open` 與
    `Path.open` 都尾名 `open`，但前者是 fd 級、後者 mode 在 args[0] 而非 args[1]，
    照內建 open 的簽名硬套會把 `p.open("rb")` 誤判成文字模式）：
      · 內建 `open(file, mode, ...)`／`io.open`／`gzip|bz2|lzma.open` → mode 在 args[1]
      · `X.open(mode, ...)`（Path-like）→ mode 在 args[0]
      · `os.open` → fd 級，無 encoding 概念，**不掃**
      · `codecs.open` → 未給 encoding 時本就退回二進位，非解碼風險，**不掃**
      · `tarfile|zipfile.open` → 其 open() 根本沒有 encoding 參數，**不掃**
      · `read_text` / `write_text` → 恆文字模式，無 mode 可言
      · `os.fdopen(fd, mode, ...)` → mode 在 args[1]
      · `tempfile.*TemporaryFile(mode, ...)` → mode 在 args[0]，**預設 'w+b'＝
        二進位**，故僅在顯式給了文字 mode 時才算違規
  - mode 字面值含 `b` → 二進位，放行（強加 encoding 是錯的）；
  - mode 為**動態值**（變數／f-string）→ **列為違規**：無法靜態判定二進位，而
    「不確定」不等於「安全」（Rule 12 fail loud）。落地當下全樹零此種站點，故此嚴格
    判準不製造既有債；確有需要者以豁免標記處理。
  - 含 `**kwargs` 雙星展開的呼叫不追（encoding 可能藏於 dict，動態邊界）；
  - `encoding=None` 顯式傳入視同已表態而放行（實際仍走 locale 預設，但該寫法本身
    即明示意圖，不宜機械斷罪——邊界與 subprocess 掃描器 SD-R13-5b 同政策）；
  - 別名匯入（`from pathlib import Path as P` 不影響尾名比對；但
    `opener = open` 後的裸 `opener(...)` 不追）——同 subprocess 掃描器的別名邊界。
  - 已知誤報可能（實測全樹零站點，故不預先排除，留豁免標記處理）：任何自訂物件
    的同名方法（`.open()` / `.read_text()` / `.write_text()`），如 `ZipFile` 之外
    的第三方 archive 包裝。

豁免機制：違規呼叫「起始行」（node.lineno）行尾加註 `# fileio-encoding-waiver: <WHY>`
（WHY 必填，空白即無豁免力且另判 stale）。標記以 tokenize COMMENT token 辨識——
字串字面值內的同形文字（如本檔 fixture）不會誤判為標記。stale 自檢：登記了標記但
該行掃不到被壓下的違規（已補 encoding／已刪除／標記放錯行）→ fail-loud，防清單腐化。

⚠️ 已知陷阱（落地時真的踩到）：**散文註解**若寫出標記的完整字面（含冒號），該行
會被 tokenize 成一個「標記」，而該行沒有違規可壓 → 判 stale。要在註解裡談論這個
標記時，請省略冒號（或寫在 docstring 裡——docstring 是 STRING token 不是 COMMENT，
不會被認成標記）。此為子字串比對機制的固有代價，subprocess 掃描器同構。

掃描範圍：直接沿用 test_subprocess_encoding_hygiene 的 `_scan_roots()` /
`_scan_single_files()` 為 SSOT——兩者的納管判準字面相同（「這段 Python 是否可能在
cp950 機器上被執行」），各抄一份必然漂移。該清單本身的釘選、per-tree 檔數下限、
LATEST 版動態解析與 fail-loud 政策皆由該檔負責，本檔只加一道「清單沒被抽空」的下限。
"""
from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import tempfile
import tokenize
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_subprocess_encoding_hygiene as _subproc_scanner  # noqa: E402

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

_WAIVER_MARKER = "fileio-encoding-waiver:"

_TEXT_ALWAYS = frozenset({"read_text", "write_text"})
_TMPFILE_FACTORIES = frozenset(
    {"NamedTemporaryFile", "TemporaryFile", "SpooledTemporaryFile"}
)
# 簽名同內建 open（file, mode, ...）：mode 在 args[1]
_BUILTIN_LIKE_RECEIVERS = frozenset({"io", "gzip", "bz2", "lzma"})
# 與「locale 預設編碼解碼」無關，整族不掃（理由見模組 docstring）
_OUT_OF_SCOPE_RECEIVERS = frozenset({"os", "codecs", "tarfile", "zipfile"})


def _tail_and_receiver(func: ast.expr) -> tuple[str | None, str | None]:
    if isinstance(func, ast.Attribute):
        recv = func.value.id if isinstance(func.value, ast.Name) else None
        return func.attr, recv
    if isinstance(func, ast.Name):
        return func.id, None
    return None, None


def _classify(node: ast.Call) -> tuple[str, int | None, bool] | None:
    """回傳 (家族標籤, mode 參數位置 or None, 預設是否為二進位)；None＝不在掃描面。"""
    func = node.func
    tail, recv = _tail_and_receiver(func)
    if tail in _TEXT_ALWAYS:
        return (tail, None, False)
    if tail in _TMPFILE_FACTORIES:
        return (tail, 0, True)
    if tail == "fdopen":
        return ("os.fdopen", 1, False)
    if tail != "open":
        return None
    if isinstance(func, ast.Name):
        return ("open", 1, False)
    if recv in _OUT_OF_SCOPE_RECEIVERS:
        return None
    if recv in _BUILTIN_LIKE_RECEIVERS:
        return (f"{recv}.open", 1, False)
    return ("Path.open", 0, False)


def _violation(node: ast.Call) -> str | None:
    """回傳違規說明；None＝合格（已帶 encoding／二進位／動態邊界）。"""
    if any(k.arg is None for k in node.keywords):  # **kwargs 展開，動態不追
        return None
    kwargs = {k.arg: k.value for k in node.keywords if k.arg is not None}
    if "encoding" in kwargs:
        return None
    classified = _classify(node)
    if classified is None:
        return None
    family, mode_pos, default_is_binary = classified
    mode = kwargs.get("mode")
    if mode is None and mode_pos is not None and len(node.args) > mode_pos:
        mode = node.args[mode_pos]
    if mode is None:
        if default_is_binary:
            return None
        return f"{family}() 未指定 encoding（走 locale 預設編碼）"
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        if "b" in mode.value:
            return None
        return f"{family}(mode={mode.value!r}) 未指定 encoding（走 locale 預設編碼）"
    return f"{family}() 的 mode 為動態值，無法靜態判定文字/二進位——請改用字面 mode"


def _marker_lines(source: str) -> dict[int, str]:
    """{行號: WHY}——僅認 COMMENT token 內的標記（字串字面值同形文字不誤判）。"""
    markers: dict[int, str] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and _WAIVER_MARKER in tok.string:
            markers[tok.start[0]] = tok.string.split(_WAIVER_MARKER, 1)[1].strip()
    return markers


def scan_source(source: str, rel: str) -> tuple[list[str], list[str]]:
    """純函式核心：回傳 (offenders, stale_markers)，元素皆為 `rel:行號: 說明`。"""
    tree = ast.parse(source)  # SyntaxError 由呼叫端 fail-loud
    markers = _marker_lines(source)
    used: set[int] = set()
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        why = _violation(node)
        if why is None:
            continue
        if markers.get(node.lineno):
            used.add(node.lineno)
            continue
        offenders.append(f"{rel}:{node.lineno}: {why}")
    stale = [
        f"{rel}:{lineno}: {_WAIVER_MARKER} 標記 stale"
        f"（{'WHY 留空' if not why else '該行無被壓下的違規'}）"
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


_FIX_HINT = (
    "發現檔案讀寫未指定 encoding 的站點——真實使用者（無 PYTHONUTF8 的 "
    "PowerShell 5.1）會走 locale 預設編碼（本機 cp950），讀 UTF-8 內容即 "
    'UnicodeDecodeError。請補 encoding="utf-8"；確屬刻意者於呼叫起始行行尾加 '
    f"`# {_WAIVER_MARKER} <WHY>` 豁免：\n"
)


class TestFileEncodingHygiene(unittest.TestCase):
    def test_repo_trees_have_no_unencoded_file_io(self) -> None:
        offenders: list[str] = []
        stale: list[str] = []
        parse_failures: list[str] = []
        for root, floor in _subproc_scanner._scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = sorted(root.rglob("*.py"))
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
            "以下 .py 無法 parse——掃描面不得靜默縮小：\n" + "\n".join(parse_failures),
        )
        self.assertEqual(offenders, [], _FIX_HINT + "\n".join(offenders))
        self.assertEqual(
            stale, [],
            f"{_WAIVER_MARKER} 豁免標記 stale（防清單腐化）：\n" + "\n".join(stale),
        )

    def test_single_file_sites_have_no_unencoded_file_io(self) -> None:
        """樹清單外零散活躍 .py 的單檔納管（同判準同豁免機制）。"""
        files = _subproc_scanner._scan_single_files()
        for f in files:
            self.assertTrue(f.is_file(), f"單檔掃描目標缺席：{f}（邊界不得靜默縮小）")
        off, st, pf = scan_files(sorted(files), _REPO_ROOT)
        self.assertEqual(pf, [], "單檔掃描 parse 失敗：\n" + "\n".join(pf))
        self.assertEqual(off, [], _FIX_HINT + "\n".join(off))
        self.assertEqual(st, [], "單檔掃描豁免標記 stale：\n" + "\n".join(st))

    def test_scan_scope_is_not_hollowed_out(self) -> None:
        """借用的掃描清單被抽空／砍半即紅（本檔唯一的範圍下限；清單內容本體由
        test_subprocess_encoding_hygiene 的 pinning 案負責）。下限刻意寫成「兩個
        子專案各至少一棵樹」而非固定條數，避免與該檔的釘選清單重複維護。"""
        rels = [
            root.relative_to(_REPO_ROOT).as_posix()
            for root, _floor in _subproc_scanner._scan_roots()
        ]
        rels += [
            f.relative_to(_REPO_ROOT).as_posix()
            for f in _subproc_scanner._scan_single_files()
        ]
        self.assertTrue(
            any(r.startswith("AutoClaude/") for r in rels), f"AutoClaude 側整體出界：{rels}"
        )
        self.assertTrue(
            any(r.startswith("AISDLC_SDD/") for r in rels), f"AISDLC_SDD 側整體出界：{rels}"
        )
        self.assertTrue(
            any(r == "tools" or r.startswith("tools/") for r in rels),
            f"monorepo 根 tools/ 出界：{rels}",
        )

    # ── 以下以注入 fixture 自證判準紅綠（fixture 僅存在於 tmp，不留違規樣本於 repo）──

    def _scan_fixture(self, source: str) -> tuple[list[str], list[str], list[str]]:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "fixture_case.py").write_text(source, encoding="utf-8")
            return scan_files(sorted(root.rglob("*.py")), root)

    def test_injected_violations_are_detected(self) -> None:
        """漏 encoding 的各家族樣本必被判 offender。"""
        off, stale, pf = self._scan_fixture(
            "import pathlib, tempfile, os\n"
            "p = pathlib.Path('x')\n"
            "p.read_text()\n"
            "p.write_text('a')\n"
            "p.open()\n"
            "p.open('w')\n"
            "open('f')\n"
            "open('f', 'w')\n"
            "os.fdopen(3, 'w')\n"
            "tempfile.NamedTemporaryFile(mode='w')\n"
        )
        self.assertEqual(pf, [])
        self.assertEqual(stale, [])
        got = [o.split(": ", 1)[1] for o in off]
        self.assertEqual(
            [o.split(":")[1] for o in off],
            ["3", "4", "5", "6", "7", "8", "9", "10"],
            f"應逐行命中八個家族，實得：{off}",
        )
        self.assertIn("read_text()", got[0])
        self.assertIn("write_text()", got[1])
        self.assertIn("Path.open()", got[2])
        self.assertIn("Path.open(mode='w')", got[3])
        self.assertIn("open()", got[4])
        self.assertIn("open(mode='w')", got[5])
        self.assertIn("os.fdopen(mode='w')", got[6])
        self.assertIn("NamedTemporaryFile(mode='w')", got[7])

    def test_binary_and_out_of_scope_sites_are_green(self) -> None:
        """二進位模式與非解碼家族**不得**誤報——強加 encoding 反而是錯的。

        `os.open` 與 `p.open("rb")` 正是第一版探針的兩個誤判源，故單獨鎖住。
        """
        off, stale, pf = self._scan_fixture(
            "import pathlib, os, codecs, tarfile, zipfile, tempfile\n"
            "p = pathlib.Path('x')\n"
            "p.open('rb')\n"
            "p.open('wb')\n"
            "open('f', 'rb')\n"
            "p.read_bytes()\n"
            "p.write_bytes(b'a')\n"
            "os.open('f', os.O_CREAT | os.O_WRONLY)\n"
            "codecs.open('f', 'r')\n"
            "tarfile.open('f.tgz')\n"
            "zipfile.ZipFile('z').open('member.txt')\n"
            "tempfile.NamedTemporaryFile()\n"
            "tempfile.NamedTemporaryFile(mode='w+b')\n"
        )
        self.assertEqual((off, stale, pf), ([], [], []))

    def test_compliant_and_dynamic_kwargs_sites_are_green(self) -> None:
        """已補 encoding／`**kwargs` 展開／顯式 encoding=None ＝不判違規。"""
        off, stale, pf = self._scan_fixture(
            "import pathlib\n"
            "p = pathlib.Path('x')\n"
            "p.read_text(encoding='utf-8')\n"
            "p.write_text('a', encoding='utf-8')\n"
            "open('f', 'w', encoding='utf-8')\n"
            "p.open('r', encoding='utf-8')\n"
            "kw = {'encoding': 'utf-8'}\n"
            "p.read_text(**kw)\n"
            "p.read_text(encoding=None)\n"
        )
        self.assertEqual((off, stale, pf), ([], [], []))

    def test_dynamic_mode_is_flagged(self) -> None:
        """mode 為動態值＝列為違規（不確定 ≠ 安全）。"""
        off, _stale, pf = self._scan_fixture(
            "import pathlib\np = pathlib.Path('x')\nm = 'rb'\np.open(m)\n"
        )
        self.assertEqual(pf, [])
        self.assertEqual(len(off), 1, off)
        self.assertIn("mode 為動態值", off[0])

    def test_waiver_marker_suppresses_violation(self) -> None:
        """行尾豁免標記（附 WHY）＝綠，且不判 stale。"""
        off, stale, pf = self._scan_fixture(
            "import pathlib\n"
            "p = pathlib.Path('x')\n"
            f"p.read_text()  # {_WAIVER_MARKER} 寫端為系統碼頁，刻意對稱\n"
        )
        self.assertEqual((off, stale, pf), ([], [], []))

    def test_stale_or_empty_why_marker_fails(self) -> None:
        """標記 stale（該行無被壓下的違規）或 WHY 留空 → fail-loud 防腐化。"""
        off, stale, pf = self._scan_fixture(
            "import pathlib\n"
            "p = pathlib.Path('x')\n"
            f"p.read_text(encoding='utf-8')  # {_WAIVER_MARKER} 已補 encoding 卻忘拆標記\n"
            f"p.write_text('a')  # {_WAIVER_MARKER}\n"
        )
        self.assertEqual(pf, [])
        # WHY 留空的標記不具豁免力：該違規仍列報
        self.assertEqual(len(off), 1, off)
        self.assertIn("fixture_case.py:4", off[0])
        self.assertEqual(len(stale), 2, stale)
        self.assertIn("該行無被壓下的違規", stale[0])
        self.assertIn("WHY 留空", stale[1])

    def test_marker_in_string_literal_is_not_honoured(self) -> None:
        """字串字面值內的同形文字不得被當成豁免標記（只認 COMMENT token）。"""
        off, _stale, pf = self._scan_fixture(
            "import pathlib\n"
            "p = pathlib.Path('x')\n"
            f'doc = "{_WAIVER_MARKER} 這是字串不是註解"\n'
            "p.read_text()\n"
        )
        self.assertEqual(pf, [])
        self.assertEqual(len(off), 1, off)
        self.assertIn("fixture_case.py:4", off[0])

    def test_parse_failure_is_fail_loud(self) -> None:
        """無法 parse 的檔案列入 parse_failures（不得靜默縮面）。"""
        off, stale, pf = self._scan_fixture("def broken(:\n")
        self.assertEqual((off, stale), ([], []))
        self.assertEqual(len(pf), 1, pf)
        self.assertIn("SyntaxError", pf[0])


class TestMarkerNamespaceDoesNotCollideWithSubprocessScanner(unittest.TestCase):
    """兩支掃描器的豁免 marker 必須互不為子字串，否則彼此的 stale 自檢會互相誤判。

    WHY 這是真實踩到的坑：J 包的 `_OK_MARKER = "encoding-ok:"` 是以 `in` 做子字串
    比對，故若本檔採用 `file-encoding-ok:` 之類命名，J 包會在本檔標記的行上找不到
    subprocess 違規而判 stale → 兩支守門互相把對方的合法豁免燒成紅燈。
    """

    def test_markers_are_mutually_non_substring(self) -> None:
        other = _subproc_scanner._OK_MARKER
        self.assertNotIn(
            other, _WAIVER_MARKER,
            f"本檔 marker {_WAIVER_MARKER!r} 含 subprocess 掃描器 marker {other!r}"
            "——會被對方 stale 自檢誤判",
        )
        self.assertNotIn(
            _WAIVER_MARKER, other,
            f"subprocess 掃描器 marker {other!r} 含本檔 marker {_WAIVER_MARKER!r}",
        )


class TestLocaleDefaultEncodingHazardIsReal(unittest.TestCase):
    """本檔存在前提的實測：移除 PYTHONUTF8 後，不指定 encoding 讀 UTF-8 檔真的會壞。

    不是推論而是真跑一個子行程：把 PYTHONUTF8 從環境剔除（＝真實使用者雙擊開
    PowerShell 5.1 的情境），在其中以 `read_text()`（不指定 encoding）讀含中文的
    UTF-8 檔。前提若哪天不成立（例如 Python 改變預設），本案會翻紅，逼使重新評估
    本檔的必要性與嚴重度，而不是留一份靠假前提撐著的守門。
    """

    _CHILD = (
        "import json, locale, pathlib, sys\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "text = '\\u4e2d\\u6587\\u6e2c\\u8a66\\n'\n"   # 中文測試
        "p.write_bytes(text.encode('utf-8'))\n"
        "out = {'utf8_mode': sys.flags.utf8_mode,\n"
        "       'preferred': locale.getpreferredencoding(False)}\n"
        "try:\n"
        "    out['implicit'] = 'SAME' if p.read_text() == text else 'MOJIBAKE'\n"
        "except UnicodeDecodeError as e:\n"
        "    out['implicit'] = 'UnicodeDecodeError'\n"
        "out['explicit'] = 'SAME' if p.read_text(encoding='utf-8') == text else 'DIFF'\n"
        # stdout 全 ASCII：子行程主控台若為 cp950，印中文本身就會炸，會混淆判讀
        "print(json.dumps(out, ensure_ascii=True))\n"
    )

    @staticmethod
    def _is_utf8_locale(name: str) -> bool:
        return name.lower().replace("-", "").replace("_", "") in {"utf8", "cp65001"}

    def test_missing_encoding_really_breaks_without_pythonutf8(self) -> None:
        env = os.environ.copy()
        env.pop("PYTHONUTF8", None)  # 這一行就是「真實使用者環境」與 session 的唯一差異
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "probe.py"
            script.write_text(self._CHILD, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(script), str(Path(td) / "data.txt")],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=env,
            )
        self.assertEqual(
            proc.returncode, 0,
            f"探針子行程失敗：rc={proc.returncode} stderr={proc.stderr.strip()!r}",
        )
        got = json.loads(proc.stdout.strip())
        self.assertEqual(
            got["utf8_mode"], 0,
            "剔除 PYTHONUTF8 後子行程仍在 UTF-8 mode，本案失去鑑別力（是否有其他"
            f"來源打開了 UTF-8 mode？實得 {got!r}）",
        )
        # 顯式 UTF-8 在任何 locale 下都正確——這是「補 encoding 就會好」的正面證據
        self.assertEqual(got["explicit"], "SAME", f"顯式 encoding='utf-8' 竟讀錯：{got!r}")
        if self._is_utf8_locale(got["preferred"]):
            self.skipTest(
                "本機 locale 預設已是 UTF-8"
                f"（preferred={got['preferred']!r}），無法在此重現危害；"
                "Windows 非 UTF-8 ACP（如 cp950）機器上本案才具鑑別力"
            )
        self.assertNotEqual(
            got["implicit"], "SAME",
            "前提可能已不成立：locale 預設非 UTF-8"
            f"（preferred={got['preferred']!r}）卻仍正確讀出 UTF-8 內容 → {got!r}。"
            "若 Python 已改變預設行為，本檔的必要性與嚴重度須重新評估",
        )


if __name__ == "__main__":
    unittest.main()
