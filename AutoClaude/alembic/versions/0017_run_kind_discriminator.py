"""0017_run_kind_discriminator — playbook_runs 加 run_kind 判別欄，CHECK 改為「僅三層 run 需 goal」

Revision ID: 0017_run_kind_discriminator
Revises: 0016_agt_phase1_memory
Create Date: 2026-07-12

DEF-101-051（SD_10 PG-track）：三層 goal_task_id 為半成品——schema/約束齊全但
應用層從未接線，導致 0010 的 ``ck_runs_post_cutoff_has_goal`` 在 cutoff（2026-05-20）
後對「所有 checkpoint save 產生的裸 run」100% 撞牆（pg-contract 7 CheckViolation）。

方向定案（使用者拍板 orphan-run 政策 = 「CHECK 加判別欄」）：
  - 保留三層追蹤能力（run→goal_task 之 FK 不放寬）。
  - 新增 ``run_kind`` 判別欄（'standalone' | 'three_tier'）明確區分兩類 run：
      * three_tier run（來自 goal 分解，帶 goal_task_id）→ **必須**有 goal_task_id；
      * standalone run（plain playbook，無 goal 分解）→ **合法**無 goal_task_id。
  - CHECK 由「時間 cutoff 判別」改為「run_kind 判別」：
        ck_runs_three_tier_has_goal  ⇒  run_kind <> 'three_tier' OR goal_task_id IS NOT NULL
    此式無時間依賴 → **消除 playbook_runs 的『時間炸彈』**（DEF-101-051 work item #7）。
  - ⚠️ 範圍僅限 playbook_runs。playbook_versions 的平行時間炸彈
    ``ck_versions_post_cutoff_has_project``（0010）**本 migration 未動、仍活體生效**
    （見 DEF-101-054，SD_10 follow-up）。

判別欄語意（非對稱，刻意）：run_kind='three_tier' 強制要有 goal_task_id；但
standalone run **允許**帶 goal_task_id（不禁），因 _ensure_run_id 只在有 goal 時才標
three_tier，實務不產生此組合，故此鬆度無風險。

低鎖策略（承 0010 SD 紅線 ❌11）：
  - ADD COLUMN ... NOT NULL DEFAULT 'standalone' 於 PG 11+ 為 metadata-only（不重寫表）。
  - CHECK 用 NOT VALID + VALIDATE 分開。⚠️ 誠實限制：alembic env.py 單一交易下 VALIDATE
    仍在既有 ACCESS EXCLUSIVE 內執行（低鎖效益僅 psql .sql autocommit 路徑完全兌現）；
    惟 playbook_runs 資料量小、掃描極快，實務衝擊有限。大表 production 應走 .sql/psql 分段。

既有列（feature dormant，run_kind 全預設 'standalone'、goal_task_id 全 NULL）
天然滿足新 CHECK，故 upgrade VALIDATE 對既有資料必然通過。

對應 contract test：test_alembic_0010_fk_three_step.py（T8/T10 同步更新至本 migration 後
語意）+ test_pg_state_repository_contract.py（three_tier 真實流程新增）。
"""
from __future__ import annotations

revision = "0017_run_kind_discriminator"
down_revision = "0016_agt_phase1_memory"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- =============================================================================
-- STEP 1：新增 run_kind 判別欄（PG 11+ metadata-only，瞬完成、不重寫表）
-- =============================================================================
ALTER TABLE playbook_runs
    ADD COLUMN IF NOT EXISTS run_kind text NOT NULL DEFAULT 'standalone';

ALTER TABLE playbook_runs
    ADD CONSTRAINT ck_runs_run_kind
        CHECK (run_kind IN ('standalone', 'three_tier'))
        NOT VALID;
ALTER TABLE playbook_runs VALIDATE CONSTRAINT ck_runs_run_kind;

-- =============================================================================
-- STEP 2：以判別欄取代時間炸彈 CHECK（DEF-101-051）
-- =============================================================================
-- 舊：ck_runs_post_cutoff_has_goal = (goal_task_id NOT NULL OR started_at < cutoff)
--     → cutoff 後所有裸 run 撞牆（時間炸彈）。
-- 新：ck_runs_three_tier_has_goal = (run_kind <> 'three_tier' OR goal_task_id NOT NULL)
--     → 僅三層 run 需 goal_task_id；standalone run 合法無 goal；無時間依賴。
ALTER TABLE playbook_runs DROP CONSTRAINT IF EXISTS ck_runs_post_cutoff_has_goal;

ALTER TABLE playbook_runs
    ADD CONSTRAINT ck_runs_three_tier_has_goal
        CHECK (run_kind <> 'three_tier' OR goal_task_id IS NOT NULL)
        NOT VALID;
ALTER TABLE playbook_runs VALIDATE CONSTRAINT ck_runs_three_tier_has_goal;
"""


_DOWNGRADE_SQL = r"""
-- 反向：drop 新 CHECK → 還原 0010 時間 cutoff CHECK（結構）→ drop run_kind 判別欄
ALTER TABLE playbook_runs DROP CONSTRAINT IF EXISTS ck_runs_three_tier_has_goal;

-- ⚠️ 只 ADD ... NOT VALID、**不 VALIDATE**（回退陷阱防護）：
-- 0017 上線後，(c) 政策合法產生的「standalone 且 post-cutoff 無 goal」列會違反舊時間
-- 炸彈 CHECK；若在此 VALIDATE 全表掃描必撞 CheckViolation → downgrade 卡死。NOT VALID
-- 仍對「新列」生效、豁免既有列，還原 0010 STEP3 的約束「結構形狀」而不做歷史全列驗證。
-- （注意：0010 upgrade 當時因無業務資料 VALIDATE 通過；但 0017 上線後歷史列已含合法
-- standalone post-cutoff 列，這些列無法再通過舊時間炸彈語意，故 downgrade 不可強驗。）
ALTER TABLE playbook_runs
    ADD CONSTRAINT ck_runs_post_cutoff_has_goal
        CHECK (goal_task_id IS NOT NULL OR started_at < '2026-05-20 00:00:00+00'::timestamptz)
        NOT VALID;

ALTER TABLE playbook_runs DROP CONSTRAINT IF EXISTS ck_runs_run_kind;
ALTER TABLE playbook_runs DROP COLUMN IF EXISTS run_kind;
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0017_run_kind_discriminator.sql"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
