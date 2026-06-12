-- 00_initial_data.sql
-- AutoClaude PostgreSQL backend 示範 seed 資料（W4-T15 m-9）
--
-- ⚠️ 重要：
--   - 僅供 staging / demo 環境使用，不可在 production 執行
--   - 執行前請確認 alembic upgrade head 已成功（schema 已建立）
--   - 此檔不在 alembic 版本鏈中，不會自動執行
--
-- 執行方式：
--   psql "$AUTOCLAUDE_DB_DSN" -f alembic/seeds/00_initial_data.sql

BEGIN;

-- ── playbook_runs 示範資料 ───────────────────────────────────────
-- 提供一筆 "running" 狀態的 demo run，方便 CheckpointPlugin smoke test
INSERT INTO playbook_runs (run_id, playbook_id, project, status, metadata)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'demo_playbook',
    'AutoClaude Demo',
    'running',
    '{"source": "alembic/seeds/00_initial_data.sql"}'::jsonb
)
ON CONFLICT (run_id) DO NOTHING;

-- ── checkpoints 示範資料 ─────────────────────────────────────────
INSERT INTO checkpoints (
    run_id, playbook_id, step_idx, step_id, total_steps,
    peak_token_pct, counters,
    completed_step_log, completed_step_ids,
    failure_history, active_step_attempt, last_correction_prompt
)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'demo_playbook',
    0,
    'T01',
    3,
    0.0,
    '{}'::jsonb,
    '{}'::text[],
    '{}'::text[],
    '[]'::jsonb,
    0,
    ''
)
ON CONFLICT (run_id) DO NOTHING;

-- ── knowledge_entries 示範資料（FailureKnowledgeBase 元學習種子） ──
-- 示範一筆 "syntax error → PINPOINT 策略" 的成功案例
INSERT INTO knowledge_entries (
    error_class, error_signature, successful_strategy,
    tried_strategies, step_id, outcome
)
VALUES (
    'syntax',
    'demo:T01:env_setup',
    'PINPOINT',
    '{}'::text[],
    'T01',
    'success'
)
ON CONFLICT DO NOTHING;

COMMIT;
