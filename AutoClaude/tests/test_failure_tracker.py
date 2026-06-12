"""FailureTracker 單元測試：is_stuck / suspect_test_file_error 邊界案例。"""
import pytest
from autoclaude.execution.failure_tracker import FailureTracker, AttemptRecord


# ─────────────────────────────
# 輔助函式
# ─────────────────────────────

def _make_tracker(step_id: str = "T01") -> FailureTracker:
    return FailureTracker(step_id)


def _record(tracker: FailureTracker, attempt: int, eval_output: str, exit_code: int = 1,
            minimax_reasoning: str = "") -> None:
    tracker.record(
        attempt=attempt,
        failure_reason="test failure",
        eval_output=eval_output,
        exit_code=exit_code,
        minimax_reasoning=minimax_reasoning,
    )


# ─────────────────────────────
# is_stuck 測試
# ─────────────────────────────

class TestIsStuck:
    def test_empty_history_not_stuck(self):
        tracker = _make_tracker()
        assert tracker.is_stuck() is False

    def test_single_record_not_stuck(self):
        tracker = _make_tracker()
        _record(tracker, 0, "SyntaxError: invalid syntax (test_foo.py line 5)")
        assert tracker.is_stuck() is False

    def test_two_identical_signatures_stuck(self):
        tracker = _make_tracker()
        output = "SyntaxError: invalid syntax (test_foo.py line 5)"
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.is_stuck() is True

    def test_two_different_signatures_not_stuck(self):
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: assert 1 == 2")
        _record(tracker, 1, "NameError: name 'foo' is not defined")
        assert tracker.is_stuck() is False

    def test_line_number_variation_treated_as_same_signature(self):
        """行號不同但錯誤類型相同，正規化後視為卡死。"""
        tracker = _make_tracker()
        _record(tracker, 0, "SyntaxError: invalid syntax at line 5")
        _record(tracker, 1, "SyntaxError: invalid syntax at line 8")
        assert tracker.is_stuck() is True

    def test_custom_consecutive_threshold(self):
        tracker = _make_tracker()
        output = "ImportError: cannot import name 'foo'"
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        _record(tracker, 2, output)
        assert tracker.is_stuck(consecutive_threshold=3) is True
        assert tracker.is_stuck(consecutive_threshold=4) is False

    def test_last_two_same_but_first_different(self):
        """前兩次不同，最後兩次相同 → 卡死（以最近 N 次為準）。"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: different error")
        _record(tracker, 1, "ImportError: same error here")
        _record(tracker, 2, "ImportError: same error here")
        assert tracker.is_stuck() is True


# ─────────────────────────────
# is_diverging 測試
# ─────────────────────────────

class TestIsDiverging:
    def test_empty_not_diverging(self):
        tracker = _make_tracker()
        assert tracker.is_diverging() is False

    def test_single_record_not_diverging(self):
        tracker = _make_tracker()
        _record(tracker, 0, "error", exit_code=1)
        assert tracker.is_diverging() is False

    def test_increasing_exit_codes_diverging(self):
        tracker = _make_tracker()
        _record(tracker, 0, "err", exit_code=1)
        _record(tracker, 1, "err", exit_code=2)
        _record(tracker, 2, "err", exit_code=3)
        assert tracker.is_diverging() is True

    def test_non_monotonic_exit_codes_not_diverging(self):
        tracker = _make_tracker()
        _record(tracker, 0, "err", exit_code=2)
        _record(tracker, 1, "err", exit_code=1)
        assert tracker.is_diverging() is False


# ─────────────────────────────
# suspect_test_file_error 測試
# ─────────────────────────────

class TestSuspectTestFileError:
    def test_empty_history_not_suspect(self):
        tracker = _make_tracker()
        assert tracker.suspect_test_file_error() is False

    def test_single_record_not_suspect(self):
        """只有 1 次，threshold 未達，不觸發。"""
        tracker = _make_tracker()
        _record(tracker, 0, "SyntaxError: invalid syntax\ntest_foo.py  SyntaxError")
        assert tracker.suspect_test_file_error() is False

    def test_two_records_pointing_to_test_file_suspect(self):
        """兩次都指向 test_ 檔案，且無實作檔錯誤。"""
        tracker = _make_tracker()
        output = "SyntaxError: invalid syntax\ntest_foo.py: SyntaxError in test code"
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is True

    def test_impl_file_error_present_not_suspect(self):
        """同時有實作檔錯誤 → 不確定，不觸發。"""
        tracker = _make_tracker()
        output = (
            "SyntaxError: invalid syntax\n"
            "test_foo.py: SyntaxError\n"
            "auth.py:42: some error"
        )
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is False

    def test_non_test_file_not_suspect(self):
        """錯誤指向非 test_ 檔案 → 不觸發。"""
        tracker = _make_tracker()
        output = "AssertionError: assert 1 == 2\nfoo.py:10: assertion failed"
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is False

    def test_import_error_in_test_file_suspect(self):
        tracker = _make_tracker()
        output = "ImportError: cannot import name 'bar'\ntest_bar.py ImportError"
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is True

    def test_mixed_records_first_ok_second_test_file(self):
        """第一次無 test 指向，第二次有 → False（需全部都指向 test）。"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: assert x == y")
        _record(tracker, 1, "SyntaxError: invalid syntax\ntest_foo.py SyntaxError")
        assert tracker.suspect_test_file_error() is False

    def test_test_file_with_linenum_colon_format_suspect(self):
        """test_foo.py:15: SyntaxError 格式（pytest 標準輸出）應觸發 suspect。"""
        tracker = _make_tracker()
        output = "SyntaxError: invalid syntax\ntest_foo.py:15: SyntaxError"
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is True

    def test_impl_file_with_linenum_not_suspect(self):
        """auth.py:42 應被偵測為實作檔錯誤，不觸發 suspect。"""
        tracker = _make_tracker()
        output = (
            "SyntaxError: invalid syntax\n"
            "test_foo.py:15: SyntaxError\n"
            "auth.py:42: another error"
        )
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is False

    def test_framework_path_not_treated_as_impl_error(self):
        """_pytest/config.py:183 與 pluggy/manager.py:120 屬框架路徑，應被過濾，不阻止 suspect 觸發。"""
        tracker = _make_tracker()
        output = (
            "SyntaxError: invalid syntax\n"
            "test_foo.py:15: SyntaxError\n"
            "_pytest/config.py:183: some internal error\n"
            "pluggy/manager.py:120: hook call\n"
        )
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is True

    def test_real_impl_error_alongside_framework_path_not_suspect(self):
        """真正的實作檔 auth.py:42 即使同時有框架路徑，仍應阻止 suspect。"""
        tracker = _make_tracker()
        output = (
            "SyntaxError: invalid syntax\n"
            "test_foo.py:15: SyntaxError\n"
            "_pytest/config.py:183: some internal error\n"
            "auth.py:42: another error\n"
        )
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is False

    def test_pytest_collection_error_cross_line_suspect(self):
        """Gap-006-C：pytest 集合錯誤跨行格式應觸發 suspect（test_foo.py 與 SyntaxError 在不同行）。"""
        tracker = _make_tracker()
        output = "ERROR collecting tests/test_foo.py\n  SyntaxError: invalid syntax"
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is True

    def test_pytest_collection_error_cross_line_with_impl_file_not_suspect(self):
        """Gap-006-C：跨行集合錯誤但同時有實作檔錯誤 → 不觸發 suspect。"""
        tracker = _make_tracker()
        output = (
            "ERROR collecting tests/test_foo.py\n"
            "  SyntaxError: invalid syntax\n"
            "auth.py:42: TypeError"
        )
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is False

    def test_pytest_importerror_cross_line_suspect(self):
        """Gap-006-C：pytest 跨行 ImportError 格式亦應觸發 suspect。"""
        tracker = _make_tracker()
        output = "ERROR collecting tests/test_bar.py\n  ImportError: cannot import name 'foo'"
        _record(tracker, 0, output)
        _record(tracker, 1, output)
        assert tracker.suspect_test_file_error() is True


# ─────────────────────────────
# build_history_summary 測試
# ─────────────────────────────

class TestBuildHistorySummary:
    def test_empty_returns_empty(self):
        tracker = _make_tracker()
        assert tracker.build_history_summary() == ""

    def test_includes_attempt_info(self):
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: assert 1 == 2", exit_code=1,
                minimax_reasoning="修正 foo.py 第 10 行")
        summary = tracker.build_history_summary()
        assert "Attempt 0" in summary
        assert "exit=1" in summary
        # Gap-008-B：新格式不再直接顯示 minimax_reasoning，改用去重 sig 格式
        assert "AssertionError" in summary

    def test_multiple_records_all_included(self):
        tracker = _make_tracker()
        for i in range(3):
            _record(tracker, i, f"error {i}", exit_code=i + 1)
        summary = tracker.build_history_summary()
        assert "Attempt 0" in summary
        assert "Attempt 1" in summary
        assert "Attempt 2" in summary

    def test_correction_prompt_sent_in_summary(self):
        """correction_prompt_sent 非空時，summary 應包含修正方向摘要（Gap-008-B 新格式）。"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError", exit_code=1)
        tracker.update_last_correction_prompt("請修正 foo.py 第 42 行的型別問題")
        summary = tracker.build_history_summary()
        assert "Minimax 最後修正方向" in summary
        assert "請修正 foo.py 第 42 行" in summary

    def test_correction_prompt_truncated_to_120(self):
        """correction_prompt_sent 超過 120 字時，只顯示前 120 字（Gap-008-B 壓縮至 120）。"""
        tracker = _make_tracker()
        _record(tracker, 0, "error", exit_code=1)
        long_prompt = "A" * 200
        tracker.update_last_correction_prompt(long_prompt)
        summary = tracker.build_history_summary()
        assert "A" * 120 in summary
        assert "A" * 121 not in summary

    def test_empty_correction_prompt_not_shown(self):
        """correction_prompt_sent 為空時，summary 不應有修正方向段落。"""
        tracker = _make_tracker()
        _record(tracker, 0, "error", exit_code=1)
        summary = tracker.build_history_summary()
        assert "Minimax 最後修正方向" not in summary


# ─────────────────────────────
# to_failure_chain 測試
# ─────────────────────────────

class TestToFailureChain:
    def test_empty_chain(self):
        tracker = _make_tracker()
        assert tracker.to_failure_chain() == []

    def test_chain_structure(self):
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError", exit_code=1, minimax_reasoning="fix it")
        chain = tracker.to_failure_chain()
        assert len(chain) == 1
        assert chain[0]["attempt"] == 0
        assert chain[0]["exit_code"] == 1
        assert chain[0]["minimax_reasoning"] == "fix it"
        assert "error_signature" in chain[0]
        assert "failure_reason" in chain[0]


# ─────────────────────────────
# _normalize_error 測試
# ─────────────────────────────

class TestNormalizeError:
    def test_strips_line_numbers(self):
        output = "SyntaxError at line 42 in foo.py"
        result = FailureTracker._normalize_error(output)
        assert "line 42" not in result
        assert "line N" in result

    def test_strips_memory_addresses(self):
        output = "object at 0x7f1234abcdef"
        result = FailureTracker._normalize_error(output)
        assert "0x7f1234abcdef" not in result
        assert "0xADDR" in result

    def test_truncates_at_200_chars(self):
        long_output = "error " * 100
        result = FailureTracker._normalize_error(long_output)
        assert len(result) <= 200


# ─────────────────────────────
# is_oscillating 測試（Gap-Osc TDD）
# ─────────────────────────────

class TestIsOscillating:
    def test_empty_not_oscillating(self):
        tracker = _make_tracker()
        assert tracker.is_oscillating() is False

    def test_less_than_window_not_oscillating(self):
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: assert 1 == 2")
        _record(tracker, 1, "TypeError: unsupported operand")
        _record(tracker, 2, "AssertionError: assert 1 == 2")
        assert tracker.is_oscillating() is False  # window=4，只有 3 筆

    def test_abab_pattern_oscillating(self):
        """ABAB 嚴格交替模式 → 振盪"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: assert 1 == 2")
        _record(tracker, 1, "TypeError: unsupported operand")
        _record(tracker, 2, "AssertionError: assert 1 == 2")
        _record(tracker, 3, "TypeError: unsupported operand")
        assert tracker.is_oscillating() is True

    def test_aabb_not_oscillating(self):
        """AABB 連續相同再切換，不算嚴格交替"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: assert 1 == 2")
        _record(tracker, 1, "AssertionError: assert 1 == 2")
        _record(tracker, 2, "TypeError: unsupported operand")
        _record(tracker, 3, "TypeError: unsupported operand")
        assert tracker.is_oscillating() is False

    def test_abba_not_oscillating(self):
        """ABBA 中間有連續相同，不算嚴格交替"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: assert 1 == 2")
        _record(tracker, 1, "TypeError: unsupported operand")
        _record(tracker, 2, "TypeError: unsupported operand")
        _record(tracker, 3, "AssertionError: assert 1 == 2")
        assert tracker.is_oscillating() is False

    def test_three_unique_sigs_not_oscillating(self):
        """3 種不同 sig → 不是二元振盪"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: value error")
        _record(tracker, 1, "TypeError: wrong type")
        _record(tracker, 2, "NameError: not defined")
        _record(tracker, 3, "AssertionError: value error")
        assert tracker.is_oscillating() is False

    def test_six_records_ababab_oscillating(self):
        """6 筆 ABABAB → 窗口內仍振盪"""
        tracker = _make_tracker()
        for i in range(3):
            _record(tracker, i * 2, "AssertionError: assert 1 == 2")
            _record(tracker, i * 2 + 1, "TypeError: unsupported operand")
        assert tracker.is_oscillating() is True

    def test_custom_window_requires_more_records(self):
        """window=6 需要至少 6 筆記錄"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: assert 1 == 2")
        _record(tracker, 1, "TypeError: unsupported operand")
        _record(tracker, 2, "AssertionError: assert 1 == 2")
        _record(tracker, 3, "TypeError: unsupported operand")
        assert tracker.is_oscillating(window=4) is True
        assert tracker.is_oscillating(window=6) is False  # 只有 4 筆，不足 6


# ─────────────────────────────
# is_cycling 測試（Gap-006-B TDD）
# ─────────────────────────────

class TestIsCycling:
    def test_empty_not_cycling(self):
        tracker = _make_tracker()
        assert tracker.is_cycling() is False

    def test_less_than_window_not_cycling(self):
        """不足 window=6 筆 → 不觸發"""
        tracker = _make_tracker()
        for i in range(5):
            _record(tracker, i, ["TypeError: bad type", "AttributeError: no attr", "NameError: undef"][i % 3])
        assert tracker.is_cycling() is False

    def test_abcabc_cycling(self):
        """ABCABC 6 筆三路振盪 → is_cycling() = True"""
        tracker = _make_tracker()
        errors = [
            "TypeError: unsupported operand type",
            "AttributeError: 'str' has no attr 'foo'",
            "NameError: name 'bar' is not defined",
        ]
        for i in range(6):
            _record(tracker, i, errors[i % 3])
        assert tracker.is_cycling() is True

    def test_all_same_not_cycling(self):
        """6 筆相同 → 只有 1 種 unique，不是 cycling（is_stuck 應處理）"""
        tracker = _make_tracker()
        for i in range(6):
            _record(tracker, i, "TypeError: same error every time")
        assert tracker.is_cycling() is False

    def test_abab_four_records_with_default_window_not_cycling(self):
        """4 筆 ABAB，window=6 → 不足記錄數，不觸發（由 is_oscillating 處理）"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError: assert 1 == 2")
        _record(tracker, 1, "TypeError: unsupported operand")
        _record(tracker, 2, "AssertionError: assert 1 == 2")
        _record(tracker, 3, "TypeError: unsupported operand")
        assert tracker.is_cycling(window=6) is False  # 只有 4 筆，不足 6

    def test_abcabc_custom_window(self):
        """使用自訂 window=4 驗證邊界"""
        tracker = _make_tracker()
        errors = ["TypeError: op error", "AttributeError: no attr x", "NameError: undef y", "TypeError: op error"]
        for i, e in enumerate(errors):
            _record(tracker, i, e)
        # 4 筆，window=4，unique=3（A,B,C,A → unique={A,B,C}），max_count=2，window//2=2 → True
        assert tracker.is_cycling(window=4) is True

    def test_cycling_needs_min_unique(self):
        """只有 1 種 unique（卡死）不觸發 cycling"""
        tracker = _make_tracker()
        for i in range(6):
            _record(tracker, i, "SyntaxError: always same")
        assert tracker.is_cycling(window=6, min_unique=2) is False


# ─────────────────────────────
# update_last_correction_prompt 與 to_failure_chain 測試
# ─────────────────────────────

class TestCorrectionPromptAudit:
    def test_update_last_correction_prompt_stored_in_chain(self):
        """update_last_correction_prompt 應寫入最後一筆 AttemptRecord，並出現在 to_failure_chain"""
        tracker = _make_tracker()
        _record(tracker, 0, "AssertionError", exit_code=1)
        tracker.update_last_correction_prompt("請修正 foo.py 第 42 行的型別問題")
        chain = tracker.to_failure_chain()
        assert chain[0]["correction_prompt_sent"] == "請修正 foo.py 第 42 行的型別問題"

    def test_update_on_empty_history_no_error(self):
        """空 history 時呼叫不應 raise"""
        tracker = _make_tracker()
        tracker.update_last_correction_prompt("some prompt")  # 不應 raise

    def test_failure_chain_has_correction_prompt_field(self):
        """to_failure_chain 的每筆記錄應包含 correction_prompt_sent 欄位"""
        tracker = _make_tracker()
        _record(tracker, 0, "SyntaxError", exit_code=1)
        chain = tracker.to_failure_chain()
        assert "correction_prompt_sent" in chain[0]
