package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchRouteViews.Route;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;
import java.util.Map;

/** 一筆分流決定與它的步驟（契約 §1.3 {@code RouteDecision}；加 {@code publishedDocs}，D-106）。{@code GET …/route} 尚無分流回 200 的 {@code null}。 */
@Schema(name = "RouteDecisionDto", description = "分流決定：軌道、目標、分支或遠端、Console 專案、內環鍵、狀態、失敗步驟、已發佈文件與步驟列")
public record RouteDecisionDto(
        @NotNull String routeId,
        @NotNull @Schema(allowableValues = {"A", "B"}) String track,
        @NotNull @Schema(allowableValues = {"MODULE", "STANDALONE"}) String targetKind,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String targetModule,
        @NotNull String targetPath,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String gitBranch,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String baseRef,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String repoUrl,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String repoVisibility,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String stackTemplate,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String consoleProjectId,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String implFsmProject,
        @NotNull @Schema(description = "PENDING｜RUNNING｜SUCCEEDED｜FAILED｜COMPENSATED") String status,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String failureStep,
        @NotNull @Schema(description = "目標 docs/ 相對路徑 → sha256（分流成功後才有）") Map<String, Object> publishedDocs,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String scopeDiffersReason,
        @NotNull String decidedBy,
        @NotNull String createdAt,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String finishedAt,
        @NotNull List<RouteStepDto> steps) {

    public static RouteDecisionDto from(Route r) {
        return new RouteDecisionDto(r.id().toString(), r.track(), r.targetKind(), r.targetModule(), r.targetPath(), r.gitBranch(), r.baseRef(), r.repoUrl(),
                r.repoVisibility(), r.stackTemplate(), r.consoleProjectId() == null ? null : r.consoleProjectId().toString(), r.implFsmProject(), r.status(),
                r.failureStep(), r.publishedDocs(), r.scopeDiffersReason(), r.decidedBy(), Iso.of(r.createdAt()), Iso.of(r.finishedAt()),
                r.steps().stream().map(RouteStepDto::from).toList());
    }
}
