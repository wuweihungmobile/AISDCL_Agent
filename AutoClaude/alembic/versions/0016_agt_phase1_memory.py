"""0016: Improving_012 Phase 1 記憶基座三表（F-C3 / F-C1 / F-C2）

Revision ID: 0016_agt_phase1_memory
Revises: 0015_merge_sd06_optional_gin
Create Date: 2026-06-13

對應（SCG-1 凍結 SRD_AGT_Phase1_Memory.md + ADR-AGT-003 ACCEPTED）：
  - kb_metrics       — F-C3，schema 依 ADR-SD09-006 §2.3
    （原規劃 0015 已被 merge revision 佔用 → 0016）
  - user_preferences — F-C1，PK (scope, key) UPSERT 語意
  - goal_progress    — F-C2，append-only ledger，索引 (goal_task_id, recorded_at DESC)
"""
from __future__ import annotations

revision = "0016_agt_phase1_memory"
down_revision = "0015_merge_sd06_optional_gin"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- =============================================================================
-- kb_metrics（F-C3；ADR-SD09-006 §2.3；[start, end) 半開區間）
-- =============================================================================
CREATE TABLE kb_metrics (
  metric_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_name      text NOT NULL,
  value            double precision NOT NULL,
  window_start_at  timestamptz NOT NULL,
  window_end_at    timestamptz NOT NULL,
  run_id           uuid,
  tags             jsonb DEFAULT '{}'::jsonb,
  recorded_at      timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kb_metrics_name_window ON kb_metrics (metric_name, window_end_at DESC);
CREATE INDEX idx_kb_metrics_run_id ON kb_metrics (run_id) WHERE run_id IS NOT NULL;

COMMENT ON TABLE kb_metrics IS
    'F-C3 / ADR-SD09-006：KB metrics 跨 session 快照（append-only，重啟不清零）';

-- =============================================================================
-- user_preferences（F-C1；L3 使用者偏好；UPSERT by (scope, key)）
-- =============================================================================
CREATE TABLE user_preferences (
  scope       text NOT NULL,
  key         text NOT NULL,
  value       text NOT NULL,
  updated_at  timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (scope, key)
);

COMMENT ON TABLE user_preferences IS
    'F-C1 / ADR-AGT-003 L3：使用者偏好（scope = global 或 playbook:{project}）';

-- =============================================================================
-- goal_progress（F-C2；L4 目標進度；append-only ledger）
-- =============================================================================
CREATE TABLE goal_progress (
  progress_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  goal_task_id        text NOT NULL,
  playbook_id         text,
  run_id              uuid,
  completed_features  jsonb NOT NULL DEFAULT '[]'::jsonb,
  progress_pct        double precision,
  recorded_at         timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_goal_progress_goal ON goal_progress (goal_task_id, recorded_at DESC);

COMMENT ON TABLE goal_progress IS
    'F-C2 / ADR-AGT-003 L4：跨 playbook run 目標進度 ledger'
    '（goal_task_id 無值時以 project:{name} fallback 鍵寫入）';
"""


_DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS goal_progress CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS kb_metrics CASCADE;
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝；請改以 psql 手動執行 0016_agt_phase1_memory 之 SQL"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
