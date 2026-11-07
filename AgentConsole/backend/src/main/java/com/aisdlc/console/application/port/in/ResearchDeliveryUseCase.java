package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 交付用例（API-RP-17／28；AC-R2P-17～21；D-138 Q-4／Q-5／Q-8／Q-10、D-142 ⚖P2-9／12／13）：交付概覽與追溯表（讀）、Release Tag 與 Pull Request（寫，僅 ADMIN）。
 * 服務層前置不成立＝409 且<b>零 Bridge 請求</b>；通過後 Bridge 恰一次、不重試；Bridge 的 409 {@code tag_exists}／502 {@code delivery_step_failed}／
 * 422 {@code digest_mismatch}／422 {@code route_unsupported_in_deployment} 原樣透傳。{@code github_token} 只放進 {@code :pr} 的 Bridge 本文。
 */
public interface ResearchDeliveryUseCase {

    @Schema(name = "DeliveryDto", description = "一筆交付（research_deliveries；snapshotSha256＝追溯快照 JSON 的雜湊，TAG 列必填、PR 列為 null）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Delivery(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String kind, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String ref, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String commitSha, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String url, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String rtmReportRef, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String fsmStateAfter, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String status, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String createdBy, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) OffsetDateTime createdAt, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String snapshotSha256) {
    }

    @Schema(name = "DeliverySnapshot", description = "追溯快照檔（03_execution/traceability_matrix.json）的相對路徑與 sha256")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Snapshot(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String relPath, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String sha256) {
    }

    @Schema(name = "DeliveryPreconditions", description = "交付前置：hasOrigin、ghAvailable 未知時為 null")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Preconditions(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean releaseReady, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean rtmFull, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean scrOpen, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) Boolean hasOrigin, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) Boolean ghAvailable) {
    }

    @Schema(name = "DeliveryOverviewDto", description = "交付概覽（API-RP-17）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Overview(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<Delivery> deliveries, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) Snapshot snapshot, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String projectRoot, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean containerMode, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Preconditions preconditions) {
    }

    @Schema(name = "TraceabilityGherkin", description = "Given／When／Then 各段摘要（純文字、每段至多 120 字）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Gherkin(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String given, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String when, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String then) {
    }

    @Schema(name = "TraceabilityRow", description = "追溯表一列（一個 AC）：source 為字串陣列（task:<id>、RTM-COVERAGE-<key>.yaml）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record TraceRow(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String ac, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String userStory, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Gherkin gherkinSummary, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String unitStatus, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String e2eStatus, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String lastRunAt, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<String> source) {
    }

    @Schema(name = "TraceabilityTotals", description = "totals：frTotal＝凍結 PRD 的 FR 條數（與標題模板同一函式同源，D-151）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record TraceTotals(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) int acTotal, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int covered, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int uncovered, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int frTotal) {
    }

    @Schema(name = "TraceabilityRtm", description = "RTM 摘要（諮詢視圖；advisory 恆為 true）；沒有 run 或報告不可得時整個物件為 null")
    @JsonInclude(JsonInclude.Include.ALWAYS) record TraceRtm(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String runId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean fullyCovered, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) Double acPct, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean advisory) {
    }

    @Schema(name = "TraceabilityDto", description = "追溯表預演（API-RP-17；Bridge :traceability-preview 原樣形狀，鍵轉 camelCase）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Traceability(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<TraceRow> rows, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) TraceTotals totals, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) TraceRtm rtm, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String generatedAt) {
    }

    /** {@code POST …/delivery/tag} 請求（{@code createGithubRelease} 為 true＝422，P2 不建立 GitHub Release）。 */
    @Schema(name = "TagRequest", description = "建立 Release Tag：tagName 為 semver（至多 64 字）、message 至多 200 字、push 預設 false、createGithubRelease 為 true＝422")
    record TagInput(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String tagName, @Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, nullable = true) String message, @Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, nullable = true) Boolean push, @Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, nullable = true) Boolean createGithubRelease) {
    }

    /** {@code POST …/delivery/pr} 請求（{@code bodyPreviewAck} 缺或為 false＝422）。 */
    @Schema(name = "PrRequest", description = "建立 Pull Request：bodyPreviewAck 須為 true（已預覽內文）；title 只作預覽，須等於模板輸出")
    record PrInput(@Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, nullable = true) String branch, @Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, nullable = true) String title, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Boolean bodyPreviewAck) {
    }

    @Schema(name = "TagResult", description = "Release Tag 建立結果")
    @JsonInclude(JsonInclude.Include.ALWAYS) record TagResult(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) Delivery delivery, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) Snapshot snapshot, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) ResearchGateUseCase.FlowCursor flow, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String fsmState) {
    }

    @Schema(name = "PrResult", description = "Pull Request 建立結果；created 為 false＝同一分支的 PR 已存在（冪等）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record PrResult(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) Delivery delivery, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean created) {
    }

    Overview overview(UUID researchId);

    /** 追溯表預演（Bridge {@code :traceability-preview}，零副作用）：Bridge 本文承接成型別。 */
    Traceability traceability(UUID researchId);

    /** 建立 Release Tag：回 Bridge 本文（{@code delivery}、{@code snapshot}、{@code flow}、{@code fsmState}）。 */
    TagResult tag(Caller caller, UUID researchId, TagInput input);

    /** 建立 Pull Request：回 Bridge 本文（{@code delivery}、{@code created}）。 */
    PrResult pr(Caller caller, UUID researchId, PrInput input);
}
