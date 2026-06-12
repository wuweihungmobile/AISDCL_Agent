"""0014_config_audit_log — ConfigResolver 設定變更稽核紀錄表

Revision ID: 0014_config_audit_log
Revises: 0013_drift_log
Create Date: 2026-05-20

SD_Improving_06 W5-T5-16（議題 #6 + R-SD06-6-1）：

ConfigResolver 4 層 merge 變更（global → workflow → step → runtime）
每一層覆寫都會經 audit_observer 觸發寫入本表，供 SRE 排查 effective
config 變動歷史。

設計重點：
  - audit_id   uuid PK
  - changed_at 變更時間（用於排序 / 過濾）
  - user_id    觸發變更的 user（可為 NULL，CLI 啟動時無 RBAC）
  - layer      'global' / 'workflow' / 'step' / 'runtime'
  - field_path 變更欄位（dot notation，例 'token_guard.compact_threshold_pct'）
  - old_value / new_value  PII filter 後的 jsonb 值
  - action     'insert' / 'update' / 'delete' / 'reject'（reject = RBAC 阻擋）
  - reason     變更說明（CLI override / hot-reload / config rollback 等）

PM #11 hybrid：old_value / new_value 入庫前必過 PII filter（W3 過濾器）。
  - secret 欄位（minimax.api_key 等）→ drop write（不入庫）
  - pii 欄位 → masked 後入庫

對應規格：
  - SD_Improving_06.md §6.5 AC6-4（config_audit_log 表）
  - SD_Improving_06.md §6.5 AC6-5（每次 ConfigResolver 變更都寫 audit_log）
  - tests/integration/test_config_audit_log.py（AC6-5）

SD_06 §11 回退策略：✅ downgrade -1（純結構，可回退）
"""
from __future__ import annotations

revision = "0014_config_audit_log"
down_revision = "0013_drift_log"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- =============================================================================
-- config_audit_log：ConfigResolver 設定變更稽核紀錄
-- =============================================================================
CREATE TABLE config_audit_log (
    audit_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    changed_at      timestamptz NOT NULL DEFAULT now(),
    -- 觸發者（可為 NULL，CLI 啟動時無 RBAC user）
    user_id         uuid,
    -- 變更層級
    layer           text        NOT NULL,
    -- 變更欄位（dot notation，例 'token_guard.compact_threshold_pct'）
    field_path      text        NOT NULL,
    -- PM #11 PII：所有 old/new value 入庫前必過濾
    old_value       jsonb,
    new_value       jsonb,
    -- 動作類型
    action          text        NOT NULL DEFAULT 'update',
    -- 變更原因（CLI override / hot-reload / config rollback 等）
    reason          text,

    CONSTRAINT ck_config_audit_layer CHECK (
        layer IN ('global', 'workflow', 'step', 'runtime')
    ),
    CONSTRAINT ck_config_audit_action CHECK (
        action IN ('insert', 'update', 'delete', 'reject')
    )
);

CREATE INDEX idx_config_audit_field ON config_audit_log (field_path, changed_at DESC);
CREATE INDEX idx_config_audit_layer
    ON config_audit_log (layer, changed_at DESC);
CREATE INDEX idx_config_audit_user
    ON config_audit_log (user_id, changed_at DESC)
    WHERE user_id IS NOT NULL;

COMMENT ON TABLE config_audit_log IS
    'SD_06 W5-T5-16：ConfigResolver 設定變更稽核紀錄。'
    '對應 4 層 hierarchical config merge：global → workflow → step → runtime。';
"""


_DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS config_audit_log CASCADE;
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0014_config_audit_log.sql"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
