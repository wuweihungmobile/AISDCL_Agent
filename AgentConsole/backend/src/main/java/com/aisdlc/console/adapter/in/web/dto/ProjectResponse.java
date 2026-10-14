package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectView;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/** 建立／更新／signoff 後的專案回應（＝詳情去掉目標清單；Architecture §11.2 的 R 欄）。 */
public record ProjectResponse(
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
        String createdBy) {

    public static ProjectResponse from(ProjectView view) {
        Project p = view.project();
        return new ProjectResponse(p.id(), p.name(), p.executionPath(), p.passCriteria(), p.description(),
                p.status(), p.autonomyLevel(), p.signedOff(), p.signedOffBy(), p.signedOffAt(),
                view.counts().goalsCount(), view.counts().tasksCount(), view.counts().tasksDone(),
                p.createdAt(), p.updatedAt(), p.createdBy());
    }
}
