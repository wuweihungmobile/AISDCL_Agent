"""event_bus.py 單元測試（Phase 2）。

驗證：
  - EventBus 註冊與 emit 的基本流程
  - priority 排序（小者先）+ 同 priority 由 register 順序 tie-break
  - DefaultResolutionPolicy 6 條決定性合併規則
  - PHASE_RESULT_CONTRACT 違反時 fail-fast（HookContractViolation）
  - get_plugin 能查找已註冊的 plugin
  - 自定義 IResolutionPolicy 可注入（DIP）
"""
from __future__ import annotations

from typing import Any, Optional

import pytest

from autoclaude.core.event_bus import DefaultResolutionPolicy, EventBus, MergedResult
from autoclaude.core.hookspec import (
    HookContext,
    HookContractViolation,
    KernelPhase,
    MutationProposal,
    PromptInjectionResult,
    ResourceRequest,
    VetoResult,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook
from autoclaude.models.step_mutation import StepMutation, StepMutationType


def _pb() -> Playbook:
    return Playbook(version="1.0", project="t",
                    global_invariants=GlobalInvariants(), tasks=[])


class _SpyHook:
    """簡單 spy plugin。"""
    def __init__(self, name: str, priority_v: int, phases: list[KernelPhase],
                 result: Optional[Any] = None):
        self._n = name
        self._p = priority_v
        self._ph = phases
        self._r = result
        self.calls: list[KernelPhase] = []

    def name(self) -> str: return self._n
    def priority(self) -> int: return self._p
    def subscribed_phases(self) -> list[KernelPhase]: return self._ph
    def on_event(self, ctx: HookContext) -> Optional[Any]:
        self.calls.append(ctx.phase)
        return self._r


class TestEventBusBasic:
    def test_register_and_emit_no_subscribers(self):
        bus = EventBus()
        merged = bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb()))
        assert isinstance(merged, MergedResult)
        assert merged.veto is False
        assert merged.contributors == []

    def test_register_invokes_on_event(self):
        bus = EventBus()
        spy = _SpyHook("spy", 50, [KernelPhase.PRE_RUN])
        bus.register(spy)
        bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb()))
        assert spy.calls == [KernelPhase.PRE_RUN]

    def test_phase_filter(self):
        bus = EventBus()
        spy = _SpyHook("spy", 50, [KernelPhase.POST_RUN])
        bus.register(spy)
        bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb()))
        assert spy.calls == []

    def test_get_plugin_by_name(self):
        bus = EventBus()
        spy = _SpyHook("alpha", 50, [KernelPhase.PRE_RUN])
        bus.register(spy)
        assert bus.get_plugin("alpha") is spy
        assert bus.get_plugin("nonexistent") is None


class TestPrioritySort:
    def test_lower_priority_called_first(self):
        bus = EventBus()
        order: list[str] = []
        class _Order:
            def __init__(self, n, p): self._n, self._p = n, p
            def name(self): return self._n
            def priority(self): return self._p
            def subscribed_phases(self): return [KernelPhase.PRE_RUN]
            def on_event(self, ctx):
                order.append(self._n)
                return None
        bus.register(_Order("late", 90))
        bus.register(_Order("early", 5))
        bus.register(_Order("mid", 50))
        bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb()))
        assert order == ["early", "mid", "late"]

    def test_same_priority_uses_register_order(self):
        bus = EventBus()
        order: list[str] = []
        class _O:
            def __init__(self, n): self._n = n
            def name(self): return self._n
            def priority(self): return 50
            def subscribed_phases(self): return [KernelPhase.PRE_RUN]
            def on_event(self, ctx):
                order.append(self._n)
                return None
        bus.register(_O("a"))
        bus.register(_O("b"))
        bus.register(_O("c"))
        bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb()))
        assert order == ["a", "b", "c"]


class TestVetoMerging:
    def test_single_veto(self):
        bus = EventBus()
        bus.register(_SpyHook("v", 5, [KernelPhase.PRE_RUN],
                              result=VetoResult(contributor="v", reason="bad")))
        merged = bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb()))
        assert merged.veto is True
        assert "[v] bad" in merged.veto_reasons

    def test_multiple_vetos_accumulated(self):
        bus = EventBus()
        bus.register(_SpyHook("v1", 5, [KernelPhase.PRE_RUN],
                              result=VetoResult(contributor="v1", reason="r1")))
        bus.register(_SpyHook("v2", 10, [KernelPhase.PRE_RUN],
                              result=VetoResult(contributor="v2", reason="r2")))
        merged = bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb()))
        assert len(merged.veto_reasons) == 2


class TestPromptInjectionMerging:
    def test_prefix_concatenation_in_priority_order(self):
        bus = EventBus()
        bus.register(_SpyHook("a", 35, [KernelPhase.PRE_ATTEMPT],
                              result=PromptInjectionResult(contributor="a", prefix="A:")))
        bus.register(_SpyHook("b", 30, [KernelPhase.PRE_ATTEMPT],
                              result=PromptInjectionResult(contributor="b", prefix="B:")))
        merged = bus.emit(HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=_pb()))
        # b 先（priority 30），a 後（35）
        assert merged.accumulated_prefix == "B:A:"


class TestResourceRequestOrLogic:
    def test_or_compact_and_halt(self):
        bus = EventBus()
        bus.register(_SpyHook("x", 30, [KernelPhase.ON_TOKEN_USAGE],
                              result=ResourceRequest(contributor="x", request_compact=True)))
        bus.register(_SpyHook("y", 30, [KernelPhase.ON_TOKEN_USAGE],
                              result=ResourceRequest(contributor="y", request_halt=True)))
        merged = bus.emit(HookContext(phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb()))
        assert merged.request_compact is True
        assert merged.request_halt is True


class TestMutationProposalMerging:
    def test_takes_first_proposal(self):
        bus = EventBus()
        m1 = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="m1")
        m2 = StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="m2")
        bus.register(_SpyHook("e1", 70, [KernelPhase.POST_ATTEMPT],
                              result=MutationProposal(contributor="e1", mutation=m1)))
        bus.register(_SpyHook("e2", 80, [KernelPhase.POST_ATTEMPT],
                              result=MutationProposal(contributor="e2", mutation=m2)))
        merged = bus.emit(HookContext(phase=KernelPhase.POST_ATTEMPT, playbook=_pb()))
        # e1 priority 較低 → 取它的 mutation
        assert merged.request_mutation is m1


class TestPhaseContractEnforcement:
    def test_pre_run_only_veto_allowed(self):
        bus = EventBus()
        # PRE_RUN 不允許 PromptInjectionResult
        bad = PromptInjectionResult(contributor="bad", prefix="x")
        bus.register(_SpyHook("bad", 5, [KernelPhase.PRE_RUN], result=bad))
        with pytest.raises(HookContractViolation):
            bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb()))

    def test_observer_phase_no_contract_allows_none(self):
        bus = EventBus()
        # ON_SUCCESS 無 contract，回傳 None 不應 fail
        bus.register(_SpyHook("kb", 50, [KernelPhase.ON_SUCCESS], result=None))
        bus.emit(HookContext(phase=KernelPhase.ON_SUCCESS, playbook=_pb()))


class TestCustomResolutionPolicy:
    def test_custom_policy_can_be_injected(self):
        # DIP 驗證：可注入自定義 policy
        called = {"merged": False}
        class _Custom:
            def merge(self, phase, results):
                called["merged"] = True
                return MergedResult(contributors=["custom"])
        bus = EventBus(policy=_Custom())
        bus.register(_SpyHook("a", 50, [KernelPhase.PRE_RUN],
                              result=VetoResult(contributor="a", reason="")))
        m = bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb()))
        assert called["merged"] is True
        assert m.contributors == ["custom"]
