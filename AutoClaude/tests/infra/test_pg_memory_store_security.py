"""T4（SD_04 §3 / M-6）：PgMemoryStore SQL 注入防護驗證。

驗證 _query_semantic 已改用 SQLAlchemy bindparams（:vec），
並涵蓋 inf/nan / 非數值輸入的防禦邊界。
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

# 測試需 sqlalchemy；若未安裝整體 skip
sqlalchemy = pytest.importorskip("sqlalchemy")

from autoclaude.infra.repositories.pg_memory_store import PgMemoryStore


class _FakeEngine:
    """供 PgMemoryStore __init__ 通過型別檢查的最小 stub。"""


def _make_store() -> PgMemoryStore:
    return PgMemoryStore(_FakeEngine())


# ══════════════════════════════════════════════
# T4：SQL 注入面已封閉
# ══════════════════════════════════════════════

class TestSqlInjectionDefense:
    def test_bindparams_no_string_interpolation(self):
        """確認 _query_semantic 構造的 stmt 使用 bindparams（不含未綁定的字面值）。"""
        store = _make_store()
        captured = {}

        class _FakeResult:
            def all(self): return []

        class _FakeConn:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return None
            async def execute(self, stmt):
                captured["stmt"] = stmt
                return _FakeResult()

        store._engine = MagicMock()
        store._engine.connect = lambda: _FakeConn()

        asyncio.run(store._query_semantic([0.1, 0.2, 0.3], top_k=5, threshold=0.8))

        stmt = captured["stmt"]
        compiled_text = str(stmt)
        # bindparam 名稱應在 SQL 中（:vec / :threshold / :top_k）
        assert ":vec" in compiled_text
        assert ":threshold" in compiled_text
        assert ":top_k" in compiled_text
        # 不可包含未綁定的向量字面值（'[0.1,...]'::vector）
        assert "::vector" not in compiled_text  # 已改用 CAST(:vec AS vector)
        assert "[0.1" not in compiled_text  # 字面向量不可出現在 SQL 字串

    def test_query_semantic_returns_empty_when_pgvector_unavailable(self):
        """pgvector 未安裝時應直接回 [] 不拋例外。"""
        store = _make_store()
        # 強制模擬 pgvector unavailable
        import autoclaude.infra.repositories.pg_memory_store as mod
        original = mod._PGVECTOR_AVAILABLE
        mod._PGVECTOR_AVAILABLE = False
        try:
            assert store.query_semantic([0.1, 0.2]) == []
        finally:
            mod._PGVECTOR_AVAILABLE = original


# ══════════════════════════════════════════════
# Dev-1：inf / nan / 非數值 fail-fast
# ══════════════════════════════════════════════

class TestEmbeddingValidation:
    def test_inf_in_embedding_raises_valueerror(self):
        store = _make_store()
        store._engine = MagicMock()
        with pytest.raises(ValueError, match="非有限數"):
            asyncio.run(store._query_semantic(
                [0.1, float("inf"), 0.3], top_k=5, threshold=0.8,
            ))

    def test_nan_in_embedding_raises_valueerror(self):
        store = _make_store()
        store._engine = MagicMock()
        with pytest.raises(ValueError, match="非有限數"):
            asyncio.run(store._query_semantic(
                [0.1, float("nan"), 0.3], top_k=5, threshold=0.8,
            ))

    def test_non_numeric_in_embedding_raises_valueerror(self):
        store = _make_store()
        store._engine = MagicMock()
        with pytest.raises(ValueError):
            asyncio.run(store._query_semantic(
                [0.1, "not_a_number", 0.3], top_k=5, threshold=0.8,  # type: ignore
            ))

    def test_query_semantic_propagates_value_error(self):
        """同步外層 query_semantic 對 ValueError 應 raise（不再 silent）。"""
        import autoclaude.infra.repositories.pg_memory_store as mod
        original = mod._PGVECTOR_AVAILABLE
        mod._PGVECTOR_AVAILABLE = True
        try:
            store = _make_store()
            store._engine = MagicMock()
            with pytest.raises(ValueError, match="非有限數"):
                store.query_semantic([0.1, float("inf")])
        finally:
            mod._PGVECTOR_AVAILABLE = original


# ══════════════════════════════════════════════
# Dev-2：silent failure 改為 logger.warning
# ══════════════════════════════════════════════

class TestSilentFailureMitigation:
    def test_query_logs_warning_on_failure(self, caplog):
        import logging
        store = _make_store()
        store._engine = MagicMock()
        store._engine.connect = MagicMock(side_effect=RuntimeError("connection lost"))
        with caplog.at_level(logging.WARNING, logger="autoclaude.infra.repositories.pg_memory"):
            result = store.query("some_signature")
        assert result is None
        assert any("query 失敗" in r.message for r in caplog.records)

    def test_record_success_logs_warning_on_failure(self, caplog):
        import logging
        store = _make_store()
        store._engine = MagicMock()
        store._engine.begin = MagicMock(side_effect=RuntimeError("PG down"))
        with caplog.at_level(logging.WARNING, logger="autoclaude.infra.repositories.pg_memory"):
            store.record_success("sig", "strategy", "T01")
        assert any("record_success 失敗" in r.message for r in caplog.records)
