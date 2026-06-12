"""0013_drift_log — DualStateRepository drift 紀錄表

Revision ID: 0013_drift_log
Revises: 0012_yaml_import_staging
Create Date: 2026-05-20

SD_Improving_06 W5-T5-5（議題 #5 + R-SD06-5-1）：

DualStateRepository.detect_drift() 偵測 File primary vs PG shadow 不一致時，
將 per-field diff 記錄至本表供 SRE / DBA 排查。

設計重點：
  - drift_id  uuid PK
  - run_id    可選（FK → playbook_runs.run_id）；fail_loud 比對找不到 run_id 時為 NULL
  - playbook_id text NOT NULL（用於跨 run 查詢）
  - source_left / source_right 標示「左 vs 右」來源（primary / shadow）
  - field_drift jsonb：{field_path: {"left": ..., "right": ...}}（PII filter 後）
  - severity   text：info / warn / critical
  - resolved_at / resolver 供事後 reconcile 流程追蹤
  - 365 天 partition：依 detected_at 做 RANGE partition by month（同 KB TTL）

PM #11 hybrid：所有 field_drift 入庫前必過 PII filter（W3 過濾器）。

對應規格：
  - SD_Improving_06.md §6.5 AC5-2（dual_state drift 全欄比對 + drift_log 表）
  - SD06_Execution_Guide.md W5 T5-5
  - tests/contract/test_dual_state_drift.py（≥ 4 case）

SD_06 §11 回退策略：✅ downgrade -1（純結構，可回退）
"""
from __future__ import annotations

revision = "0013_drift_log"
down_revision = "0012_yaml_import_staging"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- =============================================================================
-- drift_log：DualStateRepository drift 紀錄（partition by month, 365 天 TTL）
-- =============================================================================
CREATE TABLE drift_log (
    drift_id        uuid        NOT NULL DEFAULT gen_random_uuid(),
    -- detected_at 為 partition key（必須位於主鍵內）
    detected_at     timestamptz NOT NULL DEFAULT now(),
    -- run_id 可為 NULL（drift 發現時 run_id 未對齊）
    run_id          uuid,
    playbook_id     text        NOT NULL,
    -- 比對來源（primary / shadow / file / pg）
    source_left     text        NOT NULL,
    source_right    text        NOT NULL,
    -- per-field drift：{field_path: {"left": ..., "right": ...}}（PII filter 後）
    field_drift     jsonb       NOT NULL,
    severity        text        NOT NULL DEFAULT 'warn',
    -- 事後 reconcile 流程
    resolved_at     timestamptz,
    resolver        text,
    notes           text,

    -- partition by month 要求 PK 包含 partition key（detected_at）
    PRIMARY KEY (drift_id, detected_at),
    CONSTRAINT ck_drift_severity CHECK (severity IN ('info', 'warn', 'critical')),
    CONSTRAINT ck_drift_source CHECK (
        source_left IN ('primary', 'shadow', 'file', 'pg')
        AND source_right IN ('primary', 'shadow', 'file', 'pg')
    )
) PARTITION BY RANGE (detected_at);

CREATE INDEX idx_drift_log_playbook ON drift_log (playbook_id, detected_at DESC);
CREATE INDEX idx_drift_log_unresolved
    ON drift_log (severity, detected_at DESC)
    WHERE resolved_at IS NULL;
CREATE INDEX idx_drift_log_run_id
    ON drift_log (run_id, detected_at DESC)
    WHERE run_id IS NOT NULL;

COMMENT ON TABLE drift_log IS
    'SD_06 W5-T5-5：DualStateRepository detect_drift() 紀錄表。'
    '365 天 partition by month；過期 partition 由 cron drop。';

-- =============================================================================
-- 初始 partition：本月 + 後 12 個月（避免上線首日寫入失敗）
-- =============================================================================
DO $$
DECLARE
    start_month date := date_trunc('month', now())::date;
    cur_month date;
    next_month date;
    part_name text;
BEGIN
    FOR i IN 0..12 LOOP
        cur_month := (start_month + (i || ' month')::interval)::date;
        next_month := (start_month + ((i + 1) || ' month')::interval)::date;
        part_name := 'drift_log_p_' || to_char(cur_month, 'YYYYMM');
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF drift_log '
            'FOR VALUES FROM (%L) TO (%L)',
            part_name, cur_month, next_month
        );
    END LOOP;
END$$;
"""


_DOWNGRADE_SQL = r"""
-- 子 partition 隨主表 DROP 自動級聯清除
DROP TABLE IF EXISTS drift_log CASCADE;
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0013_drift_log.sql"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
