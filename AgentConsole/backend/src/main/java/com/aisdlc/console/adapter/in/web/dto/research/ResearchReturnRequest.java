package com.aisdlc.console.adapter.in.web.dto.research;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

/** 退回修改的請求本文（契約 API-RP-21；僅 ADMIN）：理由必填（1～500 字）；退回人一律取 JWT subject。 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "ResearchReturnRequest", description = "退回修改：reason（必填，1～500 字）")
public record ResearchReturnRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minLength = 1, maxLength = 500) String reason) {
}
