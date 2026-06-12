"""W1b DoD：CheckpointManager 反向委派 6 個 API 契約測試（SD_03 §3.1）。

驗證 CheckpointManager 已成為 FileStateRepository 的薄包裝器：
  1. save() 透過委派成功寫入 + 可 load 回讀
  2. load() 回傳正確資料或 None
  3. clear() 委派後檔案消失（idempotent）
  4. checkpoint_path() stem 轉換正確
  5. exists() 反映實際檔案狀態
  6. schedule_resume() 向後相容 in-place mutate + 回傳 future datetime
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint


def _make_cp(playbook_path: str = "scripts/test.yaml") -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path=playbook_path,
        step_idx=1,
        step_id="T02",
        total_steps=3,
        project="w1b-test",
    )


class TestCheckpointManagerW1bContract:
    """W1b 6 個 API 委派契約驗證。"""

    # 1. save() 委派 → 可 load 回讀
    def test_save_delegates_and_load_roundtrip(self, tmp_path: Path):
        mgr = CheckpointManager(str(tmp_path))
        cp = _make_cp()
        mgr.save(cp, "scripts/test.yaml")
        loaded = mgr.load("scripts/test.yaml")
        assert loaded is not None
        assert loaded.step_idx == 1
        assert loaded.step_id == "T02"
        assert loaded.project == "w1b-test"

    # 2. load() 不存在時回傳 None
    def test_load_returns_none_when_missing(self, tmp_path: Path):
        mgr = CheckpointManager(str(tmp_path))
        assert mgr.load("scripts/nonexistent.yaml") is None

    # 3. clear() 委派後檔案消失；idempotent（重複呼叫不拋例外）
    def test_clear_delegates_and_idempotent(self, tmp_path: Path):
        mgr = CheckpointManager(str(tmp_path))
        cp = _make_cp()
        mgr.save(cp, "scripts/test.yaml")
        assert mgr.exists("scripts/test.yaml")
        mgr.clear("scripts/test.yaml")
        assert not mgr.exists("scripts/test.yaml")
        mgr.clear("scripts/test.yaml")  # 再次清除不應拋例外

    # 4. checkpoint_path() stem 轉換正確
    def test_checkpoint_path_stem_extraction(self, tmp_path: Path):
        mgr = CheckpointManager(str(tmp_path))
        p = mgr.checkpoint_path("scripts/my_playbook.yaml")
        assert p.name == "my_playbook.checkpoint.json"
        p2 = mgr.checkpoint_path("deep/path/another.yaml")
        assert p2.name == "another.checkpoint.json"

    # 5. exists() 反映實際檔案狀態
    def test_exists_reflects_file_state(self, tmp_path: Path):
        mgr = CheckpointManager(str(tmp_path))
        assert not mgr.exists("scripts/test.yaml")
        mgr.save(_make_cp(), "scripts/test.yaml")
        assert mgr.exists("scripts/test.yaml")
        mgr.clear("scripts/test.yaml")
        assert not mgr.exists("scripts/test.yaml")

    # 6. schedule_resume() 向後相容：mutate checkpoint in-place + 回傳 future datetime
    def test_schedule_resume_backward_compat_mutates_inplace(self, tmp_path: Path):
        mgr = CheckpointManager(str(tmp_path))
        cp = _make_cp()
        assert cp.scheduled_resume_at is None
        resume_at = mgr.schedule_resume(cp, delay_minutes=5)
        # 回傳值為未來 datetime
        assert resume_at > datetime.now()
        # cp 本身被 mutate
        assert cp.scheduled_resume_at is not None
        parsed = datetime.fromisoformat(cp.scheduled_resume_at)
        assert timedelta(minutes=4) < (parsed - datetime.now()) < timedelta(minutes=6)

    def test_deprecation_warning_off_by_default(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_DEPRECATION_WARN", raising=False)
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            CheckpointManager(str(tmp_path))
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 0

    def test_deprecation_warning_on_when_env_set(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("AUTOCLAUDE_DEPRECATION_WARN", "1")
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            CheckpointManager(str(tmp_path))
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 1
        assert "deprecated" in str(dep_warnings[0].message).lower()
