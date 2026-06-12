"""0012_yaml_import_staging — yaml_import_jobs + yaml_import_diffs + advisory lock

Revision ID: 0012_yaml_import_staging
Revises: 0011_rbac_tables
Create Date: 2026-05-20

SD_Improving_06 W3-14（議題 #3 + W4 前置）：

提供 60+ YAML playbook → DB 三層任務模型的匯入 staging 機制：
  - yaml_import_jobs   匯入作業（一次 import = 一個 job）
  - yaml_import_diffs  per-task diff 紀錄（dry-run vs apply）
  - try_acquire_import_lock(playbook_id) advisory lock 避免並發衝突

PM #11 hybrid：yaml_import_diffs 寫入前必過 PII 過濾器（W3-T3-23 PII filter）。

advisory lock 設計：
  - 用 `pg_try_advisory_xact_lock(hash(playbook_id))` 避免同一 playbook 並發 import
  - hash 取 playbook_id 字串的 hashtext()，rebound 到 int4 大小
  - Lock 在事務結束時自動釋放（XACT scope）

對應規格：
  - SD_Improving_06.md §6 表第 0012
  - SD_Improving_06.md §4 W3-6 + W4 (Click CLI tools/migrate_yaml_to_db.py)
  - tests/contract/test_alembic_0012_advisory_lock.py（≥ 6 case）

SD_06 §11 回退策略：✅ downgrade -1（staging 表清空 + drop function）
"""
from __future__ import annotations

revision = "0012_yaml_import_staging"
down_revision = "0011_rbac_tables"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- =============================================================================
-- yaml_import_jobs：匯入作業頂層紀錄
-- =============================================================================
CREATE TABLE yaml_import_jobs (
    job_id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id       text        NOT NULL,
    -- W4 sha256 versioning：同 playbook_id + sha256 → 跳過重複 import
    yaml_sha256       text        NOT NULL,
    -- 'dry_run' = 預演不寫入；'apply' = 實際寫入三層 schema
    mode              text        NOT NULL,
    status            text        NOT NULL DEFAULT 'pending',
    started_at        timestamptz NOT NULL DEFAULT now(),
    finished_at       timestamptz,
    -- 結果統計
    projects_created  int         NOT NULL DEFAULT 0,
    goal_tasks_created int        NOT NULL DEFAULT 0,
    execution_items_created int   NOT NULL DEFAULT 0,
    -- 錯誤訊息（失敗時填入）
    error_message     text,
    -- 觸發者
    triggered_by      uuid        REFERENCES users (user_id) ON DELETE SET NULL,

    CONSTRAINT ck_yaml_import_mode CHECK (mode IN ('dry_run', 'apply')),
    CONSTRAINT ck_yaml_import_status CHECK (
        status IN ('pending', 'running', 'success', 'failed', 'cancelled')
    ),
    -- W4 sha256 重複 import 防護：同 (playbook_id, yaml_sha256) 已成功則跳過
    CONSTRAINT uq_yaml_import_dedupe UNIQUE (playbook_id, yaml_sha256, mode)
);

CREATE INDEX idx_yaml_jobs_playbook ON yaml_import_jobs (playbook_id);
CREATE INDEX idx_yaml_jobs_status_recent
    ON yaml_import_jobs (status, started_at DESC)
    WHERE status IN ('pending', 'running');


-- =============================================================================
-- yaml_import_diffs：per-task 變動明細（dry-run 報告基礎）
-- =============================================================================
CREATE TABLE yaml_import_diffs (
    diff_id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id            uuid        NOT NULL REFERENCES yaml_import_jobs (job_id)
                                  ON DELETE CASCADE,
    -- 影響的 target table（projects / goal_tasks / execution_items）
    target_table      text        NOT NULL,
    -- 'insert' / 'update' / 'skip' / 'conflict'
    diff_type         text        NOT NULL,
    target_id         uuid,
    -- PM #11 PII：所有 before/after 值入庫前必過濾器
    before_snapshot   jsonb,
    after_snapshot    jsonb,
    notes             text,
    created_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_yaml_diff_target_table CHECK (
        target_table IN ('projects', 'goal_tasks', 'execution_items',
                         'playbook_versions')
    ),
    CONSTRAINT ck_yaml_diff_type CHECK (
        diff_type IN ('insert', 'update', 'skip', 'conflict')
    )
);

CREATE INDEX idx_yaml_diffs_job ON yaml_import_diffs (job_id);
CREATE INDEX idx_yaml_diffs_target ON yaml_import_diffs (target_table, diff_type);


-- =============================================================================
-- try_acquire_import_lock：advisory lock helper function
-- =============================================================================
-- 用 pg_try_advisory_xact_lock：non-blocking，當鎖被持有立即回傳 false
-- 鎖在 transaction commit/rollback 時自動釋放（XACT scope）
CREATE OR REPLACE FUNCTION try_acquire_import_lock(playbook_id_arg text)
RETURNS boolean
LANGUAGE plpgsql AS $fn$
DECLARE
    lock_key bigint;
BEGIN
    -- hashtext 對任意文字產生 int4 hash；轉 bigint 確保正值
    -- pg_try_advisory_xact_lock 取 bigint 鎖鍵
    lock_key := hashtext(playbook_id_arg)::bigint;
    RETURN pg_try_advisory_xact_lock(lock_key);
END
$fn$;

COMMENT ON FUNCTION try_acquire_import_lock(text) IS
    'SD_06 W3-T3-14：non-blocking advisory lock helper。'
    '同 playbook_id 並發 import 時，後到的 caller 回傳 false 並等待。'
    '鎖鍵 = hashtext(playbook_id)，XACT scope 自動釋放。';


-- =============================================================================
-- has_active_import_for：檢測是否已有 active import job（避免 dedup race）
-- =============================================================================
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
"""


_DOWNGRADE_SQL = r"""
DROP FUNCTION IF EXISTS has_active_import_for(text);
DROP FUNCTION IF EXISTS try_acquire_import_lock(text);
DROP TABLE IF EXISTS yaml_import_diffs CASCADE;
DROP TABLE IF EXISTS yaml_import_jobs CASCADE;
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0012_yaml_import_staging.sql"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
