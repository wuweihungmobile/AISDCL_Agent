package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.Score;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

/** 審查輪的一個維度分數（契約 §1.3 {@code ReviewScoreDto}）：PRODUCT 維度的 agentId 是 {@code pm-po}（D-44）；只有 SECURITY 有輔助審查者。 */
@Schema(name = "ReviewScoreDto", description = "四維審查的一個維度分數（整數 0～100）")
public record ReviewScoreDto(
        @NotNull @Schema(description = "ARCHITECTURE｜PRODUCT｜QA｜SECURITY") String dimension,
        @NotNull @Schema(description = "權重（0.300／0.250／0.250／0.200）") BigDecimal weight,
        @NotNull @Schema(description = "整數 0～100（五項 rubric 各 0～20 之和）") int score,
        @NotNull String agentId,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "只有 SECURITY：compliance-officer") String assistAgentId,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String assistAgentYamlSha256,
        @NotNull String agentYamlSha256,
        @NotNull String personaSha256,
        @NotNull String summary) {

    public static ReviewScoreDto from(Score score) {
        return new ReviewScoreDto(score.dimension(), score.weight(), score.score(), score.agentId(), score.assistAgentId(),
                score.assistAgentYamlSha256(), score.agentYamlSha256(), score.personaSha256(), score.summary());
    }
}
