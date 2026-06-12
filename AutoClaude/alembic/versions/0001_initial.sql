-- AutoClaude PostgreSQL Schema 初始 migration（Phase 6）
-- 對應 SD_Improving_02.md v1.1 §1.3 schema 設計
-- 可直接以 psql 執行，無需 alembic 框架（手寫 .sql 提供降級路徑）

-- ──────────────────────────────────────────────
-- playbook_runs：每次 Playbook 執行的記錄
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS playbook_runs (
    run_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id     TEXT NOT NULL,
    project         TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL CHECK (status IN
                      ('running', 'success', 'escalated', 'halted', 'interrupted')),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_runs_playbook ON playbook_runs(playbook_id);
CREATE INDEX IF NOT EXISTS idx_runs_status   ON playbook_runs(status);

-- ──────────────────────────────────────────────
-- checkpoints：跨 Session 持久化的 Playbook 執行狀態
-- 含 Gap-042 / Gap-048 計數器（counters JSONB）
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id               UUID REFERENCES playbook_runs(run_id),
    playbook_id          TEXT NOT NULL,
    step_idx             INT NOT NULL,
    step_id              TEXT NOT NULL,
    total_steps          INT NOT NULL,
    saved_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    scheduled_resume_at  TIMESTAMPTZ,
    peak_token_pct       FLOAT NOT NULL DEFAULT 0,
    -- Gap-042 / Gap-048 計數器（JSONB 保留彈性）
    counters             JSONB NOT NULL DEFAULT '{
        "goto": {}, "inject_before": {}, "skip_to": {}, "step_evolution": {}
    }'::jsonb,
    completed_step_log   TEXT[] NOT NULL DEFAULT '{}',
    completed_step_ids   TEXT[] NOT NULL DEFAULT '{}',
    failure_history      JSONB NOT NULL DEFAULT '[]'::jsonb,
    active_step_attempt  INT NOT NULL DEFAULT 0,
    last_correction_prompt TEXT NOT NULL DEFAULT ''
);
-- 同一 playbook_id 只保留最新 checkpoint（透過 UPSERT 維持單一活躍狀態）
CREATE UNIQUE INDEX IF NOT EXISTS idx_ck_playbook ON checkpoints(playbook_id);

-- ──────────────────────────────────────────────
-- knowledge_entries：跨 Session 失敗知識庫
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_entries (
    entry_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_class     TEXT NOT NULL,
    error_signature TEXT NOT NULL,
    successful_strategy TEXT,
    tried_strategies    TEXT[] NOT NULL DEFAULT '{}',
    step_id         TEXT NOT NULL,
    outcome         TEXT NOT NULL CHECK (outcome IN ('success', 'escalation')),
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kb_signature ON knowledge_entries(error_class, error_signature);
CREATE INDEX IF NOT EXISTS idx_kb_recent    ON knowledge_entries(recorded_at DESC);

-- ──────────────────────────────────────────────
-- playbook_versions：Playbook 演化版本管理
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS playbook_versions (
    version_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_playbook_id TEXT NOT NULL,
    generation          INT NOT NULL,
    yaml_content        TEXT NOT NULL,
    mutation_log        TEXT[] NOT NULL DEFAULT '{}',
    parent_version_id   UUID REFERENCES playbook_versions(version_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pv_playbook ON playbook_versions(original_playbook_id, generation);
