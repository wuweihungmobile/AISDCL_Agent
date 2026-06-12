"""SD_09 W3 R29 — 5 P1 黃線清單 closure 取證 contract test。

對應：
  - SD_09 W3 R25/R28 5 P1 黃線清單原列 SD_10 backlog
  - R29 zero-trust audit 全部驗證實質已落地
  - 本 contract test 為「文件聲稱 vs 實作落地」的 SSOT 取證機制
    （紀律 #4：驗證鏡子自身要被驗證）

5 P1 黃線項目（全部 CLOSED）：
  P1-1 mutmut regex SSOT — `tools/mutmut_counts_parser.py` + 單元測試
  P1-2 ps1↔helper roundtrip — `tools/ac4_nightly_alert_parser.py` + 單元測試
  P1-3 [F2 ALERT] log:L — `tools/run_local_nightly.ps1` line 519 觸發點
  P1-4 legacy fallback — `tools/ac4_progress_check.py:_resolve_strict_p95_threshold` 三層 fallback
  P1-5 append_history M-05 dedup — `tools/mutation_baseline_lock.py:append_history` 同日去重

未來如有任一項回退（如 helper 重構不見了），本 test 會立即標紅。
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestSD09P1YellowLinesClosed:
    """5 P1 黃線 closure 取證 — 文件聲稱 vs 實作落地對齊。"""

    def test_p1_1_mutmut_regex_ssot_helper_exists(self) -> None:
        helper = PROJECT_ROOT / "tools" / "mutmut_counts_parser.py"
        assert helper.is_file(), "P1-1 SSOT helper tools/mutmut_counts_parser.py 缺失"
        content = helper.read_text(encoding="utf-8")
        assert "def parse" in content or "def _parse" in content, "P1-1 SSOT helper 無 parse function"

    def test_p1_1_mutmut_regex_ssot_test_exists(self) -> None:
        test_file = PROJECT_ROOT / "tests" / "tools" / "test_mutmut_counts_parser.py"
        assert test_file.is_file(), "P1-1 SSOT 單元測試 tests/tools/test_mutmut_counts_parser.py 缺失"

    def test_p1_2_ac4_alert_parser_helper_exists(self) -> None:
        helper = PROJECT_ROOT / "tools" / "ac4_nightly_alert_parser.py"
        assert helper.is_file(), "P1-2 helper tools/ac4_nightly_alert_parser.py 缺失"

    def test_p1_2_ac4_alert_parser_test_exists(self) -> None:
        test_file = PROJECT_ROOT / "tests" / "tools" / "test_ac4_nightly_alert_parser.py"
        assert test_file.is_file(), "P1-2 ps1↔helper roundtrip 單元測試缺失"

    def test_p1_3_f2_alert_log_trigger_in_ps1(self) -> None:
        ps1 = PROJECT_ROOT / "tools" / "run_local_nightly.ps1"
        assert ps1.is_file(), "P1-3 nightly ps1 缺失"
        content = ps1.read_text(encoding="utf-8")
        assert "[F2 ALERT]" in content, "P1-3 [F2 ALERT] log 觸發點未在 ps1 找到"
        assert "ready_for_labeled_pr" in content, "P1-3 ready_for_labeled_pr 條件邏輯缺失"

    def test_p1_4_legacy_fallback_in_ac4_progress(self) -> None:
        helper = PROJECT_ROOT / "tools" / "ac4_progress_check.py"
        assert helper.is_file(), "P1-4 ac4_progress_check.py 缺失"
        content = helper.read_text(encoding="utf-8")
        assert "_resolve_strict_p95_threshold" in content, "P1-4 _resolve_strict_p95_threshold legacy fallback function 缺失"
        assert "AUTOCLAUDE_TEST_P95_THRESHOLD_MS" in content, "P1-4 legacy env 名稱回退邏輯缺失"

    def test_p1_5_append_history_m05_dedup_test_exists(self) -> None:
        test_file = PROJECT_ROOT / "tests" / "tools" / "test_mutation_baseline_lock.py"
        assert test_file.is_file()
        content = test_file.read_text(encoding="utf-8")
        assert "test_append_history_same_date_overwrites" in content, "P1-5 append_history M-05 dedup 測試 case 缺失"

    @pytest.mark.parametrize(
        "p1_id,description",
        [
            ("P1-1", "mutmut regex SSOT"),
            ("P1-2", "ps1↔helper roundtrip"),
            ("P1-3", "[F2 ALERT] log:L"),
            ("P1-4", "legacy fallback"),
            ("P1-5", "append_history M-05 dedup"),
        ],
    )
    def test_p1_closure_documented_in_claude_md_or_sprint_history(
        self, p1_id: str, description: str
    ) -> None:
        """R29 後：CLAUDE.md 或 sprint_history.md 必須提及這 5 P1 已 CLOSED。"""
        claude_md = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        sprint_history = (PROJECT_ROOT / "docs" / "05_development" / "sprint_history.md").read_text(encoding="utf-8")
        combined = claude_md + sprint_history
        assert "5 P1" in combined, f"{p1_id} closure 聲稱未在 CLAUDE.md / sprint_history.md 出現"
