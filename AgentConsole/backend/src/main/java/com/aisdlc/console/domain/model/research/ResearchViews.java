package com.aisdlc.console.domain.model.research;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 研究到規格（ResearchToPRD P0）的讀模型：console-api 以 JDBC 唯讀 {@code console.research_*}（Bridge 是唯一寫入者；ADR-003 D4），這些不可變 record
 * 是讀配接器的輸出與 web 層 DTO 的輸入。純 Java（不依賴任何框架）；欄位語意逐欄對映 Architecture §11.3′ 的 DDL（V16～V18），時間一律帶時區。
 * 各 DTO 的 camelCase 形狀見 API 契約 §1.3；這裡不重複描述。
 */
public final class ResearchViews {

    private ResearchViews() {
    }

    /**
     * {@code research_projects} 一列（游標欄位 {@code flow_*} 由 Bridge 在引擎動作的同一交易寫入；console-api 只讀）。{@code workspacePath} 只給
     * FSM 視圖定址（{@code GET /sdd/fsm/{fsmProject}?root=<workspacePath>}）用，不出現在任何回應 DTO。
     */
    public record Project(UUID id, String rpNo, String slug, String title, String topic, Map<String, Object> scope, int scopeRev,
                          String depthLevel, String targetScope, String fsmProject, int fsmGeneration, String flowStep,
                          String flowPhase, String flowStatus, String flowDetail, UUID consoleProjectId, UUID parentResearchId,
                          long lastEventSeq, String createdBy, OffsetDateTime createdAt, OffsetDateTime updatedAt,
                          OffsetDateTime archivedAt, String workspacePath) {
    }

    /** 詳情頁的五個計數（{@code evidenceItems} 取最新矩陣版本的列數；{@code openDefects} 取全部輪中 status 為 OPEN 的缺陷數）。 */
    public record Counts(int sources, int evidenceItems, int prdVersions, int reviewRounds, int openDefects) {
    }

    /** 最新一個已完成的審查輪（輪列只在輪有結果時一次寫入，D-57）。 */
    public record LastReview(int round, BigDecimal weightedScore, Integer minDimensionScore, boolean passed, boolean escalated) {
    }

    /** {@code research_events} 一列（append-only；{@code seq} 每專案單調＝SSE 的 {@code id}）。 */
    public record Event(long seq, String eventType, String step, String actor, String refKind, UUID refId,
                        Map<String, Object> payload, OffsetDateTime occurredAt) {
    }

    /** {@code GET …/events} 的一頁：{@code nextSeq}＝最後一筆的 seq（沒有任何事件時為請求的 afterSeq），{@code truncated}＝後面還有。 */
    public record EventPage(List<Event> items, long nextSeq, boolean truncated) {
    }

    /** 一次抓取（{@code research_fetches}；含失敗與被拒）。 */
    public record Fetch(String fetchNo, String method, String observedBy, String host, Integer httpStatus, String outcome,
                        String rawSha256, Long rawBytes, OffsetDateTime fetchedAt) {
    }

    /** 來源（{@code research_sources}）加它的全部抓取紀錄（依抓取時間遞增）。 */
    public record Source(String sourceNo, String layer, String tier, String verification, String anchorKind, String url, String doi,
                         String gitCommit, String title, String authorsOrg, LocalDate publishedAt, String sourceType,
                         String licenseSpdx, String licenseNote, boolean clueOnly, List<Fetch> fetches) {
    }

    /** 證據列（{@code research_evidence_items}；七欄 F1～F7 與執行層計算的 {@code unanchored}）。 */
    public record EvidenceItem(String evidenceNo, String sourceNo, String candidate, String claim, String f1Mechanism, String f2Evidence,
                               String f3Critique, List<String> f4RiskTags, Map<String, Object> f5Applicability, String f6Limits,
                               String f7Verification, String strength, boolean unanchored, int matrixVersion, int scopeRev) {
    }

    /**
     * 一個證據矩陣版本：{@code sha256} 取該版本 {@code EVIDENCE_MATRIX} 產物（沒有則 {@code EVIDENCE_ITEMS} 產物）的雜湊；{@code itemsJson} 是
     * {@code EVIDENCE_ITEMS} 產物的 {@code content} 全文（含 counter_evidence、honest_bounds、search_log；D-43，P0 不另立表），可為 null。
     */
    public record Matrix(int matrixVersion, int scopeRev, String sha256, List<EvidenceItem> items, String itemsJson) {
    }

    /** PRD 版本（{@code research_prd_versions}；{@code content} 只有單筆端點填，清單為 null）。 */
    public record PrdVersion(int versionNo, String semver, String kind, String authorKind, String author, Integer parentVersionNo,
                             String sha256, int bytes, List<String> evidenceRefs, String changeSummary, OffsetDateTime createdAt,
                             String content) {
    }

    /** 審查輪的一個維度分數（{@code research_review_scores}）。 */
    public record Score(String dimension, BigDecimal weight, int score, String agentId, String assistAgentId, String assistAgentYamlSha256,
                        String agentYamlSha256, String personaSha256, String summary) {
    }

    /** 審查缺陷（{@code research_review_defects}）；{@code resolvedIn}＝{@code fixed_in_version_no} 所指版本的 semver。 */
    public record Defect(String defectNo, String dimension, String severity, String code, String prdAnchor, String description,
                         String suggestion, List<String> evidenceRefs, String status, Integer fixedInVersionNo, String resolvedIn,
                         String waivedBy, String waiverReason, OffsetDateTime resolvedAt) {
    }

    /** 前置否決的一項檢查（{@code precheck_detail.checks[]}）。 */
    public record PrecheckCheck(String id, boolean passed, String detail) {
    }

    /** 審查輪（{@code research_review_rounds}；沒有 status 欄——列存在即輪已完成評估）加它的分數與缺陷。 */
    public record Round(int roundNo, int fsmGeneration, int prdVersionNo, String prdVersion, String triggerKind, boolean precheckPassed,
                        List<PrecheckCheck> precheckChecks, BigDecimal weightedScore, BigDecimal threshold, int floorScore,
                        Integer minDimensionScore, int openP1Count, boolean passed, String verdict, String fsmGateResult,
                        Integer fsmRetryCount, boolean escalated, List<Score> scores, List<Defect> defects, OffsetDateTime startedAt,
                        OffsetDateTime finishedAt) {
    }

    /** 內環 run 的衍生輸入（{@code ResearchFlowPolicy} 用；只有分流後綁定了 Console 專案才有）。 */
    public record RunFact(String status, boolean retryingStep, boolean pendingReview) {
    }

    /** {@code GET …/records/audit} 的一類記錄的筆數（R1～R14；PRD §5.1.8）。 */
    public record RecordClass(String id, String name, int count) {
    }
}
