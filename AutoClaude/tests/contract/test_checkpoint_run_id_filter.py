"""SD_06 W5-T5-9：load_by_run_id / load_latest_by_playbook 雙 API contract test。

對應規格：
  - SD_Improving_06.md §6.5 AC5-3（run_id 過濾 checkpoint）
  - SD06_Execution_Guide.md W5 T5-9：≥ 3 case
  - autoclaude/core/ports/state_repository.py（IStateRepository port 擴增）

驗證不變式：
  1. load_latest_by_playbook(pb) 回傳同 playbook_id 最新一筆 cp
  2. load_by_run_id(run_id) 只回傳對應 run_id 的 cp
  3. load_checkpoint(playbook_id) 保留為 alias，行為等同 load_latest_by_playbook
  4. AUTOCLAUDE_DEPRECATION_WARN=1 時 load_checkpoint 觸發 DeprecationWarning
  5. FileStateRepository / InMemoryStateRepository / DualStateRepository 行為一致
"""
from __future__ import annotations

import os
import warnings
from pathlib import Path

import pytest

from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.infra.repositories.in_memory_state_repository import InMemoryStateRepository
from autoclaude.infra.repositories.dual_state_repository import DualStateRepository
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint


def _cp(playbook_path="p", step_idx=0, run_id=None, goal_task_id=None):
    return PlaybookCheckpoint(
        playbook_path=playbook_path,
        step_idx=step_idx,
        step_id=f"T{step_idx:02d}",
        total_steps=3,
        run_id=run_id,
        goal_task_id=goal_task_id,
    )


# ──────────────────────────────────────────────
# Case 1：FileStateRepository — load_latest_by_playbook 回傳 latest
# ──────────────────────────────────────────────
def test_file_load_latest_by_playbook(tmp_path: Path):
    repo = FileStateRepository(str(tmp_path))
    cp = _cp(step_idx=3, run_id="r1")
    repo.save_checkpoint("pb1", cp)
    loaded = repo.load_latest_by_playbook("pb1")
    assert loaded is not None
    assert loaded.step_idx == 3
    assert loaded.run_id == "r1"


# ──────────────────────────────────────────────
# Case 2：FileStateRepository — load_by_run_id 過濾
# ──────────────────────────────────────────────
def test_file_load_by_run_id_filter(tmp_path: Path):
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb1", _cp(step_idx=1, run_id="r1"))
    repo.save_checkpoint("pb2", _cp(step_idx=2, run_id="r2"))
    repo.save_checkpoint("pb3", _cp(step_idx=3, run_id="r3"))

    cp = repo.load_by_run_id("r2")
    assert cp is not None
    assert cp.step_idx == 2
    assert cp.run_id == "r2"

    # 找不到 → None
    assert repo.load_by_run_id("r_not_exist") is None
    assert repo.load_by_run_id("") is None


# ──────────────────────────────────────────────
# Case 3：load_checkpoint 為 deprecated alias，行為等同 load_latest_by_playbook
# ──────────────────────────────────────────────
def test_file_load_checkpoint_is_deprecated_alias(tmp_path: Path):
    repo = FileStateRepository(str(tmp_path))
    cp = _cp(step_idx=5, run_id="r5")
    repo.save_checkpoint("pb1", cp)

    # 不設環境變數 → 不 emit warning
    loaded1 = repo.load_checkpoint("pb1")
    loaded2 = repo.load_latest_by_playbook("pb1")
    assert loaded1 is not None and loaded2 is not None
    assert loaded1.step_idx == loaded2.step_idx == 5
    assert loaded1.run_id == loaded2.run_id == "r5"


# ──────────────────────────────────────────────
# Case 4：AUTOCLAUDE_DEPRECATION_WARN=1 時 load_checkpoint emit DeprecationWarning
# ──────────────────────────────────────────────
def test_load_checkpoint_emits_deprecation_warning_when_env_set(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("AUTOCLAUDE_DEPRECATION_WARN", "1")
    repo = FileStateRepository(str(tmp_path))
    repo.save_checkpoint("pb1", _cp())
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        repo.load_checkpoint("pb1")
    matches = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(matches) >= 1
    assert "load_latest_by_playbook" in str(matches[0].message)


# ──────────────────────────────────────────────
# Case 5：InMemoryStateRepository 雙 API 行為一致
# ──────────────────────────────────────────────
def test_inmem_load_by_run_id_and_latest():
    repo = InMemoryStateRepository()
    repo.save_checkpoint("pb1", _cp(step_idx=1, run_id="r1"))
    repo.save_checkpoint("pb2", _cp(step_idx=2, run_id="r2"))

    assert repo.load_latest_by_playbook("pb1").step_idx == 1
    assert repo.load_by_run_id("r2").step_idx == 2
    assert repo.load_by_run_id("r_missing") is None


# ──────────────────────────────────────────────
# Case 6：DualStateRepository load_by_run_id 委派至 primary，primary 缺失回退 shadow
# ──────────────────────────────────────────────
def test_dual_load_by_run_id_primary_fallback_shadow():
    from tests.contract.test_dual_state_drift import _FakeRepo
    primary = _FakeRepo()
    shadow = _FakeRepo()
    # 模擬：primary 沒有；shadow 有
    shadow.store["pb_x"] = _cp(step_idx=9, run_id="r_x")

    # _FakeRepo 沒有 load_by_run_id，需提供 fallback
    def _shadow_by_run_id(rid):
        for cp in shadow.store.values():
            if cp.run_id == rid:
                return cp
        return None
    shadow.load_by_run_id = _shadow_by_run_id  # type: ignore[attr-defined]

    dual = DualStateRepository(primary, shadow)
    result = dual.load_by_run_id("r_x")
    assert result is not None
    assert result.step_idx == 9


# ──────────────────────────────────────────────
# Case 7：DualStateRepository load_latest_by_playbook yaml_wins primary
# ──────────────────────────────────────────────
def test_dual_load_latest_yaml_wins():
    from tests.contract.test_dual_state_drift import _FakeRepo
    primary = _FakeRepo()
    shadow = _FakeRepo()
    primary.store["pb1"] = _cp(step_idx=1)
    shadow.store["pb1"] = _cp(step_idx=2)  # PG 較新（理論上不該發生）

    dual = DualStateRepository(primary, shadow, read_resolution="yaml_wins")
    result = dual.load_latest_by_playbook("pb1")
    assert result is not None
    assert result.step_idx == 1  # yaml_wins → 採 primary


# ──────────────────────────────────────────────
# Case 8：PlaybookCheckpoint.run_id / goal_task_id 預設為 None（向後相容）
# ──────────────────────────────────────────────
def test_playbook_checkpoint_run_id_defaults_none():
    cp = PlaybookCheckpoint(
        playbook_path="p", step_idx=0, step_id="T00", total_steps=1,
    )
    assert cp.run_id is None
    assert cp.goal_task_id is None
