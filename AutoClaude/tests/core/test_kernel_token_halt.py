"""Kernel production token-guard halt 接線測試（improving_78 W-78-1 / DEF-78-001 / RTM-78-2/4）。

驗證意圖（Rule 9）：這組測試守的是 DEF-78-001 的修復本質——production Kernel 路徑
必須真正把 executor 觀測到的 token% 餵給 token_guard，並在 ≥halt 門檻時 HALT + 印
真誠 TOKEN_HALT marker（供 A/B 載具計數）。同時守「無 token 訊號 → 不 emit → 零退化」
這個關鍵契約：若契約破壞，既有 3407 測試會因 ON_TOKEN_USAGE 誤觸發而行為漂移。

刻意使用**真 TokenGuardPlugin**（非 stub），驗證真實決策鏈（should_halt/should_compact）。
"""
from __future__ import annotations

import logging
from typing import Optional

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import (
    ExecutionEvent,
    ExecutionEventKind,
    ExecutionOutput,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin


class TokenEmittingExecutor:
    """測試用 IExecutor：execute 時經 on_event 發一筆 TOKEN_PCT 事件（模擬真實後端觀測）。"""

    def __init__(self, pct: Optional[float], text: str = "OK"):
        self._pct = pct
        self._text = text
        self.calls: list[str] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        self.calls.append(prompt)
        if on_event is not None and self._pct is not None:
            on_event(ExecutionEvent(
                kind=ExecutionEventKind.TOKEN_PCT,
                payload={"pct": self._pct}, sequence=1,
            ))
        return ExecutionOutput(text=self._text)


class _PassEvaluator:
    def evaluate(self, task, output):
        return None, "", 0


class _OnTokenUsageSpy:
    """純觀察者：記錄 ON_TOKEN_USAGE 是否被 emit（守零退化 no-emit 契約）。"""

    def __init__(self):
        self.fired = 0

    def name(self):
        return "on_token_usage_spy"

    def priority(self):
        return 999

    def subscribed_phases(self):
        return [KernelPhase.ON_TOKEN_USAGE]

    def on_event(self, ctx):
        self.fired += 1
        return None


def _pb() -> Playbook:
    return Playbook(
        version="1.0", project="token-halt-test",
        global_invariants=GlobalInvariants(max_retries_per_step=2),
        tasks=[PlaybookTask(step_id="T01", name="step", prompt="do")],
    )


def _kernel_with_token_guard(executor):
    bus = EventBus()
    bus.register(TokenGuardPlugin())  # 真 plugin，預設 compact=80 / halt=90 / enabled
    return PlaybookKernel(executor, _PassEvaluator(), bus=bus), bus


def test_high_token_pct_triggers_halt_and_marker(caplog):
    """≥90%（halt 門檻）→ Kernel HALT + 印真誠 TOKEN_HALT marker + 帶回 step_idx/peak。"""
    kernel, _ = _kernel_with_token_guard(TokenEmittingExecutor(pct=92.0))
    with caplog.at_level(logging.WARNING, logger="autoclaude.core.kernel"):
        result = kernel.run(_pb())
    assert result.halted is True
    assert result.halt_step_idx == 0
    assert result.peak_token_pct == 92.0
    assert "=== STATE: TOKEN_HALT" in caplog.text
    assert "[T01]" in caplog.text


def test_low_token_pct_no_halt_advances(caplog):
    """50%（低於 compact）→ 不 halt、步驟正常完成、無 TOKEN_HALT marker。"""
    kernel, _ = _kernel_with_token_guard(TokenEmittingExecutor(pct=50.0))
    with caplog.at_level(logging.WARNING, logger="autoclaude.core.kernel"):
        result = kernel.run(_pb())
    assert result.halted is False
    assert result.success is True
    assert "TOKEN_HALT" not in caplog.text


def test_compact_threshold_triggers_compact_not_halt(caplog):
    """85%（compact 區間，≥80 <90）→ token_guard 回 request_compact → Kernel 送 /compact +
    印 TOKEN_COMPACT marker（improving_79 W-78-2 已接線；compact 子路徑詳測見
    test_kernel_token_compact.py）。單次 compact 失敗未達 Gap-008-E 上限 → 不 halt、步驟完成。

    🔴 本測試於 improving_79 由「W-78-2 未接、Kernel 85% 不動作」更新為「W-78-2 已接、
    85% 觸發 compact」——反映 compact 子路徑接線後的真實行為（Rule 9 測試驗意圖）。"""
    kernel, _ = _kernel_with_token_guard(TokenEmittingExecutor(pct=85.0))
    with caplog.at_level(logging.INFO, logger="autoclaude.core.kernel"):
        result = kernel.run(_pb())
    assert result.halted is False
    assert result.success is True
    assert "=== STATE: TOKEN_COMPACT" in caplog.text  # W-78-2：85% 真送 /compact
    assert "TOKEN_HALT" not in caplog.text             # 單次失敗未達 Gap-008-E 上限


def test_no_token_event_does_not_emit_on_token_usage():
    """零退化契約：executor 不發 token 事件（peak=0）→ ON_TOKEN_USAGE 完全不 emit。"""
    bus = EventBus()
    bus.register(TokenGuardPlugin())
    spy = _OnTokenUsageSpy()
    bus.register(spy)
    kernel = PlaybookKernel(TokenEmittingExecutor(pct=None), _PassEvaluator(), bus=bus)
    result = kernel.run(_pb())
    assert result.success is True
    assert spy.fired == 0  # 無 token 訊號 → 不 emit ON_TOKEN_USAGE
