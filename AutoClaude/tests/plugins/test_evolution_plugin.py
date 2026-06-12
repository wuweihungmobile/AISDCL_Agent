"""EvolutionPlugin 單元測試（Phase 3 / W10 #11，≥ 12 cases）。"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase, MutationProposal
from autoclaude.evolution.playbook_evolver import PlaybookEvolutionProposal
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.models.step_mutation import StepMutationType
from autoclaude.plugins import EvolutionPlugin


def _pb() -> Playbook:
    return Playbook(
        version="1.0", project="P",
        global_invariants=GlobalInvariants(),
        tasks=[PlaybookTask(step_id="T01", name="n", prompt="p")],
    )


def _inject_proposal() -> PlaybookEvolutionProposal:
    return PlaybookEvolutionProposal(
        evolution_type="INJECT_STEP",
        inject_before_idx=0,
        reasoning="missing env setup",
        new_step=PlaybookTask(
            step_id="T_PRE", name="pre", prompt="install deps",
            evaluator_command="echo ok",
            expected_output_regex=r"\[OK\]",
        ),
    )


def _split_proposal() -> PlaybookEvolutionProposal:
    return PlaybookEvolutionProposal(
        evolution_type="SPLIT_STEP",
        inject_before_idx=0,
        reasoning="too complex",
        split_steps=[
            PlaybookTask(step_id="T01a", name="part-1", prompt="p1"),
            PlaybookTask(step_id="T01b", name="part-2", prompt="p2"),
        ],
    )


class TestEvolutionPluginBasics:
    def test_name(self):
        assert EvolutionPlugin().name() == "evolution"

    def test_priority_is_70(self):
        assert EvolutionPlugin().priority() == 70

    def test_subscribed_phases(self):
        """SD_05 W3-3：EvolutionPlugin 由 1 phase 擴至 4 phase。"""
        assert EvolutionPlugin().subscribed_phases() == [
            KernelPhase.ON_ESCALATION,
            KernelPhase.ON_EVOLUTION_PROPOSE,
            KernelPhase.ON_EVOLUTION_APPLY,
            KernelPhase.ON_ESCALATION_DUMP_REQUEST,
        ]


class TestEvolutionPluginNoEscalationDump:
    def test_no_dump_returns_none(self):
        plugin = EvolutionPlugin()
        ctx = HookContext(phase=KernelPhase.ON_ESCALATION, playbook=_pb())
        assert plugin.on_event(ctx) is None


class TestEvolutionPluginAiPath:
    def test_ai_proposal_used_when_succeeds(self):
        ai = MagicMock()
        ai.propose_evolution_via_ai.return_value = _inject_proposal()
        rule = MagicMock()
        plugin = EvolutionPlugin(rule_evolver=rule, ai_evolver=ai,
                                 minimax_client=MagicMock())
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(),
            payload={"escalation_dump": MagicMock(), "failed_step_idx": 0},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, MutationProposal)
        assert result.mutation.mutation_type == StepMutationType.INJECT_BEFORE
        # AI 成功 → 不應呼叫 rule
        rule.propose_evolution.assert_not_called()


class TestEvolutionPluginFallbackToRule:
    def test_rule_used_when_ai_returns_none(self):
        ai = MagicMock()
        ai.propose_evolution_via_ai.return_value = None
        rule = MagicMock()
        rule.propose_evolution.return_value = _inject_proposal()
        plugin = EvolutionPlugin(rule_evolver=rule, ai_evolver=ai,
                                 minimax_client=MagicMock())
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(),
            payload={"escalation_dump": MagicMock(), "failed_step_idx": 0},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, MutationProposal)
        assert rule.propose_evolution.called

    def test_rule_used_when_no_minimax_client(self):
        rule = MagicMock()
        rule.propose_evolution.return_value = _inject_proposal()
        plugin = EvolutionPlugin(rule_evolver=rule, minimax_client=None)
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(),
            payload={"escalation_dump": MagicMock(), "failed_step_idx": 0},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, MutationProposal)
        assert rule.propose_evolution.called

    def test_rule_used_when_ai_throws(self):
        ai = MagicMock()
        ai.propose_evolution_via_ai.side_effect = RuntimeError("api down")
        rule = MagicMock()
        rule.propose_evolution.return_value = _inject_proposal()
        plugin = EvolutionPlugin(rule_evolver=rule, ai_evolver=ai,
                                 minimax_client=MagicMock())
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(),
            payload={"escalation_dump": MagicMock(), "failed_step_idx": 0},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, MutationProposal)


class TestEvolutionPluginBothFail:
    def test_returns_none_when_both_fail(self):
        ai = MagicMock()
        ai.propose_evolution_via_ai.return_value = None
        rule = MagicMock()
        rule.propose_evolution.return_value = None
        plugin = EvolutionPlugin(rule_evolver=rule, ai_evolver=ai,
                                 minimax_client=MagicMock())
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(),
            payload={"escalation_dump": MagicMock(), "failed_step_idx": 0},
        )
        assert plugin.on_event(ctx) is None


class TestEvolutionPluginProposalConversion:
    def test_inject_step_to_inject_before(self):
        m = EvolutionPlugin._proposal_to_mutation(_inject_proposal())
        assert m is not None
        assert m.mutation_type == StepMutationType.INJECT_BEFORE
        assert m.new_step_id == "T_PRE"
        assert m.new_step_prompt == "install deps"
        assert m.new_step_evaluator_command == "echo ok"

    def test_split_step_to_inject_before_first(self):
        m = EvolutionPlugin._proposal_to_mutation(_split_proposal())
        assert m is not None
        assert m.mutation_type == StepMutationType.INJECT_BEFORE
        assert m.new_step_id == "T01a"

    def test_revise_evaluator_to_revise_current(self):
        proposal = PlaybookEvolutionProposal(
            evolution_type="REVISE_EVALUATOR",
            inject_before_idx=0,
            reasoning="bad evaluator",
            revised_evaluator="pytest -xvs",
        )
        m = EvolutionPlugin._proposal_to_mutation(proposal)
        assert m is not None
        assert m.mutation_type == StepMutationType.REVISE_CURRENT
        assert "pytest -xvs" in m.revised_prompt

    def test_unknown_proposal_returns_none(self):
        proposal = PlaybookEvolutionProposal(
            evolution_type="UNKNOWN", inject_before_idx=0, reasoning="x",
        )
        assert EvolutionPlugin._proposal_to_mutation(proposal) is None


class TestEvolutionPluginLatestProposal:
    def test_latest_proposal_cached_after_event(self):
        ai = MagicMock()
        ai.propose_evolution_via_ai.return_value = _inject_proposal()
        plugin = EvolutionPlugin(ai_evolver=ai, minimax_client=MagicMock())
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(),
            payload={"escalation_dump": MagicMock(), "failed_step_idx": 0},
        )
        plugin.on_event(ctx)
        latest = plugin.latest_proposal()
        assert latest is not None
        assert latest.evolution_type == "INJECT_STEP"


class TestEvolutionPluginEventBusIntegration:
    def test_via_bus_emits_mutation_proposal(self):
        ai = MagicMock()
        ai.propose_evolution_via_ai.return_value = _inject_proposal()
        plugin = EvolutionPlugin(ai_evolver=ai, minimax_client=MagicMock())
        bus = EventBus()
        bus.register(plugin)
        merged = bus.emit(HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(),
            payload={"escalation_dump": MagicMock(), "failed_step_idx": 0},
        ))
        assert merged.request_mutation is not None
        assert merged.request_mutation.mutation_type == StepMutationType.INJECT_BEFORE
