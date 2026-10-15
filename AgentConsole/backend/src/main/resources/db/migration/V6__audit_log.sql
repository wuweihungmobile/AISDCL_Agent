-- ============================================================================
-- V6__audit_log.sql — 寫入端點審計落庫（NFR-9.2-07；契約 §0.5／§0.4 第 5 點）
-- 內部實作：不進 HTTP 契約（沒有任何端點讀它）。每個寫入請求（POST／PUT／PATCH／DELETE，限 /api/）一列；
-- 寫入失敗不得影響主請求（AuditLoggingFilter 吞掉例外並記 WARN）。不記請求本文（避免把密碼或敏感參數寫進資料庫）。
-- ============================================================================
CREATE TABLE console.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    subject VARCHAR(100),          -- JWT subject；未認證（401）為 NULL
    role VARCHAR(20),              -- ADMIN／OPERATOR／VIEWER；未認證為 NULL
    method VARCHAR(10) NOT NULL,
    path VARCHAR(500) NOT NULL,    -- request URI（不含 query string，避免 access_token 落庫）
    entity_type VARCHAR(50),       -- 例：import、settings、projects
    entity_id VARCHAR(100),        -- 路徑上的第一個 UUID，或服務層標註的實體識別
    http_status INTEGER NOT NULL,
    trace_id VARCHAR(64)
);
CREATE INDEX idx_audit_log_occurred_at ON console.audit_log(occurred_at);
CREATE INDEX idx_audit_log_subject_occurred_at ON console.audit_log(subject, occurred_at);
