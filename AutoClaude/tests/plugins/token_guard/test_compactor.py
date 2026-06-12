"""compactor.py 純函式 + CompactFailureState 單元測試（SD_07 W3-T3-10）。

對應子模組：autoclaude/plugins/token_guard/compactor.py
測試 API：
  - CompactFailureState（record/reset/is_critical）
  - build_compact_prompt（SD_05 W2-1d，純函式）
  - process_compact_result（SD_05 W2-1d + M-2 SSOT 拔除）

目標：≥ 5 case + coverage 100%
"""
from __future__ import annotations

from autoclaude.models.playbook import PlaybookTask
from autoclaude.plugins.token_guard.compactor import (
    CompactFailureState,
    build_compact_prompt,
    process_compact_result,
)


class TestCompactFailureState:
    def test_default_count_zero(self):
        s = CompactFailureState()
        assert s.count == 0
        assert s.is_critical() is False

    def test_record_failure_increments(self):
        s = CompactFailureState()
        assert s.record_failure() == 1
        assert s.record_failure() == 2
        assert s.count == 2

    def test_reset_clears_count(self):
        s = CompactFailureState(count=3)
        s.reset()
        assert s.count == 0
        assert s.is_critical() is False

    def test_is_critical_at_threshold(self):
        s = CompactFailureState(count=2, critical_threshold=2)
        assert s.is_critical() is True

    def test_custom_critical_threshold(self):
        s = CompactFailureState(count=3, critical_threshold=5)
        assert s.is_critical() is False
        s.count = 5
        assert s.is_critical() is True


class TestBuildCompactPrompt:
    def test_no_task_returns_base_prompt(self):
        prompt = build_compact_prompt()
        assert "/compact" in prompt
        assert "MEMORY ANCHOR" not in prompt

    def test_with_task_includes_anchor(self):
        task = PlaybookTask(step_id="T01", name="step name", prompt="p")
        prompt = build_compact_prompt(task=task, attempt=2)
        assert "MEMORY ANCHOR" in prompt
        assert "T01: step name" in prompt
        assert "[ATTEMPT] 3" in prompt

    def test_with_expected_regex_includes_success_condition(self):
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            expected_output_regex=r"\[DONE\]",
        )
        prompt = build_compact_prompt(task=task)
        assert "[SUCCESS_CONDITION]" in prompt
        # regex 原文保留 backslash escape
        assert r"\[DONE\]" in prompt

    def test_with_failure_summary(self):
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = build_compact_prompt(
            task=task, failure_summary="line1\nSyntaxError at line 42",
        )
        assert "[LAST_FAILURE]" in prompt
        assert "SyntaxError at line 42" in prompt
        # 結尾追加 failure summary 完整版
        assert "壓縮後必須記住以下當前失敗背景" in prompt

    def test_global_goal_truncation(self):
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        long_goal = "G" * 500
        prompt = build_compact_prompt(
            task=task, global_goal=long_goal, global_goal_anchor_chars=50,
        )
        assert "[GLOBAL_GOAL]" in prompt
        assert "…" in prompt  # 截斷標示

    def test_global_goal_short_no_ellipsis(self):
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = build_compact_prompt(
            task=task, global_goal="short", global_goal_anchor_chars=100,
        )
        assert "[GLOBAL_GOAL] short" in prompt


class TestProcessCompactResult:
    def test_compact_failed_increments_state(self):
        s = CompactFailureState()
        ok = process_compact_result(state=s, triggered_compact=True)
        assert ok is True  # 一次失敗未達 critical
        assert s.count == 1

    def test_critical_failure_returns_false(self):
        s = CompactFailureState(critical_threshold=2)
        process_compact_result(state=s, triggered_compact=True)
        ok = process_compact_result(state=s, triggered_compact=True)
        assert ok is False  # 連續 2 次達 critical
        assert s.count == 2

    def test_no_compact_resets_state(self):
        s = CompactFailureState(count=3)
        ok = process_compact_result(state=s, triggered_compact=False)
        assert ok is True
        assert s.count == 0
