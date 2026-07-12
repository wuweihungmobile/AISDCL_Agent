"""0018_version_kind_discriminator — playbook_versions 加 version_kind 判別欄 + CHECK 判別化

Revision ID: 0018_version_kind_discriminator
Revises: 0017_run_kind_discriminator
Create Date: 2026-07-12

DEF-101-054（SD_10 PG-track）：`playbook_versions.project_id` 的平行時間炸彈。
0010 建 ``ck_versions_post_cutoff_has_project``（``project_id IS NOT NULL OR
created_at < '2026-05-20'``）+ FK 欄，但 ``PlaybookVersion`` ORM 未映射 project_id、
``pg_playbook_repository._persist()`` INSERT 不帶 project_id → cutoff（2026-05-20）後
任何經 PG 落地的 evolution 版本必撞 CheckViolation。與 DEF-101-051 的 runs 時間炸彈同構，
0017 只修 runs，此欄未動、仍活體生效（僅因 PG playbook 持久化未上 production 而 dormant）。

方向定案（比照 runs (c) 政策 = 「CHECK 加判別欄」，使用者拍板同一 orphan-policy 精神）：
  - 保留 project 關聯能力（version→project 之 FK 不放寬）。
  - 新增 ``version_kind`` 判別欄（'standalone' | 'project_scoped'）明確區分兩類版本：
      * project_scoped version（隸屬某三層 project，帶 project_id）→ **必須**有 project_id；
      * standalone version（plain playbook 之 evolution，無 project 脈絡）→ **合法**無 project_id。
  - CHECK 由「時間 cutoff 判別」改為「version_kind 判別」：
        ck_versions_project_scoped_has_project
          ⇒  version_kind <> 'project_scoped' OR project_id IS NOT NULL
    此式無時間依賴 → **消除 playbook_versions 的『時間炸彈』**（DEF-101-054）。

判別欄語意（非對稱，刻意，與 0017 run_kind 同慣例）：version_kind='project_scoped' 強制
要有 project_id；standalone version **允許**帶 project_id（不禁）。現行 evolution 路徑
（persist_evolution）未攜 project 脈絡，故 PG 落地版本恆為 standalone（server_default），
天然滿足新 CHECK；未來若接通 project 脈絡再於應用層標 project_scoped。

低鎖策略（承 0010 SD 紅線 ❌11 / 0017 慣例）：
  - ADD COLUMN ... NOT NULL DEFAULT 'standalone' 於 PG 11+ 為 metadata-only（不重寫表）。
  - CHECK 用 NOT VALID + VALIDATE 分開。⚠️ 誠實限制：alembic env.py 單一交易下 VALIDATE
    仍在既有 ACCESS EXCLUSIVE 內執行（低鎖效益僅 psql .sql autocommit 路徑完全兌現）；
    惟 playbook_versions 資料量小、掃描極快，實務衝擊有限。大表 production 應走 .sql/psql 分段。

既有列（feature dormant，version_kind 全預設 'standalone'、project_id 全 NULL）
天然滿足新 CHECK，故 upgrade VALIDATE 對既有資料必然通過。

對應 contract test：test_alembic_0010_fk_three_step.py（T9 更新至本 migration 後語意 +
T11/T11b/T11c versions 判別欄斷言）+ test_pg_existing_schema_lock.py（DDL baseline +
test_playbook_versions_self_fk_chain 現真跑）。
"""
from __future__ import annotations

revision = "0018_version_kind_discriminator"
down_revision = "0017_run_kind_discriminator"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- =============================================================================
-- STEP 1：新增 version_kind 判別欄（PG 11+ metadata-only，瞬完成、不重寫表）
-- =============================================================================
ALTER TABLE playbook_versions
    ADD COLUMN IF NOT EXISTS version_kind text NOT NULL DEFAULT 'standalone';

ALTER TABLE playbook_versions
    ADD CONSTRAINT ck_versions_version_kind
        CHECK (version_kind IN ('standalone', 'project_scoped'))
        NOT VALID;
ALTER TABLE playbook_versions VALIDATE CONSTRAINT ck_versions_version_kind;

-- =============================================================================
-- STEP 2：以判別欄取代時間炸彈 CHECK（DEF-101-054）
-- =============================================================================
-- 舊：ck_versions_post_cutoff_has_project = (project_id NOT NULL OR created_at < cutoff)
--     → cutoff 後所有無 project 的版本撞牆（時間炸彈）。
-- 新：ck_versions_project_scoped_has_project = (version_kind <> 'project_scoped'
--       OR project_id NOT NULL)
--     → 僅 project_scoped 版本需 project_id；standalone version 合法無 project；無時間依賴。
ALTER TABLE playbook_versions DROP CONSTRAINT IF EXISTS ck_versions_post_cutoff_has_project;

ALTER TABLE playbook_versions
    ADD CONSTRAINT ck_versions_project_scoped_has_project
        CHECK (version_kind <> 'project_scoped' OR project_id IS NOT NULL)
        NOT VALID;
ALTER TABLE playbook_versions VALIDATE CONSTRAINT ck_versions_project_scoped_has_project;
"""


_DOWNGRADE_SQL = r"""
-- 反向：drop 新 CHECK → 還原 0010 時間 cutoff CHECK（結構）→ drop version_kind 判別欄
ALTER TABLE playbook_versions DROP CONSTRAINT IF EXISTS ck_versions_project_scoped_has_project;

-- ⚠️ 只 ADD ... NOT VALID、**不 VALIDATE**（回退陷阱防護，比照 0017 downgrade）：
-- 0018 上線後，(c) 政策合法產生的「standalone 且 post-cutoff 無 project」列會違反舊時間
-- 炸彈 CHECK；若在此 VALIDATE 全表掃描必撞 CheckViolation → downgrade 卡死。NOT VALID
-- 仍對「新列」生效、豁免既有列，還原 0010 STEP3 的約束「結構形狀」而不做歷史全列驗證。
ALTER TABLE playbook_versions
    ADD CONSTRAINT ck_versions_post_cutoff_has_project
        CHECK (project_id IS NOT NULL OR created_at < '2026-05-20 00:00:00+00'::timestamptz)
        NOT VALID;

ALTER TABLE playbook_versions DROP CONSTRAINT IF EXISTS ck_versions_version_kind;
ALTER TABLE playbook_versions DROP COLUMN IF EXISTS version_kind;
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用："
            "psql -f alembic/versions/0018_version_kind_discriminator.sql"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
