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
    /** 已認證但角色不足（403；安全層的 RBAC 與 controller 的角色檢查共用，附錄 B.1）。 */
    public static final String ACCESS_DENIED = "ACCESS_DENIED";

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

    // ── 執行（Phase 4；附錄 B.2）────────────────────────────────────────────
    /** PRD 逐字（API-EXE-11）。 */
    public static final String UNSIGNED_DRAFT = "未經人工審批的草案不可執行";
    public static final String PROJECT_EXECUTING = "專案正在執行中";
    public static final String PROJECT_STATE_NOT_EXECUTABLE = "專案狀態不允許執行";
    public static final String SCOPE_INVALID = "所選範圍不合法";
    public static final String SCOPE_ALREADY_DONE = "所選任務或目標已完成";
    public static final String SCOPE_MISSING_DEPENDENCIES = "所選目標依賴未完成的前置目標";
    public static final String NOTHING_TO_EXECUTE = "沒有可執行的任務";
    /** 與 Phase 2 的 {@code DagService.CYCLE_REASON} 同字串（附錄 B.1：400／執行時偵測到成環為 409）。 */
    public static final String DEPENDENCY_CYCLE = "依賴成環";
    public static final String PROMPT_TOO_LONG = "步驟 prompt 超過 20000 字元上限";
    public static final String EVALUATOR_DENIED_CHARS = "評估指令含禁用字元";
    public static final String EVALUATOR_NOT_ALLOWED = "評估指令不在可執行檔白名單";
    public static final String REGEX_NOT_COMPILABLE = "expectedOutputRegex 無法編譯";
    public static final String TOO_MANY_TASKS = "範圍任務數超過單一批次上限 500";
    public static final String MAX_RETRIES_EXCEEDED = "任務最大重試次數超過上限 20";
    public static final String LOCK_HELD = "同專案同路徑已有執行中的批次";
    public static final String RUN_STATE_NOT_ALLOWED = "目前執行狀態不允許此操作";
    public static final String NO_CHECKPOINT = "找不到可續跑的 checkpoint";
    public static final String RUN_UNKNOWN_AT_BRIDGE = "引擎端已無此執行（工作區可能已清除）";
    public static final String RESTORE_ONLY_LATEST = "只能還原專案最新的執行批次";
    public static final String REVIEW_ALREADY_DECIDED = "審核項已處理";
    public static final String REVIEW_DECISION_NOT_ALLOWED = "此審核項不允許該決定";

    // ── 專案刪除與復原（W5，契約 v1.2；附錄 B.2）────────────────────────────────
    // 🔴 這三個是英文識別字（契約 §0.3 第 5 點），與 Phase 3～6 的中文逐字常數並存；規則相同：逐字、前後端各一份、不得用 message 判斷。
    /**
     * 刪除目標／任務時專案有進行中批次（C-8，QA O-05；契約 §1.6.3）。🔴 與上面 {@link #PROJECT_EXECUTING}（{@code 專案正在執行中}：
     * <b>啟動執行</b>被擋）是不同的 reason，不可混用。
     */
    public static final String PROJECT_RUN_IN_PROGRESS = "project_executing";
    /** 復原一個沒被軟刪除的專案（C-3；契約 §1.6.1）。 */
    public static final String PROJECT_NOT_DELETED = "project_not_deleted";
    /** 軟刪除已超過保留期（{@code console.retention.soft-delete-days}），不可再經 API 復原（C-3；契約 §1.6.1）。 */
    public static final String RESTORE_WINDOW_EXPIRED = "restore_window_expired";

    // ── 監控（Phase 5）──────────────────────────────────────────────────────
    public static final String TIME_RANGE_INVALID = "時間範圍不合法";
    public static final String REPORT_FORMAT_UNSUPPORTED = "不支援的報表格式";

    // ── SDD 整合迴圈（v1.5，整合輪 115；契約 §0.3 第 8 點、附錄 B.5）────────────────────
    // 🔴 全是英文識別字（逐字、前後端各一份、不得用 message 判斷）；沒有 sdd_not_bound（D-115-14 之後不存在「未綁定」狀態）。
    /** freeze：{@code current_state} 不是 {@code HUMAN_PENDING}；execute／resume／restore（SDD run）：預檢表判 409。 */
    public static final String SDD_FSM_STATE_CONFLICT = "sdd_fsm_state_conflict";
    /** freeze／execute：有效 FSM 專案沒有狀態檔（要先在專案根的 SDD session 建立）。 */
    public static final String SDD_FSM_NOT_FOUND = "sdd_fsm_not_found";
    /** 規格內容與（核准人看過的／凍結時的／匯入時的）摘要不同：freeze 的 {@code expected_vs_file}、批次預檢的 {@code frozen_vs_file}／{@code import_vs_file}。 */
    public static final String SDD_SPEC_DIGEST_CHANGED = "sdd_spec_digest_changed";
    /** 綁定唯一性：同一個 {@code (executionPath, sddProject)} 已被另一個未刪除的專案綁定，或匯入併入時與目標專案的綁定不一致。 */
    public static final String SDD_BINDING_CONFLICT = "sdd_binding_conflict";
    /** backend 或 Bridge 沒有設定寫入權杖（{@code BRIDGE_SDD_WRITE_TOKEN}）：SDD 寫入面整個停用（503）。 */
    public static final String SDD_WRITE_DISABLED = "sdd_write_disabled";
    /**
     * {@code GET /executions/{runId}/rtm}：批次存在但沒有追溯報告（404；「404 的 reason 省略」慣例的例外之一，另一個是
     * {@link #SI_NOT_FOUND}）。
     */
    public static final String RTM_NOT_FOUND = "rtm_not_found";

    // ── SelfImproving 唯讀鏡像（P1b；Architecture §11.1〈SelfImproving 相關的 reason〉；前端住 lib/domain/si.ts 的 SI_REASONS）──
    // 🔴 前端 REASONS 與凍結契約附錄 B 雙向鎖，所以這兩個常數不進 lib/api/reasons.ts；兩邊各一份、逐字相同。
    /** Bridge 的 {@code /si/*} 不可用（503）：{@code details.cause}、{@code details.detail} 逐字取自 Bridge（原因與 stderr 末 1,000 字元）。 */
    public static final String SI_UNAVAILABLE = "si_unavailable";
    /** 單筆提案不存在（404，帶 {@code details.id}）：「404 的 reason 省略」慣例的例外之一，另一個是 {@link #RTM_NOT_FOUND}。 */
    public static final String SI_NOT_FOUND = "si_not_found";

    // ── SelfImproving 寫入載體（P2b；TCS-SelfImprovingDecide-P2b W15；Architecture §11.1；前端住 lib/domain/si.ts 的 SI_REASONS）──
    /**
     * SelfImproving 寫入面停用（503）：backend 沒有設定稽核簽章金鑰或 Bridge 寫入權杖（{@code details.cause}＝{@code audit_key_unset}｜
     * {@code bridge_token_unset}，先中者），或 Bridge 回報它沒設權杖或稽核目錄（{@code details.detail} 逐字）。
     */
    public static final String SI_WRITE_DISABLED = "si_write_disabled";
    /**
     * 沒有資格寫入（403）：JWT 帳號名不在 {@code console.si.deciders} 名單內（區分大小寫），或 Bridge 拒絕 backend 附的權杖
     * （兩端權杖設定不一致）。與 {@link #ACCESS_DENIED}（角色非 ADMIN）是兩件事。
     */
    public static final String SI_WRITE_FORBIDDEN = "si_write_forbidden";
    /** 稽核檔已存在（409）：Bridge 以獨佔建檔拒絕覆寫同名 {@code <audit_ref>.json}（每次新 ref，正常情況不會發生）。 */
    public static final String SI_AUDIT_EXISTS = "si_audit_exists";

    // ── 議題中心（TCS-IssueCenter-20261027 D-C5；契約 API_Contract_IssueCenter.md 的〈issue 類 reason 表〉；前端住 lib/domain/issues.ts 的 ISSUE_REASONS）──
    // 🔴 與 SI 類同規則：不進 lib/api/reasons.ts（它與 API_Contract_P3-6.md 附錄 B 雙向鎖）；前端 ISSUE_REASONS、本類別的 ISSUE_ 前綴常數與契約表三方雙向鎖。
    /** 設定優先順序的議題狀態不是可排的三種之一（409；{@code details.id}、{@code details.status}）：PUT 不寫入。 */
    public static final String ISSUE_NOT_RANKABLE = "issue_not_rankable";
}
