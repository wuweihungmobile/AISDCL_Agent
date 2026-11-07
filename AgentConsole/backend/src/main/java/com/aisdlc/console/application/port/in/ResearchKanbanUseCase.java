package com.aisdlc.console.application.port.in;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 看板投影用例（API-RP-26；AC-R2P-15；D-138 Q-1）：console-api 聚合、<b>唯讀、零寫入、零 Bridge 寫入請求</b>。五欄的值與來源端點用同一份計算
 * （拆解＝{@code ResearchDecompositionUseCase#current}、自癒＝{@code ResearchHealingReadPort#facts}、回歸＝RTM 查詢與內環 FSM 現態），不另寫第二份。
 * Bridge 不可達時回 DB 快照：FSM 衍生欄 null 加 {@code unknown=true}、{@code stale=true}。
 */
public interface ResearchKanbanUseCase {

    @Schema(name = "KanbanDecompose", description = "Task 拆解欄：done＝已簽核且非 stale")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Decompose(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean done, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String status, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int tasksCount, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean stale) {
    }

    @Schema(name = "KanbanTcs", description = "測試規格產生欄：done＝Stage-2 已凍結；Bridge 不可達時 stage2Frozen／negotiated／fsmState 為 null 且 unknown 為 true")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Tcs(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean done, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) Boolean stage2Frozen, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) Boolean negotiated, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String fsmState, @Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, description = "只在為 true 時出現（Bridge 不可達、值未知）") @JsonInclude(JsonInclude.Include.NON_NULL) Boolean unknown) {
    }

    @Schema(name = "KanbanTaskCounts", description = "專案任務計數；retrying＝最新 run 內仍在重試的任務數")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Tasks(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) int total, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int running, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int completed, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int skipped, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int failed, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int escalated, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int retrying) {
    }

    @Schema(name = "KanbanImplement", description = "程式碼實作欄：done＝total 大於 0 且 completed 加 skipped 等於 total")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Implement(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean done, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String fsmState, @Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, description = "只在為 true 時出現（Bridge 不可達、值未知）") @JsonInclude(JsonInclude.Include.NON_NULL) Boolean unknown, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Tasks tasks) {
    }

    @Schema(name = "KanbanHealing", description = "自癒修復欄：done＝retryingSteps 與 escalatedTasks 皆為 0")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Healing(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean done, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int retryingSteps, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int escalatedTasks, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int maxRetries) {
    }

    @Schema(name = "KanbanRtm", description = "RTM 摘要（諮詢視圖；advisory 恆為 true）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Rtm(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) UUID runId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int atPassed, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int atTotal, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int acCovered, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int acTotal, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) double acPct, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean fullyCovered, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean advisory) {
    }

    @Schema(name = "KanbanRegression", description = "回歸驗收欄：done 僅在 acPct 為 100、fullyCovered 為真、現態屬 RELEASE_READY 或 RELEASE")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Regression(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean done, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String fsmState, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) Boolean releaseReady, @Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, description = "只在為 true 時出現（Bridge 不可達、值未知）") @JsonInclude(JsonInclude.Include.NON_NULL) Boolean unknown, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean rtmAvailable, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) Rtm rtm) {
    }

    @JsonInclude(JsonInclude.Include.ALWAYS) record Columns(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) Decompose decompose, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Tcs tcs, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Implement implement, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Healing healing, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Regression regression) {
    }

    @Schema(name = "KanbanPendingReview", description = "待審項目（review_requests 的 PENDING）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record PendingReview(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) UUID reviewId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) UUID runId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String kind, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) UUID taskId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String reason, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) OffsetDateTime createdAt, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<String> allowedDecisions) {
    }

    @Schema(name = "KanbanGate", description = "內環閘決定（SCG4、SCG5、SCG6 各最近 5 筆，decidedAt 新到舊）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Gate(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String gate, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String decision, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String decidedBy, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) OffsetDateTime decidedAt, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String fsmStateAfter, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String reason) {
    }

    @Schema(name = "KanbanDto", description = "看板投影（API-RP-26）；Bridge 不可達：bridgeReachable＝false、stale＝true、snapshotAt＝三個 DB 來源時間的最大值")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Kanban(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) UUID researchId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) UUID consoleProjectId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) UUID latestRunId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) OffsetDateTime generatedAt, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean bridgeReachable, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) OffsetDateTime snapshotAt, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean stale, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean scrOpen, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Columns columns, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<PendingReview> pendingReviews, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<Gate> gates) {
    }

    /** 研究專案不存在丟 404 {@code research_not_found}。 */
    Kanban kanban(UUID researchId);
}
