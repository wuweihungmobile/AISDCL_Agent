"""Phase 1 三個 PG adapter 單元測試（QA audit P1-3 修復；mock engine，無真 PG）。

驗證意圖：PG 路徑（both/db_only）在 pg_real e2e 之前必須有 gating 的單元防線 ——
buffer/flush 列數、counter 恢復過濾、UPSERT 必須用 SQL func.now()（非字面字串，
SA·SD 複核發現之 bug 的回歸鎖）、summarize 聯集語意與 File 後端對等。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

pytest.importorskip("sqlalchemy")

from autoclaude.infra.adapters.local_kb_metric_store import _p95 as _local_p95
from autoclaude.infra.adapters.pg_goal_progress_ledger import PgGoalProgressLedger
from autoclaude.infra.adapters.pg_kb_metric_store import PgKbMetricStore
from autoclaude.infra.adapters.pg_kb_metric_store import _p95 as _pg_p95
from autoclaude.infra.adapters.pg_preference_store import PgPreferenceStore


# ── fake async engine ────────────────────────────────────────
class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeConn:
    def __init__(self, owner):
        self._owner = owner

    async def execute(self, stmt, params=None):
        self._owner.executed.append((stmt, params))
        return _FakeResult(self._owner.rows)


class _AsyncCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class _FakeEngine:
    """記錄 executed (stmt, params)；rows 為查詢回傳值。"""

    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed: list = []

    def connect(self):
        return _AsyncCtx(_FakeConn(self))

    def begin(self):
        return _AsyncCtx(_FakeConn(self))


# ── _p95 邊界（兩份實作行為一致）─────────────────────────────
class TestP95Boundaries:
    @pytest.mark.parametrize("p95", [_local_p95, _pg_p95])
    def test_empty_returns_zero(self, p95):
        assert p95([]) == 0.0

    @pytest.mark.parametrize("p95", [_local_p95, _pg_p95])
    def test_small_sample_returns_max(self, p95):
        assert p95([3.0, 9.0, 1.0]) == 9.0

    @pytest.mark.parametrize("p95", [_local_p95, _pg_p95])
    def test_large_sample_p95_index(self, p95):
        samples = [float(i) for i in range(1, 101)]  # 1..100
        assert p95(samples) == 95.0  # sorted[int(0.95*100)-1] = sorted[94] = 95.0


# ── PgKbMetricStore ──────────────────────────────────────────
class TestPgKbMetricStore:
    def _store(self, rows=None) -> tuple[PgKbMetricStore, _FakeEngine]:
        engine = _FakeEngine(rows)
        return PgKbMetricStore(engine), engine

    def test_restore_filters_total_suffix_latest_only(self):
        rows = [
            ("kb_queries_total", 7.0, datetime.now(UTC)),
            ("kb_queries_total", 3.0, datetime.now(UTC)),  # 較舊，應忽略
            ("kb_query_latency_ms", 12.0, datetime.now(UTC)),  # 非 _total，不恢復
        ]
        store, _ = self._store(rows)
        snap = store.snapshot()
        assert snap["kb_queries_total"].value == 7.0
        assert "kb_query_latency_ms" not in snap

    def test_flush_inserts_one_row_per_metric(self):
        store, engine = self._store()
        store.record_counter("kb_queries_total", 2)
        store.record_histogram("kb_query_latency_ms", 5.0)
        engine.executed.clear()  # 移除 restore 期間的查詢
        store.flush()
        assert len(engine.executed) == 1
        _stmt, params = engine.executed[0]
        assert {p["metric_name"] for p in params} == {
            "kb_queries_total", "kb_query_latency_ms",
        }

    def test_flush_empty_buffer_is_noop(self):
        store, engine = self._store()
        engine.executed.clear()
        store.flush()
        assert engine.executed == []

    def test_broken_engine_degrades_without_raising(self):
        class _BrokenEngine:
            def connect(self):
                raise RuntimeError("no pg")

            def begin(self):
                raise RuntimeError("no pg")

        store = PgKbMetricStore(_BrokenEngine())  # restore 失敗以零起算
        store.record_counter("kb_queries_total", 1)
        store.flush()  # warning 不 raise
        assert store.snapshot()["kb_queries_total"].value == 1.0


# ── PgPreferenceStore ────────────────────────────────────────
class TestPgPreferenceStore:
    def test_upsert_uses_sql_now_function_not_literal(self):
        """SA·SD 複核 bug 回歸鎖：updated_at 必須是 SQL now() 函式，
        不可是字面字串 'now()'（PG 會 invalid input syntax）。"""
        engine = _FakeEngine()
        PgPreferenceStore(engine).set("k", "v")
        stmt, _ = engine.executed[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "now()" in compiled.lower()  # 出現在 SQL 文本（函式）
        # 綁定參數中不得有字面 'now()' 字串
        params = stmt.compile().params
        assert "now()" not in [v for v in params.values() if isinstance(v, str)]

    def test_list_merged_playbook_overrides_global(self):
        rows = [("global", "k", "g"), ("global", "a", "1"), ("playbook:P", "k", "p")]
        engine = _FakeEngine(rows)
        merged = PgPreferenceStore(engine).list()
        assert merged == {"k": "p", "a": "1"}

    def test_get_returns_none_when_missing(self):
        assert PgPreferenceStore(_FakeEngine()).get("nope") is None

    def test_db_failure_degrades_to_safe_defaults(self):
        class _BrokenEngine:
            def connect(self):
                raise RuntimeError("no pg")

            def begin(self):
                raise RuntimeError("no pg")

        store = PgPreferenceStore(_BrokenEngine())
        store.set("k", "v")  # warning 不 raise
        assert store.get("k") is None
        assert store.list() == {}


# ── PgGoalProgressLedger ─────────────────────────────────────
class TestPgGoalProgressLedger:
    def test_record_insert_row_structure(self):
        engine = _FakeEngine()
        PgGoalProgressLedger(engine).record(
            "g1", playbook_id="P", completed_features=["T01"], progress_pct=50.0,
        )
        _stmt, params = engine.executed[0]
        row = params[0]
        assert row["goal_task_id"] == "g1"
        assert row["completed_features"] == ["T01"]
        assert row["progress_pct"] == 50.0

    def test_summarize_union_and_latest_pct(self):
        now = datetime.now(UTC)
        rows = [
            (SimpleNamespace(completed_features=["A", "B"], progress_pct=50.0,
                             recorded_at=now - timedelta(minutes=1)),),
            (SimpleNamespace(completed_features=["B", "C"], progress_pct=75.0,
                             recorded_at=now),),
        ]
        summary = PgGoalProgressLedger(_FakeEngine(rows)).summarize("g1")
        assert summary["run_count"] == 2
        assert summary["completed_features"] == ["A", "B", "C"]
        assert summary["progress_pct"] == 75.0

    def test_db_failure_returns_empty_summary(self):
        class _BrokenEngine:
            def connect(self):
                raise RuntimeError("no pg")

            def begin(self):
                raise RuntimeError("no pg")

        summary = PgGoalProgressLedger(_BrokenEngine()).summarize("g1")
        assert summary["run_count"] == 0
        assert summary["completed_features"] == []


class TestPgKbMetricStoreQueryWindowAndGuards:
    """補 coverage：query_window 成功路徑 + ImportError 守門（SRD §4 單模組 ≥90%）。"""

    def test_query_window_maps_rows_to_metric_values(self):
        now = datetime.now(UTC)
        rows = [
            (SimpleNamespace(metric_name="kb_queries_total", value=5.0,
                             window_start_at=now - timedelta(hours=1),
                             window_end_at=now, run_id=None),),
        ]
        store = PgKbMetricStore(_FakeEngine(rows))
        result = store.query_window("kb_queries_total", now - timedelta(days=1))
        assert len(result) == 1
        assert result[0].metric_name == "kb_queries_total"
        assert result[0].value == 5.0
        assert result[0].run_id is None

    def test_import_guard_raises_without_sqlalchemy(self, monkeypatch):
        from autoclaude.infra.adapters import pg_kb_metric_store as mod

        monkeypatch.setattr(mod, "_SQLALCHEMY_AVAILABLE", False)
        with pytest.raises(ImportError, match="postgres"):
            mod.PgKbMetricStore(_FakeEngine())
