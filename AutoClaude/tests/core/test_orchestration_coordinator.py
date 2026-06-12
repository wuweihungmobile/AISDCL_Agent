"""tests/core/test_orchestration_coordinator.py — AC0-3 + ADR §7.4 QA 條件 1。

≥ 12 case 覆蓋：
  - phase 序錯誤偵測 → raise PhaseOrderViolation
  - 6 phase round-trip 正向 case
  - MAX_ACTIVE_RUNS_PER_GOAL guard 邊界（=5 / >5 拒絕）
  - send_interrupt EventBus + ACK seq 防重複觸發
  - Veto 短路 → 跳過 EXEC/ON_EVENT 直達 AFTER_EXEC

對應 ADR-SD06-001 §6.1 phase 序 + §6.4 send_interrupt + PM #8 guard。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import (
    HookContext,
    IHook,
    KernelPhase,
    VetoResult,
)
from autoclaude.core.orchestration import (
    CoordinatorResult,
    MaxActiveRunsExceeded,
    OrchestrationCoordinator,
    PhaseOrderViolation,
)
from autoclaude.core.ports.brain import BrainCapabilities, RetryPolicy
from autoclaude.core.ports.executor import (
    ExecutionEvent,
    ExecutionEventKind,
    ExecutionOutput,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask


# ──────────────────────────────────────────────────────────────
# Fake Brain / Executor / Plugin
# ──────────────────────────────────────────────────────────────
class _FakeBrain:
    def __init__(self, model_id: str = "fake-model"):
        self._model_id = model_id
        self.capabilities_call_count = 0

    def capabilities(self) -> BrainCapabilities:
        self.capabilities_call_count += 1
        return BrainCapabilities(
            max_context_tokens=100_000,
            supports_streaming=False,
            retry_policy=RetryPolicy(),
            model_id=self._model_id,
            dimension=1024,
        )

    def decide_correction(self, **_kwargs):
        return None

    def decide_escalation(self, **_kwargs):
        from autoclaude.core.ports.brain import EscalationDecision
        return EscalationDecision(human_handoff=True, reasoning="fake")


class _FakeExecutor:
    def __init__(self, completed: bool = True, emit_events: int = 2):
        self.completed = completed
        self.emit_events = emit_events
        self.interrupted_count = 0
        self.execute_call_count = 0
        self.last_on_event = None

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="",
                on_event=None) -> ExecutionOutput:
        self.execute_call_count += 1
        self.last_on_event = on_event
        if on_event is not None:
            for i in range(self.emit_events):
                on_event(ExecutionEvent(
                    kind=ExecutionEventKind.PROGRESS,
                    payload={"step": i + 1, "total": self.emit_events},
                    sequence=i + 1,
                ))
            on_event(ExecutionEvent(
                kind=ExecutionEventKind.COMPLETION,
                payload={"completed": self.completed, "exit_code": 0 if self.completed else 1},
                sequence=self.emit_events + 1,
            ))
        return ExecutionOutput(
            text="fake-output",
            exit_code=0 if self.completed else 1,
            completed=self.completed,
        )

    def send_interrupt(self, reason: str = "") -> bool:
        self.interrupted_count += 1
        return True


@dataclass
class _PhaseSpy(IHook):
    """記錄收到的 phase 順序的 fake Plugin。"""
    _name: str = "phase_spy"
    _priority: int = 50
    _subscribed: tuple = (
        KernelPhase.BEFORE_DECIDE,
        KernelPhase.DECIDE,
        KernelPhase.BEFORE_EXEC,
        KernelPhase.ON_EVENT,
        KernelPhase.AFTER_EXEC,
    )
    seen: list = None  # type: ignore[assignment]

    def __post_init__(self):
        self.seen = []

    def name(self) -> str:
        return self._name

    def priority(self) -> int:
        return self._priority

    def subscribed_phases(self) -> list:
        return list(self._subscribed)

    def on_event(self, ctx: HookContext):
        self.seen.append(ctx.phase)
        return None


class _VetoBeforeExecPlugin:
    """模擬 FastPath：BEFORE_EXEC 回 VetoResult。"""

    def name(self) -> str:
        return "veto_before_exec"

    def priority(self) -> int:
        return 50

    def subscribed_phases(self) -> list:
        return [KernelPhase.BEFORE_EXEC]

    def on_event(self, ctx: HookContext):
        return VetoResult(contributor="veto_test", reason="fast_path_skip")


def _make_playbook_and_task():
    pb = Playbook(version="1.0", project="test",
                  global_invariants=GlobalInvariants(), tasks=[])
    task = PlaybookTask(step_id="T01", name="test", prompt="do something",
                        expected_output_regex="fake-output")
    return pb, task


def _make_coord(*, max_runs: Optional[int] = None, executor_completed: bool = True,
                executor_events: int = 2, plugins: Optional[list] = None,
                ) -> tuple[OrchestrationCoordinator, EventBus, _FakeBrain, _FakeExecutor]:
    bus = EventBus()
    if plugins:
        for p in plugins:
            bus.register(p)
    brain = _FakeBrain()
    executor = _FakeExecutor(completed=executor_completed, emit_events=executor_events)
    coord = OrchestrationCoordinator(
        bus=bus, brain=brain, executor=executor,
        max_active_runs_per_goal=max_runs,
    )
    return coord, bus, brain, executor


# ──────────────────────────────────────────────────────────────
# AC0-3：6 phase round-trip 正向
# ──────────────────────────────────────────────────────────────
class TestPhaseOrderHappyPath:
    def test_run_step_completes_six_phases(self):
        """正常 step 跑完 6 phase 並回傳 CoordinatorResult。"""
        spy = _PhaseSpy()
        coord, _, brain, executor = _make_coord(plugins=[spy])
        pb, task = _make_playbook_and_task()

        result = coord.run_step(playbook=pb, task=task, step_idx=0)

        assert isinstance(result, CoordinatorResult)
        assert result.output.completed is True
        assert result.event_count == 3  # 2 PROGRESS + 1 COMPLETION
        assert brain.capabilities_call_count == 1
        assert executor.execute_call_count == 1
        # Plugin spy 收到 BEFORE_DECIDE, DECIDE, BEFORE_EXEC, ON_EVENT, AFTER_EXEC
        # （EXEC phase Plugin 不訂閱）
        assert spy.seen == [
            KernelPhase.BEFORE_DECIDE,
            KernelPhase.DECIDE,
            KernelPhase.BEFORE_EXEC,
            KernelPhase.ON_EVENT,
            KernelPhase.AFTER_EXEC,
        ]

    def test_reset_allows_subsequent_run(self):
        """run_step 兩次正常運作（reset 自動觸發）。"""
        coord, _, _, executor = _make_coord()
        pb, task = _make_playbook_and_task()
        coord.run_step(playbook=pb, task=task, step_idx=0)
        coord.run_step(playbook=pb, task=task, step_idx=1)
        assert executor.execute_call_count == 2


# ──────────────────────────────────────────────────────────────
# AC0-3：phase 序錯誤偵測 → raise PhaseOrderViolation
# ──────────────────────────────────────────────────────────────
class TestPhaseOrderViolation:
    def test_enter_phase_out_of_order_raises(self):
        """外部直接呼叫 _enter_phase 跳序時 raise。"""
        coord, *_ = _make_coord()
        coord.reset()
        coord._enter_phase(KernelPhase.BEFORE_DECIDE)
        with pytest.raises(PhaseOrderViolation, match="預期 decide"):
            coord._enter_phase(KernelPhase.BEFORE_EXEC)  # 跳過 DECIDE

    def test_enter_phase_after_complete_raises(self):
        """6 phase 跑完後再進入 raise PhaseOrderViolation。"""
        coord, *_ = _make_coord()
        pb, task = _make_playbook_and_task()
        coord.run_step(playbook=pb, task=task, step_idx=0)
        with pytest.raises(PhaseOrderViolation, match="6 phase 序已完成"):
            coord._enter_phase(KernelPhase.BEFORE_DECIDE)

    def test_repeat_same_phase_raises(self):
        """重複進入同一 phase raise。"""
        coord, *_ = _make_coord()
        coord.reset()
        coord._enter_phase(KernelPhase.BEFORE_DECIDE)
        with pytest.raises(PhaseOrderViolation):
            coord._enter_phase(KernelPhase.BEFORE_DECIDE)


# ──────────────────────────────────────────────────────────────
# PM #8：MAX_ACTIVE_RUNS_PER_GOAL guard 邊界
# ──────────────────────────────────────────────────────────────
class TestMaxActiveRunsGuard:
    def test_under_limit_passes(self):
        """active_runs < 5 正常通過。"""
        coord, *_ = _make_coord(max_runs=5)
        pb, task = _make_playbook_and_task()
        result = coord.run_step(playbook=pb, task=task, step_idx=0,
                                active_runs_for_goal=4)
        assert result.output.completed is True

    def test_at_limit_rejected(self):
        """active_runs == 5 觸發 raise（>=）。"""
        coord, *_ = _make_coord(max_runs=5)
        pb, task = _make_playbook_and_task()
        with pytest.raises(MaxActiveRunsExceeded, match="MAX_ACTIVE_RUNS_PER_GOAL=5"):
            coord.run_step(playbook=pb, task=task, step_idx=0,
                           active_runs_for_goal=5)

    def test_over_limit_rejected(self):
        """active_runs > 5 觸發 raise。"""
        coord, *_ = _make_coord(max_runs=5)
        pb, task = _make_playbook_and_task()
        with pytest.raises(MaxActiveRunsExceeded):
            coord.run_step(playbook=pb, task=task, step_idx=0,
                           active_runs_for_goal=10)

    def test_env_var_override(self, monkeypatch):
        """環境變數 MAX_ACTIVE_RUNS_PER_GOAL 覆寫建構子值。"""
        monkeypatch.setenv("MAX_ACTIVE_RUNS_PER_GOAL", "2")
        coord, *_ = _make_coord(max_runs=99)
        assert coord.max_active_runs_per_goal == 2

    def test_default_value_is_five(self, monkeypatch):
        """無 env / 無建構子值 → 預設 5（PM #8）。"""
        monkeypatch.delenv("MAX_ACTIVE_RUNS_PER_GOAL", raising=False)
        coord, *_ = _make_coord()
        assert coord.max_active_runs_per_goal == 5


# ──────────────────────────────────────────────────────────────
# Veto 短路：BEFORE_EXEC 被 Plugin 阻擋
# ──────────────────────────────────────────────────────────────
class TestBeforeExecVeto:
    def test_veto_skips_executor(self):
        """BEFORE_EXEC 被 Veto 後不呼叫 executor.execute。"""
        coord, _, _, executor = _make_coord(plugins=[_VetoBeforeExecPlugin()])
        pb, task = _make_playbook_and_task()
        result = coord.run_step(playbook=pb, task=task, step_idx=0)
        # MergedResult.veto_reasons 帶 [contributor] 前綴
        assert result.veto_reason is not None
        assert "fast_path_skip" in result.veto_reason
        assert executor.execute_call_count == 0
        assert result.output.completed is False  # placeholder


# ──────────────────────────────────────────────────────────────
# ADR §6.4：send_interrupt EventBus + ACK 防重複
# ──────────────────────────────────────────────────────────────
class TestSendInterrupt:
    def test_request_interrupt_forwards_to_executor(self):
        """coord.request_interrupt 委派至 executor.send_interrupt。"""
        coord, _, _, executor = _make_coord()
        ok = coord.request_interrupt("token_halt")
        assert ok is True
        assert executor.interrupted_count == 1

    def test_request_interrupt_idempotent_multiple_calls(self):
        """多次呼叫 request_interrupt 不會 race（adapter 端標記 idempotent）。"""
        coord, _, _, executor = _make_coord()
        coord.request_interrupt("first")
        coord.request_interrupt("second")
        assert executor.interrupted_count == 2  # adapter 自行 idempotent；coord 不去重

    def test_executor_event_sequence_monotonic(self):
        """ExecutionEvent.sequence 在單次 execute 內單調遞增（ACK seq 基礎）。"""
        coord, *_ = _make_coord(executor_events=3)
        pb, task = _make_playbook_and_task()
        coord.run_step(playbook=pb, task=task, step_idx=0)
        events = coord._captured_events
        seqs = [e.sequence for e in events]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == len(seqs)  # 無重複


# ──────────────────────────────────────────────────────────────
# ADR §6.2：capabilities 在 BEFORE_DECIDE phase 被讀取
# ──────────────────────────────────────────────────────────────
class TestCapabilitiesRead:
    def test_capabilities_called_once_per_step(self):
        """每個 run_step 呼叫一次 capabilities()。"""
        coord, _, brain, _ = _make_coord()
        pb, task = _make_playbook_and_task()
        coord.run_step(playbook=pb, task=task, step_idx=0)
        assert brain.capabilities_call_count == 1


# ──────────────────────────────────────────────────────────────
# ADR R3：Brain ↛ Executor 隔離（透過 EventBus on_event callback 仲裁）
# ──────────────────────────────────────────────────────────────
class TestBrainExecutorIsolation:
    def test_executor_receives_callback_from_coordinator_not_brain(self):
        """on_event callback 來自 Coordinator 內部 method，非 Brain 物件。"""
        coord, _, brain, executor = _make_coord()
        pb, task = _make_playbook_and_task()
        coord.run_step(playbook=pb, task=task, step_idx=0)
        # last_on_event 應該綁定 coord._on_executor_event；不可指向 brain
        assert executor.last_on_event is not None
        assert getattr(executor.last_on_event, "__self__", None) is coord
        # Brain 對 executor 沒有引用
        assert not hasattr(brain, "_executor")
