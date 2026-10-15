package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.TaskStepView;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/**
 * 任務詳情的「執行歷史」單筆（US-T-02；由 {@code execution_steps} 依 {@code task_id} 衍生，跨批次、依時間升冪、最多 200 筆）。
 * {@code stepNumber} 是該 step 事件的 Bridge seq（每個批次各自起算）；{@code tokensUsed} 只有 COMPLETED／FAILED 的列才有。
 */
public record ExecutionStepBrief(
        @NotNull UUID id,
        @NotNull int stepNumber,
        @NotNull String action,
        @NotNull String status,
        Long tokensUsed,
        String errorMessage,
        Instant timestamp) {

    public static ExecutionStepBrief from(TaskStepView v) {
        return new ExecutionStepBrief(v.id(), v.stepNumber(), v.action(), v.status(), v.tokensUsed(),
                v.errorMessage(), v.timestamp());
    }
}
