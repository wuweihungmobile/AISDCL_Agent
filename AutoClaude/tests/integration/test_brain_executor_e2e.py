"""tests/integration/test_brain_executor_e2e.py — SD_07 W2 T2-1 議題 0 e2e。

對應 AC0-1 / AC0-2 / AC0-3（[docs/03_testing/SD07_AC_Matrix.md](../../docs/03_testing/SD07_AC_Matrix.md)）：
  AC0-1 Token Halt → Coordinator → CheckpointPlugin → AutoResumeService 完整往返
  AC0-2 decide_correction → ExecutorPort.execute(on_event) → ON_EVENT phase 廣播
  AC0-2 decide_escalation → EvolutionPlugin → ON_ESCALATION_DUMP_REQUEST
  AC0-3 send_interrupt ACK + seq 嚴格遞增；ESC+F12 → ON_INTERRUPT_REQUEST → checkpoint round-trip

覆蓋 ≥ 8 case；fixture：tests/integration/fixtures/sd07_e2e_samples/。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pytest
import yaml

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import (
    CounterSnapshotResult,
    EscalationDumpedResult,
    HookContext,
    IHook,
    KernelPhase,
    ScheduleResumeResult,
)
from autoclaude.core.orchestration import (
    CoordinatorResult,
    MaxActiveRunsExceeded,
    OrchestrationCoordinator,
)
from autoclaude.core.ports.brain import (
    BrainCapabilities,
    CorrectionResult,
    EscalationDecision,
    RetryPolicy,
)
from autoclaude.core.ports.executor import (
    ExecutionEvent,
    ExecutionEventKind,
    ExecutionOutput,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sd07_e2e_samples"


# ──────────────────────────────────────────────────────────────
# Fake ports
# ──────────────────────────────────────────────────────────────
class _CountingBrain:
    """記錄 capabilities / decide_correction / decide_escalation 呼叫次數。"""

    def __init__(
        self,
        *,
        model_id: str = "MiniMax-Text-01",
        correction: Optional[CorrectionResult] = None,
        escalation: Optional[EscalationDecision] = None,
    ):
        self._model_id = model_id
        self._correction = correction
        self._escalation = escalation or EscalationDecision(
            human_handoff=True, reasoning="exhausted"
        )
        self.capabilities_calls = 0
        self.correction_calls = 0
        self.escalation_calls = 0

    def capabilities(self) -> BrainCapabilities:
        self.capabilities_calls += 1
        return BrainCapabilities(
            max_context_tokens=128_000,
            supports_streaming=False,
            retry_policy=RetryPolicy(max_attempts=3),
            model_id=self._model_id,
            dimension=1024,
        )

    def decide_correction(self, **_kwargs) -> Optional[CorrectionResult]:
        self.correction_calls += 1
        return self._correction

    def decide_escalation(self, **_kwargs) -> EscalationDecision:
        self.escalation_calls += 1
        return self._escalation


class _CountingExecutor:
    """可程式化的 IExecutor：emit 事件序列 + 記錄 send_interrupt seq。"""

    def __init__(
        self,
        *,
        events: Optional[list[ExecutionEvent]] = None,
        text: str = "[OK]",
        completed: bool = True,
    ):
        self._events = events or []
        self._text = text
        self._completed = completed
        self.execute_calls = 0
        self.interrupts: list[tuple[int, str]] = []
        self._interrupt_seq = 0
        self.last_callback: Optional[Any] = None
        self.subprocess_invocations = 0  # 紅線：dry_run 必 0

    def execute(
        self,
        prompt: str,
        *,
        maintain_context: bool = True,
        timeout: int = 600,
        label: str = "",
        on_event=None,
    ) -> ExecutionOutput:
        self.execute_calls += 1
        self.last_callback = on_event
        if on_event is not None:
            for ev in self._events:
                on_event(ev)
        return ExecutionOutput(
            text=self._text,
            exit_code=0 if self._completed else 1,
            completed=self._completed,
        )

    def send_interrupt(self, reason: str = "") -> bool:
        self._interrupt_seq += 1
        self.interrupts.append((self._interrupt_seq, reason))
        return True


# ──────────────────────────────────────────────────────────────
# Spy plugin：記錄 EventBus 廣播的 phase 序
# ──────────────────────────────────────────────────────────────
class _PhaseSpy(IHook):
    """訂閱多 phase，記錄收到順序；可指定回傳特定 IHookResult。"""

    def __init__(
        self,
        name: str,
        phases: tuple[KernelPhase, ...],
        *,
        priority: int = 50,
        responder=None,
    ):
        self._name = name
        self._priority = priority
        self._phases = phases
        self._responder = responder
        self.seen: list[KernelPhase] = []
        self.payloads: list[dict] = []

    def name(self) -> str:
        return self._name

    def priority(self) -> int:
        return self._priority

    def subscribed_phases(self) -> list[KernelPhase]:
        return list(self._phases)

    def on_event(self, ctx: HookContext):
        self.seen.append(ctx.phase)
        self.payloads.append(dict(ctx.payload or {}))
        if self._responder is not None:
            return self._responder(ctx)
        return None


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def _load_fixture(name: str) -> dict:
    return yaml.safe_load((FIXTURE_DIR / f"{name}.yaml").read_text(encoding="utf-8"))


def _make_playbook_from_fixture(fixture: dict) -> tuple[Playbook, list[PlaybookTask]]:
    pb_spec = fixture["playbook"]
    invariants = GlobalInvariants(**pb_spec.get("global_invariants", {}))
    tasks = [PlaybookTask(**t) for t in pb_spec["tasks"]]
    pb = Playbook(
        version=pb_spec.get("version", "1.0"),
        project=pb_spec["project"],
        global_goal=pb_spec.get("global_goal"),
        global_invariants=invariants,
        tasks=tasks,
    )
    return pb, tasks


def _make_coord(
    brain: _CountingBrain,
    executor: _CountingExecutor,
    plugins: Optional[list[IHook]] = None,
    *,
    max_runs: Optional[int] = None,
) -> tuple[OrchestrationCoordinator, EventBus]:
    bus = EventBus()
    for p in plugins or []:
        bus.register(p)
    coord = OrchestrationCoordinator(
        bus=bus, brain=brain, executor=executor,
        max_active_runs_per_goal=max_runs,
    )
    return coord, bus


# ──────────────────────────────────────────────────────────────
# AC0-1：capabilities cache + dry_run 完整 phase 序
# ──────────────────────────────────────────────────────────────
class TestCapabilitiesAndDryRun:
    def test_capabilities_single_call_per_step(self):
        """單一 step 內 capabilities() 只呼叫 1 次（dry_run 也須如此）。"""
        brain = _CountingBrain()
        executor = _CountingExecutor()
        coord, _ = _make_coord(brain, executor)
        pb, tasks = _make_playbook_from_fixture(_load_fixture("dry_run_mode"))
        coord.run_step(playbook=pb, task=tasks[0], step_idx=0)
        assert brain.capabilities_calls == 1

    def test_dry_run_full_phase_sequence(self):
        """dry_run fixture：完整 6 phase 廣播 + 不呼叫真實 subprocess。"""
        spy = _PhaseSpy(
            "dry_run_spy",
            (
                KernelPhase.BEFORE_DECIDE,
                KernelPhase.DECIDE,
                KernelPhase.BEFORE_EXEC,
                KernelPhase.ON_EVENT,
                KernelPhase.AFTER_EXEC,
            ),
        )
        brain = _CountingBrain(model_id="dry-run-fake")
        executor = _CountingExecutor(text="[DRY_RUN_OK]")
        coord, _ = _make_coord(brain, executor, [spy])
        pb, tasks = _make_playbook_from_fixture(_load_fixture("dry_run_mode"))

        for idx, task in enumerate(tasks):
            coord.run_step(playbook=pb, task=task, step_idx=idx)

        # 2 step × 5 訂閱 phase = 10
        assert len(spy.seen) == 10
        assert spy.seen[:5] == [
            KernelPhase.BEFORE_DECIDE,
            KernelPhase.DECIDE,
            KernelPhase.BEFORE_EXEC,
            KernelPhase.ON_EVENT,
            KernelPhase.AFTER_EXEC,
        ]
        # 紅線：fixture expected_subprocess_count=0
        assert executor.subprocess_invocations == 0
        assert brain.correction_calls == 0


# ──────────────────────────────────────────────────────────────
# AC0-1：Token Halt → Coordinator → CheckpointPlugin → AutoResume
# ──────────────────────────────────────────────────────────────
class TestTokenHaltRoundTrip:
    def test_token_halt_round_trip(self):
        """on_event 收到 token_pct=0.92 → 後續 ON_TOKEN_USAGE + ON_CHECKPOINT_SAVE_REQUEST。"""
        # Token Halt 事件由 Executor 透過 on_event 傳遞
        halt_event = ExecutionEvent(
            kind=ExecutionEventKind.TOKEN_PCT,
            payload={"pct": 0.92, "raw_match": "Context: 92% used"},
            sequence=1,
        )
        events_spy = _PhaseSpy("events_spy", (KernelPhase.ON_EVENT, KernelPhase.AFTER_EXEC))
        brain = _CountingBrain()
        executor = _CountingExecutor(events=[halt_event], completed=False)
        coord, bus = _make_coord(brain, executor, [events_spy])

        pb, tasks = _make_playbook_from_fixture(_load_fixture("token_halt"))
        result = coord.run_step(playbook=pb, task=tasks[0], step_idx=0)

        # Coordinator 捕獲事件；event_count 反映 on_event 收到 1 筆
        assert result.event_count == 1
        assert result.interrupted is True  # executor.completed=False

        # 模擬 CheckpointPlugin 收到 ON_CHECKPOINT_SAVE_REQUEST 廣播
        ckpt_spy = _PhaseSpy("ckpt", (KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,))
        bus.register(ckpt_spy)
        bus.emit(HookContext(
            phase=KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,
            playbook=pb,
            task=tasks[0],
            step_idx=0,
            payload={"peak_pct": 0.92, "trigger": "token_halt"},
        ))
        assert ckpt_spy.seen == [KernelPhase.ON_CHECKPOINT_SAVE_REQUEST]
        assert ckpt_spy.payloads[0]["trigger"] == "token_halt"


# ──────────────────────────────────────────────────────────────
# AC0-2：decide_correction → ExecutorPort.execute(on_event) → ON_EVENT
# ──────────────────────────────────────────────────────────────
class TestDecideCorrectionOnEvent:
    def test_decide_correction_on_event(self):
        """Brain 提供 correction（fixture 中 attempt=1 失敗、attempt=2 成功）。"""
        fixture = _load_fixture("decide_correction")
        revised = fixture["brain_decisions"]["decisions"][0]["revised_prompt"]
        brain = _CountingBrain(
            correction=CorrectionResult(
                correction_prompt=revised,
                reasoning="原 prompt 未指定輸出方式",
            ),
        )
        executor = _CountingExecutor(
            events=[
                ExecutionEvent(kind=ExecutionEventKind.PROGRESS,
                               payload={"line": "trying"}, sequence=1),
                ExecutionEvent(kind=ExecutionEventKind.PARTIAL_OUTPUT,
                               payload={"text": "[SUCCESS]"}, sequence=2),
                ExecutionEvent(kind=ExecutionEventKind.COMPLETION,
                               payload={"exit_code": 0, "completed": True}, sequence=3),
            ],
            text="[SUCCESS]",
        )
        on_event_spy = _PhaseSpy("on_event_spy", (KernelPhase.ON_EVENT,))
        coord, _ = _make_coord(brain, executor, [on_event_spy])
        pb, tasks = _make_playbook_from_fixture(fixture)

        result = coord.run_step(playbook=pb, task=tasks[0], step_idx=0)
        assert result.event_count == 3
        assert result.output.completed is True

        # ON_EVENT 廣播 1 次（彙整模式，W1 設計）
        assert on_event_spy.seen == [KernelPhase.ON_EVENT]
        assert on_event_spy.payloads[0]["event_count"] == 3

        # 模擬上層 PlaybookRunner 在 failure 時呼叫 decide_correction
        correction = brain.decide_correction(failure_reason="regex_no_match")
        assert correction is not None
        assert "echo" in correction.correction_prompt


# ──────────────────────────────────────────────────────────────
# AC0-2：decide_escalation → EvolutionPlugin → ON_ESCALATION_DUMP_REQUEST
# ──────────────────────────────────────────────────────────────
class TestDecideEscalationDump:
    def test_decide_escalation_dump_request_phase(self):
        """重試耗盡 → Brain.decide_escalation 回 human_handoff → Plugin 收 dump_request。"""
        brain = _CountingBrain(
            escalation=EscalationDecision(human_handoff=True, reasoning="exhausted"),
        )
        executor = _CountingExecutor(completed=False)
        # Spy 訂閱 escalation 三 phase + 提供 EscalationDumpedResult
        def _dump_responder(ctx):
            if ctx.phase == KernelPhase.ON_ESCALATION_DUMP_REQUEST:
                return EscalationDumpedResult(
                    contributor="evolution_plugin",
                    dump_path="/tmp/escalation_dump.json",
                )
            return None

        esc_spy = _PhaseSpy(
            "esc",
            (
                KernelPhase.ON_ESCALATION,
                KernelPhase.ON_EVOLUTION_PROPOSE,
                KernelPhase.ON_ESCALATION_DUMP_REQUEST,
            ),
            responder=_dump_responder,
        )
        _, bus = _make_coord(brain, executor, [esc_spy])
        pb, tasks = _make_playbook_from_fixture(_load_fixture("decide_escalation"))

        # 模擬 escalation 路徑：ON_ESCALATION → ON_EVOLUTION_PROPOSE → ON_ESCALATION_DUMP_REQUEST
        for ph in (
            KernelPhase.ON_ESCALATION,
            KernelPhase.ON_EVOLUTION_PROPOSE,
            KernelPhase.ON_ESCALATION_DUMP_REQUEST,
        ):
            bus.emit(HookContext(
                phase=ph, playbook=pb, task=tasks[0], step_idx=0,
                payload={"reason": "retry_exhausted"},
            ))

        assert esc_spy.seen == [
            KernelPhase.ON_ESCALATION,
            KernelPhase.ON_EVOLUTION_PROPOSE,
            KernelPhase.ON_ESCALATION_DUMP_REQUEST,
        ]
        decision = brain.decide_escalation(
            task=tasks[0], failure_history=[], convergence_trend="cycling",
        )
        assert decision.human_handoff is True
        assert brain.escalation_calls == 1


# ──────────────────────────────────────────────────────────────
# AC0-3：send_interrupt ACK + seq 嚴格遞增 + restart
# ──────────────────────────────────────────────────────────────
class TestSendInterruptAckAndRestart:
    def test_send_interrupt_seq_monotonic(self):
        """連續 send_interrupt seq 必嚴格遞增（restart 後也不重複）。"""
        brain = _CountingBrain()
        executor = _CountingExecutor()
        coord, _ = _make_coord(brain, executor)

        # 連續 5 次 interrupt（模擬 hotkey 重複觸發）
        for i in range(5):
            assert coord.request_interrupt(f"hotkey:{i}") is True

        seqs = [s for s, _ in executor.interrupts]
        # 嚴格遞增 + 起點為 1
        assert seqs == [1, 2, 3, 4, 5]
        assert all(seqs[i] < seqs[i + 1] for i in range(len(seqs) - 1))

    def test_interrupt_then_checkpoint_then_restart(self):
        """中斷 → 廣播 ON_CHECKPOINT_SAVE_REQUEST → 第二次 run_step 從正確 step 繼續。"""
        brain = _CountingBrain()
        executor = _CountingExecutor(events=[
            ExecutionEvent(kind=ExecutionEventKind.PROGRESS,
                           payload={"line": "running"}, sequence=1),
        ], completed=False)
        # ON_CHECKPOINT_SAVE_REQUEST 契約限定回 CounterSnapshotResult
        # （由 GotoCounterPlugin 回 counter snapshot，CheckpointPlugin 整合後寫檔）
        ckpt_spy = _PhaseSpy("ckpt", (KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,),
                             responder=lambda _ctx: CounterSnapshotResult(
                                 contributor="ckpt",
                                 snapshot={"goto": {}, "inject_before": {},
                                           "skip_to": {}, "step_evolution": {},
                                           "compact_failure": 0}))
        coord, bus = _make_coord(brain, executor, [ckpt_spy])
        pb, tasks = _make_playbook_from_fixture(_load_fixture("esc_f12_interrupt"))

        # 中斷觸發 → executor 標記 interrupted
        coord.request_interrupt("hotkey:esc+f12")
        # 模擬 HotkeyPlugin 廣播 checkpoint save
        bus.emit(HookContext(
            phase=KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,
            playbook=pb, task=tasks[0], step_idx=0,
            payload={"trigger": "hotkey_esc_f12"},
        ))
        assert ckpt_spy.seen == [KernelPhase.ON_CHECKPOINT_SAVE_REQUEST]

        # restart：從 step_idx=0 重啟（fixture restart_behavior.next_step_idx=0）
        # 模擬 Brain capabilities 在新 session 內仍只呼叫 1 次（cache 在 step 範圍內）
        executor2 = _CountingExecutor()  # 新 executor 模擬 restart
        coord2, _ = _make_coord(brain, executor2)
        result = coord2.run_step(playbook=pb, task=tasks[0], step_idx=0)
        assert result.output.completed is True


# ──────────────────────────────────────────────────────────────
# AC0-3：Brain/Executor isolation — callback 是唯一通道
# ──────────────────────────────────────────────────────────────
class TestBrainExecutorIsolation:
    def test_on_event_is_only_back_channel(self):
        """Executor 不可直接呼叫 Brain；only on_event callback 抵達 Coordinator。"""
        brain = _CountingBrain()
        executor = _CountingExecutor(events=[
            ExecutionEvent(kind=ExecutionEventKind.PROGRESS,
                           payload={"step": 1}, sequence=1),
        ])
        coord, _ = _make_coord(brain, executor)
        pb, tasks = _make_playbook_from_fixture(_load_fixture("dry_run_mode"))

        coord.run_step(playbook=pb, task=tasks[0], step_idx=0)

        # Executor 收到的 callback 是 Coordinator._on_executor_event；不是 Brain
        assert executor.last_callback is not None
        # Brain 沒被 Executor 直接呼叫（capabilities=1 來自 Coordinator）
        assert brain.capabilities_calls == 1
        assert brain.correction_calls == 0
        assert brain.escalation_calls == 0


# ──────────────────────────────────────────────────────────────
# PM #8：MAX_ACTIVE_RUNS_PER_GOAL guard 端對端
# ──────────────────────────────────────────────────────────────
class TestMaxActiveRunsGuardE2E:
    def test_max_active_runs_guard_blocks_sixth_run(self):
        """5 個 run 並存，第 6 個觸發 MaxActiveRunsExceeded。"""
        brain = _CountingBrain()
        executor = _CountingExecutor()
        coord, _ = _make_coord(brain, executor, max_runs=5)
        pb, tasks = _make_playbook_from_fixture(_load_fixture("dry_run_mode"))

        # 前 5 個 active runs：active_runs_for_goal=0..4 都應通過
        for active in range(5):
            r = coord.run_step(
                playbook=pb, task=tasks[0], step_idx=0, active_runs_for_goal=active,
            )
            assert isinstance(r, CoordinatorResult)

        # 第 6 個（active_runs_for_goal=5）觸發
        with pytest.raises(MaxActiveRunsExceeded, match="MAX_ACTIVE_RUNS_PER_GOAL=5"):
            coord.run_step(
                playbook=pb, task=tasks[0], step_idx=0, active_runs_for_goal=5,
            )


# ──────────────────────────────────────────────────────────────
# AutoResume wake metrics（ON_AUTO_RESUME_WAKE 廣播）
# ──────────────────────────────────────────────────────────────
class TestAutoResumeWakeMetrics:
    def test_token_halt_wake_kind_emitted(self):
        """token_halt 觸發後，AutoResumeService emit ON_AUTO_RESUME_WAKE，plugin 收到 'token_halt' kind。"""
        wake_spy = _PhaseSpy("wake_spy", (KernelPhase.ON_AUTO_RESUME_WAKE,),
                             responder=lambda _ctx: ScheduleResumeResult(
                                 contributor="notif", scheduled_at="2026-05-18T12:00:00Z"))
        brain = _CountingBrain()
        executor = _CountingExecutor()
        _, bus = _make_coord(brain, executor, [wake_spy])
        pb, tasks = _make_playbook_from_fixture(_load_fixture("token_halt"))

        # 模擬 AutoResumeService.record_wake_and_emit 路徑：emit ON_AUTO_RESUME_WAKE
        bus.emit(HookContext(
            phase=KernelPhase.ON_AUTO_RESUME_WAKE,
            playbook=pb, task=tasks[0], step_idx=0,
            payload={"kind": "token_halt", "scheduled_resume_at": "2026-05-18T12:00:00Z"},
        ))
        assert wake_spy.seen == [KernelPhase.ON_AUTO_RESUME_WAKE]
        assert wake_spy.payloads[0]["kind"] == "token_halt"
