-- 0009_three_tier_schema.sql — projects / goal_tasks / execution_items
-- SD_Improving_06 W3-3
-- 對應 .py：alembic/versions/0009_three_tier_schema.py
BEGIN;

-- 1. projects
CREATE TABLE projects (
    project_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name              text        NOT NULL,
    description       text,
    config_snapshot   jsonb       NOT NULL DEFAULT '{}'::jsonb,
    owner_id          uuid,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_projects_name UNIQUE (name)
);
CREATE INDEX idx_projects_owner ON projects (owner_id) WHERE owner_id IS NOT NULL;
CREATE INDEX idx_projects_created ON projects (created_at DESC);

-- 2. goal_tasks (depth ≤ 3，self-reference parent_id)
CREATE TABLE goal_tasks (
    goal_task_id      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        uuid        NOT NULL REFERENCES projects (project_id) ON DELETE CASCADE,
    parent_id         uuid        REFERENCES goal_tasks (goal_task_id) ON DELETE CASCADE,
    title             text        NOT NULL,
    description       text,
    depth             int         NOT NULL,
    priority          int         NOT NULL DEFAULT 3,
    status            text        NOT NULL DEFAULT 'pending',
    config_snapshot   jsonb       NOT NULL DEFAULT '{}'::jsonb,
    embedding_v       halfvec(1024),
    embedding_model_id text,
    embedding_status  text        NOT NULL DEFAULT 'pending',
    embedding_attempts int        NOT NULL DEFAULT 0,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_goal_tasks_depth CHECK (depth BETWEEN 1 AND 3),
    CONSTRAINT ck_goal_tasks_priority CHECK (priority BETWEEN 1 AND 5),
    CONSTRAINT ck_goal_tasks_status CHECK (status IN ('pending','running','success','failed','aborted')),
    CONSTRAINT ck_goal_tasks_embedding_status CHECK (embedding_status IN ('pending','ok','failed'))
);
CREATE INDEX idx_goal_tasks_project ON goal_tasks (project_id);
CREATE INDEX idx_goal_tasks_parent ON goal_tasks (parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX idx_goal_tasks_status ON goal_tasks (status);
CREATE INDEX idx_goal_tasks_embedding_retry ON goal_tasks (embedding_status, embedding_attempts)
    WHERE embedding_status != 'ok';
CREATE INDEX idx_goal_tasks_embedding_hnsw ON goal_tasks USING hnsw (embedding_v halfvec_cosine_ops)
    WITH (m = 8, ef_construction = 64) WHERE embedding_v IS NOT NULL;

-- 3. execution_items
CREATE TABLE execution_items (
    exec_id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_task_id      uuid        NOT NULL REFERENCES goal_tasks (goal_task_id) ON DELETE CASCADE,
    action            text        NOT NULL,
    status            text        NOT NULL DEFAULT 'pending',
    estimated_minutes int,
    actual_minutes    int,
    result            jsonb,
    embedding_v       halfvec(1024),
    embedding_model_id text,
    embedding_status  text        NOT NULL DEFAULT 'pending',
    embedding_attempts int        NOT NULL DEFAULT 0,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_execution_items_status CHECK (status IN ('pending','running','ok','failed','skipped')),
    CONSTRAINT ck_execution_items_estimated CHECK (estimated_minutes IS NULL OR estimated_minutes >= 0),
    CONSTRAINT ck_execution_items_embedding_status CHECK (embedding_status IN ('pending','ok','failed'))
);
CREATE INDEX idx_execution_items_goal_task ON execution_items (goal_task_id);
CREATE INDEX idx_execution_items_status ON execution_items (status);
CREATE INDEX idx_execution_items_embedding_retry ON execution_items (embedding_status, embedding_attempts)
    WHERE embedding_status != 'ok';
CREATE INDEX idx_execution_items_embedding_hnsw ON execution_items USING hnsw (embedding_v halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64) WHERE embedding_v IS NOT NULL;

-- 4. updated_at trigger
CREATE OR REPLACE FUNCTION _three_tier_touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END
$fn$;
CREATE TRIGGER trg_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();
CREATE TRIGGER trg_goal_tasks_updated_at BEFORE UPDATE ON goal_tasks
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();
CREATE TRIGGER trg_execution_items_updated_at BEFORE UPDATE ON execution_items
    FOR EACH ROW EXECUTE FUNCTION _three_tier_touch_updated_at();

COMMIT;
