package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SiWriteUseCase.ScheduleSetInput;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * {@code POST /api/v1/si/schedule/set} 的請求本文（TCS-SelfImprovingSchedule W-S7、表 M-S；契約 P2c §1.2.1）。<b>刻意沒有 Bean Validation，且三個欄位都以
 * {@code Object} 接收 JSON 解出的原始型別</b>：字串 {@code "true"}、小數、字串 {@code "120"}、布林充當整數都要在輸入閘被當成違規一次全列（422
 * {@code invalid_request}、{@code details.violations[{field,message}]}），不能被序列化器悄悄轉型。下面的 {@code @Schema} 只供 OpenAPI 文件。
 * 未知欄位沿其他 POST 的現行行為（Spring Boot 的預設：忽略；稽核 body 只由這三個欄位組成，不會把未知欄位簽進去）。
 */
@Schema(name = "SiScheduleSetRequest", description = "設定自動演化排程（啟用或停用、週期）。enabled 與 periodMinutes 兩鍵皆必備（停用時也須帶界內週期）；"
        + "週期的界取自 GET /si/status 的 schedule.periodMin～periodMax（含端點），不寫死在前後端")
public record SiScheduleSetRequest(
        @Schema(type = "boolean", requiredMode = Schema.RequiredMode.REQUIRED, description = "true＝啟用、false＝停用；必須是 JSON 布林（字串 \"true\" 不收）")
        Object enabled,
        @Schema(type = "integer", format = "int32", minimum = "1", requiredMode = Schema.RequiredMode.REQUIRED,
                description = "週期（分鐘）；必須是 JSON 整數（小數、字串、布林、0、負數不收），且須在當下 status.schedule 的界內（含端點）")
        Object periodMinutes,
        @Schema(type = "string", minLength = 1, maxLength = 120, description = "理由（選填；1～120 個 code point 的單行字串，不含控制字元，有值不得全空白；允許豎線）。省略則稽核 body 不含該鍵")
        Object reason) {

    public ScheduleSetInput toInput() {
        return new ScheduleSetInput(enabled, periodMinutes, reason);
    }
}
