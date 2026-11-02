package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.service.ResearchFlowPolicy;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/**
 * 流程脊（契約 §1.3 {@code Flow}）：固定五步（topic→studio→route→build→deliver）、目前步、最遠步，加 {@code effective}（步驟 3 之後由 {@code ResearchFlowPolicy}
 * 衍生，步驟 1～3 原樣取 DB 游標；不落 DB）與續接連結。
 */
@Schema(name = "ResearchFlow", description = "研究工作流的流程脊（固定 5 步；effective 由 ResearchFlowPolicy 計算、不落 DB）")
public record ResearchFlow(
        @NotNull @Schema(description = "目前步（topic｜studio｜route｜build｜deliver）") String currentStep,
        @NotNull @Schema(description = "最遠步＝DB 游標與衍生位置中較後者（供判斷 ?step= 是否可達）") String furthestStep,
        @NotNull @Schema(description = "固定 5 項，順序＝topic→deliver") List<Step> steps,
        @NotNull Effective effective,
        @NotNull @Schema(description = "例 /research/<id>?step=studio") String resumeHref) {

    /** 五步列的一項；{@code phase}、{@code blockedReason} 只有目前步才有（其餘省略）。 */
    @Schema(name = "ResearchFlowStep")
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Step(
            @NotNull String id,
            @NotNull String label,
            @NotNull @Schema(description = "DONE｜CURRENT｜BLOCKED｜TODO") String state,
            String phase,
            String blockedReason) {
    }

    /** 衍生後的目前位置。 */
    @Schema(name = "ResearchFlowEffective")
    public record Effective(
            @NotNull String step,
            @NotNull String phase,
            @NotNull @Schema(description = "DB 游標的八值加衍生的 PAUSED") String status,
            @NotNull String detail) {
    }

    public static ResearchFlow from(ResearchFlowPolicy.Flow flow) {
        List<Step> steps = flow.steps().stream()
                .map(step -> new Step(step.id(), step.label(), step.state(), step.phase(), step.blockedReason())).toList();
        ResearchFlowPolicy.Effective effective = flow.effective();
        return new ResearchFlow(flow.currentStep(), flow.furthestStep(), steps,
                new Effective(effective.step(), effective.phase(), effective.status(), effective.detail()), flow.resumeHref());
    }
}
