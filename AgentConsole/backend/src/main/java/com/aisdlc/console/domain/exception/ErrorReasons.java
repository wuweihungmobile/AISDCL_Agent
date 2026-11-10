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

    // ── SelfImproving 寫入載體（P2b；TCS-SelfImprovingDecide-P2b W15；重送閘 TCS-SelfImprovingDecideDedupe W-D1；Architecture §11.1；前端住 lib/domain/si.ts 的 SI_REASONS）──
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
    /**
     * 同一張卡的同一決定已送出過（409；TCS-SelfImprovingDecideDedupe W-D1）：只有 {@code POST /api/v1/si/proposals/{id}/decide} 且動詞帶卡面 digest
     * （approve、reject、return、promote、decline-promote、ack-handoff）時，{@code console.si_console_writes} 已有 {@code kind=decide} 且 subject、digest、dkind
     * 三者相同的列（不論該列是否已入帳、哪個帳號送的）；{@code details}＝{@code existingAuditRef}、{@code dkind}、{@code subject}、{@code digest8}。
     * 這個 reason 由 backend 自己產生，不是 Bridge 的錯誤（{@code SiBridgeErrors} 不涉及）。
     */
    public static final String SI_DECISION_DUPLICATE = "si_decision_duplicate";

    // ── 議題中心（TCS-IssueCenter-20261027 D-C5；契約 API_Contract_IssueCenter.md 的〈issue 類 reason 表〉；前端住 lib/domain/issues.ts 的 ISSUE_REASONS）──
    // 🔴 與 SI 類同規則：不進 lib/api/reasons.ts（它與 API_Contract_P3-6.md 附錄 B 雙向鎖）；前端 ISSUE_REASONS、本類別的 ISSUE_ 前綴常數與契約表三方雙向鎖。
    /** 設定優先順序的議題狀態不是可排的三種之一（409；{@code details.id}、{@code details.status}）：PUT 不寫入。 */
    public static final String ISSUE_NOT_RANKABLE = "issue_not_rankable";

    // ── 系統管理／資料庫備份（TCS-SysAdminBackup-20261027 §C4；契約 API_Contract_SysAdminBackup.md 的〈backup 類 reason 表〉；前端住 lib/domain/sysadminBackup.ts 的 BACKUP_REASONS）──
    // 🔴 與 SI、議題類同規則：不進 lib/api/reasons.ts（它與 API_Contract_P3-6.md 附錄 B 雙向鎖）；前端 BACKUP_REASONS、本類別的 BACKUP_ 前綴常數
    // 與契約表三方雙向鎖。這五個是「有狀態碼的 API reason」；契約表另有八個工作理由（狀態碼欄為「—」），住 BackupJobReason 列舉。
    // 入口閘的 invalid_request（422）以區域常數持有（BackupJobService.INVALID_REQUEST）、不入本類別與契約表（先例 SiWriteGates）。
    /** 控制面不可用（503）：目錄未設定、心跳過期、匯出檔不可讀、資料庫讀取失敗，或寫請求檔失敗（該列已補償為 FAILED）。 */
    public static final String BACKUP_CONTROL_UNAVAILABLE = "backup_control_unavailable";
    /** POST 缺 {@code confirm:true}（400；字串 "true"、數字 1 都不算）。 */
    public static final String BACKUP_CONFIRM_REQUIRED = "backup_confirm_required";
    /** 已有 QUEUED 或 RUNNING 的工作（409；含部分唯一索引的衝突）。 */
    public static final String BACKUP_JOB_IN_PROGRESS = "backup_job_in_progress";
    /** 距離上一份同類備份過近（409；{@code details.type}、{@code details.nextAllowedAt}）。 */
    public static final String BACKUP_TOO_FREQUENT = "backup_too_frequent";
    /** 單筆工作不存在或 id 不是 UUID（404）。 */
    public static final String BACKUP_JOB_NOT_FOUND = "backup_job_not_found";

    // ── 研究到規格（ResearchToPRD P0；TCS-ResearchToPRD-P0-20261102 §5.1「錯誤 reason」、AT-960-5-6；契約 API_Contract_ResearchToPRD.md §0.2；前端住 lib/domain/research.ts 的 RESEARCH_REASONS）──
    // 🔴 與 SI、議題、備份類同規則：不進 lib/api/reasons.ts（它與 API_Contract_P3-6.md 附錄 B 雙向鎖）；前端 RESEARCH_REASONS、本類別的 RESEARCH_ 前綴常數與契約表三方雙向鎖。
    // 前綴一律 RESEARCH_（不得以 ISSUE_、BACKUP_ 起頭，否則兩個既有契約測試的集合鎖紅；TCS §4 #26）。值為英文識別字、逐字；Bridge 的 reason 由 console-api 原樣透傳。
    // 本節的集合＝console-api 實際會回（或自 Bridge 逐字轉出）的研究 reason：P0 契約的十七個加 Bridge 專屬的五個（見本節末）；`invalid_request`（輸入閘，400／422）是區域常數
    // （ResearchInputGates.INVALID_REQUEST）、不入本類別與契約表（先例 SiWriteGates）。契約原列的 `spec_digest_changed`（409）已被 D-72 的 `digest_mismatch`／`missing_digests`（422）取代、
    // Bridge 對研究端點不再回它，所以不再是本類別的常數（契約與前端已於 2026-11-03 勘誤落地移除它——契約〈勘誤記錄〉第 1、2 列；ResearchReasonsTest 以退役名單鎖住它不得再出現於後端、契約、前端任一處）。
    /** backend 或 Bridge 沒有設定研究寫入權杖（503）：研究寫入面整個停用。 */
    public static final String RESEARCH_WRITE_DISABLED = "research_write_disabled";
    /**
     * 403：Bridge 拒絕 backend 附的權杖（缺或錯），或 console-api 服務層角色檢查（OPERATOR 打換世代，D-64）。兩者是不同的擋下層
     * （前者在 Bridge 傳輸層，後者在 {@code ResearchCommandService} 入口），但共用同一個識別字。
     */
    public static final String RESEARCH_WRITE_FORBIDDEN = "research_write_forbidden";
    /** Bridge 沒有資料庫連線（503）：研究端點不降級成純檔案模式（能力探針除外：它仍回 200 並以 db=false 說明）。 */
    public static final String RESEARCH_REQUIRES_DB = "research_requires_db";
    /** 研究資料庫暫時不可用（503；stage run 進 BLOCKED_DB，復原後 outbox 重放）。 */
    public static final String RESEARCH_DB_BLOCKED = "db_blocked";
    /** 研究專案（或 allowlist 條目）不存在（404；「404 的 reason 省略」慣例的例外）。 */
    public static final String RESEARCH_NOT_FOUND = "research_not_found";
    /** slug 已被未封存的研究專案使用（409）。 */
    public static final String RESEARCH_SLUG_IN_USE = "slug_in_use";
    /** 同一研究專案已有進行中的 stage，或重試（reinit 不帶 generation）的狀態前置不成立——flowStatus 不是 FAILED（D-81）（409；details 由 Bridge 逐字帶出）。 */
    public static final String RESEARCH_STAGE_CONFLICT = "stage_conflict";
    /** PRD 存檔的 baseVersion 不是目前 head（409；details.headVersion）。 */
    public static final String RESEARCH_PRD_VERSION_CONFLICT = "prd_version_conflict";
    /** head 版本沒有通過的審查輪，不能核准（409）。 */
    public static final String RESEARCH_REVIEW_NOT_PASSED = "review_not_passed";
    /** 外環 FSM 現態不允許這個動作（409；details.current_state）。 */
    public static final String RESEARCH_FSM_STATE_CONFLICT = "fsm_state_conflict";
    /** 外環 FSM 在 ESCALATION*（409；details.recovery 帶恢復指令）。 */
    public static final String RESEARCH_ESCALATED = "escalated";
    /** 規格已於 Gate 0 凍結，不能再存 PRD 新版（409）。 */
    public static final String RESEARCH_SPEC_FROZEN = "spec_frozen";
    /** 建立請求勾了 industry 層，但 Web 層未啟用（400；Bridge 入口回 422，console-api 輸入閘回 400）。 */
    public static final String RESEARCH_LAYER_UNAVAILABLE = "layer_unavailable";
    /** 路徑或名稱沒有通過 Bridge 的安全檢查（422）。 */
    public static final String RESEARCH_SANITIZATION_FAILED = "sanitization_failed";
    /** Reddit 網域的 allowlist 條目沒有確認服務條款（422）。 */
    public static final String RESEARCH_TERMS_ACK_REQUIRED = "terms_ack_required";
    /** 研究呼叫連不上 Engine Bridge（502；連線階段失敗）：研究端點的專屬識別字，不同於既有端點的中文常數 {@link #BRIDGE_UNREACHABLE}。 */
    public static final String RESEARCH_BRIDGE_UNREACHABLE = "bridge_unreachable";
    /** 研究呼叫讀取逾時（504；POST 不重試，結果不明）。 */
    public static final String RESEARCH_BRIDGE_TIMEOUT = "bridge_timeout";

    // ── Bridge 專屬的五個 reason（契約 API_Contract_ResearchToPRD §0.2 第 5a／7a／7b／8a／8b 列與前端 RESEARCH_REASONS 已於 2026-11-03 勘誤落地列入——契約〈勘誤記錄〉第 1 列）──
    // 值逐字取自 Bridge（console-api 原樣透傳）；ResearchReasonsTest 以 22 個 P0 reason 做三方雙向鎖（後端常數＝前端 RESEARCH_REASONS＝契約 §0.2＝Architecture §11.1），任一處漏列即紅。
    /** allowlist 已有同 list_kind 與 host 的條目（409）。 */
    public static final String RESEARCH_ALLOWLIST_EXISTS = "allowlist_exists";
    /** 專案初始化的某一步失敗（Bridge 回 502；{@code details.step}＝workspace｜files｜fsm）：游標已標 FAILED，以重試初始化補建。 */
    public static final String RESEARCH_INIT_FAILED = "init_failed";
    /**
     * Bridge 端點本體尚未實作（Bridge 回 501；P1 起 Bridge 無觸發者——{@code stages/tcs-draft} 已實作，D-111 保留供 P2 骨架）：console-api 轉成上游失敗（<b>502</b>，主控裁決：上游未實作屬上游失敗類；
     * {@code details} 帶 Bridge 的 {@code endpoint}、{@code stage}、{@code detail} 與 {@code bridgeStatus=501}），不假裝成功。
     */
    public static final String RESEARCH_NOT_IMPLEMENTED = "not_implemented";
    /**
     * Gate 0 核准時，前端送來的檔案摘要與現檔不符（422；D-72）：只比對送來的鍵，{@code details.files[{key,expected,current}]}（{@code current} 為 null＝該檔不存在或不在
     * 凍結的四檔內）。取代契約原列的 409 {@code spec_digest_changed}。
     */
    public static final String RESEARCH_DIGEST_MISMATCH = "digest_mismatch";
    /**
     * Gate 0 核准一個摘要鍵都沒送（422；D-72，防止盲核）：console-api 的輸入閘單獨以它回（{@code details.violations}、零 Bridge 請求）；Bridge 端同名同義
     * （{@code details.accepted_keys} 列出可送的鍵）。
     */
    public static final String RESEARCH_MISSING_DIGESTS = "missing_digests";

    // ── P0 未結 R-2 的尾巴四個（ResearchToPRD P1 ⚖P1-25；契約 §0.2 勘誤補列；值逐字取自 Bridge 或 console-api 輸入閘）──
    /** 研究 stage 的 persona／playbook 編譯失敗（503；Bridge 逐字轉出）。 */
    public static final String RESEARCH_COMPILE_FAILED = "compile_failed";
    /** Bridge 的 SDD CLI 子行程失敗（502；Bridge 逐字轉出）。 */
    public static final String RESEARCH_SDD_CLI_FAILED = "sdd_cli_failed";
    /** FSM 狀態檔壞掉、讀不出來（422；Bridge 逐字轉出）。 */
    public static final String RESEARCH_FSM_STATE_UNREADABLE = "fsm_state_unreadable";
    /** 輸入閘或 Bridge 拒絕此請求（400／422；{@code details.violations[{field,rule,message}]}）：P0 的區域常數 {@code ResearchInputGates.INVALID_REQUEST} 改引用本常數。 */
    public static final String RESEARCH_INVALID_REQUEST = "invalid_request";

    // ── P1 新增的九個 reason（分流、SCR、拆解；IFACE §2、D-118 ⚖P1-25；Bridge 回的由 console-api 逐字轉出）──
    /** 此部署不支援分流（422；{@code details.missing[{item,reason}]}：git｜gh｜repo_writable｜scaffold_root｜scaffold_templates｜worktree_root｜gh_auth）。 */
    public static final String RESEARCH_ROUTE_UNSUPPORTED_IN_DEPLOYMENT = "route_unsupported_in_deployment";
    /** 軌道 A 的分支已存在（409；{@code details.branch}）。 */
    public static final String RESEARCH_BRANCH_EXISTS = "branch_exists";
    /** 軌道 B 的目標目錄非空（422；{@code details.path} 只回相對於 BRIDGE_SCAFFOLD_ROOT 的路徑）。 */
    public static final String RESEARCH_TARGET_NOT_EMPTY = "target_not_empty";
    /** PUBLIC 遠端須以 confirmRepoName 重述庫名確認（422）。 */
    public static final String RESEARCH_PUBLIC_CONFIRMATION_REQUIRED = "public_confirmation_required";
    /** 同一研究專案已有 PENDING、RUNNING 或 SUCCEEDED 的分流，或重試的前置不成立（409）。 */
    public static final String RESEARCH_ROUTE_CONFLICT = "route_conflict";
    /** 分流的某一步失敗（502；{@code details.failure_step}、{@code route_id}；該分流列已是 FAILED，游標 route／ROUTING／FAILED）。 */
    public static final String RESEARCH_ROUTE_STEP_FAILED = "route_step_failed";
    /** 有開啟中的 SCR（409）：內環唯讀，拆解觸發、TCS 草擬與內環 run 啟動皆被擋。 */
    public static final String RESEARCH_SCR_OPEN = "scr_open";
    /** 同一研究專案的 MINOR SCR 已達上限（409）。 */
    public static final String RESEARCH_SCR_LIMIT = "scr_limit";
    /** 拆解綁定的 PRD 摘要與現行凍結摘要不符（409；{@code details.expected_sha256}、{@code actual_sha256}）。 */
    public static final String RESEARCH_DECOMPOSITION_STALE = "decomposition_stale";
    /** Release Tag 名稱已存在（409；P2 交付 {@code :tag}，Bridge 回、console-api 原樣透傳）。 */
    public static final String RESEARCH_TAG_EXISTS = "tag_exists";
    /** 交付的某一步失敗（502；{@code details.failure_step}；Bridge 回、console-api 原樣透傳）。 */
    public static final String RESEARCH_DELIVERY_STEP_FAILED = "delivery_step_failed";

    // ── 研究來源單一化（登記）reason 家族（TCS-ResearchRegistry；契約 API_Contract_ResearchToPRD §5A.5；前端住 lib/domain/researchRegistry.ts 的 RESEARCH_REGISTRY_REASONS）──
    // 🔴 刻意不以 RESEARCH_ 為前綴：ResearchReasonsTest 以 RESEARCH_ 前綴常數與前端 RESEARCH_REASONS 做集合全等並逐項要求 Architecture §11.1 列出，
    // 加入它們須連動重凍多把鍵；獨立家族讓既有鎖零改動（SI_ 先例同型）。後端常數＝前端 RESEARCH_REGISTRY_REASONS＝契約 §5A.5 三處集合相等。
    /** 追蹤來源 slug 已存在（409；slug 永不重用，含已停用者；{@code details.slug}；Bridge 回、console-api 逐字透傳）。 */
    public static final String REGISTRY_WATCH_SOURCE_EXISTS = "watch_source_exists";
    /** 追蹤來源的 host 不在有效網域清單（422；{@code details.host}；Bridge 回、逐字透傳）。 */
    public static final String REGISTRY_HOST_NOT_ALLOWED = "host_not_allowed";
    /** 登記快照或稽核檔超過上限（422；{@code details.what}＝{@code registry_text}｜{@code audit_file}、{@code limit}、{@code size}）。 */
    public static final String REGISTRY_TOO_LARGE = "registry_too_large";
}
