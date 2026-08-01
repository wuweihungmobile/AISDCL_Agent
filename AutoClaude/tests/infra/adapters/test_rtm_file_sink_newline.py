"""R68 回歸鎖：文字模式寫檔必須顯式指定 newline，杜絕 Windows 隱式 CRLF。

缺陷：`FileRtmSink.append_report_line` 的 docstring 明寫「強制 LF 收尾」，但
`open("a", encoding="utf-8")` 未指定 newline → text 模式預設 newline=None，
Windows 上每個 "\\n" 被翻成 "\\r\\n"，該承諾在 Windows 是假的。同一缺陷類別
（DEF-101-524/534）已在 AISDLC_SDD v0.30 rule_loader 修過，但沒有任何機械掃描
把它橫向套到 AutoClaude 生產碼（實查：autoclaude/ 202 檔零 `newline=`）。

鎖的形態刻意選「原始碼結構」而非「執行期位元組」：POSIX 上 newline=None 不做
任何轉換，位元組斷言在 mac/Linux CI 恆綠、零鑑別力（Scan-H 判準①）。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from autoclaude.infra.adapters.rtm_file_sink import FileRtmSink

_AUTOCLAUDE_ROOT = Path(__file__).resolve().parents[3] / "autoclaude"

# 已修（必須維持零違規）的模組。
_MUST_BE_CLEAN = {"infra/adapters/rtm_file_sink.py"}

# 尚未償還的舊債（shrink-only：只准縮，不准新增）。本輪 Pkg-1 僅獨佔
# rtm_file_sink.py，其餘檔案屬別包/後續輪次；此處登記為既有債務基線，
# 別包修好後這裡自然變少（本鎖刻意不對「清單有殘留」下斷言，避免
# 並行輪次中他包修好自己的檔反而把本鎖打紅）。
_KNOWN_MISSING_NEWLINE = {
    "evolution/playbook_evolver.py",
    "infra/adapters/file_preference_store.py",
    "infra/adapters/local_kb_metric_store.py",
    "infra/adapters/translation_learning_sink.py",
    "infra/repositories/file_playbook_repository.py",
    "infra/repositories/file_state_repository.py",
    "plugins/playbook_persistence_plugin.py",
    "tools/sdd_compile.py",
    "utils/goal_progress.py",
    "utils/knowledge_base.py",
    "utils/logger.py",
    "utils/notifier.py",
    "utils/perf_baseline.py",
    "utils/token_tracker.py",
}


def _write_mode_sites_without_newline() -> set[str]:
    """AST 掃描：文字模式的寫入型 open()/Path.open()/write_text() 未帶 newline=。"""
    hits: set[str] = set()
    for py in _AUTOCLAUDE_ROOT.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name not in ("open", "write_text"):
                continue
            if any(kw.arg == "newline" for kw in node.keywords):
                continue
            if name == "open" and not _is_text_write_mode(node, func):
                continue
            hits.add(py.relative_to(_AUTOCLAUDE_ROOT).as_posix())
    return hits


def _is_text_write_mode(node: ast.Call, func: ast.expr) -> bool:
    # builtin open() 的 mode 是第 2 個位置引數；Path.open() 是第 1 個。
    idx = 1 if isinstance(func, ast.Name) else 0
    mode = "r"
    if len(node.args) > idx and isinstance(node.args[idx], ast.Constant):
        mode = node.args[idx].value
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = kw.value.value
    if not isinstance(mode, str) or "b" in mode:
        return False
    return any(c in mode for c in "wax+")


def test_no_new_text_write_sites_without_explicit_newline():
    found = _write_mode_sites_without_newline()
    allowed = _KNOWN_MISSING_NEWLINE
    assert found <= allowed, (
        "新增未指定 newline= 的文字模式寫檔站點："
        f"{sorted(found - allowed)}；Windows 上會靜默寫出 CRLF"
    )


@pytest.mark.parametrize("rel", sorted(_MUST_BE_CLEAN))
def test_fixed_modules_stay_clean(rel):
    assert rel not in _write_mode_sites_without_newline(), (
        f"{rel} 的 newline= 被移除（R68 缺陷復發：docstring 承諾 LF、實作在 Windows 給 CRLF）"
    )


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
