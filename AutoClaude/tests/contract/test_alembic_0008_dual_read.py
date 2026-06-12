"""SD_Improving_06 W3-4 — alembic 0008 embedding 變動維度 dual-read 契約測試

對應：alembic/versions/0008_embedding_variable_dim.py
規格：SD_Improving_06.md §6 表第 0008 + §6.5 AC4-1/4-4

驗證項目（≥ 6 case）：
  T1 embedding_v halfvec(1024) 欄位存在
  T2 embedding_model_id text 欄位存在
  T3 embedding_status / embedding_attempts 三態 + retry 欄位存在
  T4 ck_kb_embedding_status CHECK 約束（pending/ok/failed）
  T5 舊欄位 embedding vector(1536) 仍存在（deprecation 6 個月，不可直接 drop）
  T6 per-partition partial HNSW per model_id ≥ 13（halfvec_cosine_ops）
  T7 idx_kb_embedding_status partial index（WHERE != 'ok'）retry queue 支援
  T8 dim mismatch：插入錯誤維度 halfvec 失敗
"""
from __future__ import annotations

import os
import re

import pytest

_DSN_RAW = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
_DSN = re.sub(r"\+asyncpg", "", _DSN_RAW) if _DSN_RAW else None


pytestmark = pytest.mark.skipif(
    _DSN is None,
    reason="需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN 才能跑 0008 契約測試",
)


@pytest.fixture(scope="module")
def conn():
    psycopg2 = pytest.importorskip("psycopg2")
    connection = psycopg2.connect(_DSN)
    connection.autocommit = True
    yield connection
    connection.close()


_HEAD_PREFIX_RE = re.compile(r"^(\d{4})_")


def _max_head_num(heads: set[str]) -> int:
    nums = []
    for h in heads:
        m = _HEAD_PREFIX_RE.match(h)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) if nums else 0


@pytest.fixture(scope="module")
def alembic_head(conn):
    """alembic main chain head 編號 ≥ 8（含 0008 ancestry），否則 skip。"""
    with conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version;")
        heads = {row[0] for row in cur.fetchall()}
    if _max_head_num(heads) < 8:
        pytest.skip("alembic main chain 編號 < 8；請執行 `alembic upgrade 0008_embedding_variable_dim`")
    return heads


class TestAlembic0008DualRead:
    """SD_06 W3-2 alembic 0008 契約測試。"""

    def test_embedding_v_halfvec_1024_column(self, conn, alembic_head):
        """T1：embedding_v halfvec(1024) 欄位存在。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT atttypmod, t.typname FROM pg_attribute a "
                "JOIN pg_type t ON t.oid = a.atttypid "
                "WHERE a.attrelid = 'knowledge_entries'::regclass "
                "  AND a.attname = 'embedding_v';"
            )
            row = cur.fetchone()
        assert row is not None, "embedding_v 欄位不存在"
        # pgvector atttypmod 編碼維度（halfvec(1024) → atttypmod=1024）
        atttypmod, typname = row
        assert typname == "halfvec", f"預期 halfvec 型別，實際 {typname!r}"
        assert atttypmod == 1024, f"預期 halfvec(1024)，實際 atttypmod={atttypmod}"

    def test_embedding_model_id_text_column(self, conn, alembic_head):
        """T2：embedding_model_id text 欄位存在。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT t.typname FROM pg_attribute a "
                "JOIN pg_type t ON t.oid = a.atttypid "
                "WHERE a.attrelid = 'knowledge_entries'::regclass "
                "  AND a.attname = 'embedding_model_id';"
            )
            row = cur.fetchone()
        assert row is not None, "embedding_model_id 欄位不存在"
        assert row[0] == "text", f"預期 text 型別，實際 {row[0]!r}"

    def test_embedding_status_and_attempts_columns(self, conn, alembic_head):
        """T3：embedding_status text + embedding_attempts int 欄位存在。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT attname, t.typname, attnotnull FROM pg_attribute a "
                "JOIN pg_type t ON t.oid = a.atttypid "
                "WHERE a.attrelid = 'knowledge_entries'::regclass "
                "  AND a.attname IN ('embedding_status', 'embedding_attempts');"
            )
            rows = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        assert "embedding_status" in rows, "embedding_status 不存在"
        assert rows["embedding_status"][0] == "text"
        assert rows["embedding_status"][1] is True, "embedding_status 必為 NOT NULL"

        assert "embedding_attempts" in rows, "embedding_attempts 不存在"
        assert rows["embedding_attempts"][0] == "int4"
        assert rows["embedding_attempts"][1] is True, "embedding_attempts 必為 NOT NULL"

    def test_embedding_status_check_constraint(self, conn, alembic_head):
        """T4：ck_kb_embedding_status 三態約束（pending/ok/failed）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_kb_embedding_status';"
            )
            row = cur.fetchone()
        assert row is not None, "ck_kb_embedding_status 約束不存在"
        defn = row[0]
        for state in ("pending", "ok", "failed"):
            assert state in defn, f"CHECK 約束缺三態 {state!r}：{defn}"

    def test_legacy_embedding_vector_1536_kept_for_deprecation(self, conn, alembic_head):
        """T5：舊欄位 embedding vector(1536) 仍存在（6 個月 deprecation 期）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT atttypmod FROM pg_attribute a "
                "JOIN pg_type t ON t.oid = a.atttypid "
                "WHERE a.attrelid = 'knowledge_entries'::regclass "
                "  AND a.attname = 'embedding' AND t.typname = 'vector';"
            )
            row = cur.fetchone()
        assert row is not None, (
            "舊 embedding vector(1536) 欄位已被移除；SD_06 紅線 ❌10 禁止直接 drop"
        )
        assert row[0] == 1536, f"舊欄位維度漂移：atttypmod={row[0]}"

    def test_per_partition_partial_hnsw_for_embedding_v(self, conn, alembic_head):
        """T6：per-partition partial HNSW for embedding_v ≥ 13（halfvec_cosine_ops）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM pg_class c "
                "JOIN pg_am am ON am.oid = c.relam "
                "WHERE c.relname LIKE 'idx_kb_embedding_v_hnsw_%' "
                "  AND am.amname = 'hnsw';"
            )
            cnt = cur.fetchone()[0]
        assert cnt >= 13, (
            f"預期 ≥ 13 個 per-partition halfvec HNSW index，實際 {cnt}"
        )

    def test_retry_queue_partial_index(self, conn, alembic_head):
        """T7：idx_kb_embedding_status partial index 存在（WHERE != 'ok'）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'idx_kb_embedding_status';"
            )
            row = cur.fetchone()
        assert row is not None, "idx_kb_embedding_status 不存在"
        defn = row[0]
        assert "embedding_status" in defn, f"index 缺欄 embedding_status：{defn}"
        assert "<>" in defn or "!=" in defn, f"預期 partial WHERE != 'ok'：{defn}"

    def test_halfvec_dim_mismatch_rejected(self, conn, alembic_head):
        """T8：插入錯誤維度 halfvec 必須失敗。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c2 = psycopg2.connect(_DSN)
        c2.autocommit = False
        try:
            with c2.cursor() as cur:
                # 嘗試插入 1023 維 halfvec（錯誤），預期 PG 報錯
                fake_vec = "[" + ",".join(["0.1"] * 1023) + "]"
                with pytest.raises(psycopg2.errors.DataException):
                    cur.execute(
                        "INSERT INTO knowledge_entries "
                        "(error_class, error_signature, step_id, outcome, "
                        " embedding_v, embedding_model_id) "
                        "VALUES ('DIM_TEST', 'sig_dim_001', 'step_test', 'success', "
                        f"        %s::halfvec, 'fake_model');",
                        (fake_vec,),
                    )
        finally:
            c2.rollback()
            c2.close()
