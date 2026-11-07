package com.aisdlc.console.domain.model.research;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * 研究到規格 P2（看板、自癒、交付）的讀模型：console-api 以 JDBC 唯讀（{@code v_research_healing_attempts}、{@code review_requests}、
 * {@code research_gate_decisions}、{@code research_deliveries}、{@code tasks}；Bridge 是 {@code research_*} 的唯一寫入者，ADR-003 D4）。純 Java。
 */
public final class ResearchP2Views {

    private ResearchP2Views() {
    }

    /** 自癒視圖的一列：{@code excerpt} 已先遮蔽再截尾 300 字元；{@code attempt} 為 (run, task) 內依 step_number 的序號。 */
    public record HealingAttempt(UUID runId, UUID taskId, int stepNumber, int attempt, String status, String excerpt, OffsetDateTime occurredAt,
                                 boolean resolved, boolean escalated) {
    }

    /** 專案任務計數（看板的程式碼實作欄；{@code retrying}＝最新 run 內仍在重試的任務數）。 */
    public record TaskCounts(int total, int running, int completed, int skipped, int failed, int escalated, int retrying) {

        /** 完成判定：total 大於 0 且 completed 加 skipped 等於 total。 */
        public boolean done() {
            return total > 0 && completed + skipped == total;
        }
    }

    /** 待審項目（{@code review_requests.status='PENDING'}）。 */
    public record PendingReview(UUID reviewId, UUID runId, String kind, UUID taskId, String reason, OffsetDateTime createdAt) {
    }

    /** 內環閘決定（SCG4／SCG5／SCG6）。 */
    public record GateRow(String gate, String decision, String decidedBy, OffsetDateTime decidedAt, String fsmStateAfter, String reason) {
    }

    /** 交付列（{@code research_deliveries}；契約 DeliveryDto 無 id 欄）。 */
    public record DeliveryRow(String kind, String ref, String commitSha, String url, String rtmReportRef, String fsmStateAfter, String status,
                              String createdBy, OffsetDateTime createdAt, String snapshotSha256) {
    }

    /** 看板／自癒共用的 DB 事實。 */
    public record HealingFacts(int retryingSteps, int escalatedTasks) {
    }
}
