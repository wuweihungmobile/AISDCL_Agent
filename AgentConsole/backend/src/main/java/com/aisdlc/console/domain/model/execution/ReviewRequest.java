package com.aisdlc.console.domain.model.execution;

import java.time.Instant;
import java.util.UUID;

/**
 * 待審核／已處理的審核項（{@code review_requests} 的一列；契約 §3.6）。
 *
 * @param stepRowId 佐證步驟列 {@code execution_steps.id}（UUID；不是 playbook 的 step_id，契約 §0.6）
 * @param eventSeq  重播錨點：建立當下已處理到的最後一則 Bridge 事件 seq（契約 §2.2）
 * @param eventSub  同錨點下的子序號（≥1）
 */
public record ReviewRequest(UUID id, UUID runId, UUID stepRowId, UUID taskId, UUID goalId, ReviewKind kind,
                            ReviewStatus status, String reason, Instant requestedAt, String decidedBy,
                            Instant decidedAt, String comment, int eventSeq, int eventSub) {

    public boolean pending() {
        return status == ReviewStatus.PENDING;
    }

    /** 寫入決定（人工決定或系統自動關閉）後的新狀態；原記錄不變。 */
    public ReviewRequest decided(ReviewStatus newStatus, String by, Instant at, String note) {
        return new ReviewRequest(id, runId, stepRowId, taskId, goalId, kind, newStatus, reason, requestedAt, by, at,
                note, eventSeq, eventSub);
    }

    /** 系統自動關閉的決定人（新批次取代、cancel、restore、終態）。 */
    public static final String SYSTEM = "system";
}
