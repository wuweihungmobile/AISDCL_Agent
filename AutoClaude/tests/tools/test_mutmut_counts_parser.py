"""tests/tools/test_mutmut_counts_parser.py — ADR-SD09-010 §5 W1 必做。

紀律 #4「驗證鏡子自身要被驗證」— mutmut_counts_parser.py 為 ps1 line 337-358
(4 條件分支：inSection start / end / counts line match / no marker WARN) 的 SSOT 同構鏡子。
本 test 必須覆蓋 4 條分支 + 防 P0-AUDIT-R3-3 迴歸（regex 過寬 / backlog 路徑誤判）。
"""
from __future__ import annotations

from pathlib import Path

from tools.mutmut_counts_parser import main, parse_mutmut_counts


# ----- 分支 1: section_found=True + emitted=5 → 正常 OK -----


def test_parse_full_marker_section_with_five_counts() -> None:
    """正常情境：完整 marker section + 5 type counts → 全命中 + 無 warning。"""
    text = (
        "--- mutmut full counts (from cache; SD_09 P0-G) ---\n"
        "Killed (111)\n"
        "Survived (38)\n"
        "Timeout (0)\n"
        "Suspicious (0)\n"
        "Skipped (0)\n"
        "--- mutmut full counts (end) ---\n"
    )
    result = parse_mutmut_counts(text)
    assert result.section_found is True
    assert result.emitted == 5
    assert result.counts == {"killed": 111, "survived": 38, "timeout": 0, "suspicious": 0, "skipped": 0}
    assert result.warning is None
    assert result.formatted_lines == (
        "[mutation counts] Killed (111)",
        "[mutation counts] Survived (38)",
        "[mutation counts] Timeout (0)",
        "[mutation counts] Suspicious (0)",
        "[mutation counts] Skipped (0)",
    )


# ----- 分支 2: section_found=False → 無 marker → WARN -----


def test_parse_no_marker_section_warning() -> None:
    """ps1 line 360：emitted=0 → WARN（P0-AUDIT-R3-3 防迴歸：無 marker 必須 WARN）。"""
    text = (
        "Killed 🎉 (999)\n"
        "Survived 🙁 (999)\n"
        "Skipped (0)\n"
    )
    result = parse_mutmut_counts(text)
    assert result.section_found is False
    assert result.emitted == 0
    assert result.counts == {}
    assert result.warning is not None
    assert "no marker section found" in result.warning


# ----- 分支 3: section_found=True + emitted=0 (空 section) → WARN -----


def test_parse_empty_marker_section_warning() -> None:
    """marker 存在但 section 內無 counts line（mutmut 異常輸出）→ WARN。"""
    text = (
        "--- mutmut full counts (from cache) ---\n"
        "\n"
        "--- mutmut full counts (end) ---\n"
    )
    result = parse_mutmut_counts(text)
    assert result.section_found is True
    assert result.emitted == 0
    assert result.warning is not None


# ----- 分支 4: P0-AUDIT-R3-3 迴歸防禦 — backlog 路徑不誤判 -----


def test_parse_ignores_backlog_paths_outside_marker() -> None:
    """P0-AUDIT-R3-3 迴歸防禦：marker 外的 `compactor.py (13)` 等 backlog 路徑不應誤判為 counts。

    舊版 ps1 用過寬 regex `\\([0-9]+\\)` 會抓 backlog 路徑 → 主 log 回流 11 行雜訊。
    Marker section 邊界限制是修法核心。
    """
    text = (
        "Survived 🙁 (38)\n"
        "---- compactor.py (13) ----\n"
        "---- policy.py (17) ----\n"
        "--- mutmut full counts (from cache) ---\n"
        "Killed (111)\n"
        "Survived (38)\n"
        "Timeout (0)\n"
        "Suspicious (2)\n"
        "Skipped (0)\n"
        "--- mutmut full counts (end) ---\n"
    )
    result = parse_mutmut_counts(text)
    assert result.section_found is True
    assert result.emitted == 5
    assert result.counts["survived"] == 38  # 取 marker section 內，非 raw `Survived (38)`
    assert result.counts["suspicious"] == 2
    # backlog 路徑 `compactor.py (13)` 不應被當成 counts
    assert "compactor" not in str(result.counts)
    assert "policy" not in str(result.counts)


# ----- 防呆：begin marker regex 不誤匹配 end marker -----


def test_begin_marker_excludes_end_marker() -> None:
    """ADR-SD09-010 §5 W1：begin marker 須排除 `(end)` 字樣，否則同 regex 雙匹配。

    對齊 mutation_baseline_lock._COUNTS_BEGIN_MARKER 的 negative lookahead `(?!\\s*\\(end\\))`。
    """
    text = (
        "--- mutmut full counts (end) ---\n"  # 只有 end，沒有 begin
        "Killed (999)\n"  # 不該被解析
        "Survived (999)\n"
    )
    result = parse_mutmut_counts(text)
    assert result.section_found is False
    assert result.emitted == 0


# ----- end-to-end: CLI 模式 -----


def test_cli_main_prints_formatted_lines_to_stdout(tmp_path: Path, capsys) -> None:
    """CLI 模式：read log → 印 ps1 等價 `[mutation counts] X` 行至 stdout；rc=0。"""
    log = tmp_path / "mutmut.log"
    log.write_text(
        "--- mutmut full counts (from cache) ---\n"
        "Killed (50)\n"
        "Survived (10)\n"
        "Timeout (1)\n"
        "Suspicious (3)\n"
        "Skipped (0)\n"
        "--- mutmut full counts (end) ---\n",
        encoding="utf-8",
    )
    rc = main([str(log)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[mutation counts] Killed (50)" in captured.out
    assert "[mutation counts] Suspicious (3)" in captured.out
    # 5 行全列
    assert captured.out.count("[mutation counts]") == 5


def test_cli_main_missing_log_returns_1(tmp_path: Path, capsys) -> None:
    """CLI 模式：log 不存在 → rc=1 + stderr ERROR。"""
    rc = main([str(tmp_path / "nonexistent.log")])
    assert rc == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.err
    assert "log not found" in captured.err
