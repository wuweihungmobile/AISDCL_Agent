-- V18__research_prd_review_gate.sql — PRD 版本（含本文，供工作室編輯器與 Diff）、四方審查輪、分數、缺陷、人工決定（Gate 0 屬 P0，所以決定表隨 V18）
CREATE TABLE console.research_prd_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    semver VARCHAR(30) NOT NULL CHECK (semver ~ '^v[0-9]+\.[0-9]+\.[0-9]+(-draft)?$'),   -- 含 v 前綴：例 v0.3.0-draft、v1.0.0（審查卡與 route_decision.json 的 prd_version 字串；D-43）
    kind VARCHAR(8) NOT NULL CHECK (kind IN ('DRAFT','BASELINE')),
    author_kind VARCHAR(5) NOT NULL CHECK (author_kind IN ('AGENT','HUMAN')),
    author VARCHAR(100) NOT NULL,                          -- agent id 或 JWT subject
    parent_version_no INTEGER,
    content TEXT NOT NULL CHECK (octet_length(content) <= 1048576),   -- 位元組（非字元數；D-59(2)）
    rel_path VARCHAR(500) NOT NULL,
    sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    bytes INTEGER NOT NULL CHECK (bytes >= 0),
    evidence_refs VARCHAR(8)[] NOT NULL DEFAULT '{}',      -- PRD 內 [E-NNN] 引用（M1 證據錨定率的分子分母）
    change_summary VARCHAR(500) NOT NULL DEFAULT '',
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (research_id, version_no),
    FOREIGN KEY (research_id, parent_version_no) REFERENCES console.research_prd_versions (research_id, version_no)
);
CREATE TRIGGER trg_research_prd_versions_guard BEFORE UPDATE OR DELETE ON console.research_prd_versions
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

-- 審查輪列只在輪有結果時（前置否決已判，或四維審查卡皆通過驗證並彙整、`gate` 已回傳）與四維分數列、缺陷列、research_events 同一交易一次寫入（D-57）。
-- 列存在＝輪已完成評估，所以沒有 status 欄：單值欄位沒有資訊量，還會留下「日後有人寫 RUNNING 列」的後路；
-- 進行中、取消、中斷（額度或 API）、Bridge 重啟、輸出無效（REVIEW_INVALID）一律不寫列、不佔 round_no、不耗預算，
-- 只記 REVIEW stage run（research_stage_runs，UNIQUE(research_id, stage, round_no, attempt)）與事件。
-- round_no＝已完成評估的序號，與 FSM gate 呼叫一一對應（POST_HUMAN 通過輪除外；人工退回呼叫 gate FAIL 但不是審查輪）。
-- round_no 連續（1、2、3…不跳號）由 Bridge 寫入器於同交易 max+1 配號保證、AT 守（D-61）：UNIQUE(research_id, round_no) 只擋重複、不擋跳號，連續性不下沉為 DDL。
CREATE TABLE console.research_review_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    round_no INTEGER NOT NULL CHECK (round_no >= 1),
    fsm_generation INTEGER NOT NULL DEFAULT 1,
    prd_version_no INTEGER NOT NULL,
    trigger_kind VARCHAR(10) NOT NULL CHECK (trigger_kind IN ('AUTO','MANUAL','POST_HUMAN')),
    precheck_passed BOOLEAN NOT NULL,                      -- 前置否決 P1（SLV-001／SLV-002／SLV-003／AMBIGUITY）；FALSE＝不計分直接 FAIL
    precheck_detail JSONB NOT NULL DEFAULT '{}'::jsonb,    -- {"checks":[{"id","passed","detail"}×4]}（審查卡 precheck.checks[]）
    weighted_score NUMERIC(5,2) CHECK (weighted_score BETWEEN 0 AND 100),   -- W100/100 精確值，不四捨五入（D-42）；前置否決不過時 NULL
    threshold NUMERIC(5,2) NOT NULL DEFAULT 85.00 CHECK (threshold BETWEEN 50.00 AND 100.00),   -- D-61：產品常數的範圍鎖（passed 的 CHECK 以它為比較基準，被寫成 0 會使 passed 恆真）
    floor_score INTEGER NOT NULL DEFAULT 60 CHECK (floor_score BETWEEN 50 AND 100),   -- D-14／D-42／D-65：任一維度不低於地板（初值 60、未校準）；範圍鎖與 threshold 對稱，地板被寫成 0 會架空 D-14
    min_dimension_score INTEGER CHECK (min_dimension_score BETWEEN 0 AND 100),
    open_p1_count INTEGER NOT NULL DEFAULT 0 CHECK (open_p1_count >= 0),
    passed BOOLEAN NOT NULL,
    verdict VARCHAR(8) NOT NULL CHECK (verdict IN ('PASS','REVISE','ESCALATE')),     -- REVIEW_INVALID 不是輪的 verdict：無效輸出不寫輪列、不佔 round_no，只記 stage run（exit_reason=review_invalid）與事件 research.review_invalid（D-55）
    fsm_gate_result VARCHAR(4) CHECK (fsm_gate_result IN ('PASS','FAIL')),
    fsm_retry_count INTEGER,                               -- gate FAIL 的回傳 retry_count；gate PASS 的回傳不帶 retry_count，引擎於 PASS 時歸零，故寫 0；POST_HUMAN 通過輪未呼叫 gate ⇒ NULL（D-61；與 fsm_gate_result 同為 NULL）
    escalated BOOLEAN NOT NULL DEFAULT FALSE,
    stage_run_id UUID NOT NULL REFERENCES console.research_stage_runs(id),   -- 產生本輪的 REVIEW stage run；進行中的狀態只住那裡（D-57）
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,          -- 取自該 stage run 的 started_at；列到有結果才寫，不能用 DEFAULT NOW()（那會變成寫入時刻）
    finished_at TIMESTAMP WITH TIME ZONE NOT NULL,         -- 取自該 stage run 的 finished_at
    UNIQUE (research_id, round_no),
    FOREIGN KEY (research_id, prd_version_no) REFERENCES console.research_prd_versions (research_id, version_no),
    CHECK (finished_at >= started_at),
    -- 以 IS TRUE 形式寫，避免 NULL 比較使 CHECK 靜默通過（D-14 三條件＋預檢＋verdict；D-42：weighted_score 是 W100/100 精確值，比較不經四捨五入）
    CHECK (passed IS NOT TRUE OR ((weighted_score >= threshold) IS TRUE AND (min_dimension_score >= floor_score) IS TRUE
                                  AND open_p1_count = 0 AND precheck_passed IS TRUE AND verdict IS NOT DISTINCT FROM 'PASS')),
    -- D-50：自動／手動觸發的通過輪必有 gate PASS；人工退回後的再審（POST_HUMAN）通過只記 DB、不呼叫 gate PASS
    CHECK (passed IS NOT TRUE OR trigger_kind = 'POST_HUMAN' OR fsm_gate_result IS NOT DISTINCT FROM 'PASS'),
    CHECK (NOT (trigger_kind = 'POST_HUMAN' AND passed IS TRUE) OR fsm_gate_result IS NULL),
    -- D-57：輪與 gate 呼叫一一對應——未通過的輪必有 gate FAIL（與上兩條合起來：fsm_gate_result 為 NULL ⇔ POST_HUMAN 通過）
    CHECK (passed IS TRUE OR fsm_gate_result IS NOT DISTINCT FROM 'FAIL'),
    -- 前置否決不過＝不計分（審查卡：weighted_total、min_dimension_score 為 null）
    CHECK (precheck_passed IS NOT FALSE OR (weighted_score IS NULL AND min_dimension_score IS NULL AND passed IS NOT TRUE)),
    -- D-61：單向 CHECK 留下的反向缺口（以下三條只用 NOT NULL 欄或 IS NULL 判，不產生 NULL 結果）
    CHECK ((verdict = 'PASS') = (passed IS TRUE)),                       -- PASS 與 passed 互為充要（補「passed 為 false 卻 verdict='PASS'」）
    CHECK (escalated = (verdict = 'ESCALATE')),                          -- escalated 與 ESCALATE 互為充要
    CHECK ((fsm_retry_count IS NULL) = (fsm_gate_result IS NULL))        -- 兩欄同為 NULL（POST_HUMAN 通過輪未呼叫 gate）或同非 NULL
);
-- append-only（D-57）：任何 UPDATE／DELETE 一律拒絕；輪列沒有「事後寫終態欄」這回事，所以不在通用守衛的允許清單內
CREATE TRIGGER trg_research_review_rounds_guard BEFORE UPDATE OR DELETE ON console.research_review_rounds
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_review_scores (
    round_id UUID NOT NULL REFERENCES console.research_review_rounds(id),
    dimension VARCHAR(12) NOT NULL CHECK (dimension IN ('ARCHITECTURE','PRODUCT','QA','SECURITY')),
    weight NUMERIC(4,3) NOT NULL CHECK (weight > 0 AND weight <= 1),                -- 0.300／0.250／0.250／0.200
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),                        -- 五項 rubric（各 0～20）之和；整數（D-42）
    agent_id VARCHAR(80) NOT NULL,                         -- sd-architect／pm-po／qa-tester／security-engineer（PRODUCT 維度＝pm-po，即 agent/core/03.pm-po-agent-zh.yaml 的 agent.id；D-44）
    assist_agent_id VARCHAR(80),                           -- 只有 SECURITY：compliance-officer（授權項輔助），其餘 NULL
    assist_agent_yaml_sha256 CHAR(64) CHECK (assist_agent_yaml_sha256 IS NULL OR assist_agent_yaml_sha256 ~ '^[0-9a-f]{64}$'),
    agent_yaml_path VARCHAR(300) NOT NULL,
    agent_yaml_sha256 CHAR(64) NOT NULL CHECK (agent_yaml_sha256 ~ '^[0-9a-f]{64}$'),
    persona_sha256 CHAR(64) NOT NULL CHECK (persona_sha256 ~ '^[0-9a-f]{64}$'),
    summary TEXT NOT NULL DEFAULT '',
    raw_rel_path VARCHAR(500) NOT NULL,
    raw_sha256 CHAR(64) NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    CHECK ((assist_agent_id IS NULL) = (assist_agent_yaml_sha256 IS NULL)),
    PRIMARY KEY (round_id, dimension)
);
CREATE TRIGGER trg_research_review_scores_guard BEFORE UPDATE OR DELETE ON console.research_review_scores
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_review_defects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES console.research_review_rounds(id),
    defect_no VARCHAR(16) NOT NULL,                        -- D-<輪>-<NNN>（審查卡 defects[].id）
    dimension VARCHAR(12) NOT NULL CHECK (dimension IN ('ARCHITECTURE','PRODUCT','QA','SECURITY')),
    severity VARCHAR(2) NOT NULL CHECK (severity IN ('P1','P2','P3','P4')),
    code VARCHAR(40) NOT NULL,
    prd_anchor VARCHAR(200) NOT NULL DEFAULT '',
    description TEXT NOT NULL,
    suggestion TEXT NOT NULL DEFAULT '',
    evidence_refs VARCHAR(8)[] NOT NULL DEFAULT '{}',
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','FIXED','WAIVED','SUPERSEDED','REGRESSED')),
    fixed_in_version_no INTEGER,
    waived_by VARCHAR(100),
    waiver_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (round_id, defect_no),
    CHECK (status <> 'WAIVED' OR (waived_by IS NOT NULL AND waiver_reason IS NOT NULL)),          -- 審查卡 waiver{by,reason,at}：by／reason 必填（D-53）
    CHECK (status NOT IN ('FIXED','WAIVED','SUPERSEDED') OR resolved_at IS NOT NULL)            -- 離開 OPEN 的終態必有解決時間（D-53）；WAIVED 的 waiver.at＝resolved_at
);
-- 缺陷 status 單向轉移（D-49；審查卡模板 §5.3）：OPEN→FIXED／WAIVED／SUPERSEDED、FIXED→REGRESSED、REGRESSED→FIXED，其餘一律拒；status 未變動的 UPDATE 不受限
CREATE FUNCTION console.research_defect_status_guard() RETURNS trigger LANGUAGE plpgsql AS
$$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
           (OLD.status = 'OPEN'      AND NEW.status IN ('FIXED','WAIVED','SUPERSEDED'))
        OR (OLD.status = 'FIXED'     AND NEW.status = 'REGRESSED')
        OR (OLD.status = 'REGRESSED' AND NEW.status = 'FIXED')) THEN
        RAISE EXCEPTION 'research_review_defects.status 不得由 % 轉為 %', OLD.status, NEW.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_research_defects_guard BEFORE UPDATE OR DELETE ON console.research_review_defects
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_defects_status BEFORE UPDATE OF status ON console.research_review_defects
    FOR EACH ROW EXECUTE FUNCTION console.research_defect_status_guard();
CREATE INDEX idx_research_defects_open ON console.research_review_defects (round_id) WHERE status = 'OPEN';

CREATE TABLE console.research_gate_decisions (             -- append-only；內容與 V6 audit_log 以 audit_trace_id 對應
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    gate VARCHAR(11) NOT NULL CHECK (gate IN ('GATE0','SCR','ROUTE','STAGE2','SCG4','SCG5','ABANDON_KEY')),
    decision VARCHAR(9) NOT NULL CHECK (decision IN ('APPROVED','REJECTED','CHANGES','ABANDONED')),
    decided_by VARCHAR(100) NOT NULL,                      -- JWT subject（人；僅 ADMIN 動作，D-12）
    decided_at TIMESTAMP WITH TIME ZONE NOT NULL,
    prd_version_no INTEGER,
    review_round_no INTEGER,
    fsm_project VARCHAR(100) NOT NULL,
    fsm_stage VARCHAR(64),                                 -- Gate-0／Gate-0-SCR1／Stage-1／Stage-2
    fsm_state_after VARCHAR(40),
    frozen_digests JSONB NOT NULL DEFAULT '{}'::jsonb,     -- {相對路徑: sha256}；＝frozen_stages[-1].spec_doc_digests
    reason TEXT NOT NULL DEFAULT '',
    audit_trace_id VARCHAR(64),
    CHECK (gate <> 'GATE0' OR decision <> 'APPROVED' OR (frozen_digests <> '{}'::jsonb AND fsm_stage IS NOT NULL))
);
CREATE INDEX idx_research_gate_research ON console.research_gate_decisions (research_id, decided_at);
CREATE TRIGGER trg_research_gate_guard BEFORE UPDATE OR DELETE ON console.research_gate_decisions
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();
