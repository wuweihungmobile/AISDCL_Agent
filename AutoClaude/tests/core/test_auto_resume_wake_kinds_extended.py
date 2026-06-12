"""SD_Improving_08 W4 / T4-F12：AutoResumeMetrics wake_kinds 擴展測試。

覆蓋：
  - 新增 wake_kinds: "esc_f12" + "manual"（覆蓋 HotkeyPlugin + CLI 觸發場景）
  - 新增計數欄位: esc_f12_resumes + manual_resumes
  - snapshot 包含新欄位
  - 非法 kind 仍 raise ValueError
"""
from __future__ import annotations

import pytest

from autoclaude.core.services._auto_resume_metrics import (
    AutoResumeMetrics,
    record_wake_and_emit,
)


def test_metrics_initialize_with_new_wake_kind_counters():
    m = AutoResumeMetrics()
    assert m.esc_f12_resumes == 0
    assert m.manual_resumes == 0
    snap = m.snapshot()
    assert "esc_f12_resumes" in snap
    assert "manual_resumes" in snap


def test_record_wake_esc_f12_accumulates():
    m = AutoResumeMetrics()
    record_wake_and_emit(
        m, bus=None,
        kind="esc_f12", scheduled_at=None, wait_secs=0.0,
    )
    assert m.esc_f12_resumes == 1
    assert m.total_wakes == 1
    assert "esc_f12" in m.wake_kinds


def test_record_wake_manual_accumulates():
    m = AutoResumeMetrics()
    record_wake_and_emit(
        m, bus=None,
        kind="manual", scheduled_at=None, wait_secs=0.0,
    )
    assert m.manual_resumes == 1
    assert m.total_wakes == 1
    assert "manual" in m.wake_kinds


def test_unknown_wake_kind_still_raises_value_error():
    """確認 backward compat：未知 kind 仍 raise ValueError（M-SA2）。"""
    m = AutoResumeMetrics()
    with pytest.raises(ValueError, match="不支援的 kind"):
        record_wake_and_emit(
            m, bus=None,
            kind="bogus_kind", scheduled_at=None, wait_secs=0.0,
        )


def test_snapshot_includes_all_five_wake_kinds():
    m = AutoResumeMetrics()
    for k in ["halt", "evolution", "checkpoint_resume", "esc_f12", "manual"]:
        record_wake_and_emit(m, bus=None, kind=k, scheduled_at=None, wait_secs=0.0)
    snap = m.snapshot()
    assert snap["total_wakes"] == 5
    assert snap["halt_resumes"] == 1
    assert snap["evolution_restarts"] == 1
    assert snap["checkpoint_resumes"] == 1
    assert snap["esc_f12_resumes"] == 1
    assert snap["manual_resumes"] == 1
    assert list(snap["wake_kinds"]) == [
        "halt", "evolution", "checkpoint_resume", "esc_f12", "manual",
    ]
