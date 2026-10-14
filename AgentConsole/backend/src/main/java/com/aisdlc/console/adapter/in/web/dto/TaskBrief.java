package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

/** 目標詳情內的任務標題清單（US-G-03）。 */
public record TaskBrief(
        @NotNull UUID id,
        @NotNull String name,
        @NotNull TaskStatus status,
        @NotNull int sortOrder,
        @NotNull int retryCount,
        @NotNull int maxRetries,
        @NotNull boolean signedOff) {

    public static TaskBrief from(Task t) {
        return new TaskBrief(t.id(), t.name(), t.status(), t.sortOrder(), t.retryCount(), t.maxRetries(),
                t.signedOff());
    }
}
