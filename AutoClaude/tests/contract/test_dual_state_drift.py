"""SD_06 W5-T5-6：DualStateRepository.detect_drift contract test。

對應規格：
  - SD_Improving_06.md §6.5 AC5-2（dual_state drift 全欄比對）
  - SD06_Execution_Guide.md W5 T5-6：≥ 4 case
  - autoclaude/infra/repositories/dual_state_repository.py（DriftReport + detect_drift）

不變式：
  1. 兩個完全相同的 checkpoint → has_drift=False, severity='info'
  2. step_idx / total_steps / completed_step_ids 不同 → severity='critical'
  3. 僅 saved_at 等非關鍵欄位不同 → severity='warn'
  4. drift_observer 在 fail_loud 模式下被呼叫
  5. PG-first 模式 File 失敗 → reconcile queue 累積
"""
from __future__ import annotations

from typing import Optional

import pytest

from autoclaude.infra.repositories.dual_state_repository import (
    DriftReport,
    DualStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint


class _FakeRepo:
    """記憶體假 repository，可注入失敗。"""

    def __init__(self, *, fail_save: bool = False, fail_load: bool = False):
        self.store: dict[str, PlaybookCheckpoint] = {}
        self.fail_save = fail_save
        self.fail_load = fail_load
        self.save_calls = 0
        self.load_calls = 0

    def save_checkpoint(self, playbook_id: str, cp: PlaybookCheckpoint) -> None:
        self.save_calls += 1
        if self.fail_save:
            raise RuntimeError("simulated save failure")
        self.store[playbook_id] = cp

    def load_checkpoint(self, playbook_id: str) -> Optional[PlaybookCheckpoint]:
        return self.load_latest_by_playbook(playbook_id)

    def load_latest_by_playbook(self, playbook_id: str) -> Optional[PlaybookCheckpoint]:
        self.load_calls += 1
        if self.fail_load:
            raise RuntimeError("simulated load failure")
        return self.store.get(playbook_id)

    def load_by_run_id(self, run_id: str) -> Optional[PlaybookCheckpoint]:
        for cp in self.store.values():
            if getattr(cp, "run_id", None) == run_id:
                return cp
        return None

    def clear_checkpoint(self, playbook_id: str) -> None:
        self.store.pop(playbook_id, None)

    def schedule_resume(self, playbook_id: str, delay_minutes: int):
        from datetime import datetime, timedelta
        return datetime.now() + timedelta(minutes=delay_minutes)


def _cp(step_idx: int = 0, *, total_steps: int = 3,
        completed: Optional[list[str]] = None,
        peak: float = 0.0) -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path="p",
        step_idx=step_idx,
        step_id=f"T{step_idx:02d}",
        total_steps=total_steps,
        project="proj",
        completed_step_log=[],
        peak_token_pct=peak,
        completed_step_ids=completed or [],
    )


# ──────────────────────────────────────────────
# Case 1：相同 checkpoint 不報 drift
# ──────────────────────────────────────────────
def test_detect_drift_identical_no_drift():
    primary = _FakeRepo()
    shadow = _FakeRepo()
    dual = DualStateRepository(primary, shadow)
    cp = _cp(step_idx=2, completed=["T00", "T01"])
    report = dual.detect_drift("pb", cp, cp)
    assert report.has_drift is False
    assert report.severity == "info"
    assert report.field_drift == {}


# ──────────────────────────────────────────────
# Case 2：step_idx 不同 → critical
# ──────────────────────────────────────────────
def test_detect_drift_step_idx_diff_critical():
    primary = _FakeRepo()
    shadow = _FakeRepo()
    dual = DualStateRepository(primary, shadow)
    left = _cp(step_idx=2, completed=["T00", "T01"])
    right = _cp(step_idx=3, completed=["T00", "T01", "T02"])
    report = dual.detect_drift("pb", left, right)
    assert report.has_drift is True
    assert report.severity == "critical"
    assert "step_idx" in report.field_drift
    assert report.field_drift["step_idx"] == {"left": 2, "right": 3}
    assert "completed_step_ids" in report.field_drift


# ──────────────────────────────────────────────
# Case 3：僅 saved_at 不同 → warn（非 critical 欄位）
# ──────────────────────────────────────────────
def test_detect_drift_saved_at_only_warn():
    primary = _FakeRepo()
    shadow = _FakeRepo()
    dual = DualStateRepository(primary, shadow)
    left = _cp(step_idx=1)
    right = _cp(step_idx=1)
    right.saved_at = "2026-05-17T20:00:00"
    left.saved_at = "2026-05-17T18:30:00"
    report = dual.detect_drift("pb", left, right)
    assert report.has_drift is True
    assert report.severity == "warn"
    assert "saved_at" in report.field_drift
    assert "step_idx" not in report.field_drift


# ──────────────────────────────────────────────
# Case 4：fail_loud 模式下 drift_observer 被呼叫並 raise
# ──────────────────────────────────────────────
def test_fail_loud_invokes_drift_observer_and_raises():
    primary = _FakeRepo()
    shadow = _FakeRepo()
    captured: list[DriftReport] = []

    def observer(report: DriftReport) -> None:
        captured.append(report)

    dual = DualStateRepository(
        primary, shadow,
        read_resolution="fail_loud",
        drift_observer=observer,
    )
    primary.store["pb"] = _cp(step_idx=2, completed=["T00", "T01"])
    shadow.store["pb"] = _cp(step_idx=3, completed=["T00", "T01", "T02"])

    with pytest.raises(RuntimeError, match="drift detected"):
        dual.load_checkpoint("pb")

    assert len(captured) == 1
    assert captured[0].severity == "critical"
    assert "step_idx" in captured[0].field_drift
    assert dual.metrics.shadow_drift_detected == 1


# ──────────────────────────────────────────────
# Case 5：fail_loud 模式下完全相同 → 不 raise，回傳 primary
# ──────────────────────────────────────────────
def test_fail_loud_identical_returns_primary():
    primary = _FakeRepo()
    shadow = _FakeRepo()
    dual = DualStateRepository(primary, shadow, read_resolution="fail_loud")
    cp = _cp(step_idx=1)
    primary.store["pb"] = cp
    shadow.store["pb"] = _cp(step_idx=1)  # 結構相同
    result = dual.load_checkpoint("pb")
    assert result is not None
    assert result.step_idx == 1


# ──────────────────────────────────────────────
# Case 6：PG-first 模式下 File 寫入失敗 → 排入 reconcile queue
# ──────────────────────────────────────────────
def test_pg_first_file_failure_queues_reconcile():
    primary = _FakeRepo(fail_save=True)
    shadow = _FakeRepo()
    dual = DualStateRepository(
        primary, shadow, dual_write_mode="pg_first", strict=False,
    )
    cp = _cp(step_idx=1)
    dual.save_checkpoint("pb", cp)
    assert dual.metrics.dual_write_failure == 1
    assert dual.metrics.reconcile_queued == 1
    assert len(dual.reconcile_queue) == 1
    assert dual.reconcile_queue[0][0] == "pb"
    # shadow 已寫入
    assert "pb" in shadow.store


# ──────────────────────────────────────────────
# Case 7：drain_reconcile_queue 補寫成功後清空
# ──────────────────────────────────────────────
def test_drain_reconcile_queue_succeeds_when_recovered():
    primary = _FakeRepo(fail_save=True)
    shadow = _FakeRepo()
    dual = DualStateRepository(primary, shadow, dual_write_mode="pg_first")
    cp = _cp(step_idx=2)
    dual.save_checkpoint("pb", cp)
    assert len(dual.reconcile_queue) == 1
    primary.fail_save = False  # 模擬 File 恢復
    succeeded = dual.drain_reconcile_queue()
    assert succeeded == 1
    assert len(dual.reconcile_queue) == 0
    assert "pb" in primary.store


# ──────────────────────────────────────────────
# Case 8：相同 ISO 字串不應視為 drift（PlaybookCheckpoint 內已以 string 保存）
# ──────────────────────────────────────────────
def test_detect_drift_identical_iso_strings_no_drift():
    primary = _FakeRepo()
    shadow = _FakeRepo()
    dual = DualStateRepository(primary, shadow)
    left = _cp(step_idx=1)
    right = _cp(step_idx=1)
    left.scheduled_resume_at = "2026-05-17T12:30:00"
    right.scheduled_resume_at = "2026-05-17T12:30:00"
    report = dual.detect_drift("pb", left, right)
    assert "scheduled_resume_at" not in report.field_drift
    assert report.has_drift is False


# ──────────────────────────────────────────────
# Case 9：DriftReport.to_dict() 為純資料 dict
# ──────────────────────────────────────────────
def test_drift_report_to_dict_round_trip():
    report = DriftReport(
        playbook_id="pb",
        source_left="file",
        source_right="pg",
        field_drift={"step_idx": {"left": 1, "right": 2}},
        severity="critical",
    )
    d = report.to_dict()
    assert d["playbook_id"] == "pb"
    assert d["source_left"] == "file"
    assert d["severity"] == "critical"
    assert d["field_drift"] == {"step_idx": {"left": 1, "right": 2}}
    # 純資料 → json 可序列化
    import json
    json.dumps(d)
