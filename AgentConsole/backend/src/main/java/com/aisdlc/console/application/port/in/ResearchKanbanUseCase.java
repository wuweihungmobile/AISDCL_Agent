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
    @JsonInclude(JsonInclude.Include.ALWAYS) record Decompose(boolean done, String status, int tasksCount, boolean stale) {
    }

    @Schema(name = "KanbanTcs", description = "測試規格產生欄：done＝Stage-2 已凍結；Bridge 不可達時 stage2Frozen／negotiated／fsmState 為 null 且 unknown 為 true")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Tcs(boolean done, Boolean stage2Frozen, Boolean negotiated, String fsmState, @JsonInclude(JsonInclude.Include.NON_NULL) Boolean unknown) {
    }

    @Schema(name = "KanbanTaskCounts", description = "專案任務計數；retrying＝最新 run 內仍在重試的任務數")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Tasks(int total, int running, int completed, int skipped, int failed, int escalated, int retrying) {
    }

    @Schema(name = "KanbanImplement", description = "程式碼實作欄：done＝total 大於 0 且 completed 加 skipped 等於 total")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Implement(boolean done, String fsmState, @JsonInclude(JsonInclude.Include.NON_NULL) Boolean unknown, Tasks tasks) {
    }

    @Schema(name = "KanbanHealing", description = "自癒修復欄：done＝retryingSteps 與 escalatedTasks 皆為 0")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Healing(boolean done, int retryingSteps, int escalatedTasks, int maxRetries) {
    }

    @Schema(name = "KanbanRtm", description = "RTM 摘要（諮詢視圖；advisory 恆為 true）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Rtm(UUID runId, int atPassed, int atTotal, int acCovered, int acTotal, double acPct, boolean fullyCovered, boolean advisory) {
    }

    @Schema(name = "KanbanRegression", description = "回歸驗收欄：done 僅在 acPct 為 100、fullyCovered 為真、現態屬 RELEASE_READY 或 RELEASE")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Regression(boolean done, String fsmState, Boolean releaseReady, @JsonInclude(JsonInclude.Include.NON_NULL) Boolean unknown,
                      boolean rtmAvailable, Rtm rtm) {
    }

    @JsonInclude(JsonInclude.Include.ALWAYS) record Columns(Decompose decompose, Tcs tcs, Implement implement, Healing healing, Regression regression) {
    }

    @Schema(name = "KanbanPendingReview", description = "待審項目（review_requests 的 PENDING）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record PendingReview(UUID reviewId, UUID runId, String kind, UUID taskId, String reason, OffsetDateTime createdAt, List<String> allowedDecisions) {
    }

    @Schema(name = "KanbanGate", description = "內環閘決定（SCG4、SCG5、SCG6 各最近 5 筆，decidedAt 新到舊）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Gate(String gate, String decision, String decidedBy, OffsetDateTime decidedAt, String fsmStateAfter, String reason) {
    }

    @Schema(name = "KanbanDto", description = "看板投影（API-RP-26）；Bridge 不可達：bridgeReachable＝false、stale＝true、snapshotAt＝三個 DB 來源時間的最大值")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Kanban(UUID researchId, UUID consoleProjectId, UUID latestRunId, OffsetDateTime generatedAt, boolean bridgeReachable, OffsetDateTime snapshotAt,
                  boolean stale, boolean scrOpen, Columns columns, List<PendingReview> pendingReviews, List<Gate> gates) {
    }

    /** 研究專案不存在丟 404 {@code research_not_found}。 */
    Kanban kanban(UUID researchId);
}
