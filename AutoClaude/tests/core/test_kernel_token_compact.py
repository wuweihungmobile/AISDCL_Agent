"""Kernel production token-guard compact 接線測試（improving_79 W-78-2 / DEF-78-001 / RTM-79-2/3）。

驗證意圖（Rule 9）：這組測試守的是 DEF-78-001 的 compact 子路徑修復本質——production Kernel
路徑在 ≥80% compact 門檻時必須真正送 /compact（印真誠 TOKEN_COMPACT marker 供 A/B 載具計
compact_count），且完整移植 Gap-008-E：連續 compact 失敗（壓不下來）達上限 → 強制 HALT，
否則 token 失控時 compact 區間（80~90%）無安全網。

刻意使用**真 TokenGuardPlugin**（非 stub），驗證 should_compact / CompactFailureState（SSOT
在 plugin）/ POST_COMPACT 決策鏈，確認非偽造 marker、而是真接線。
"""
from __future__ import annotations

import logging
from typing import Optional

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import (
    ExecutionEvent,
    ExecutionEventKind,
    ExecutionOutput,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin


class SequencedTokenExecutor:
    """測試用 IExecutor：每次 execute 依序回放一筆 token% 事件。

    這讓我們能分別控制「步驟執行」與其後「/compact 執行」觀測到的 token%，
    模擬 compact 成功（壓下來）或失敗（仍高）。pct=None → 不發事件（peak 0）。
    """

    def __init__(self, pcts: list[Optional[float]]):
        self._pcts = pcts
        self._i = 0
        self.calls: list[dict] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        pct = self._pcts[self._i] if self._i < len(self._pcts) else None
        self._i += 1
        self.calls.append({"prompt": prompt, "label": label})
        if on_event is not None and pct is not None:
            on_event(ExecutionEvent(
                kind=ExecutionEventKind.TOKEN_PCT, payload={"pct": pct}, sequence=1,
            ))
        return ExecutionOutput(text="OK")


class _PassEvaluator:
    def evaluate(self, task, output):
        return None, "", 0


def _pb(n_steps: int = 1) -> Playbook:
    return Playbook(
        version="1.0", project="token-compact-test",
        global_invariants=GlobalInvariants(max_retries_per_step=2),
        tasks=[
            PlaybookTask(step_id=f"T{i:02d}", name="step", prompt="do")
            for i in range(1, n_steps + 1)
        ],
    )


def _kernel(executor):
    bus = EventBus()
    bus.register(TokenGuardPlugin())  # 真 plugin（compact=80 / halt=90 / critical=2）
    return PlaybookKernel(executor, _PassEvaluator(), bus=bus)


def test_compact_threshold_sends_compact_and_marker(caplog):
    """RTM-79-2：85%（compact 區間）→ Kernel 送 /compact + 印真誠 TOKEN_COMPACT marker；
    compact 後降到 50%（成功）→ 不 halt、步驟正常完成、續評估原 output。"""
    executor = SequencedTokenExecutor(pcts=[85.0, 50.0])  # 步驟 85% → 觸發 compact；compact 後 50%
    kernel = _kernel(executor)
    with caplog.at_level(logging.INFO, logger="autoclaude.core.kernel"):
        result = kernel.run(_pb())
    assert result.halted is False
    assert result.success is True
    # 真送 /compact：兩次 execute（步驟 + compact），且 compact 那次 label 標 _compact
    assert len(executor.calls) == 2
    assert executor.calls[1]["label"] == "T01_compact"
    assert executor.calls[1]["prompt"].startswith("/compact")
    # 真誠 marker（載具計數依此）
    assert "=== STATE: TOKEN_COMPACT" in caplog.text
    assert "[T01]" in caplog.text
    assert "TOKEN_HALT" not in caplog.text


def test_single_compact_failure_does_not_halt(caplog):
    """單次 compact 失敗（compact 後仍 85%）→ 記 1 次失敗，未達 Gap-008-E 上限 → 不 halt。"""
    executor = SequencedTokenExecutor(pcts=[85.0, 85.0])  # compact 後仍高 = 失敗 1 次
    kernel = _kernel(executor)
    with caplog.at_level(logging.WARNING, logger="autoclaude.core.kernel"):
        result = kernel.run(_pb())
    assert result.halted is False
    assert result.success is True
    assert "TOKEN_HALT" not in caplog.text


def test_consecutive_compact_failures_trigger_gap008e_halt(caplog):
    """RTM-79-3：連續兩步 compact 皆失敗（壓不下來）→ 第 2 次達上限 → Gap-008-E 強制 HALT。

    CompactFailureState（SSOT 在 plugin）跨步驟累計：step1 compact 失敗 count=1（不 halt、
    步驟通過），step2 compact 失敗 count=2 → critical → request_halt → Kernel HALT at step 2。"""
    # 步驟1=85 → compact=85（失敗）；步驟2=85 → compact=88（失敗，達上限）
    executor = SequencedTokenExecutor(pcts=[85.0, 85.0, 85.0, 88.0])
    kernel = _kernel(executor)
    with caplog.at_level(logging.WARNING, logger="autoclaude.core.kernel"):
        result = kernel.run(_pb(n_steps=2))
    assert result.halted is True
    assert result.halt_step_idx == 1          # 第 2 步（idx=1）觸發 Gap-008-E
    assert result.peak_token_pct == 88.0      # max(觸發峰值, compact 後峰值)
    assert "=== STATE: TOKEN_HALT" in caplog.text
    assert "Gap-008-E" in caplog.text


def test_no_token_event_no_compact():
    """零退化契約：executor 不發 token 事件（peak=0）→ 不 emit、不 compact、步驟正常完成。"""
    executor = SequencedTokenExecutor(pcts=[None])
    kernel = _kernel(executor)
    result = kernel.run(_pb())
    assert result.success is True
    assert len(executor.calls) == 1  # 只有步驟 execute，無 /compact
