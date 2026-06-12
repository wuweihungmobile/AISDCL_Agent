"""0009_three_tier_schema — projects / goal_tasks / execution_items 三層任務模型

Revision ID: 0009_three_tier_schema
Revises: 0008_embedding_variable_dim
Create Date: 2026-05-20

SD_Improving_06 W3-3（議題 #3 + R-SD06-3-1）：建立 PG 三層任務模型 schema。

三層結構（對應 autoclaude/models/three_tier_schema.py Pydantic 模型）：
    Project (頂層) ─┐
                    └─→ GoalTask (中層，可巢狀 sub_tasks，depth ≤ 3)
                            └─→ ExecutionItem (底層原子單元)

per-table HNSW 調參（SD_06 §4 W3 規格 + AC3-5）：
    - goal_tasks      m=8   （任務描述少量，較疏 graph）
    - execution_items m=16  （明細多，較密 graph）
    - 共 (knowledge_entries m=16，per-partition，0007/0008 已建立)

PM 拍板：
    - #1 sub-task 樹狀深度 ≤ 3（CHECK constraint）
    - #4 config_snapshot JSONB：凍結 run 設定快照
    - #6 RBAC：owner_id 預留 nullable，0011_rbac_tables 補 FK

對應 contract test：tests/contract/test_three_tier_schema.py（≥ 12 case，AC3-1~AC3-5）。
SD_06 §11 回退策略：✅ downgrade -1（純結構，無業務資料）。
"""
from __future__ import annotations

revision = "0009_three_tier_schema"
down_revision = "0008_embedding_variable_dim"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- =============================================================================
-- 三層任務模型 schema（projects / goal_tasks / execution_items）
-- =============================================================================

-- =============================================================================
-- 1. projects 表（頂層專案）
-- =============================================================================
CREATE TABLE projects (
    project_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name              text        NOT NULL,
    description       text,
    -- PM #4 config_snapshot：凍結 run 設定快照
    config_snapshot   jsonb       NOT NULL DEFAULT '{}'::jsonb,
    -- PM #7 RBAC owner（0011_rbac_tables 補 FK → users.user_id）
    owner_id          uuid,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_projects_name UNIQUE (name)
);

CREATE INDEX idx_projects_owner ON projects (owner_id) WHERE owner_id IS NOT NULL;
CREATE INDEX idx_projects_created ON projects (created_at DESC);


-- =============================================================================
-- 2. goal_tasks 表（中層目標任務，遞迴 sub_tasks，depth ≤ 3）
-- =============================================================================
CREATE TABLE goal_tasks (
    goal_task_id      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        uuid        NOT NULL REFERENCES projects (project_id)
                                  ON DELETE CASCADE,
    parent_id         uuid        REFERENCES goal_tasks (goal_task_id)
                                  ON DELETE CASCADE,
    title             text        NOT NULL,
    description       text,
    -- PM #1 sub-task 樹狀深度上限 ≤ 3（與 Pydantic model 對齊）
    depth             int         NOT NULL,
    priority          int         NOT NULL DEFAULT 3,
    status            text        NOT NULL DEFAULT 'pending',
    -- PM #4 config_snapshot：每個 goal_task 凍結配置（W3 寫入時填入）
    config_snapshot   jsonb       NOT NULL DEFAULT '{}'::jsonb,
    -- embedding 欄位（W3 IEmbedder dual-read）
    embedding_v       halfvec(1024),
    embedding_model_id text,
    embedding_status  text        NOT NULL DEFAULT 'pending',
    embedding_attempts int        NOT NULL DEFAULT 0,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    -- PM #1 紅線：深度上限 1-3
    CONSTRAINT ck_goal_tasks_depth CHECK (depth BETWEEN 1 AND 3),
    CONSTRAINT ck_goal_tasks_priority CHECK (priority BETWEEN 1 AND 5),
    CONSTRAINT ck_goal_tasks_status CHECK (
        status IN ('pending', 'running', 'success', 'failed', 'aborted')
    ),
    CONSTRAINT ck_goal_tasks_embedding_status CHECK (
        embedding_status IN ('pending', 'ok', 'failed')
    )
);

CREATE INDEX idx_goal_tasks_project ON goal_tasks (project_id);
CREATE INDEX idx_goal_tasks_parent ON goal_tasks (parent_id)
    WHERE parent_id IS NOT NULL;
CREATE INDEX idx_goal_tasks_status ON goal_tasks (status);
CREATE INDEX idx_goal_tasks_embedding_retry
    ON goal_tasks (embedding_status, embedding_attempts)
    WHERE embedding_status != 'ok';

-- per-table HNSW for goal_tasks，m=8（SD_06 §4 W3-3）
CREATE INDEX idx_goal_tasks_embedding_hnsw
    ON goal_tasks USING hnsw (embedding_v halfvec_cosine_ops)
    WITH (m = 8, ef_construction = 64)
    WHERE embedding_v IS NOT NULL;


-- =============================================================================
-- 3. execution_items 表（底層原子執行單元）
-- =============================================================================
CREATE TABLE execution_items (
    exec_id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_task_id      uuid        NOT NULL REFERENCES goal_tasks (goal_task_id)
                                  ON DELETE CASCADE,
    action            text        NOT NULL,
    status            text        NOT NULL DEFAULT 'pending',
    estimated_minutes int,
    actual_minutes    int,
    result            jsonb,
    -- embedding 欄位
    embedding_v       halfvec(1024),
    embedding_model_id text,
    embedding_status  text        NOT NULL DEFAULT 'pending',
    embedding_attempts int        NOT NULL DEFAULT 0,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_execution_items_status CHECK (
        status IN ('pending', 'running', 'ok', 'failed', 'skipped')
    ),
    CONSTRAINT ck_execution_items_estimated CHECK (
        estimated_minutes IS NULL OR estimated_minutes >= 0
    ),
    CONSTRAINT ck_execution_items_embedding_status CHECK (
        embedding_status IN ('pending', 'ok', 'failed')
    )
);

CREATE INDEX idx_execution_items_goal_task ON execution_items (goal_task_id);
CREATE INDEX idx_execution_items_status ON execution_items (status);
CREATE INDEX idx_execution_items_embedding_retry
    ON execution_items (embedding_status, embedding_attempts)
    WHERE embedding_status != 'ok';

-- per-table HNSW for execution_items，m=16（SD_06 §4 W3-3）
CREATE INDEX idx_execution_items_embedding_hnsw
    ON execution_items USING hnsw (embedding_v halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding_v IS NOT NULL;


-- =============================================================================
-- 4. updated_at 自動更新 trigger function（三表共用）
-- =============================================================================
CREATE OR REPLACE FUNCTION _three_tier_touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    -- 使用 clock_timestamp()（statement-time）而非 now()（transaction-time）
    -- 確保同事務內多次 UPDATE 也能反映實際更新時序
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END
$fn$;

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();

CREATE TRIGGER trg_goal_tasks_updated_at
    BEFORE UPDATE ON goal_tasks
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();

CREATE TRIGGER trg_execution_items_updated_at
    BEFORE UPDATE ON execution_items
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();
"""


_DOWNGRADE_SQL = r"""
-- 反向 drop（CASCADE 處理 FK）
DROP TRIGGER IF EXISTS trg_execution_items_updated_at ON execution_items;
DROP TRIGGER IF EXISTS trg_goal_tasks_updated_at ON goal_tasks;
DROP TRIGGER IF EXISTS trg_projects_updated_at ON projects;
DROP FUNCTION IF EXISTS _three_tier_touch_updated_at();

DROP TABLE IF EXISTS execution_items CASCADE;
DROP TABLE IF EXISTS goal_tasks CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0009_three_tier_schema.sql"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
