package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.AllowlistInput;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 新增 allowlist 條目的請求本文（契約 API-RP-22；僅 ADMIN）。{@code minIntervalSeconds} 建立時決定、建立後不可改；Reddit 網域（reddit.com、*.reddit.com、
 * redd.it）須 {@code tosAcknowledged=true}（否則 422 {@code terms_ack_required}）。新增人一律取 JWT subject。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "ResearchAllowlistRequest", description = "新增 allowlist 條目：listKind、host、layer、purpose、tosNote、minIntervalSeconds、tosAcknowledged")
public record ResearchAllowlistRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"FETCH", "WEB"}) String listKind,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "小寫 host（無 scheme、埠、路徑、userinfo）") String host,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY"}) String layer,
        @Schema(maxLength = 200) String purpose,
        String tosNote,
        @Schema(minimum = "1", maximum = "3600", description = "建立時決定、建立後不可改；實際間隔＝max(Bridge 內建下限, 本值)；缺省由 Bridge 取預設") Integer minIntervalSeconds,
        @Schema(description = "Reddit 網域必為 true") Boolean tosAcknowledged) {

    public AllowlistInput toInput() {
        return new AllowlistInput(listKind, host, layer, purpose, tosNote, minIntervalSeconds, tosAcknowledged);
    }
}
