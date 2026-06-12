"""SD_Improving_06 W3-13 — alembic 0011 RBAC 五表契約測試（AC3-3）

對應：alembic/versions/0011_rbac_tables.py
規格：SD_Improving_06.md §6.5 AC3-3 + §9.2 PM #7 拍板

驗證項目（≥ 8 case）：
  T1  users 表存在含必要欄位（含 password_hash / locked_until / failed_login_count）
  T2  roles 表含 policy_json JSONB + is_system 旗標
  T3  role_bindings 多對多 + project_id nullable（全域 vs project 範圍）
  T4  user_sessions 表存在（W6 預擴）
  T5  rbac_audit_log 表存在 + action CHECK constraint
  T6  PM #7 三系統角色 seed：admin / developer / viewer（is_system=true）
  T7  policy_json 結構正確：admin 全權 / developer CRUD / viewer read-only
  T8  projects.owner_id FK 已補至 users.user_id（VALIDATED）
  T9  email format CHECK 約束
  T10 role_bindings UNIQUE(user, role, project_id) 防重複授權
  T11 rbac_audit_log action CHECK 限制（grant/revoke/login/...）
  T12 FK CASCADE：刪 user 連帶刪 role_bindings 與 sessions
"""
from __future__ import annotations

import os
import re

import pytest

_DSN_RAW = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
_DSN = re.sub(r"\+asyncpg", "", _DSN_RAW) if _DSN_RAW else None


pytestmark = pytest.mark.skipif(
    _DSN is None,
    reason="需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN 才能跑 0011 契約測試",
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
    if _max_head_num(heads) < 11:
        pytest.skip("alembic main chain 編號 < 11；請執行 `alembic upgrade 0011_rbac_tables`")
    return heads


def _new_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    c = psycopg2.connect(_DSN)
    c.autocommit = False
    return c


class TestRBACFiveTables:
    """AC3-3：RBAC 五表結構。"""

    def test_users_table_with_security_columns(self, conn, alembic_head):
        """T1：users 表含必要欄位。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users';"
            )
            cols = {r[0] for r in cur.fetchall()}
        required = {
            "user_id", "username", "email", "password_hash",
            "is_active", "locked_until", "failed_login_count",
            "created_at", "updated_at", "last_login_at",
        }
        missing = required - cols
        assert not missing, f"users 缺欄：{missing}"

    def test_roles_table_with_policy_json(self, conn, alembic_head):
        """T2：roles 表含 policy_json JSONB + is_system。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'roles';"
            )
            cols = {r[0]: r[1] for r in cur.fetchall()}
        assert "policy_json" in cols, "roles 缺 policy_json"
        assert cols["policy_json"] == "jsonb", (
            f"policy_json 必為 jsonb，實際 {cols['policy_json']!r}"
        )
        assert "is_system" in cols, "roles 缺 is_system"

    def test_role_bindings_multi_to_multi(self, conn, alembic_head):
        """T3：role_bindings 多對多 + project_id nullable。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, is_nullable FROM information_schema.columns "
                "WHERE table_name = 'role_bindings';"
            )
            cols = {r[0]: r[1] for r in cur.fetchall()}
        assert "user_id" in cols, "role_bindings 缺 user_id"
        assert "role_id" in cols, "role_bindings 缺 role_id"
        assert cols.get("project_id") == "YES", (
            "project_id 必為 nullable（NULL = 全域；非 NULL = project 範圍）"
        )

    def test_user_sessions_table_exists(self, conn, alembic_head):
        """T4：user_sessions 表存在（W6 預擴）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_name = 'user_sessions';"
            )
            cnt = cur.fetchone()[0]
        assert cnt == 1, "user_sessions 表不存在"

    def test_rbac_audit_log_with_action_check(self, conn, alembic_head):
        """T5 + T11：rbac_audit_log 表存在 + action CHECK。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_name = 'rbac_audit_log';"
            )
            assert cur.fetchone()[0] == 1, "rbac_audit_log 不存在"
            cur.execute(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_rbac_audit_action';"
            )
            row = cur.fetchone()
        assert row is not None, "ck_rbac_audit_action 不存在"
        defn = row[0]
        for action in ("grant", "revoke", "login", "logout"):
            assert action in defn, f"action CHECK 缺 {action!r}：{defn}"


class TestSeedData:
    """AC3-3：PM #7 三系統角色 seed。"""

    def test_three_system_roles_seeded(self, conn, alembic_head):
        """T6：admin / developer / viewer 三系統角色（is_system=true）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role_name FROM roles "
                "WHERE is_system = true ORDER BY role_name;"
            )
            names = [r[0] for r in cur.fetchall()]
        assert names == ["admin", "developer", "viewer"], (
            f"PM #7 三角色 seed 偏移：{names}"
        )

    def test_policy_json_structure(self, conn, alembic_head):
        """T7：policy_json 結構正確。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role_name, policy_json FROM roles "
                "WHERE role_name IN ('admin', 'developer', 'viewer');"
            )
            policies = {r[0]: r[1] for r in cur.fetchall()}

        # admin: 全權
        assert policies["admin"]["resources"] == ["*"]
        assert policies["admin"]["actions"] == ["*"]
        # developer: CRUD + execute
        assert "execute" in policies["developer"]["actions"]
        assert "projects" in policies["developer"]["resources"]
        # viewer: read-only
        assert policies["viewer"]["actions"] == ["read"]

    def test_casbin_role_marker_present(self, conn, alembic_head):
        """T7b：所有系統角色 policy_json 含 casbin_role 標記（W6 整合用）。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role_name, policy_json->>'casbin_role' FROM roles "
                "WHERE is_system = true;"
            )
            rows = dict(cur.fetchall())
        assert rows["admin"] == "admin"
        assert rows["developer"] == "developer"
        assert rows["viewer"] == "viewer"


class TestProjectsOwnerFK:
    """AC3-3：projects.owner_id 補 FK 至 users（W3-T3-12 補完）。"""

    def test_projects_owner_fk_exists_and_validated(self, conn, alembic_head):
        """T8：fk_projects_owner 存在且 VALIDATED。"""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT confdeltype, convalidated FROM pg_constraint "
                "WHERE conname = 'fk_projects_owner';"
            )
            row = cur.fetchone()
        assert row is not None, "fk_projects_owner 不存在"
        deltype, validated = row
        assert deltype == "n", "owner FK 必為 ON DELETE SET NULL"
        assert validated is True, "fk_projects_owner 必為 VALIDATED"


class TestUserChecks:
    """AC3-3：CHECK 約束 + UNIQUE。"""

    def test_email_format_check(self, conn, alembic_head):
        """T9：email format CHECK（必含 @）。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cur.execute(
                        "INSERT INTO users (username, email) "
                        "VALUES ('bad_email_user', 'not_an_email');"
                    )
        finally:
            c.rollback()
            c.close()

    def test_role_bindings_unique_user_role_project(self, conn, alembic_head):
        """T10：role_bindings UNIQUE(user, role, project_id) 防重複授權。"""
        psycopg2 = pytest.importorskip("psycopg2")
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, email) "
                    "VALUES ('uq_test_u', 'uq@test.com') RETURNING user_id;"
                )
                uid = cur.fetchone()[0]
                cur.execute(
                    "SELECT role_id FROM roles WHERE role_name = 'admin';"
                )
                rid = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO role_bindings (user_id, role_id) VALUES (%s, %s);",
                    (uid, rid),
                )
                with pytest.raises(psycopg2.errors.UniqueViolation):
                    cur.execute(
                        "INSERT INTO role_bindings (user_id, role_id) "
                        "VALUES (%s, %s);",
                        (uid, rid),
                    )
        finally:
            c.rollback()
            c.close()


class TestFKCascade:
    """AC3-3：FK CASCADE。"""

    def test_delete_user_cascades_role_bindings(self, conn, alembic_head):
        """T12：刪 user 連帶刪 role_bindings + sessions。"""
        c = _new_conn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, email) "
                    "VALUES ('cascade_u', 'c@test.com') RETURNING user_id;"
                )
                uid = cur.fetchone()[0]
                cur.execute("SELECT role_id FROM roles WHERE role_name='admin';")
                rid = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO role_bindings (user_id, role_id) "
                    "VALUES (%s, %s);",
                    (uid, rid),
                )
                cur.execute(
                    "INSERT INTO user_sessions (user_id, token_hash, expires_at) "
                    "VALUES (%s, 'tk_cascade', now() + interval '1 hour');",
                    (uid,),
                )
                # delete user
                cur.execute("DELETE FROM users WHERE user_id = %s;", (uid,))
                cur.execute(
                    "SELECT count(*) FROM role_bindings WHERE user_id = %s;",
                    (uid,),
                )
                assert cur.fetchone()[0] == 0, "role_bindings 未隨 user CASCADE 刪"
                cur.execute(
                    "SELECT count(*) FROM user_sessions WHERE user_id = %s;",
                    (uid,),
                )
                assert cur.fetchone()[0] == 0, "user_sessions 未隨 user CASCADE 刪"
        finally:
            c.rollback()
            c.close()
