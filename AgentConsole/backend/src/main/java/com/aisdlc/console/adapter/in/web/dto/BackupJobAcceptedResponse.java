package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.BackupJobUseCase.Accepted;
import io.swagger.v3.oas.annotations.media.Schema;

/** {@code POST /api/v1/sysadmin/backups/jobs} 成功（202）的 {@code data}（TCS-SysAdminBackup-20261027 §C3.4）：{@code status} 恆為 {@code QUEUED}。 */
@Schema(name = "BackupJobAccepted", description = "手動觸發已受理：工作已排入佇列（QUEUED），由 sidecar 撿取後執行")
public record BackupJobAcceptedResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "工作 id（UUID；伺服器產生）") String id,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"full", "diff", "verify"}) String type,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"QUEUED"}) String status,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "要求時間（UTC，ISO-8601 帶 Z）") String requestedAt) {

    public static BackupJobAcceptedResponse from(Accepted accepted) {
        return new BackupJobAcceptedResponse(accepted.id(), accepted.type(), accepted.status(), accepted.requestedAt().toString());
    }
}
