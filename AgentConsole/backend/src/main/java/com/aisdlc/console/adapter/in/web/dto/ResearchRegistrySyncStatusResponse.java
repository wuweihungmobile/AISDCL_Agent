package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SiWriteUseCase.RegistrySyncStatus;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 登記同步狀態（API-SI-14；TCS-ResearchRegistry AT-965-7-3）：{@code data} 的鍵集合恰為這八個；<b>沒有 body、mac、keyId、registryText</b>。
 * {@code unknown}（鏡像讀不到）時 {@code unknownCause} 非 null、{@code currentSha256} 之外的欄位皆 null；量不到不顯示成已同步或零。
 */
@Schema(name = "ResearchRegistrySyncStatus", description = "研究來源登記與自我進化鏡像的同步狀態")
public record ResearchRegistrySyncStatusResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"synced", "unsynced", "pending", "unknown"}) String state,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED,
                allowableValues = {"scan_cap_exceeded", "si_unavailable", "bridge_unreachable", "bridge_timeout"}, description = "state=unknown 時的原因") String unknownCause,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "Console 當下登記快照的 digest（sha256:…）") String currentSha256,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "自我進化鏡像最新已入帳的登記 digest；從未同步為 null") String ingestedSha256,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String ingestedAuditRef,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "state=pending 時：最新待入帳的稽核檔編號") String pendingAuditRef,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "state=pending 時：該稽核檔的 time（±HH:MM）") String pendingTime,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "自我進化每次抓取上限（只轉鏡像值；缺席或非正整數為 null）") Integer researchFetchMax) {

    public static ResearchRegistrySyncStatusResponse from(RegistrySyncStatus status) {
        return new ResearchRegistrySyncStatusResponse(status.state(), status.unknownCause(), status.currentSha256(), status.ingestedSha256(),
                status.ingestedAuditRef(), status.pendingAuditRef(), status.pendingTime(), status.researchFetchMax());
    }
}
