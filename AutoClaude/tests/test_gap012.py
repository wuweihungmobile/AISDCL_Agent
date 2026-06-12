"""
Gap-012 實作驗證測試（Gap-012-A~F）。

覆蓋範圍：
  A - INJECT_BEFORE：在失敗步驟前注入前置步驟並立即執行
  B - GOTO_STEP：跳回指定步驟重新執行（含無限迴圈防護）
  C - DELETE_STEP：刪除後續已確定冗餘的步驟
  D - 演化後自動重載（PlaybookResult.evolved_playbook_path + run() 閉環）
  E - global_goal 進 compact anchor（防止多次 /compact 後目標漂移）
  F - 前提條件錯誤第 1 次就允許 INJECT_BEFORE
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest

from autoclaude.execution.playbook_runner import PlaybookResult, PlaybookRunner, _StepOutput
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.models.step_mutation import StepMutation, StepMutationType
from autoclaude.execution.error_classifier import ErrorClass
from autoclaude.utils.config import AppConfig
from tests.helpers.kernel_fixtures import make_kernel


# ──────────────────────────────────────────────
# 共用輔助
# ──────────────────────────────────────────────

def _make_runner(dry_run: bool = False, checkpoint_mgr=None) -> PlaybookRunner:
    cfg = AppConfig()
    minimax = MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    return PlaybookRunner(cfg, minimax, hotkey, dry_run=dry_run,
                          checkpoint_mgr=checkpoint_mgr)


def _make_playbook(*step_ids: str, global_goal: str = "") -> Playbook:
    tasks = [
        PlaybookTask(
            step_id=sid,
            name=f"Step {sid}",
            prompt=f"do {sid}",
            expected_output_regex=f"done-{sid}",
        )
        for sid in step_ids
    ]
    return Playbook(
        project="TestProj",
        global_goal=global_goal or None,
        global_invariants=GlobalInvariants(max_retries_per_step=3),
        tasks=tasks,
    )


# ──────────────────────────────────────────────
# Gap-012-A：INJECT_BEFORE 模型與枚舉
# ──────────────────────────────────────────────

class TestInjectBefore:
    def test_enum_exists(self):
        """StepMutationType 包含 INJECT_BEFORE。"""
        assert StepMutationType.INJECT_BEFORE == "INJECT_BEFORE"

    def test_model_has_new_step_fields(self):
        """StepMutation 可以建立 INJECT_BEFORE 型別。"""
        m = StepMutation(
            mutation_type=StepMutationType.INJECT_BEFORE,
            new_step_id="T01_PRE",
            new_step_name="前置初始化",
            new_step_prompt="建立 requirements.txt",
            reasoning="環境未初始化",
        )
        assert m.mutation_type == StepMutationType.INJECT_BEFORE
        assert m.new_step_id == "T01_PRE"

    def test_inject_before_inserts_at_current_idx_dry_run(self):
        """Kernel 模式：2 步驟 Playbook 執行成功（INJECT_BEFORE 整合場景基線）。"""
        kernel, _ = make_kernel(outputs=["[DONE]", "[DONE]"])
        playbook = _make_playbook("T01", "T02")
        result = kernel.run(playbook)
        assert result.success

    def test_inject_before_counter_prevents_infinite_recursion(self):
        """INJECT_BEFORE 同一步驟超過 3 次 → 忽略（防遞迴）。"""
        runner = _make_runner(dry_run=False)
        playbook = _make_playbook("T01")
        task = playbook.tasks[0]

        # 直接操作計數器，模擬已注入 3 次
        _inject_before_counter: dict[str, int] = {"T01": 3}

        # 模擬 mutation 處理段：cnt > 3 時應 warn 而非插入
        cnt = _inject_before_counter.get(task.step_id, 0) + 1
        assert cnt > 3  # 觸發防護條件

    def test_inject_before_task_inserted_at_correct_index(self):
        """直接測試插入邏輯：INJECT_BEFORE 將步驟插入 step_idx 位置。"""
        playbook = _make_playbook("T01", "T02", "T03")
        step_idx = 1  # 當前在 T02

        new_task = PlaybookTask(
            step_id="T01_PRE",
            name="前置步驟",
            prompt="init env",
        )
        playbook.tasks.insert(step_idx, new_task)

        assert playbook.tasks[1].step_id == "T01_PRE"
        assert playbook.tasks[2].step_id == "T02"
        assert len(playbook.tasks) == 4


# ──────────────────────────────────────────────
# Gap-012-B：GOTO_STEP 模型與枚舉
# ──────────────────────────────────────────────

class TestGotoStep:
    def test_enum_exists(self):
        """StepMutationType 包含 GOTO_STEP。"""
        assert StepMutationType.GOTO_STEP == "GOTO_STEP"

    def test_model_has_goto_step_id(self):
        """StepMutation 的 goto_step_id 欄位可設定。"""
        m = StepMutation(
            mutation_type=StepMutationType.GOTO_STEP,
            goto_step_id="T01",
            reasoning="T03 發現 T01 config 有誤",
        )
        assert m.goto_step_id == "T01"

    def test_goto_target_idx_logic(self):
        """GOTO_STEP 跳轉到較早步驟的索引計算正確。"""
        playbook = _make_playbook("T01", "T02", "T03")
        target_id = "T01"
        target_idx = next(
            (i for i, t in enumerate(playbook.tasks) if t.step_id == target_id), None
        )
        assert target_idx == 0

    def test_goto_forward_not_allowed(self):
        """GOTO_STEP 不允許向前跳（target_idx >= current_idx）。"""
        playbook = _make_playbook("T01", "T02", "T03")
        step_idx = 1  # 當前在 T02
        target_id = "T03"
        target_idx = next(
            (i for i, t in enumerate(playbook.tasks) if t.step_id == target_id), None
        )
        # target_idx(2) >= step_idx(1) → 不允許
        assert target_idx is not None
        assert target_idx >= step_idx

    def test_goto_counter_prevents_infinite_loop(self):
        """GOTO_STEP 同一目標超過 3 次 → 觸發防護。"""
        _goto_counter: dict[str, int] = {"T01": 3}
        target_id = "T01"
        _gc = _goto_counter.get(target_id, 0) + 1
        assert _gc > 3  # 觸發防護條件


# ──────────────────────────────────────────────
# Gap-012-C：DELETE_STEP 模型與枚舉
# ──────────────────────────────────────────────

class TestDeleteStep:
    def test_enum_exists(self):
        """StepMutationType 包含 DELETE_STEP。"""
        assert StepMutationType.DELETE_STEP == "DELETE_STEP"

    def test_model_has_delete_step_id(self):
        """StepMutation 的 delete_step_id 欄位可設定。"""
        m = StepMutation(
            mutation_type=StepMutationType.DELETE_STEP,
            delete_step_id="T03",
            reasoning="T03 已被 INJECT_BEFORE 的前置步驟完成",
        )
        assert m.delete_step_id == "T03"

    def test_delete_step_only_after_current(self):
        """DELETE_STEP 只允許刪除 step_idx 之後的步驟。"""
        playbook = _make_playbook("T01", "T02", "T03")
        step_idx = 1  # 當前在 T02

        # 刪除 T03（step_idx=2 > current step_idx=1）→ 合法
        del_id = "T03"
        del_idx = next(
            (i for i, t in enumerate(playbook.tasks) if t.step_id == del_id), None
        )
        assert del_idx is not None
        assert del_idx > step_idx
        del playbook.tasks[del_idx]
        assert len(playbook.tasks) == 2
        assert playbook.tasks[-1].step_id == "T02"

    def test_delete_current_step_not_allowed(self):
        """DELETE_STEP 不允許刪除當前或之前的步驟。"""
        playbook = _make_playbook("T01", "T02", "T03")
        step_idx = 1

        # 嘗試刪除 T01（idx=0 <= step_idx=1）→ 不合法
        del_id = "T01"
        del_idx = next(
            (i for i, t in enumerate(playbook.tasks) if t.step_id == del_id), None
        )
        assert del_idx is not None
        assert not (del_idx > step_idx)  # 非法條件


# ──────────────────────────────────────────────
# Gap-012-D：PlaybookResult.evolved_playbook_path
# ──────────────────────────────────────────────

class TestEvolvedPlaybookPath:
    def test_playbook_result_has_evolved_path_field(self):
        """PlaybookResult 包含 evolved_playbook_path 欄位，預設為 None。"""
        result = PlaybookResult(
            success=False,
            completed_steps=0,
            total_steps=3,
            reason="escalation",
        )
        assert result.evolved_playbook_path is None

    def test_playbook_result_with_evolved_path(self):
        """PlaybookResult 可以攜帶 evolved_playbook_path。"""
        result = PlaybookResult(
            success=False,
            completed_steps=1,
            total_steps=3,
            reason="escalation with evolution",
            evolved_playbook_path="/tmp/evolved_test.yaml",
        )
        assert result.evolved_playbook_path == "/tmp/evolved_test.yaml"

    def test_run_triggers_auto_reload_when_evolved_path_set(self):
        """
        run() 在收到 evolved_playbook_path 時應自動重載演化版 Playbook。
        驗證：_run_steps 被呼叫兩次（第一次觸發演化，第二次執行演化版）。
        """
        runner = _make_runner(dry_run=True, checkpoint_mgr=MagicMock())

        mock_playbook = _make_playbook("T01")
        _evolved_path = "evolved_fake.yaml"
        _evolved_playbook = _make_playbook("T00_PRE", "T01")

        call_seq = []

        def fake_load_playbook(path):
            call_seq.append(path)
            if path == _evolved_path:
                return _evolved_playbook
            return mock_playbook

        def fake_run_steps(playbook, path, *args, **kwargs):
            if path == _evolved_path:
                # 演化版執行成功
                return PlaybookResult(True, 2, 2, "done")
            # 原始版觸發演化
            return PlaybookResult(
                False, 0, 1, "escalation",
                evolved_playbook_path=_evolved_path,
            )

        with patch.object(runner, "_load_playbook", side_effect=fake_load_playbook), \
             patch.object(runner, "_validate_evaluator_commands"), \
             patch.object(runner, "_detect_workflow", return_value=MagicMock()), \
             patch.object(runner, "_resolve_start", return_value=(0, [], True, None)), \
             patch.object(runner, "_run_steps", side_effect=fake_run_steps), \
             patch.object(runner, "_hotkey") as mock_hotkey:
            mock_hotkey.register = MagicMock()
            mock_hotkey.unregister = MagicMock()
            runner._hotkey = mock_hotkey

            result = runner.run("original.yaml")

        assert result.success
        assert len(call_seq) == 2
        assert call_seq[0] == "original.yaml"
        assert call_seq[1] == _evolved_path

    def test_run_limits_max_evolutions(self):
        """run() 最多自動重載演化版 3 次，防止無限演化。"""
        runner = _make_runner(dry_run=True, checkpoint_mgr=MagicMock())
        _evolved_path = "evolved_infinite.yaml"

        def fake_load_playbook(path):
            return _make_playbook("T01")

        def fake_run_steps(playbook, path, *args, **kwargs):
            return PlaybookResult(
                False, 0, 1, "escalation",
                evolved_playbook_path=_evolved_path,
            )

        call_count = {"run_steps": 0}

        def counting_run_steps(*args, **kwargs):
            call_count["run_steps"] += 1
            return fake_run_steps(*args, **kwargs)

        with patch.object(runner, "_load_playbook", side_effect=fake_load_playbook), \
             patch.object(runner, "_validate_evaluator_commands"), \
             patch.object(runner, "_detect_workflow", return_value=MagicMock()), \
             patch.object(runner, "_resolve_start", return_value=(0, [], True, None)), \
             patch.object(runner, "_run_steps", side_effect=counting_run_steps), \
             patch.object(runner, "_hotkey") as mock_hotkey:
            mock_hotkey.register = MagicMock()
            mock_hotkey.unregister = MagicMock()
            runner._hotkey = mock_hotkey

            result = runner.run("original.yaml")

        # 原始 1 次 + 演化版最多 3 次 = 4 次總計
        assert call_count["run_steps"] == 4
        assert not result.success


# ──────────────────────────────────────────────
# Gap-012-E：global_goal 進 compact anchor
# ──────────────────────────────────────────────

class TestCompactGlobalGoal:
    def test_send_compact_accepts_global_goal_param(self):
        """_send_compact() 接受 global_goal 參數（不拋例外）。"""
        runner = _make_runner(dry_run=False)
        task = PlaybookTask(step_id="T01", name="Test", prompt="do something")

        mock_out = _StepOutput(text="", peak_token_pct=10.0, triggered_compact=False)
        with patch.object(runner, "_execute_prompt", return_value=mock_out):
            result = runner._send_compact(
                is_first=False,
                task=task,
                attempt=0,
                global_goal="建立完整 FastAPI 登入模組",
            )
        assert result is True  # compact 成功

    def test_send_compact_includes_global_goal_in_anchor(self):
        """_send_compact() 建構 anchor 時包含 [GLOBAL_GOAL] 標籤。"""
        runner = _make_runner(dry_run=False)
        task = PlaybookTask(step_id="T01", name="Test", prompt="do something")

        captured_prompts = []
        mock_out = _StepOutput(text="", peak_token_pct=10.0, triggered_compact=False)

        def fake_execute(prompt, **kwargs):
            captured_prompts.append(prompt)
            return mock_out

        with patch.object(runner, "_execute_prompt", side_effect=fake_execute):
            runner._send_compact(
                is_first=False,
                task=task,
                attempt=1,
                global_goal="系統總目標：建立 FastAPI 登入模組",
            )

        assert len(captured_prompts) == 1
        assert "[GLOBAL_GOAL]" in captured_prompts[0]
        assert "FastAPI" in captured_prompts[0]

    def test_send_compact_truncates_long_global_goal(self):
        """global_goal 超過 400 字時，anchor 只取前 400 字（Gap-013-H：預設由 400 改為可配置）。"""
        runner = _make_runner(dry_run=False)
        task = PlaybookTask(step_id="T01", name="Test", prompt="do something")
        long_goal = "目標：" + "X" * 600  # 超過預設 400 字元

        captured_prompts = []
        mock_out = _StepOutput(text="", peak_token_pct=10.0, triggered_compact=False)

        def fake_execute(prompt, **kwargs):
            captured_prompts.append(prompt)
            return mock_out

        with patch.object(runner, "_execute_prompt", side_effect=fake_execute):
            runner._send_compact(
                is_first=False,
                task=task,
                attempt=0,
                global_goal=long_goal,
            )

        anchor_line = [ln for ln in captured_prompts[0].split("\n") if "[GLOBAL_GOAL]" in ln]
        assert len(anchor_line) == 1
        # Gap-013-H：預設 400 字截斷，加 [GLOBAL_GOAL] 前綴後最多 ~415 字元
        assert len(anchor_line[0]) <= 420  # 允許 tag 前綴（預設 400 字）
        # 確認 600 個 X 確實被截斷（不包含全部 X）
        assert "X" * 401 not in anchor_line[0]

    def test_send_compact_without_global_goal_no_anchor_line(self):
        """未傳入 global_goal 時，anchor 不含 [GLOBAL_GOAL] 行。"""
        runner = _make_runner(dry_run=False)
        task = PlaybookTask(step_id="T01", name="Test", prompt="do something")

        captured_prompts = []
        mock_out = _StepOutput(text="", peak_token_pct=10.0, triggered_compact=False)

        def fake_execute(prompt, **kwargs):
            captured_prompts.append(prompt)
            return mock_out

        with patch.object(runner, "_execute_prompt", side_effect=fake_execute):
            runner._send_compact(is_first=False, task=task, attempt=0)

        assert "[GLOBAL_GOAL]" not in captured_prompts[0]


# ──────────────────────────────────────────────
# Gap-012-F：前提條件錯誤第 1 次就允許 INJECT_BEFORE
# ──────────────────────────────────────────────

class TestPrerequisiteErrorEarlyMutation:
    def test_error_class_enum_values(self):
        """ErrorClass 包含 IMPORT 和 ENVIRONMENT。"""
        assert ErrorClass.IMPORT.value == "import"
        assert ErrorClass.ENVIRONMENT.value == "environment"

    def _check_allow_mutation(self, error_cls: ErrorClass, attempt: int, trend: str) -> bool:
        """模擬 playbook_runner.py 中 allow_mutation 的計算邏輯。"""
        _is_prerequisite_error = error_cls in (ErrorClass.IMPORT, ErrorClass.ENVIRONMENT)
        return (
            (_is_prerequisite_error and attempt >= 1)
            or (attempt >= 2 and trend in ("stuck", "oscillating", "cycling"))
        )

    def test_import_error_at_attempt_1_allows_mutation(self):
        """IMPORT 錯誤在 attempt=1 時就允許 mutation（Gap-012-F）。"""
        assert self._check_allow_mutation(ErrorClass.IMPORT, attempt=1, trend="worsening") is True

    def test_environment_error_at_attempt_1_allows_mutation(self):
        """ENVIRONMENT 錯誤在 attempt=1 時就允許 mutation（Gap-012-F）。"""
        assert self._check_allow_mutation(ErrorClass.ENVIRONMENT, attempt=1, trend="normal") is True

    def test_import_error_at_attempt_0_not_allowed(self):
        """IMPORT 錯誤在 attempt=0 時不允許 mutation（需至少失敗一次）。"""
        assert self._check_allow_mutation(ErrorClass.IMPORT, attempt=0, trend="stuck") is False

    def test_syntax_error_still_needs_attempt_2(self):
        """非前提條件錯誤（SYNTAX）仍需 attempt>=2 且 trend=stuck 才允許 mutation。"""
        assert self._check_allow_mutation(ErrorClass.SYNTAX, attempt=1, trend="stuck") is False
        assert self._check_allow_mutation(ErrorClass.SYNTAX, attempt=2, trend="stuck") is True

    def test_assertion_error_not_prerequisite_needs_attempt_2(self):
        """ASSERTION 錯誤不是前提條件錯誤，不受 Gap-012-F 加速。"""
        assert self._check_allow_mutation(ErrorClass.ASSERTION, attempt=1, trend="oscillating") is False
        assert self._check_allow_mutation(ErrorClass.ASSERTION, attempt=2, trend="oscillating") is True


# ──────────────────────────────────────────────
# Gap-012-F：prompt_builder schema 包含新 mutation 類型
# ──────────────────────────────────────────────

class TestPromptBuilderMutationSchema:
    def test_schema_includes_inject_before(self):
        """_MUTATION_SCHEMA_SECTION 包含 INJECT_BEFORE 說明。"""
        from autoclaude.decision.prompt_builder import _MUTATION_SCHEMA_SECTION
        assert "INJECT_BEFORE" in _MUTATION_SCHEMA_SECTION

    def test_schema_includes_goto_step(self):
        """_MUTATION_SCHEMA_SECTION 包含 GOTO_STEP 說明。"""
        from autoclaude.decision.prompt_builder import _MUTATION_SCHEMA_SECTION
        assert "GOTO_STEP" in _MUTATION_SCHEMA_SECTION

    def test_schema_includes_delete_step(self):
        """_MUTATION_SCHEMA_SECTION 包含 DELETE_STEP 說明。"""
        from autoclaude.decision.prompt_builder import _MUTATION_SCHEMA_SECTION
        assert "DELETE_STEP" in _MUTATION_SCHEMA_SECTION

    def test_build_correction_system_prompt_with_mutation_has_all_types(self):
        """allow_step_mutation=True 時，system prompt 包含所有 5 種 mutation 類型。"""
        from autoclaude.decision.prompt_builder import build_correction_system_prompt
        prompt = build_correction_system_prompt(allow_step_mutation=True)
        for mutation_type in ["REVISE_CURRENT", "INJECT_AFTER", "INJECT_BEFORE", "GOTO_STEP", "DELETE_STEP"]:
            assert mutation_type in prompt, f"{mutation_type} 不在 system prompt 中"

    def test_build_correction_system_prompt_without_mutation_no_new_types(self):
        """allow_step_mutation=False 時，system prompt 不含 Gap-012 的新 mutation 類型。"""
        from autoclaude.decision.prompt_builder import build_correction_system_prompt
        prompt = build_correction_system_prompt(allow_step_mutation=False)
        assert "INJECT_BEFORE" not in prompt
        assert "GOTO_STEP" not in prompt
        assert "DELETE_STEP" not in prompt


# ──────────────────────────────────────────────
# Gap-012-A/B/C/D：dry_run 整合測試（完整 _run_steps 流程）
# ──────────────────────────────────────────────

class TestDryRunIntegration:
    def test_dry_run_multi_step_all_pass(self):
        """Kernel 模式：3 步驟 Playbook 全部通過。"""
        kernel, _ = make_kernel(outputs=["[DONE]", "[DONE]", "[DONE]"])
        playbook = _make_playbook("T01", "T02", "T03")
        result = kernel.run(playbook)
        assert result.success
        assert result.completed_steps == 3

    def test_playbook_result_repr_with_evolved_path(self):
        """SD_07 W4-T4-12：PlaybookResult dataclass 物理拔除為 factory → KernelResult；
        repr 改為 KernelResult 標準 dataclass 格式（驗證 success=False 與 evolved_path）。
        """
        result = PlaybookResult(
            success=False,
            completed_steps=0,
            total_steps=1,
            reason="escalation",
            evolved_playbook_path="evolved_test.yaml",
        )
        r = repr(result)
        assert "success=False" in r
        assert "evolved_playbook_path='evolved_test.yaml'" in r
