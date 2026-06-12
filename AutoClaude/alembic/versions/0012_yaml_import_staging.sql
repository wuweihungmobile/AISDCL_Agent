-- 0012_yaml_import_staging.sql — yaml_import_jobs + yaml_import_diffs + advisory lock
-- SD_Improving_06 W3-14
-- 對應 .py：alembic/versions/0012_yaml_import_staging.py
BEGIN;

-- yaml_import_jobs
CREATE TABLE yaml_import_jobs (
    job_id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id       text        NOT NULL,
    yaml_sha256       text        NOT NULL,
    mode              text        NOT NULL,
    status            text        NOT NULL DEFAULT 'pending',
    started_at        timestamptz NOT NULL DEFAULT now(),
    finished_at       timestamptz,
    projects_created  int         NOT NULL DEFAULT 0,
    goal_tasks_created int        NOT NULL DEFAULT 0,
    execution_items_created int   NOT NULL DEFAULT 0,
    error_message     text,
    triggered_by      uuid        REFERENCES users (user_id) ON DELETE SET NULL,
    CONSTRAINT ck_yaml_import_mode CHECK (mode IN ('dry_run', 'apply')),
    CONSTRAINT ck_yaml_import_status CHECK (status IN ('pending','running','success','failed','cancelled')),
    CONSTRAINT uq_yaml_import_dedupe UNIQUE (playbook_id, yaml_sha256, mode)
);
CREATE INDEX idx_yaml_jobs_playbook ON yaml_import_jobs (playbook_id);
CREATE INDEX idx_yaml_jobs_status_recent ON yaml_import_jobs (status, started_at DESC)
    WHERE status IN ('pending', 'running');

-- yaml_import_diffs
CREATE TABLE yaml_import_diffs (
    diff_id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id            uuid        NOT NULL REFERENCES yaml_import_jobs (job_id) ON DELETE CASCADE,
    target_table      text        NOT NULL,
    diff_type         text        NOT NULL,
    target_id         uuid,
    before_snapshot   jsonb,
    after_snapshot    jsonb,
    notes             text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_yaml_diff_target_table CHECK (
        target_table IN ('projects','goal_tasks','execution_items','playbook_versions')
    ),
    CONSTRAINT ck_yaml_diff_type CHECK (diff_type IN ('insert','update','skip','conflict'))
);
CREATE INDEX idx_yaml_diffs_job ON yaml_import_diffs (job_id);
CREATE INDEX idx_yaml_diffs_target ON yaml_import_diffs (target_table, diff_type);

-- advisory lock helpers
CREATE OR REPLACE FUNCTION try_acquire_import_lock(playbook_id_arg text)
RETURNS boolean
LANGUAGE plpgsql AS $fn$
DECLARE
    lock_key bigint;
BEGIN
    lock_key := hashtext(playbook_id_arg)::bigint;
    RETURN pg_try_advisory_xact_lock(lock_key);
END
$fn$;

CREATE OR REPLACE FUNCTION has_active_import_for(playbook_id_arg text)
RETURNS boolean
LANGUAGE plpgsql STABLE AS $fn$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM yaml_import_jobs
        WHERE playbook_id = playbook_id_arg
          AND status IN ('pending', 'running')
    );
END
$fn$;

COMMIT;
