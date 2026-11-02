package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.ReinitInput;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 重試初始化／換世代的請求本文（契約 API-RP-20；本文可省略）：無 {@code generation}＝重試初始化（冪等，OPERATOR 以上）；{@code generation="next"}＝換世代
 * （<b>僅 ADMIN</b>，{@code reason} 必填 1～500 字；D-60、D-64）。<b>本文型別沒有決定者欄</b>：決定者一律取 JWT subject，多帶的欄位被忽略。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "ResearchReinitRequest", description = "重試初始化（空本文）或換世代（generation=next＋reason）")
public record ResearchReinitRequest(
        @Schema(allowableValues = {"next"}, description = "next＝換世代（僅 ADMIN）；缺省＝重試初始化") String generation,
        @Schema(maxLength = 500, description = "換世代必填（1～500 字）") String reason) {

    public ReinitInput toInput() {
        return new ReinitInput(generation, reason);
    }
}
