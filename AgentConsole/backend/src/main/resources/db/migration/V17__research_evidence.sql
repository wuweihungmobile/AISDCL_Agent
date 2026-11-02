-- V17__research_evidence.sql — 來源實體、每次抓取、證據抽取、ADMIN 管理的 allowlist（根層研究 SOP S2／S3 的資料化）
CREATE TABLE console.research_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    source_no VARCHAR(8) NOT NULL CHECK (source_no ~ '^S-[0-9]{3,4}$'),
    layer VARCHAR(9) NOT NULL CHECK (layer IN ('ACADEMIC','INDUSTRY','OSS','COMMUNITY')),
    tier VARCHAR(2) NOT NULL CHECK (tier IN ('T1','T2','T3')),                     -- SOP S2:58
    verification VARCHAR(2) NOT NULL CHECK (verification IN ('V1','V2','V3')),     -- SOP S2:69（V0 不得列入）
    anchor_kind VARCHAR(6) NOT NULL CHECK (anchor_kind IN ('URL','DOI','COMMIT')),
    url TEXT NOT NULL,
    doi VARCHAR(200),
    git_commit VARCHAR(64),
    title TEXT NOT NULL,
    authors_org TEXT NOT NULL DEFAULT '',
    published_at DATE,
    source_type VARCHAR(10) NOT NULL DEFAULT 'OTHER'
        CHECK (source_type IN ('PAPER','PREPRINT','ENG_BLOG','WHITEPAPER','PATENT','REPO','ISSUE_PR','FORUM','DOC','OTHER')),
    license_spdx VARCHAR(100),
    license_note TEXT NOT NULL DEFAULT '',
    clue_only BOOLEAN NOT NULL DEFAULT FALSE,                -- T3 強制 true 由下方 CHECK 鎖；T1／T2 的 clue_only 由 Bridge 寫入器依證據分層規則設定，不下沉為 CHECK（D-61：應用層保證、AT 守）
    first_fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,    -- 首次出現時間：Bridge 抓取＝抓取時間；宣告型來源＝其網址首次出現於 search_log 的時間
    UNIQUE (research_id, source_no),
    UNIQUE (research_id, url),
    CHECK (tier <> 'T3' OR clue_only),                                              -- SOP S2:58：T3 只當線索、不入正式證據
    CHECK (anchor_kind <> 'DOI' OR doi IS NOT NULL),
    CHECK (anchor_kind <> 'COMMIT' OR (git_commit IS NOT NULL AND git_commit ~ '^[0-9a-f]{40}$')),               -- 證據矩陣模板 §2.3 規則 3；NULL 不得靜默通過（D-59(1)）：CHECK 對 NULL 視為通過，COMMIT 錨點缺 git_commit 時 ~ 運算為 NULL，所以先判 IS NOT NULL
    CHECK (url ~ '^https://')                                                       -- 同上：來源網址必須 https
);
-- 受控可更新＋單向（D-49）：通用守衛只放行 verification 並擋任何 DELETE；專用守衛再鎖「只升不降」
CREATE FUNCTION console.research_source_verification_guard() RETURNS trigger LANGUAGE plpgsql AS
$$
BEGIN
    IF substr(NEW.verification, 2)::int < substr(OLD.verification, 2)::int THEN        -- V1 < V2 < V3
        RAISE EXCEPTION 'research_sources.verification 只升不降（% → %）', OLD.verification, NEW.verification
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_research_sources_guard BEFORE UPDATE OR DELETE ON console.research_sources
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_sources_verification BEFORE UPDATE OF verification ON console.research_sources
    FOR EACH ROW EXECUTE FUNCTION console.research_source_verification_guard();

CREATE TABLE console.research_fetches (                    -- 每次抓取（含被拒）；append-only
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    source_id UUID REFERENCES console.research_sources(id),
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    layer VARCHAR(9) NOT NULL CHECK (layer IN ('ACADEMIC','INDUSTRY','OSS','COMMUNITY')),
    fetch_no VARCHAR(10) NOT NULL CHECK (fetch_no ~ '^F-[0-9]{4,}$'),    -- 每研究專案單調：Bridge 於同交易 max+1 配號（同專案同時只有一個 RUNNING stage run，UNIQUE 兜底）；來源的 fetch_refs 指向它
    fetch_method VARCHAR(10) NOT NULL CHECK (fetch_method IN ('API','WEB_FETCH','WEB_SEARCH','MANUAL')),
    observed_by VARCHAR(14) NOT NULL CHECK (observed_by IN ('BRIDGE','AGENT_DECLARED')),   -- WEB_* 由 agent 宣告，Bridge 觀測不到單筆
    search_no INTEGER CHECK (search_no IS NULL OR search_no >= 1),                         -- 只有 agent 宣告的 search_log 列有：Q-NNN 的數字部分（search_log[].id；D-43、D-53）
    result_urls JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(result_urls) = 'array'),   -- search_log[].result_urls（https 字串陣列；D-53）
    host VARCHAR(255),                                                                     -- WEB_SEARCH 列為空（搜尋沒有單一網址）；解析不出 host 的被拒外呼寫保留字 '(unparsed)'（非空、不是合法主機名，D-61 的非空 CHECK 放行；D-66）
    url TEXT,
    query_text TEXT,
    http_status INTEGER,
    outcome VARCHAR(18) NOT NULL CHECK (outcome IN (
        'OK','DENIED_ALLOWLIST','DENIED_PRIVATE_IP','HTTP_ERROR','TIMEOUT','TOO_LARGE','PARSE_ERROR','RATE_LIMITED')),
    raw_rel_path VARCHAR(500),
    raw_sha256 CHAR(64) CHECK (raw_sha256 IS NULL OR raw_sha256 ~ '^[0-9a-f]{64}$'),
    raw_bytes BIGINT CHECK (raw_bytes IS NULL OR raw_bytes >= 0),
    duration_ms INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (research_id, fetch_no),
    -- NULL 不得靜默通過（D-59(1)）：非 WEB_SEARCH 列 url、host 皆必填；WEB_SEARCH 列兩欄皆空（搜尋沒有單一網址）；兩條都只用 IS NULL／IS NOT NULL 判，不產生 NULL 結果
    CHECK (fetch_method = 'WEB_SEARCH' OR (url IS NOT NULL AND host IS NOT NULL)),
    CHECK (fetch_method <> 'WEB_SEARCH' OR (url IS NULL AND host IS NULL)),
    CHECK (host IS NULL OR host <> ''),                                              -- D-61：非 NULL 的 host 不得為空字串（DENIED 列也一樣，否則空 host 的被拒紀錄無從稽核）
    CHECK (observed_by = 'AGENT_DECLARED' OR search_no IS NULL)
);
CREATE UNIQUE INDEX ux_research_fetches_search_no ON console.research_fetches (research_id, search_no) WHERE search_no IS NOT NULL;
CREATE INDEX idx_research_fetches_research ON console.research_fetches (research_id, fetched_at);
CREATE TRIGGER trg_research_fetches_guard BEFORE UPDATE OR DELETE ON console.research_fetches
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_evidence_items (             -- SOP S3 七欄；缺欄寫「未見」（NOT NULL＋gate 驗非空）；以 matrix_version 新增、不改
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    matrix_version INTEGER NOT NULL CHECK (matrix_version >= 1),    -- ＝ research_artifacts(kind='EVIDENCE_ITEMS').version
    scope_rev INTEGER NOT NULL DEFAULT 1 CHECK (scope_rev >= 1),
    evidence_no VARCHAR(8) NOT NULL CHECK (evidence_no ~ '^E-[0-9]{3,4}$'),
    source_id UUID NOT NULL REFERENCES console.research_sources(id),
    candidate VARCHAR(200),                                         -- 候選技術名（供優缺點矩陣分組；可空；D-43）
    claim TEXT NOT NULL,                                            -- PRD 引用的論點
    f1_mechanism TEXT NOT NULL,
    f2_evidence TEXT NOT NULL,
    f3_critique TEXT NOT NULL,
    f4_risk_tags TEXT[] NOT NULL DEFAULT '{}',
    f5_applicability JSONB NOT NULL,                                -- 六格 A／M／N＋理由（技術可行｜授權相容｜維護風險｜效能邊界｜資安｜成本）
    f6_limits TEXT NOT NULL,
    f7_verification VARCHAR(2) NOT NULL CHECK (f7_verification IN ('V1','V2','V3')),
    strength VARCHAR(9) NOT NULL DEFAULT 'WEAK' CHECK (strength IN ('STRONG','MEDIUM','WEAK','CANDIDATE')),   -- 必須等於證據矩陣模板 §3.3 函式值（Bridge 驗）
    unanchored BOOLEAN NOT NULL DEFAULT FALSE,                      -- F2 數字在抓取原文比對不到：Bridge 入庫時計算，研究者不寫；TRUE 的列 PRD 不得引用
    UNIQUE (research_id, matrix_version, evidence_no)
);
CREATE INDEX idx_research_evidence_source ON console.research_evidence_items (source_id);
CREATE TRIGGER trg_research_evidence_items_guard BEFORE UPDATE OR DELETE ON console.research_evidence_items
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_allowlist_entries (          -- D-17：產業網域由 ADMIN 逐一加入；Reddit 預設不在任何清單
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    list_kind VARCHAR(5) NOT NULL CHECK (list_kind IN ('FETCH','WEB')),
    host VARCHAR(255) NOT NULL CHECK (host ~ '^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$'),
    layer VARCHAR(9) NOT NULL CHECK (layer IN ('ACADEMIC','INDUSTRY','OSS','COMMUNITY')),
    purpose VARCHAR(200) NOT NULL DEFAULT '',
    tos_note TEXT NOT NULL DEFAULT '',
    min_interval_seconds INTEGER NOT NULL DEFAULT 3 CHECK (min_interval_seconds BETWEEN 1 AND 3600),   -- 實際間隔＝max(Bridge 內建下限, 本值)（PRD NFR-R2P-03-6）；建立後不可改（受控更新守衛只放行 enabled／disabled_*），要調整＝停用後重建
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    tos_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    added_by VARCHAR(100) NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    disabled_by VARCHAR(100),
    disabled_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (list_kind, host),
    CHECK (host !~ '(^|\.)(reddit\.com|redd\.it)$' OR tos_acknowledged),            -- Reddit 須先確認條款
    CHECK (enabled OR (disabled_by IS NOT NULL AND disabled_at IS NOT NULL))
);
-- 受控可更新（D-49）：由通用守衛 research_controlled_update_guard() 只放行 enabled／disabled_by／disabled_at，並擋任何 DELETE
CREATE TRIGGER trg_research_allowlist_guard BEFORE UPDATE OR DELETE ON console.research_allowlist_entries
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
