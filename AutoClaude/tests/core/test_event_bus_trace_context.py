"""SD_Improving_08 W4：EventBus 自動注入 trace_id（ADR-SD08-004 §2.3）。

測試 EventBus.emit 從 ContextVar 自動讀取 trace_id 作為 fallback：
  1. ctx.payload["_trace_id"] 顯式 → 採用顯式（向後相容）
  2. 無顯式 + with_trace_id() → 採用 ContextVar
  3. 無顯式 + 無 ContextVar → 自動 uuid 生成
"""
from __future__ import annotations

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.models.playbook import GlobalInvariants, Playbook
from autoclaude.utils.trace_context import with_trace_id


def _stub_playbook() -> Playbook:
    return Playbook(
        version="1.0",
        project="test",
        global_invariants=GlobalInvariants(),
        tasks=[],
    )


def test_explicit_trace_id_in_payload_takes_priority():
    bus = EventBus()
    ctx = HookContext(
        phase=KernelPhase.PRE_RUN,
        playbook=_stub_playbook(),
        payload={"_trace_id": "explicit-trace"},
    )
    bus.emit(ctx)
    assert bus.last_trace_id() == "explicit-trace"


def test_context_var_trace_id_used_when_no_explicit():
    bus = EventBus()
    ctx = HookContext(
        phase=KernelPhase.PRE_RUN,
        playbook=_stub_playbook(),
        payload={},
    )
    with with_trace_id("ctx-var-trace"):
        bus.emit(ctx)
    assert bus.last_trace_id() == "ctx-var-trace"


def test_auto_uuid_fallback_when_neither_explicit_nor_context_var():
    bus = EventBus()
    ctx = HookContext(
        phase=KernelPhase.PRE_RUN,
        playbook=_stub_playbook(),
        payload={},
    )
    bus.emit(ctx)
    # uuid4().hex[:12] = 12 字 hex
    tid = bus.last_trace_id()
    assert tid is not None
    assert len(tid) == 12
    assert all(c in "0123456789abcdef" for c in tid)
