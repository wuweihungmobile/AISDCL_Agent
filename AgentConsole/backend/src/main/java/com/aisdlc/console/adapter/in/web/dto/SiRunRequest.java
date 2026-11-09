package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SiWriteUseCase.RunRequestInput;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * {@code POST /api/v1/si/runs/request} 的請求本文（TCS-SelfImprovingSchedule W-S7、表 M-R；契約 P2c §1.2.2）：{@code {}} 或 {@code {note}}。
 * 同 {@link SiScheduleSetRequest}：沒有 Bean Validation、{@code note} 以 {@code Object} 接收（非字串＝422）。
 */
@Schema(name = "SiRunRequest", description = "請求主機立即啟動一次自我進化運轉（觸發 a）。本文可為空物件；note 選填。"
        + "201 是稽核檔已落地、待入帳，不是已啟動")
public record SiRunRequest(
        @Schema(implementation = String.class, minLength = 1, maxLength = 120, description = "備註（選填；1～120 個 code point 的單行字串，不含控制字元，有值不得全空白；允許豎線）。省略則稽核 body 不含該鍵")
        Object note) {

    public RunRequestInput toInput() {
        return new RunRequestInput(note);
    }
}
