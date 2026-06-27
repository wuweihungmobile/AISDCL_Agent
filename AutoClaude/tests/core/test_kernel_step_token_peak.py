"""Kernel per-step token% 可觀測標記測試（improving_86 W-86-1 / RTM-86-1/2）。

驗證意圖（Rule 9）：這組測試守的是「per-step token% 可觀測來源」——production Kernel 在
低負載真跑（未撞 80/90% 門檻）下，整輪只落一個 KernelResult.peak_token_pct，**沒有任何
逐步驟 token 訊號**，致 A/B 載具（tools/ab_compare_backends.py）per-step token% 恆 0%。
W-86-1 讓每 attempt 觀測到的真實 token%（peak>0 才印）逐步驟可觀測。缺此標記即 A/B 無法
量逐步驟 token；而 peak==0（dry-run/fake）時不可虛報 token → 不發標記（零退化）。
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


class _TokenEmittingExecutor:
    """測試用 IExecutor：每次 execute 依序回放一筆 token% 事件（pct=None → 不發事件）。"""

    def __init__(self, pcts: list[Optional[float]]):
        self._pcts = pcts
        self._i = 0

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        pct = self._pcts[self._i] if self._i < len(self._pcts) else None
        self._i += 1
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
        version="1.0", project="step-token-peak-test",
        global_invariants=GlobalInvariants(max_retries_per_step=2),
        tasks=[
            PlaybookTask(step_id=f"S{i:02d}", name="step", prompt="do")
            for i in range(1, n_steps + 1)
        ],
    )


def _kernel(executor) -> PlaybookKernel:
    return PlaybookKernel(executor, _PassEvaluator(), bus=EventBus())


def test_step_token_peak_marker_emitted_when_peak_positive(caplog):
    """RTM-86-1：peak>0 → 每步發 STEP_TOKEN_PEAK marker，帶該步 step_id 與真實 pct。"""
    executor = _TokenEmittingExecutor(pcts=[6.0, 12.5])  # S01=6%、S02=12.5%
    with caplog.at_level(logging.INFO, logger="autoclaude.core.kernel"):
        result = _kernel(executor).run(_pb(n_steps=2))

    assert result.success
    markers = [r.getMessage() for r in caplog.records if "STEP_TOKEN_PEAK" in r.getMessage()]
    assert len(markers) == 2
    # 標記須帶各步 step_id 與其真實 token%（per-step 歸因唯一來源）
    assert any("step=S01" in m and "6.0000" in m for m in markers)
    assert any("step=S02" in m and "12.5000" in m for m in markers)


def test_no_step_token_peak_marker_when_no_token_signal(caplog):
    """RTM-86-2：peak==0（dry-run/fake 無 token 訊號）→ 不發標記（零退化、不虛報 token）。"""
    executor = _TokenEmittingExecutor(pcts=[None])  # 不發 token 事件 → observer.peak_pct=0
    with caplog.at_level(logging.INFO, logger="autoclaude.core.kernel"):
        result = _kernel(executor).run(_pb(n_steps=1))

    assert result.success
    markers = [r for r in caplog.records if "STEP_TOKEN_PEAK" in r.getMessage()]
    assert markers == []
