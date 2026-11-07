-- V19__research_route_scr_delivery.sql — 分流、SCR、拆解、交付；自癒視圖
CREATE TABLE console.research_route_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    track CHAR(1) NOT NULL CHECK (track IN ('A','B')),
    target_kind VARCHAR(10) NOT NULL CHECK (target_kind IN ('MODULE','STANDALONE')),
    target_module VARCHAR(12) CHECK (target_module IN ('autoclaude','agentconsole','sdd','monorepo')),
    target_path VARCHAR(500) NOT NULL,
    git_branch VARCHAR(200),
    base_ref VARCHAR(200),
    repo_url VARCHAR(500),
    repo_visibility VARCHAR(7) CHECK (repo_visibility IN ('PUBLIC','PRIVATE')),
    stack_template VARCHAR(40),
    console_project_id UUID REFERENCES console.projects(id),
    impl_fsm_project VARCHAR(100),
    impl_state_dir VARCHAR(500),
    published_docs JSONB NOT NULL DEFAULT '{}'::jsonb,     -- {目標 docs/ 相對路徑: sha256}
    scope_differs_reason VARCHAR(200),                     -- 分流與 PRD target_scope 不同時必填（FR-R2P-11）
    status VARCHAR(11) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','COMPENSATED')),
    failure_step VARCHAR(30),
    decided_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    CHECK ((track = 'A' AND target_kind = 'MODULE' AND target_module IS NOT NULL)
        OR (track = 'B' AND target_kind = 'STANDALONE' AND target_module IS NULL)),
    CHECK (repo_visibility IS DISTINCT FROM 'PUBLIC' OR track = 'B')
);
CREATE UNIQUE INDEX ux_research_route_active ON console.research_route_decisions (research_id)
    WHERE status IN ('PENDING','RUNNING','SUCCEEDED');

CREATE TABLE console.research_route_steps (
    route_id UUID NOT NULL REFERENCES console.research_route_decisions(id),
    step_no INTEGER NOT NULL CHECK (step_no >= 1),
    step VARCHAR(24) NOT NULL CHECK (step IN (
        'VALIDATE_TARGET','GIT_SWITCH','SCAFFOLD_FILES','GIT_INIT','GIT_COMMIT','GH_REPO_CREATE','PUBLISH_DOCS',
        'COPY_WORKSPACE','REGISTER_STUB','IMPL_KEY_INIT','BASELINE_ADOPT')),               -- GIT_SWITCH＝git worktree add（獨立 worktree，D-20 SA-08）
    status VARCHAR(11) NOT NULL CHECK (status IN ('RUNNING','OK','FAILED','SKIPPED','COMPENSATED')),
    argv_redacted TEXT NOT NULL DEFAULT '',                -- 去敏後的 argv（不含 token）
    exit_code INTEGER,
    stdout_tail VARCHAR(2000) NOT NULL DEFAULT '',
    stderr_tail VARCHAR(2000) NOT NULL DEFAULT '',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (route_id, step_no)
);

CREATE TABLE console.research_scr (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    scr_no INTEGER NOT NULL CHECK (scr_no >= 1),
    kind VARCHAR(5) NOT NULL CHECK (kind IN ('MINOR','MAJOR')),
    source_kind VARCHAR(14) NOT NULL CHECK (source_kind IN ('HUMAN','REVIEW_FINDING','SCG4','HEALING_FAILED')),
    reason TEXT NOT NULL,
    reason_class VARCHAR(10) NOT NULL DEFAULT 'OTHER' CHECK (reason_class IN ('EVIDENCE','AC_VAGUE','REQ_CHANGE','INFEASIBLE','OTHER')),   -- PRD 缺漏證據／AC 模糊／需求變更／技術不可行／其他（M6 分群）
    affected_sections TEXT[] NOT NULL DEFAULT '{}',
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','APPROVED','REJECTED','APPLIED','SUPERSEDED')),
    prd_from_version_no INTEGER,
    prd_to_version_no INTEGER,
    successor_research_id UUID REFERENCES console.research_projects(id),   -- MAJOR：新研究專案
    impl_fsm_actions JSONB NOT NULL DEFAULT '[]'::jsonb,                   -- 實際呼叫過的 FSM 動詞序列（稽核）
    requested_by VARCHAR(100) NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    decided_by VARCHAR(100),
    decided_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (research_id, scr_no)
);

CREATE TABLE console.research_decompositions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    path CHAR(1) NOT NULL CHECK (path IN ('A','B','C')),                    -- 沿 import 解析路徑 A／B／C（ImportController.java:108-116）
    draft_id VARCHAR(64),                                                   -- /autoclaude/decompose 草稿 id（路徑 C）
    import_record_id UUID REFERENCES console.import_records(id),
    tcs_rel_path VARCHAR(500),
    tcs_sha256 CHAR(64) CHECK (tcs_sha256 IS NULL OR tcs_sha256 ~ '^[0-9a-f]{64}$'),
    prd_sha256 CHAR(64) CHECK (prd_sha256 IS NULL OR prd_sha256 ~ '^[0-9a-f]{64}$'),   -- 拆解綁凍結 PRD（stale 判定）
    tasks_count INTEGER NOT NULL DEFAULT 0 CHECK (tasks_count >= 0),
    gate_rejection VARCHAR(30),                                             -- max_steps／cycle／empty_prompt／brain_*（decompose.py:37-47）
    status VARCHAR(10) NOT NULL DEFAULT 'DRAFTED'
        CHECK (status IN ('DRAFTED','SCG_PASSED','FROZEN','IMPORTED','SIGNED_OFF','REJECTED','STALE')),
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 受控可更新表掛通用守衛（D-49；允許清單已在 V16 的函式內宣告）
CREATE TRIGGER trg_research_route_decisions_guard BEFORE UPDATE OR DELETE ON console.research_route_decisions
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_route_steps_guard BEFORE UPDATE OR DELETE ON console.research_route_steps
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_scr_guard BEFORE UPDATE OR DELETE ON console.research_scr
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_decompositions_guard BEFORE UPDATE OR DELETE ON console.research_decompositions
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();

CREATE TABLE console.research_deliveries (                 -- append-only（P2 寫入；表隨 V19 建立，Flyway 已發佈檔不改）
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    kind VARCHAR(12) NOT NULL CHECK (kind IN ('RELEASE_TAG','PULL_REQUEST','RELEASE_NOTE')),
    ref VARCHAR(200) NOT NULL,                             -- tag 名或 PR 編號
    commit_sha VARCHAR(40) CHECK (commit_sha IS NULL OR commit_sha ~ '^[0-9a-f]{40}$'),
    url VARCHAR(500),
    rtm_run_id UUID REFERENCES console.execution_runs(id),
    rtm_report_ref VARCHAR(300),
    fsm_state_after VARCHAR(40),
    status VARCHAR(7) NOT NULL CHECK (status IN ('CREATED','FAILED')),
    detail VARCHAR(2000) NOT NULL DEFAULT '',
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (research_id, kind, ref)
);
CREATE TRIGGER trg_research_deliveries_guard BEFORE UPDATE OR DELETE ON console.research_deliveries
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

-- 自癒嘗試＝既有 execution_steps（RETRYING／FAILED）；視圖不新增任何寫入路徑
CREATE VIEW console.v_research_healing_attempts AS
SELECT rp.id AS research_id, er.id AS run_id, er.run_number, es.task_id, es.step_number, es.action,
       es.status, es.error_message, es.tokens_used, es."timestamp" AS occurred_at
FROM console.research_projects rp
JOIN console.execution_runs er ON er.project_id = rp.console_project_id
JOIN console.execution_steps es ON es.run_id = er.id
WHERE es.status IN ('RETRYING', 'FAILED');
