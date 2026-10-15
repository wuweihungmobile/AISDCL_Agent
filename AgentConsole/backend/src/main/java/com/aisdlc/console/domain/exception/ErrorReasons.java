package com.aisdlc.console.domain.exception;

/**
 * 錯誤 {@code reason} 常數集中處（契約 §0.3 第 1 點、附錄 B；前端 {@code lib/api/reasons.ts} 與此逐字相同，
 * E2E 以 {@code reason} 逐字比對，所以任何一個字都不能改）。
 *
 * <p>{@code message} 是給人看的句子、可含動態值，<b>不得</b>拿來做程式判斷；{@code reason} 才是前後端共用的常數。
 * 本類別只收 Phase 3（匯入）、Phase 6（設定）與通用的常數；執行與監控的常數由後續棒次在同一處補入（附錄 B.2）。
 */
public final class ErrorReasons {

    private ErrorReasons() {
    }

    // ── 通用 ────────────────────────────────────────────────────────────────
    public static final String RATE_LIMITED = "超過每分鐘 100 次請求上限";
    public static final String BRIDGE_UNREACHABLE = "引擎橋接服務無法連線";
    public static final String BRIDGE_TIMEOUT = "引擎橋接服務逾時";
    public static final String BRIDGE_ERROR = "引擎橋接服務錯誤";
    public static final String BRIDGE_REJECTED = "引擎拒絕此請求";

    // ── Phase 1+2 既有（逐字沿用）────────────────────────────────────────────
    public static final String ALREADY_SIGNED_OFF = "已 signoff";
    public static final String COMMAND_DENIED_CHARS = "命令含禁用字元";

    // ── 匯入（Phase 3）──────────────────────────────────────────────────────
    public static final String FILE_MISSING = "未提供檔案";
    public static final String FILE_EMPTY = "檔案是空的";
    public static final String FILE_TOO_LARGE = "檔案超過 10MB 上限";
    public static final String FILE_TYPE_UNSUPPORTED = "只支援 .md／.pdf／.docx 檔案";
    public static final String FILE_CONTENT_MISMATCH = "檔案內容與副檔名不符";
    public static final String FILE_NOT_UTF8 = "檔案不是有效的 UTF-8 文字";
    public static final String PDF_ENCRYPTED = "PDF 已加密，無法擷取文字";
    public static final String FILE_CORRUPT = "檔案已損毀，無法讀取";
    public static final String FILE_NO_TEXT = "無法從檔案擷取文字";
    public static final String IMPORT_PARSING = "解析中，請稍候";
    public static final String IMPORT_SIGNED_OFF_NO_REPARSE = "已 signoff，不可重新解析";
    public static final String IMPORT_STATE_NOT_ALLOWED = "匯入記錄狀態不允許此操作";
    public static final String IMPORT_GATE_REJECTED = "解析結果未通過有界閘";
    public static final String SDD_SPEC_REJECTED = "SDD 規格檢查未通過";
    public static final String DRAFT_EXPIRED = "草案已失效，請重新解析";
    public static final String IMPORT_NOT_SIGNED_OFF = "草案尚未 signoff，不可確認匯入";
    public static final String ALREADY_IMPORTED = "已匯入";

    // ── 設定（Phase 6）──────────────────────────────────────────────────────
    public static final String REVEAL_ADMIN_ONLY = "僅 ADMIN 可揭露敏感參數";
    public static final String CONFIG_VALUE_INVALID = "參數值不符合型別或驗證規則";
    /** PRD 逐字（NFR-SEC-05）。 */
    public static final String TOKEN_GUARD_ORDER = "halt_threshold_pct 必須大於 compact_threshold_pct";
    public static final String OUTBOUND_REJECTED = "目標位址未通過 SSRF／allowlist 檢查";
    public static final String CONFIG_UPDATE_CONFIRM = "敏感參數更新需二次確認（confirm=true）";
    public static final String CONFIG_RESET_CONFIRM = "敏感參數重置需二次確認（confirm=true）";
    public static final String SETTINGS_FILE_FORMAT = "設定檔格式錯誤";
    public static final String SETTINGS_FILE_TOO_LARGE = "設定檔超過 1MB 上限";
    public static final String SETTINGS_FILE_TYPE = "只接受 JSON 設定檔";
    /** 匯入設定檔時，檔案裡有一筆「不存在於系統的鍵」（契約 §1.5.10）。 */
    public static final String CONFIG_KEY_UNKNOWN = "設定鍵不存在";
}
