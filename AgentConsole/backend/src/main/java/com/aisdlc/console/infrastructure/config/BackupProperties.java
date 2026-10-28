package com.aisdlc.console.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/**
 * 備份控制面的程序層設定（{@code console.backup.*}；TCS-SysAdminBackup-20261027 §C3.5）。<b>只作綁定</b>：服務層一律經
 * {@code application/port/out/BackupSettings} 取值（application 層不認得 infrastructure），實作是 {@link BackupSettingsAdapter}。
 *
 * <p>{@code export-dir}（環境變數 {@code CONSOLE_BACKUP_OUT_DIR}）與 {@code request-dir}（{@code CONSOLE_BACKUP_REQ_DIR}）<b>未設＝停用</b>
 * （空白視為未設）：不在 Docker 全棧時整個備份頁顯示「備份控制面未設定」，不是靜默回空。compose 把兩者設成字面常數 {@code /backup-out}、{@code /backup-req}，
 * 不含機密。GET 只依 export-dir，POST 另依 request-dir。
 *
 * @param exportDir             輸出卷根目錄；空白＝null
 * @param requestDir            請求卷根目錄；空白＝null
 * @param requestTtlSeconds     請求存活秒數（預設 120）
 * @param jobMaxSeconds         RUNNING 工作的逾時上限秒數（預設 21600）
 * @param reconcileIntervalMs   對帳排程週期毫秒（預設 5000）
 * @param overdueGraceMinutes   逾期的寬限分鐘（預設 30）
 * @param minFullIntervalSeconds 全備的頻率上限秒數（預設 86400）
 * @param minDiffIntervalSeconds 增備的頻率上限秒數（預設 3600）
 */
@ConfigurationProperties(prefix = "console.backup")
public record BackupProperties(String exportDir, String requestDir,
                               @DefaultValue("120") int requestTtlSeconds,
                               @DefaultValue("21600") int jobMaxSeconds,
                               @DefaultValue("5000") long reconcileIntervalMs,
                               @DefaultValue("30") int overdueGraceMinutes,
                               @DefaultValue("86400") long minFullIntervalSeconds,
                               @DefaultValue("3600") long minDiffIntervalSeconds) {

    public BackupProperties {
        exportDir = blankToNull(exportDir);
        requestDir = blankToNull(requestDir);
        requirePositive(requestTtlSeconds, "console.backup.request-ttl-seconds");
        requirePositive(jobMaxSeconds, "console.backup.job-max-seconds");
        requirePositive(reconcileIntervalMs, "console.backup.reconcile-interval-ms");
        requirePositive(overdueGraceMinutes, "console.backup.overdue-grace-minutes");
        requirePositive(minFullIntervalSeconds, "console.backup.min-full-interval-seconds");
        requirePositive(minDiffIntervalSeconds, "console.backup.min-diff-interval-seconds");
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.strip();
    }

    private static void requirePositive(long value, String property) {
        if (value < 1) {
            throw new IllegalArgumentException(property + " 必須 ≥ 1（目前為 " + value + "）");
        }
    }
}
