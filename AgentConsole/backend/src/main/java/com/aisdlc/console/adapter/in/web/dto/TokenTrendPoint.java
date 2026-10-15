package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.MonitorUseCase.TokenTrendView;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;

/** Token 趨勢的一個桶（契約 §1.3.2、§3.8.2）：沒有資料的桶不輸出（前端自行補零）。 */
@Schema(name = "TokenTrendPoint")
public record TokenTrendPoint(
        @NotNull @Schema(description = "桶起點（UTC 整點或整日）") Instant bucketStart,
        @NotNull @Schema(description = "該桶內 Token 增量之和") long tokens,
        @NotNull @Schema(description = "視窗起點起累計") long cumulativeTokens,
        @JsonInclude(JsonInclude.Include.ALWAYS)
        @Schema(nullable = true, description = "預算線；無預算為 null") Long budget) {

    public static TokenTrendPoint from(TokenTrendView v) {
        return new TokenTrendPoint(v.bucketStart(), v.tokens(), v.cumulativeTokens(), v.budget());
    }
}
