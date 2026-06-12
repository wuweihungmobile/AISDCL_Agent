"""tests/core/ports/test_executor_events.py — AC0-2（SD_Improving_06 W1 T1-8）。

驗證 ExecutionEvent + ExecutionEventKind + on_event callback + send_interrupt 機制。

對應 ADR-SD06-001 §6.3 五種事件種類：
  progress / partial_output / tool_use / token_pct / completion
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from autoclaude.core.ports.executor import (
    ExecutionEvent,
    ExecutionEventKind,
    ExecutionOutput,
    IExecutor,
)
from autoclaude.infra.adapters.dry_run_executor import DryRunExecutor


# ──────────────────────────────────────────────────────────────
# AC0-2：ExecutionEventKind 五值定案（ADR §6.3）
# ──────────────────────────────────────────────────────────────
class TestExecutionEventKind:
    def test_five_kinds_defined(self):
        """ADR §6.3 五值（含 QA 強制 completion）。"""
        assert set(ExecutionEventKind.all()) == {
            "progress",
            "partial_output",
            "tool_use",
            "token_pct",
            "completion",
        }

    def test_completion_is_present(self):
        """QA 條件：completion 必須在；缺少將導致 AFTER_EXEC 漏失終態。"""
        assert ExecutionEventKind.COMPLETION == "completion"


# ──────────────────────────────────────────────────────────────
# ExecutionEvent dataclass 結構
# ──────────────────────────────────────────────────────────────
class TestExecutionEvent:
    def test_event_is_frozen(self):
        ev = ExecutionEvent(kind="completion", payload={}, sequence=0)
        with pytest.raises(FrozenInstanceError):
            ev.sequence = 1  # type: ignore[misc]

    def test_event_payload_default_factory(self):
        ev = ExecutionEvent(kind="progress")
        assert ev.payload == {}
        assert ev.sequence == 0


# ──────────────────────────────────────────────────────────────
# on_event callback 整合（DryRunExecutor 為測試夾具）
# ──────────────────────────────────────────────────────────────
class TestOnEventCallback:
    def test_on_event_receives_completion_event(self):
        """DryRunExecutor 在 execute 結束時 emit 一筆 COMPLETION event。"""
        received: list[ExecutionEvent] = []

        executor = DryRunExecutor()
        executor.execute(
            "prompt",
            label="T01",
            on_event=lambda ev: received.append(ev),
        )
        assert len(received) == 1
        assert received[0].kind == ExecutionEventKind.COMPLETION
        assert received[0].payload["completed"] is True

    def test_on_event_callback_optional(self):
        """on_event 為可選參數；不傳不應拋例外。"""
        executor = DryRunExecutor()
        out = executor.execute("prompt", label="T01")
        assert isinstance(out, ExecutionOutput)
        assert out.text == "[dry-run] dry-run-pass"

    def test_on_event_exception_does_not_crash_executor(self):
        """callback 拋例外不應影響 execute 結果（adapter 邊界吞掉）。"""
        def _bad_callback(ev):
            raise RuntimeError("plugin bug")

        executor = DryRunExecutor()
        out = executor.execute("prompt", label="T01", on_event=_bad_callback)
        assert out.completed is True


# ──────────────────────────────────────────────────────────────
# send_interrupt 機制（ADR §6.4）
# ──────────────────────────────────────────────────────────────
class TestSendInterrupt:
    def test_send_interrupt_returns_true(self):
        """send_interrupt 應回傳 True 代表已接收請求。"""
        executor = DryRunExecutor()
        assert executor.send_interrupt("test_reason") is True

    def test_send_interrupt_short_circuits_next_execute(self):
        """send_interrupt 後下次 execute 直接回 completed=False。"""
        executor = DryRunExecutor()
        executor.send_interrupt("token_halt")
        out = executor.execute("prompt", label="T01")
        assert out.completed is False
        assert out.exit_code == 1

    def test_send_interrupt_flag_resets_after_execute(self):
        """interrupt 旗標執行後重置；下次 execute 正常進行。"""
        executor = DryRunExecutor()
        executor.send_interrupt("once")
        executor.execute("p1", label="T01")  # 被中斷
        out = executor.execute("p2", label="T02")  # 恢復正常
        assert out.completed is True


# ──────────────────────────────────────────────────────────────
# IExecutor Protocol 結構驗證
# ──────────────────────────────────────────────────────────────
class TestIExecutorProtocol:
    def test_execute_in_protocol(self):
        assert hasattr(IExecutor, "execute")

    def test_send_interrupt_in_protocol(self):
        """ADR §6.4：send_interrupt 為新增 Protocol 方法。"""
        assert hasattr(IExecutor, "send_interrupt")
