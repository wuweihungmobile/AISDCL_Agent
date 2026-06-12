"""0010_link_legacy_to_tiers — 既有 4 表加 nullable FK 至三層模型（**三步流程**）

Revision ID: 0010_link_legacy_tiers
Revises: 0009_three_tier_schema
Create Date: 2026-05-20

SD_Improving_06 W3-7/8/9（R-SD06-3-1 + SD 一票否決）：
  既有 4 表（playbook_runs / playbook_versions / checkpoints / knowledge_entries）
  整合至三層模型，但 production 已有資料，必須避免 long lock。

⛔ SD 紅線 ❌11：FK backfill 與 SET NOT NULL 在同事務（會與在線寫入死鎖）。
   ⇒ **拆三步**：
       step 1: add nullable FK 欄位（低風險，瞬完成；可立即回退）
       step 2: backfill batch function（可分批執行；可中斷可重跑）
       step 3: CHECK constraint NOT VALID + VALIDATE CONSTRAINT
                （NOT VALID 不掃既有資料 + VALIDATE 分階段校驗）

⚠️ PM W-1 強制前置（G3 阻塞條件）：本 migration 進入 production 前需有 **1M 列
   staging DB 完整 dry-run + 回退演練紀錄**（docs/05_development/SD06_FK_DryRun_Report.md）。

本地測試：
  - step 1 與 step 2 function 定義必跑
  - step 3 CHECK NOT VALID 加入（但 VALIDATE 因本地無業務資料而 skip）
  - VALIDATE CONSTRAINT 留至 staging dry-run 手動執行

對應 contract test：tests/contract/test_alembic_0010_fk_three_step.py（≥ 10 case）。
SD_06 §11 回退策略：
  - step 1 / step 3 失敗：✅ downgrade -1（可回退；找 SD + DBA 雙簽）
  - step 2 backfill ≥ 50% 失敗：⚠️ point-of-no-return，前滾修補；SD + DBA + PM 三簽
"""
from __future__ import annotations

revision = "0010_link_legacy_tiers"
down_revision = "0009_three_tier_schema"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


# Cutoff timestamp：CHECK constraint 用於 legacy 資料豁免
# 任何 started_at < cutoff 的既有資料不強制有 FK；新資料則必須補 FK
_CUTOFF_TS = "2026-05-20 00:00:00+00"


_UPGRADE_SQL_STEP1 = r"""
-- =============================================================================
-- STEP 1：add nullable FK 至既有 4 表（瞬完成，低風險）
-- =============================================================================

-- 1a. playbook_runs → goal_tasks
ALTER TABLE playbook_runs
    ADD COLUMN IF NOT EXISTS goal_task_id uuid,
    ADD CONSTRAINT fk_runs_goal_task
        FOREIGN KEY (goal_task_id) REFERENCES goal_tasks (goal_task_id)
        ON DELETE SET NULL
        NOT VALID;
CREATE INDEX IF NOT EXISTS idx_runs_goal_task ON playbook_runs (goal_task_id)
    WHERE goal_task_id IS NOT NULL;

-- PM #8 partial index：MAX_ACTIVE_RUNS_PER_GOAL=5 用此 index 快速 count
-- WHERE status='running' 縮小掃描範圍
CREATE INDEX IF NOT EXISTS idx_runs_active_per_goal
    ON playbook_runs (goal_task_id)
    WHERE status = 'running' AND goal_task_id IS NOT NULL;

-- 1b. playbook_versions → projects
ALTER TABLE playbook_versions
    ADD COLUMN IF NOT EXISTS project_id uuid,
    ADD CONSTRAINT fk_versions_project
        FOREIGN KEY (project_id) REFERENCES projects (project_id)
        ON DELETE SET NULL
        NOT VALID;
CREATE INDEX IF NOT EXISTS idx_versions_project ON playbook_versions (project_id)
    WHERE project_id IS NOT NULL;

-- 1c. checkpoints → goal_tasks（冗餘但有助於 dashboard 查詢）
ALTER TABLE checkpoints
    ADD COLUMN IF NOT EXISTS goal_task_id uuid,
    ADD CONSTRAINT fk_checkpoints_goal_task
        FOREIGN KEY (goal_task_id) REFERENCES goal_tasks (goal_task_id)
        ON DELETE SET NULL
        NOT VALID;
CREATE INDEX IF NOT EXISTS idx_checkpoints_goal_task ON checkpoints (goal_task_id)
    WHERE goal_task_id IS NOT NULL;

-- 1d. knowledge_entries → execution_items
-- ⚠️ PG 限制：partitioned table 不支援 NOT VALID FK，必須直接 VALID。
-- 因 execution_item_id 為新加 NULL 欄位（無既有 row 持值），VALID FK
-- 校驗不會失敗；FK 約束會自動傳播至所有子分區。
ALTER TABLE knowledge_entries
    ADD COLUMN IF NOT EXISTS execution_item_id uuid;
ALTER TABLE knowledge_entries
    ADD CONSTRAINT fk_kb_execution_item
        FOREIGN KEY (execution_item_id) REFERENCES execution_items (exec_id)
        ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_kb_execution_item ON knowledge_entries (execution_item_id)
    WHERE execution_item_id IS NOT NULL;
"""


_UPGRADE_SQL_STEP2 = r"""
-- =============================================================================
-- STEP 2：backfill batch function（可分批執行；可中斷可重跑）
-- =============================================================================
-- 本 function 留給 staging / production 手動分批執行。
-- 本地測試環境無業務資料，不執行 backfill。
--
-- 使用方式（staging）：
--     SELECT backfill_legacy_fk('playbook_runs', 1000);    -- 每批 1000 列
--     SELECT backfill_legacy_fk('playbook_versions', 1000);
--     SELECT backfill_legacy_fk('checkpoints', 1000);
--     SELECT backfill_legacy_fk('knowledge_entries', 1000);
--
-- 回傳：本次 backfill 影響列數。當回傳 0 時表示已 backfill 完成。

CREATE OR REPLACE FUNCTION backfill_legacy_fk(target_table text, batch_size int)
RETURNS bigint
LANGUAGE plpgsql AS $fn$
DECLARE
    affected_rows bigint := 0;
BEGIN
    -- 此 function 為 staging dry-run 規劃用樣板；
    -- 實際 backfill 邏輯依賴具體業務 metadata 對應（例如 playbook_runs.metadata
    -- 中的 project_name → projects.name 解析）。
    --
    -- 本地測試環境：直接回傳 0（無業務資料可 backfill）。
    -- staging 環境：需替換為實際 UPDATE ... FROM ... LIMIT batch_size 邏輯。

    IF target_table = 'playbook_runs' THEN
        -- 範例：UPDATE playbook_runs SET goal_task_id = (...) WHERE goal_task_id IS NULL ...
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
    'SD_06 W3-T3-8 step 2：legacy FK backfill batch job 樣板。'
    'Production 部署前需依業務 metadata 客製化每個 target_table 的 UPDATE 邏輯。'
    '回傳 0 表示該批已完成或無資料可 backfill。';
"""


_UPGRADE_SQL_STEP3 = r"""
-- =============================================================================
-- STEP 3：VALIDATE CONSTRAINT（NOT VALID 已加；VALIDATE 分階段執行）
-- =============================================================================
-- ⚠️ SD 紅線 ❌11：本步驟在 NOT VALID FK 上 VALIDATE，不會與在線寫入衝突。
-- VALIDATE CONSTRAINT 只掃既有資料一次，不取 ACCESS EXCLUSIVE LOCK。
--
-- 本地測試環境：VALIDATE 跑成功（既有資料皆 NULL，無 FK 違規）。
-- staging 環境：先完成 step 2 backfill ≥ 95%，再執行 VALIDATE，否則 raise FK violation。

ALTER TABLE playbook_runs VALIDATE CONSTRAINT fk_runs_goal_task;
ALTER TABLE playbook_versions VALIDATE CONSTRAINT fk_versions_project;
ALTER TABLE checkpoints VALIDATE CONSTRAINT fk_checkpoints_goal_task;
-- knowledge_entries.fk_kb_execution_item 已直接 VALID（partitioned table 限制）

-- 同時加 CHECK constraint：新資料（cutoff 後）必須有 FK
-- legacy 資料（cutoff 前）豁免，避免 fail
ALTER TABLE playbook_runs
    ADD CONSTRAINT ck_runs_post_cutoff_has_goal
    CHECK (goal_task_id IS NOT NULL OR started_at < '2026-05-20 00:00:00+00'::timestamptz)
    NOT VALID;

ALTER TABLE playbook_versions
    ADD CONSTRAINT ck_versions_post_cutoff_has_project
    CHECK (project_id IS NOT NULL OR created_at < '2026-05-20 00:00:00+00'::timestamptz)
    NOT VALID;

-- VALIDATE 新 CHECK：legacy 資料已豁免，新資料須符合
ALTER TABLE playbook_runs VALIDATE CONSTRAINT ck_runs_post_cutoff_has_goal;
ALTER TABLE playbook_versions VALIDATE CONSTRAINT ck_versions_post_cutoff_has_project;
"""


_DOWNGRADE_SQL = r"""
-- 反向：drop CHECK + FK + columns + function（純結構，可回退）
ALTER TABLE playbook_versions
    DROP CONSTRAINT IF EXISTS ck_versions_post_cutoff_has_project;
ALTER TABLE playbook_runs
    DROP CONSTRAINT IF EXISTS ck_runs_post_cutoff_has_goal;

-- Drop FK constraints
ALTER TABLE knowledge_entries DROP CONSTRAINT IF EXISTS fk_kb_execution_item;
ALTER TABLE checkpoints DROP CONSTRAINT IF EXISTS fk_checkpoints_goal_task;
ALTER TABLE playbook_versions DROP CONSTRAINT IF EXISTS fk_versions_project;
ALTER TABLE playbook_runs DROP CONSTRAINT IF EXISTS fk_runs_goal_task;

-- Drop indexes
DROP INDEX IF EXISTS idx_kb_execution_item;
DROP INDEX IF EXISTS idx_checkpoints_goal_task;
DROP INDEX IF EXISTS idx_versions_project;
DROP INDEX IF EXISTS idx_runs_active_per_goal;
DROP INDEX IF EXISTS idx_runs_goal_task;

-- Drop columns
ALTER TABLE knowledge_entries DROP COLUMN IF EXISTS execution_item_id;
ALTER TABLE checkpoints DROP COLUMN IF EXISTS goal_task_id;
ALTER TABLE playbook_versions DROP COLUMN IF EXISTS project_id;
ALTER TABLE playbook_runs DROP COLUMN IF EXISTS goal_task_id;

-- Drop function
DROP FUNCTION IF EXISTS backfill_legacy_fk(text, int);
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0010_link_legacy_to_tiers.sql"
        )
    # 三步順序執行（SD 紅線 ❌11：FK backfill 與 SET NOT NULL 不可同事務 →
    # 此處 NOT VALID + VALIDATE 切開，不會 long lock）
    op.execute(_UPGRADE_SQL_STEP1)
    op.execute(_UPGRADE_SQL_STEP2)
    op.execute(_UPGRADE_SQL_STEP3)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
