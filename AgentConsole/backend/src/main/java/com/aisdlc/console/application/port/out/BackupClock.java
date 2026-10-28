package com.aisdlc.console.application.port.out;

import java.time.Instant;

/**
 * 備份功能專屬的時間來源（TCS-SysAdminBackup-20261027 §5.2、R-BK-12）。備份的服務層一律取它、不呼叫任何「現在」的靜態方法
 * （{@code BackupArchTest} 以掃描鎖住）；正式實作委派全域 {@code Clock}（{@code BackupClockConfig}）。
 *
 * <p>為什麼不直接注入全域 {@code Clock}：JWT 的簽發與驗證、限流、審計都吃全域時鐘，整合測試若為了驗逾期而撥動它，同一個 JVM 裡共用的
 * access token 會全部過期而連帶 401；專屬型別讓測試只撥備份用的這一支（先例 {@code SiWriteSeam}）。
 */
@FunctionalInterface
public interface BackupClock {

    /** 現在（UTC 的瞬間）。 */
    Instant instant();
}
