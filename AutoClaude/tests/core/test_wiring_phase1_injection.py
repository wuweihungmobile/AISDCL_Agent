"""wiring Phase 1 注入鏈測試（QA audit P1-1 / P1-4 / P1-5 修復）。

驗證意圖：wiring 對三個記憶 store 採 try/except 吞錯降級設計 —— 若建構靜默
失敗變 None，F-C3/F-C1/F-C2 整個功能會「全綠但消失」。本檔守住：
(1) yaml_only 正常路徑下三個 store 必須非 None 且型別正確（P1-1）；
(2) factory 三個 builder 的 yaml_only 路由與落地路徑（P1-4）；
(3) config.preferences seed 確實寫入 store（P1-5）；
(4) factory raise 時降級為 None 而非炸毀組裝（既定 fail-soft 設計的明示化）。
"""
from __future__ import annotations

import pytest

from autoclaude.core import wiring
from autoclaude.infra.adapters.file_preference_store import FilePreferenceStore
from autoclaude.infra.adapters.local_kb_metric_store import LocalKbMetricStore
from autoclaude.infra.repositories import factory
from autoclaude.utils.config import AppConfig, StorageConfig
from autoclaude.utils.goal_progress import GoalProgressLedger


def _cfg(tmp_path, **kwargs) -> AppConfig:
    return AppConfig(checkpoint_dir=str(tmp_path), **kwargs)


class TestPluginStoreInjection:
    """P1-1：yaml_only 下三個 plugin 的 store 注入必須真的發生。"""

    def test_preference_memory_store_injected(self, tmp_path):
        plugins = wiring._build_plugin_set(_cfg(tmp_path))
        assert isinstance(plugins["preference_memory"]._store, FilePreferenceStore)

    def test_goal_progress_ledger_injected(self, tmp_path):
        plugins = wiring._build_plugin_set(_cfg(tmp_path))
        assert isinstance(plugins["goal_progress"]._ledger, GoalProgressLedger)

    def test_kb_metric_store_injected(self, tmp_path):
        plugins = wiring._build_plugin_set(_cfg(tmp_path))
        kb = plugins["knowledge_base"]._kb
        assert isinstance(kb._metric_store, LocalKbMetricStore)


class TestFactoryFailureDegradesToNone:
    """factory raise → store=None（fail-soft），組裝不得炸毀。"""

    def test_preference_store_failure_degrades(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            factory, "build_preference_store",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        plugins = wiring._build_plugin_set(_cfg(tmp_path))
        assert plugins["preference_memory"]._store is None

    def test_ledger_failure_degrades(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            factory, "build_goal_progress_ledger",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        plugins = wiring._build_plugin_set(_cfg(tmp_path))
        assert plugins["goal_progress"]._ledger is None


class TestFactoryYamlOnlyRouting:
    """P1-4：三個 builder 的 yaml_only 路由與落地檔案路徑。"""

    def test_preference_store_routes_to_file(self, tmp_path):
        store = factory.build_preference_store(
            str(tmp_path), StorageConfig(mode="yaml_only")
        )
        assert isinstance(store, FilePreferenceStore)
        store.set("k", "v")
        assert (tmp_path / "preferences.jsonl").exists()

    def test_goal_progress_routes_to_file(self, tmp_path):
        ledger = factory.build_goal_progress_ledger(
            str(tmp_path), StorageConfig(mode="yaml_only")
        )
        assert isinstance(ledger, GoalProgressLedger)
        ledger.record("g1", completed_features=["A"])
        assert (tmp_path / "goal_progress.jsonl").exists()

    def test_kb_metric_store_routes_to_local(self, tmp_path):
        store = factory.build_kb_metric_store(
            str(tmp_path), StorageConfig(mode="yaml_only")
        )
        assert isinstance(store, LocalKbMetricStore)
        store.record_counter("kb_queries_total", 1)
        store.flush()
        assert (tmp_path / ".kb_metrics_local.jsonl").exists()

    @pytest.mark.parametrize("builder", [
        factory.build_preference_store,
        factory.build_goal_progress_ledger,
        factory.build_kb_metric_store,
    ])
    def test_db_mode_without_dsn_fails_loud(self, tmp_path, builder, monkeypatch):
        """無 DSN 的 db 模式必須 fail loud：config 層 ValidationError 先擋
        （StorageConfig validator），factory 層 RuntimeError 為第二道防線。"""
        monkeypatch.delenv("AUTOCLAUDE_DB_DSN", raising=False)
        monkeypatch.delenv("AUTOCLAUDE_PG_DSN", raising=False)
        import pydantic
        with pytest.raises((RuntimeError, pydantic.ValidationError)):
            builder(str(tmp_path), StorageConfig(mode="db_only"))


class TestConfigPreferencesSeed:
    """P1-5：config.preferences 必須 seed 進 store（global scope，str 轉型）。"""

    def test_seed_written_to_store(self, tmp_path):
        # pydantic 已在 config 層強制 dict[str, str]；wiring 的 str(_v) 為防禦性
        cfg = _cfg(tmp_path, preferences={"report_format": "json", "max_lines": "100"})
        plugins = wiring._build_plugin_set(cfg)
        store = plugins["preference_memory"]._store
        assert store.get("report_format") == "json"
        assert store.get("max_lines") == "100"

    def test_seed_idempotent_last_wins(self, tmp_path):
        cfg = _cfg(tmp_path, preferences={"k": "v"})
        wiring._build_plugin_set(cfg)
        plugins = wiring._build_plugin_set(cfg)  # 重複 wire（模擬重啟）
        assert plugins["preference_memory"]._store.get("k") == "v"
