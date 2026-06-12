"""SD_Improving_05 W5 批3-C / M-9：AutoResumeMetrics + ON_AUTO_RESUME_WAKE 測試。

覆蓋：
  - AutoResumeMetrics 初始化與 snapshot
  - record_wake_and_emit 累計 metrics（halt / evolution / checkpoint_resume）
  - ON_AUTO_RESUME_WAKE phase 觸發 EventBus.emit
  - bus=None 時 metrics 仍累計但 emit 跳過
  - emit 異常不影響主流程
  - AutoResumeService.metrics property 對外暴露
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import (
    HookContext,
    HookContractViolation,
    IHook,
    KernelPhase,
    PromptInjectionResult,
    ScheduleResumeResult,
)
from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.services._auto_resume_metrics import (
    AutoResumeMetrics,
    record_wake_and_emit,
)
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.repositories.in_memory_state_repository import (
    InMemoryStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
from autoclaude.utils.config import AppConfig

FIXTURES_DIR = Path(__file__).parent.parent / "equivalence" / "fixtures"
SIMPLE_PB = str(FIXTURES_DIR / "01_simple_2_step.yaml")


class _RecordingHook:
    """訂閱 ON_AUTO_RESUME_WAKE 並記錄收到的 payload。"""

    def __init__(self):
        self.received: list[dict] = []

    def name(self): return "recorder"
    def priority(self): return 50
    def subscribed_phases(self): return [KernelPhase.ON_AUTO_RESUME_WAKE]

    def on_event(self, ctx: HookContext):
        self.received.append(dict(ctx.payload))
        return ScheduleResumeResult(
            contributor="recorder",
            scheduled_at=ctx.payload.get("scheduled_at") or "",
        )


class _FakeKernelWithBus:
    """記錄 run() 收到的 start_idx，並提供真實 EventBus。"""

    def __init__(self, result: KernelResult | None = None, bus: EventBus | None = None):
        self.calls: list[int] = []
        self._result = result or KernelResult(
            success=True, completed_steps=2, total_steps=2, reason="success",
        )
        self._bus = bus or EventBus()

    @property
    def bus(self) -> EventBus:
        return self._bus

    def run(self, playbook, start_idx: int = 0) -> KernelResult:
        self.calls.append(start_idx)
        return self._result


class TestAutoResumeMetricsDataclass:
    def test_initial_values_are_zero(self):
        m = AutoResumeMetrics()
        assert m.total_wakes == 0
        assert m.halt_resumes == 0
        assert m.evolution_restarts == 0
        assert m.checkpoint_resumes == 0
        assert m.failed_emits == 0  # W5 三方審查 Major-SA1：新增 failed_emits
        assert m.total_wait_seconds == 0.0
        assert m.last_wake_at is None
        assert m.last_scheduled_resume_at is None
        assert list(m.wake_kinds) == []

    def test_snapshot_returns_dict_with_all_fields(self):
        m = AutoResumeMetrics(total_wakes=3, halt_resumes=2)
        snap = m.snapshot()
        assert snap["total_wakes"] == 3
        assert snap["halt_resumes"] == 2
        # W5 三方審查 Minor-SA2：用 >= 而非 == 提供 forward compatibility
        required_keys = {
            "total_wakes", "halt_resumes", "evolution_restarts",
            "checkpoint_resumes", "failed_emits", "total_wait_seconds",
            "last_wake_at", "last_scheduled_resume_at", "wake_kinds",
        }
        assert required_keys.issubset(snap.keys())

    def test_snapshot_does_not_share_wake_kinds_reference(self):
        """snapshot 應淺拷貝 wake_kinds 避免外部污染。"""
        m = AutoResumeMetrics()
        m.wake_kinds.append("halt")
        snap = m.snapshot()
        snap["wake_kinds"].append("mutated")
        assert list(m.wake_kinds) == ["halt"]


class TestRecordWakeAndEmit:
    def test_halt_kind_increments_halt_counter(self):
        m = AutoResumeMetrics()
        bus = EventBus()
        record_wake_and_emit(m, bus, kind="halt", scheduled_at="2026-01-01T00:00:00", wait_secs=12.5)
        assert m.total_wakes == 1
        assert m.halt_resumes == 1
        assert m.evolution_restarts == 0
        assert m.checkpoint_resumes == 0
        assert m.total_wait_seconds == 12.5
        assert list(m.wake_kinds) == ["halt"]
        assert m.last_scheduled_resume_at == "2026-01-01T00:00:00"

    def test_evolution_kind_increments_evolution_counter(self):
        m = AutoResumeMetrics()
        record_wake_and_emit(m, EventBus(), kind="evolution", scheduled_at=None, wait_secs=0.0)
        assert m.evolution_restarts == 1
        assert m.halt_resumes == 0
        assert m.checkpoint_resumes == 0

    def test_checkpoint_resume_kind(self):
        m = AutoResumeMetrics()
        record_wake_and_emit(m, EventBus(), kind="checkpoint_resume",
                             scheduled_at="2026-01-01", wait_secs=5.0)
        assert m.checkpoint_resumes == 1

    def test_unknown_kind_raises_value_error(self):
        """W5 三方審查 Major-SA2：未知 kind 必須 raise ValueError（防 silent failure）。"""
        m = AutoResumeMetrics()
        with pytest.raises(ValueError, match="不支援的 kind"):
            record_wake_and_emit(m, EventBus(), kind="unknown_kind",  # type: ignore[arg-type]
                                 scheduled_at=None, wait_secs=1.0)
        # 應在 raise 前就拒絕，不累計 metrics
        assert m.total_wakes == 0

    def test_negative_wait_clamped_to_zero(self):
        m = AutoResumeMetrics()
        record_wake_and_emit(m, EventBus(), kind="halt", scheduled_at=None, wait_secs=-10.0)
        assert m.total_wait_seconds == 0.0

    def test_bus_none_logs_error_but_still_records_metrics(self, caplog):
        """W5 三方審查 Major-A2：bus=None 改 logger.error（wiring 異常 alarm）。"""
        m = AutoResumeMetrics()
        with caplog.at_level("ERROR"):
            record_wake_and_emit(m, None, kind="halt", scheduled_at=None, wait_secs=1.0)
        assert m.total_wakes == 1
        assert m.halt_resumes == 1
        assert any("bus=None" in rec.message for rec in caplog.records)

    def test_emit_triggers_event_bus_with_correct_payload(self):
        bus = EventBus()
        hook = _RecordingHook()
        bus.register(hook)
        m = AutoResumeMetrics()
        record_wake_and_emit(m, bus, kind="halt",
                             scheduled_at="2026-01-01T00:00:00", wait_secs=30.0)

        assert len(hook.received) == 1
        payload = hook.received[0]
        assert payload["kind"] == "halt"
        assert payload["wait_seconds"] == 30.0
        assert payload["scheduled_at"] == "2026-01-01T00:00:00"
        assert "wake_at" in payload
        assert payload["metrics_snapshot"]["total_wakes"] == 1
        assert payload["metrics_snapshot"]["halt_resumes"] == 1

    def test_emit_exception_does_not_break_main_flow(self):
        """OSError/ValueError/RuntimeError 降為 warning，metrics 仍累計（failed_emits +1）。"""
        m = AutoResumeMetrics()

        class _ThrowingBus:
            def emit(self, ctx):
                raise RuntimeError("emit failed")

        record_wake_and_emit(m, _ThrowingBus(), kind="halt",
                             scheduled_at=None, wait_secs=5.0)
        assert m.total_wakes == 1
        assert m.halt_resumes == 1
        assert m.failed_emits == 1

    def test_hook_contract_violation_must_propagate(self):
        """W5 三方審查 Critical-A2+SD2：真實 EventBus 的 HookContractViolation
        必須冒泡（W0 fail-fast 契約），不可被 metrics 路徑吞噬。"""
        class _BadHook:
            def name(self): return "bad"
            def priority(self): return 50
            def subscribed_phases(self): return [KernelPhase.ON_AUTO_RESUME_WAKE]
            def on_event(self, ctx):
                # 回傳 PHASE_RESULT_CONTRACT 不允許的型別
                return PromptInjectionResult(contributor="bad", prefix="X")

        bus = EventBus()
        bus.register(_BadHook())
        m = AutoResumeMetrics()
        with pytest.raises(HookContractViolation):
            record_wake_and_emit(m, bus, kind="halt", scheduled_at=None, wait_secs=1.0)
        # metrics 累計仍應發生（reserve 在 emit 之前）
        assert m.total_wakes == 1
        assert m.failed_emits == 1

    def test_multiple_wakes_accumulate(self):
        m = AutoResumeMetrics()
        bus = EventBus()
        record_wake_and_emit(m, bus, kind="halt", scheduled_at=None, wait_secs=10.0)
        record_wake_and_emit(m, bus, kind="halt", scheduled_at=None, wait_secs=20.0)
        record_wake_and_emit(m, bus, kind="evolution", scheduled_at=None, wait_secs=0.0)
        assert m.total_wakes == 3
        assert m.halt_resumes == 2
        assert m.evolution_restarts == 1
        assert m.total_wait_seconds == 30.0
        assert list(m.wake_kinds) == ["halt", "halt", "evolution"]

    def test_wake_kinds_bounded_deque_prevents_memory_leak(self):
        """W5 三方審查 Major-SA1：wake_kinds 為 bounded deque（maxlen=200）。"""
        m = AutoResumeMetrics()
        bus = EventBus()
        for _ in range(250):
            record_wake_and_emit(m, bus, kind="halt", scheduled_at=None, wait_secs=0.0)
        assert m.total_wakes == 250  # counter 不受 maxlen 限制
        assert len(m.wake_kinds) == 200  # deque maxlen 強制


def _playbook_id_for(path: str, cfg: AppConfig) -> str:
    from autoclaude.infra.repositories.factory import canonical_playbook_id
    return canonical_playbook_id(path, mode=cfg.storage.mode)


def _make_checkpoint(step_idx: int = 1, scheduled: str | None = None) -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path=SIMPLE_PB,
        step_idx=step_idx,
        step_id=f"T{step_idx + 1:02d}",
        total_steps=2,
        completed_step_log=[f"[T{i + 1:02d}] done" for i in range(step_idx)],
        scheduled_resume_at=scheduled,
    )


class TestAutoResumeServiceMetricsProperty:
    def test_metrics_property_returns_snapshot_dict(self):
        """W5 三方審查 Major-A1：metrics 改回 snapshot dict，防外部寫入。"""
        cfg = AppConfig()
        kernel = _FakeKernelWithBus()
        svc = AutoResumeService(kernel, cfg)
        assert isinstance(svc.metrics, dict)
        assert svc.metrics["total_wakes"] == 0
        # 外部修改 snapshot 不影響內部狀態
        svc.metrics["total_wakes"] = 999
        assert svc._metrics_object.total_wakes == 0  # internal unchanged

    def test_run_with_expired_checkpoint_records_checkpoint_resume(self):
        """過期 scheduled_resume_at 仍記錄 checkpoint_resume metrics。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        past = (datetime.now() - timedelta(minutes=10)).isoformat(timespec="seconds")
        ck = _make_checkpoint(step_idx=1, scheduled=past)
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), ck)
        kernel = _FakeKernelWithBus()
        svc = AutoResumeService(kernel, cfg, state_repository=repo)

        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            svc.run(SIMPLE_PB, fresh=False)

        snap = svc.metrics
        assert snap["checkpoint_resumes"] == 1
        assert snap["total_wakes"] == 1
        assert "checkpoint_resume" in snap["wake_kinds"]

    def test_run_with_future_checkpoint_records_metrics_within_expected_range(self):
        """W5 三方審查 Minor-SA1：補上界斷言（防 wait_secs 計算 overflow）。"""
        cfg = AppConfig()
        repo = InMemoryStateRepository()
        future = (datetime.now() + timedelta(minutes=5)).isoformat(timespec="seconds")
        ck = _make_checkpoint(step_idx=1, scheduled=future)
        repo.save_checkpoint(_playbook_id_for(SIMPLE_PB, cfg), ck)
        kernel = _FakeKernelWithBus()
        svc = AutoResumeService(kernel, cfg, state_repository=repo)

        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            svc.run(SIMPLE_PB, fresh=False)

        snap = svc.metrics
        assert snap["checkpoint_resumes"] == 1
        # 5 分鐘 = 300 秒；扣除 latency 餘裕後 60 < x <= 310
        assert 60 < snap["total_wait_seconds"] <= 310

    def test_run_with_halt_records_halt_metrics(self):
        """Kernel 回傳 halted=True 觸發 halt resume metrics（用 Mock 取代 _SeqKernel）。"""
        from unittest.mock import MagicMock
        cfg = AppConfig()
        future = (datetime.now() + timedelta(seconds=1)).isoformat(timespec="seconds")
        halt_result = KernelResult(
            success=False, completed_steps=0, total_steps=2,
            reason="halt", halted=True, scheduled_resume_at=future,
        )
        ok_result = KernelResult(
            success=True, completed_steps=2, total_steps=2, reason="ok",
        )

        kernel = _FakeKernelWithBus()
        kernel.run = MagicMock(side_effect=[halt_result, ok_result])
        svc = AutoResumeService(kernel, cfg)
        with patch("autoclaude.core.services.auto_resume.time.sleep"):
            svc.run(SIMPLE_PB, fresh=True)

        snap = svc.metrics
        assert snap["halt_resumes"] == 1
        assert "halt" in snap["wake_kinds"]
        assert kernel.run.call_count == 2  # halt → resume → success
