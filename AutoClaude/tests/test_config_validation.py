"""tests/test_config_validation.py — M-3/X-3 Pydantic config validation 測試。

驗證 TokenGuardConfig 與 StorageConfig 的 Pydantic validator 防呆行為。
"""
from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from autoclaude.utils.config import TokenGuardConfig, StorageConfig, AppConfig


# ─────────────────────────────────────────────
# TokenGuardConfig validators
# ─────────────────────────────────────────────

class TestTokenGuardConfigValidation:
    def test_valid_default_config(self):
        """預設值（compact=80, halt=90）應通過驗證。"""
        cfg = TokenGuardConfig()
        assert cfg.compact_threshold_pct == 80.0
        assert cfg.halt_threshold_pct == 90.0

    def test_valid_custom_thresholds(self):
        """compact=70, halt=85 合法排序應通過。"""
        cfg = TokenGuardConfig(compact_threshold_pct=70.0, halt_threshold_pct=85.0)
        assert cfg.compact_threshold_pct == 70.0
        assert cfg.halt_threshold_pct == 85.0

    def test_halt_less_than_compact_raises(self):
        """compact=95, halt=85（倒序）應拋 ValidationError。"""
        with pytest.raises(ValidationError, match="halt_threshold_pct"):
            TokenGuardConfig(compact_threshold_pct=95.0, halt_threshold_pct=85.0)

    def test_halt_equal_compact_raises(self):
        """compact=80, halt=80（相等）應拋 ValidationError。"""
        with pytest.raises(ValidationError, match="halt_threshold_pct"):
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=80.0)

    def test_invalid_regex_pattern_raises(self):
        """無效 regex pattern 應拋 ValidationError。"""
        with pytest.raises(ValidationError, match="無效 regex"):
            TokenGuardConfig(context_patterns=["(unclosed"])

    def test_valid_custom_regex_patterns(self):
        """合法自訂 regex pattern 應通過驗證。"""
        cfg = TokenGuardConfig(context_patterns=[r"\d+%", r"token:\s*(\d+)"])
        assert len(cfg.context_patterns) == 2

    def test_out_of_range_compact_raises(self):
        """compact_threshold_pct 超出 0~100 範圍應拋 ValidationError。

        Dev-5（W1P0 三方審查）：精準驗證 compact_threshold_pct 欄位錯誤，
        halt 用合法值（90.0）以隔離只測 compact 越界，避免 halt 也越界
        導致誤把 halt 的錯誤訊息當成測試通過依據。
        """
        with pytest.raises(ValidationError, match="compact_threshold_pct"):
            TokenGuardConfig(compact_threshold_pct=101.0, halt_threshold_pct=90.0)

    def test_out_of_range_compact_negative_raises(self):
        """compact_threshold_pct 負值（<0）應拋 ValidationError。"""
        with pytest.raises(ValidationError, match="compact_threshold_pct"):
            TokenGuardConfig(compact_threshold_pct=-1.0, halt_threshold_pct=90.0)

    def test_out_of_range_halt_raises(self):
        """halt_threshold_pct 超出 0~100 範圍應拋 ValidationError。"""
        with pytest.raises(ValidationError, match="halt_threshold_pct"):
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=101.0)

    def test_boundary_zero_and_hundred_ok(self):
        """compact=0, halt=100 為合法邊界值（compact < halt 條件成立）。"""
        cfg = TokenGuardConfig(compact_threshold_pct=0.0, halt_threshold_pct=100.0)
        assert cfg.compact_threshold_pct == 0.0
        assert cfg.halt_threshold_pct == 100.0


# ─────────────────────────────────────────────
# StorageConfig validators
# ─────────────────────────────────────────────

class TestStorageConfigValidation:
    def test_yaml_only_no_dsn_ok(self):
        """yaml_only 模式不需 db_dsn，應通過驗證。"""
        cfg = StorageConfig(mode="yaml_only")
        assert cfg.mode == "yaml_only"

    def test_db_only_with_db_dsn_ok(self):
        """db_only + db_dsn 提供時應通過驗證。"""
        cfg = StorageConfig(mode="db_only", db_dsn="postgresql+asyncpg://user:pass@localhost/db")
        assert cfg.mode == "db_only"

    def test_both_with_db_dsn_ok(self):
        """both + db_dsn 提供時應通過驗證。"""
        cfg = StorageConfig(mode="both", db_dsn="postgresql+asyncpg://user:pass@localhost/db")
        assert cfg.mode == "both"

    def test_db_only_no_dsn_no_env_raises(self, monkeypatch):
        """db_only + 無 db_dsn + 無環境變數 → ValidationError。"""
        monkeypatch.delenv("AUTOCLAUDE_DB_DSN", raising=False)
        monkeypatch.delenv("AUTOCLAUDE_PG_DSN", raising=False)
        with pytest.raises(ValidationError, match="db_dsn"):
            StorageConfig(mode="db_only")

    def test_both_no_dsn_no_env_raises(self, monkeypatch):
        """both + 無 db_dsn + 無環境變數 → ValidationError。"""
        monkeypatch.delenv("AUTOCLAUDE_DB_DSN", raising=False)
        monkeypatch.delenv("AUTOCLAUDE_PG_DSN", raising=False)
        with pytest.raises(ValidationError, match="db_dsn"):
            StorageConfig(mode="both")

    def test_db_only_no_dsn_but_env_ok(self, monkeypatch):
        """db_only + 無 db_dsn + AUTOCLAUDE_DB_DSN 環境變數存在 → 通過驗證。"""
        monkeypatch.setenv("AUTOCLAUDE_DB_DSN", "postgresql+asyncpg://x:y@localhost/db")
        cfg = StorageConfig(mode="db_only")
        assert cfg.mode == "db_only"

    def test_db_only_no_dsn_legacy_env_ok(self, monkeypatch):
        """db_only + 無 db_dsn + AUTOCLAUDE_PG_DSN（deprecated）環境變數存在 → 通過驗證。"""
        monkeypatch.delenv("AUTOCLAUDE_DB_DSN", raising=False)
        monkeypatch.setenv("AUTOCLAUDE_PG_DSN", "postgresql+asyncpg://x:y@localhost/db")
        cfg = StorageConfig(mode="db_only")
        assert cfg.mode == "db_only"


# ─────────────────────────────────────────────
# AppConfig 整合驗證（確認 validator 不破壞預設值）
# ─────────────────────────────────────────────

class TestAppConfigDefaultsUnchanged:
    def test_default_appconfig_valid(self):
        """AppConfig() 預設值應全部通過 Pydantic 驗證。"""
        cfg = AppConfig()
        assert cfg.token_guard.compact_threshold_pct == 80.0
        assert cfg.token_guard.halt_threshold_pct == 90.0
        assert cfg.storage.mode == "yaml_only"
