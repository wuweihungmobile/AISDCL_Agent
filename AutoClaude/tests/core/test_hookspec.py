"""hookspec.py 單元測試（Phase 2 + SD_Improving_05 W0 T0-1 擴張）。

驗證：
  - KernelPhase 27 個 phase 完整（19 原始 + 8 新增 by SD_05 W0）
  - HookContext 為 frozen dataclass
  - 10 個 IHookResult 都是 frozen dataclass，欄位正確（4 原始 + 6 新增 by SD_05 W0）
  - PHASE_RESULT_CONTRACT 涵蓋核心 + 觀察 + 新 phase（補 7 + 8 = 15 條 by SD_05 W0）
  - HookContractViolation 可拋
"""
from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from autoclaude.core.hookspec import (
    CounterSnapshotResult,
    EscalationDumpedResult,
    GoalValidationResult,
    HookContext,
    HookContractViolation,
    KernelPhase,
    MutationApplyResult,
    MutationProposal,
    PHASE_RESULT_CONTRACT,
    PersistenceResult,
    PromptInjectionResult,
    ResourceRequest,
    ScheduleResumeResult,
    VetoResult,
)
from autoclaude.models.playbook import Playbook, GlobalInvariants


def _make_playbook() -> Playbook:
    return Playbook(version="1.0", project="test",
                    global_invariants=GlobalInvariants(), tasks=[])


class TestKernelPhase:
    def test_has_34_phases(self):
        # 17 原始 + 2 個 W4-T17/M-11（ON_CHECKPOINT_RESTORE/SAVE_REQUEST）
        # + 8 個 SD_05 W0 T0-1 新增（PRE/POST_COMPACT, ON_PERSISTENCE_REQUEST,
        #   ON_ESCALATION_DUMP_REQUEST, ON_EVOLUTION_PROPOSE/APPLY,
        #   ON_AUTO_RESUME_WAKE, ON_PROMPT_PREPARED）
        # + 7 個 SD_06 W1 T1-4 新增（BEFORE_DECIDE, DECIDE, BEFORE_EXEC, EXEC,
        #   ON_EVENT, AFTER_EXEC, ON_INTERRUPT_REQUEST — Coordinator 6 phase 序）
        assert len(KernelPhase) == 34

    def test_pre_run_value(self):
        assert KernelPhase.PRE_RUN.value == "pre_run"

    def test_on_token_usage_value(self):
        assert KernelPhase.ON_TOKEN_USAGE.value == "on_token_usage"

    def test_on_evolution_value(self):
        assert KernelPhase.ON_EVOLUTION.value == "on_evolution"

    def test_w4_t17_checkpoint_phases(self):
        # W4-T17 / M-11：CheckpointPlugin <-> GotoCounterPlugin 解耦事件
        assert KernelPhase.ON_CHECKPOINT_RESTORE.value == "on_checkpoint_restore"
        assert KernelPhase.ON_CHECKPOINT_SAVE_REQUEST.value == "on_checkpoint_save_request"

    def test_sd05_w0_new_phases(self):
        # SD_Improving_05 W0 T0-1：新增 8 phase（支撐 W1~W4 mixin 下沉）
        assert KernelPhase.PRE_COMPACT.value == "pre_compact"
        assert KernelPhase.POST_COMPACT.value == "post_compact"
        assert KernelPhase.ON_PERSISTENCE_REQUEST.value == "on_persistence_request"
        assert KernelPhase.ON_ESCALATION_DUMP_REQUEST.value == "on_escalation_dump_request"
        assert KernelPhase.ON_EVOLUTION_PROPOSE.value == "on_evolution_propose"
        assert KernelPhase.ON_EVOLUTION_APPLY.value == "on_evolution_apply"
        assert KernelPhase.ON_AUTO_RESUME_WAKE.value == "on_auto_resume_wake"
        assert KernelPhase.ON_PROMPT_PREPARED.value == "on_prompt_prepared"


class TestHookContext:
    def test_is_frozen_dataclass(self):
        assert is_dataclass(HookContext)
        ctx = HookContext(phase=KernelPhase.PRE_RUN, playbook=_make_playbook())
        with pytest.raises((AttributeError, Exception)):
            ctx.phase = KernelPhase.POST_RUN  # type: ignore[misc]

    def test_default_payload_is_empty_dict(self):
        ctx = HookContext(phase=KernelPhase.PRE_RUN, playbook=_make_playbook())
        assert ctx.payload == {}

    def test_optional_fields_default_none(self):
        ctx = HookContext(phase=KernelPhase.PRE_RUN, playbook=_make_playbook())
        assert ctx.task is None
        assert ctx.step_idx is None
        assert ctx.attempt is None


class TestVetoResult:
    def test_is_frozen(self):
        assert is_dataclass(VetoResult)
        v = VetoResult(contributor="x", reason="bad")
        with pytest.raises((AttributeError, Exception)):
            v.reason = "modified"  # type: ignore[misc]

    def test_fields(self):
        v = VetoResult(contributor="hotkey", reason="ESC pressed")
        assert v.contributor == "hotkey"
        assert v.reason == "ESC pressed"


class TestPromptInjectionResult:
    def test_default_position_top(self):
        p = PromptInjectionResult(contributor="goal", prefix="GOAL:")
        assert p.position == "top"

    def test_custom_position(self):
        p = PromptInjectionResult(contributor="g", prefix="X", position="before_anchor")
        assert p.position == "before_anchor"


class TestResourceRequest:
    def test_default_all_false(self):
        r = ResourceRequest(contributor="x")
        assert r.request_compact is False
        assert r.request_halt is False
        assert r.request_escalation is False

    def test_can_set_each_flag(self):
        r = ResourceRequest(contributor="tg", request_compact=True, reason="80%")
        assert r.request_compact is True
        assert r.reason == "80%"


class TestMutationProposal:
    def test_holds_mutation(self):
        from autoclaude.models.step_mutation import StepMutation, StepMutationType
        m = StepMutation(mutation_type=StepMutationType.NO_OP if hasattr(StepMutationType, "NO_OP")
                         else StepMutationType.REVISE_CURRENT,
                         revised_prompt="x")
        proposal = MutationProposal(contributor="evo", mutation=m, rationale="r")
        assert proposal.mutation is m
        assert proposal.rationale == "r"


class TestPhaseResultContract:
    def test_pre_run_only_veto(self):
        assert PHASE_RESULT_CONTRACT[KernelPhase.PRE_RUN] == {VetoResult}

    def test_post_attempt_includes_resource_and_mutation(self):
        allowed = PHASE_RESULT_CONTRACT[KernelPhase.POST_ATTEMPT]
        assert ResourceRequest in allowed
        assert MutationProposal in allowed

    def test_on_token_usage_only_resource_request(self):
        assert PHASE_RESULT_CONTRACT[KernelPhase.ON_TOKEN_USAGE] == {ResourceRequest}

    def test_sd05_w0_observer_phases_have_contract(self):
        # SD_Improving_05 W0 T0-1：ON_FAILURE / ON_SUCCESS / ON_INTERRUPT /
        # ON_EVOLUTION / ON_STATE_TRANSITION 補入 PHASE_RESULT_CONTRACT
        assert KernelPhase.ON_FAILURE in PHASE_RESULT_CONTRACT
        assert KernelPhase.ON_SUCCESS in PHASE_RESULT_CONTRACT
        assert KernelPhase.ON_INTERRUPT in PHASE_RESULT_CONTRACT
        assert KernelPhase.ON_EVOLUTION in PHASE_RESULT_CONTRACT
        assert KernelPhase.ON_STATE_TRANSITION in PHASE_RESULT_CONTRACT
        assert KernelPhase.ON_CHECKPOINT_RESTORE in PHASE_RESULT_CONTRACT
        assert KernelPhase.ON_CHECKPOINT_SAVE_REQUEST in PHASE_RESULT_CONTRACT

    def test_sd05_w0_new_phase_contracts(self):
        # SD_Improving_05 W0 T0-1：8 個新 phase 對應契約
        assert ScheduleResumeResult in PHASE_RESULT_CONTRACT[KernelPhase.ON_AUTO_RESUME_WAKE]
        assert CounterSnapshotResult in PHASE_RESULT_CONTRACT[KernelPhase.ON_CHECKPOINT_SAVE_REQUEST]
        assert PersistenceResult in PHASE_RESULT_CONTRACT[KernelPhase.ON_PERSISTENCE_REQUEST]
        assert MutationApplyResult in PHASE_RESULT_CONTRACT[KernelPhase.ON_EVOLUTION_APPLY]
        assert MutationProposal in PHASE_RESULT_CONTRACT[KernelPhase.ON_EVOLUTION_PROPOSE]
        assert EscalationDumpedResult in PHASE_RESULT_CONTRACT[KernelPhase.ON_ESCALATION_DUMP_REQUEST]
        assert GoalValidationResult in PHASE_RESULT_CONTRACT[KernelPhase.ON_SUCCESS]


class TestSD05NewResults:
    """SD_Improving_05 W0 T0-1：6 個新 IHookResult 驗證。"""

    def test_schedule_resume_result(self):
        r = ScheduleResumeResult(contributor="auto_resume", scheduled_at="2026-05-16T10:00:00Z")
        assert is_dataclass(r)
        assert r.scheduled_at == "2026-05-16T10:00:00Z"
        with pytest.raises((AttributeError, Exception)):
            r.scheduled_at = "x"  # type: ignore[misc]

    def test_counter_snapshot_result(self):
        snap = {"goto": {"T01": 2}, "inject_before": {}, "skip_to": {}, "step_evolution": {}}
        r = CounterSnapshotResult(contributor="goto_counter", snapshot=snap)
        assert r.snapshot["goto"]["T01"] == 2

    def test_persistence_result(self):
        r = PersistenceResult(contributor="checkpoint", path="/tmp/x.yaml", succeeded=True)
        assert r.succeeded is True
        assert r.path == "/tmp/x.yaml"

    def test_mutation_apply_result_default(self):
        r = MutationApplyResult(contributor="mutation_service")
        assert r.clear_goal_summary is False

    def test_goal_validation_result(self):
        r = GoalValidationResult(contributor="goal_synthesis", achieved=True, reasoning="all tests pass")
        assert r.achieved is True
        assert r.reasoning == "all tests pass"

    def test_escalation_dumped_result(self):
        r = EscalationDumpedResult(contributor="evolution", dump_path="/tmp/escalation_T03.json")
        assert r.dump_path.endswith(".json")


class TestHookContractViolation:
    def test_is_exception(self):
        assert issubclass(HookContractViolation, Exception)

    def test_can_raise(self):
        with pytest.raises(HookContractViolation):
            raise HookContractViolation("test")
