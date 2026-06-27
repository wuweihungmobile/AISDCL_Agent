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


# ─────────────────────────────────────────────
# improving_91 W-91-1/3：EmbedderConfig + 設定治理一致性
# ─────────────────────────────────────────────

class TestEmbedderConfig:
    def test_embedder_block_loaded_not_dropped(self):
        """RTM-91-1 / DEF-91-003：config.yaml 的 embedder 區塊被 Pydantic 接受、不再靜默丟棄。

        WHY：修復前 AppConfig 無 embedder 欄位 + Pydantic extra=ignore → 使用者填的
        embedder 區塊被丟棄（hasattr 為 False），且 ConfigResolver 的 embedder.api_key
        RBAC 在保護幽靈欄位。本測試鎖死「embedder 區塊真的進得了 AppConfig」。
        """
        cfg = AppConfig.model_validate(
            {"embedder": {"base_url": "http://x/emb", "model": "m1", "dimension": 512}}
        )
        assert hasattr(cfg, "embedder")
        assert cfg.embedder.base_url == "http://x/emb"
        assert cfg.embedder.model == "m1"
        assert cfg.embedder.dimension == 512

    def test_embedder_defaults_are_non_secret(self):
        """RTM-91-1：EmbedderConfig 非機密預設正確；api_key 預設留空（機密走 env）。

        WHY：機密邊界紅線——api_key 入庫預設必須是空字串（同 MinimaxConfig），
        確保模板/預設不會夾帶任何真實金鑰。
        """
        e = AppConfig().embedder
        assert e.base_url == "https://api.minimax.io/v1/embeddings"
        assert e.model == "embo-01"
        assert e.dimension == 1024
        assert e.api_key == ""

    def test_minimax_dataclass_default_aligns_with_config_yaml(self):
        """RTM-91-6 / DEF-91-001：MinimaxConfig dataclass 預設須與 config.yaml 一致。

        WHY：improving_90 統一 config.yaml 為非機密權威源，但 dataclass 預設仍是舊端點/
        舊 model；config.yaml 缺 minimax 欄位時會 fallback 到舊值＝設定漂移。鎖死預設＝
        config.yaml 當前值，防漂移復活。
        """
        m = AppConfig().minimax
        assert m.base_url == "https://api.minimax.io/v1/text/chatcompletion_v2"
        assert m.model == "MiniMax-M2.7"

    def test_embedder_bge_m3_defaults(self):
        """RTM-92-1：EmbedderConfig bge-m3 非機密預設正確（方案 B 收尾）。

        WHY：TEI 為本地容器、全非機密——預設須對齊 bgem3_local.py 硬編值（localhost:8080 /
        BAAI/bge-m3 / 1024），且【不】夾帶任何 api_key 機密欄位（與 Minimax embedder 不同）。
        """
        e = AppConfig().embedder
        assert e.bge_m3_url == "http://localhost:8080"
        assert e.bge_m3_model == "BAAI/bge-m3"
        assert e.bge_m3_dimension == 1024
        assert e.bge_m3_timeout_seconds == 30.0
        # 機密邊界：bge-m3 無任何 api_key 欄位（TEI 本地容器無認證）
        assert not hasattr(e, "bge_m3_api_key")

    def test_embedder_bge_m3_block_loaded(self):
        """RTM-92-1 / DEF-92-003：config.yaml 的 embedder.bge_m3_* 被 Pydantic 接受、不被丟棄。

        WHY：修復前 EmbedderConfig 無 bge_m3_* 欄位，使用者填的 bge-m3 設定會被 extra=ignore
        靜默丟棄＝TEI 設定無法集中於 config.yaml。本測試鎖死「bge-m3 區塊真的進得了 AppConfig」。
        """
        cfg = AppConfig.model_validate(
            {"embedder": {"bge_m3_url": "http://tei:9090", "bge_m3_model": "m2",
                          "bge_m3_dimension": 768}}
        )
        assert cfg.embedder.bge_m3_url == "http://tei:9090"
        assert cfg.embedder.bge_m3_model == "m2"
        assert cfg.embedder.bge_m3_dimension == 768
        # 同物件的 Minimax 欄位維持預設（互不干擾）
        assert cfg.embedder.model == "embo-01"
