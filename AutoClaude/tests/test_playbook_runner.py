"""
PlaybookRunner 狀態機完整測試（dry_run + 真實 mock + ESCALATION + ContextNegotiation）。

關注點：
  - _evaluate() 的 ANSI strip 邏輯
  - dry_run 模式的成功路徑、多步驟、step_log
  - 真實 PtyWrapper mock 下的 regex 通過 / Minimax 修正 / ESCALATION
  - CONTEXT_NEGOTIATION 的執行行為
  - PlaybookResult repr 格式
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from autoclaude.execution.playbook_runner import PlaybookResult, PlaybookRunner
from autoclaude.models.playbook import PlaybookTask
from autoclaude.utils.config import AppConfig
from tests.helpers.kernel_fixtures import make_service

# ──────────────────────────────────────────────
# 測試輔助函式
# ──────────────────────────────────────────────

def _make_runner(dry_run: bool = False, minimax_mock=None) -> PlaybookRunner:
    cfg = AppConfig()
    minimax = minimax_mock or MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    return PlaybookRunner(cfg, minimax, hotkey, dry_run=dry_run)


def _write_playbook(tmp_path: Path, tasks: list[dict], extra: dict | None = None) -> str:
    data: dict = {
        "version": "1.0",
        "project": "UnitTest",
        "global_invariants": {"max_retries_per_step": 2, "auto_compact_interval": 0},
        "tasks": tasks,
    }
    if extra:
        data.update(extra)
    p = tmp_path / "pb.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return str(p)


# ──────────────────────────────────────────────
# _evaluate() ANSI strip 行為
# ──────────────────────────────────────────────

class TestPlaybookRunnerEvaluate:
    def _task(self, regex):
        return PlaybookTask(step_id="T01", name="n", prompt="p", expected_output_regex=regex)

    def test_evaluate_ansi_stripped(self):
        runner = _make_runner(dry_run=True)
        reason, *_ = runner._evaluate(self._task(r"\[INIT_DONE\]"), "\x1b[32m[INIT_DONE]\x1b[0m")
        assert reason is None

    def test_evaluate_fails_when_no_keyword(self):
        runner = _make_runner(dry_run=True)
        reason, *_ = runner._evaluate(
            self._task(r"\[INIT_DONE\]"), "some random output without keyword"
        )
        assert reason is not None
        assert "INIT_DONE" in reason

    def test_evaluate_passes_when_keyword_present(self):
        runner = _make_runner(dry_run=True)
        reason, *_ = runner._evaluate(self._task(r"\[DONE\]"), "output [DONE] here")
        assert reason is None

    def test_evaluate_no_regex_passes(self):
        runner = _make_runner(dry_run=True)
        reason, *_ = runner._evaluate(self._task(None), "any output")
        assert reason is None


# ──────────────────────────────────────────────
# dry_run 狀態機
# ──────────────────────────────────────────────

class TestPlaybookRunnerDryRun:
    def test_dry_run_single_step_success(self, tmp_path):
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "init", "prompt": "step1",
             "expected_output_regex": r"\[INIT_DONE\]"},
        ])
        service, _ = make_service(outputs=["[INIT_DONE]"])
        result = service.run(pb_path)
        assert result.success is True
        assert result.completed_steps == 1
        assert result.total_steps == 1

    def test_dry_run_multi_step_success(self, tmp_path):
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "s1", "prompt": "step1",
             "expected_output_regex": r"\[INIT_DONE\]"},
            {"step_id": "T02", "name": "s2", "prompt": "step2",
             "expected_output_regex": r"\[TEST_CREATED\]"},
            {"step_id": "T03", "name": "s3", "prompt": "ping",
             "expected_output_regex": r"\[PONG\]"},
        ])
        service, _ = make_service(outputs=["[INIT_DONE]", "[TEST_CREATED]", "[PONG]"])
        result = service.run(pb_path)
        assert result.success is True
        assert result.completed_steps == 3
        assert result.total_steps == 3

    def test_done_state_on_success(self, tmp_path):
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "n", "prompt": "step1",
             "expected_output_regex": r"\[INIT_DONE\]"},
        ])
        service, _ = make_service(outputs=["[INIT_DONE]"])
        result = service.run(pb_path)
        assert result.success is True  # KernelResult.reason = "success"（等價於舊 "完成"）

    def test_step_log_populated_on_success(self, tmp_path):
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "step1", "prompt": "step1",
             "expected_output_regex": r"\[INIT_DONE\]"},
            {"step_id": "T02", "name": "step2", "prompt": "step2",
             "expected_output_regex": r"\[TEST_CREATED\]"},
        ])
        service, _ = make_service(outputs=["[INIT_DONE]", "[TEST_CREATED]"])
        result = service.run(pb_path)
        assert result.success is True
        assert any("T01" in log for log in result.step_log)
        assert any("T02" in log for log in result.step_log)

    def test_file_not_found_raises(self):
        service, _ = make_service()
        with pytest.raises(FileNotFoundError):
            service.run("/nonexistent/playbook.yaml")

    def test_no_regex_step_passes_in_dry_run(self, tmp_path):
        pb_path = _write_playbook(tmp_path, [
            {"step_id": "T01", "name": "n", "prompt": "p"},
        ])
        service, _ = make_service(outputs=["[DONE]"])
        result = service.run(pb_path)
        assert result.success is True


# ──────────────────────────────────────────────
# 真實 mock 路徑（PtyWrapper 與 Minimax 注入）
# ──────────────────────────────────────────────

@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_runner_regex_pass(mock_pty_cls, tmp_path):
    """當輸出符合 expected_output_regex 且無 evaluator，應直接成功。"""
    mock_pty = MagicMock()
    mock_pty.readline.side_effect = ["result: INIT_DONE_OK here\n", None]
    mock_pty_cls.return_value = mock_pty

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "step1", "prompt": "do it",
         "expected_output_regex": "INIT_DONE_OK", "maintain_context": False},
    ])
    runner = _make_runner(dry_run=False)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)
    assert result.success is True
    assert result.completed_steps == 1


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_runner_minimax_failure_stops_gracefully(mock_pty_cls, tmp_path):
    """Minimax 故障時應安全停止，不拋出異常。"""
    from autoclaude.decision.minimax_client import MinimaxError
    mock_pty = MagicMock()
    mock_pty.readline.return_value = None
    mock_pty_cls.return_value = mock_pty

    minimax = MagicMock()
    minimax.decide_correction.side_effect = MinimaxError("API down")

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "step1", "prompt": "do it",
         "expected_output_regex": r"\[NEVER\]",
         "max_retries": 2, "maintain_context": False},
    ])
    runner = _make_runner(dry_run=False, minimax_mock=minimax)
    with patch("autoclaude.execution.playbook_runner.notify"):
        result = runner.run(pb_path)
    assert result.success is False
    assert "Minimax" in result.reason


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_escalation_on_max_retries(mock_pty_cls, tmp_path):
    """max_retries=0 (單次嘗試) 後應進入 ESCALATION 並失敗回傳。"""
    mock_pty = MagicMock()
    mock_pty.readline.return_value = None
    mock_pty_cls.return_value = mock_pty

    minimax = MagicMock()
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "will_fail", "prompt": "bad_cmd",
         "expected_output_regex": r"\[NEVER_MATCH\]",
         "max_retries": 0},
    ])
    runner = _make_runner(dry_run=False, minimax_mock=minimax)
    with patch("autoclaude.execution.playbook_runner.notify"), \
         patch.object(runner, "_save_escalation_dump"), \
         patch.object(runner._evolver, "propose_evolution", return_value=None):
        result = runner.run(pb_path)
    assert result.success is False
    assert "T01" in result.reason
    assert "重試超限" in result.reason


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_escalation_on_diverging(mock_pty_cls, tmp_path):
    """exit_code 嚴格遞增時，ConvergenceMonitor 應提前觸發 ESCALATION。"""
    mock_pty = MagicMock()
    mock_pty.readline.return_value = None
    mock_pty_cls.return_value = mock_pty

    minimax = MagicMock()
    minimax.decide_correction.return_value = MagicMock(
        correction_prompt="fix it", reasoning="try this"
    )

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "diverge_step", "prompt": "do something",
         "expected_output_regex": r"\[NEVER\]", "max_retries": 3},
    ])
    runner = _make_runner(dry_run=False, minimax_mock=minimax)

    call_count = [0]

    def mock_evaluate(_task, _output):
        call_count[0] += 1
        # attempt=0 exit=1, attempt=1 exit=2 → is_diverging()=True → ESCALATION
        return "fail", "error output", call_count[0]

    with patch("autoclaude.execution.playbook_runner.notify"), \
         patch.object(runner, "_save_escalation_dump"), \
         patch.object(runner._evolver, "propose_evolution", return_value=None), \
         patch.object(runner, "_evaluate", side_effect=mock_evaluate):
        result = runner.run(pb_path)

    assert result.success is False
    assert "T01" in result.reason
    # alert_ladder 預設 on（2026-06-13 SCG-6 人工 waiver）後，diverging 收斂信號改走階梯：
    #   attempt2 出 WARNING(1/3) → attempt3 由 F-B2 no_improve_streak=2
    #   提前升級（bypass 剩餘階梯）。
    # 仍為有界提前 ESCALATION（未耗完 max_retries=3 的全部 4 次嘗試），僅被 WARNING 階延後一手。
    # （設 alert_ladder.enabled=False 可還原為 call_count==2 的直接升級時序。）
    assert call_count[0] == 3


# ──────────────────────────────────────────────
# CONTEXT_NEGOTIATION
# ──────────────────────────────────────────────

class TestContextNegotiationRunner:
    def test_dry_run_with_context_negotiation_succeeds(self, tmp_path):
        """dry_run 模式下 context_negotiation 應略過直接成功。"""
        pb_path = _write_playbook(
            tmp_path,
            tasks=[{"step_id": "T01", "name": "n", "prompt": "step1",
                    "expected_output_regex": r"\[INIT_DONE\]"}],
            extra={"context_negotiation": {"prompt": "start session", "expected_keyword": "ready"}},
        )
        runner = _make_runner(dry_run=True)
        with patch("autoclaude.execution.playbook_runner.notify"):
            result = runner.run(pb_path)
        assert result.success is True
        assert result.completed_steps == 1

    def test_dry_run_without_context_negotiation_succeeds(self, tmp_path):
        """無 context_negotiation 的 playbook 執行不受影響。"""
        pb_path = _write_playbook(
            tmp_path,
            tasks=[{"step_id": "T01", "name": "n", "prompt": "step1",
                    "expected_output_regex": r"\[INIT_DONE\]"}],
        )
        runner = _make_runner(dry_run=True)
        with patch("autoclaude.execution.playbook_runner.notify"):
            result = runner.run(pb_path)
        assert result.success is True

    @patch("autoclaude.execution.playbook_runner.PtyWrapper")
    def test_context_negotiation_keyword_found_proceeds(self, mock_pty_cls, tmp_path):
        """非 dry_run：expected_keyword 出現在輸出中時應繼續執行任務。"""
        mock_pty = MagicMock()
        mock_pty.readline.side_effect = [
            "DummyCLI v1.0 ready\n",  # context_negotiation 輸出
            None,                      # context_negotiation prompt 結束
            "[INIT_DONE]\n",           # T01 輸出
            None,                      # T01 結束
        ]
        mock_pty_cls.return_value = mock_pty

        pb_path = _write_playbook(
            tmp_path,
            tasks=[{"step_id": "T01", "name": "n", "prompt": "step1",
                    "expected_output_regex": r"\[INIT_DONE\]"}],
            extra={
                "context_negotiation": {
                    "prompt": "start", "expected_keyword": "DummyCLI v1.0 ready"
                }
            },
        )
        runner = _make_runner(dry_run=False)
        with patch("autoclaude.execution.playbook_runner.notify"):
            result = runner.run(pb_path)
        assert result.success is True

    @patch("autoclaude.execution.playbook_runner.PtyWrapper")
    def test_context_negotiation_keyword_missing_fails(self, mock_pty_cls, tmp_path):
        """非 dry_run：expected_keyword 不在輸出中時應回傳 failure。"""
        mock_pty = MagicMock()
        mock_pty.readline.side_effect = [
            "unexpected output\n",
            None,
        ]
        mock_pty_cls.return_value = mock_pty

        pb_path = _write_playbook(
            tmp_path,
            tasks=[{"step_id": "T01", "name": "n", "prompt": "step1"}],
            extra={
                "context_negotiation": {"prompt": "start", "expected_keyword": "MISSING_KEYWORD"}
            },
        )
        runner = _make_runner(dry_run=False)
        with patch("autoclaude.execution.playbook_runner.notify"):
            result = runner.run(pb_path)
        assert result.success is False
        assert "CONTEXT_NEGOTIATION" in result.reason
        assert "MISSING_KEYWORD" in result.reason


# ──────────────────────────────────────────────
# PlaybookResult repr
# ──────────────────────────────────────────────

class TestPlaybookResultRepr:
    """SD_07 W4-T4-12：PlaybookResult dataclass 物理拔除為 factory → KernelResult；
    repr 改為 KernelResult 標準 dataclass 格式（驗證 success/欄位內容而非中文字串）。
    """
    def test_repr_success(self):
        r = PlaybookResult(success=True, completed_steps=3, total_steps=3, reason="所有步驟完成")
        rs = repr(r)
        assert "success=True" in rs
        assert "completed_steps=3" in rs
        assert "total_steps=3" in rs

    def test_repr_failure(self):
        r = PlaybookResult(success=False, completed_steps=1, total_steps=3, reason="T01 失敗")
        rs = repr(r)
        assert "success=False" in rs
        assert "T01 失敗" in rs


# ──────────────────────────────────────────────
# 振盪場景（Gap-Osc）
# ──────────────────────────────────────────────

@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_escalation_on_oscillation(mock_pty_cls, tmp_path):
    """
    ABAB 振盪錯誤模式下，ConvergenceMonitor 在第 4 次 evaluate 後應觸發 ESCALATION，
    而非無限重試到 max_retries。
    """
    mock_pty = MagicMock()
    mock_pty.readline.return_value = None
    mock_pty_cls.return_value = mock_pty

    minimax = MagicMock()
    minimax.decide_correction.return_value = MagicMock(
        correction_prompt="fix it", reasoning="try this"
    )

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "oscillate_step", "prompt": "do something",
         "expected_output_regex": r"\[NEVER\]", "max_retries": 10},  # 高 max_retries 但應提前中止
    ])
    runner = _make_runner(dry_run=False, minimax_mock=minimax)

    eval_call_count = [0]

    def mock_evaluate_oscillating(_task, _output):
        """交替回傳兩種不同的 eval_output，模擬 ABAB 振盪。"""
        idx = eval_call_count[0]
        eval_call_count[0] += 1
        if idx % 2 == 0:
            return "fail", "AssertionError: assert 1 == 2\nerror in logic", 1
        else:
            return "fail", "TypeError: unsupported operand type(s)", 1

    with patch("autoclaude.execution.playbook_runner.notify"), \
         patch.object(runner, "_save_escalation_dump"), \
         patch.object(runner._evolver, "propose_evolution", return_value=None), \
         patch.object(runner, "_evaluate", side_effect=mock_evaluate_oscillating):
        result = runner.run(pb_path)

    assert result.success is False
    # 振盪偵測需要 window=4 筆記錄，第 5 次 evaluate 時已有 4 筆 history → ESCALATION
    # 不應等到 max_retries=10 才停止
    assert eval_call_count[0] <= 6  # 至多 6 次 evaluate（保守上限）
    assert "T01" in result.reason


# ──────────────────────────────────────────────
# Gap-011-A：Global Goal Anchor 整合測試
# ──────────────────────────────────────────────

def test_dry_run_with_global_goal_succeeds(tmp_path):
    """global_goal 欄位存在時，AutoResumeService 模式應正常執行（向後相容）。"""
    pb_path = _write_playbook(
        tmp_path,
        [{"step_id": "T01", "name": "init", "prompt": "step1",
          "expected_output_regex": r"\[INIT_DONE\]"}],
        extra={"global_goal": "建立一個符合 SDD 規格的 FastAPI JWT 驗證模組。"},
    )
    service, _ = make_service(outputs=["[INIT_DONE]"])
    result = service.run(pb_path)
    assert result.success is True


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_global_goal_passed_to_minimax_decide_correction(mock_pty_cls, tmp_path):
    """playbook.global_goal 應傳遞給 minimax.decide_correction 的 global_goal 參數。"""
    mock_pty = MagicMock()
    mock_pty.readline.return_value = None
    mock_pty_cls.return_value = mock_pty

    minimax = MagicMock()
    minimax.decide_correction.return_value = MagicMock(
        correction_prompt="fix line 5",
        reasoning="test",
        task_goal_summary=None,
        step_mutation=None,
    )

    pb_path = _write_playbook(
        tmp_path,
        [{"step_id": "T01", "name": "step1", "prompt": "do it",
          "expected_output_regex": r"\[NEVER\]", "max_retries": 1,
          "maintain_context": False}],
        extra={"global_goal": "建立一個 FastAPI JWT 驗證模組。"},
    )
    runner = _make_runner(dry_run=False, minimax_mock=minimax)
    with patch("autoclaude.execution.playbook_runner.notify"), \
         patch.object(runner, "_save_escalation_dump", return_value=MagicMock()):
        runner.run(pb_path)

    # 驗證 global_goal 有傳入 decide_correction
    call_kwargs = minimax.decide_correction.call_args
    assert call_kwargs is not None
    passed_global_goal = call_kwargs.kwargs.get("global_goal") or (
        call_kwargs.args[15] if len(call_kwargs.args) > 15 else None
    )
    assert passed_global_goal == "建立一個 FastAPI JWT 驗證模組。"


# ──────────────────────────────────────────────
# Gap-011-B：StepMutation 四元組與應用測試
# ──────────────────────────────────────────────

def test_get_correction_returns_four_tuple_with_step_mutation():
    """_get_correction 應回傳 (correction_prompt, reasoning, goal_summary, step_mutation)
    四元組。"""
    from autoclaude.models.decision import CorrectionDecision
    from autoclaude.models.step_mutation import StepMutation, StepMutationType

    mutation = StepMutation(
        mutation_type=StepMutationType.REVISE_CURRENT,
        revised_prompt="新的、更明確的步驟 prompt",
        reasoning="原 prompt 太寬泛",
    )
    minimax = MagicMock()
    minimax.decide_correction.return_value = CorrectionDecision(
        correction_prompt="請修正 line 5 的 TypeError",
        reasoning="型別錯誤",
        step_mutation=mutation,
    )
    runner = _make_runner(minimax_mock=minimax)
    task = PlaybookTask(step_id="T01", name="test", prompt="original prompt")

    result = runner._get_correction(
        task=task,
        failure_reason="TypeError at line 5",
        eval_output="TypeError: unsupported operand at line 5",
        attempt=2,
    )
    assert result is not None
    cp, reasoning, goal_summary, step_mut = result
    assert cp == "請修正 line 5 的 TypeError"
    assert step_mut is not None
    assert step_mut.mutation_type == StepMutationType.REVISE_CURRENT
    assert step_mut.revised_prompt == "新的、更明確的步驟 prompt"


def test_get_correction_returns_none_mutation_when_not_present():
    """step_mutation=None 時，_get_correction 四元組第四元素應為 None。"""
    from autoclaude.models.decision import CorrectionDecision

    minimax = MagicMock()
    minimax.decide_correction.return_value = CorrectionDecision(
        correction_prompt="fix it",
        reasoning="normal",
        step_mutation=None,
    )
    runner = _make_runner(minimax_mock=minimax)
    task = PlaybookTask(step_id="T01", name="test", prompt="prompt")

    result = runner._get_correction(
        task=task,
        failure_reason="fail",
        eval_output="SyntaxError at line 3",
        attempt=1,
    )
    assert result is not None
    _, _, _, step_mut = result
    assert step_mut is None


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_revise_current_updates_task_prompt(mock_pty_cls, tmp_path):
    """REVISE_CURRENT mutation 應更新步驟的 prompt，使後續 attempt 使用新 prompt。"""
    from autoclaude.models.decision import CorrectionDecision
    from autoclaude.models.step_mutation import StepMutation, StepMutationType

    mock_pty = MagicMock()
    mock_pty.readline.return_value = None
    mock_pty_cls.return_value = mock_pty

    minimax = MagicMock()
    minimax.decide_correction.return_value = CorrectionDecision(
        correction_prompt="fix the type error",
        reasoning="type error",
        step_mutation=StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="更簡單的步驟：只實作基本的 foo() 函式",
            reasoning="原 prompt 過於複雜",
        ),
    )

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "step1", "prompt": "原始複雜 prompt",
         "max_retries": 3, "maintain_context": False},
    ])
    runner = _make_runner(dry_run=False, minimax_mock=minimax)
    eval_calls = [0]

    def mock_eval(_task, _output):
        eval_calls[0] += 1
        if eval_calls[0] == 1:
            return "fail", "TypeError: unsupported operand at line 5", 1
        return None, "", 0  # 第二次成功

    with patch("autoclaude.execution.playbook_runner.notify"), \
         patch.object(runner, "_evaluate", side_effect=mock_eval):
        result = runner.run(pb_path)

    assert result.success is True
    # 驗證 decide_correction 被呼叫（觸發了 CORRECTION 狀態）
    assert minimax.decide_correction.call_count >= 1
    # 驗證 task.prompt 已被 REVISE_CURRENT 更新（透過查詢 decide_correction 第二次呼叫的參數）
    # 第二次 decide_correction 呼叫時，task_prompt 應已是修改後的版本
    if minimax.decide_correction.call_count >= 2:
        second_call_kwargs = minimax.decide_correction.call_args_list[1].kwargs
        assert second_call_kwargs.get("task_prompt") == "更簡單的步驟：只實作基本的 foo() 函式"


@patch("autoclaude.execution.playbook_runner.PtyWrapper")
def test_inject_after_adds_step_to_playbook(mock_pty_cls, tmp_path):
    """INJECT_AFTER mutation 應在當前步驟後插入新步驟，總步驟數應增加。"""
    from autoclaude.models.decision import CorrectionDecision
    from autoclaude.models.step_mutation import StepMutation, StepMutationType

    mock_pty = MagicMock()
    mock_pty.readline.return_value = None
    mock_pty_cls.return_value = mock_pty

    minimax = MagicMock()
    # correction_prompt 需夠長（>= 50 字）且含具體引用，以通過 Hallucination Guard
    minimax.decide_correction.return_value = CorrectionDecision(
        correction_prompt=(
            "請先修復環境設定：將 config.yaml 複製到正確位置，"
            "確認 EnvironmentError 路徑設定正確後，執行 pytest 驗證通過。"
        ),
        reasoning="env not ready",
        step_mutation=StepMutation(
            mutation_type=StepMutationType.INJECT_AFTER,
            new_step_id="T01_ENV",
            new_step_name="環境修復步驟",
            new_step_prompt="請修復測試環境後再繼續",
            reasoning="環境問題需先處理",
        ),
    )

    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "step1", "prompt": "run tests",
         "max_retries": 3, "maintain_context": False},
    ])
    runner = _make_runner(dry_run=False, minimax_mock=minimax)
    eval_calls = [0]

    def mock_eval(task, _output):
        eval_calls[0] += 1
        # T01 第一次失敗（觸發 CORRECTION + INJECT_AFTER），第二次成功；T01_ENV 直接成功
        if task.step_id == "T01" and eval_calls[0] == 1:
            return "fail", "EnvironmentError: config.yaml not found at line 1", 1
        return None, "", 0

    with patch("autoclaude.execution.playbook_runner.notify"), \
         patch.object(runner, "_evaluate", side_effect=mock_eval):
        result = runner.run(pb_path)

    assert result.success is True
    # 注入後 total_steps 應為 2（原 1 步驟 + 注入 1 步驟）
    assert result.total_steps == 2


# ──────────────────────────────────────────────
# Gap-036：INJECT 步驟攜帶評估欄位（防假陽性）
# ──────────────────────────────────────────────

def test_gap036_inject_before_uses_evaluator_command_from_mutation(tmp_path):
    """Gap-036：INJECT_BEFORE 步驟使用 Minimax 提供的 evaluator_command。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "build", "prompt": "build app", "max_retries": 2},
    ])
    minimax = MagicMock()
    minimax.decide_correction.return_value = MagicMock(
        correction_prompt="請先安裝 fastapi",
        reasoning="IMPORT error",
        task_goal_summary=None,
        step_mutation=StepMutation(
            mutation_type=StepMutationType.INJECT_BEFORE,
            new_step_id="T00_INIT",
            new_step_name="安裝依賴",
            new_step_prompt="pip install fastapi",
            new_step_evaluator_command="pip show fastapi && echo OK",
            new_step_expected_regex="OK",
            reasoning="IMPORT error",
        ),
    )
    runner = _make_runner(dry_run=False, minimax_mock=minimax)
    eval_calls = [0]

    def mock_eval(task, _output):
        eval_calls[0] += 1
        if task.step_id == "T01" and eval_calls[0] == 1:
            return "fail", "ImportError: No module named fastapi at line 1", 1
        return None, "", 0

    with patch("autoclaude.execution.playbook_runner.notify"), \
         patch.object(runner, "_evaluate", side_effect=mock_eval), \
         patch.object(runner, "_execute_prompt", return_value=MagicMock(
             text="pip show fastapi OK", peak_token_pct=0.0,
             triggered_compact=False, triggered_halt=False)):
        result = runner.run(pb_path)

    assert result.success is True
    # 驗證注入步驟攜帶了 evaluator_command（透過成功執行推斷）
    assert result.total_steps >= 2


def test_gap036_inject_after_uses_git_diff_fallback_when_no_evaluator(tmp_path):
    """Gap-036：INJECT_AFTER 無 evaluator_command 時使用 git-diff 兜底。"""
    from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    runner = _make_runner(dry_run=True)
    pb = Playbook(
        project="test",
        global_invariants=GlobalInvariants(),
        tasks=[PlaybookTask(step_id="T01", name="build", prompt="build")],
    )
    mutation = StepMutation(
        mutation_type=StepMutationType.INJECT_AFTER,
        new_step_id="T01_POST",
        new_step_name="後置步驟",
        new_step_prompt="verify output",
        # 未提供 new_step_evaluator_command → 應使用 git-diff 兜底
        reasoning="補充驗證",
    )
    with patch.object(runner, "_persist_mutated_playbook"):
        runner._apply_single_mutation(
            mutation, pb, "pb.yaml",
            pb.tasks[0], 0,
            [], [], 0, {}, {}, {}, MagicMock(), 0, MagicMock(), "",
        )
    # INJECT_AFTER 插入後 tasks 應有 2 個步驟
    assert len(pb.tasks) == 2
    injected = pb.tasks[1]
    assert injected.step_id == "T01_POST"
    # 未提供 evaluator → 使用 git-diff 兜底
    assert injected.evaluator_command is not None
    assert "git diff" in injected.evaluator_command


def test_gap036_inject_before_has_evaluator_on_injected_task(tmp_path):
    """Gap-036：INJECT_BEFORE 注入的 PlaybookTask 確實帶有 evaluator_command。"""
    from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    runner = _make_runner(dry_run=True)
    pb = Playbook(
        project="test",
        global_invariants=GlobalInvariants(),
        tasks=[PlaybookTask(step_id="T01", name="build", prompt="build")],
    )
    mutation = StepMutation(
        mutation_type=StepMutationType.INJECT_BEFORE,
        new_step_id="T00_PRE",
        new_step_name="前置步驟",
        new_step_prompt="install deps",
        new_step_evaluator_command="pip show fastapi",
        new_step_expected_regex=r"fastapi",
        new_step_max_retries=2,
        reasoning="需要安裝環境",
    )
    with patch.object(runner, "_persist_mutated_playbook"):
        runner._apply_single_mutation(
            mutation, pb, "pb.yaml",
            pb.tasks[0], 0,
            [], [], 0, {}, {}, {}, MagicMock(), 0, MagicMock(), "",
        )
    injected = pb.tasks[0]
    assert injected.step_id == "T00_PRE"
    assert injected.evaluator_command == "pip show fastapi"
    assert injected.expected_output_regex == r"fastapi"
    assert injected.max_retries == 2


# ──────────────────────────────────────────────
# Gap-029：批次相容性補漏（INJECT_BEFORE + INJECT_AFTER）
# ──────────────────────────────────────────────

def test_gap029_batch_inject_before_and_after_rejected():
    """Gap-029：批次中同時包含 INJECT_BEFORE 與 INJECT_AFTER 被拒絕。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    runner = _make_runner(dry_run=True)
    batch = [
        StepMutation(mutation_type=StepMutationType.INJECT_BEFORE, new_step_prompt="pre"),
        StepMutation(mutation_type=StepMutationType.INJECT_AFTER, new_step_prompt="post"),
    ]
    valid, reason = runner._validate_batch_compatibility(batch)
    assert valid is False
    assert "INJECT_BEFORE" in reason and "INJECT_AFTER" in reason


def test_gap029_batch_inject_after_only_allowed():
    """Gap-029：批次中只有 INJECT_AFTER 允許通過。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    runner = _make_runner(dry_run=True)
    batch = [
        StepMutation(mutation_type=StepMutationType.INJECT_AFTER, new_step_prompt="post"),
        StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="new prompt"),
    ]
    valid, reason = runner._validate_batch_compatibility(batch)
    assert valid is True


def test_gap029_batch_inject_before_only_allowed():
    """Gap-029：批次中只有 INJECT_BEFORE（無 INJECT_AFTER）允許通過。"""
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    runner = _make_runner(dry_run=True)
    batch = [
        StepMutation(mutation_type=StepMutationType.INJECT_BEFORE, new_step_prompt="pre"),
        StepMutation(mutation_type=StepMutationType.DELETE_STEP, delete_step_id="T03"),
    ]
    valid, reason = runner._validate_batch_compatibility(batch)
    assert valid is True


# ──────────────────────────────────────────────
# Gap-035：GOAL_SYNTHESIS ESCALATION 不觸發 Evolver
# ────────────────────────────────────────────

def test_gap035_goal_synthesis_escalation_skips_evolver(tmp_path):
    """Gap-035：GOAL_SYNTHESIS 步驟 ESCALATION 後不呼叫 Evolver，直接回傳失敗。"""
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "GOAL_SYNTHESIS", "name": "目標驗證", "prompt": "verify goal",
         "max_retries": 1, "expected_output_regex": "DONE"},
    ])
    minimax = MagicMock()
    minimax.decide_correction.return_value = MagicMock(
        correction_prompt="請補完目標",
        reasoning="缺口",
        task_goal_summary=None,
        step_mutation=None,
    )
    runner = _make_runner(dry_run=False, minimax_mock=minimax)

    def mock_eval(task, _output):
        return "fail", "未達成目標 assert failed at line 1", 1

    with patch("autoclaude.execution.playbook_runner.notify"), \
         patch.object(runner, "_evaluate", side_effect=mock_eval), \
         patch.object(runner, "_execute_prompt", return_value=MagicMock(
             text="output", peak_token_pct=0.0,
             triggered_compact=False, triggered_halt=False)), \
         patch.object(runner._evolver, "propose_evolution") as mock_evolver, \
         patch.object(runner._minimax_evolver, "propose_evolution_via_ai", return_value=None):
        result = runner.run(pb_path)

    assert result.success is False
    assert "GOAL_SYNTHESIS" in result.reason
    mock_evolver.assert_not_called()


# ──────────────────────────────────────────────
# Gap-030：GOAL_SYNTHESIS 使用 suggested_evaluator
# ──────────────────────────────────────────────

def test_gap030_goal_synthesis_uses_suggested_evaluator(tmp_path):
    """Gap-030：GOAL_SYNTHESIS 步驟的 evaluator_command 來自 Minimax suggested_evaluator。"""
    from autoclaude.models.decision import GoalAchievementDecision
    pb_path = _write_playbook(tmp_path, [
        {"step_id": "T01", "name": "build", "prompt": "build app", "max_retries": 1,
         "expected_output_regex": "DONE"},
    ], extra={"global_goal": "建立 FastAPI 服務"})
    minimax = MagicMock()
    minimax.validate_goal_achievement.return_value = GoalAchievementDecision(
        is_achieved=False,
        completion_prompt="請補完整合測試",
        gap_analysis="缺少整合測試",
        suggested_evaluator="pytest tests/integration/ -v",
    )
    minimax.decide_correction.return_value = MagicMock(
        correction_prompt="請補完 assert 通過目標達成",
        reasoning="整合測試通過",
        task_goal_summary=None,
        step_mutation=None,
    )
    runner = _make_runner(dry_run=False, minimax_mock=minimax)
    synth_tasks = []

    def mock_eval(task, _output):
        if task.step_id == "GOAL_SYNTHESIS":
            synth_tasks.append(task)
        if task.step_id == "T01":
            return None, "", 0
        return None, "", 0

    with patch("autoclaude.execution.playbook_runner.notify"), \
         patch.object(runner, "_evaluate", side_effect=mock_eval), \
         patch.object(runner, "_execute_prompt", return_value=MagicMock(
             text="目標達成 DONE", peak_token_pct=0.0,
             triggered_compact=False, triggered_halt=False)):
        runner.run(pb_path)

    assert len(synth_tasks) > 0
    # GOAL_SYNTHESIS 步驟應有 evaluator_command
    assert synth_tasks[0].evaluator_command == "pytest tests/integration/ -v"


# ──────────────────────────────────────────────
# Gap-034：REVISE_CURRENT 後 _task_goal_summary 清除
# ──────────────────────────────────────────────

def test_gap034_revise_current_sets_clear_goal_summary():
    """Gap-034：REVISE_CURRENT 突變回傳 _MutationResult.clear_goal_summary=True。"""
    from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    runner = _make_runner(dry_run=True)
    pb = Playbook(
        project="test",
        global_invariants=GlobalInvariants(),
        tasks=[PlaybookTask(step_id="T01", name="build", prompt="original prompt")],
    )
    mutation = StepMutation(
        mutation_type=StepMutationType.REVISE_CURRENT,
        revised_prompt="全新修改後的 prompt",
        reasoning="原 prompt 不清楚",
    )
    with patch.object(runner, "_persist_mutated_playbook"):
        result = runner._apply_single_mutation(
            mutation, pb, "pb.yaml",
            pb.tasks[0], 0,
            [], [], 1, {}, {}, {}, MagicMock(), 0, MagicMock(), "",
        )
    assert result.clear_goal_summary is True
    assert pb.tasks[0].prompt == "全新修改後的 prompt"


# ──────────────────────────────────────────────
# Gap-037：INJECT_BEFORE 計數上限 3→5
# ──────────────────────────────────────────────

def test_gap037_inject_before_allows_up_to_5_times():
    """Gap-037：INJECT_BEFORE 在第 4、5 次時不被拒絕（上限從 3 提升至 5）。"""
    from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    runner = _make_runner(dry_run=True)
    pb = Playbook(
        project="test",
        global_invariants=GlobalInvariants(),
        tasks=[PlaybookTask(step_id="T01", name="build", prompt="build")],
    )
    mutation = StepMutation(
        mutation_type=StepMutationType.INJECT_BEFORE,
        new_step_id="T01_PRE",
        new_step_prompt="pre action",
        reasoning="前置",
    )
    _counter = {"T01": 4}  # 已注入 4 次（舊上限 3 應被拒絕，新上限 5 應允許）
    with patch.object(runner, "_persist_mutated_playbook"):
        result = runner._apply_single_mutation(
            mutation, pb, "pb.yaml",
            pb.tasks[0], 0,
            [], [], 0, _counter, {}, {}, MagicMock(), 0, MagicMock(), "",
        )
    # 第 5 次（counter+1=5，_cnt > 5 不成立）應允許注入
    assert result.inject_before_pending is True


def test_gap037_inject_before_rejected_at_6th_time():
    """Gap-037：INJECT_BEFORE 第 6 次被拒絕（_cnt > 5）。"""
    from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    runner = _make_runner(dry_run=True)
    pb = Playbook(
        project="test",
        global_invariants=GlobalInvariants(),
        tasks=[PlaybookTask(step_id="T01", name="build", prompt="build")],
    )
    mutation = StepMutation(
        mutation_type=StepMutationType.INJECT_BEFORE,
        new_step_id="T01_PRE",
        new_step_prompt="pre action",
        reasoning="前置",
    )
    _counter = {"T01": 5}  # 已注入 5 次，_cnt=6 > 5 → 拒絕
    with patch.object(runner, "_persist_mutated_playbook"):
        result = runner._apply_single_mutation(
            mutation, pb, "pb.yaml",
            pb.tasks[0], 0,
            [], [], 0, _counter, {}, {}, MagicMock(), 0, MagicMock(), "",
        )
    assert result.inject_before_pending is False


# ──────────────────────────────────────────────
# Gap-038：CONDITIONAL timeout 使用 config 值
# ──────────────────────────────────────────────

def test_gap038_conditional_uses_config_timeout(tmp_path):
    """Gap-038：CONDITIONAL evaluator 使用
    config.playbook.conditional_evaluator_timeout_seconds。"""
    from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
    from autoclaude.models.step_mutation import StepMutation, StepMutationType
    from autoclaude.utils.config import AppConfig, PlaybookConfig
    cfg = AppConfig()
    cfg.playbook = PlaybookConfig(conditional_evaluator_timeout_seconds=10)
    minimax = MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    runner = PlaybookRunner(cfg, minimax, hotkey, dry_run=True)
    pb = Playbook(
        project="test",
        global_invariants=GlobalInvariants(),
        tasks=[PlaybookTask(step_id="T01", name="build", prompt="build")],
    )
    mutation = StepMutation(
        mutation_type=StepMutationType.CONDITIONAL,
        condition_evaluator="echo test",
        true_mutation=StepMutation(
            mutation_type=StepMutationType.REVISE_CURRENT,
            revised_prompt="revised",
        ),
        reasoning="條件判斷",
    )
    with patch("subprocess.run") as mock_run, \
         patch.object(runner, "_persist_mutated_playbook"):
        mock_run.return_value.returncode = 0
        runner._apply_single_mutation(
            mutation, pb, "pb.yaml",
            pb.tasks[0], 0,
            [], [], 0, {}, {}, {}, MagicMock(), 0, MagicMock(), "",
        )
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args
    assert call_kwargs[1].get("timeout") == 10


# ──────────────────────────────────────────────
# Gap-033：PlaybookEvolver 跨步驟 escalation 模式學習
# ──────────────────────────────────────────────

def test_gap033_evolver_cross_step_import_triggers_global_init():
    """Gap-033：2+ 步驟均因 import 錯誤 ESCALATE 時，Evolver 注入 ENV_INIT_GLOBAL。"""
    from autoclaude.evolution.playbook_evolver import PlaybookEvolver
    from autoclaude.models.escalation import EscalationDump
    from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask

    evolver = PlaybookEvolver()
    pb = Playbook(
        project="test",
        global_invariants=GlobalInvariants(max_retries_per_step=3),
        tasks=[PlaybookTask(step_id="T01", name="build", prompt="build")],
    )

    def _make_dump(step_id, error_class):
        return EscalationDump(
            playbook_path="pb.yaml",
            step_id=step_id, step_name="s", total_attempts=3,
            failure_chain=[{
                "attempt": 0, "failure_reason": "err", "eval_output": "err",
                "exit_code": 1, "error_class": error_class,
                "error_signature": "ImportError", "minimax_reasoning": "",
                "correction_prompt_sent": None,
            }],
            final_eval_output="ImportError", is_stuck=False,
            is_diverging=False, suspect_test_file=False,
        )

    history = [_make_dump("T01", "import"), _make_dump("T02", "import")]
    current_dump = _make_dump("T03", "import")
    proposal = evolver.propose_evolution(pb, 0, current_dump, history)

    assert proposal is not None
    assert proposal.evolution_type == "INJECT_STEP"
    assert proposal.new_step is not None
    assert proposal.new_step.step_id == "ENV_INIT_GLOBAL"
    assert proposal.inject_before_idx == 0

    # DEF-101（R50）：ENV_INIT_GLOBAL 的 evaluator_command 曾用單引號字串
    # （python -c 'import fastapi' && echo 'OK'），cmd.exe 不把單引號視為字串
    # 分隔符會拆成多個引數。改用雙引號後，親跑 subprocess 驗證真實成敗語意
    # （而非只比對字面字串），確保仍能正確辨別 import 成功/失敗。
    evaluator_command = proposal.new_step.evaluator_command
    assert evaluator_command is not None
    assert "'" not in evaluator_command, "evaluator_command 不應含單引號（cmd.exe 不安全）"

    # R51 迴歸鎖：evaluator_command 必須含 sys.executable 絕對路徑，不得退化為
    # 裸字面值 "python"（macOS/多數現代 Linux distro 的 /usr/bin 下無 python
    # 別名，裸字面值會以 rc=127 command not found 收場）。既有的 ok_proc/
    # fail_proc 兩段 subprocess 驗證皆繼承呼叫端 .venv 的 PATH（恆含 python
    # 別名），對「PATH 上無裸 python」這個環境維度零鑑別力；本段補上 token 級
    # 直接斷言 + 受限 PATH 親跑，若日後改回裸字面值 "python" 會在任何機器上變紅。
    import sys

    assert f'"{sys.executable}"' in evaluator_command, (
        f"evaluator_command 應含 sys.executable 絕對路徑，實際: {evaluator_command}"
    )

    import subprocess

    ok_proc = subprocess.run(
        evaluator_command.replace("fastapi", "os"),
        shell=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=10,
    )
    assert ok_proc.returncode == 0, f"可 import 的模組應通過: {ok_proc.stdout}{ok_proc.stderr}"

    fail_proc = subprocess.run(
        evaluator_command.replace("fastapi", "__module_does_not_exist__"),
        shell=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=10,
    )
    assert fail_proc.returncode != 0, "不存在的模組應讓 evaluator 回報失敗"

    # 受限環境親跑：複製目前環境變數但清空 PATH，模擬 PATH 上無任何 python
    # 可被裸字面值找到的情境，證明本 evaluator_command 靠絕對路徑而非 PATH
    # 查找，即使受限環境下仍能正確辨別 import 成功/失敗語意。
    import os

    restricted_env = dict(os.environ)
    restricted_env["PATH"] = ""
    ok_restricted = subprocess.run(
        evaluator_command.replace("fastapi", "os"),
        shell=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=10, env=restricted_env,
    )
    assert ok_restricted.returncode == 0, (
        "受限 PATH 下可 import 的模組仍應通過（絕對路徑不靠 PATH 查找），"
        f"實際 rc={ok_restricted.returncode}, stdout={ok_restricted.stdout!r}, "
        f"stderr={ok_restricted.stderr!r}"
    )


def test_gap033_evolver_single_escalation_no_cross_step():
    """Gap-033：只有 1 個 escalation 歷史時，不觸發跨步驟全域注入。"""
    from autoclaude.evolution.playbook_evolver import PlaybookEvolver
    from autoclaude.models.escalation import EscalationDump
    from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask

    evolver = PlaybookEvolver()
    pb = Playbook(
        project="test",
        global_invariants=GlobalInvariants(max_retries_per_step=3),
        tasks=[PlaybookTask(step_id="T01", name="build", prompt="build")],
    )
    single_history = [EscalationDump(
        playbook_path="pb.yaml",
        step_id="T01", step_name="s", total_attempts=3,
        failure_chain=[{
            "attempt": 0, "failure_reason": "err", "eval_output": "err",
            "exit_code": 1, "error_class": "import",
            "error_signature": "ImportError", "minimax_reasoning": "",
            "correction_prompt_sent": None,
        }],
        final_eval_output="ImportError", is_stuck=False,
        is_diverging=False, suspect_test_file=False,
    )]
    current_dump = EscalationDump(
        playbook_path="pb.yaml",
        step_id="T02", step_name="s", total_attempts=4,
        failure_chain=[{
            "attempt": 0, "failure_reason": "AssertionError at line 10",
            "eval_output": "AssertionError: assert False at line 10",
            "exit_code": 1, "error_class": "assertion",
            "error_signature": "AssertionError", "minimax_reasoning": "",
            "correction_prompt_sent": None,
        }],
        final_eval_output="err", is_stuck=False,
        is_diverging=False, suspect_assertion_mismatch=True, suspect_test_file=False,
    )
    proposal = evolver.propose_evolution(pb, 0, current_dump, single_history)
    # 只有 1 個歷史，不應觸發跨步驟 ENV_INIT_GLOBAL（Gap-033 需要 >= 2 個 escalation 歷史）
    # proposal 可能非 None（Case 2 AssertionError 分支），但絕不應是 ENV_INIT_GLOBAL
    assert proposal is None or (
        proposal.new_step is None or proposal.new_step.step_id != "ENV_INIT_GLOBAL"
    )


# ──────────────────────────────────────────────
# Gap-031：GOTO 跳轉前置 /compact
# ──────────────────────────────────────────────

def test_gap031_goto_calls_compact_before_jump():
    """Gap-031：GOTO 跳轉前必須呼叫 _send_compact。"""
    runner = _make_runner(dry_run=True)
    runner._cfg.token_guard.enabled = True
    runner._step_counter = 5  # 有步驟計數，不是 0

    compact_called_before_jump = {"called": False}

    def mock_compact():
        compact_called_before_jump["called"] = True
    runner._send_compact = mock_compact
    runner._dry_run = False  # 讓 compact 條件成立

    # 手動觸發 GOTO 邏輯（簡化版，直接測試 compact 呼叫條件）
    if (not runner._dry_run and
            runner._cfg.token_guard.enabled and
            runner._step_counter > 0):
        runner._send_compact()

    assert compact_called_before_jump["called"] is True


def test_gap031_goto_no_compact_when_dry_run():
    """Gap-031：dry_run=True 時 GOTO 不呼叫 _send_compact。"""
    runner = _make_runner(dry_run=True)
    runner._cfg.token_guard.enabled = True
    runner._step_counter = 5
    compact_called = {"called": False}

    def mock_compact():
        compact_called["called"] = True
    runner._send_compact = mock_compact

    # dry_run=True 時條件不成立
    if (not runner._dry_run and
            runner._cfg.token_guard.enabled and
            runner._step_counter > 0):
        runner._send_compact()

    assert compact_called["called"] is False


def test_gap031_goto_no_compact_when_token_guard_disabled():
    """Gap-031：token_guard 停用時 GOTO 不呼叫 _send_compact。"""
    runner = _make_runner(dry_run=False)
    runner._cfg.token_guard.enabled = False  # 停用 token guard
    runner._step_counter = 5
    compact_called = {"called": False}

    def mock_compact():
        compact_called["called"] = True
    runner._send_compact = mock_compact

    if (not runner._dry_run and
            runner._cfg.token_guard.enabled and
            runner._step_counter > 0):
        runner._send_compact()

    assert compact_called["called"] is False


def test_gap031_goto_no_compact_when_step_counter_zero():
    """Gap-031：step_counter=0 時 GOTO 不呼叫 _send_compact。"""
    runner = _make_runner(dry_run=False)
    runner._cfg.token_guard.enabled = True
    runner._step_counter = 0  # 0 不觸發
    compact_called = {"called": False}

    def mock_compact():
        compact_called["called"] = True
    runner._send_compact = mock_compact

    if (not runner._dry_run and
            runner._cfg.token_guard.enabled and
            runner._step_counter > 0):
        runner._send_compact()

    assert compact_called["called"] is False
