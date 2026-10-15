-- ============================================================================
-- V7__console_event_anchors_and_token_samples.sql — W3-B2（契約 §0.5）
-- ① Console 自產 SSE 事件（review-request／alert）的重播錨點（子序號規則見契約 §2.2）
-- ② console-api 已處理到的 Bridge 事件 seq（Console 擁有此欄；Bridge 不寫）
-- ③ Token 趨勢與任務 Token 歸因的來源（Bridge 不寫 execution_steps.tokens_used，契約 §6 D-16）
-- ④ 同一規則＋對象在被確認前不重複產生告警（PRD §5.4.4；DB 層兜底）
-- ============================================================================

-- ① 重播錨點：event_seq＝建立當下已處理到的最後一則 Bridge 事件 seq；event_sub＝同錨點下的子序號（≥1）
ALTER TABLE console.review_requests
    ADD COLUMN event_seq INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN event_sub INTEGER NOT NULL DEFAULT 1;
ALTER TABLE console.alerts
    ADD COLUMN event_seq INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN event_sub INTEGER NOT NULL DEFAULT 1;      -- 0＝Bridge 告警事件的持久化鏡像（SSE 不重播它）

-- ② console-api 已處理到的 Bridge 事件 seq（Console 擁有此欄；Bridge 不寫）
ALTER TABLE console.execution_runs
    ADD COLUMN console_last_seq INTEGER NOT NULL DEFAULT 0;

-- ③ Token 趨勢與任務 Token 歸因的來源
CREATE TABLE console.run_token_samples (
    run_id      UUID NOT NULL REFERENCES console.execution_runs(id) ON DELETE CASCADE,
    seq         INTEGER NOT NULL,
    ts          TIMESTAMP WITH TIME ZONE NOT NULL,
    tokens_used BIGINT NOT NULL,            -- 本批次累計（Bridge token 事件的 tokens_used）
    delta       BIGINT NOT NULL,            -- 與前一則的差
    context_pct DOUBLE PRECISION,
    task_id     UUID REFERENCES console.tasks(id),   -- 增量歸因的任務（目前 RUNNING 的步驟）
    PRIMARY KEY (run_id, seq)
);
CREATE INDEX idx_run_token_samples_ts ON console.run_token_samples(ts);

-- ④ 同一規則＋對象在被確認前不重複產生告警（alerts.subject 對規則型告警永遠非 null，否則 NULL 會讓索引失效）
CREATE UNIQUE INDEX uq_alerts_open_rule_subject
    ON console.alerts(project_id, rule, subject) WHERE acknowledged = FALSE;
