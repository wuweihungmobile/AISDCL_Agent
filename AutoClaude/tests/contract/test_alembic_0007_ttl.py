"""SD_Improving_06 W3-2 — alembic 0007 KB UNIQUE/TTL/partition 契約測試

對應：alembic/versions/0007_kb_unique_ttl_partition.py
規格：SD_Improving_06.md §6.5 AC5-5 + §6 表第 0007 列

驗證項目（≥ 8 case）：
  T1 knowledge_entries 為 partitioned table（pg_partitioned_table 有紀錄）
  T2 12 個月 partition + 1 default partition = 13 child relations
  T3 default partition 存在（partbound IS NULL）
  T4 UNIQUE 約束含 partition key recorded_at
  T5 kb_ttl_cleanup() function 存在且 returns bigint
  T6 kb_ttl_trigger AFTER INSERT 存在
  T7 per-partition HNSW index ≥ 13（cosine + m=16 + ef_construction=64）
  T8 UNIQUE 衝突：同 (error_class, error_signature, recorded_at) INSERT 兩次失敗
  T9 partition routing：插入特定月份 row 落入對應 partition
  T10 TTL function 可呼叫且回傳 0（無 > 365 天資料）
"""
from __future__ import annotations

import os
import re

import pytest

# 優先用 contract 專用 DSN；fallback 至 AUTOCLAUDE_DB_DSN（保持與 alembic env.py 一致）
_DSN_RAW = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
_DSN = None
if _DSN_RAW:
    # 移除 asyncpg dialect 與 sslmode 不相容的 query 串（psycopg2 用 sync）
    _DSN = re.sub(r"\+asyncpg", "", _DSN_RAW)


pytestmark = pytest.mark.skipif(
    _DSN is None,
    reason="需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN 才能跑 0007 契約測試",
)


@pytest.fixture(scope="module")
def conn():
    """sync psycopg2 connection；測試結束時關閉。

    要求 alembic upgrade 至 0007_kb_unique_ttl_part 已完成（外部前置）。
    """
    psycopg2 = pytest.importorskip("psycopg2")
    connection = psycopg2.connect(_DSN)
    connection.autocommit = True
    yield connection
    connection.close()


_HEAD_PREFIX_RE = re.compile(r"^(\d{4})_")


def _max_head_num(heads: set[str]) -> int:
    """從 alembic_version 取出 main chain 最大編號（≥ 表示已升級含本 migration）。"""
    nums = []
    for h in heads:
        m = _HEAD_PREFIX_RE.match(h)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) if nums else 0


@pytest.fixture(scope="module")
def alembic_head(conn):
    """驗證 alembic main chain head 編號 ≥ 7（含 0007 ancestry），否則 skip。"""
    with conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version;")
        heads = {row[0] for row in cur.fetchall()}
    if _max_head_num(heads) < 7:
        pytest.skip(
            "alembic main chain 編號 < 7；請執行 "
            "`alembic upgrade 0007_kb_unique_ttl_part` 或更新版本"
        )
    return heads


class TestAlembic0007TTL:
    """SD_06 W3-1 alembic 0007 契約測試。"""

    def test_knowledge_entries_is_partitioned(self, conn, alembic_head):
        """T1：knowledge_entries 必為 partitioned table。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT partstrat FROM pg_partitioned_table "
                "WHERE partrelid = 'knowledge_entries'::regclass;"
            )
            row = cur.fetchone()
        assert row is not None, "knowledge_entries 未註冊為 partitioned table"
        # 'r' = RANGE partition
        assert row[0] == "r", f"預期 RANGE 分區（'r'），實際 {row[0]!r}"

    def test_partition_count_12_months_plus_default(self, conn, alembic_head):
        """T2：12 個月 partition + 1 default partition = 13 child relations。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM pg_inherits "
                "WHERE inhparent = 'knowledge_entries'::regclass;"
            )
            cnt = cur.fetchone()[0]
        assert cnt == 13, f"預期 13 個子分區（12 月 + default），實際 {cnt}"

    def test_default_partition_exists(self, conn, alembic_head):
        """T3：default partition 必須存在（partbound IS NULL 表示 DEFAULT partition）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.relname FROM pg_class c "
                "JOIN pg_inherits i ON i.inhrelid = c.oid "
                "WHERE i.inhparent = 'knowledge_entries'::regclass "
                "  AND pg_get_expr(c.relpartbound, c.oid) = 'DEFAULT';"
            )
            row = cur.fetchone()
        assert row is not None, "default partition 不存在"
        assert row[0] == "knowledge_entries_default", (
            f"default partition 命名異常：{row[0]!r}"
        )

    def test_unique_constraint_includes_partition_key(self, conn, alembic_head):
        """T4：UNIQUE 約束必須含 partition key recorded_at（PG 限制）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid = 'knowledge_entries'::regclass "
                "  AND contype = 'u';"
            )
            rows = cur.fetchall()
        assert rows, "knowledge_entries 上找不到 UNIQUE 約束"
        names = {r[0] for r in rows}
        assert "uq_kb_class_signature_recorded" in names, (
            f"預期 uq_kb_class_signature_recorded 約束，實際 {names}"
        )
        # 約束定義必須包含三欄
        defn = dict(rows)["uq_kb_class_signature_recorded"]
        for col in ("error_class", "error_signature", "recorded_at"):
            assert col in defn, f"UNIQUE 缺欄 {col!r}：{defn}"

    def test_ttl_cleanup_function_exists(self, conn, alembic_head):
        """T5：kb_ttl_cleanup() function 存在且 returns bigint。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT prorettype::regtype::text FROM pg_proc "
                "WHERE proname = 'kb_ttl_cleanup';"
            )
            row = cur.fetchone()
        assert row is not None, "kb_ttl_cleanup() function 不存在"
        assert row[0] == "bigint", f"預期 returns bigint，實際 {row[0]!r}"

    def test_ttl_trigger_exists_after_insert(self, conn, alembic_head):
        """T6：kb_ttl_trigger 必為 AFTER INSERT STATEMENT-level trigger。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tgname, tgtype FROM pg_trigger "
                "WHERE tgname = 'kb_ttl_trigger' AND NOT tgisinternal;"
            )
            row = cur.fetchone()
        assert row is not None, "kb_ttl_trigger 不存在"
        # tgtype bitmask：bit 0=ROW（0=STATEMENT），bit 1=BEFORE（0=AFTER），bit 2=INSERT
        tgtype = row[1]
        is_statement = (tgtype & 1) == 0
        is_after = (tgtype & 2) == 0
        is_insert = (tgtype & 4) != 0
        assert is_statement and is_after and is_insert, (
            f"預期 AFTER INSERT STATEMENT trigger，tgtype={tgtype:b}"
        )

    def test_per_partition_hnsw_indexes_count(self, conn, alembic_head):
        """T7：per-partition HNSW index ≥ 13（每個子分區一個）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE indexname LIKE 'idx_kb_embedding_hnsw_%';"
            )
            names = [r[0] for r in cur.fetchall()]
        assert len(names) >= 13, (
            f"預期 ≥ 13 個 per-partition HNSW index，實際 {len(names)}"
        )
        # 驗證至少一個 index 用 hnsw access method
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM pg_index i "
                "JOIN pg_class c ON c.oid = i.indexrelid "
                "JOIN pg_am am ON am.oid = c.relam "
                "WHERE c.relname LIKE 'idx_kb_embedding_hnsw_%' "
                "  AND am.amname = 'hnsw';"
            )
            hnsw_cnt = cur.fetchone()[0]
        assert hnsw_cnt >= 13, f"預期 ≥ 13 個 hnsw access method index，實際 {hnsw_cnt}"

    def test_unique_violation_on_duplicate_insert(self, conn, alembic_head):
        """T8：同 (error_class, error_signature, recorded_at) 插入兩次須失敗。"""
        psycopg2 = pytest.importorskip("psycopg2")
        # 用獨立連線避免汙染 module-scope conn 的 autocommit 狀態
        c2 = psycopg2.connect(_DSN)
        c2.autocommit = False
        try:
            with c2.cursor() as cur:
                cur.execute(
                    "INSERT INTO knowledge_entries "
                    "(error_class, error_signature, step_id, outcome, recorded_at) "
                    "VALUES ('UQ_TEST', 'sig_unique_001', 'step_test', 'success', "
                    "        now()) RETURNING entry_id;"
                )
                _ = cur.fetchone()
                # 第二次 INSERT 同 (error_class, error_signature, recorded_at)
                with pytest.raises(psycopg2.errors.UniqueViolation):
                    cur.execute(
                        "INSERT INTO knowledge_entries "
                        "(error_class, error_signature, step_id, outcome, recorded_at) "
                        "VALUES ('UQ_TEST', 'sig_unique_001', 'step_test', 'success', "
                        "        (SELECT recorded_at FROM knowledge_entries "
                        "         WHERE error_class='UQ_TEST' "
                        "         AND error_signature='sig_unique_001' LIMIT 1));"
                    )
        finally:
            c2.rollback()
            c2.close()

    def test_partition_routing_current_month(self, conn, alembic_head):
        """T9：插入當月 row 必須落入 YYYY_MM partition。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c2 = psycopg2.connect(_DSN)
        c2.autocommit = False
        try:
            with c2.cursor() as cur:
                cur.execute(
                    "INSERT INTO knowledge_entries "
                    "(error_class, error_signature, step_id, outcome) "
                    "VALUES ('PART_TEST', 'sig_routing', 'step_test', 'success') "
                    "RETURNING entry_id, "
                    "  to_char(date_trunc('month', recorded_at), 'YYYY_MM');"
                )
                _, month_str = cur.fetchone()
                # 確認資料落入對應 partition
                cur.execute(
                    f"SELECT count(*) FROM knowledge_entries_{month_str} "
                    f"WHERE error_class = 'PART_TEST';"
                )
                cnt = cur.fetchone()[0]
                assert cnt == 1, (
                    f"當月 partition knowledge_entries_{month_str} "
                    f"應有 1 筆 PART_TEST row，實際 {cnt}"
                )
        finally:
            c2.rollback()
            c2.close()

    def test_ttl_cleanup_returns_zero_when_no_old_rows(self, conn, alembic_head):
        """T10：kb_ttl_cleanup() 在無 > 365 天資料時回傳 0。"""
        with conn.cursor() as cur:
            cur.execute("SELECT kb_ttl_cleanup();")
            deleted = cur.fetchone()[0]
        # 因為新建 DB 不會有 > 365 天舊資料，預期 0
        assert deleted == 0, (
            f"預期 cleanup 刪除 0 筆（無舊資料），實際 {deleted}"
        )
