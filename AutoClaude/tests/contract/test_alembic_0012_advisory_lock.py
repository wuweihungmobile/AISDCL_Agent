"""SD_Improving_06 W3-15 — alembic 0012 YAML import staging + advisory lock 契約測試

對應：alembic/versions/0012_yaml_import_staging.py
規格：SD_Improving_06.md §6 表第 0012 + §4 W3-6

驗證項目（≥ 6 case）：
  T1 yaml_import_jobs 表 + 必要欄位（mode/status/sha256 等）
  T2 yaml_import_diffs 表 + FK CASCADE 至 jobs
  T3 mode CHECK（dry_run/apply）
  T4 status CHECK 5 態
  T5 UNIQUE(playbook_id, yaml_sha256, mode) 防重複 import
  T6 try_acquire_import_lock(text) function 存在
  T7 並發 import：第二個 lock acquire 失敗
  T8 鎖在 transaction commit 後自動釋放
  T9 has_active_import_for(text) 偵測 pending/running job
  T10 yaml_import_diffs target_table + diff_type CHECK
"""
from __future__ import annotations

import os
import re

import pytest

_DSN_RAW = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
_DSN = re.sub(r"\+asyncpg", "", _DSN_RAW) if _DSN_RAW else None


pytestmark = pytest.mark.skipif(
    _DSN is None,
    reason="需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN 才能跑 0012 契約測試",
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
    if _max_head_num(heads) < 12:
        pytest.skip("alembic main chain 編號 < 12；請執行 `alembic upgrade 0012_yaml_import_staging`")
    return heads


def _new_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    c = psycopg2.connect(_DSN)
    c.autocommit = False
    return c


class TestYAMLImportTables:
    """AC: yaml_import_jobs + yaml_import_diffs 結構。"""

    def test_yaml_import_jobs_columns(self, conn, alembic_head):
        """T1：yaml_import_jobs 表 + 必要欄位。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'yaml_import_jobs';"
            )
            cols = {r[0] for r in cur.fetchall()}
        required = {
            "job_id", "playbook_id", "yaml_sha256", "mode", "status",
            "started_at", "finished_at", "projects_created",
            "goal_tasks_created", "execution_items_created",
            "error_message", "triggered_by",
        }
        missing = required - cols
        assert not missing, f"yaml_import_jobs 缺欄：{missing}"

    def test_yaml_import_diffs_fk_cascade(self, conn, alembic_head):
        """T2：yaml_import_diffs.job_id FK CASCADE 至 yaml_import_jobs。"""
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO yaml_import_jobs "
                    "(playbook_id, yaml_sha256, mode) "
                    "VALUES ('test_pb', 'sha_001', 'dry_run') RETURNING job_id;"
                )
                jid = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO yaml_import_diffs "
                    "(job_id, target_table, diff_type, notes) "
                    "VALUES (%s, 'projects', 'insert', 'cascade test');",
                    (jid,),
                )
                cur.execute(
                    "DELETE FROM yaml_import_jobs WHERE job_id = %s;", (jid,)
                )
                cur.execute(
                    "SELECT count(*) FROM yaml_import_diffs WHERE job_id = %s;",
                    (jid,),
                )
                assert cur.fetchone()[0] == 0, (
                    "yaml_import_diffs 未隨 jobs CASCADE 刪除"
                )
        finally:
            c.rollback()
            c.close()


class TestCheckConstraints:
    """AC: CHECK 約束。"""

    def test_mode_check_dry_run_apply_only(self, conn, alembic_head):
        """T3：mode CHECK 只能 dry_run / apply。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO yaml_import_jobs "
                        "(playbook_id, yaml_sha256, mode) "
                        "VALUES ('m_test', 'sha', 'invalid_mode');"
                    )
        finally:
            c.rollback()
            c.close()

    def test_status_check_five_states(self, conn, alembic_head):
        """T4：status CHECK 5 態（pending/running/success/failed/cancelled）。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO yaml_import_jobs "
                        "(playbook_id, yaml_sha256, mode, status) "
                        "VALUES ('s_test', 'sha', 'dry_run', 'unknown');"
                    )
        finally:
            c.rollback()
            c.close()

    def test_diff_target_table_check(self, conn, alembic_head):
        """T10：yaml_import_diffs.target_table CHECK 限制。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO yaml_import_jobs "
                    "(playbook_id, yaml_sha256, mode) "
                    "VALUES ('dtt_test', 'sha', 'dry_run') RETURNING job_id;"
                )
                jid = cur.fetchone()[0]
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO yaml_import_diffs "
                        "(job_id, target_table, diff_type) "
                        "VALUES (%s, 'invalid_table', 'insert');",
                        (jid,),
                    )
        finally:
            c.rollback()
            c.close()


class TestDeduplication:
    """AC: W4 sha256 重複 import 防護。"""

    def test_unique_dedupe_playbook_sha_mode(self, conn, alembic_head):
        """T5：UNIQUE(playbook_id, yaml_sha256, mode) 防重複。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO yaml_import_jobs "
                    "(playbook_id, yaml_sha256, mode) "
                    "VALUES ('dedupe_pb', 'sha_dedupe', 'apply');"
                )
                with pytest.raises(psycopg2.errors.UniqueViolation):
                    cur.execute(
                        "INSERT INTO yaml_import_jobs "
                        "(playbook_id, yaml_sha256, mode) "
                        "VALUES ('dedupe_pb', 'sha_dedupe', 'apply');"
                    )
        finally:
            c.rollback()
            c.close()


class TestAdvisoryLock:
    """AC: try_acquire_import_lock + has_active_import_for。"""

    def test_lock_function_exists(self, conn, alembic_head):
        """T6：try_acquire_import_lock(text) function 存在。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT prorettype::regtype::text FROM pg_proc "
                "WHERE proname = 'try_acquire_import_lock';"
            )
            row = cur.fetchone()
        assert row is not None, "try_acquire_import_lock 不存在"
        assert row[0] == "boolean", f"預期 returns boolean，實際 {row[0]!r}"

    def test_concurrent_lock_acquire_fails(self, conn, alembic_head):
        """T7：第一個 caller 成功取鎖；第二個 caller 取不到鎖。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c1 = _new_conn()
        c2 = _new_conn()
        try:
            with c1.cursor() as cur1:
                cur1.execute("SELECT try_acquire_import_lock('concurrent_pb');")
                ok1 = cur1.fetchone()[0]
            assert ok1 is True, "第一個 caller 應成功取鎖"

            with c2.cursor() as cur2:
                cur2.execute("SELECT try_acquire_import_lock('concurrent_pb');")
                ok2 = cur2.fetchone()[0]
            assert ok2 is False, "第二個 caller 應取不到鎖（已被持有）"
        finally:
            c1.rollback()
            c2.rollback()
            c1.close()
            c2.close()

    def test_lock_released_on_commit(self, conn, alembic_head):
        """T8：鎖在 transaction commit 後自動釋放（XACT scope）。"""
        c1 = _new_conn()
        c2 = _new_conn()
        try:
            with c1.cursor() as cur1:
                cur1.execute("SELECT try_acquire_import_lock('release_pb');")
                assert cur1.fetchone()[0] is True
            c1.commit()  # 釋放鎖

            with c2.cursor() as cur2:
                cur2.execute("SELECT try_acquire_import_lock('release_pb');")
                ok = cur2.fetchone()[0]
            assert ok is True, "鎖未在 commit 後釋放"
            c2.rollback()
        finally:
            c1.close()
            c2.close()

    def test_has_active_import_for(self, conn, alembic_head):
        """T9：has_active_import_for 偵測 pending/running job。"""
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute("SELECT has_active_import_for('inactive_pb');")
                assert cur.fetchone()[0] is False, (
                    "尚無 job 時應回傳 false"
                )

                cur.execute(
                    "INSERT INTO yaml_import_jobs "
                    "(playbook_id, yaml_sha256, mode, status) "
                    "VALUES ('active_pb', 'sha_active', 'apply', 'running');"
                )

                cur.execute("SELECT has_active_import_for('active_pb');")
                assert cur.fetchone()[0] is True, (
                    "active job 存在時應回傳 true"
                )
        finally:
            c.rollback()
            c.close()
