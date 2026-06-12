-- 0016_agt_phase1_memory.sql — 純 psql 環境 fallback 鏡像
-- 對應 alembic/versions/0016_agt_phase1_memory.py（Improving_012 Phase 1）
-- 執行前提：0015_merge_sd06_optional_gin 已套用

BEGIN;

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
    'F-C2 / ADR-AGT-003 L4：跨 playbook run 目標進度 ledger（goal_task_id 無值時以 project:{name} fallback 鍵寫入）';

-- alembic 版本戳記（純 psql fallback 時手動推進）
UPDATE alembic_version SET version_num = '0016_agt_phase1_memory';

COMMIT;
