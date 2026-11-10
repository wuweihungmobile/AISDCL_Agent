-- V24__research_watch_sources.sql — 研究來源單一化（Console 半；PRD FR-R2P-24、契約 API_Contract_ResearchToPRD §5A.1、TCS-ResearchRegistry W-R1）
-- WHY：自我進化（SI）的追蹤來源原本只住 git 檔 research_sources.json，與 Console「研究來源設定」兩處維護、會漂移。
-- 結構層正解＝追蹤來源住本表（console.research_watch_sources），SI 讀由 Console 簽章同步而來的鏡像檔。
-- 追蹤來源與 research_allowlist_entries 一樣是全域資源：沒有 research_id、不寫 research_events；只增不刪（slug 永不重用）。
-- 受控更新：以 CREATE OR REPLACE 擴充既有通用守衛 console.research_controlled_update_guard()（V16 定義）的允許清單，
-- 只增一條 WHEN 'research_watch_sources'；其餘九條既有 WHEN 與函式其餘文字逐字不動（Flyway 已發佈的 V16 原文不改）。

CREATE TABLE console.research_watch_sources (
    slug VARCHAR(32) PRIMARY KEY CHECK (slug ~ '^[a-z0-9][a-z0-9-]{0,31}$'),
    url VARCHAR(500) NOT NULL
        CHECK (url ~ '^https://[a-z0-9]([a-z0-9.-]*[a-z0-9])?([/?][^[:space:]#]*)?$'),     -- https；host 小寫 ASCII、無 userinfo／埠（含顯式 :443）／尾點／方括號 IPv6；無空白與片段
    CONSTRAINT research_watch_sources_url_no_idna CHECK (url !~ '^https://([^/?]*\.)?xn--'),            -- 拒 IDNA／xn-- 任一 label（D-EQA-1）
    CONSTRAINT research_watch_sources_url_no_localhost CHECK (url !~ '^https://([^/?]*\.)?localhost([/?]|$)'),  -- 拒 localhost 與 *.localhost
    CONSTRAINT research_watch_sources_url_no_ipv4 CHECK (url !~ '^https://[0-9.]+([/?]|$)'),          -- 拒 IPv4 字面（任何 IP 字面皆拒；IPv6 已被 host 字元集擋下）
    kind VARCHAR(9) NOT NULL CHECK (kind IN ('changelog','docs','release','blog','sitemap','search')),
    extract VARCHAR(200) NOT NULL CHECK (char_length(extract) >= 1 AND extract !~ '[[:cntrl:]]'),
    layer VARCHAR(9) NOT NULL CHECK (layer IN ('ACADEMIC','INDUSTRY','OSS','COMMUNITY')),
    expand_mode VARCHAR(7) CHECK (expand_mode IN ('links','sitemap')),
    expand_prefix VARCHAR(200) CHECK (expand_prefix ~ '^/[^[:space:]?#[:cntrl:]]*$'),
    expand_max SMALLINT CHECK (expand_max BETWEEN 1 AND 3),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    added_by VARCHAR(100) NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    disabled_by VARCHAR(100),
    disabled_at TIMESTAMP WITH TIME ZONE,
    CHECK ((expand_mode IS NULL) = (expand_prefix IS NULL) AND (expand_mode IS NULL) = (expand_max IS NULL)),
    CHECK (enabled OR (disabled_by IS NOT NULL AND disabled_at IS NOT NULL))
);

-- 通用守衛重定義：本體逐字複製 V16 的 console.research_controlled_update_guard()，只在允許清單加最後一條 WHEN。
CREATE OR REPLACE FUNCTION console.research_controlled_update_guard() RETURNS trigger
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
        WHEN 'research_watch_sources' THEN ARRAY['enabled','disabled_by','disabled_at']
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

CREATE TRIGGER trg_research_watch_sources_guard BEFORE UPDATE OR DELETE ON console.research_watch_sources
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();

-- 追蹤來源種子（17 列：SI 舊表 15 列＋anthropic-research＋arxiv-agents；啟用 10、停用 7）。時間取固定常數 2026-11-10T00:00:00+00:00。
-- 重跑冪等：ON CONFLICT DO NOTHING（不覆寫被人手動停用的列）。停用列（含 retired 與 anthropic-engineering）之網域不種入 allowlist。
INSERT INTO console.research_watch_sources
    (slug, url, kind, extract, layer, expand_mode, expand_prefix, expand_max, enabled, added_by, added_at, disabled_by, disabled_at)
VALUES
    ('anthropic-engineering', 'https://www.anthropic.com/engineering', 'blog', '最新 5 篇文章的標題與日期（逐字）', 'INDUSTRY', NULL, NULL, NULL, FALSE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', 'migration:V24（以 anthropic-research 取代）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('anthropic-research', 'https://www.anthropic.com/sitemap.xml', 'sitemap', '最新 3 篇研究文章的全文（逐字）', 'INDUSTRY', 'sitemap', '/research/', 3, TRUE,
     'migration:V24（研究來源單一化種子）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL),
    ('anthropic-sdk-python-releases', 'https://github.com/anthropics/anthropic-sdk-python/releases.atom', 'release', '最新 5 個 release 的編號與日期，以及其中提到的新模型 ID 或 API 參數名（逐字）', 'OSS', NULL, NULL, NULL, TRUE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL),
    ('arxiv-agents', 'https://export.arxiv.org/api/query?search_query=%28abs:%22self-improving%22+OR+abs:%22self-evolving%22+OR+abs:%22agent+memory%22%29+AND+%28cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.SE%29&sortBy=submittedDate&sortOrder=descending&max_results=10', 'search', '最新 10 篇論文的標題、作者、日期與摘要首句（逐字）', 'ACADEMIC', NULL, NULL, NULL, TRUE,
     'migration:V24（研究來源單一化種子）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL),
    ('cc-changelog', 'https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md', 'changelog', '最新 5 個版本的編號與各版首行（逐字，不改寫）', 'OSS', NULL, NULL, NULL, FALSE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', 'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('cc-docs-hooks', 'https://code.claude.com/docs/en/hooks-guide', 'docs', '標題清單＋事件名清單（逐字）', 'INDUSTRY', NULL, NULL, NULL, FALSE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', 'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('cc-docs-hooks-md', 'https://code.claude.com/docs/en/hooks-guide.md', 'docs', '標題清單＋事件名清單（逐字）', 'INDUSTRY', NULL, NULL, NULL, TRUE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL),
    ('cc-docs-index', 'https://code.claude.com/docs/llms.txt', 'docs', '與上次相比新增或改名的頁面標題清單（逐字）', 'INDUSTRY', NULL, NULL, NULL, TRUE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL),
    ('cc-docs-memory', 'https://code.claude.com/docs/en/memory', 'docs', '頁面標題清單＋含數字上限的句子（逐字）', 'INDUSTRY', NULL, NULL, NULL, FALSE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', 'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('cc-docs-memory-md', 'https://code.claude.com/docs/en/memory.md', 'docs', '頁面標題清單＋含數字上限的句子（逐字）', 'INDUSTRY', NULL, NULL, NULL, TRUE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL),
    ('cc-docs-skills', 'https://code.claude.com/docs/en/skills', 'docs', '標題清單＋frontmatter 欄位名清單（逐字）', 'INDUSTRY', NULL, NULL, NULL, FALSE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', 'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('cc-docs-skills-md', 'https://code.claude.com/docs/en/skills.md', 'docs', '標題清單＋frontmatter 欄位名清單（逐字）', 'INDUSTRY', NULL, NULL, NULL, TRUE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL),
    ('cc-releases', 'https://github.com/anthropics/claude-code/releases.atom', 'release', '最新 5 個 release 的編號、日期與各版首行（逐字，不改寫）', 'OSS', NULL, NULL, NULL, TRUE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL),
    ('openai-agents-releases', 'https://github.com/openai/openai-agents-python/releases.atom', 'release', '最新 5 個 release 的編號與日期（逐字）', 'OSS', NULL, NULL, NULL, FALSE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', 'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('openai-agents-tags', 'https://github.com/openai/openai-agents-python/tags.atom', 'release', '最新 5 個 release 的編號與日期（逐字）', 'OSS', NULL, NULL, NULL, TRUE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL),
    ('openai-api-changelog', 'https://platform.openai.com/docs/changelog', 'changelog', '最新 5 筆變更的日期與標題（逐字）', 'INDUSTRY', NULL, NULL, NULL, FALSE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', 'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('openai-api-changelog-md', 'https://developers.openai.com/api/docs/changelog.md', 'changelog', '最新 5 筆變更的日期與標題（逐字）', 'INDUSTRY', NULL, NULL, NULL, TRUE,
     'migration:V24（SI research_sources.json 匯入）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00', NULL, NULL)
ON CONFLICT (slug) DO NOTHING;

-- 網域種子：恰四個 FETCH 網域（WEB 零新增；export.arxiv.org 已在部署基底，不另種；停用列的網域 raw.githubusercontent.com、platform.openai.com 不種）。
INSERT INTO console.research_allowlist_entries
    (list_kind, host, layer, min_interval_seconds, enabled, tos_acknowledged, added_by, added_at)
VALUES
    ('FETCH', 'www.anthropic.com', 'INDUSTRY', 5, TRUE, FALSE, 'migration:V24（自我進化研究來源種子）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('FETCH', 'github.com', 'OSS', 5, TRUE, FALSE, 'migration:V24（自我進化研究來源種子）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('FETCH', 'code.claude.com', 'INDUSTRY', 5, TRUE, FALSE, 'migration:V24（自我進化研究來源種子）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00'),
    ('FETCH', 'developers.openai.com', 'INDUSTRY', 5, TRUE, FALSE, 'migration:V24（自我進化研究來源種子）', TIMESTAMPTZ '2026-11-10T00:00:00+00:00')
ON CONFLICT (list_kind, host) DO NOTHING;
