package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SiWriteUseCase.RegistrySyncResult;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 登記同步的收據（API-SI-15）。{@code written}（201）：稽核檔已落地、<b>待入帳</b>（不是已生效）；{@code unchanged}（200）：零副作用，{@code auditRef} 是已存在那一份，
 * {@code kind}、{@code time}、{@code keyId} 為 null。沒有 body 與 mac。
 */
@Schema(name = "ResearchRegistrySyncResult", description = "登記同步的結果；written＝稽核檔已落地、待入帳；unchanged＝內容沒變、零副作用")
public record ResearchRegistrySyncResultResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"written", "unchanged"}) String outcome,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"pending", "synced"}) String state,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String registrySha256,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, format = "uuid", description = "稽核編號（written＝新的；unchanged＝已存在的）") String auditRef,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"src-registry"}) String kind,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "稽核 body 的 time（±HH:MM）") String time,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "簽章金鑰的 sha256 前 8 碼") String keyId) {

    public static ResearchRegistrySyncResultResponse from(RegistrySyncResult result) {
        return new ResearchRegistrySyncResultResponse(result.outcome(), result.state(), result.registrySha256(), result.auditRef(), result.kind(),
                result.time(), result.keyId());
    }
}
