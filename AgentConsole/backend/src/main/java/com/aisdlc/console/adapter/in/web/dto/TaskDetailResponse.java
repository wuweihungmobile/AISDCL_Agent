package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** 任務詳情（Architecture §11.2 的 D 欄）：全部欄位＋最近一次執行日誌＋執行歷史（Phase 2 為空清單）。 */
public record TaskDetailResponse(
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
        String executionLog,
        @NotNull List<ExecutionStepBrief> executionHistory,
        @NotNull boolean signedOff,
        String signedOffBy,
        Instant signedOffAt,
        @NotNull Instant createdAt,
        @NotNull Instant updatedAt,
        Instant startedAt,
        Instant completedAt) {

    public static TaskDetailResponse from(Task t) {
        return new TaskDetailResponse(t.id(), t.goalId(), t.name(), t.description(), t.passCriteria(),
                t.evaluatorCommand(), t.expectedOutputRegex(), JsonSupport.toObject(t.passCriteriaSpec()),
                t.sortOrder(), t.status(), t.estimatedTokens(), t.actualTokens(), t.retryCount(), t.maxRetries(),
                t.assignedAgent(), t.executionLog(), List.of(), t.signedOff(), t.signedOffBy(), t.signedOffAt(),
                t.createdAt(), t.updatedAt(), t.startedAt(), t.completedAt());
    }
}
