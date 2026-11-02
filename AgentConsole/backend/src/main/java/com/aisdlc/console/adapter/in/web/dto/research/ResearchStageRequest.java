package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.StageInput;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 啟動階段的選填請求本文（契約 API-RP-11）。{@code requested_by} 不在本文：一律取 JWT subject。{@code afterEscalation}＝「我已恢復，繼續」——Bridge 唯讀驗證 FSM
 * 已離開 ESCALATION*（否則 409 {@code fsm_state_conflict}），不呼叫任何 FSM 寫入動詞；恢復後預算不歸零、至多再得一次審查（D-60）。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "ResearchStageRequest", description = "啟動階段的選填本文：auto（自動迭代）、note、afterEscalation（我已恢復，繼續）")
public record ResearchStageRequest(
        @Schema(description = "自動模式（預設 false）") Boolean auto,
        @Schema(description = "給本次階段的備註") String note,
        @Schema(description = "ESCALATION 人工恢復後的繼續（只對 revise 有意義；預設 false）") Boolean afterEscalation) {

    public StageInput toInput() {
        return new StageInput(auto, note, afterEscalation);
    }
}
