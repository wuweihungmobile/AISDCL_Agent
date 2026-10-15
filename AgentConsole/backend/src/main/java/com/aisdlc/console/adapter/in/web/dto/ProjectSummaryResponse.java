package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectView;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/**
 * 專案列表的一列（Architecture §11.2 的 S 欄）：名稱、狀態、目標數、任務數、最後更新時間。{@code deletedAt}（v1.2，C-3）只有
 * {@code GET /projects?deleted=true} 的列表帶值，其餘缺席。
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
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
        @NotNull Instant updatedAt,
        @Schema(description = "軟刪除當下的時間；只有 GET /projects?deleted=true 的列表帶值（v1.2，C-3）") Instant deletedAt) {

    public static ProjectSummaryResponse from(ProjectView view) {
        Project p = view.project();
        return new ProjectSummaryResponse(p.id(), p.name(), p.executionPath(), p.status(), p.autonomyLevel(),
                p.signedOff(), view.counts().goalsCount(), view.counts().tasksCount(), view.counts().tasksDone(),
                p.updatedAt(), p.deletedAt());
    }
}
