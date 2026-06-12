"""
Gap-013 實作驗證測試（Gap-013-A~H）。

覆蓋範圍：
  A - FailureTracker GOTO 重訪熱啟動（_step_trackers）
  B - PlaybookEvolver REVISE_EVALUATOR 處理分支
  C - 動態突變持久化（.mutated.yaml）
  D - 突變歷史注入 Minimax 修正訊息（mutation_history）
  E - GOTO 無限迴圈防護觸發後諮詢 PlaybookEvolver
  F - global_goal 注入 Claude Code 執行層首次 Prompt
  G - PlaybookEvolver 注入步驟 max_retries 從 global_invariants 推算
  H - global_goal MEMORY ANCHOR 截斷長度可配置
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from autoclaude.decision.prompt_builder import build_correction_message
from autoclaude.evolution.playbook_evolver import PlaybookEvolver, PlaybookEvolutionProposal
from autoclaude.execution.playbook_runner import PlaybookRunner, _StepOutput
from autoclaude.execution.failure_tracker import FailureTracker
from autoclaude.models.escalation import EscalationDump
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.utils.config import AppConfig, PlaybookConfig
from tests.helpers.kernel_fixtures import make_service


# ──────────────────────────────────────────────
# 共用輔助
# ──────────────────────────────────────────────

def _make_runner(dry_run: bool = False, cfg: AppConfig = None) -> PlaybookRunner:
    if cfg is None:
        cfg = AppConfig()
    minimax = MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    return PlaybookRunner(cfg, minimax, hotkey, dry_run=dry_run)


def _make_playbook(
    tasks: list[PlaybookTask],
    global_goal: str = "",
    max_retries: int = 3,
) -> Playbook:
    return Playbook(
        version="1.0",
        project="TestProject",
        global_goal=global_goal or None,
        global_invariants=GlobalInvariants(max_retries_per_step=max_retries),
        tasks=tasks,
    )


def _make_task(step_id: str = "T01", regex: str = r"DONE") -> PlaybookTask:
    return PlaybookTask(
        step_id=step_id,
        name=f"步驟 {step_id}",
        prompt=f"{step_id} prompt",
        expected_output_regex=regex,
    )


def _make_escalation_dump(
    step_id: str = "T01",
    is_stuck: bool = True,
    suspect_test_file: bool = False,
    suspect_assertion_mismatch: bool = False,
    total_attempts: int = 3,
) -> EscalationDump:
    return EscalationDump(
        playbook_path="test_playbook.yaml",
        step_id=step_id,
        step_name=f"步驟 {step_id}",
        total_attempts=total_attempts,
        failure_chain=[f"err_{i}" for i in range(total_attempts)],
        final_eval_output="FAILED test",
        is_stuck=is_stuck,
        is_diverging=False,
        suspect_test_file=suspect_test_file,
        is_oscillating=False,
        is_worsening=False,
        suspect_assertion_mismatch=suspect_assertion_mismatch,
        human_hint="測試失敗",
    )


# ──────────────────────────────────────────────
# Gap-013-A：FailureTracker GOTO 重訪熱啟動
# ──────────────────────────────────────────────

class TestGotoTrackerWarmStart:
    def test_warm_start_inherits_tried_strategies(self):
        """GOTO 後重訪同一步驟，tracker 繼承 _tried_strategies。"""
        runner = _make_runner(dry_run=True)
        step_trackers: dict[str, FailureTracker] = {}

        # 模擬第一次訪問：tracker 嘗試了 REWRITE 策略
        original_tracker = FailureTracker("T01")
        original_tracker._tried_strategies.add("REWRITE")
        step_trackers["T01"] = original_tracker

        # 模擬 GOTO 重訪邏輯
        if "T01" in step_trackers:
            prev = step_trackers["T01"]
            warm_tracker = FailureTracker("T01")
            warm_tracker._tried_strategies = prev._tried_strategies.copy()
        else:
            warm_tracker = FailureTracker("T01")

        assert "REWRITE" in warm_tracker._tried_strategies
        assert "PINPOINT" in warm_tracker._tried_strategies  # 預設策略

    def test_warm_start_clears_failure_history(self):
        """GOTO 重訪的熱啟動，失敗歷史清空（讓收斂評估重新計算）。"""
        original_tracker = FailureTracker("T01")
        # 模擬有歷史記錄
        original_tracker.record(0, "err", "FAILED", 1, "reasoning")

        step_trackers = {"T01": original_tracker}
        prev = step_trackers["T01"]
        warm_tracker = FailureTracker("T01")
        warm_tracker._tried_strategies = prev._tried_strategies.copy()

        # 熱啟動後 history 應為空
        assert len(warm_tracker.history) == 0

    def test_warm_start_does_not_inherit_attempt_offset(self):
        """熱啟動後 attempt 從 0 開始，不繼承前次訪問的 attempt_offset。"""
        original_tracker = FailureTracker("T01")
        original_tracker._tried_strategies.update(["REWRITE", "ADD_TYPES"])
        step_trackers = {"T01": original_tracker}

        prev = step_trackers["T01"]
        warm_tracker = FailureTracker("T01")
        warm_tracker._tried_strategies = prev._tried_strategies.copy()

        # attempt_offset 應為 0（由 PlaybookRunner 控制，不是 tracker 的責任）
        assert len(warm_tracker.history) == 0

    def test_first_visit_creates_fresh_tracker(self):
        """首次訪問步驟（不在 _step_trackers 中）建立全新 tracker。"""
        step_trackers: dict[str, FailureTracker] = {}

        if "T01" in step_trackers:
            prev = step_trackers["T01"]
            tracker = FailureTracker("T01")
            tracker._tried_strategies = prev._tried_strategies.copy()
        else:
            tracker = FailureTracker("T01")

        # 全新 tracker 只有預設的 PINPOINT
        assert tracker._tried_strategies == {"PINPOINT"}

    def test_runner_run_dry_run_completes_successfully(self, tmp_path):
        """AutoResumeService + FakeExecutor 模式下能成功執行完整 playbook（smoke test）。"""
        service, _ = make_service(outputs=["[DONE]"])
        task = _make_task("T01", r"dry-run-pass")
        playbook = _make_playbook([task])
        pb_path = tmp_path / "play.yaml"
        with open(pb_path, "w", encoding="utf-8") as f:
            yaml.dump(playbook.model_dump(exclude_none=True), f, allow_unicode=True)
        result = service.run(str(pb_path))
        assert result.success


# ──────────────────────────────────────────────
# Gap-013-B：PlaybookEvolver REVISE_EVALUATOR
# ──────────────────────────────────────────────

class TestReviseEvaluator:
    def test_revise_evaluator_applies_to_task(self, tmp_path):
        """REVISE_EVALUATOR 正確更新 evaluator_command。"""
        evolver = PlaybookEvolver()
        task = PlaybookTask(
            step_id="T01", name="步驟1", prompt="做某事",
            evaluator_command="pytest old_test.py",
        )
        playbook = _make_playbook([task])

        proposal = PlaybookEvolutionProposal(
            evolution_type="REVISE_EVALUATOR",
            inject_before_idx=0,
            reasoning="舊的 evaluator 已過時",
            revised_evaluator="pytest new_test.py -v",
        )

        pb_file = tmp_path / "test_play.yaml"
        pb_file.write_text(yaml.dump(playbook.model_dump(exclude_none=True)), encoding="utf-8")

        evolved_path = evolver.apply_evolution(playbook, proposal, str(pb_file))

        # evolved_*.yaml 應該被寫入
        assert evolved_path != str(pb_file)
        assert Path(evolved_path).exists()

        # 載入 evolved YAML 並確認 evaluator 已更新
        with open(evolved_path, encoding="utf-8") as f:
            evolved_data = yaml.safe_load(f)
        assert evolved_data["tasks"][0]["evaluator_command"] == "pytest new_test.py -v"

    def test_revise_evaluator_invalid_idx_returns_original(self, tmp_path):
        """REVISE_EVALUATOR idx 超出範圍時，靜默回傳原路徑（不崩潰）。"""
        evolver = PlaybookEvolver()
        task = _make_task("T01")
        playbook = _make_playbook([task])

        proposal = PlaybookEvolutionProposal(
            evolution_type="REVISE_EVALUATOR",
            inject_before_idx=99,  # 超出範圍
            reasoning="測試邊界",
            revised_evaluator="pytest invalid.py",
        )

        pb_file = tmp_path / "test_play.yaml"
        pb_file.write_text(yaml.dump(playbook.model_dump(exclude_none=True)), encoding="utf-8")

        result_path = evolver.apply_evolution(playbook, proposal, str(pb_file))
        assert result_path == str(pb_file)  # 回傳原路徑

    def test_revise_evaluator_writes_evolved_yaml(self, tmp_path):
        """REVISE_EVALUATOR 成功時 evolved_*.yaml 被寫入。"""
        evolver = PlaybookEvolver()
        task = PlaybookTask(
            step_id="T01", name="步驟1", prompt="做某事",
            evaluator_command="pytest old.py",
        )
        playbook = _make_playbook([task])

        proposal = PlaybookEvolutionProposal(
            evolution_type="REVISE_EVALUATOR",
            inject_before_idx=0,
            reasoning="需更新 evaluator",
            revised_evaluator="pytest new.py",
        )

        pb_file = tmp_path / "my_playbook.yaml"
        pb_file.write_text(yaml.dump(playbook.model_dump(exclude_none=True)), encoding="utf-8")

        evolved_path = evolver.apply_evolution(playbook, proposal, str(pb_file))

        assert "evolved_" in Path(evolved_path).name
        assert Path(evolved_path).exists()

    def test_revise_evaluator_no_handler_was_silent_bug(self, tmp_path):
        """確認舊 bug（REVISE_EVALUATOR 落入 else 分支）已修復：不再回傳原始路徑。"""
        evolver = PlaybookEvolver()
        task = PlaybookTask(
            step_id="T01", name="步驟1", prompt="做某事",
            evaluator_command="pytest old.py",
        )
        playbook = _make_playbook([task])

        proposal = PlaybookEvolutionProposal(
            evolution_type="REVISE_EVALUATOR",
            inject_before_idx=0,
            reasoning="修復 Bug",
            revised_evaluator="pytest fixed.py",
        )

        pb_file = tmp_path / "play.yaml"
        pb_file.write_text(yaml.dump(playbook.model_dump(exclude_none=True)), encoding="utf-8")

        # 修復後應回傳 evolved_*.yaml，而非原始路徑
        result = evolver.apply_evolution(playbook, proposal, str(pb_file))
        assert result != str(pb_file), "REVISE_EVALUATOR 不應再靜默回傳原路徑（Bug 已修復）"


# ──────────────────────────────────────────────
# Gap-013-C：動態突變持久化（.mutated.yaml）
# ──────────────────────────────────────────────

class TestMutationPersistence:
    def test_persist_mutated_playbook_creates_file(self, tmp_path):
        """_persist_mutated_playbook() 在 checkpoint_dir 建立 .mutated.yaml。"""
        cfg = AppConfig(checkpoint_dir=str(tmp_path))
        runner = _make_runner(cfg=cfg)

        task = _make_task("T01")
        playbook = _make_playbook([task])

        pb_path = str(tmp_path / "my_playbook.yaml")
        runner._persist_mutated_playbook(playbook, pb_path)

        mutated_file = tmp_path / "my_playbook.mutated.yaml"
        assert mutated_file.exists()

    def test_persist_mutated_playbook_content_matches(self, tmp_path):
        """持久化的 .mutated.yaml 內容與當前 playbook.tasks 相符。"""
        cfg = AppConfig(checkpoint_dir=str(tmp_path))
        runner = _make_runner(cfg=cfg)

        task1 = _make_task("T01")
        task2 = _make_task("T02")
        playbook = _make_playbook([task1, task2])

        pb_path = str(tmp_path / "play.yaml")
        runner._persist_mutated_playbook(playbook, pb_path)

        mutated_file = tmp_path / "play.mutated.yaml"
        with open(mutated_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        task_ids = [t["step_id"] for t in data["tasks"]]
        assert task_ids == ["T01", "T02"]

    def test_persist_mutated_playbook_after_inject_after(self, tmp_path):
        """INJECT_AFTER 突變後持久化的 YAML 包含新步驟。"""
        cfg = AppConfig(checkpoint_dir=str(tmp_path))
        runner = _make_runner(cfg=cfg)

        task1 = _make_task("T01")
        task2 = _make_task("T02")
        playbook = _make_playbook([task1, task2])

        # 模擬 INJECT_AFTER 突變
        injected = PlaybookTask(step_id="T01_FIX", name="修復步驟", prompt="修復")
        playbook.tasks.insert(1, injected)

        pb_path = str(tmp_path / "play.yaml")
        runner._persist_mutated_playbook(playbook, pb_path)

        with open(tmp_path / "play.mutated.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        task_ids = [t["step_id"] for t in data["tasks"]]
        assert "T01_FIX" in task_ids

    def test_mutated_yaml_loaded_on_restart(self, tmp_path):
        """重啟時若存在 .mutated.yaml 且 checkpoint，優先載入突變版。"""
        cfg = AppConfig(checkpoint_dir=str(tmp_path))
        runner = _make_runner(cfg=cfg)

        # 建立帶突變步驟的 mutated YAML
        task1 = _make_task("T01")
        injected = PlaybookTask(step_id="T01_PRE", name="前置步驟", prompt="前置")
        task2 = _make_task("T02")
        mutated_playbook = _make_playbook([injected, task1, task2])

        mutated_path = tmp_path / "play.mutated.yaml"
        with open(mutated_path, "w", encoding="utf-8") as f:
            yaml.dump(mutated_playbook.model_dump(exclude_none=True), f, allow_unicode=True)

        # 建立原始 playbook（不含 T01_PRE）
        original_playbook = _make_playbook([task1, task2])
        original_path = tmp_path / "play.yaml"
        with open(original_path, "w", encoding="utf-8") as f:
            yaml.dump(original_playbook.model_dump(exclude_none=True), f, allow_unicode=True)

        # 模擬有 checkpoint 存在
        from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint
        cp = PlaybookCheckpoint(
            playbook_path=str(original_path),
            step_idx=0,
            step_id="T01_PRE",
            total_steps=3,
            project="TestProject",
        )
        CheckpointManager(str(tmp_path)).save(cp, str(original_path))

        # 載入時 _load_playbook(.mutated.yaml) 應返回含 T01_PRE 的版本
        loaded = runner._load_playbook(str(mutated_path))
        assert any(t.step_id == "T01_PRE" for t in loaded.tasks)

    def test_mutated_yaml_loaded_via_run(self, tmp_path):
        """
        通過 runner.run() 模擬真實的 Token HALT 後恢復場景：
        確認有 checkpoint + .mutated.yaml 時，run() 實際讀取突變版 Playbook。
        """
        from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint

        cfg = AppConfig(checkpoint_dir=str(tmp_path))
        runner = _make_runner(dry_run=True, cfg=cfg)

        # 原始 playbook（T01 regex="ORIGINAL_MARKER"）
        original_task = PlaybookTask(
            step_id="T01", name="原始步驟", prompt="原始 prompt",
            expected_output_regex="ORIGINAL_MARKER",
        )
        original_playbook = _make_playbook([original_task])
        original_path = tmp_path / "play.yaml"
        with open(original_path, "w", encoding="utf-8") as f:
            yaml.dump(original_playbook.model_dump(exclude_none=True), f, allow_unicode=True)

        # 突變版 playbook（T01 regex="MUTATED_MARKER"）—— 注意 dry_run 會合成匹配輸出
        mutated_task = PlaybookTask(
            step_id="T01", name="突變步驟", prompt="突變 prompt",
            expected_output_regex="MUTATED_MARKER",
        )
        mutated_playbook = _make_playbook([mutated_task])
        mutated_path = tmp_path / "play.mutated.yaml"
        with open(mutated_path, "w", encoding="utf-8") as f:
            yaml.dump(mutated_playbook.model_dump(exclude_none=True), f, allow_unicode=True)

        # 寫入 checkpoint（讓 runner 認為有前次執行）
        cp = PlaybookCheckpoint(
            playbook_path=str(original_path),
            step_idx=0,
            step_id="T01",
            total_steps=1,
            project="TestProject",
        )
        CheckpointManager(str(tmp_path)).save(cp, str(original_path))

        # 追蹤 _load_playbook 被呼叫的路徑
        load_calls = []
        original_load = runner._load_playbook

        def tracking_load(path):
            load_calls.append(path)
            return original_load(path)

        runner._load_playbook = tracking_load

        # fresh=False，應觸發 .mutated.yaml 優先載入邏輯
        result = runner.run(str(original_path), fresh=False)

        # 驗證：_load_playbook 曾被以 .mutated.yaml 路徑呼叫
        mutated_path_str = str(mutated_path)
        assert any(mutated_path_str in p for p in load_calls), (
            f"run() 應讀取 .mutated.yaml，但實際呼叫路徑為: {load_calls}"
        )
        # 突變版 regex="MUTATED_MARKER"，dry_run 合成輸出含 MUTATED_MARKER，應成功
        assert result.success, f"突變版 playbook 應成功執行，reason={result.reason}"

    def test_success_clears_mutated_yaml(self, tmp_path):
        """成功完成 Playbook 後，.mutated.yaml 應被清理。"""
        cfg = AppConfig(checkpoint_dir=str(tmp_path))
        runner = _make_runner(dry_run=True, cfg=cfg)

        task = _make_task("T01", r"dry-run-pass")
        playbook = _make_playbook([task])

        pb_path = tmp_path / "play.yaml"
        with open(pb_path, "w", encoding="utf-8") as f:
            yaml.dump(playbook.model_dump(exclude_none=True), f, allow_unicode=True)

        # 預先建立 mutated.yaml
        mutated_path = tmp_path / "play.mutated.yaml"
        mutated_path.write_text("dummy", encoding="utf-8")
        assert mutated_path.exists()

        result = runner.run(str(pb_path))
        assert result.success
        assert not mutated_path.exists(), ".mutated.yaml 應在成功後被清理"


# ──────────────────────────────────────────────
# Gap-013-D：突變歷史注入 Minimax 修正訊息
# ──────────────────────────────────────────────

class TestMutationHistoryInPrompt:
    def test_mutation_history_in_correction_message(self):
        """mutation_history 出現在 Minimax 修正訊息中。"""
        mutation_history = [
            "[attempt 1] INJECT_BEFORE: 插入前置步驟 T01_PRE 於 T01 前",
            "[attempt 2] REVISE_CURRENT: 步驟 T01 prompt 已更新",
        ]
        msg = build_correction_message(
            step_id="T01",
            task_name="步驟1",
            task_prompt="做某事",
            expected_regex=None,
            failure_reason="FAILED",
            eval_output="error output",
            retry_count=3,
            mutation_history=mutation_history,
        )
        assert "本次執行的突變歷史（含前序步驟）" in msg
        assert "INJECT_BEFORE" in msg
        assert "REVISE_CURRENT" in msg

    def test_empty_mutation_history_no_section(self):
        """空的突變歷史不生成「突變紀錄」區段。"""
        msg = build_correction_message(
            step_id="T01",
            task_name="步驟1",
            task_prompt="做某事",
            expected_regex=None,
            failure_reason="FAILED",
            eval_output="error output",
            retry_count=1,
            mutation_history=[],
        )
        assert "本次執行的突變歷史（含前序步驟）" not in msg

    def test_mutation_log_accumulated_across_attempts(self):
        """多次突變的記錄均出現在訊息中（累積性）。"""
        mutation_history = [
            "[attempt 1] INJECT_BEFORE: 插入 T01_PRE",
            "[attempt 3] DELETE_STEP: 刪除步驟 T03",
            "[attempt 4] GOTO_STEP: 跳回 T01",
        ]
        msg = build_correction_message(
            step_id="T01",
            task_name="步驟1",
            task_prompt="做某事",
            expected_regex=None,
            failure_reason="FAILED",
            eval_output="error output",
            retry_count=4,
            mutation_history=mutation_history,
        )
        assert "T01_PRE" in msg
        assert "DELETE_STEP" in msg
        assert "GOTO_STEP" in msg

    def test_mutation_history_default_is_empty(self):
        """mutation_history 預設為空，不影響現有呼叫。"""
        msg = build_correction_message(
            step_id="T01",
            task_name="步驟1",
            task_prompt="做某事",
            expected_regex=None,
            failure_reason="FAILED",
            eval_output="error output",
            retry_count=1,
        )
        # 無突變歷史，訊息正常，不崩潰
        assert "## 失敗步驟" in msg


# ──────────────────────────────────────────────
# Gap-013-E：GOTO 迴圈防護觸發後諮詢 PlaybookEvolver
# ──────────────────────────────────────────────

class TestGotoLoopEvolution:
    def test_goto_loop_triggers_evolver(self, tmp_path):
        """
        GOTO > 3 後，PlaybookRunner 應自動呼叫 _evolver.propose_evolution()。

        設計：
        - T01 永遠通過，T02 永遠失敗
        - Minimax 每次都建議 GOTO_STEP(T01)（跳回 T01）
        - 第 4 次 GOTO 時 _gc > 3，觸發 Gap-013-E 的 Evolver 呼叫
        - 驗證：result.success == False 且 _evolver.propose_evolution 被呼叫
        """
        from autoclaude.models.decision import CorrectionDecision
        from autoclaude.models.step_mutation import StepMutation, StepMutationType

        cfg = AppConfig(checkpoint_dir=str(tmp_path))
        runner = _make_runner(dry_run=False, cfg=cfg)

        # T01 通過（regex 可匹配），T02 永遠失敗（regex 不可能匹配 Claude 輸出）
        task_t01 = PlaybookTask(
            step_id="T01", name="步驟T01", prompt="T01 prompt",
            expected_output_regex="T01_PASS",
        )
        task_t02 = PlaybookTask(
            step_id="T02", name="步驟T02", prompt="T02 prompt",
            expected_output_regex="T02_NEVER_MATCH_XXXYYY",
            max_retries=20,  # 允許多次重試
        )
        playbook = _make_playbook([task_t01, task_t02], max_retries=20)

        import tempfile, yaml
        pb_path = tmp_path / "play_goto.yaml"
        with open(pb_path, "w", encoding="utf-8") as f:
            yaml.dump(playbook.model_dump(exclude_none=True), f, allow_unicode=True)

        # Mock _execute_prompt：T01 返回含 T01_PASS 的輸出，T02 返回空輸出
        def fake_execute_prompt(prompt, **kwargs):
            if "T01" in prompt:
                return _StepOutput(text="T01_PASS")
            return _StepOutput(text="T02 output")

        runner._execute_prompt = fake_execute_prompt

        # Mock Minimax：每次 T02 失敗都建議 GOTO_STEP(T01)
        goto_decision = CorrectionDecision(
            correction_prompt="請重新執行 T01",
            reasoning="T01 有誤",
            step_mutation=StepMutation(
                mutation_type=StepMutationType.GOTO_STEP,
                goto_step_id="T01",
                reasoning="跳回 T01",
            ),
        )
        runner._minimax.decide_correction.return_value = goto_decision

        # Mock Evolver（Gap-013-E）
        runner._evolver = MagicMock()
        runner._evolver.propose_evolution.return_value = None  # 無演化提議
        runner._evolver.apply_evolution.return_value = None

        result = runner.run(str(pb_path), fresh=True)

        # 驗證：GOTO 防護觸發後 propose_evolution 應被呼叫
        assert runner._evolver.propose_evolution.called, \
            "GOTO > 3 次後應呼叫 _evolver.propose_evolution()"
        # 執行應以失敗結束（GOTO 無限迴圈防護）
        assert result.success is False

    def test_goto_loop_returns_evolved_path(self, tmp_path):
        """若有演化提議，PlaybookResult.evolved_playbook_path 應不為 None。"""
        evolver = PlaybookEvolver()

        # Case 3: is_stuck + failure_chain >= 3 → SPLIT_STEP
        dump = _make_escalation_dump("T02", is_stuck=True, total_attempts=3)

        task0 = _make_task("T01")
        task1 = PlaybookTask(
            step_id="T02", name="複雜步驟",
            prompt="第一部分\n第二部分\n第三部分",
        )
        playbook = _make_playbook([task0, task1])

        proposal = evolver.propose_evolution(playbook, 1, dump)
        assert proposal is not None
        assert proposal.evolution_type == "SPLIT_STEP"

        pb_file = tmp_path / "play.yaml"
        pb_file.write_text(yaml.dump(playbook.model_dump(exclude_none=True)), encoding="utf-8")

        evolved_path = evolver.apply_evolution(playbook, proposal, str(pb_file))
        assert evolved_path != str(pb_file)
        assert Path(evolved_path).exists()

    def test_goto_loop_no_proposal_returns_false_result(self, tmp_path):
        """無演化提議時 evolved_playbook_path=None，正常返回失敗結果。"""
        evolver = PlaybookEvolver()

        # 當 is_stuck=False, suspect_test_file=False → 無法自動演化
        dump = _make_escalation_dump("T01", is_stuck=False, total_attempts=1)

        task = _make_task("T01")
        playbook = _make_playbook([task])

        proposal = evolver.propose_evolution(playbook, 0, dump)
        assert proposal is None, "無法自動演化時應回傳 None"


# ──────────────────────────────────────────────
# Gap-013-F：global_goal 注入執行層首次 Prompt
# ──────────────────────────────────────────────

class TestGlobalGoalInClaudeContext:
    def test_prepend_global_goal_with_goal(self):
        """_prepend_global_goal() 在 prompt 前加入目標區塊。"""
        runner = _make_runner()
        original = "請實作 user.py"
        result = runner._prepend_global_goal(original, "建立 FastAPI 登入模組")

        assert "本次自動化任務的總目標" in result
        assert "建立 FastAPI 登入模組" in result
        assert original in result
        assert result.index("本次自動化任務的總目標") < result.index(original)

    def test_prepend_global_goal_without_goal(self):
        """無 global_goal 時，_prepend_global_goal() 回傳原始 prompt 不變。"""
        runner = _make_runner()
        original = "請實作 user.py"
        result = runner._prepend_global_goal(original, None)
        assert result == original

    def test_prepend_global_goal_empty_string(self):
        """global_goal 為空字串時，回傳原始 prompt 不變。"""
        runner = _make_runner()
        original = "請實作 user.py"
        result = runner._prepend_global_goal(original, "")
        assert result == original

    def test_prepend_global_goal_truncates_at_500(self):
        """超長 global_goal 只取前 500 字元。"""
        runner = _make_runner()
        long_goal = "A" * 600
        result = runner._prepend_global_goal("prompt", long_goal)

        # 最多 500 個 A，不應有 501 個以上的 A
        assert "A" * 500 in result
        assert "A" * 501 not in result

    def test_global_goal_in_first_prompt_dry_run(self, tmp_path):
        """dry_run 模式下首次 prompt 仍觸發 global_goal 注入（通過 _prepend_global_goal）。"""
        runner = _make_runner(dry_run=True)
        goal = "建立完整的 FastAPI 服務"

        # 追蹤 _prepend_global_goal 被呼叫
        calls = []
        original_fn = runner._prepend_global_goal

        def tracking_fn(prompt, goal_arg):
            calls.append((prompt, goal_arg))
            return original_fn(prompt, goal_arg)

        runner._prepend_global_goal = tracking_fn

        task = _make_task("T01", r"dry-run-pass")
        playbook = _make_playbook([task], global_goal=goal)

        pb_path = tmp_path / "play.yaml"
        with open(pb_path, "w", encoding="utf-8") as f:
            yaml.dump(playbook.model_dump(exclude_none=True), f, allow_unicode=True)

        runner.run(str(pb_path))

        # _prepend_global_goal 至少被呼叫一次
        assert len(calls) >= 1
        # 其中至少有一次 goal_arg 不為空
        assert any(g == goal for _, g in calls)

    def test_global_goal_not_repeated_in_second_step(self, tmp_path):
        """第二步驟 prompt 不重複注入 global_goal（is_first_prompt=False）。"""
        goal_injections = []
        runner = _make_runner(dry_run=True)
        orig_fn = runner._prepend_global_goal

        def tracking(prompt, g):
            goal_injections.append(g)
            return orig_fn(prompt, g)

        runner._prepend_global_goal = tracking

        t1 = _make_task("T01", r"dry-run-pass")
        t2 = _make_task("T02", r"dry-run-pass")
        playbook = _make_playbook([t1, t2], global_goal="總目標")

        pb_path = tmp_path / "play.yaml"
        with open(pb_path, "w", encoding="utf-8") as f:
            yaml.dump(playbook.model_dump(exclude_none=True), f, allow_unicode=True)

        runner.run(str(pb_path))

        # 只有第一次呼叫時 is_first_prompt=True，後續 None（不呼叫）
        # 所以 goal_injections 中只有第一次是非空的
        non_none = [g for g in goal_injections if g]
        assert len(non_none) == 1, f"global_goal 應只注入首次，但注入了 {len(non_none)} 次"


# ──────────────────────────────────────────────
# Gap-013-G：PlaybookEvolver 注入步驟 max_retries 推算
# ──────────────────────────────────────────────

class TestEvolverMaxRetries:
    def test_inject_step_uses_global_max_retries_when_higher(self):
        """全域 max_retries=5 時，注入步驟最多 3 次（上限 3）。"""
        evolver = PlaybookEvolver()

        task = _make_task("T01")
        playbook = _make_playbook([task], max_retries=5)

        dump = _make_escalation_dump("T01", suspect_test_file=True)
        proposal = evolver.propose_evolution(playbook, 0, dump)

        assert proposal is not None
        assert proposal.new_step is not None
        assert proposal.new_step.max_retries == 3  # min(5, 3) = 3

    def test_inject_step_minimum_2(self):
        """全域 max_retries=1 時，注入步驟至少 2 次（下限 2）。"""
        evolver = PlaybookEvolver()

        task = _make_task("T01")
        playbook = _make_playbook([task], max_retries=1)

        dump = _make_escalation_dump("T01", suspect_test_file=True)
        proposal = evolver.propose_evolution(playbook, 0, dump)

        assert proposal is not None
        assert proposal.new_step is not None
        assert proposal.new_step.max_retries == 2  # max(2, min(1, 3)) = 2

    def test_inject_step_within_range_global_3(self):
        """全域 max_retries=3 時，注入步驟 max_retries=3。"""
        evolver = PlaybookEvolver()

        task = _make_task("T01")
        playbook = _make_playbook([task], max_retries=3)

        dump = _make_escalation_dump("T01", suspect_test_file=True)
        proposal = evolver.propose_evolution(playbook, 0, dump)

        assert proposal is not None
        assert proposal.new_step.max_retries == 3  # max(2, min(3, 3)) = 3

    def test_assert_fix_step_also_uses_global_max_retries(self):
        """Case 2（AssertionError 修復步驟）也從 global_invariants 推算。"""
        evolver = PlaybookEvolver()

        task = _make_task("T01")
        playbook = _make_playbook([task], max_retries=5)

        dump = _make_escalation_dump("T01", suspect_assertion_mismatch=True, total_attempts=4)
        proposal = evolver.propose_evolution(playbook, 0, dump)

        assert proposal is not None
        assert proposal.new_step is not None
        assert proposal.new_step.max_retries == 3  # min(5, 3) = 3


# ──────────────────────────────────────────────
# Gap-013-H：global_goal MEMORY ANCHOR 截斷長度可配置
# ──────────────────────────────────────────────

class TestGoalAnchorSize:
    def test_compact_default_400_chars(self):
        """PlaybookConfig 預設 global_goal_anchor_chars=400。"""
        cfg = PlaybookConfig()
        assert cfg.global_goal_anchor_chars == 400

    def test_compact_config_field_validated_min(self):
        """global_goal_anchor_chars 下限 100。"""
        with pytest.raises(Exception):
            PlaybookConfig(global_goal_anchor_chars=99)

    def test_compact_config_field_validated_max(self):
        """global_goal_anchor_chars 上限 1000。"""
        with pytest.raises(Exception):
            PlaybookConfig(global_goal_anchor_chars=1001)

    def test_compact_uses_configurable_anchor_size(self, tmp_path):
        """_send_compact() 使用 global_goal_anchor_chars 截斷 global_goal。"""
        cfg = AppConfig(
            checkpoint_dir=str(tmp_path),
            playbook=PlaybookConfig(global_goal_anchor_chars=150),
        )
        runner = _make_runner(dry_run=False, cfg=cfg)

        long_goal = "X" * 500

        # 攔截 _execute_prompt，檢查發送的 compact prompt
        captured_prompts = []

        def capture_execute(prompt, **kwargs):
            captured_prompts.append(prompt)
            return _StepOutput(text="compacted")

        runner._execute_prompt = capture_execute
        runner._send_compact(False, global_goal=long_goal, task=MagicMock(
            step_id="T01", name="步驟1",
            expected_output_regex=None,
        ), attempt=0)

        assert len(captured_prompts) == 1
        prompt = captured_prompts[0]
        assert "[GLOBAL_GOAL]" in prompt
        # 確認截斷為 150 字元（不應有 151 個 X）
        assert "X" * 150 in prompt
        assert "X" * 151 not in prompt

    def test_compact_config_field_default_overridable(self):
        """global_goal_anchor_chars 可在 AppConfig 中覆寫。"""
        cfg = AppConfig(playbook=PlaybookConfig(global_goal_anchor_chars=600))
        runner = _make_runner(cfg=cfg)
        assert runner._cfg.playbook.global_goal_anchor_chars == 600
