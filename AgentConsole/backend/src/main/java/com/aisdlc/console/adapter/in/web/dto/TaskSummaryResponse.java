package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/** 任務列表的一列（Architecture §11.2 的 S 欄）。 */
public record TaskSummaryResponse(
        @NotNull UUID id,
        @NotNull UUID goalId,
        @NotNull String name,
        @NotNull int sortOrder,
        @NotNull TaskStatus status,
        Long estimatedTokens,
        Long actualTokens,
        @NotNull int retryCount,
        @NotNull int maxRetries,
        @NotNull boolean signedOff,
        @NotNull Instant updatedAt) {

    public static TaskSummaryResponse from(Task t) {
        return new TaskSummaryResponse(t.id(), t.goalId(), t.name(), t.sortOrder(), t.status(),
                t.estimatedTokens(), t.actualTokens(), t.retryCount(), t.maxRetries(), t.signedOff(),
                t.updatedAt());
    }
}
