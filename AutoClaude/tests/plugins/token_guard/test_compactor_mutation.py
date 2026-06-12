"""compactor.py 補強測試 — SD_09 W1 A-1（mutation pilot kill rate ≥ 70%）。

對應 SD_Improving_09 W1 範疇：針對 mutmut 2.4.3 在 compactor.py 留下的 24 個 survived
mutation（mutmut id: 12-16, 18, 23, 25-30, 33-35, 37, 41-47），補強：
  - boundary：`is_critical()` 在 count == threshold 時觸發
  - constant：default values 精確值（critical_threshold=2、count=0）
  - return value：build_compact_prompt 的字串組裝、process_compact_result 的 True/False
  - branch：每個 if 分支都被走過
  - string_literal：anchor 文字、prompt 段落結構精確比對

不重複 test_compactor.py 既有 7 case；本檔聚焦 mutmut survived 殘留點位。
"""
from __future__ import annotations

from autoclaude.models.playbook import PlaybookTask
from autoclaude.plugins.token_guard.compactor import (
    CompactFailureState,
    build_compact_prompt,
    process_compact_result,
)


class TestCompactFailureStateMutations:
    """SD_09 W1：補 24 survived 中與 CompactFailureState 相關（id 12-16, 18, 23, 25-30）。"""

    def test_default_critical_threshold_is_exactly_2(self):
        """殺 `critical_threshold=2` → `critical_threshold=3` 之類 constant mutation。"""
        s = CompactFailureState()
        assert s.critical_threshold == 2

    def test_default_count_is_exactly_0(self):
        """殺 `count: int = 0` → `count: int = 1` constant mutation。"""
        s = CompactFailureState()
        assert s.count == 0

    def test_is_critical_below_threshold_is_false(self):
        """殺 `>= → >` boundary mutation：count=1, threshold=2 → 仍 False。"""
        s = CompactFailureState(count=1, critical_threshold=2)
        assert s.is_critical() is False

    def test_is_critical_at_exact_threshold_is_true(self):
        """殺 `>= → >` boundary mutation：count=2, threshold=2 → True（>= 是必要的）。"""
        s = CompactFailureState(count=2, critical_threshold=2)
        assert s.is_critical() is True

    def test_is_critical_above_threshold_is_true(self):
        """殺 `>= → ==` boundary mutation：count=3 > threshold=2 → 仍 True。"""
        s = CompactFailureState(count=3, critical_threshold=2)
        assert s.is_critical() is True

    def test_record_failure_returns_new_count(self):
        """殺 `return self.count` → `return self.count - 1` 之類 mutation。"""
        s = CompactFailureState()
        assert s.record_failure() == 1  # 起始 0+1
        assert s.record_failure() == 2
        assert s.record_failure() == 3

    def test_record_failure_increments_by_exactly_one(self):
        """殺 `self.count += 1` → `+= 2` arithmetic mutation。"""
        s = CompactFailureState(count=5)
        s.record_failure()
        assert s.count == 6  # 不是 7、不是 5+2

    def test_reset_sets_count_to_exactly_zero(self):
        """殺 `self.count = 0` → `= 1` / `-= 1` mutation。"""
        s = CompactFailureState(count=100)
        s.reset()
        assert s.count == 0

    def test_reset_does_not_change_threshold(self):
        """殺 reset 額外行為 mutation；threshold 應 untouched。"""
        s = CompactFailureState(count=5, critical_threshold=7)
        s.reset()
        assert s.critical_threshold == 7


class TestBuildCompactPromptMutations:
    """SD_09 W1：build_compact_prompt 24 mutation 中對應字串組裝/分支點位。"""

    def test_anchor_attempt_label_is_attempt_plus_one(self):
        """殺 `[ATTEMPT] {attempt + 1}` → `attempt` / `attempt - 1` mutation。"""
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = build_compact_prompt(task=task, attempt=0)
        assert "[ATTEMPT] 1" in prompt
        prompt = build_compact_prompt(task=task, attempt=5)
        assert "[ATTEMPT] 6" in prompt

    def test_anchor_contains_active_task_label(self):
        """殺 `[ACTIVE_TASK]` 字串字面值 mutation。"""
        task = PlaybookTask(step_id="X9", name="my_step", prompt="p")
        prompt = build_compact_prompt(task=task, attempt=0)
        assert "[ACTIVE_TASK] X9: my_step" in prompt

    def test_memory_anchor_header_present_with_task(self):
        """殺 anchor 開頭字串 mutation。"""
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = build_compact_prompt(task=task)
        assert "=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===" in prompt
        assert "=== END ANCHOR ===" in prompt

    def test_no_task_no_anchor_header(self):
        """殺 `if task is not None:` 分支條件翻轉 mutation。"""
        prompt = build_compact_prompt(task=None)
        assert "MEMORY ANCHOR" not in prompt
        assert "[ACTIVE_TASK]" not in prompt
        assert "END ANCHOR" not in prompt

    def test_expected_regex_omitted_when_none(self):
        """殺 `if task.expected_output_regex:` 條件 mutation。"""
        task = PlaybookTask(step_id="T01", name="n", prompt="p", expected_output_regex=None)
        prompt = build_compact_prompt(task=task)
        assert "[SUCCESS_CONDITION]" not in prompt

    def test_failure_summary_last_line_truncated_to_120_chars(self):
        """殺 `[:120]` slice 常量 mutation（如 :119 / :121 / 不切）。"""
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        long_last = "E" * 300
        prompt = build_compact_prompt(task=task, failure_summary=f"prev\n{long_last}")
        # anchor 內僅取 120 字
        anchor_block = prompt.split("=== END ANCHOR ===")[0]
        # [LAST_FAILURE] line 後面恰好 120 個 E
        assert "[LAST_FAILURE] " + "E" * 120 + "\n" in anchor_block
        # 121 個 E 不應出現於 anchor 內
        assert "[LAST_FAILURE] " + "E" * 121 not in anchor_block

    def test_failure_summary_split_keeps_last_line(self):
        """殺 `.split("\\n")[-1]` 中 `-1` index mutation（如 0 / -2）。"""
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = build_compact_prompt(
            task=task, failure_summary="line0\nline1\nFINAL_ERR",
        )
        # anchor 取最後一行 FINAL_ERR
        assert "[LAST_FAILURE] FINAL_ERR" in prompt

    def test_global_goal_anchor_chars_default_is_200(self):
        """殺 `global_goal_anchor_chars: int = 200` default value mutation。"""
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        long_goal = "G" * 250
        prompt = build_compact_prompt(task=task, global_goal=long_goal)
        # 預設 200 → 取前 200 G 後加 …
        assert "G" * 200 + "…" in prompt
        # 201 個 G 不應出現
        assert "G" * 201 not in prompt

    def test_global_goal_at_exact_anchor_chars_no_ellipsis(self):
        """殺 `len(global_goal) > global_goal_anchor_chars` boundary mutation。"""
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        # 長度恰等於 anchor_chars → 不加 …
        prompt = build_compact_prompt(
            task=task, global_goal="G" * 50, global_goal_anchor_chars=50,
        )
        assert "[GLOBAL_GOAL] " + "G" * 50 + "\n" in prompt
        assert "…" not in prompt

    def test_global_goal_one_over_anchor_chars_has_ellipsis(self):
        """殺 boundary mutation：51 chars vs 50 limit → 加 …"""
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = build_compact_prompt(
            task=task, global_goal="G" * 51, global_goal_anchor_chars=50,
        )
        # 取前 50 + …
        assert "[GLOBAL_GOAL] " + "G" * 50 + "…\n" in prompt

    def test_compact_command_present(self):
        """殺 `/compact` 字串字面值刪除 mutation。"""
        prompt = build_compact_prompt()
        assert prompt.startswith("/compact\n")

    def test_compact_priority_lines_preserved(self):
        """殺 prompt 內容字串 mutation。"""
        prompt = build_compact_prompt()
        assert "1. 目前正在實作的檔案清單與關鍵函式名稱" in prompt
        assert "2. 測試案例的名稱與期望行為" in prompt
        assert "3. 最近一次的錯誤訊息" in prompt

    def test_failure_summary_appended_after_anchor(self):
        """殺 `if failure_summary:` 條件 mutation + 末尾追加邏輯。"""
        prompt_no_fs = build_compact_prompt()
        prompt_with_fs = build_compact_prompt(failure_summary="boom")
        # 沒有 failure_summary 不該有此段
        assert "壓縮後必須記住" not in prompt_no_fs
        # 有 failure_summary 必須出現於結尾
        assert "壓縮後必須記住以下當前失敗背景" in prompt_with_fs
        assert prompt_with_fs.rstrip().endswith("boom")


class TestProcessCompactResultMutations:
    """SD_09 W1：process_compact_result 相關（mutation id 41-47 約涵蓋此函式）。"""

    def test_no_compact_returns_true_and_resets(self):
        """殺 `triggered_compact` boolean condition mutation + reset 行為。"""
        s = CompactFailureState(count=5)
        result = process_compact_result(state=s, triggered_compact=False)
        assert result is True
        assert s.count == 0  # reset 必須清零

    def test_first_compact_returns_true(self):
        """殺 `is_critical()` 返回邏輯 mutation。count=1 < threshold=2 → True。"""
        s = CompactFailureState(critical_threshold=2)
        result = process_compact_result(state=s, triggered_compact=True)
        assert result is True
        assert s.count == 1

    def test_second_compact_returns_false_critical(self):
        """殺 critical 返回 False 的邏輯 mutation。連續 2 次達 threshold=2 → False。"""
        s = CompactFailureState(critical_threshold=2)
        process_compact_result(state=s, triggered_compact=True)
        result = process_compact_result(state=s, triggered_compact=True)
        assert result is False  # 不是 True，不是 None
        assert s.count == 2

    def test_compact_does_not_reset(self):
        """殺 `else: reset()` 分支提前執行的 mutation。"""
        s = CompactFailureState(count=3)
        process_compact_result(state=s, triggered_compact=True)
        assert s.count == 4  # 應從 3 → 4，不是被 reset 至 0+1

    def test_no_compact_with_zero_count_still_returns_true(self):
        """殺 `return True` mutation。"""
        s = CompactFailureState(count=0)
        assert process_compact_result(state=s, triggered_compact=False) is True
        assert s.count == 0
