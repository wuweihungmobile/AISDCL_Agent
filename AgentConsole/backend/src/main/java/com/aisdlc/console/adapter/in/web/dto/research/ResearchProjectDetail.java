package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchQueryUseCase.ProjectDetail;
import com.aisdlc.console.domain.model.research.ResearchViews.Counts;
import com.aisdlc.console.domain.model.research.ResearchViews.LastReview;
import com.aisdlc.console.domain.model.research.ResearchViews.Project;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;
import java.util.Map;

/**
 * 研究專案詳情（契約 §1.3 {@code ResearchProjectDetail}＝摘要全部欄位加下列各欄）：五個計數、PRD head 版號、最新已完成的審查輪、流程脊。
 * {@code flow} 由 {@code ResearchFlowPolicy.effective} 計算（API-RP-04；純函式、相態不落 DB）。
 */
@Schema(name = "ResearchProjectDetail", description = "研究專案詳情（摘要全部欄位加 topic、scope、計數、PRD head、最新審查輪、流程脊）")
public record ResearchProjectDetail(
        @NotNull String id,
        @NotNull String rpNo,
        @NotNull String slug,
        @NotNull String title,
        @NotNull String depthLevel,
        @NotNull String targetScope,
        @NotNull String flowStep,
        @NotNull String flowPhase,
        @NotNull String flowStatus,
        @NotNull String flowDetail,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String consoleProjectId,
        @NotNull String createdBy,
        @NotNull String createdAt,
        @NotNull String updatedAt,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String archivedAt,
        @NotNull String topic,
        @NotNull @Schema(description = "issue_scope.json 的鏡像（層開關 layers、技術棧 techStack、檢索邊界 inScope／outOfScope、文獻年限 recencyYears、"
                + "適用性軸 applicabilityAxes、落點提示 targetScopeHint）；鍵一律 camelCase（Bridge 寫入的 snake_case 鍵在邊界轉換，D-76(2)）；值原樣") Map<String, Object> scope,
        @NotNull int scopeRev,
        @NotNull @Schema(description = "外環 FSM 鍵 research-<slug>[-g<N>]") String fsmProject,
        @NotNull int fsmGeneration,
        @NotNull ResearchFlow flow,
        @NotNull CountsDto counts,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "PRD head 版號；尚無版本為 null") Integer headPrdVersion,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "最新一個已完成的審查輪（D-57）；尚無為 null")
        LastReviewDto lastReview,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "大型 SCR 的前身研究專案（P0 恆為 null）")
        String parentResearchId) {

    /** 詳情頁的五個計數。 */
    @Schema(name = "ResearchCounts")
    public record CountsDto(@NotNull int sources, @NotNull int evidenceItems, @NotNull int prdVersions, @NotNull int reviewRounds,
                            @NotNull int openDefects) {

        static CountsDto from(Counts counts) {
            return new CountsDto(counts.sources(), counts.evidenceItems(), counts.prdVersions(), counts.reviewRounds(), counts.openDefects());
        }
    }

    /** 最新已完成審查輪的摘要；{@code weightedScore}、{@code minDimensionScore} 於前置否決不過（未計分）時為 null。 */
    @Schema(name = "ResearchLastReview")
    public record LastReviewDto(
            @NotNull int round,
            @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "W100/100，兩位小數（NUMERIC(5,2) 原樣）") BigDecimal weightedScore,
            @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Integer minDimensionScore,
            @NotNull boolean passed,
            @NotNull boolean escalated) {

        static LastReviewDto from(LastReview review) {
            return review == null ? null : new LastReviewDto(review.round(), review.weightedScore(), review.minDimensionScore(), review.passed(),
                    review.escalated());
        }
    }

    public static ResearchProjectDetail from(ProjectDetail detail) {
        Project p = detail.project();
        return new ResearchProjectDetail(p.id().toString(), p.rpNo(), p.slug(), p.title(), p.depthLevel(), p.targetScope(), p.flowStep(),
                p.flowPhase(), p.flowStatus(), p.flowDetail(), p.consoleProjectId() == null ? null : p.consoleProjectId().toString(),
                p.createdBy(), Iso.of(p.createdAt()), Iso.of(p.updatedAt()), Iso.of(p.archivedAt()), p.topic(), Iso.camelKeys(p.scope()), p.scopeRev(),
                p.fsmProject(), p.fsmGeneration(), ResearchFlow.from(detail.flow()), CountsDto.from(detail.counts()), detail.headPrdVersion(),
                LastReviewDto.from(detail.lastReview()), p.parentResearchId() == null ? null : p.parentResearchId().toString());
    }
}
