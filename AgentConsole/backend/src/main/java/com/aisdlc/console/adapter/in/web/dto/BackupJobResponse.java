package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.BackupQueryUseCase.JobView;
import io.swagger.v3.oas.annotations.media.Schema;

import java.time.Instant;

/**
 * 一筆 Console 發起的備份工作（TCS-SysAdminBackup-20261027 §C3.2、§C3.3；{@code GET /backups/jobs} 的 {@code items[]} 與單筆端點的 {@code data}）。
 * 時間為 UTC 帶 {@code Z} 的 ISO-8601；{@code requestedBy}、{@code detail} <b>僅 ADMIN</b> 有值（非 ADMIN 為 null）。
 */
@Schema(name = "BackupJob", description = "Console 發起的備份工作（手動觸發；排程工作不在此表）")
public record BackupJobResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "工作 id（UUID）") String id,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"full", "diff", "verify"}) String type,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED,
                allowableValues = {"QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "REJECTED", "EXPIRED"}) String status,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "要求時間（UTC，ISO-8601 帶 Z）") String requestedAt,
        @Schema(nullable = true, description = "runner 撿起請求的時間；尚未開始為 null") String startedAt,
        @Schema(nullable = true, description = "終態時間；進行中為 null") String finishedAt,
        @Schema(nullable = true, description = "耗時（秒）") Integer durationSeconds,
        @Schema(nullable = true, description = "工作腳本的結束碼；被拒、逾時、中斷者為 null") Integer exitCode,
        @Schema(nullable = true, description = "封閉詞彙（契約〈backup 類 reason 表〉的工作理由）；成功為 null") String reason,
        @Schema(nullable = true, description = "觸發者；僅 ADMIN") String requestedBy,
        @Schema(nullable = true, description = "已遮罩的輸出尾段（≤2000 字元）；僅 ADMIN") String detail) {

    public static BackupJobResponse from(JobView view) {
        return new BackupJobResponse(view.id(), view.type(), view.status(), iso(view.requestedAt()), iso(view.startedAt()),
                iso(view.finishedAt()), view.durationSeconds(), view.exitCode(), view.reason(), view.requestedBy(), view.detail());
    }

    static String iso(Instant instant) {
        return instant == null ? null : instant.toString();
    }
}
