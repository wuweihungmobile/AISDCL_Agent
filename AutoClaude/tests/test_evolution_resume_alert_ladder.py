"""P1-1 接線測試：escalation 觸發演化時，alert_ladder 必須隨 evolution-resume
checkpoint 一同持久化（Improving_012 Phase 2 / ADR-AGT-004，凍結 SRD §1.4
「三條 additive 存檔路徑含 evolution」）。

測試意圖（Rule 9）：
  SRD §1.4 要求 evolution-resume 為三條存檔路徑之一，必須帶上 alert_ladder
  快照，否則演化重啟後階梯/streak 計數歸零 → 緩階次數可被演化重置而無限延長，
  破壞有界性。本測試直接斷言三條 escalation 路徑呼叫
  save_evolution_resume_checkpoint 時收到的 alert_ladder == 傳入快照；
  若任一函式漏接 alert_ladder（回歸）→ 攔截到的 kwarg 為 None/{} → 測試失敗。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.execution.error_classifier import ErrorClass
from autoclaude.execution.failure_tracker import FailureTracker
from autoclaude.execution.steps_orchestrator._escalation_handler import (
    handle_convergence_escalation,
    handle_max_retries_escalation,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask

_LADDER_SNAP = {"T01": {"warning": 1, "hint": 1, "no_improve_streak": 2}}


def _make_runner() -> MagicMock:
    """mock runner：演化鏈成功（propose→apply 回傳路徑），save 回傳 True。"""
    runner = MagicMock()  # record_escalation 等內部呼叫由 MagicMock 自動承接
    runner._save_escalation_dump = MagicMock(return_value=MagicMock())
    runner._escalation_history = []
    # MinimaxEvolver 無提議 → 回退規則引擎；規則引擎給 proposal
    runner._minimax_evolver.propose_evolution_via_ai = MagicMock(return_value=None)
    runner._evolver.propose_evolution = MagicMock(return_value=MagicMock(reasoning="r"))
    runner._evolver.apply_evolution = MagicMock(return_value="evolved.yaml")
    runner._checkpoint_plugin.save_evolution_resume_checkpoint = MagicMock(
        return_value=True
    )
    runner._notify = MagicMock()
    return runner


def _make_tracker() -> FailureTracker:
    t = FailureTracker("T01")
    t.record(0, "fail", "AssertionError: x", 1, "", error_class="assertion")
    return t


def _playbook() -> Playbook:
    return Playbook(
        version="1.0", project="P",
        global_invariants=GlobalInvariants(max_retries_per_step=2),
        tasks=[PlaybookTask(step_id="T01", name="t", prompt="p")],
    )


def _common_kwargs(runner):
    return dict(
        runner=runner, playbook=_playbook(), playbook_path="pb.yaml",
        task=_playbook().tasks[0], step_idx=0, tracker=_make_tracker(),
        eval_output="AssertionError: x", error_cls=ErrorClass.ASSERTION,
        step_log=[], workflow="auto", total=1, mutation_log=[],
        completed_step_ids=set(), step_evolution_counter={},
    )


def test_convergence_escalation_passes_alert_ladder_to_evolution_checkpoint():
    runner = _make_runner()
    handle_convergence_escalation(
        convergence_trend="stuck", convergence_reasoning="無法收斂",
        alert_ladder=_LADDER_SNAP, **_common_kwargs(runner),
    )
    save = runner._checkpoint_plugin.save_evolution_resume_checkpoint
    assert save.called
    assert save.call_args.kwargs["alert_ladder"] == _LADDER_SNAP


def test_max_retries_escalation_passes_alert_ladder_to_evolution_checkpoint():
    runner = _make_runner()
    handle_max_retries_escalation(
        max_retries=2, failure_reason="fail",
        alert_ladder=_LADDER_SNAP, **_common_kwargs(runner),
    )
    save = runner._checkpoint_plugin.save_evolution_resume_checkpoint
    assert save.called
    assert save.call_args.kwargs["alert_ladder"] == _LADDER_SNAP


def test_default_none_keeps_backward_compatibility():
    """未傳 alert_ladder（向下相容）時 save 收到 None，不報錯。"""
    runner = _make_runner()
    handle_convergence_escalation(
        convergence_trend="stuck", convergence_reasoning="x",
        **_common_kwargs(runner),
    )
    save = runner._checkpoint_plugin.save_evolution_resume_checkpoint
    assert save.call_args.kwargs["alert_ladder"] is None
