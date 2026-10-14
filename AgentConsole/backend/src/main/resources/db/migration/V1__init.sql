-- ============================================================================
-- V1__init.sql — AgentConsole 資料表（Flyway 擁有 DDL；ADR-001 D5）
-- 來源：PRD §6.2 PostgreSQL DDL 概要，逐字採用（本檔唯一增補是下方的 CREATE SCHEMA）。
-- 表名不加 schema 前綴：spring.flyway.schemas／default-schema = console 時，Flyway 會把
-- search_path 設為 console，因此全部落在 console schema（驗證見 SchemaMigrationIT）。
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS console;

-- 專案表
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    execution_path VARCHAR(500) NOT NULL,
    pass_criteria TEXT NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','READY','EXECUTING','COMPLETED','FAILED','ARCHIVED')),
    autonomy_level INTEGER DEFAULT 3 CHECK (autonomy_level BETWEEN 1 AND 10),
    -- 🔴 人工 signoff 硬閘
    signed_off BOOLEAN NOT NULL DEFAULT FALSE,
    signed_off_by VARCHAR(100),
    signed_off_at TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- 目標表
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    pass_criteria TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','IN_PROGRESS','COMPLETED','FAILED','SKIPPED')),
    -- depends_on UUID[] 已移除：改用獨立關聯表 goal_dependencies（可 FK + 應用層 Kahn 防環）
    signed_off BOOLEAN NOT NULL DEFAULT FALSE,
    signed_off_by VARCHAR(100),
    signed_off_at TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 目標依賴關聯表（取代 goals.depends_on 陣列：可 FK 完整性 + UNIQUE 去重；
-- 環偵測由應用層 Kahn 拓撲排序負責，新增依賴前先試算，成環則拒絕）
CREATE TABLE goal_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    depends_on_goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_goal_dependency UNIQUE (goal_id, depends_on_goal_id),
    CONSTRAINT chk_no_self_dependency CHECK (goal_id <> depends_on_goal_id)
);

-- 任務表
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    pass_criteria TEXT NOT NULL,
    -- 通過標準物化（對映引擎 PlaybookTask；經白名單模板消毒，見 §0.3 / NFR-SEC-03）
    evaluator_command VARCHAR(1000),
    expected_output_regex VARCHAR(1000),
    pass_criteria_spec JSONB,
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','QUEUED','BLOCKED','RUNNING','VALIDATING',
                          'COMPLETED','FAILED','ESCALATED','PAUSED','SKIPPED','CANCELLED')),
    estimated_tokens BIGINT,
    actual_tokens BIGINT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    assigned_agent VARCHAR(100),
    execution_log TEXT,
    -- 🔴 人工 signoff 硬閘
    signed_off BOOLEAN NOT NULL DEFAULT FALSE,
    signed_off_by VARCHAR(100),
    signed_off_at TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 執行批次表
CREATE TABLE execution_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    run_number INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'INITIALIZING'
        CHECK (status IN ('INITIALIZING','RUNNING','PAUSED','COMPLETED','FAILED','CANCELLED')),
    autonomy_level INTEGER NOT NULL,
    scope JSONB NOT NULL,
    total_tokens_used BIGINT DEFAULT 0,
    token_budget BIGINT,
    -- 並發互斥與子程序治理（見 §0.2.2）
    advisory_lock_key BIGINT,           -- pg_advisory_lock(hashtext(project||':'||path)) 之鍵
    subprocess_pid INTEGER,             -- Bridge spawn 的子程序 PID（孤兒回收用）
    bridge_instance VARCHAR(100),       -- 持有此 run 的 Bridge 實例識別（崩潰 reconciliation 用）
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    dag JSONB,
    UNIQUE (project_id, run_number)
);

-- 執行步驟日誌表
CREATE TABLE execution_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES execution_runs(id),
    task_id UUID NOT NULL REFERENCES tasks(id),
    step_number INTEGER NOT NULL,
    action VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL,
    input JSONB,
    output TEXT,
    tokens_used BIGINT,
    error_message TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 斷點表
CREATE TABLE checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES execution_runs(id),
    name VARCHAR(200) NOT NULL,
    state_snapshot JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_automatic BOOLEAN DEFAULT TRUE
);

-- 匯入記錄表
CREATE TABLE import_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(20) NOT NULL,
    source_content TEXT NOT NULL,
    source_file_name VARCHAR(500),
    parsed_result JSONB,
    project_id UUID REFERENCES projects(id),
    status VARCHAR(20) NOT NULL DEFAULT 'UPLOADED'
        CHECK (status IN ('UPLOADED','PARSING','PARSED','REVIEWING','IMPORTED','REJECTED')),
    -- 🔴 人工 signoff 硬閘（草案落為正式專案前置）
    signed_off BOOLEAN NOT NULL DEFAULT FALSE,
    signed_off_by VARCHAR(100),
    signed_off_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ai_model VARCHAR(100),
    token_used BIGINT
);

-- 系統參數表
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    key VARCHAR(200) NOT NULL,
    value TEXT NOT NULL,
    value_type VARCHAR(20) NOT NULL,
    default_value TEXT,
    description VARCHAR(500),
    is_encrypted BOOLEAN DEFAULT FALSE,
    validation_rule VARCHAR(500),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(100),
    UNIQUE (category, key)
);

-- 系統參數修改歷史表
CREATE TABLE system_config_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID NOT NULL REFERENCES system_configs(id),
    old_value TEXT,
    new_value TEXT NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(100)
);

-- 索引
-- 列表查詢索引採 partial index（僅索引未軟刪除列，縮小索引、加速列表）
CREATE INDEX idx_goals_project_id ON goals(project_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_tasks_goal_id ON tasks(goal_id) WHERE is_deleted = FALSE;
-- 目標依賴關聯表索引（雙向查詢 + Kahn 拓撲）
CREATE INDEX idx_goal_dependencies_goal_id ON goal_dependencies(goal_id);
CREATE INDEX idx_goal_dependencies_depends_on ON goal_dependencies(depends_on_goal_id);
CREATE INDEX idx_execution_runs_project_id ON execution_runs(project_id);
CREATE INDEX idx_execution_steps_run_id ON execution_steps(run_id);
CREATE INDEX idx_execution_steps_task_id ON execution_steps(task_id);
CREATE INDEX idx_execution_steps_timestamp ON execution_steps(timestamp);
CREATE INDEX idx_checkpoints_run_id ON checkpoints(run_id);
CREATE INDEX idx_import_records_project_id ON import_records(project_id);
CREATE INDEX idx_system_configs_category_key ON system_configs(category, key);
