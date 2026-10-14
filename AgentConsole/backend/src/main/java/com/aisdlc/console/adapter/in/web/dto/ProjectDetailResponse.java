package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectDetailView;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** 專案詳情（Architecture §11.2 的 D 欄）：全部欄位＋目標摘要清單（依 sortOrder）。 */
public record ProjectDetailResponse(
        @NotNull UUID id,
        @NotNull String name,
        @NotNull String executionPath,
        @NotNull String passCriteria,
        String description,
        @NotNull ProjectStatus status,
        @NotNull int autonomyLevel,
        @NotNull boolean signedOff,
        String signedOffBy,
        Instant signedOffAt,
        @NotNull int goalsCount,
        @NotNull int tasksCount,
        @NotNull int tasksDone,
        @NotNull Instant createdAt,
        @NotNull Instant updatedAt,
        String createdBy,
        @NotNull List<GoalBrief> goals) {

    public static ProjectDetailResponse from(ProjectDetailView view) {
        Project p = view.project();
        return new ProjectDetailResponse(p.id(), p.name(), p.executionPath(), p.passCriteria(), p.description(),
                p.status(), p.autonomyLevel(), p.signedOff(), p.signedOffBy(), p.signedOffAt(),
                view.counts().goalsCount(), view.counts().tasksCount(), view.counts().tasksDone(),
                p.createdAt(), p.updatedAt(), p.createdBy(), view.goals().stream().map(GoalBrief::from).toList());
    }
}
