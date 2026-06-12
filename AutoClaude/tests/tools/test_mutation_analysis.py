"""tests/tools/test_mutation_analysis.py — SD_09 W2 audit P0-AUDIT-06 修復。

紀律 #4「驗證鏡子自身要被驗證」— mutation_analysis.py 是「mutmut log → survived backlog」
的真實性鏡子，必須有單元測試證明「假 PASS / 解析錯誤場景能被偵測」。

涵蓋：
  - extract_survived_ids dash range 展開（P0-D）
  - extract_survived_ids cross-file section（mutmut 2.4 每檔分段）
  - marker section summary 與「最後一筆」優先順序（P1-AUDIT-14 對齊 baseline_lock）
  - parsed survived count vs summary 不一致時印 WARN（紀律 #5 跨工具對齊）
  - classify_diff 各分類邊界
  - render_backlog 結構正確
  - SD_09 W2 P0-AUDIT-04：marker 優先取勝
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.mutation_analysis import (
    _expand_id_tokens,
    _extract_survived_from_marker,
    classify_diff,
    extract_survived_ids,
    render_backlog,
)


# ----- _expand_id_tokens -----


def test_expand_dash_range() -> None:
    """`12-16` → ["12","13","14","15","16"]（P0-D 修復）。"""
    out = _expand_id_tokens(["12-16"])
    assert out == ["12", "13", "14", "15", "16"]


def test_expand_plain_digits() -> None:
    """獨立數字原樣保留。"""
    out = _expand_id_tokens(["3", "5", "7"])
    assert out == ["3", "5", "7"]


def test_expand_mixed_tokens() -> None:
    out = _expand_id_tokens(["1", "5-7", "10"])
    assert out == ["1", "5", "6", "7", "10"]


def test_expand_invalid_range_dropped() -> None:
    """`5-3`（lo > hi）→ drop（不展開）。"""
    out = _expand_id_tokens(["5-3", "8"])
    assert out == ["8"]


def test_expand_garbage_tokens_dropped() -> None:
    """非數字 / 非 range token 全 drop。"""
    out = _expand_id_tokens(["abc", "1.5", "x-y", "5"])
    assert out == ["5"]


def test_expand_whitespace_handling() -> None:
    """token 內外空白容忍。"""
    out = _expand_id_tokens(["  3 - 5  ", " 8 "])
    assert out == ["3", "4", "5", "8"]


# ----- _extract_survived_from_marker -----


def test_marker_section_extracts_survived(tmp_path: Path) -> None:
    text = (
        "noise raw\n"
        "Survived 🙁 (999)\n"
        "--- mutmut full counts (from cache; SD_09 P0-G) ---\n"
        "Killed (80)\n"
        "Survived (38)\n"
        "Timeout (0)\n"
        "--- mutmut full counts (end) ---\n"
    )
    assert _extract_survived_from_marker(text) == 38


def test_marker_missing_returns_none() -> None:
    """無 marker → None（讓 caller fallback 至最後一筆）。"""
    text = "Survived (5)\nSurvived (10)\n"
    assert _extract_survived_from_marker(text) is None


def test_marker_end_missing_returns_none() -> None:
    """只有 begin 無 end → 不算合法 marker。"""
    text = "--- mutmut full counts ---\nSurvived (5)\n"
    assert _extract_survived_from_marker(text) is None


# ----- extract_survived_ids -----


def test_extract_survived_ids_with_marker_assertion_consistent(tmp_path: Path) -> None:
    """marker 內 Survived (3) + raw 列 3 個 id → 一致，無 WARN。"""
    log = tmp_path / "mutmut.log"
    log.write_text(
        "Survived 🙁 (3)\n"
        "10, 11, 12\n"
        "\n"
        "--- mutmut full counts (from cache; SD_09 P0-G) ---\n"
        "Killed (100)\n"
        "Survived (3)\n"
        "Timeout (0)\n"
        "Suspicious (0)\n"
        "Skipped (0)\n"
        "--- mutmut full counts (end) ---\n",
        encoding="utf-8",
    )
    ids = extract_survived_ids(log)
    assert ids == ["10", "11", "12"]


def test_extract_survived_ids_dash_range(tmp_path: Path) -> None:
    """dash range token 展開（P0-D 整合）。"""
    log = tmp_path / "mutmut.log"
    log.write_text(
        "Survived 🙁 (5)\n"
        "12-16\n"
        "\n"
        "--- mutmut full counts ---\n"
        "Survived (5)\n"
        "--- mutmut full counts (end) ---\n",
        encoding="utf-8",
    )
    ids = extract_survived_ids(log)
    assert ids == ["12", "13", "14", "15", "16"]


def test_extract_survived_ids_count_mismatch_warns(tmp_path: Path, capsys) -> None:
    """parsed != summary → stderr 印 WARN（紀律 #5）。"""
    log = tmp_path / "mutmut.log"
    log.write_text(
        "Survived 🙁 (10)\n"
        "1, 2, 3\n"  # 只有 3 個 id 但 summary 說 10
        "\n"
        "--- mutmut full counts ---\n"
        "Survived (10)\n"
        "--- mutmut full counts (end) ---\n",
        encoding="utf-8",
    )
    ids = extract_survived_ids(log)
    assert len(ids) == 3
    captured = capsys.readouterr()
    assert "WARN" in captured.err
    assert "parsed survived count" in captured.err


def test_extract_survived_ids_empty_log_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_survived_ids(tmp_path / "nonexistent.log")


def test_extract_survived_ids_zero_survived(tmp_path: Path) -> None:
    """0 survived → 回空 list，無 WARN。"""
    log = tmp_path / "mutmut.log"
    log.write_text(
        "--- mutmut full counts ---\n"
        "Killed (100)\n"
        "Survived (0)\n"
        "--- mutmut full counts (end) ---\n",
        encoding="utf-8",
    )
    ids = extract_survived_ids(log)
    assert ids == []


def test_extract_survived_ids_strips_file_section_headers(tmp_path: Path) -> None:
    """`---- file.py (24) ----` 子標題行內的數字不應被當作 mutant id。"""
    log = tmp_path / "mutmut.log"
    log.write_text(
        "Survived 🙁 (3)\n"
        "---- autoclaude/plugins/token_guard/policy.py (3) ----\n"
        "1, 2, 3\n"
        "\n"
        "--- mutmut full counts ---\n"
        "Survived (3)\n"
        "--- mutmut full counts (end) ---\n",
        encoding="utf-8",
    )
    ids = extract_survived_ids(log)
    # 子標題 `(3)` 應被剔除，只取 1, 2, 3
    assert ids == ["1", "2", "3"]


# ----- classify_diff -----


def test_classify_boundary_operators() -> None:
    diff = "-    if x >= threshold:\n+    if x > threshold:\n"
    assert classify_diff(diff) == "boundary"


def test_classify_constant_true_false() -> None:
    diff = "-    return True\n+    return False\n"
    assert classify_diff(diff) == "constant"


def test_classify_string_literal() -> None:
    diff = "-    log.info('start processing')\n+    log.info('XXstart processingXX')\n"
    assert classify_diff(diff) == "string_literal"


def test_classify_empty_diff_returns_other() -> None:
    assert classify_diff("") == "other"


def test_classify_no_change_lines_returns_other() -> None:
    diff = "   unchanged line\n"
    assert classify_diff(diff) == "other"


# ----- render_backlog -----


def test_render_backlog_includes_all_categories() -> None:
    classified = {
        "boundary": [{"id": "1", "preview": "diff"}],
        "constant": [],
        "dead_branch": [],
        "string_literal": [{"id": "2", "preview": "diff"}],
        "other": [],
    }
    md = render_backlog("token_guard", classified)
    assert "token_guard" in md
    assert "boundary" in md
    assert "string_literal（ignore）" in md
    assert "#1" in md
    assert "#2" in md


def test_render_backlog_zero_survived() -> None:
    classified = {"boundary": [], "constant": [], "dead_branch": [], "string_literal": [], "other": []}
    md = render_backlog("token_guard", classified)
    assert "0 个" in md or "共 0 " in md or "共 0" in md
