"""0011_rbac_tables — RBAC 五表（users / roles / role_bindings + sessions/audit_log）

Revision ID: 0011_rbac_tables
Revises: 0010_link_legacy_tiers
Create Date: 2026-05-20

SD_Improving_06 W3-12（議題 #3 + PM #7 拍板）：

PM #7 拍板（2026-05-17）：
  - admin   = 全權（CRUD all resources + RBAC 管理）
  - developer = project CRUD + run execute
  - viewer  = read-only

保留 `policy_json` 欄位以利後續擴 casbin policy engine。

五表結構：
  - users         身分認證主表
  - roles         角色定義 + policy_json
  - role_bindings user × role 多對多
  - user_sessions（W6 預擴；本 migration 預埋 schema）
  - rbac_audit_log（W6 預擴；本 migration 預埋 schema）

對應規格：
  - SD_Improving_06.md §6.5 AC3-3（RBAC 五表 + role matrix + 違反 role 必 403）
  - SD_Improving_06.md §9.2 #7 PM 拍板
  - tests/contract/test_alembic_0011_rbac.py（≥ 8 case）

SD_06 §11 回退策略：✅ downgrade -1（純結構 + seed 資料）
"""
from __future__ import annotations

revision = "0011_rbac_tables"
down_revision = "0010_link_legacy_tiers"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- =============================================================================
-- RBAC 五表：users / roles / role_bindings / user_sessions / rbac_audit_log
-- =============================================================================

-- =============================================================================
-- 1. users（身分認證主表）
-- =============================================================================
CREATE TABLE users (
    user_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    username       text        NOT NULL,
    email          text        NOT NULL,
    -- bcrypt / argon2 hash（不存明文）
    password_hash  text,
    is_active      boolean     NOT NULL DEFAULT true,
    -- 帳號鎖定（防暴力破解）
    locked_until   timestamptz,
    failed_login_count int     NOT NULL DEFAULT 0,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    last_login_at  timestamptz,

    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT ck_users_email_format CHECK (email LIKE '%@%')
);

CREATE INDEX idx_users_active ON users (is_active) WHERE is_active = true;


-- =============================================================================
-- 2. roles（角色定義 + policy_json 供 casbin 擴展）
-- =============================================================================
CREATE TABLE roles (
    role_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name      text        NOT NULL,
    description    text,
    -- PM #7：policy_json 預留 casbin policy 序列化（W6 起接 casbin enforcer）
    policy_json    jsonb       NOT NULL DEFAULT '{}'::jsonb,
    -- 系統內建角色（admin/developer/viewer）不可被 dev API 刪除
    is_system      boolean     NOT NULL DEFAULT false,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_roles_role_name UNIQUE (role_name)
);


-- =============================================================================
-- 3. role_bindings（user × role 多對多）
-- =============================================================================
CREATE TABLE role_bindings (
    binding_id     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        uuid        NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    role_id        uuid        NOT NULL REFERENCES roles (role_id) ON DELETE CASCADE,
    -- 限制綁定範圍：NULL = 全域；非 NULL = 只在該 project 內生效
    project_id     uuid        REFERENCES projects (project_id) ON DELETE CASCADE,
    granted_by     uuid        REFERENCES users (user_id) ON DELETE SET NULL,
    granted_at     timestamptz NOT NULL DEFAULT now(),
    expires_at     timestamptz,

    -- PG 15+ NULLS NOT DISTINCT：兩個 NULL project_id 視為相同（防全域角色重複授權）
    CONSTRAINT uq_role_bindings_user_role_project
        UNIQUE NULLS NOT DISTINCT (user_id, role_id, project_id)
);

CREATE INDEX idx_bindings_user ON role_bindings (user_id);
CREATE INDEX idx_bindings_role ON role_bindings (role_id);
CREATE INDEX idx_bindings_project ON role_bindings (project_id) WHERE project_id IS NOT NULL;
-- partial index 中不能用 now()（IMMUTABLE 限制），改為索引「未設過期時間」的綁定
-- 查詢時需動態加 WHERE expires_at IS NULL OR expires_at > now()
CREATE INDEX idx_bindings_no_expiry ON role_bindings (user_id, role_id)
    WHERE expires_at IS NULL;


-- =============================================================================
-- 4. user_sessions（W6 預擴；本 migration 預埋 schema）
-- =============================================================================
CREATE TABLE user_sessions (
    session_id     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        uuid        NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    -- JWT / session token hash（不存明文 token）
    token_hash     text        NOT NULL,
    issued_at      timestamptz NOT NULL DEFAULT now(),
    expires_at     timestamptz NOT NULL,
    ip_address     inet,
    user_agent     text,
    revoked_at     timestamptz,

    CONSTRAINT uq_sessions_token UNIQUE (token_hash)
);

-- partial index 中不能用 now()，改為索引「未撤銷」的 session
-- 查詢時需動態加 AND expires_at > now()
CREATE INDEX idx_sessions_user_unrevoked ON user_sessions (user_id, expires_at)
    WHERE revoked_at IS NULL;


-- =============================================================================
-- 5. rbac_audit_log（W6 預擴；記錄 RBAC 操作）
-- =============================================================================
CREATE TABLE rbac_audit_log (
    audit_id       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id  uuid        REFERENCES users (user_id) ON DELETE SET NULL,
    action         text        NOT NULL,
    target_table   text        NOT NULL,
    target_id      uuid,
    -- PM #11 PII：actor/target 細節以 JSONB 存放，過濾器於入庫前處理
    detail_json    jsonb       NOT NULL DEFAULT '{}'::jsonb,
    occurred_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_rbac_audit_action CHECK (
        action IN ('grant', 'revoke', 'create_user', 'delete_user',
                   'login', 'login_failed', 'logout', 'token_revoke')
    )
);

CREATE INDEX idx_rbac_audit_occurred ON rbac_audit_log (occurred_at DESC);
CREATE INDEX idx_rbac_audit_actor ON rbac_audit_log (actor_user_id, occurred_at DESC)
    WHERE actor_user_id IS NOT NULL;


-- =============================================================================
-- 6. PM #7 seed data：admin / developer / viewer 三系統角色
-- =============================================================================
INSERT INTO roles (role_name, description, policy_json, is_system) VALUES
    ('admin', '管理員 — 全權 CRUD + RBAC 管理',
     '{"resources": ["*"], "actions": ["*"], "casbin_role": "admin"}'::jsonb,
     true),
    ('developer', '開發者 — project CRUD + run execute',
     '{"resources": ["projects", "goal_tasks", "execution_items", "playbook_runs"], '
     '"actions": ["create", "read", "update", "execute"], "casbin_role": "developer"}'::jsonb,
     true),
    ('viewer', '檢視者 — read-only',
     '{"resources": ["*"], "actions": ["read"], "casbin_role": "viewer"}'::jsonb,
     true);


-- =============================================================================
-- 7. projects.owner_id 補 FK 至 users.user_id（W3-T3-12 補完）
-- =============================================================================
ALTER TABLE projects
    ADD CONSTRAINT fk_projects_owner
        FOREIGN KEY (owner_id) REFERENCES users (user_id)
        ON DELETE SET NULL
        NOT VALID;
-- 既有 projects.owner_id 全為 NULL，VALIDATE 安全
ALTER TABLE projects VALIDATE CONSTRAINT fk_projects_owner;


-- =============================================================================
-- 8. updated_at trigger（users / roles 共用既有 function）
-- =============================================================================
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();

CREATE TRIGGER trg_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();
"""


_DOWNGRADE_SQL = r"""
-- 反向：drop trigger + FK + tables（CASCADE 處理依賴）
DROP TRIGGER IF EXISTS trg_roles_updated_at ON roles;
DROP TRIGGER IF EXISTS trg_users_updated_at ON users;

ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_owner;

DROP TABLE IF EXISTS rbac_audit_log CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS role_bindings CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS users CASCADE;
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0011_rbac_tables.sql"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
