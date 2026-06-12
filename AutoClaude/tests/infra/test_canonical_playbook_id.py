"""T8（SD_04 §3 / M-2）：canonical_playbook_id 統一計算測試。

驗證：
  - yaml_only / both 模式：使用 Path.stem（人類可讀，向後相容）
  - db_only 模式：使用 sha256(abs_path)[:16]（PG 純後端唯一性保證）
  - CheckpointManager 注入式 id_resolver：可覆寫預設 stem 行為
  - both 模式下 dual save/load 在同一 ID 下對得上
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from autoclaude.infra.repositories import canonical_playbook_id
from autoclaude.infra.repositories.factory import canonical_playbook_id as factory_id
from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint


# ══════════════════════════════════════════════
# canonical_playbook_id：依模式切換策略
# ══════════════════════════════════════════════

class TestCanonicalIdStrategy:
    def test_yaml_only_uses_stem(self):
        assert canonical_playbook_id("scripts/my_playbook.yaml", "yaml_only") == "my_playbook"

    def test_yaml_only_handles_absolute_path(self):
        assert canonical_playbook_id("/abs/path/to/foo.yaml", "yaml_only") == "foo"

    def test_yaml_only_handles_no_extension(self):
        assert canonical_playbook_id("plain_name", "yaml_only") == "plain_name"

    def test_both_mode_uses_stem(self):
        """both 模式必須與 yaml_only 一致（因為 dual-write 兩端共享同一 ID）。"""
        assert canonical_playbook_id("scripts/playbook.yaml", "both") == "playbook"

    def test_both_and_yaml_only_produce_same_id(self):
        """yaml_only 與 both 對同一路徑必須回傳相同 ID。"""
        path = "scripts/test.yaml"
        assert (
            canonical_playbook_id(path, "yaml_only")
            == canonical_playbook_id(path, "both")
        )

    def test_db_only_uses_sha256_hex16(self):
        """db_only 用 sha256(abs_path)[:16]。"""
        path = "scripts/playbook.yaml"
        result = canonical_playbook_id(path, "db_only")
        # 16 hex 字元
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)
        # 確認與直接計算一致
        abs_path = str(Path(path).resolve())
        expected = hashlib.sha256(abs_path.encode("utf-8")).hexdigest()[:16]
        assert result == expected

    def test_db_only_consistent_for_same_absolute_path(self):
        """同一絕對路徑必須產生同一 ID。"""
        a = canonical_playbook_id("./scripts/x.yaml", "db_only")
        b = canonical_playbook_id("scripts/x.yaml", "db_only")
        # 兩者 resolve() 後相同
        assert a == b

    def test_db_only_different_paths_different_ids(self):
        a = canonical_playbook_id("scripts/playbook_a.yaml", "db_only")
        b = canonical_playbook_id("scripts/playbook_b.yaml", "db_only")
        assert a != b

    def test_factory_export_matches_module(self):
        """從 repositories package 與 factory module 取得的函式一致。"""
        path = "scripts/test.yaml"
        assert canonical_playbook_id(path, "yaml_only") == factory_id(path, "yaml_only")


# ══════════════════════════════════════════════
# CheckpointManager 注入式 id_resolver
# ══════════════════════════════════════════════

class TestCheckpointManagerIdResolver:
    def test_default_resolver_uses_stem(self, tmp_path):
        """未注入 id_resolver 時行為與舊版相同（stem）。"""
        mgr = CheckpointManager(str(tmp_path))
        assert mgr._to_id("scripts/my.yaml") == "my"

    def test_injected_resolver_overrides_default(self, tmp_path):
        """注入自訂 resolver 後完全替換預設行為。"""
        mgr = CheckpointManager(
            str(tmp_path),
            id_resolver=lambda p: f"custom_{Path(p).stem}",
        )
        assert mgr._to_id("scripts/foo.yaml") == "custom_foo"

    def test_injected_canonical_resolver_yaml_only(self, tmp_path):
        """注入 canonical_playbook_id（yaml_only）效果與預設一致。"""
        mgr = CheckpointManager(
            str(tmp_path),
            id_resolver=lambda p: canonical_playbook_id(p, "yaml_only"),
        )
        assert mgr._to_id("scripts/abc.yaml") == "abc"

    def test_injected_canonical_resolver_db_only(self, tmp_path):
        """注入 db_only resolver 應產生 16-hex ID。"""
        mgr = CheckpointManager(
            str(tmp_path),
            id_resolver=lambda p: canonical_playbook_id(p, "db_only"),
        )
        cid = mgr._to_id("scripts/zzz.yaml")
        assert len(cid) == 16
        assert all(c in "0123456789abcdef" for c in cid)

    def test_save_load_with_injected_resolver(self, tmp_path):
        """注入 resolver 後 save/load 仍正常 round-trip。"""
        mgr = CheckpointManager(
            str(tmp_path),
            id_resolver=lambda p: f"prefix_{Path(p).stem}",
        )
        cp = PlaybookCheckpoint(
            playbook_path="scripts/x.yaml",
            step_idx=1,
            step_id="T01",
            total_steps=3,
            project="P",
        )
        mgr.save(cp, "scripts/x.yaml")
        # 檔案應命名為 prefix_x.checkpoint.json
        path = mgr.checkpoint_path("scripts/x.yaml")
        assert path.name == "prefix_x.checkpoint.json"
        assert path.exists()
        # load 應取回同一筆
        loaded = mgr.load("scripts/x.yaml")
        assert loaded is not None
        assert loaded.step_idx == 1


# ══════════════════════════════════════════════
# Both 模式 ID 一致性（dual-write 對齊）
# ══════════════════════════════════════════════

class TestBothModeIdAlignment:
    def test_dual_save_load_uses_same_id(self, tmp_path):
        """both 模式下，主/影 backend 共用同一 stem-based ID。

        驗證 canonical_playbook_id("yaml_only") 與 ("both") 等價，
        確保 DualStateRepository 對兩端傳遞相同的 playbook_id。
        """
        from autoclaude.infra.repositories import DualStateRepository, FileStateRepository

        path = "scripts/dual_test.yaml"
        pid_yaml = canonical_playbook_id(path, "yaml_only")
        pid_both = canonical_playbook_id(path, "both")
        assert pid_yaml == pid_both  # dual-write 對齊保證

        # 使用 FileStateRepository × 2 模擬 primary + shadow
        primary = FileStateRepository(str(tmp_path / "p"))
        shadow = FileStateRepository(str(tmp_path / "s"))
        dual = DualStateRepository(primary=primary, shadow=shadow)

        cp = PlaybookCheckpoint(
            playbook_path=path, step_idx=2, step_id="T03",
            total_steps=5, project="DualTest",
        )
        dual.save_checkpoint(pid_both, cp)

        loaded = dual.load_checkpoint(pid_both)
        assert loaded is not None
        assert loaded.step_idx == 2
