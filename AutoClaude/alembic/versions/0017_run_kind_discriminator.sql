-- 0017_run_kind_discriminator.sql — 手動 psql fallback（對應 0017_run_kind_discriminator.py）
-- DEF-101-051：playbook_runs 加 run_kind 判別欄，改 CHECK 為「僅三層 run 需 goal_task_id」，
-- 消除 0010 ck_runs_post_cutoff_has_goal 的時間炸彈。
-- 用法：psql "$AUTOCLAUDE_DB_DSN(psycopg2 形式)" -f alembic/versions/0017_run_kind_discriminator.sql

-- STEP 1：新增 run_kind 判別欄（PG 11+ metadata-only）
ALTER TABLE playbook_runs
    ADD COLUMN IF NOT EXISTS run_kind text NOT NULL DEFAULT 'standalone';

ALTER TABLE playbook_runs
    ADD CONSTRAINT ck_runs_run_kind
        CHECK (run_kind IN ('standalone', 'three_tier'))
        NOT VALID;
ALTER TABLE playbook_runs VALIDATE CONSTRAINT ck_runs_run_kind;

-- STEP 2：以判別欄取代時間炸彈 CHECK
ALTER TABLE playbook_runs DROP CONSTRAINT IF EXISTS ck_runs_post_cutoff_has_goal;

ALTER TABLE playbook_runs
    ADD CONSTRAINT ck_runs_three_tier_has_goal
        CHECK (run_kind <> 'three_tier' OR goal_task_id IS NOT NULL)
        NOT VALID;
ALTER TABLE playbook_runs VALIDATE CONSTRAINT ck_runs_three_tier_has_goal;
