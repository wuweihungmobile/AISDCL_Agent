"""SD_Improving_05 W0 三方審查 SA-C2 / Arch-M2：EventBus trace_id + escalate 測試。

QA Q-M1：「EventBus dispatch 加 trace_id，確保跨 phase 可追蹤」+
「連續 3 次相同 phase 失敗應 escalate」

驗證：
  - emit() 每次產生新 trace_id（除非 payload 顯式覆寫）
  - trace_id 不寫入 ctx.payload（SD-M5）
  - 相同 phase 跨 emit 各自獨立 trace_id
  - 連續 N 次相同 phase 失敗達 FAILURE_ESCALATE_THRESHOLD 進入 escalated_phases
  - 成功 dispatch 重置失敗計數
  - HookContractViolation 計入失敗
"""
from __future__ import annotations

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import (
    HookContext,
    HookContractViolation,
    IHook,
    KernelPhase,
    PHASE_RESULT_CONTRACT,
    PromptInjectionResult,
    VetoResult,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook


def _pb() -> Playbook:
    return Playbook(version="1.0", project="t",
                    global_invariants=GlobalInvariants(), tasks=[])


def _ctx(phase: KernelPhase = KernelPhase.PRE_RUN, payload: dict = None) -> HookContext:
    return HookContext(phase=phase, playbook=_pb(), payload=payload or {})


class _ContractViolatingHook:
    """總是在 PRE_RUN 回傳不合法 type（PromptInjectionResult，PRE_RUN 只允許 VetoResult）。"""
    def name(self): return "violator"
    def priority(self): return 50
    def subscribed_phases(self): return [KernelPhase.PRE_RUN]
    def on_event(self, ctx):
        return PromptInjectionResult(contributor="violator", prefix="X")


class _RaisingHook:
    """總是拋例外。"""
    def name(self): return "raiser"
    def priority(self): return 50
    def subscribed_phases(self): return [KernelPhase.PRE_STEP]
    def on_event(self, ctx):
        raise RuntimeError("boom")


class _PassiveHook:
    """什麼都不回傳的 hook。"""
    def name(self): return "passive"
    def priority(self): return 50
    def subscribed_phases(self): return [KernelPhase.PRE_RUN]
    def on_event(self, ctx):
        return None


class TestTraceId:
    def test_each_emit_generates_new_trace_id(self):
        bus = EventBus()
        bus.emit(_ctx())
        t1 = bus.last_trace_id()
        bus.emit(_ctx())
        t2 = bus.last_trace_id()
        assert t1 != t2

    def test_trace_id_is_12_hex_chars(self):
        bus = EventBus()
        bus.emit(_ctx())
        tid = bus.last_trace_id()
        assert tid is not None
        assert len(tid) == 12
        int(tid, 16)  # 必為合法 hex

    def test_explicit_payload_trace_id_preserved(self):
        bus = EventBus()
        ctx = _ctx(payload={"_trace_id": "abc123def456"})
        bus.emit(ctx)
        assert bus.last_trace_id() == "abc123def456"

    def test_payload_not_mutated_on_emit(self):
        """SD-M5：emit 不修改 ctx.payload。"""
        bus = EventBus()
        original_payload = {}
        ctx = _ctx(payload=original_payload)
        bus.emit(ctx)
        assert "_trace_id" not in original_payload

    def test_per_phase_trace_id_tracked(self):
        bus = EventBus()
        bus.emit(_ctx(KernelPhase.PRE_RUN))
        bus.emit(_ctx(KernelPhase.PRE_STEP))
        t_pre_run = bus.get_phase_trace_id(KernelPhase.PRE_RUN)
        t_pre_step = bus.get_phase_trace_id(KernelPhase.PRE_STEP)
        assert t_pre_run is not None
        assert t_pre_step is not None
        assert t_pre_run != t_pre_step


class TestPhaseFailureCounting:
    def test_successful_dispatch_keeps_count_zero(self):
        bus = EventBus()
        bus.register(_PassiveHook())
        bus.emit(_ctx())
        assert bus.get_phase_failure_count(KernelPhase.PRE_RUN) == 0

    def test_contract_violation_increments_counter(self):
        bus = EventBus()
        bus.register(_ContractViolatingHook())
        with pytest.raises(HookContractViolation):
            bus.emit(_ctx())
        assert bus.get_phase_failure_count(KernelPhase.PRE_RUN) == 1

    def test_hook_exception_increments_counter(self):
        bus = EventBus()
        bus.register(_RaisingHook())
        with pytest.raises(RuntimeError):
            bus.emit(_ctx(KernelPhase.PRE_STEP))
        assert bus.get_phase_failure_count(KernelPhase.PRE_STEP) == 1

    def test_success_after_failure_resets_count(self):
        bus = EventBus()
        bus.register(_ContractViolatingHook())
        with pytest.raises(HookContractViolation):
            bus.emit(_ctx())
        assert bus.get_phase_failure_count(KernelPhase.PRE_RUN) == 1
        # 移除違規 hook 後再 emit
        bus._subscribers[KernelPhase.PRE_RUN] = []
        bus.register(_PassiveHook())
        bus.emit(_ctx())
        assert bus.get_phase_failure_count(KernelPhase.PRE_RUN) == 0

    def test_different_phases_track_independently(self):
        bus = EventBus()
        bus.register(_ContractViolatingHook())
        bus.register(_RaisingHook())
        with pytest.raises(HookContractViolation):
            bus.emit(_ctx(KernelPhase.PRE_RUN))
        assert bus.get_phase_failure_count(KernelPhase.PRE_RUN) == 1
        assert bus.get_phase_failure_count(KernelPhase.PRE_STEP) == 0


class TestEscalateThreshold:
    """QA Q-M1：連續 3 次相同 phase 失敗 → escalate。"""

    def test_escalate_threshold_is_three(self):
        assert EventBus.FAILURE_ESCALATE_THRESHOLD == 3

    def test_two_failures_not_yet_escalated(self):
        bus = EventBus()
        bus.register(_ContractViolatingHook())
        for _ in range(2):
            with pytest.raises(HookContractViolation):
                bus.emit(_ctx())
        assert bus.is_phase_escalated(KernelPhase.PRE_RUN) is False

    def test_three_consecutive_failures_triggers_escalate(self):
        bus = EventBus()
        bus.register(_ContractViolatingHook())
        for _ in range(3):
            with pytest.raises(HookContractViolation):
                bus.emit(_ctx())
        assert bus.is_phase_escalated(KernelPhase.PRE_RUN) is True
        assert bus.get_phase_failure_count(KernelPhase.PRE_RUN) == 3

    def test_intermittent_success_prevents_escalate(self):
        """連續性中斷後不 escalate。"""
        bus = EventBus()
        bus.register(_ContractViolatingHook())
        bus.register(_PassiveHook())
        # 第 1 次：違規（fail）
        with pytest.raises(HookContractViolation):
            bus.emit(_ctx())
        # 移除違規 hook（模擬 fix 上線）
        bus._subscribers[KernelPhase.PRE_RUN] = [h for h in
            bus._subscribers[KernelPhase.PRE_RUN] if h.name() != "violator"]
        # 第 2 次：成功（reset count）
        bus.emit(_ctx())
        assert bus.is_phase_escalated(KernelPhase.PRE_RUN) is False
        assert bus.get_phase_failure_count(KernelPhase.PRE_RUN) == 0


class TestPhaseMigrationFlag:
    """SD_05 W0 SD-C7：T18_P2_PHASES_MIGRATED feature flag 環境讀取。"""

    def test_default_empty_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", raising=False)
        from autoclaude.core.phase_migration_flag import (
            get_migrated_phases, set_migrated_phases,
        )
        set_migrated_phases(None)  # 還原為環境變數
        assert get_migrated_phases() == frozenset()

    def test_env_var_parsed_into_set(self, monkeypatch):
        from autoclaude.core.phase_migration_flag import (
            get_migrated_phases, set_migrated_phases,
        )
        set_migrated_phases(None)
        monkeypatch.setenv(
            "AUTOCLAUDE_T18_P2_PHASES_MIGRATED",
            "PRE_COMPACT,POST_COMPACT,ON_PERSISTENCE_REQUEST",
        )
        phases = get_migrated_phases()
        assert phases == frozenset({"PRE_COMPACT", "POST_COMPACT", "ON_PERSISTENCE_REQUEST"})

    def test_illegal_phase_name_raises(self, monkeypatch):
        from autoclaude.core.phase_migration_flag import (
            get_migrated_phases, set_migrated_phases,
        )
        set_migrated_phases(None)
        monkeypatch.setenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", "BOGUS_PHASE")
        with pytest.raises(ValueError, match="非法|illegal"):
            get_migrated_phases()

    def test_is_phase_migrated(self, monkeypatch):
        from autoclaude.core.phase_migration_flag import (
            is_phase_migrated, set_migrated_phases,
        )
        set_migrated_phases({"PRE_COMPACT"})
        assert is_phase_migrated(KernelPhase.PRE_COMPACT) is True
        assert is_phase_migrated(KernelPhase.POST_COMPACT) is False
        set_migrated_phases(None)
