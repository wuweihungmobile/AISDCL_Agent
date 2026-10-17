package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectDetailView;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 專案詳情（Architecture §11.2 的 D 欄）：全部欄位＋目標摘要清單（依 sortOrder）。
 *
 * <p>v1.5（G-07、D-115-14；契約 §1.10.5）：另帶 SDD 綁定三欄（皆可 null；null 與缺席等價）。
 */
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
        @Schema(description = "v1.5：FSM 專案鍵（≤ 100 字元）；null＝「用預設」（專案名）", nullable = true, maxLength = 100)
        String sddProject,
        @Schema(description = "v1.5：規格檔所在目錄（絕對路徑）；尚未用路徑 A 匯入為 null", nullable = true, maxLength = 500)
        String sddSpecDir,
        @Schema(description = "v1.5：規格檔（絕對路徑）；尚未用路徑 A 匯入為 null", nullable = true, maxLength = 500)
        String sddSpecFile,
        @NotNull List<GoalBrief> goals) {

    public static ProjectDetailResponse from(ProjectDetailView view) {
        Project p = view.project();
        return new ProjectDetailResponse(p.id(), p.name(), p.executionPath(), p.passCriteria(), p.description(),
                p.status(), p.autonomyLevel(), p.signedOff(), p.signedOffBy(), p.signedOffAt(),
                view.counts().goalsCount(), view.counts().tasksCount(), view.counts().tasksDone(),
                p.createdAt(), p.updatedAt(), p.createdBy(), p.sddProject(), p.sddSpecDir(), p.sddSpecFile(),
                view.goals().stream().map(GoalBrief::from).toList());
    }
}
