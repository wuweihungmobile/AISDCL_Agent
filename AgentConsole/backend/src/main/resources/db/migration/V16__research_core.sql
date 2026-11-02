-- V16__research_core.sql — ResearchToPRD P0：研究專案（流程脊游標）、事件帳、stage run、檔案登記
-- 寫入者唯一＝engine-bridge（Architecture §7.2）；console-api 只讀（JDBC，無 JPA 實體，ddl-auto=validate 不檢查本表；先例 V13／V15）。
-- 人工決定的「誰對哪個實體做了請求」由既有 V6 audit_log 記；內容住 V18 research_gate_decisions。
CREATE SEQUENCE console.research_rp_seq START 1;

CREATE FUNCTION console.research_next_rp_no() RETURNS text LANGUAGE sql AS
$$ SELECT 'RP-' || lpad(n::text, GREATEST(4, length(n::text)), '0') FROM (SELECT nextval('console.research_rp_seq') AS n) s $$;   -- 超過 4 位數不截斷

CREATE TABLE console.research_projects (
    id UUID PRIMARY KEY,                                   -- console-api 配號（同 execution_runs.id 先例）
    rp_no VARCHAR(12) NOT NULL UNIQUE DEFAULT console.research_next_rp_no() CHECK (rp_no ~ '^RP-[0-9]{4,}$'),   -- 顯示編號（D-37）
    slug VARCHAR(30) NOT NULL CHECK (slug ~ '^[a-z0-9][a-z0-9-]{0,29}$'),
    title VARCHAR(200) NOT NULL,
    topic TEXT NOT NULL CHECK (char_length(topic) <= 500),
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,              -- issue_scope.json 的鏡像：技術棧、層開關、檢索邊界
    scope_rev INTEGER NOT NULL DEFAULT 1 CHECK (scope_rev >= 1),
    depth_level VARCHAR(10) NOT NULL DEFAULT 'STANDARD' CHECK (depth_level IN ('QUICK','STANDARD','DEEP')),
    target_scope VARCHAR(20) NOT NULL DEFAULT 'UNDECIDED'
        CHECK (target_scope IN ('UNDECIDED','AISDLC_MODULE','STANDALONE_PROJECT')),
    workspace_path VARCHAR(500) NOT NULL,                  -- <BRIDGE_RESEARCH_ROOT>/<slug>（絕對路徑；預設 repo 外，D-28）
    fsm_project VARCHAR(100) NOT NULL,                     -- 外環鍵 research-<slug>[-g<N>]
    fsm_state_dir VARCHAR(500) NOT NULL,                   -- <workspace>/build/reports/fsm
    fsm_generation INTEGER NOT NULL DEFAULT 1 CHECK (fsm_generation >= 1),
    -- 流程脊游標（Bridge 與引擎動作同一交易寫入；步驟 3 之後的相態為衍生，不落此欄）
    flow_step VARCHAR(10) NOT NULL DEFAULT 'topic' CHECK (flow_step IN ('topic','studio','route','build','deliver')),
    flow_phase VARCHAR(20) NOT NULL DEFAULT 'INGESTED' CHECK (flow_phase IN (
        'INGESTED','RESEARCHING','EVIDENCE_READY','DRAFTING','REVIEWING','REVISING','GATE0_PENDING','FROZEN',
        'ROUTING','ROUTED','TCS_DRAFTING','TCS_PENDING','SCR_OPEN')),
    flow_status VARCHAR(14) NOT NULL DEFAULT 'IDLE' CHECK (flow_status IN (
        'IDLE','RUNNING','WAITING_HUMAN','BLOCKED','ESCALATED','FAILED','CANCELLED','COMPLETED')),
    flow_detail VARCHAR(300) NOT NULL DEFAULT '',
    console_project_id UUID REFERENCES console.projects(id),   -- 分流後綁定的 Console 專案（console-api 先建、Bridge 後填；D-37）
    parent_research_id UUID REFERENCES console.research_projects(id),   -- 大型 SCR 的前身
    last_event_seq BIGINT NOT NULL DEFAULT 0,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMP WITH TIME ZONE
);
CREATE UNIQUE INDEX ux_research_projects_slug_active ON console.research_projects (slug) WHERE archived_at IS NULL;
CREATE UNIQUE INDEX ux_research_projects_console_project ON console.research_projects (console_project_id) WHERE console_project_id IS NOT NULL;
CREATE INDEX idx_research_projects_flow ON console.research_projects (flow_step, flow_status) WHERE archived_at IS NULL;

-- 共用的 append-only 守衛（V13 si_console_writes_guard 的泛化：任何 UPDATE／DELETE 一律拒絕）
CREATE FUNCTION console.research_append_only_guard() RETURNS trigger
    LANGUAGE plpgsql AS
$$
BEGIN
    RAISE EXCEPTION '% 為 append-only（不可改、不可刪）', TG_TABLE_NAME
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;

-- 受控可更新表的通用守衛（D-49）：表名→允許更新欄位清單；清單外欄位的 UPDATE 與任何 DELETE 一律拒絕（更正＝追加新列）。
-- 全部 18 張 research_* 表不是掛 research_append_only_guard() 就是掛本函式，所以沒有任何一張表可被 DELETE；兩者拒絕時一律 ERRCODE = 'integrity_constraint_violation'（SQLSTATE 23000；D-53）。審查輪表 research_review_rounds 是 append-only（掛 research_append_only_guard()），不在下方允許清單內（D-57）。
-- V19 各表的條目一併在此宣告（函式於 V16 一次建立；V19 只掛觸發器，Flyway 已發佈檔不改）。
CREATE FUNCTION console.research_controlled_update_guard() RETURNS trigger
    LANGUAGE plpgsql AS
$$
DECLARE
    allowed text[];
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION '% 不可刪除（更正＝追加新列）', TG_TABLE_NAME
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    allowed := CASE TG_TABLE_NAME
        WHEN 'research_projects' THEN ARRAY['title','topic','scope','scope_rev','depth_level','target_scope','fsm_project','fsm_generation',
                                            'flow_step','flow_phase','flow_status','flow_detail','console_project_id',
                                            'last_event_seq','updated_at','archived_at']
        WHEN 'research_stage_runs' THEN ARRAY['status','tokens_used','exit_reason','started_at','finished_at']
        WHEN 'research_sources' THEN ARRAY['verification']
        WHEN 'research_review_defects' THEN ARRAY['status','fixed_in_version_no','waived_by','waiver_reason','resolved_at']
        WHEN 'research_allowlist_entries' THEN ARRAY['enabled','disabled_by','disabled_at']
        WHEN 'research_route_decisions' THEN ARRAY['status','failure_step','finished_at','repo_url','published_docs',
                                                   'console_project_id','impl_fsm_project','impl_state_dir']
        WHEN 'research_route_steps' THEN ARRAY['status','exit_code','stdout_tail','stderr_tail','finished_at']
        WHEN 'research_decompositions' THEN ARRAY['status','draft_id','import_record_id','tcs_rel_path','tcs_sha256','tasks_count','gate_rejection']
        WHEN 'research_scr' THEN ARRAY['status','prd_to_version_no','successor_research_id','impl_fsm_actions','decided_by','decided_at']
        ELSE NULL
    END;
    IF allowed IS NULL THEN
        RAISE EXCEPTION '% 未登記於 research_controlled_update_guard 的允許清單', TG_TABLE_NAME
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (to_jsonb(NEW) - allowed) IS DISTINCT FROM (to_jsonb(OLD) - allowed) THEN
        RAISE EXCEPTION '% 只准更新 %', TG_TABLE_NAME, allowed
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_research_projects_guard BEFORE UPDATE OR DELETE ON console.research_projects
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();

CREATE TABLE console.research_events (
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    seq BIGINT NOT NULL CHECK (seq >= 1),                  -- 每專案單調；＝SSE id
    event_type VARCHAR(40) NOT NULL,                       -- research.step／run／source／evidence／prd／review／review_invalid／defect／gate／reconcile／route／scr／delivery／alert
    step VARCHAR(10) NOT NULL,
    actor VARCHAR(100) NOT NULL,                           -- JWT subject 或 'bridge'
    ref_kind VARCHAR(30),
    ref_id UUID,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (research_id, seq)
);
CREATE INDEX idx_research_events_type ON console.research_events (research_id, event_type);
CREATE TRIGGER trg_research_events_guard BEFORE UPDATE OR DELETE ON console.research_events
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_stage_runs (
    id UUID PRIMARY KEY,                                   -- Bridge 配號；＝引擎 run_id
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    stage VARCHAR(10) NOT NULL CHECK (stage IN ('RESEARCH','DRAFT','REVIEW','REVISE','TCS_DRAFT')),
    round_no INTEGER NOT NULL DEFAULT 0 CHECK (round_no >= 0),   -- REVIEW stage run：本次要產生的輪號（已完成評估的輪數＋1）；取消／中斷／無效輸出後重審沿用同號、attempt＋1，審查輪列不因此新增或佔號（D-57）
    attempt INTEGER NOT NULL DEFAULT 1 CHECK (attempt >= 1),
    scope_rev INTEGER NOT NULL DEFAULT 1 CHECK (scope_rev >= 1),
    status VARCHAR(10) NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','BLOCKED_DB')),
    playbook_sha256 CHAR(64) CHECK (playbook_sha256 ~ '^[0-9a-f]{64}$'),
    config_sha256 CHAR(64) CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    prompt_manifest JSONB NOT NULL DEFAULT '[]'::jsonb,    -- [{role, agent_yaml, yaml_sha256, persona_sha256}]
    allowlist_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb, -- 本 run 的有效 FETCH／WEB 清單（D-17 事後稽核）
    tokens_used BIGINT NOT NULL DEFAULT 0,
    exit_reason VARCHAR(300) NOT NULL DEFAULT '',
    requested_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (research_id, stage, round_no, attempt)
);
CREATE INDEX idx_research_stage_runs_status ON console.research_stage_runs (status) WHERE status IN ('QUEUED','RUNNING','BLOCKED_DB');
CREATE UNIQUE INDEX ux_research_stage_runs_active ON console.research_stage_runs (research_id) WHERE status IN ('QUEUED','RUNNING');   -- D-61（D-27）：同一研究專案同時至多一個進行中的 stage run；並行上限 1 由資料庫守，應用層 409 stage_conflict 在其前
-- 編譯結果欄（playbook_sha256／config_sha256／prompt_manifest／allowlist_snapshot）於建立列時一併寫入、之後唯讀（通用守衛的允許清單只有 status／tokens_used／exit_reason／started_at／finished_at）
CREATE TRIGGER trg_research_stage_runs_guard BEFORE UPDATE OR DELETE ON console.research_stage_runs
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();

CREATE TABLE console.research_artifacts (                  -- 檔案登記：每個具名檔案版本一列（「檔案 ↔ 表」的樞紐）
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    kind VARCHAR(20) NOT NULL CHECK (kind IN (
        'ISSUE_SCOPE','EVIDENCE_ITEMS','EVIDENCE_MATRIX','PRD_DRAFT','PRD_BASELINE','ADR_DRAFT','REVIEW_CARD',
        'ROUTE_DECISION','STATE_EXPORT','TASK_DECOMPOSITION','TCS','HEALING_LOG')),
    version INTEGER NOT NULL CHECK (version >= 1),
    rel_path VARCHAR(500) NOT NULL,                        -- 相對工作區
    sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    bytes BIGINT NOT NULL CHECK (bytes >= 0),
    origin VARCHAR(6) NOT NULL CHECK (origin IN ('AGENT','HUMAN','BRIDGE')),
    content TEXT CHECK (content IS NULL OR octet_length(content) <= 1048576),   -- JSON 類產物全文（nullable，≤1 MiB 位元組：octet_length 計位元組、length 計字元，多位元組字元會使後者低估；D-53、D-59(2)）：kind=EVIDENCE_ITEMS 者為 evidence_items.json 位元組原樣全文，含 counter_evidence／honest_bounds（D-43；P0 不另立表）
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (research_id, kind, version)
);
CREATE TRIGGER trg_research_artifacts_guard BEFORE UPDATE OR DELETE ON console.research_artifacts
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();
