-- 0010_link_legacy_to_tiers.sql — 既有 4 表加 nullable FK 至三層模型（三步流程）
-- SD_Improving_06 W3-7/8/9
-- 對應 .py：alembic/versions/0010_link_legacy_to_tiers.py
-- ⛔ SD 紅線 ❌11：FK backfill 與 SET NOT NULL 不可同事務
-- ⚠️ PM W-1：production 前需 1M 列 staging dry-run + 回退演練紀錄
BEGIN;

-- =============================================================================
-- STEP 1：add nullable FK + indexes（NOT VALID 不掃既有資料）
-- =============================================================================

-- playbook_runs → goal_tasks
ALTER TABLE playbook_runs
    ADD COLUMN IF NOT EXISTS goal_task_id uuid,
    ADD CONSTRAINT fk_runs_goal_task
        FOREIGN KEY (goal_task_id) REFERENCES goal_tasks (goal_task_id)
        ON DELETE SET NULL
        NOT VALID;
CREATE INDEX IF NOT EXISTS idx_runs_goal_task ON playbook_runs (goal_task_id)
    WHERE goal_task_id IS NOT NULL;

-- PM #8 partial index：MAX_ACTIVE_RUNS_PER_GOAL guard
CREATE INDEX IF NOT EXISTS idx_runs_active_per_goal
    ON playbook_runs (goal_task_id)
    WHERE status = 'running' AND goal_task_id IS NOT NULL;

-- playbook_versions → projects
ALTER TABLE playbook_versions
    ADD COLUMN IF NOT EXISTS project_id uuid,
    ADD CONSTRAINT fk_versions_project
        FOREIGN KEY (project_id) REFERENCES projects (project_id)
        ON DELETE SET NULL
        NOT VALID;
CREATE INDEX IF NOT EXISTS idx_versions_project ON playbook_versions (project_id)
    WHERE project_id IS NOT NULL;

-- checkpoints → goal_tasks（冗餘 dashboard 查詢）
ALTER TABLE checkpoints
    ADD COLUMN IF NOT EXISTS goal_task_id uuid,
    ADD CONSTRAINT fk_checkpoints_goal_task
        FOREIGN KEY (goal_task_id) REFERENCES goal_tasks (goal_task_id)
        ON DELETE SET NULL
        NOT VALID;
CREATE INDEX IF NOT EXISTS idx_checkpoints_goal_task ON checkpoints (goal_task_id)
    WHERE goal_task_id IS NOT NULL;

-- knowledge_entries → execution_items（partitioned table）
-- PG 限制：partitioned table 不支援 NOT VALID FK，必須直接 VALID
-- 新加 NULL 欄位無既有 row 違規，VALID 校驗安全
ALTER TABLE knowledge_entries
    ADD COLUMN IF NOT EXISTS execution_item_id uuid;
ALTER TABLE knowledge_entries
    ADD CONSTRAINT fk_kb_execution_item
        FOREIGN KEY (execution_item_id) REFERENCES execution_items (exec_id)
        ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_kb_execution_item ON knowledge_entries (execution_item_id)
    WHERE execution_item_id IS NOT NULL;

-- =============================================================================
-- STEP 2：backfill batch function 樣板（可分批執行）
-- =============================================================================
CREATE OR REPLACE FUNCTION backfill_legacy_fk(target_table text, batch_size int)
RETURNS bigint
LANGUAGE plpgsql AS $fn$
DECLARE
    affected_rows bigint := 0;
BEGIN
    IF target_table = 'playbook_runs' THEN
        affected_rows := 0;
    ELSIF target_table = 'playbook_versions' THEN
        affected_rows := 0;
    ELSIF target_table = 'checkpoints' THEN
        affected_rows := 0;
    ELSIF target_table = 'knowledge_entries' THEN
        affected_rows := 0;
    ELSE
        RAISE EXCEPTION 'Unknown target_table for backfill: %', target_table;
    END IF;
    RETURN affected_rows;
END
$fn$;
COMMENT ON FUNCTION backfill_legacy_fk(text, int) IS
    'SD_06 W3-T3-8 step 2：legacy FK backfill batch job 樣板。';

-- =============================================================================
-- STEP 3：VALIDATE CONSTRAINT + CHECK new-row enforcement
-- =============================================================================
ALTER TABLE playbook_runs VALIDATE CONSTRAINT fk_runs_goal_task;
ALTER TABLE playbook_versions VALIDATE CONSTRAINT fk_versions_project;
ALTER TABLE checkpoints VALIDATE CONSTRAINT fk_checkpoints_goal_task;
-- knowledge_entries.fk_kb_execution_item 已直接 VALID（partitioned table 限制）

ALTER TABLE playbook_runs
    ADD CONSTRAINT ck_runs_post_cutoff_has_goal
    CHECK (goal_task_id IS NOT NULL OR started_at < '2026-05-20 00:00:00+00'::timestamptz)
    NOT VALID;
ALTER TABLE playbook_versions
    ADD CONSTRAINT ck_versions_post_cutoff_has_project
    CHECK (project_id IS NOT NULL OR created_at < '2026-05-20 00:00:00+00'::timestamptz)
    NOT VALID;
ALTER TABLE playbook_runs VALIDATE CONSTRAINT ck_runs_post_cutoff_has_goal;
ALTER TABLE playbook_versions VALIDATE CONSTRAINT ck_versions_post_cutoff_has_project;

COMMIT;
