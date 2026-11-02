package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.Project;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/** 研究專案清單的一列（契約 §1.3 {@code ResearchProjectSummary}；清單端點回陣列）。時間一律 ISO-8601 帶 offset。 */
@Schema(name = "ResearchProjectSummary", description = "研究專案摘要（清單的一列）")
public record ResearchProjectSummary(
        @NotNull String id,
        @NotNull @Schema(description = "顯示編號 RP-NNNN（DB 序列配號）") String rpNo,
        @NotNull String slug,
        @NotNull String title,
        @NotNull @Schema(description = "QUICK｜STANDARD｜DEEP") String depthLevel,
        @NotNull @Schema(description = "AISDLC_MODULE｜STANDALONE_PROJECT｜UNDECIDED") String targetScope,
        @NotNull String flowStep,
        @NotNull String flowPhase,
        @NotNull String flowStatus,
        @NotNull @Schema(description = "失敗時 init_failed:<步驟>；其餘為自由說明（可為空字串）") String flowDetail,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "分流後綁定的 Console 專案（P0 恆為 null）")
        String consoleProjectId,
        @NotNull String createdBy,
        @NotNull String createdAt,
        @NotNull String updatedAt,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "封存時間；未封存為 null") String archivedAt) {

    public static ResearchProjectSummary from(Project project) {
        return new ResearchProjectSummary(project.id().toString(), project.rpNo(), project.slug(), project.title(), project.depthLevel(),
                project.targetScope(), project.flowStep(), project.flowPhase(), project.flowStatus(), project.flowDetail(),
                project.consoleProjectId() == null ? null : project.consoleProjectId().toString(), project.createdBy(),
                Iso.of(project.createdAt()), Iso.of(project.updatedAt()), Iso.of(project.archivedAt()));
    }
}
