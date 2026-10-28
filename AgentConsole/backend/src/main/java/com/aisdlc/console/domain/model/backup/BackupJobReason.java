package com.aisdlc.console.domain.model.backup;

import java.util.Arrays;
import java.util.Optional;

/**
 * {@code console.backup_jobs.reason} 的封閉詞彙（TCS-SysAdminBackup-20261027 §C4〈backup 類 reason 表〉狀態碼欄為「—」的八列；R-BK-60）。
 * 契約表、本列舉、前端 {@code BACKUP_REASONS} 三方鍵集合與訊息雙向鎖住（{@code BackupReasonsContractTest}）：新增或刪除一個值，鎖就紅。
 *
 * <p>誰寫哪一個：{@code script_failed}、{@code interrupted}、{@code lock_timeout}、{@code busy}、{@code rejected_invalid}、{@code expired}
 * 來自 sidecar 的 results（對帳時只收詞彙內的值，詞彙外一律當 {@code script_failed}）；{@code timeout}、{@code control_write_failed}
 * 只由 console-api 自己寫（對帳逾時、補償 UPDATE），sidecar 不寫。
 */
public enum BackupJobReason {

    SCRIPT_FAILED("script_failed", "備份腳本執行失敗，請看輸出尾段"),
    INTERRUPTED("interrupted", "容器重啟或工作被中斷"),
    TIMEOUT("timeout", "工作逾時，控制面無回應"),
    LOCK_TIMEOUT("lock_timeout", "等待維護鎖逾時，已有其他工作在執行"),
    CONTROL_WRITE_FAILED("control_write_failed", "請求無法送出（控制面寫入失敗）"),
    BUSY("busy", "排程工作執行中，稍後再試"),
    REJECTED_INVALID("rejected_invalid", "請求內容不合法，已被拒絕"),
    EXPIRED("expired", "請求逾時未被執行");

    private final String value;
    private final String message;

    BackupJobReason(String value, String message) {
        this.value = value;
        this.message = message;
    }

    /** 寫進資料庫與 API 的值（snake_case 識別字）。 */
    public String value() {
        return value;
    }

    /** 給人看的中文訊息（與契約表的「中文訊息」欄逐字相同）。 */
    public String message() {
        return message;
    }

    /** 由字串找列舉；不在詞彙內回空。 */
    public static Optional<BackupJobReason> of(String value) {
        return Arrays.stream(values()).filter(reason -> reason.value.equals(value)).findFirst();
    }
}
