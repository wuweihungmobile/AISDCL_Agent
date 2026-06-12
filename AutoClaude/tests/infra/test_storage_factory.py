"""StorageConfig + build_state_repository 三段開關單元測試。

對應 SD_Improving_02.md v1.1 §2.8 Phase 6 補註：
  yaml_only / both / db_only 三模式行為與失敗模式驗證。
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from autoclaude.utils.config import AppConfig, StorageConfig
from autoclaude.infra.repositories import (
    FileStateRepository, DualStateRepository, build_state_repository,
)


class TestStorageConfigDefaults:
    def test_default_mode_is_yaml_only(self):
        cfg = AppConfig()
        assert cfg.storage.mode == "yaml_only"
        assert cfg.storage.db_dsn is None
        assert cfg.storage.dual_write_strict is False
        assert cfg.storage.dual_read_resolution == "yaml_wins"

    def test_explicit_mode_validates_literal(self):
        with pytest.raises(Exception):  # pydantic ValidationError
            StorageConfig(mode="invalid_mode")  # type: ignore

    def test_dual_read_resolution_validates(self):
        with pytest.raises(Exception):
            StorageConfig(mode="both", dual_read_resolution="random")  # type: ignore


class TestBuildStateRepositoryYamlOnly:
    def test_yaml_only_returns_file_repo(self, tmp_path: Path):
        cfg = StorageConfig(mode="yaml_only")
        repo = build_state_repository(str(tmp_path), cfg)
        assert isinstance(repo, FileStateRepository)


class TestBuildStateRepositoryBothMode:
    def test_both_mode_without_dsn_raises(self, tmp_path: Path, monkeypatch):
        # M-D / SA-M4 精確化：T3 後驗證責任在 StorageConfig 建構期（ValidationError），
        # 不再依賴 build_state_repository 拋 RuntimeError。
        monkeypatch.delenv("AUTOCLAUDE_DB_DSN", raising=False)
        monkeypatch.delenv("AUTOCLAUDE_PG_DSN", raising=False)
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="db_dsn"):
            StorageConfig(mode="both", db_dsn=None)

    def test_both_mode_uses_env_var_for_dsn(self, tmp_path: Path):
        # StorageConfig 建構須在設定 AUTOCLAUDE_DB_DSN 的 patch.dict 範圍內（T3 修正後 validator 即時驗證）
        with patch.dict(
            os.environ,
            {"AUTOCLAUDE_DB_DSN": "postgresql+asyncpg://x/y?sslmode=require"},
        ):
            cfg = StorageConfig(mode="both", db_dsn=None)
            with patch(
                "autoclaude.infra.repositories.factory._smoke_test_pg",
            ):
                try:
                    repo = build_state_repository(str(tmp_path), cfg)
                except ImportError:
                    pytest.skip("sqlalchemy 未安裝；DSN 解析路徑驗證仍通過（拋 ImportError 而非 RuntimeError）")
            assert isinstance(repo, DualStateRepository)

    def test_both_mode_strict_propagates(self, tmp_path: Path):
        cfg = StorageConfig(
            mode="both", db_dsn="postgresql+asyncpg://x/y?sslmode=require",
            dual_write_strict=True, dual_read_resolution="fail_loud",
        )
        with patch(
            "autoclaude.infra.repositories.factory._smoke_test_pg",
        ):
            try:
                repo = build_state_repository(str(tmp_path), cfg)
            except ImportError:
                pytest.skip("sqlalchemy 未安裝")
        assert isinstance(repo, DualStateRepository)
        assert repo._strict is True
        assert repo._read_resolution == "fail_loud"


class TestBuildStateRepositoryDbOnly:
    def test_db_only_without_dsn_raises(self, tmp_path: Path, monkeypatch):
        # M-D / SA-M4 精確化：T3 後驗證責任在 StorageConfig 建構期，只預期 ValidationError。
        monkeypatch.delenv("AUTOCLAUDE_DB_DSN", raising=False)
        monkeypatch.delenv("AUTOCLAUDE_PG_DSN", raising=False)
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="db_dsn"):
            StorageConfig(mode="db_only")


class TestBuildStateRepositoryTLSEnforcement:
    """Security review：強制 TLS（sslmode=require）。"""

    def test_db_only_dsn_without_ssl_raises(self, tmp_path: Path):
        cfg = StorageConfig(mode="db_only", db_dsn="postgresql+asyncpg://u:p@h/d")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUTOCLAUDE_DB_DSN", None)
            os.environ.pop("AUTOCLAUDE_PG_DSN", None)
            os.environ.pop("AUTOCLAUDE_ALLOW_INSECURE_DB", None)
            with pytest.raises(RuntimeError, match="必須啟用 TLS"):
                build_state_repository(str(tmp_path), cfg)

    def test_dsn_with_sslmode_passes_tls_check(self, tmp_path: Path):
        cfg = StorageConfig(
            mode="db_only",
            db_dsn="postgresql+asyncpg://u:p@h/d?sslmode=require",
        )
        try:
            build_state_repository(str(tmp_path), cfg)
        except ImportError:
            pytest.skip("sqlalchemy 未安裝")
        except RuntimeError as exc:
            if "必須啟用 TLS" in str(exc):
                pytest.fail("sslmode=require 應通過 TLS 檢查")

    def test_insecure_override_disables_tls_check(self, tmp_path: Path):
        cfg = StorageConfig(mode="db_only", db_dsn="postgresql+asyncpg://u:p@h/d")
        with patch.dict(os.environ, {"AUTOCLAUDE_ALLOW_INSECURE_DB": "1"}, clear=False):
            os.environ.pop("AUTOCLAUDE_DB_DSN", None)
            os.environ.pop("AUTOCLAUDE_PG_DSN", None)
            try:
                build_state_repository(str(tmp_path), cfg)
            except ImportError:
                pytest.skip("sqlalchemy 未安裝")
            except RuntimeError as exc:
                if "必須啟用 TLS" in str(exc):
                    pytest.fail("AUTOCLAUDE_ALLOW_INSECURE_DB=1 應跳過 TLS 檢查")


class TestLegacyEnvVarCompat:
    def test_legacy_pg_dsn_still_works_with_warning(self, tmp_path: Path, caplog):
        # T3 修正後：StorageConfig 建構須在設定環境變數的 patch.dict 範圍內
        with patch.dict(
            os.environ,
            {"AUTOCLAUDE_PG_DSN": "postgresql+asyncpg://u:p@h/d?sslmode=require"},
            clear=False,
        ):
            os.environ.pop("AUTOCLAUDE_DB_DSN", None)
            cfg = StorageConfig(mode="db_only")
            with patch(
                "autoclaude.infra.repositories.factory._smoke_test_pg",
            ):
                try:
                    build_state_repository(str(tmp_path), cfg)
                except ImportError:
                    pass  # 需要 sqlalchemy 才能完整建構，但 DSN 解析路徑驗證即可
        assert any(
            "AUTOCLAUDE_PG_DSN 已 deprecated" in r.message
            for r in caplog.records
        )


class TestDsnRedaction:
    def test_redact_strips_password(self):
        from autoclaude.infra.repositories.pg_state_repository import _redact
        msg = "Connection failed: postgresql+asyncpg://admin:supersecret@host/db?ssl=require"
        out = _redact(msg)
        assert "supersecret" not in out
        assert "***" in out

    def test_redact_preserves_message_structure(self):
        from autoclaude.infra.repositories.pg_state_repository import _redact
        msg = "Generic error without DSN"
        assert _redact(msg) == msg


class TestDualStateRepositoryBehavior:
    """DualStateRepository 寫入主/影路徑與容錯行為。"""

    class _FakePrimary:
        def __init__(self):
            self.saved = {}
            self.cleared = []
        def save_checkpoint(self, pid, cp): self.saved[pid] = cp
        def load_checkpoint(self, pid): return self.saved.get(pid)
        def clear_checkpoint(self, pid): self.cleared.append(pid)
        def schedule_resume(self, pid, m):
            from datetime import datetime, timedelta
            return datetime.now() + timedelta(minutes=m)

    class _FakeShadow:
        def __init__(self, fail_save=False, fail_load=False):
            self.saved = {}
            self.fail_save = fail_save
            self.fail_load = fail_load
        def save_checkpoint(self, pid, cp):
            if self.fail_save: raise RuntimeError("PG down")
            self.saved[pid] = cp
        def load_checkpoint(self, pid):
            if self.fail_load: raise RuntimeError("PG down")
            return self.saved.get(pid)
        def clear_checkpoint(self, pid): self.saved.pop(pid, None)
        def schedule_resume(self, pid, m):
            from datetime import datetime, timedelta
            return datetime.now() + timedelta(minutes=m)

    def _make_cp(self, step_idx=0):
        from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
        return PlaybookCheckpoint(
            playbook_path="pb_001", step_idx=step_idx, step_id="T01", total_steps=3,
        )

    def test_save_writes_both_when_shadow_ok(self):
        primary, shadow = self._FakePrimary(), self._FakeShadow()
        dual = DualStateRepository(primary=primary, shadow=shadow)
        cp = self._make_cp()
        dual.save_checkpoint("pb_dual_001", cp)
        assert "pb_dual_001" in primary.saved
        assert "pb_dual_001" in shadow.saved

    def test_save_continues_when_shadow_fails_non_strict(self):
        primary, shadow = self._FakePrimary(), self._FakeShadow(fail_save=True)
        dual = DualStateRepository(primary=primary, shadow=shadow, strict=False)
        cp = self._make_cp()
        dual.save_checkpoint("pb_dual_002", cp)  # 不應 raise
        assert "pb_dual_002" in primary.saved
        assert "pb_dual_002" not in shadow.saved

    def test_save_strict_raises_when_shadow_fails(self):
        primary, shadow = self._FakePrimary(), self._FakeShadow(fail_save=True)
        dual = DualStateRepository(primary=primary, shadow=shadow, strict=True)
        cp = self._make_cp()
        with pytest.raises(RuntimeError, match="PG down"):
            dual.save_checkpoint("pb_dual_003", cp)
        assert "pb_dual_003" in primary.saved  # primary 已寫入

    def test_load_yaml_wins_returns_primary(self):
        primary, shadow = self._FakePrimary(), self._FakeShadow()
        primary.saved["pb_004"] = self._make_cp(step_idx=2)
        shadow.saved["pb_004"] = self._make_cp(step_idx=99)
        dual = DualStateRepository(primary=primary, shadow=shadow, read_resolution="yaml_wins")
        loaded = dual.load_checkpoint("pb_004")
        assert loaded.step_idx == 2

    def test_load_db_wins_returns_shadow(self):
        primary, shadow = self._FakePrimary(), self._FakeShadow()
        primary.saved["pb_005"] = self._make_cp(step_idx=2)
        shadow.saved["pb_005"] = self._make_cp(step_idx=99)
        dual = DualStateRepository(primary=primary, shadow=shadow, read_resolution="db_wins")
        loaded = dual.load_checkpoint("pb_005")
        assert loaded.step_idx == 99

    def test_load_fail_loud_raises_on_drift(self):
        primary, shadow = self._FakePrimary(), self._FakeShadow()
        primary.saved["pb_006"] = self._make_cp(step_idx=2)
        shadow.saved["pb_006"] = self._make_cp(step_idx=99)
        dual = DualStateRepository(primary=primary, shadow=shadow, read_resolution="fail_loud")
        with pytest.raises(RuntimeError, match="drift detected"):
            dual.load_checkpoint("pb_006")

    def test_load_yaml_wins_falls_back_to_shadow_when_primary_missing(self):
        primary, shadow = self._FakePrimary(), self._FakeShadow()
        shadow.saved["pb_007"] = self._make_cp(step_idx=5)
        dual = DualStateRepository(primary=primary, shadow=shadow, read_resolution="yaml_wins")
        loaded = dual.load_checkpoint("pb_007")
        assert loaded.step_idx == 5  # 災難回復場景

    def test_load_handles_shadow_exception_gracefully(self):
        primary, shadow = self._FakePrimary(), self._FakeShadow(fail_load=True)
        primary.saved["pb_008"] = self._make_cp(step_idx=3)
        dual = DualStateRepository(primary=primary, shadow=shadow, read_resolution="yaml_wins")
        loaded = dual.load_checkpoint("pb_008")
        assert loaded.step_idx == 3
