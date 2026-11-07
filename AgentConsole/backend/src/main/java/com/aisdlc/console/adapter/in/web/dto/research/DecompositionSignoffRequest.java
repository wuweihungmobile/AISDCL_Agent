package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchDecompositionUseCase.WaiverInput;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.List;

/**
 * 簽核拆解的本文（API-RP-16；D-113）：{@code waivers[{ac, reason}]} 選填——未覆蓋的 AC 須被 task 涵蓋或在這裡附 1～500 字的人工豁免理由。
 * approver 一律取 JWT subject（憑證無帳號名＝400；本文帶 approver 被忽略）。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "DecompositionSignoffRequest", description = "簽核拆解：選填 waivers[{ac, reason}]（未覆蓋 AC 的人工豁免理由，1～500 字）")
public record DecompositionSignoffRequest(@Schema(description = "豁免清單（選填）") List<Waiver> waivers) {

    /** 一條豁免。 */
    @Schema(name = "DecompositionWaiverRequest")
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Waiver(@Schema(description = "AC 編號") String ac, @Schema(description = "豁免理由，1～500 字") String reason) {
    }

    public List<WaiverInput> toInput() {
        return waivers == null ? null : waivers.stream().map(w -> new WaiverInput(w == null ? null : w.ac(), w == null ? null : w.reason())).toList();
    }
}
