"""SD_Improving_05 W0 三方審查 SA-C1：MergedResult 7 個新欄位 round-trip 測試。

驗證 DefaultResolutionPolicy.merge() 對 6 個新 IHookResult 的合併行為：
  - ScheduleResumeResult → scheduled_resume_at
  - CounterSnapshotResult → counter_diff（含衝突偵測 Arch-M1）
  - PersistenceResult → persistence_paths / evolved_playbook_path / escalation_dump_path（依 kind）
  - MutationApplyResult → evolution_metadata.clear_goal_summary
  - GoalValidationResult → goal_achieved + evolution_metadata.goal_reasoning
  - EscalationDumpedResult → escalation_dump_path

並驗證既有 4 條決定性規則（VetoResult 短路 / PromptInjectionResult 串接 /
ResourceRequest or 邏輯 / MutationProposal 取第一個）未被破壞。
"""
from __future__ import annotations

import pytest

from autoclaude.core.event_bus import DefaultResolutionPolicy, MergedResult
from autoclaude.core.hookspec import (
    CounterSnapshotResult,
    EscalationDumpedResult,
    GoalValidationResult,
    HookContractViolation,
    KernelPhase,
    MutationApplyResult,
    PersistenceResult,
    ScheduleResumeResult,
)


def _merge(phase: KernelPhase, results: list) -> MergedResult:
    return DefaultResolutionPolicy().merge(phase, results)


class TestScheduleResumeResult:
    def test_single_contributor_sets_scheduled_resume_at(self):
        r = ScheduleResumeResult(contributor="auto_resume", scheduled_at="2026-05-16T10:00:00Z")
        merged = _merge(KernelPhase.ON_AUTO_RESUME_WAKE, [r])
        assert merged.scheduled_resume_at == "2026-05-16T10:00:00Z"

    def test_multiple_contributors_first_wins(self):
        r1 = ScheduleResumeResult(contributor="auto_resume", scheduled_at="2026-05-16T10:00:00Z")
        r2 = ScheduleResumeResult(contributor="evolution", scheduled_at="2026-05-17T10:00:00Z")
        merged = _merge(KernelPhase.ON_AUTO_RESUME_WAKE, [r1, r2])
        assert merged.scheduled_resume_at == "2026-05-16T10:00:00Z"

    def test_empty_results_returns_none(self):
        merged = _merge(KernelPhase.ON_AUTO_RESUME_WAKE, [])
        assert merged.scheduled_resume_at is None


class TestCounterSnapshotResult:
    def test_single_contributor_writes_counter_diff(self):
        r = CounterSnapshotResult(
            contributor="goto_counter",
            snapshot={"goto": {"T01": 2}, "inject_before": {}},
        )
        merged = _merge(KernelPhase.ON_CHECKPOINT_SAVE_REQUEST, [r])
        assert merged.counter_diff["goto"] == {"T01": 2}
        assert merged.counter_diff["inject_before"] == {}

    def test_disjoint_keys_merge_successfully(self):
        r1 = CounterSnapshotResult(contributor="goto_counter", snapshot={"goto": {"T01": 2}})
        r2 = CounterSnapshotResult(contributor="token_guard", snapshot={"compact_failure": 0})
        merged = _merge(KernelPhase.ON_CHECKPOINT_SAVE_REQUEST, [r1, r2])
        assert merged.counter_diff["goto"] == {"T01": 2}
        assert merged.counter_diff["compact_failure"] == 0

    def test_conflicting_keys_raise_hook_contract_violation(self):
        """Arch-M1 / SD-M6：多 plugin 對同 key 寫不同值必須 fail-fast。"""
        r1 = CounterSnapshotResult(contributor="goto_counter", snapshot={"goto": {"T01": 2}})
        r2 = CounterSnapshotResult(contributor="evolution", snapshot={"goto": {"T01": 5}})
        with pytest.raises(HookContractViolation, match="multi plugin|key.*goto"):
            _merge(KernelPhase.ON_CHECKPOINT_SAVE_REQUEST, [r1, r2])

    def test_same_value_from_multiple_contributors_not_conflict(self):
        """同值不算衝突（idempotent emit）。"""
        r1 = CounterSnapshotResult(contributor="a", snapshot={"k": 1})
        r2 = CounterSnapshotResult(contributor="b", snapshot={"k": 1})
        merged = _merge(KernelPhase.ON_CHECKPOINT_SAVE_REQUEST, [r1, r2])
        assert merged.counter_diff["k"] == 1


class TestPersistenceResultKind:
    def test_checkpoint_kind_does_not_set_evolved_path(self):
        r = PersistenceResult(
            contributor="checkpoint", path="/tmp/ck.yaml",
            succeeded=True, kind="checkpoint",
        )
        merged = _merge(KernelPhase.ON_PERSISTENCE_REQUEST, [r])
        assert "/tmp/ck.yaml" in merged.persistence_paths
        assert merged.evolved_playbook_path is None
        assert merged.escalation_dump_path is None

    def test_evolved_playbook_kind_sets_evolved_path(self):
        """Arch-C2 / SD-C4：依 kind 而非 endswith 字串嗅探。"""
        r = PersistenceResult(
            contributor="playbook_persistence", path="/tmp/evolved.yaml",
            succeeded=True, kind="evolved_playbook",
        )
        merged = _merge(KernelPhase.ON_EVOLUTION_APPLY, [r])
        assert merged.evolved_playbook_path == "/tmp/evolved.yaml"

    def test_escalation_dump_kind_sets_escalation_path(self):
        r = PersistenceResult(
            contributor="evolution", path="/tmp/dump.json",
            succeeded=True, kind="escalation_dump",
        )
        merged = _merge(KernelPhase.ON_ESCALATION_DUMP_REQUEST, [r])
        assert merged.escalation_dump_path == "/tmp/dump.json"

    def test_failed_persistence_not_appended(self):
        r = PersistenceResult(
            contributor="checkpoint", path="/tmp/x", succeeded=False, kind="checkpoint",
        )
        merged = _merge(KernelPhase.ON_PERSISTENCE_REQUEST, [r])
        assert "/tmp/x" not in merged.persistence_paths


class TestMutationApplyResult:
    def test_clear_goal_summary_flag_propagates(self):
        r = MutationApplyResult(contributor="mutation_service", clear_goal_summary=True)
        merged = _merge(KernelPhase.ON_EVOLUTION_APPLY, [r])
        assert merged.evolution_metadata.get("clear_goal_summary") is True


class TestGoalValidationResult:
    def test_achieved_propagates(self):
        r = GoalValidationResult(
            contributor="goal_synthesis", achieved=True, reasoning="all tests pass",
        )
        merged = _merge(KernelPhase.ON_SUCCESS, [r])
        assert merged.goal_achieved is True
        assert merged.evolution_metadata.get("goal_reasoning") == "all tests pass"

    def test_not_achieved(self):
        r = GoalValidationResult(contributor="goal_synthesis", achieved=False, reasoning="")
        merged = _merge(KernelPhase.ON_SUCCESS, [r])
        assert merged.goal_achieved is False


class TestEscalationDumpedResult:
    def test_dump_path_propagates(self):
        r = EscalationDumpedResult(contributor="evolution", dump_path="/tmp/esc.json")
        merged = _merge(KernelPhase.ON_ESCALATION_DUMP_REQUEST, [r])
        assert merged.escalation_dump_path == "/tmp/esc.json"


class TestBackwardCompatibilityNotBroken:
    """既有 4 條決定性規則（v1.1）未被破壞驗證。"""

    def test_veto_short_circuits_with_reasons(self):
        from autoclaude.core.hookspec import VetoResult
        r1 = VetoResult(contributor="hotkey", reason="ESC")
        r2 = VetoResult(contributor="validator", reason="bad")
        merged = _merge(KernelPhase.PRE_RUN, [r1, r2])
        assert merged.veto is True
        assert len(merged.veto_reasons) == 2

    def test_prompt_injection_concat_in_order(self):
        from autoclaude.core.hookspec import PromptInjectionResult
        r1 = PromptInjectionResult(contributor="a", prefix="GOAL:\n")
        r2 = PromptInjectionResult(contributor="b", prefix="HINT:\n")
        merged = _merge(KernelPhase.PRE_ATTEMPT, [r1, r2])
        assert "GOAL:" in merged.accumulated_prefix
        assert "HINT:" in merged.accumulated_prefix

    def test_resource_request_or_logic(self):
        from autoclaude.core.hookspec import ResourceRequest
        r1 = ResourceRequest(contributor="token_guard", request_compact=True)
        r2 = ResourceRequest(contributor="other", request_halt=True)
        merged = _merge(KernelPhase.ON_TOKEN_USAGE, [r1, r2])
        assert merged.request_compact is True
        assert merged.request_halt is True

    def test_mutation_proposal_first_wins(self):
        from autoclaude.core.hookspec import MutationProposal
        from autoclaude.models.step_mutation import StepMutation, StepMutationType
        m1 = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="p1")
        m2 = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="p2")
        r1 = MutationProposal(contributor="a", mutation=m1)
        r2 = MutationProposal(contributor="b", mutation=m2)
        merged = _merge(KernelPhase.POST_ATTEMPT, [r1, r2])
        assert merged.request_mutation is m1
