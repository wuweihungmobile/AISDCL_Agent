package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.BackupQueryUseCase.JobPageView;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.List;

/** {@code GET /api/v1/sysadmin/backups/jobs} 的 {@code data}（TCS-SysAdminBackup-20261027 §C3.2、D-BK-T14）：{@code requested_at} 嚴格新到舊的一頁加續取游標。 */
@Schema(name = "BackupJobPage", description = "工作紀錄的一頁（新到舊）；nextBefore 是續取游標（尚有更多時為本頁最後一筆的 requestedAt，否則 null）")
public record BackupJobPageResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<BackupJobResponse> items,
        @Schema(nullable = true, description = "續取游標：下一頁以 before=<nextBefore> 請求（嚴格小於）") String nextBefore) {

    public static BackupJobPageResponse from(JobPageView page) {
        return new BackupJobPageResponse(page.items().stream().map(BackupJobResponse::from).toList(),
                BackupJobResponse.iso(page.nextBefore()));
    }
}
