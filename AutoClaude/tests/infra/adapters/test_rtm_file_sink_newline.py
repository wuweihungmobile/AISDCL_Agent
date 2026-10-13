"""R68 回歸鎖：文字模式寫檔必須顯式指定 newline，杜絕 Windows 隱式 CRLF。

缺陷：`FileRtmSink.append_report_line` 的 docstring 明寫「強制 LF 收尾」，但
`open("a", encoding="utf-8")` 未指定 newline → text 模式預設 newline=None，
Windows 上每個 "\\n" 被翻成 "\\r\\n"，該承諾在 Windows 是假的。同一缺陷類別
（DEF-101-524/534）已在 AISDLC_SDD v0.30 rule_loader 修過，但沒有任何機械掃描
把它橫向套到 AutoClaude 生產碼（實查：autoclaude/ 202 檔零 `newline=`）。

鎖的形態刻意選「原始碼結構」而非「執行期位元組」：POSIX 上 newline=None 不做
任何轉換，位元組斷言在 mac/Linux CI 恆綠、零鑑別力（Scan-H 判準①）。

舊債表（14 檔／18 站點）已清零，判準＝全樹零容忍、站點級回報：只要求「宣告」newline
（要平台原生行尾就明寫 newline=os.linesep，不需任何豁免口）。mode 非字面量的站點無從
判定，只計數印出、不判紅；射程＝builtin／io／Path 的 open 與 write_text（現況
autoclaude/ 無 tempfile／os.fdopen 形態）。
"""
from __future__ import annotations

import ast
from pathlib import Path

from autoclaude.infra.adapters.rtm_file_sink import FileRtmSink

_AUTOCLAUDE_ROOT = Path(__file__).resolve().parents[3] / "autoclaude"


def _mode_node(node: ast.Call, func: ast.expr) -> ast.expr | None:
    for kw in node.keywords:
        if kw.arg == "mode":
            return kw.value
    # builtin open()／io.open() 的 mode 是第 2 個位置引數；Path.open() 是第 1 個。
    by_path = isinstance(func, ast.Attribute) and not (
        isinstance(func.value, ast.Name) and func.value.id == "io"
    )
    idx = 0 if by_path else 1
    return node.args[idx] if len(node.args) > idx else None


def _scan_source(src: str, rel: str) -> tuple[list[str], int]:
    """回 (缺 newline= 的文字模式寫入站點「相對路徑:行號」, mode 非字面量而跳過的站點數)。"""
    hits: list[str] = []
    nonliteral = 0
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name == "open":
            mode = _mode_node(node, func)
            if mode is None:  # 缺省 mode＝讀取
                continue
            if not (isinstance(mode, ast.Constant) and isinstance(mode.value, str)):
                nonliteral += 1
                continue
            if "b" in mode.value or not any(c in mode.value for c in "wax+"):
                continue
        elif name != "write_text":
            continue
        if not any(kw.arg == "newline" for kw in node.keywords):
            hits.append(f"{rel}:{node.lineno}")
    return hits, nonliteral


def _text_write_sites_without_newline() -> tuple[list[str], int]:
    hits: list[str] = []
    nonliteral = 0
    for py in sorted(_AUTOCLAUDE_ROOT.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        rel = py.relative_to(_AUTOCLAUDE_ROOT).as_posix()
        h, n = _scan_source(py.read_text(encoding="utf-8"), rel)
        hits += h
        nonliteral += n
    return hits, nonliteral


def test_no_new_text_write_sites_without_explicit_newline():
    hits, nonliteral = _text_write_sites_without_newline()
    print(f"[newline-lock] mode 非字面量而跳過的站點數＝{nonliteral}（只計數、不判紅）")
    assert not hits, (
        f"{len(hits)} 個文字模式寫檔站點未指定 newline=（Windows 上會靜默寫出 CRLF）："
        f"{hits}；open 補 newline=\"\"、write_text 補 newline=\"\\n\""
    )


def test_scanner_has_teeth_on_synthetic_sources():
    """鎖的自證：掃描器若瞎了（恆回空），上面那條就是恆綠的假鎖。"""
    bad = (
        "p.open('w', encoding='utf-8')\n"
        "p.open(mode='a')\n"
        "open(p, 'r+')\n"
        "p.write_text('x')\n"
    )
    ok = (
        "p.open('w', encoding='utf-8', newline='')\n"
        "p.write_text('x', newline='\\n')\n"
        "p.open('wb')\n"
        "open(p, 'rb')\n"
        "open(p)\n"
        "p.open(encoding='utf-8')\n"
        "p.read_text()\n"
    )
    assert _scan_source(bad, "bad.py") == (["bad.py:1", "bad.py:2", "bad.py:3", "bad.py:4"], 0)
    assert _scan_source(ok, "ok.py") == ([], 0)
    assert _scan_source("m = 'w'\nopen(p, m)\np.open(m)\n", "nl.py") == ([], 2)
    assert _scan_source("io.open(p, 'w')\n", "io.py") == (["io.py:1"], 0)


def test_append_report_line_writes_lf_bytes(tmp_path):
    """行為面補充鎖：POSIX 上恆綠（無轉換），Windows 上才有鑑別力——
    刻意保留，作為未來 Windows 真機輪次的現成取證點。"""
    sink = FileRtmSink(str(tmp_path))
    path = Path(sink.append_report_line("rtm_history", '{"a": 1}'))
    sink.append_report_line("rtm_history", '{"a": 2}')
    assert path.read_bytes() == b'{"a": 1}\n{"a": 2}\n'


def test_write_report_writes_lf_bytes(tmp_path):
    sink = FileRtmSink(str(tmp_path))
    path = Path(sink.write_report("cov", "line1\nline2\n", fmt="md"))
    assert path.read_bytes() == b"line1\nline2\n"
