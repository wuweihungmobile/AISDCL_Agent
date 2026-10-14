-- ============================================================================
-- V4__monitor_alerts.sql — 持久化告警與確認狀態（ADR-001 D5.3；Phase 5 使用，本波只建表）
-- 來源：Architecture §11.3「DDL 增補」逐字（PRD §6.2 無對應表，見 ADR-001 G-08）。
-- ============================================================================
CREATE TABLE console.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES console.projects(id),
    run_id UUID REFERENCES console.execution_runs(id),
    rule VARCHAR(40) NOT NULL,   -- TOKEN_BUDGET_WARNING／TOKEN_BUDGET_EXCEEDED／CONSECUTIVE_FAILURES／AGENT_UNRESPONSIVE／TASK_DURATION_EXCEEDED／HIGH_RETRY_RATE
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('WARNING','CRITICAL')),
    subject VARCHAR(100),
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_alerts_project_ack ON console.alerts(project_id, acknowledged);
