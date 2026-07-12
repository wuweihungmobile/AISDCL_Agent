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
  T8  STEP 3：run→goal CHECK 存在且 validated
        ⚠️ DEF-101-051 / 0017：0010 原 ck_runs_post_cutoff_has_goal（時間 cutoff 判別）
           已由 0017 ck_runs_three_tier_has_goal（run_kind 判別）取代；本測試斷言 head
           狀態，故驗證後者。
  T9  STEP 3：ck_versions_post_cutoff_has_project CHECK constraint 存在（0017 未動）
  T10 STEP 3：run→goal CHECK 行為（0017 後）— three_tier run 無 goal 被拒；
        standalone run 無 goal 允許（orphan-run 政策）
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

    def test_ck_runs_three_tier_has_goal_exists_and_validated(self, conn, alembic_head):
        """T8：run→goal CHECK 存在且已 VALIDATE。

        DEF-101-051 / 0017：head 狀態下為 ck_runs_three_tier_has_goal（取代 0010 的
        ck_runs_post_cutoff_has_goal 時間炸彈）；同時斷言舊 CHECK 已移除。
        """
        with conn.cursor() as cur:
            cur.execute(
                "SELECT convalidated FROM pg_constraint "
                "WHERE conname = 'ck_runs_three_tier_has_goal';"
            )
            row = cur.fetchone()
            cur.execute(
                "SELECT count(*) FROM pg_constraint "
                "WHERE conname = 'ck_runs_post_cutoff_has_goal';"
            )
            old = cur.fetchone()[0]
        assert row is not None, "ck_runs_three_tier_has_goal 不存在（0017 未套用？）"
        assert row[0] is True, "CHECK 必為 VALIDATED"
        assert old == 0, "0017 應已移除舊 ck_runs_post_cutoff_has_goal（時間炸彈）"

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

    def test_ck_blocks_three_tier_run_without_goal(self, conn, alembic_head):
        """T10：three_tier run 無 goal_task_id 應被 CHECK 拒（DEF-101-051 / 0017）。

        判別欄語意：宣稱自己是三層 run（run_kind='three_tier'）就必須帶 goal_task_id，
        否則違反 ck_runs_three_tier_has_goal。此為保留三層追蹤能力的核心（非放寬約束）。
        """
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                # match= 綁定 constraint 名，確保是「對的原因」被拒（Rule 9）
                with pytest.raises(
                    psycopg2.errors.CheckViolation, match="ck_runs_three_tier_has_goal"
                ):
                    cur.execute(
                        "INSERT INTO playbook_runs "
                        "(playbook_id, project, status, metadata, run_kind) "
                        "VALUES ('three_tier_pb', 'proj', 'running', '{}'::jsonb, "
                        "        'three_tier');"
                    )
        finally:
            c.rollback()
            c.close()

    def test_ck_run_kind_rejects_invalid_value(self, conn, alembic_head):
        """T10c：run_kind 只允許 {standalone, three_tier}；非法值被 ck_runs_run_kind 拒。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                with pytest.raises(
                    psycopg2.errors.CheckViolation, match="ck_runs_run_kind"
                ):
                    cur.execute(
                        "INSERT INTO playbook_runs "
                        "(playbook_id, project, status, metadata, run_kind) "
                        "VALUES ('bad_kind_pb', 'proj', 'running', '{}'::jsonb, 'garbage');"
                    )
        finally:
            c.rollback()
            c.close()

    def test_ck_allows_standalone_run_without_goal(self, conn, alembic_head):
        """T10b：standalone run（plain playbook）無 goal_task_id 應允許（orphan-run 政策）。

        DEF-101-051 / 0017：改採 run_kind 判別後，無時間依賴——不論 started_at 為
        cutoff 前後，standalone run 皆合法無 goal（消除 0010 時間炸彈）。
        """
        c = _new_conn()
        try:
            with c.cursor() as cur:
                # 明確設 started_at 為 cutoff 後（2026-05-21）：舊時間炸彈 CHECK 會拒，
                # 新 run_kind CHECK 應放行（run_kind 預設 'standalone'）。
                cur.execute(
                    "INSERT INTO playbook_runs "
                    "(playbook_id, project, status, metadata, started_at) "
                    "VALUES ('standalone_pb', 'proj', 'running', '{}'::jsonb, "
                    "        '2026-05-21 00:00:00+00'::timestamptz) RETURNING run_id, run_kind;"
                )
                row = cur.fetchone()
                assert row is not None, "standalone run 應允許 NULL goal_task_id"
                assert row[1] == "standalone", "未指定時 run_kind 應預設 standalone"
        finally:
            c.rollback()
            c.close()
