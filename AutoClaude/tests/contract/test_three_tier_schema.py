"""SD_Improving_06 W3-6 — alembic 0009 三層 schema 契約測試（AC3-1 ~ AC3-5）

對應：alembic/versions/0009_three_tier_schema.py
規格：SD_Improving_06.md §6.5 AC3-1 ~ AC3-5

驗證項目（≥ 12 case）：
  T1  projects 表存在含必要欄位
  T2  goal_tasks 表存在含必要欄位 + parent_id self-FK
  T3  execution_items 表存在含必要欄位
  T4  FK CASCADE：projects → goal_tasks → execution_items
  T5  PM #1 depth ≤ 3：插入 depth=4 必須失敗
  T6  PM #1 depth ≥ 1：插入 depth=0 必須失敗
  T7  priority CHECK 1-5
  T8  status CHECK pending/running/success/failed/aborted
  T9  config_snapshot JSONB 預設 '{}'
  T10 per-table HNSW：goal_tasks m=8 / execution_items m=16
  T11 embedding_status 三態 CHECK
  T12 updated_at trigger 自動更新
  T13 owner_id 預留 nullable（0011 之前）
  T14 projects.name UNIQUE 約束
"""
from __future__ import annotations

import os
import re

import pytest

_DSN_RAW = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
_DSN = re.sub(r"\+asyncpg", "", _DSN_RAW) if _DSN_RAW else None


pytestmark = pytest.mark.skipif(
    _DSN is None,
    reason="需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN 才能跑三層 schema 契約測試",
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
    """alembic main chain head 編號 ≥ 9（含 0009 ancestry），否則 skip。"""
    with conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version;")
        heads = {row[0] for row in cur.fetchall()}
    if _max_head_num(heads) < 9:
        pytest.skip("alembic main chain 編號 < 9；請執行 `alembic upgrade 0009_three_tier_schema`")
    return heads


def _new_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    c = psycopg2.connect(_DSN)
    c.autocommit = False
    return c


class TestThreeTierSchemaStructure:
    """AC3-1：三表結構驗證。"""

    def test_projects_table_exists_with_required_columns(self, conn, alembic_head):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'projects';"
            )
            cols = {r[0] for r in cur.fetchall()}
        required = {
            "project_id", "name", "description", "config_snapshot",
            "owner_id", "created_at", "updated_at",
        }
        missing = required - cols
        assert not missing, f"projects 缺欄：{missing}"

    def test_goal_tasks_table_with_parent_self_fk(self, conn, alembic_head):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'goal_tasks';"
            )
            cols = {r[0] for r in cur.fetchall()}
        required = {
            "goal_task_id", "project_id", "parent_id", "title",
            "depth", "priority", "status", "config_snapshot",
            "embedding_v", "embedding_model_id", "embedding_status",
            "embedding_attempts", "created_at", "updated_at",
        }
        missing = required - cols
        assert not missing, f"goal_tasks 缺欄：{missing}"

        # 確認 parent_id self-reference FK
        with conn.cursor() as cur:
            cur.execute(
                "SELECT confrelid::regclass::text FROM pg_constraint "
                "WHERE conrelid = 'goal_tasks'::regclass "
                "  AND contype = 'f' "
                "  AND conkey = (SELECT array[attnum] FROM pg_attribute "
                "                WHERE attrelid='goal_tasks'::regclass AND attname='parent_id');"
            )
            row = cur.fetchone()
        assert row is not None and row[0] == "goal_tasks", (
            "parent_id 必須 self-reference 至 goal_tasks"
        )

    def test_execution_items_table_columns(self, conn, alembic_head):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'execution_items';"
            )
            cols = {r[0] for r in cur.fetchall()}
        required = {
            "exec_id", "goal_task_id", "action", "status",
            "estimated_minutes", "actual_minutes", "result",
            "embedding_v", "embedding_model_id", "embedding_status",
            "embedding_attempts", "created_at", "updated_at",
        }
        missing = required - cols
        assert not missing, f"execution_items 缺欄：{missing}"


class TestFKCascade:
    """AC3-1：FK CASCADE 驗證（projects → goal_tasks → execution_items）。"""

    def test_delete_project_cascades_to_goal_tasks(self, conn, alembic_head):
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name) VALUES ('cascade_test_p1') "
                    "RETURNING project_id;"
                )
                pid = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO goal_tasks (project_id, title, depth) "
                    "VALUES (%s, 'gt1', 1) RETURNING goal_task_id;",
                    (pid,),
                )
                gtid = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO execution_items (goal_task_id, action) "
                    "VALUES (%s, 'a1') RETURNING exec_id;",
                    (gtid,),
                )
                # delete project
                cur.execute("DELETE FROM projects WHERE project_id = %s;", (pid,))
                cur.execute("SELECT count(*) FROM goal_tasks WHERE goal_task_id = %s;", (gtid,))
                assert cur.fetchone()[0] == 0, "goal_tasks 未隨 projects CASCADE 刪除"
                cur.execute(
                    "SELECT count(*) FROM execution_items WHERE goal_task_id = %s;",
                    (gtid,),
                )
                assert cur.fetchone()[0] == 0, (
                    "execution_items 未隨 goal_tasks CASCADE 刪除"
                )
        finally:
            c.rollback()
            c.close()


class TestDepthConstraint:
    """AC3-1：PM #1 sub-task depth ≤ 3 強制。"""

    def test_depth_4_rejected(self, conn, alembic_head):
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name) VALUES ('depth_test_p') "
                    "RETURNING project_id;"
                )
                pid = cur.fetchone()[0]
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO goal_tasks (project_id, title, depth) "
                        "VALUES (%s, 'bad', 4);",
                        (pid,),
                    )
        finally:
            c.rollback()
            c.close()

    def test_depth_0_rejected(self, conn, alembic_head):
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name) VALUES ('depth0_test_p') "
                    "RETURNING project_id;"
                )
                pid = cur.fetchone()[0]
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO goal_tasks (project_id, title, depth) "
                        "VALUES (%s, 'bad', 0);",
                        (pid,),
                    )
        finally:
            c.rollback()
            c.close()


class TestCheckConstraints:
    """AC3-1：其他 CHECK 約束驗證。"""

    def test_priority_out_of_range_rejected(self, conn, alembic_head):
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name) VALUES ('prio_test_p') "
                    "RETURNING project_id;"
                )
                pid = cur.fetchone()[0]
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO goal_tasks (project_id, title, depth, priority) "
                        "VALUES (%s, 'bad', 1, 6);",
                        (pid,),
                    )
        finally:
            c.rollback()
            c.close()

    def test_status_invalid_rejected(self, conn, alembic_head):
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name) VALUES ('status_test_p') "
                    "RETURNING project_id;"
                )
                pid = cur.fetchone()[0]
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO goal_tasks (project_id, title, depth, status) "
                        "VALUES (%s, 'bad', 1, 'unknown');",
                        (pid,),
                    )
        finally:
            c.rollback()
            c.close()

    def test_embedding_status_three_state(self, conn, alembic_head):
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name) VALUES ('embstatus_test_p') "
                    "RETURNING project_id;"
                )
                pid = cur.fetchone()[0]
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO goal_tasks "
                        "(project_id, title, depth, embedding_status) "
                        "VALUES (%s, 'bad', 1, 'unknown_status');",
                        (pid,),
                    )
        finally:
            c.rollback()
            c.close()


class TestDefaults:
    """AC3-1：欄位預設值。"""

    def test_config_snapshot_default_empty_jsonb(self, conn, alembic_head):
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name) VALUES ('cs_test') "
                    "RETURNING config_snapshot;"
                )
                cs = cur.fetchone()[0]
                assert cs == {}, f"config_snapshot 預設應為空 JSONB，實際 {cs!r}"
        finally:
            c.rollback()
            c.close()

    def test_owner_id_nullable_pre_rbac(self, conn, alembic_head):
        """owner_id 必須為 nullable（0011_rbac_tables 補 FK 前）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name='projects' AND column_name='owner_id';"
            )
            row = cur.fetchone()
        assert row[0] == "YES", "owner_id 必為 nullable（W3 階段）"


class TestPerTableHNSW:
    """AC3-5：per-table HNSW 調參驗證。"""

    def test_goal_tasks_hnsw_m_8(self, conn, alembic_head):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_get_indexdef(indexrelid) FROM pg_index i "
                "JOIN pg_class c ON c.oid = i.indexrelid "
                "WHERE c.relname = 'idx_goal_tasks_embedding_hnsw';"
            )
            row = cur.fetchone()
        assert row is not None, "idx_goal_tasks_embedding_hnsw 不存在"
        defn = row[0]
        assert "m='8'" in defn or "m=8" in defn, (
            f"goal_tasks HNSW m 必為 8（SD_06 §4 W3-3）：{defn}"
        )
        assert "halfvec_cosine_ops" in defn, f"必須用 halfvec_cosine_ops：{defn}"

    def test_execution_items_hnsw_m_16(self, conn, alembic_head):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_get_indexdef(indexrelid) FROM pg_index i "
                "JOIN pg_class c ON c.oid = i.indexrelid "
                "WHERE c.relname = 'idx_execution_items_embedding_hnsw';"
            )
            row = cur.fetchone()
        assert row is not None, "idx_execution_items_embedding_hnsw 不存在"
        defn = row[0]
        assert "m='16'" in defn or "m=16" in defn, (
            f"execution_items HNSW m 必為 16（SD_06 §4 W3-3）：{defn}"
        )


class TestUniqueConstraints:
    """AC3-1：UNIQUE 約束。"""

    def test_projects_name_unique(self, conn, alembic_head):
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute("INSERT INTO projects (name) VALUES ('unique_n_001');")
                with pytest.raises(psycopg2.errors.UniqueViolation):
                    cur.execute("INSERT INTO projects (name) VALUES ('unique_n_001');")
        finally:
            c.rollback()
            c.close()


class TestUpdatedAtTrigger:
    """AC3-1：updated_at trigger 自動更新。"""

    def test_updated_at_trigger_on_update(self, conn, alembic_head):
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name) VALUES ('upd_test_001') "
                    "RETURNING project_id, updated_at;"
                )
                pid, t1 = cur.fetchone()
                cur.execute("SELECT pg_sleep(0.01);")
                cur.execute(
                    "UPDATE projects SET description='new desc' "
                    "WHERE project_id = %s RETURNING updated_at;",
                    (pid,),
                )
                t2 = cur.fetchone()[0]
                assert t2 > t1, f"updated_at trigger 未觸發：{t1} → {t2}"
        finally:
            c.rollback()
            c.close()
