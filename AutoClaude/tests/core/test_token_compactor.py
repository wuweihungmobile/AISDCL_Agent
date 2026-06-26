"""perform_compact 單元測試（improving_79 W-78-2 / DEF-78-001 / RTM-79-1）。

驗證意圖（Rule 9）：production Kernel 路徑的 compact 動作 helper 必須——
  (1) 印真誠 TOKEN_COMPACT marker（含 [Sxx] 與 NN%），否則 A/B 載具無法計 compact_count；
  (2) 真正送 /compact 給 executor（含結構化保留提示），否則 context 不會被壓縮；
  (3) 以 fresh observer 回傳 compact 後真實 peak，供 Gap-008-E 連續失敗判定；
  (4) executor 無 token 事件時回 0.0（零退化契約）。
這些是 compact 子路徑「真接線、非偽造 marker」的核心保證。
"""
from __future__ import annotations

import logging

from autoclaude.core._token_compactor import perform_compact
from autoclaude.core.ports.executor import (
    ExecutionEvent,
    ExecutionEventKind,
    ExecutionOutput,
)


class _FakeExecutor:
    """記錄 execute 呼叫；可選擇性地對 on_event 回放 token% 事件模擬 compact 後峰值。"""

    def __init__(self, emit_pcts: list[float] | None = None):
        self._emit_pcts = emit_pcts or []
        self.calls: list[dict] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="",
                on_event=None):
        self.calls.append({
            "prompt": prompt, "maintain_context": maintain_context,
            "timeout": timeout, "label": label,
        })
        for i, pct in enumerate(self._emit_pcts):
            if on_event is not None:
                on_event(ExecutionEvent(
                    kind=ExecutionEventKind.TOKEN_PCT, payload={"pct": pct}, sequence=i,
                ))
        return ExecutionOutput(text="[compacted]", exit_code=0, completed=True)

    def send_interrupt(self, reason: str = "") -> bool:
        return False


def test_prints_honest_compact_marker(caplog):
    """印 TOKEN_COMPACT marker，含 step_id [Sxx] 與觸發峰值 NN%（載具計數/歸因依此）。"""
    exec_ = _FakeExecutor()
    with caplog.at_level(logging.INFO, logger="autoclaude.core.kernel"):
        perform_compact(exec_, step_id="S03", peak_pct=85.0)
    marker_lines = [r.getMessage() for r in caplog.records if "TOKEN_COMPACT" in r.getMessage()]
    assert len(marker_lines) == 1
    assert "[S03]" in marker_lines[0]
    assert "85%" in marker_lines[0]


def test_sends_compact_command_to_executor():
    """真正送 /compact prompt（含結構化保留提示）給 executor，label 標 compact。"""
    exec_ = _FakeExecutor()
    perform_compact(exec_, step_id="S01", peak_pct=82.0)
    assert len(exec_.calls) == 1
    call = exec_.calls[0]
    assert call["prompt"].startswith("/compact")
    assert "優先保留" in call["prompt"]
    assert call["label"] == "S01_compact"
    assert call["maintain_context"] is True


def test_returns_post_compact_peak_from_fresh_observer():
    """compact 執行期間 executor 發 token% 事件 → 回傳觀測到的最高水位。"""
    exec_ = _FakeExecutor(emit_pcts=[70.0, 91.0, 60.0])
    post_peak = perform_compact(exec_, step_id="S02", peak_pct=85.0)
    assert post_peak == 91.0


def test_no_token_events_returns_zero():
    """零退化契約：compact 後無 token 訊號 → 回 0.0（不會誤判為連續失敗）。"""
    exec_ = _FakeExecutor(emit_pcts=[])
    post_peak = perform_compact(exec_, step_id="S04", peak_pct=80.0)
    assert post_peak == 0.0
