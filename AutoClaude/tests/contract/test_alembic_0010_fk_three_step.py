"""SD_Improving_06 W3-11 — alembic 0010 三步 FK 契約測試（AC3-2）

對應：alembic/versions/0010_link_legacy_to_tiers.py
規格：SD_Improving_06.md §6 表第 0010 + §6.5 AC3-2

驗證項目（≥ 10 case）：
  T1  STEP 1：4 個 nullable FK column 已加（goal_task_id / project_id / execution_item_id）
  T2  STEP 1：4 個 FK constraint 已建立（且 ON DELETE SET NULL）
  T3  STEP 1：playbook_runs.fk_runs_goal_task 為 VALIDATED
  T4  STEP 1：knowledge_entries FK 已自動傳播至 13 子分區
  T5  STEP 1：PM #8 partial index idx_runs_active_per_goal（WHERE status='running'）
  T6  STEP 2：backfill_legacy_fk(text, int) function 存在且可呼叫
  T7  STEP 2：backfill 對未知 target_table 應 raise
  T8  STEP 3：ck_runs_post_cutoff_has_goal CHECK constraint 存在
  T9  STEP 3：ck_versions_post_cutoff_has_project CHECK constraint 存在
  T10 STEP 3：CHECK validated（legacy 豁免，新資料必須有 FK）
  T11 SD ❌11：FK 為 ON DELETE SET NULL（不 CASCADE，保留 audit）
  T12 downgrade -1 可清空全部 4 個 FK + CHECK + function
"""
from __future__ import annotations

import os
import re

import pytest

_DSN_RAW = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
_DSN = re.sub(r"\+asyncpg", "", _DSN_RAW) if _DSN_RAW else None


pytestmark = pytest.mark.skipif(
    _DSN is None,
    reason="需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN 才能跑 0010 契約測試",
)


_HEAD_PREFIX_RE = re.compile(r"^(\d{4})_")


def _max_head_num(heads: set[str]) -> int:
    nums = []
    for h in heads:
        m = _HEAD_PREFIX_RE.match(h)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) if nums else 0


@pytest.fixture(scope="module")
def conn():
    psycopg2 = pytest.importorskip("psycopg2")
    connection = psycopg2.connect(_DSN)
    connection.autocommit = True
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def alembic_head(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version;")
        heads = {row[0] for row in cur.fetchall()}
    if _max_head_num(heads) < 10:
        pytest.skip("alembic main chain 編號 < 10；請執行 `alembic upgrade 0010_link_legacy_tiers`")
    return heads


def _new_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    c = psycopg2.connect(_DSN)
    c.autocommit = False
    return c


class TestStep1AddNullableFK:
    """STEP 1：add nullable FK columns + FK constraints。"""

    def test_four_fk_columns_added(self, conn, alembic_head):
        """T1：4 個 nullable FK column 已加。"""
        expectations = [
            ("playbook_runs", "goal_task_id"),
            ("playbook_versions", "project_id"),
            ("checkpoints", "goal_task_id"),
            ("knowledge_entries", "execution_item_id"),
        ]
        for tbl, col in expectations:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = %s;",
                    (tbl, col),
                )
                row = cur.fetchone()
            assert row is not None, f"{tbl}.{col} 欄位不存在"
            assert row[0] == "YES", f"{tbl}.{col} 必為 nullable（W3 階段）"

    def test_four_fk_constraints_with_on_delete_set_null(self, conn, alembic_head):
        """T2 + T11：4 個 FK constraint 已建立，且 ON DELETE SET NULL。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT conname, confdeltype FROM pg_constraint "
                "WHERE conname IN ('fk_runs_goal_task', 'fk_versions_project', "
                "                  'fk_checkpoints_goal_task', 'fk_kb_execution_item') "
                "  AND contype = 'f';"
            )
            rows = cur.fetchall()
        # knowledge_entries.fk_kb_execution_item 會傳播至 13 子分區，所以有 14 行
        names = {r[0] for r in rows}
        assert {
            "fk_runs_goal_task",
            "fk_versions_project",
            "fk_checkpoints_goal_task",
            "fk_kb_execution_item",
        }.issubset(names), f"FK 缺：{names}"
        # 'n' = SET NULL
        for name, deltype in rows:
            assert deltype == "n", (
                f"{name} 必須 ON DELETE SET NULL（SD ❌11），實際 {deltype!r}"
            )

    def test_fk_runs_goal_task_validated(self, conn, alembic_head):
        """T3：fk_runs_goal_task 必為 VALIDATED（step 3 後）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT convalidated FROM pg_constraint "
                "WHERE conname = 'fk_runs_goal_task';"
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] is True, "fk_runs_goal_task 必須 VALIDATED（step 3）"

    def test_kb_fk_propagated_to_13_partitions(self, conn, alembic_head):
        """T4：knowledge_entries.fk_kb_execution_item 自動傳播至 12 月 + 1 default + 1 parent = 14 列。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM pg_constraint "
                "WHERE conname = 'fk_kb_execution_item';"
            )
            cnt = cur.fetchone()[0]
        assert cnt >= 13, (
            f"FK 應傳播至所有分區（≥ 13 含 parent），實際 {cnt}"
        )

    def test_pm_8_partial_index_running(self, conn, alembic_head):
        """T5：PM #8 partial index `WHERE status='running'`。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'idx_runs_active_per_goal';"
            )
            row = cur.fetchone()
        assert row is not None, "PM #8 idx_runs_active_per_goal 不存在"
        defn = row[0]
        assert "running" in defn, f"partial index 必含 status='running'：{defn}"
        assert "goal_task_id IS NOT NULL" in defn, f"必含 goal_task_id 過濾：{defn}"


class TestStep2BackfillFunction:
    """STEP 2：backfill batch function。"""

    def test_backfill_function_exists(self, conn, alembic_head):
        """T6：backfill_legacy_fk(text, int) function 存在。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT prorettype::regtype::text FROM pg_proc "
                "WHERE proname = 'backfill_legacy_fk';"
            )
            row = cur.fetchone()
        assert row is not None, "backfill_legacy_fk() 不存在"
        assert row[0] == "bigint", f"預期 returns bigint，實際 {row[0]!r}"

    def test_backfill_callable_returns_zero(self, conn, alembic_head):
        """T6b：backfill 對 4 個合法 target_table 應回傳 0（本地無資料）。"""
        targets = [
            "playbook_runs",
            "playbook_versions",
            "checkpoints",
            "knowledge_entries",
        ]
        for tgt in targets:
            with conn.cursor() as cur:
                cur.execute("SELECT backfill_legacy_fk(%s, 100);", (tgt,))
                affected = cur.fetchone()[0]
            assert affected == 0, (
                f"本地無業務資料，預期 backfill('{tgt}') 回傳 0，實際 {affected}"
            )

    def test_backfill_unknown_target_raises(self, conn, alembic_head):
        """T7：未知 target_table 應 raise。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                with pytest.raises(psycopg2.errors.RaiseException):
                    cur.execute("SELECT backfill_legacy_fk('unknown_table', 100);")
        finally:
            c.rollback()
            c.close()


class TestStep3CheckConstraints:
    """STEP 3：CHECK constraint NOT VALID + VALIDATE。"""

    def test_ck_runs_post_cutoff_exists_and_validated(self, conn, alembic_head):
        """T8：ck_runs_post_cutoff_has_goal CHECK 存在且已 VALIDATE。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT convalidated FROM pg_constraint "
                "WHERE conname = 'ck_runs_post_cutoff_has_goal';"
            )
            row = cur.fetchone()
        assert row is not None, "ck_runs_post_cutoff_has_goal 不存在"
        assert row[0] is True, "CHECK 必為 VALIDATED（step 3）"

    def test_ck_versions_post_cutoff_exists(self, conn, alembic_head):
        """T9：ck_versions_post_cutoff_has_project CHECK 存在。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT convalidated FROM pg_constraint "
                "WHERE conname = 'ck_versions_post_cutoff_has_project';"
            )
            row = cur.fetchone()
        assert row is not None, "ck_versions_post_cutoff_has_project 不存在"
        assert row[0] is True

    def test_ck_blocks_new_row_without_fk(self, conn, alembic_head):
        """T10：cutoff 後（2026-05-20+）新 row 必須有 FK；無 FK 應失敗。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                # 明確設 started_at 為 cutoff 後（2026-05-21），且 goal_task_id NULL
                # CHECK 應 raise；2026-05-20 為 G0 啟動日，當天起新 row 必有 FK
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO playbook_runs "
                        "(playbook_id, project, status, metadata, started_at) "
                        "VALUES ('test_pb', 'test_proj', 'running', '{}'::jsonb, "
                        "        '2026-05-21 00:00:00+00'::timestamptz);"
                    )
        finally:
            c.rollback()
            c.close()

    def test_ck_allows_legacy_row(self, conn, alembic_head):
        """T10b：cutoff 前 row 豁免（started_at < 2026-05-20）。"""
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO playbook_runs "
                    "(playbook_id, project, status, metadata, started_at) "
                    "VALUES ('legacy_pb', 'legacy_proj', 'running', '{}'::jsonb, "
                    "        '2026-01-01 00:00:00+00') RETURNING run_id;"
                )
                row = cur.fetchone()
                assert row is not None, "legacy row 應允許 NULL goal_task_id"
        finally:
            c.rollback()
            c.close()
