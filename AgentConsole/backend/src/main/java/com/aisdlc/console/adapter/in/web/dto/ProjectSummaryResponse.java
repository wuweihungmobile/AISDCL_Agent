package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectView;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/** 專案列表的一列（Architecture §11.2 的 S 欄）：名稱、狀態、目標數、任務數、最後更新時間。 */
public record ProjectSummaryResponse(
        @NotNull UUID id,
        @NotNull String name,
        @NotNull String executionPath,
        @NotNull ProjectStatus status,
        @NotNull int autonomyLevel,
        @NotNull boolean signedOff,
        @NotNull int goalsCount,
        @NotNull int tasksCount,
        @NotNull int tasksDone,
        @NotNull Instant updatedAt) {

    public static ProjectSummaryResponse from(ProjectView view) {
        Project p = view.project();
        return new ProjectSummaryResponse(p.id(), p.name(), p.executionPath(), p.status(), p.autonomyLevel(),
                p.signedOff(), view.counts().goalsCount(), view.counts().tasksCount(), view.counts().tasksDone(),
                p.updatedAt());
    }
}
