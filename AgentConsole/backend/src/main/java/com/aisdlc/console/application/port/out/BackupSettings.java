package com.aisdlc.console.application.port.out;

import java.nio.file.Path;

/**
 * 備份控制面的程序層設定（{@code console.backup.*}；TCS-SysAdminBackup-20261027 §C3.5）。application 層不認得 {@code infrastructure}，所以目錄與門檻
 * 經這支埠取值（實作：{@code BackupSettingsAdapter}，由 {@code BackupProperties} 轉出）。每次呼叫都重新取值（測試以可切換的假實作驗各種情境）。
 *
 * <p><b>未設＝停用</b>：{@link #exportDir()} 未設 ⇒ {@code GET /backups} 回 200 加 {@code not_configured}；POST 另需 {@link #requestDir()}
 * （GET 只依 export-dir，POST 另依 request-dir）。
 */
public interface BackupSettings {

    /** 輸出卷根目錄（容器內 {@code /backup-out}；其下 {@code export/}、{@code results/}）；未設為 null。 */
    Path exportDir();

    /** 請求卷根目錄（容器內 {@code /backup-req}）；未設為 null。 */
    Path requestDir();

    /** 請求的存活秒數（{@code expires_at = requested_at + 此值}；預設 120）。 */
    int requestTtlSeconds();

    /** RUNNING 工作的逾時上限秒數（預設 21600）；逾時且心跳過期才標 {@code timeout}。 */
    int jobMaxSeconds();

    /** 對帳排程的週期（毫秒；預設 5000）。 */
    long reconcileIntervalMs();

    /** 逾期的寬限分鐘（預設 30；嚴格大於才算逾期）。 */
    int overdueGraceMinutes();

    /** 全備的頻率上限秒數（預設 86400）。 */
    long minFullIntervalSeconds();

    /** 增備的頻率上限秒數（預設 3600）。 */
    long minDiffIntervalSeconds();
}
