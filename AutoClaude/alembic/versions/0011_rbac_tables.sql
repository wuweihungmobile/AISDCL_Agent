-- 0011_rbac_tables.sql — RBAC 五表 + admin/developer/viewer seed
-- SD_Improving_06 W3-12
-- 對應 .py：alembic/versions/0011_rbac_tables.py
BEGIN;

-- 1. users
CREATE TABLE users (
    user_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    username       text        NOT NULL,
    email          text        NOT NULL,
    password_hash  text,
    is_active      boolean     NOT NULL DEFAULT true,
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

-- 2. roles
CREATE TABLE roles (
    role_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name      text        NOT NULL,
    description    text,
    policy_json    jsonb       NOT NULL DEFAULT '{}'::jsonb,
    is_system      boolean     NOT NULL DEFAULT false,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_roles_role_name UNIQUE (role_name)
);

-- 3. role_bindings
CREATE TABLE role_bindings (
    binding_id     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        uuid        NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    role_id        uuid        NOT NULL REFERENCES roles (role_id) ON DELETE CASCADE,
    project_id     uuid        REFERENCES projects (project_id) ON DELETE CASCADE,
    granted_by     uuid        REFERENCES users (user_id) ON DELETE SET NULL,
    granted_at     timestamptz NOT NULL DEFAULT now(),
    expires_at     timestamptz,
    -- PG 15+ NULLS NOT DISTINCT
    CONSTRAINT uq_role_bindings_user_role_project UNIQUE NULLS NOT DISTINCT (user_id, role_id, project_id)
);
CREATE INDEX idx_bindings_user ON role_bindings (user_id);
CREATE INDEX idx_bindings_role ON role_bindings (role_id);
CREATE INDEX idx_bindings_project ON role_bindings (project_id) WHERE project_id IS NOT NULL;
-- partial index 中不能用 now()（IMMUTABLE 限制）
CREATE INDEX idx_bindings_no_expiry ON role_bindings (user_id, role_id)
    WHERE expires_at IS NULL;

-- 4. user_sessions
CREATE TABLE user_sessions (
    session_id     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        uuid        NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    token_hash     text        NOT NULL,
    issued_at      timestamptz NOT NULL DEFAULT now(),
    expires_at     timestamptz NOT NULL,
    ip_address     inet,
    user_agent     text,
    revoked_at     timestamptz,
    CONSTRAINT uq_sessions_token UNIQUE (token_hash)
);
CREATE INDEX idx_sessions_user_unrevoked ON user_sessions (user_id, expires_at)
    WHERE revoked_at IS NULL;

-- 5. rbac_audit_log
CREATE TABLE rbac_audit_log (
    audit_id       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id  uuid        REFERENCES users (user_id) ON DELETE SET NULL,
    action         text        NOT NULL,
    target_table   text        NOT NULL,
    target_id      uuid,
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

-- 6. PM #7 三系統角色 seed
INSERT INTO roles (role_name, description, policy_json, is_system) VALUES
    ('admin', '管理員 — 全權 CRUD + RBAC 管理',
     '{"resources": ["*"], "actions": ["*"], "casbin_role": "admin"}'::jsonb, true),
    ('developer', '開發者 — project CRUD + run execute',
     '{"resources": ["projects", "goal_tasks", "execution_items", "playbook_runs"], "actions": ["create", "read", "update", "execute"], "casbin_role": "developer"}'::jsonb, true),
    ('viewer', '檢視者 — read-only',
     '{"resources": ["*"], "actions": ["read"], "casbin_role": "viewer"}'::jsonb, true);

-- 7. projects.owner_id FK
ALTER TABLE projects
    ADD CONSTRAINT fk_projects_owner
        FOREIGN KEY (owner_id) REFERENCES users (user_id)
        ON DELETE SET NULL
        NOT VALID;
ALTER TABLE projects VALIDATE CONSTRAINT fk_projects_owner;

-- 8. updated_at triggers
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();
CREATE TRIGGER trg_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();

COMMIT;
