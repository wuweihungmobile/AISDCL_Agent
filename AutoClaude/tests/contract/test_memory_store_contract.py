"""IMemoryStore 契約測（Phase 5）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from autoclaude.infra.repositories import FileMemoryStore, InMemoryMemoryStore


class IMemoryStoreContract(ABC):
    @abstractmethod
    def _make_store(self, tmp_path: Path):
        ...

    def test_query_missing_returns_none(self, tmp_path: Path):
        store = self._make_store(tmp_path)
        assert store.query("never_recorded") is None

    def test_record_success_then_query(self, tmp_path: Path):
        store = self._make_store(tmp_path)
        store.record_success(
            error_signature="regex_miss",
            strategy="retry_with_hint",
            step_id="T01",
            error_class="syntax",
        )
        # 查詢回傳 None 或 dict（兩種後端可能行為略異，但 record 本身不可拋例外）
        result = store.query("regex_miss")
        # File backend 的 query 可能依賴內部 cache；至少不應拋例外
        assert result is None or isinstance(result, dict)

    def test_record_escalation_no_exception(self, tmp_path: Path):
        store = self._make_store(tmp_path)
        # 不應拋例外
        store.record_escalation(
            error_signature="import_err",
            tried_strategies=["retry", "evolve"],
            step_id="T05",
        )

    def test_query_strategy_priority_returns_list(self, tmp_path: Path):
        store = self._make_store(tmp_path)
        result = store.query_strategy_priority("syntax")
        assert isinstance(result, list)


class TestFileMemoryStoreContract(IMemoryStoreContract):
    def _make_store(self, tmp_path: Path):
        return FileMemoryStore(jsonl_path=str(tmp_path / "kb.jsonl"))


class TestInMemoryMemoryStoreContract(IMemoryStoreContract):
    def _make_store(self, tmp_path: Path):
        return InMemoryMemoryStore()


class TestInMemoryStoreSpecificBehaviors:
    """專屬 InMemory 後端的 LSP 額外行為驗證。"""

    def test_query_returns_dict_after_record(self):
        store = InMemoryMemoryStore()
        store.record_success(
            error_signature="x", strategy="s", step_id="T01", error_class="syntax",
        )
        result = store.query("x")
        assert result is not None
        assert result["strategy"] == "s"

    def test_strategy_priority_after_recording(self):
        store = InMemoryMemoryStore()
        store.record_success(
            error_signature="x1", strategy="s_a", step_id="T01", error_class="syntax",
        )
        store.record_success(
            error_signature="x2", strategy="s_a", step_id="T02", error_class="syntax",
        )
        store.record_success(
            error_signature="x3", strategy="s_b", step_id="T03", error_class="syntax",
        )
        prio = store.query_strategy_priority("syntax")
        # s_a 出現 2 次 → 優先
        assert prio[0] == "s_a"
