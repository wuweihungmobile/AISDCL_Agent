package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.ReinitResult;
import com.aisdlc.console.domain.service.ResearchFlowPolicy;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * 重試初始化／換世代的結果（契約 API-RP-20）：{@code flow} 是成功後自 DB 重讀、由 {@code ResearchFlowPolicy} 計算的流程脊；換世代另帶新的外環鍵與世代號、決定列 id
 * （重試初始化沒有這三欄，省略）。
 */
@Schema(name = "ReinitResult", description = "重試初始化（只有 flow）或換世代（另有 fsmProject、fsmGeneration、gateDecisionId）的結果")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ReinitResultDto(
        @NotNull ResearchFlow flow,
        @Schema(description = "換世代後的外環鍵 research-<slug>-g<N>") String fsmProject,
        @Schema(description = "換世代後的世代號（原世代＋1）") Integer fsmGeneration,
        @Schema(description = "換世代決定列 id（gate=ABANDON_KEY、decision=ABANDONED）") String gateDecisionId) {

    public static ReinitResultDto from(ReinitResult result) {
        ResearchFlowPolicy.Flow flow = result.project().flow();
        return new ReinitResultDto(ResearchFlow.from(flow), result.fsmProject(), result.fsmGeneration(), result.gateDecisionId());
    }
}
