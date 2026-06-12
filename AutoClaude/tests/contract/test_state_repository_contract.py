"""IStateRepository 契約測（SD_Improving_01.md v1.1 §3.9 / SD_Improving_02.md v1.1 §2.7）。

採 abstract base class 強制所有 IStateRepository 實作通過同一組行為驗證。
任何新後端（File / InMemory / Phase 6 PG）必須繼承 IStateRepositoryContract
並實作 _make_repo()，否則 CI 阻擋合併。

≥ 7 個契約測（v1.1 §3.9 必測）:
  1. test_save_load_roundtrip
  2. test_load_missing_returns_none
  3. test_clear_idempotent
  4. test_counter_persistence_round_trip   (Gap-042 / Gap-048)
  5. test_failure_history_round_trip       (Gap-007-A)
  6. test_schedule_resume_sets_iso_timestamp
  7. test_overwrite_preserves_atomicity
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pytest

from autoclaude.infra.repositories import (
    FileStateRepository,
    InMemoryStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint


def _make_sample_checkpoint(**overrides) -> PlaybookCheckpoint:
    defaults = dict(
        playbook_path="x.yaml",
        step_idx=2,
        step_id="T03",
        total_steps=5,
        project="contract-test",
        completed_step_log=["[OK] T01", "[OK] T02"],
        peak_token_pct=42.5,
        completed_step_ids=["T01", "T02"],
        goto_counter={"T01": 2, "T03": 1},
        inject_before_counter={"T02": 1},
        skip_to_counter={"T04": 3},
        step_evolution_counter={"T05": 2, "T06": 1},
        failure_history=[{"attempt": 0, "reason": "regex miss"}],
        active_step_attempt=1,
        last_correction_prompt="please retry",
    )
    defaults.update(overrides)
    return PlaybookCheckpoint(**defaults)


class IStateRepositoryContract(ABC):
    """所有 IStateRepository 實作必通過的共同行為（LSP 驗證）。"""

    @abstractmethod
    def _make_repo(self, tmp_path: Path):
        ...

    def test_save_load_roundtrip(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        cp = _make_sample_checkpoint()
        repo.save_checkpoint("pb_001", cp)
        loaded = repo.load_checkpoint("pb_001")
        assert loaded is not None
        assert loaded.step_id == cp.step_id
        assert loaded.step_idx == cp.step_idx
        assert loaded.completed_step_ids == cp.completed_step_ids

    def test_load_missing_returns_none(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        assert repo.load_checkpoint("nonexistent_id") is None

    def test_clear_idempotent(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        repo.clear_checkpoint("pb_001")  # 不存在也不應拋例外
        repo.save_checkpoint("pb_001", _make_sample_checkpoint())
        repo.clear_checkpoint("pb_001")
        repo.clear_checkpoint("pb_001")  # 重複 clear 仍 idempotent
        assert repo.load_checkpoint("pb_001") is None

    def test_counter_persistence_round_trip(self, tmp_path: Path):
        """Gap-042 / Gap-048：4 個跨 Session 計數器須完整保留。"""
        repo = self._make_repo(tmp_path)
        cp = _make_sample_checkpoint(
            goto_counter={"T01": 5, "T03": 2},
            inject_before_counter={"T02": 1},
            skip_to_counter={"T04": 3, "T07": 1},
            step_evolution_counter={"T05": 2, "T06": 1, "T09": 4},
        )
        repo.save_checkpoint("pb_002", cp)
        loaded = repo.load_checkpoint("pb_002")
        assert loaded.goto_counter == cp.goto_counter
        assert loaded.inject_before_counter == cp.inject_before_counter
        assert loaded.skip_to_counter == cp.skip_to_counter
        assert loaded.step_evolution_counter == cp.step_evolution_counter

    def test_failure_history_round_trip(self, tmp_path: Path):
        """Gap-007-A：FailureTracker 歷史跨 Session 持久化。"""
        repo = self._make_repo(tmp_path)
        cp = _make_sample_checkpoint(
            failure_history=[
                {"attempt": 0, "reason": "regex miss"},
                {"attempt": 1, "reason": "syntax error"},
            ],
            active_step_attempt=2,
            last_correction_prompt="apply hint",
        )
        repo.save_checkpoint("pb_003", cp)
        loaded = repo.load_checkpoint("pb_003")
        assert loaded.failure_history == cp.failure_history
        assert loaded.active_step_attempt == 2
        assert loaded.last_correction_prompt == "apply hint"

    def test_schedule_resume_sets_iso_timestamp(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        repo.save_checkpoint("pb_004", _make_sample_checkpoint())
        resume_at = repo.schedule_resume("pb_004", delay_minutes=5)
        assert isinstance(resume_at, datetime)
        loaded = repo.load_checkpoint("pb_004")
        assert loaded.scheduled_resume_at is not None
        # 確認可被解析為 ISO 8601
        datetime.fromisoformat(loaded.scheduled_resume_at)

    def test_overwrite_preserves_atomicity(self, tmp_path: Path):
        """先 save 一次，再 save 一次（不同內容），讀取應為最新版。"""
        repo = self._make_repo(tmp_path)
        cp1 = _make_sample_checkpoint(step_idx=0, step_id="T01")
        cp2 = _make_sample_checkpoint(step_idx=4, step_id="T05")
        repo.save_checkpoint("pb_005", cp1)
        repo.save_checkpoint("pb_005", cp2)
        loaded = repo.load_checkpoint("pb_005")
        assert loaded.step_idx == 4
        assert loaded.step_id == "T05"


# ──────────────────────────────────────────────
# 具體後端繼承（PG backend 留待 Phase 6 加入）
# ──────────────────────────────────────────────
class TestFileStateRepositoryContract(IStateRepositoryContract):
    def _make_repo(self, tmp_path: Path):
        return FileStateRepository(checkpoint_dir=str(tmp_path))


class TestInMemoryStateRepositoryContract(IStateRepositoryContract):
    def _make_repo(self, tmp_path: Path):
        return InMemoryStateRepository()
