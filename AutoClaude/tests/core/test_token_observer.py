"""TokenObserver 單元測試（improving_78 W-78-1 / DEF-78-001 / RTM-78-1）。

驗證意圖（Rule 9）：Kernel 路徑的 token 觀測器須能從兩後端事件流正確追蹤 token% 峰值，
且「無 token 事件 → peak 0」這個零退化契約必須成立（否則 Kernel 會誤觸發 halt）。
"""
from __future__ import annotations

from autoclaude.core._token_observer import TokenObserver
from autoclaude.core.ports.executor import ExecutionEvent, ExecutionEventKind


def _ev(kind: str, payload: dict, seq: int = 1) -> ExecutionEvent:
    return ExecutionEvent(kind=kind, payload=payload, sequence=seq)


def test_observes_sdk_token_pct_events_tracks_peak():
    """SDK 後端：TOKEN_PCT 事件 {pct} → 追蹤最高水位（非最後值）。"""
    obs = TokenObserver()
    for pct in (50.0, 92.0, 80.0):
        obs(_ev(ExecutionEventKind.TOKEN_PCT, {"pct": pct}))
    assert obs.peak_pct == 92.0


def test_observes_pty_partial_output_context_pct():
    """PTY 後端：PARTIAL_OUTPUT 行文字 → 以 extract_context_pct 解析行內 context%。"""
    obs = TokenObserver()
    obs(_ev(ExecutionEventKind.PARTIAL_OUTPUT, {"text": "[CONTEXT_USAGE: 88%]"}))
    assert obs.peak_pct == 88.0


def test_no_events_peak_zero():
    """零退化契約：完全無事件 → peak 0.0（Kernel 不會誤觸發 halt）。"""
    obs = TokenObserver()
    assert obs.peak_pct == 0.0


def test_ignores_unrelated_event_kinds():
    """COMPLETION / TOOL_USE / PROGRESS 不影響 peak（非 token 訊號）。"""
    obs = TokenObserver()
    obs(_ev(ExecutionEventKind.COMPLETION, {"exit_code": 0, "completed": True}))
    obs(_ev(ExecutionEventKind.TOOL_USE, {"tool": "Read", "args": {}}))
    obs(_ev(ExecutionEventKind.PROGRESS, {"step": 1, "total": 2}))
    assert obs.peak_pct == 0.0


def test_partial_output_without_pct_no_change():
    """PARTIAL_OUTPUT 無 context% 行文字 → peak 不變（解析回 None）。"""
    obs = TokenObserver()
    obs(_ev(ExecutionEventKind.PARTIAL_OUTPUT, {"text": "hello world, no percentage here"}))
    assert obs.peak_pct == 0.0


def test_token_pct_none_payload_no_crash():
    """TOKEN_PCT 但 pct 缺失 → 安全略過、不崩。"""
    obs = TokenObserver()
    obs(_ev(ExecutionEventKind.TOKEN_PCT, {}))
    assert obs.peak_pct == 0.0
