-- V22__research_flow_phase_delivered.sql — research_projects.flow_phase 放寬 DELIVERED（D-162(a)）
-- WHY：V16 的 flow_phase CHECK 沒有 DELIVERED，TCS AT-962-18-5 要求的交付完成游標 deliver／DELIVERED／COMPLETED 寫不進來；
-- 結構層正解＝新遷移放寬 CHECK（與 V21 對 gate 加 SCG6 同型），不改已發佈的 V16／V21。
-- flow_step 的 CHECK 已含 deliver、flow_status 的 CHECK 已含 COMPLETED，故只放寬 flow_phase；不改其他表、沒有新表。

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c
                   JOIN pg_class t ON t.oid = c.conrelid
                   JOIN pg_namespace n ON n.oid = t.relnamespace
                   WHERE n.nspname = 'console' AND t.relname = 'research_projects'
                     AND c.conname = 'research_projects_flow_phase_check' AND c.contype = 'c') THEN
        RAISE EXCEPTION 'V22: 找不到 research_projects_flow_phase_check，拒絕在未確認舊 CHECK 的情況下加新 CHECK'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
END
$$;
ALTER TABLE console.research_projects DROP CONSTRAINT research_projects_flow_phase_check;
ALTER TABLE console.research_projects ADD CONSTRAINT research_projects_flow_phase_check
    CHECK (flow_phase IN (
        'INGESTED','RESEARCHING','EVIDENCE_READY','DRAFTING','REVIEWING','REVISING','GATE0_PENDING','FROZEN',
        'ROUTING','ROUTED','TCS_DRAFTING','TCS_PENDING','SCR_OPEN','DELIVERED'));
