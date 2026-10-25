package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SiWriteUseCase.CloseInput;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * {@code POST /api/v1/si/observations/{id}/close} 的請求本文（TCS-SelfImprovingDecide-P2b W12、表 M-C；PRD AC-SI-35-2）：把處置為 open 的觀察列一次關成
 * 終值。路徑 {@code id} 是 OBS 號。{@code ref} 與 {@code text} 恰擇一（依終值）。刻意沒有 Bean Validation（同 {@link SiDecideRequest}）。
 */
@Schema(name = "SiCloseRequest", description = "關閉觀察列。七個終值（沒有 open）：fixed（ref＝7～40 碼小寫十六進位提交編號）、def（ref＝DEF-<n>-<n>）、"
        + "merged（ref＝OBS 號）、proposed（ref＝PROP 號）、deferred／retired／decided（text＝1～120 個字元，不含豎線、控制字元與「之後再看」）")
public record SiCloseRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"fixed", "def", "deferred", "retired", "decided",
                "merged", "proposed"}, description = "終值") String terminal,
        @Schema(description = "fixed、def、merged、proposed 必填（格式依終值）；其餘不可帶") String ref,
        @Schema(minLength = 1, maxLength = 120, description = "deferred、retired、decided 必填；其餘不可帶。與終值以全形冒號相接成處置終值") String text) {

    public CloseInput toInput() {
        return new CloseInput(terminal, ref, text);
    }
}
