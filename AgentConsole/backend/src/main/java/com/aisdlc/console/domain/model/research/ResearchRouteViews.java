package com.aisdlc.console.domain.model.research;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 研究到規格 P1（分流、SCR、拆解）的讀模型：console-api 以 JDBC 唯讀 V19 的表（{@code research_route_decisions}、{@code research_route_steps}、
 * {@code research_scr}、{@code research_decompositions}；Bridge 是唯一寫入者，ADR-003 D4），這些不可變 record 是讀配接器的輸出與 web 層 DTO 的輸入。
 * 純 Java；欄位語意逐欄對映 Architecture K.4 的 DDL（V19），時間一律帶時區。
 */
public final class ResearchRouteViews {

    private ResearchRouteViews() {
    }

    /** 分流的一個步驟（{@code research_route_steps}；沒有 {@code id} 欄，以 (route_id, step_no) 定位）。 */
    public record RouteStep(int stepNo, String step, String status, String argvRedacted, Integer exitCode, String stdoutTail,
                            String stderrTail, OffsetDateTime startedAt, OffsetDateTime finishedAt) {
    }

    /** 一筆分流決定（{@code research_route_decisions}）加它的步驟（依 step_no 遞增）。 */
    public record Route(UUID id, UUID researchId, String track, String targetKind, String targetModule, String targetPath, String gitBranch,
                        String baseRef, String repoUrl, String repoVisibility, String stackTemplate, UUID consoleProjectId,
                        String implFsmProject, String implStateDir, Map<String, Object> publishedDocs, String scopeDiffersReason,
                        String status, String failureStep, String decidedBy, OffsetDateTime createdAt, OffsetDateTime finishedAt,
                        List<RouteStep> steps) {
    }

    /** 一筆規格變更請求（{@code research_scr}）。 */
    public record Scr(UUID id, int scrNo, String kind, String sourceKind, String reason, String reasonClass, List<String> affectedSections,
                      String status, Integer prdFromVersionNo, Integer prdToVersionNo, UUID successorResearchId, List<Object> implFsmActions,
                      String requestedBy, OffsetDateTime requestedAt, String decidedBy, OffsetDateTime decidedAt, String evidenceUrl) {
    }

    /** 既有匯入記錄的參照（簽核冪等，D-133）：id、狀態（UPLOADED｜PARSING｜PARSED｜REVIEWING｜IMPORTED｜REJECTED）與是否已 signoff。 */
    public record ImportRef(UUID id, String status, boolean signedOff) {
    }

    /**
     * 一筆拆解（{@code research_decompositions}）。{@code content}＝同一研究專案最新版 {@code research_artifacts(kind=TASK_DECOMPOSITION)} 的 JSON
     * 全文（goals／tasks／waivers／覆蓋對映；沒有則 null）。
     */
    public record Decomposition(UUID id, String path, String draftId, UUID importRecordId, String tcsRelPath, String tcsSha256,
                                String prdSha256, int tasksCount, String gateRejection, String status, String createdBy,
                                OffsetDateTime createdAt, Map<String, Object> content) {
    }
}
