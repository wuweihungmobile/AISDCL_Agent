"""DualStateRepository smoke test（SD_Improving_03 §5.2 DoD #8）。

驗證 DualStateRepository 雙寫行為（storage.mode="both"）：
  - 使用 FileStateRepository（主）+ FileStateRepository（shadow，模擬 PG shadow）
  - 測試 dual_write、yaml_wins / db_wins / fail_loud 等讀取策略
  - 測試 shadow 失敗不阻擋主流程（strict=False）
  - 測試 clear_checkpoint 同步清兩個後端
"""
from __future__ import annotations

import pytest

from autoclaude.infra.repositories.dual_state_repository import DualStateRepository
from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint


def _make_checkpoint(step_idx: int = 0, step_id: str = "T01") -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path="test.yaml",
        step_idx=step_idx,
        step_id=step_id,
        total_steps=3,
    )


def _make_dual(tmp_path, *, strict=False, read_resolution="yaml_wins"):
    primary_dir = tmp_path / "primary"
    shadow_dir = tmp_path / "shadow"
    primary = FileStateRepository(checkpoint_dir=str(primary_dir))
    shadow = FileStateRepository(checkpoint_dir=str(shadow_dir))
    dual = DualStateRepository(
        primary, shadow,
        strict=strict,
        read_resolution=read_resolution,
    )
    return dual, primary, shadow


# ──────────────────────────────────────────────────────────
class TestDualRepositoryYamlWinsMode:
    def test_dual_repository_yaml_wins_mode_save_load(self, tmp_path):
        """storage.mode=both yaml_wins：save 成功，load 從主（file）讀取。"""
        dual, primary, shadow = _make_dual(tmp_path, read_resolution="yaml_wins")
        cp = _make_checkpoint(step_idx=1, step_id="T02")
        dual.save_checkpoint("proj1", cp)

        loaded = dual.load_checkpoint("proj1")
        assert loaded is not None
        assert loaded.step_idx == 1
        assert loaded.step_id == "T02"

    def test_dual_repository_both_backends_receive_save(self, tmp_path):
        """dual write：兩個後端都收到 save 呼叫，存入相同 checkpoint。"""
        dual, primary, shadow = _make_dual(tmp_path)
        cp = _make_checkpoint(step_idx=2, step_id="T03")
        dual.save_checkpoint("proj2", cp)

        primary_loaded = primary.load_checkpoint("proj2")
        shadow_loaded = shadow.load_checkpoint("proj2")

        assert primary_loaded is not None, "主後端應存有 checkpoint"
        assert shadow_loaded is not None, "影子後端應存有 checkpoint"
        assert primary_loaded.step_idx == 2
        assert shadow_loaded.step_idx == 2

    def test_dual_write_success_metric_incremented(self, tmp_path):
        """save_checkpoint 成功時 metrics.dual_write_success 遞增。"""
        dual, _, _ = _make_dual(tmp_path)
        assert dual.metrics.dual_write_success == 0
        dual.save_checkpoint("proj3", _make_checkpoint())
        assert dual.metrics.dual_write_success == 1
        dual.save_checkpoint("proj3", _make_checkpoint(step_idx=1))
        assert dual.metrics.dual_write_success == 2


# ──────────────────────────────────────────────────────────
class TestDualRepositoryShadowFailure:
    def test_dual_repository_shadow_failure_does_not_block(self, tmp_path):
        """shadow write 失敗（strict=False）不阻擋主流程，主後端仍可讀取。"""
        primary_dir = tmp_path / "primary"
        primary = FileStateRepository(checkpoint_dir=str(primary_dir))

        # 建立一個故意失敗的 shadow（使用能記錄呼叫的 mock）
        class FailingShadow:
            def save_checkpoint(self, playbook_id, checkpoint):
                raise RuntimeError("PG 連線失敗（模擬）")

            def load_checkpoint(self, playbook_id):
                raise RuntimeError("PG 連線失敗（模擬）")

            def clear_checkpoint(self, playbook_id):
                raise RuntimeError("PG 連線失敗（模擬）")

        dual = DualStateRepository(
            primary, FailingShadow(),
            strict=False,
            read_resolution="yaml_wins",
        )
        cp = _make_checkpoint(step_idx=1, step_id="T01")

        # strict=False：不應拋出例外
        dual.save_checkpoint("proj4", cp)
        assert dual.metrics.dual_write_failure == 1

        # 主後端仍可讀取
        loaded = dual.load_checkpoint("proj4")
        assert loaded is not None
        assert loaded.step_idx == 1

    def test_dual_repository_shadow_failure_strict_raises(self, tmp_path):
        """strict=True 時 shadow 失敗應 raise RuntimeError。"""
        primary_dir = tmp_path / "primary"
        primary = FileStateRepository(checkpoint_dir=str(primary_dir))

        class FailingShadow:
            def save_checkpoint(self, playbook_id, checkpoint):
                raise RuntimeError("PG 連線失敗")

            def load_checkpoint(self, playbook_id):
                return None

            def clear_checkpoint(self, playbook_id):
                pass

        dual = DualStateRepository(
            primary, FailingShadow(),
            strict=True,
        )
        with pytest.raises(RuntimeError, match="PG 連線失敗"):
            dual.save_checkpoint("proj5", _make_checkpoint())


# ──────────────────────────────────────────────────────────
class TestDualRepositoryClear:
    def test_dual_repository_clear_propagates(self, tmp_path):
        """clear_checkpoint() 同步清兩個後端。"""
        dual, primary, shadow = _make_dual(tmp_path)
        cp = _make_checkpoint(step_idx=1)
        dual.save_checkpoint("proj6", cp)

        # 確認兩端都有資料
        assert primary.load_checkpoint("proj6") is not None
        assert shadow.load_checkpoint("proj6") is not None

        # 清除後兩端都應無資料
        dual.clear_checkpoint("proj6")
        assert primary.load_checkpoint("proj6") is None
        assert shadow.load_checkpoint("proj6") is None


# ──────────────────────────────────────────────────────────
class TestDualRepositoryLoadBehavior:
    def test_dual_repository_load_checkpoint_when_primary_empty(self, tmp_path):
        """主後端無 checkpoint，yaml_wins 模式返回 None（shadow 也為空）。"""
        dual, _, _ = _make_dual(tmp_path, read_resolution="yaml_wins")
        result = dual.load_checkpoint("nonexistent_proj")
        assert result is None

    def test_dual_repository_db_wins_prefers_shadow(self, tmp_path):
        """db_wins 模式：shadow 有資料時優先返回 shadow 的結果。"""
        dual, primary, shadow = _make_dual(tmp_path, read_resolution="db_wins")

        # 只在 shadow 寫入（直接使用 shadow FileStateRepository）
        shadow_cp = _make_checkpoint(step_idx=5, step_id="T06")
        shadow.save_checkpoint("proj7", shadow_cp)

        # db_wins 模式應返回 shadow 的結果
        loaded = dual.load_checkpoint("proj7")
        assert loaded is not None
        assert loaded.step_idx == 5

    def test_dual_repository_fail_loud_detects_drift(self, tmp_path):
        """fail_loud 模式：主／影子 step_idx 不一致時 raise RuntimeError（drift）。"""
        dual, primary, shadow = _make_dual(tmp_path, read_resolution="fail_loud")

        # 分別寫入不同 step_idx
        primary.save_checkpoint("proj8", _make_checkpoint(step_idx=2))
        shadow.save_checkpoint("proj8", _make_checkpoint(step_idx=5))

        with pytest.raises(RuntimeError, match="drift detected"):
            dual.load_checkpoint("proj8")
        assert dual.metrics.shadow_drift_detected == 1

    def test_dual_repository_fail_loud_no_drift_when_consistent(self, tmp_path):
        """fail_loud 模式：主／影子 step_idx 一致時不 raise。"""
        dual, _, _ = _make_dual(tmp_path, read_resolution="fail_loud")

        # 透過 dual.save_checkpoint 同時寫入，step_idx 一致
        dual.save_checkpoint("proj9", _make_checkpoint(step_idx=3))
        loaded = dual.load_checkpoint("proj9")
        assert loaded is not None
        assert loaded.step_idx == 3
