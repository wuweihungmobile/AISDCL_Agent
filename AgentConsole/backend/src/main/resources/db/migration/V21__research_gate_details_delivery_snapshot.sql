-- V21__research_gate_details_delivery_snapshot.sql — SCG6、決定列 details、交付快照 sha256、SCR 證據連結（D-139）
-- 四個欄位缺口的結構層正解（取代 IFACE-P2 §0 以 reason 前綴與 rtm_report_ref 與 reason 末行承載的作法）。
-- 不改 V1～V20；沒有新表。

-- (1) research_gate_decisions.gate 加 SCG6（RELEASE_READY FAIL 的登錄；與框架 transition_rules.py:311 對齊）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c
                   JOIN pg_class t ON t.oid = c.conrelid
                   JOIN pg_namespace n ON n.oid = t.relnamespace
                   WHERE n.nspname = 'console' AND t.relname = 'research_gate_decisions'
                     AND c.conname = 'research_gate_decisions_gate_check' AND c.contype = 'c') THEN
        RAISE EXCEPTION 'V21: 找不到 research_gate_decisions_gate_check，拒絕在未確認舊 CHECK 的情況下加新 CHECK'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
END
$$;
ALTER TABLE console.research_gate_decisions DROP CONSTRAINT research_gate_decisions_gate_check;
ALTER TABLE console.research_gate_decisions ADD CONSTRAINT research_gate_decisions_gate_check
    CHECK (gate IN ('GATE0','SCR','ROUTE','STAGE2','SCG4','SCG5','SCG6','ABANDON_KEY'));

-- (2) research_gate_decisions.details：審查者獨立性聲明、審查報告參照、CI 紅標記（JSON 物件）
ALTER TABLE console.research_gate_decisions ADD COLUMN details JSONB NOT NULL DEFAULT '{}'::jsonb;   -- 鍵：reviewer_independent、review_report_ref、ci_red
ALTER TABLE console.research_gate_decisions ADD CONSTRAINT ck_research_gate_details_object
    CHECK (jsonb_typeof(details) = 'object');

-- (3) research_deliveries.snapshot_sha256：R11 追溯快照 JSON（03_execution/traceability_matrix.json）的 sha256
ALTER TABLE console.research_deliveries ADD COLUMN snapshot_sha256 CHAR(64);                          -- TAG 列必填由應用層守；PR 列為 NULL
ALTER TABLE console.research_deliveries ADD CONSTRAINT ck_research_deliveries_snapshot_sha256
    CHECK (snapshot_sha256 IS NULL OR snapshot_sha256 ~ '^[0-9a-f]{64}$');

-- (4) research_scr.evidence_url：SCR 的失敗證據連結（https 限定、至多 500 字元；不在受控更新清單）
ALTER TABLE console.research_scr ADD COLUMN evidence_url TEXT;
ALTER TABLE console.research_scr ADD CONSTRAINT ck_research_scr_evidence_url
    CHECK (evidence_url IS NULL OR (evidence_url ~ '^https://' AND char_length(evidence_url) <= 500));
