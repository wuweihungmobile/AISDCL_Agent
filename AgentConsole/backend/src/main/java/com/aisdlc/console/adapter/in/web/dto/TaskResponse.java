package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/** 建立／更新／retry／signoff 後的任務回應（Architecture §11.2 的 R 欄＝詳情去掉執行日誌與歷史）。 */
public record TaskResponse(
        @NotNull UUID id,
        @NotNull UUID goalId,
        @NotNull String name,
        String description,
        @NotNull String passCriteria,
        String evaluatorCommand,
        String expectedOutputRegex,
        Map<String, Object> passCriteriaSpec,
        @NotNull int sortOrder,
        @NotNull TaskStatus status,
        Long estimatedTokens,
        Long actualTokens,
        @NotNull int retryCount,
        @NotNull int maxRetries,
        String assignedAgent,
        @NotNull boolean signedOff,
        String signedOffBy,
        Instant signedOffAt,
        @NotNull Instant createdAt,
        @NotNull Instant updatedAt,
        Instant startedAt,
        Instant completedAt) {

    public static TaskResponse from(Task t) {
        return new TaskResponse(t.id(), t.goalId(), t.name(), t.description(), t.passCriteria(),
                t.evaluatorCommand(), t.expectedOutputRegex(), JsonSupport.toObject(t.passCriteriaSpec()),
                t.sortOrder(), t.status(), t.estimatedTokens(), t.actualTokens(), t.retryCount(), t.maxRetries(),
                t.assignedAgent(), t.signedOff(), t.signedOffBy(), t.signedOffAt(), t.createdAt(), t.updatedAt(),
                t.startedAt(), t.completedAt());
    }
}
