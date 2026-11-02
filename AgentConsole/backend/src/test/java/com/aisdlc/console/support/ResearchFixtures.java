package com.aisdlc.console.support;

import org.springframework.jdbc.core.JdbcTemplate;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.UUID;

/**
 * 研究表的資料庫夾具（ResearchToPRD P0；ADR-003 D4：console-api 對 {@code console.research_*} 唯讀，這些列在正式環境只有 Bridge 能寫）。測試把自己當成 Bridge，
 * 直接以 JDBC 寫入各表；每個方法只填 DDL 的必填欄位與測試要的欄位，其餘取預設。表間外鍵由呼叫端依序建立（專案→stage run→PRD 版本→審查輪→分數／缺陷）。
 * 清表不用在這裡做：{@code AbstractApiIT} 每個測試前的 {@code TRUNCATE console.projects CASCADE} 會沿外鍵一路清到 {@code research_*}
 * （{@code research_projects.console_project_id} 參照 {@code projects}）。
 */
public final class ResearchFixtures {

    private final JdbcTemplate jdbc;

    public ResearchFixtures(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ── 專案與事件帳 ─────────────────────────────────────────────────────────────────────

    /** 剛建立的專案：topic／INGESTED／IDLE。 */
    public UUID project(String slug) {
        return project(slug, "topic", "INGESTED", "IDLE", "");
    }

    public UUID project(String slug, String flowStep, String flowPhase, String flowStatus, String flowDetail) {
        UUID id = UUID.randomUUID();
        jdbc.update("insert into console.research_projects (id, slug, title, topic, scope, workspace_path, fsm_project, fsm_state_dir, "
                + "flow_step, flow_phase, flow_status, flow_detail, created_by) values (?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, ?, ?, ?, ?)",
                id, slug, "研究 " + slug, "研究議題 " + slug, "{\"layers\":{\"academic\":true,\"industry\":false,\"oss\":true,\"community\":false}}",
                "/research-root/" + slug, "research-" + slug, "/research-root/" + slug + "/build/reports/fsm", flowStep, flowPhase, flowStatus,
                flowDetail, "operator");
        return id;
    }

    /** 專案換世代後的外環鍵與世代號（只給 FSM 視圖的夾具用；DDL 的受控更新守衛放行這兩欄）。 */
    public void generation(UUID id, int generation, String fsmProject) {
        jdbc.update("update console.research_projects set fsm_generation = ?, fsm_project = ? where id = ?", generation, fsmProject, id);
    }

    public void archive(UUID id) {
        jdbc.update("update console.research_projects set archived_at = now() where id = ?", id);
    }

    /** 事件帳的一列（{@code seq} 由呼叫端給；允許不連續——缺口的夾具）；同時推進專案的 {@code last_event_seq}。 */
    public void event(UUID id, long seq, String eventType, String payloadJson) {
        jdbc.update("insert into console.research_events (research_id, seq, event_type, step, actor, payload) values (?, ?, ?, 'topic', 'bridge', ?::jsonb)",
                id, seq, eventType, payloadJson);
        jdbc.update("update console.research_projects set last_event_seq = greatest(last_event_seq, ?) where id = ?", seq, id);
    }

    /** {@code fromSeq..toSeq}（含）連續的一批事件（一次 SQL；大量事件的夾具），同時推進專案的 {@code last_event_seq}。 */
    public void events(UUID id, long fromSeq, long toSeq) {
        jdbc.update("insert into console.research_events (research_id, seq, event_type, step, actor, payload) "
                + "select ?, g, 'research.step', 'topic', 'bridge', '{}'::jsonb from generate_series(?::bigint, ?::bigint) as g", id, fromSeq, toSeq);
        jdbc.update("update console.research_projects set last_event_seq = greatest(last_event_seq, ?) where id = ?", toSeq, id);
    }

    public long eventCount(UUID id) {
        Long count = jdbc.queryForObject("select count(*) from console.research_events where research_id = ?", Long.class, id);
        return count == null ? 0 : count;
    }

    public String cursor(UUID id) {
        return jdbc.queryForObject("select flow_step || '/' || flow_phase || '/' || flow_status || '/' || flow_detail from console.research_projects where id = ?",
                String.class, id);
    }

    // ── stage run ────────────────────────────────────────────────────────────────────────

    public UUID stageRun(UUID researchId, String stage, int roundNo, int attempt, String status, String exitReason) {
        UUID id = UUID.randomUUID();
        jdbc.update("insert into console.research_stage_runs (id, research_id, stage, round_no, attempt, status, exit_reason, requested_by, "
                + "started_at, finished_at) values (?, ?, ?, ?, ?, ?, ?, 'operator', now() - interval '2 minutes', now() - interval '1 minute')",
                id, researchId, stage, roundNo, attempt, status, exitReason);
        return id;
    }

    // ── PRD 版本與審查輪 ─────────────────────────────────────────────────────────────────

    public void prdVersion(UUID researchId, int versionNo, String semver, String content) {
        jdbc.update("insert into console.research_prd_versions (research_id, version_no, semver, kind, author_kind, author, parent_version_no, content, "
                + "rel_path, sha256, bytes, change_summary) values (?, ?, ?, 'DRAFT', 'AGENT', 'pm-po', ?, ?, ?, ?, ?, ?)",
                researchId, versionNo, semver, versionNo > 1 ? versionNo - 1 : null, content, "01_specs/PRD-" + semver + ".md", sha256(content),
                content.getBytes(StandardCharsets.UTF_8).length, "第 " + versionNo + " 版");
    }

    /**
     * 一個已完成評估的審查輪（連同它的 REVIEW stage run）。{@code gateResult}／{@code retryCount} 依 DDL：兩者同為 NULL（POST_HUMAN 通過輪）或同非 NULL。
     * 加權分與最低維度分由呼叫端給（前置否決不過時傳 null、{@code precheckPassed=false}）。
     */
    public UUID round(UUID researchId, int roundNo, int generation, int prdVersionNo, String triggerKind, boolean precheckPassed, BigDecimal weighted,
                      Integer minDimension, int openP1, boolean passed, String verdict, String gateResult, Integer retryCount) {
        UUID stageRun = stageRun(researchId, "REVIEW", roundNo, 1, "SUCCEEDED", "");
        UUID id = UUID.randomUUID();
        String precheck = "{\"checks\":[{\"id\":\"SLV-001\",\"passed\":" + precheckPassed + ",\"detail\":\"ok\"},{\"id\":\"SLV-002\",\"passed\":true,\"detail\":\"ok\"},"
                + "{\"id\":\"SLV-003\",\"passed\":true,\"detail\":\"ok\"},{\"id\":\"AMBIGUITY\",\"passed\":true,\"detail\":\"ok\"}]}";
        jdbc.update("insert into console.research_review_rounds (id, research_id, round_no, fsm_generation, prd_version_no, trigger_kind, precheck_passed, "
                + "precheck_detail, weighted_score, min_dimension_score, open_p1_count, passed, verdict, fsm_gate_result, fsm_retry_count, escalated, "
                + "stage_run_id, started_at, finished_at) values (?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, ?, ?, ?, ?, ?, now() - interval '2 minutes', "
                + "now() - interval '1 minute')",
                id, researchId, roundNo, generation, prdVersionNo, triggerKind, precheckPassed, precheck, weighted, minDimension, openP1, passed, verdict,
                gateResult, retryCount, "ESCALATE".equals(verdict), stageRun);
        return id;
    }

    /** 四維分數（ARCHITECTURE、PRODUCT、QA、SECURITY；SECURITY 帶輔助審查者）。 */
    public void scores(UUID roundId, int score) {
        String[][] rows = {{"ARCHITECTURE", "0.300", "sd-architect"}, {"PRODUCT", "0.250", "pm-po"}, {"QA", "0.250", "qa-tester"},
                {"SECURITY", "0.200", "security-engineer"}};
        for (String[] row : rows) {
            boolean security = "SECURITY".equals(row[0]);
            jdbc.update("insert into console.research_review_scores (round_id, dimension, weight, score, agent_id, assist_agent_id, assist_agent_yaml_sha256, "
                    + "agent_yaml_path, agent_yaml_sha256, persona_sha256, summary, raw_rel_path, raw_sha256) values (?, ?, ?::numeric, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    roundId, row[0], row[1], score, row[2], security ? "compliance-officer" : null, security ? sha256("assist") : null,
                    "agent/core/" + row[2] + ".yaml", sha256(row[2]), sha256("persona-" + row[2]), "摘要 " + row[0], "01_specs/review/" + row[0] + ".json", sha256("raw"));
        }
    }

    /** 缺陷一列；{@code WAIVED} 依 DDL 的 CHECK 必帶 waived_by／waiver_reason，離開 OPEN 的終態必有 resolved_at。 */
    public void defect(UUID roundId, String defectNo, String dimension, String severity, String status) {
        boolean waived = "WAIVED".equals(status);
        jdbc.update("insert into console.research_review_defects (round_id, defect_no, dimension, severity, code, prd_anchor, description, suggestion, status, "
                + "waived_by, waiver_reason, resolved_at) values (?, ?, ?, ?, 'ARCH-001', '§3.2', '缺口說明', '建議補強', ?, ?, ?, ?)", roundId, defectNo, dimension,
                severity, status, waived ? "admin" : null, waived ? "風險可接受" : null,
                "OPEN".equals(status) ? null : java.sql.Timestamp.from(java.time.Instant.now()));
    }

    // ── 人工決定 ─────────────────────────────────────────────────────────────────────────

    /** 人工決定一列；{@code GATE0}＋{@code APPROVED} 須帶非空 {@code frozenDigests} 與 {@code fsmStage}（DDL 的 CHECK）。 */
    public void decision(UUID researchId, String gate, String decision, String fsmProject, String fsmStage, String frozenDigestsJson) {
        jdbc.update("insert into console.research_gate_decisions (research_id, gate, decision, decided_by, decided_at, fsm_project, fsm_stage, frozen_digests, reason) "
                + "values (?, ?, ?, 'admin', now(), ?, ?, ?::jsonb, '夾具')", researchId, gate, decision, fsmProject, fsmStage, frozenDigestsJson);
    }

    // ── 來源、抓取與證據 ─────────────────────────────────────────────────────────────────

    public UUID source(UUID researchId, String sourceNo, String url, String tier) {
        UUID id = UUID.randomUUID();
        jdbc.update("insert into console.research_sources (id, research_id, source_no, layer, tier, verification, anchor_kind, url, title, authors_org, "
                + "published_at, source_type, license_spdx, license_note, clue_only, first_fetched_at) values (?, ?, ?, 'ACADEMIC', ?, 'V2', 'URL', ?, ?, 'Example Lab', "
                + "date '2025-03-01', 'PAPER', null, '未見', ?, now())", id, researchId, sourceNo, tier, url, "來源 " + sourceNo, "T3".equals(tier));
        return id;
    }

    public void fetch(UUID researchId, UUID sourceId, String fetchNo, String outcome) {
        jdbc.update("insert into console.research_fetches (research_id, source_id, layer, fetch_no, fetch_method, observed_by, host, url, http_status, outcome, "
                + "raw_sha256, raw_bytes) values (?, ?, 'ACADEMIC', ?, 'WEB_FETCH', 'BRIDGE', 'example.org', 'https://example.org/p', 200, ?, ?, 1024)",
                researchId, sourceId, fetchNo, outcome, sha256("raw-" + fetchNo));
    }

    public void artifact(UUID researchId, String kind, int version, String content) {
        jdbc.update("insert into console.research_artifacts (research_id, kind, version, rel_path, sha256, bytes, origin, content, created_by) "
                + "values (?, ?, ?, ?, ?, ?, 'AGENT', ?, 'research-analyst')", researchId, kind, version, "00_research/" + kind.toLowerCase() + ".json",
                sha256(content == null ? kind : content), content == null ? 0 : content.getBytes(StandardCharsets.UTF_8).length, content);
    }

    public void evidenceItem(UUID researchId, UUID sourceId, int matrixVersion, String evidenceNo, String candidate) {
        jdbc.update("insert into console.research_evidence_items (research_id, matrix_version, evidence_no, source_id, candidate, claim, f1_mechanism, f2_evidence, "
                + "f3_critique, f5_applicability, f6_limits, f7_verification, strength) values (?, ?, ?, ?, ?, '論點', '機制', '證據', '批評', "
                + "'{\"technical\":{\"grade\":\"A\",\"reason\":\"可行\"}}'::jsonb, '限制', 'V2', 'MEDIUM')", researchId, matrixVersion, evidenceNo, sourceId, candidate);
    }

    /** 一個內容固定的 sha256（小寫十六進位）。 */
    public static String sha256(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
