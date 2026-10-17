package com.aisdlc.console.adapter.in.web.dto;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * {@code PUT /api/v1/projects/{id}/sdd-binding} 的請求本文（契約 §1.10.7；ADR-XPLAT-016 §7.2）：{@code {"sddProject": "<名稱>" | null}}。
 *
 * <p>這個 record <b>只供 OpenAPI 文件</b>——欄位是「必填但可為 null」（{@code null}＝清除、回到「用預設」＝專案名；鍵缺席是 400），
 * Jackson 的 record 綁定分不出「鍵缺席」與「值為 null」，所以控制器改以 {@code Map} 收本文並顯式檢查鍵是否存在
 * （避免 {@code {}} 悄悄清掉一個綁定）。
 */
@Schema(name = "SddBindingRequest", description = "編輯專案的 FSM 專案鍵（v1.5，D-115-14；ADR-XPLAT-016 §7.2）。sddProject 為 null＝清除，回到「用預設」"
        + "（專案名）；非 null 時去前後空白後 1～100 字元、不含控制字元。不檢查狀態檔是否存在、不呼叫 Bridge")
public record SddBindingRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true, minLength = 1, maxLength = 100,
                description = "FSM 專案鍵（自由輸入，由 Bridge 淨化後生效）；null＝清除，回到「用預設」（專案名）；鍵缺席 → 400")
        String sddProject) {
}
