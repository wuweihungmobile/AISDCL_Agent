-- ============================================================================
-- V3__review_requests.sql — 持久化待審核項（ADR-001 D5.3；Phase 4 使用，本波只建表）
-- 來源：Architecture §11.3「DDL 增補」逐字（PRD §6.2 無對應表，見 ADR-001 G-08）。
-- ============================================================================
CREATE TABLE console.review_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES console.execution_runs(id),
    step_id UUID REFERENCES console.execution_steps(id),
    task_id UUID REFERENCES console.tasks(id),
    goal_id UUID REFERENCES console.goals(id),
    kind VARCHAR(20) NOT NULL
        CHECK (kind IN ('TASK_CONFIRM','GOAL_CONFIRM','GOAL_COMPLETED','ESCALATED')),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','APPROVED','REJECTED','RETRIED','SKIPPED')),
    reason TEXT,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decided_by VARCHAR(100),
    decided_at TIMESTAMP WITH TIME ZONE,
    comment TEXT
);
CREATE INDEX idx_review_requests_run_status ON console.review_requests(run_id, status);
