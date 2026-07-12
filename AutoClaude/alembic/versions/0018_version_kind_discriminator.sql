-- 0018_version_kind_discriminator.sql — 手動 psql fallback（對應 0018_version_kind_discriminator.py）
-- DEF-101-054：playbook_versions 加 version_kind 判別欄，改 CHECK 為「僅 project_scoped 版本需 project_id」，
-- 消除 0010 ck_versions_post_cutoff_has_project 的時間炸彈（與 0017 修 runs 同構）。
-- 用法：psql "$AUTOCLAUDE_DB_DSN(psycopg2 形式)" -f alembic/versions/0018_version_kind_discriminator.sql

-- STEP 1：新增 version_kind 判別欄（PG 11+ metadata-only）
ALTER TABLE playbook_versions
    ADD COLUMN IF NOT EXISTS version_kind text NOT NULL DEFAULT 'standalone';

ALTER TABLE playbook_versions
    ADD CONSTRAINT ck_versions_version_kind
        CHECK (version_kind IN ('standalone', 'project_scoped'))
        NOT VALID;
ALTER TABLE playbook_versions VALIDATE CONSTRAINT ck_versions_version_kind;

-- STEP 2：以判別欄取代時間炸彈 CHECK
ALTER TABLE playbook_versions DROP CONSTRAINT IF EXISTS ck_versions_post_cutoff_has_project;

ALTER TABLE playbook_versions
    ADD CONSTRAINT ck_versions_project_scoped_has_project
        CHECK (version_kind <> 'project_scoped' OR project_id IS NOT NULL)
        NOT VALID;
ALTER TABLE playbook_versions VALIDATE CONSTRAINT ck_versions_project_scoped_has_project;
