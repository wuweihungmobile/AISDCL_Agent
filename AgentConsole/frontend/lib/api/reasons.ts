/**
 * 錯誤 `reason` 常數總表——前後端共用、逐字（契約 API_Contract_P3-6.md 附錄 B；§0.3 第 1 點）。
 *  - 後端集中在 ErrorReasons，前端集中在這支檔；兩邊字串逐字相同，E2E 以 reason 逐字比對。
 *  - 程式判斷一律用這裡的常數，不拿 message（給人看的動態句子）判斷，也不自己造英文代碼。
 *  - lib/api/reasons.test.ts 會解析契約附錄 B，雙向比對「契約有、這裡沒有」與「這裡有、契約沒有」。
 *  - 404 沿用 Phase 2：reason 省略、只有 message（樣板見附錄 B.3），所以沒有對應常數。
 */
export const REASONS = {
  // ── B.1 Phase 1+2 既有 ───────────────────────────────────────────────
  MALFORMED_REQUEST_BODY: "MALFORMED_REQUEST_BODY",
  UNAUTHENTICATED: "UNAUTHENTICATED",
  TOKEN_EXPIRED: "TOKEN_EXPIRED",
  TOKEN_INVALID: "TOKEN_INVALID",
  INVALID_CREDENTIALS: "INVALID_CREDENTIALS",
  INVALID_REFRESH_TOKEN: "INVALID_REFRESH_TOKEN",
  ACCESS_DENIED: "ACCESS_DENIED",
  ALREADY_SIGNED_OFF: "已 signoff",
  TASK_NOT_RETRYABLE: "目前狀態不可重試",
  TASK_RUNNING_NOT_DELETABLE: "RUNNING 狀態的任務不可刪除",
  COMMAND_FORBIDDEN_CHARS: "命令含禁用字元",
  DEPENDENCY_CYCLE: "依賴成環",

  // ── B.2 通用 ─────────────────────────────────────────────────────────
  RATE_LIMITED: "超過每分鐘 100 次請求上限",
  BRIDGE_UNREACHABLE: "引擎橋接服務無法連線",
  BRIDGE_TIMEOUT: "引擎橋接服務逾時",
  BRIDGE_ERROR: "引擎橋接服務錯誤",

  // ── B.2 匯入 ─────────────────────────────────────────────────────────
  IMPORT_NO_FILE: "未提供檔案",
  IMPORT_EMPTY_FILE: "檔案是空的",
  IMPORT_FILE_TOO_LARGE: "檔案超過 10MB 上限",
  IMPORT_UNSUPPORTED_EXTENSION: "只支援 .md／.pdf／.docx 檔案",
  IMPORT_CONTENT_MISMATCH: "檔案內容與副檔名不符",
  IMPORT_NOT_UTF8: "檔案不是有效的 UTF-8 文字",
  IMPORT_PDF_ENCRYPTED: "PDF 已加密，無法擷取文字",
  IMPORT_FILE_CORRUPT: "檔案已損毀，無法讀取",
  IMPORT_NO_TEXT: "無法從檔案擷取文字",
  IMPORT_PARSING_IN_PROGRESS: "解析中，請稍候",
  IMPORT_SIGNED_OFF_NO_REPARSE: "已 signoff，不可重新解析",
  IMPORT_STATE_NOT_ALLOWED: "匯入記錄狀態不允許此操作",
  IMPORT_GATE_REJECTED: "解析結果未通過有界閘",
  IMPORT_SDD_SPEC_REJECTED: "SDD 規格檢查未通過",
  IMPORT_DRAFT_EXPIRED: "草案已失效，請重新解析",
  IMPORT_NOT_SIGNED_OFF: "草案尚未 signoff，不可確認匯入",
  IMPORT_ALREADY_IMPORTED: "已匯入",

  // ── B.2 執行（W4-F2 使用；集中放這裡，避免兩棒各造一份）──────────────────────
  EXEC_UNSIGNED_DRAFT: "未經人工審批的草案不可執行",
  EXEC_PROJECT_RUNNING: "專案正在執行中",
  EXEC_PROJECT_STATE_NOT_ALLOWED: "專案狀態不允許執行",
  EXEC_SCOPE_INVALID: "所選範圍不合法",
  EXEC_SCOPE_ALREADY_COMPLETED: "所選任務或目標已完成",
  EXEC_SCOPE_MISSING_DEPENDENCIES: "所選目標依賴未完成的前置目標",
  EXEC_NO_RUNNABLE_TASKS: "沒有可執行的任務",
  EXEC_PROMPT_TOO_LONG: "步驟 prompt 超過 20000 字元上限",
  EXEC_EVALUATOR_FORBIDDEN_CHARS: "評估指令含禁用字元",
  EXEC_EVALUATOR_NOT_WHITELISTED: "評估指令不在可執行檔白名單",
  EXEC_REGEX_INVALID: "expectedOutputRegex 無法編譯",
  EXEC_TOO_MANY_TASKS: "範圍任務數超過單一批次上限 500",
  EXEC_MAX_RETRIES_EXCEEDED: "任務最大重試次數超過上限 20",
  EXEC_PATH_LOCKED: "同專案同路徑已有執行中的批次",
  EXEC_ENGINE_REJECTED: "引擎拒絕此請求",
  EXEC_RUN_STATE_NOT_ALLOWED: "目前執行狀態不允許此操作",
  EXEC_NO_CHECKPOINT: "找不到可續跑的 checkpoint",
  EXEC_RUN_GONE: "引擎端已無此執行（工作區可能已清除）",
  EXEC_ONLY_LATEST_RUN: "只能還原專案最新的執行批次",
  EXEC_REVIEW_ALREADY_DECIDED: "審核項已處理",
  EXEC_DECISION_NOT_ALLOWED: "此審核項不允許該決定",

  // ── B.2 監控 ─────────────────────────────────────────────────────────
  MONITOR_RANGE_INVALID: "時間範圍不合法",
  MONITOR_REPORT_FORMAT_UNSUPPORTED: "不支援的報表格式",
  MONITOR_PDF_NOT_READY: "PDF 報表尚未提供（W5）",

  // ── B.2 設定 ─────────────────────────────────────────────────────────
  SETTINGS_REVEAL_ADMIN_ONLY: "僅 ADMIN 可揭露敏感參數",
  SETTINGS_VALUE_INVALID: "參數值不符合型別或驗證規則",
  SETTINGS_TOKEN_GUARD_ORDER: "halt_threshold_pct 必須大於 compact_threshold_pct",
  SETTINGS_URL_REJECTED: "目標位址未通過 SSRF／allowlist 檢查",
  SETTINGS_UPDATE_NEEDS_CONFIRM: "敏感參數更新需二次確認（confirm=true）",
  SETTINGS_RESET_NEEDS_CONFIRM: "敏感參數重置需二次確認（confirm=true）",
  SETTINGS_FILE_MALFORMED: "設定檔格式錯誤",
  SETTINGS_FILE_TOO_LARGE: "設定檔超過 1MB 上限",
  SETTINGS_FILE_NOT_JSON: "只接受 JSON 設定檔",
} as const;

export type Reason = (typeof REASONS)[keyof typeof REASONS];

/**
 * 附錄 B.2「設定」列：`目標位址未通過 SSRF／allowlist 檢查` 的 details.violation 值域，
 * 對應給人看的中文（前端顯示用；鍵是契約的逐字常數）。
 */
export const URL_VIOLATION_LABEL: Record<string, string> = {
  malformed_url: "網址格式不正確",
  scheme: "只允許 http／https",
  userinfo: "網址不得含帳號密碼",
  loopback: "不可連到本機（loopback）位址",
  link_local: "不可連到 link-local 位址",
  private_ip: "不可連到私有網段位址",
  not_in_allowlist: "主機不在允許清單（allowlist）內",
  dns_rebinding: "網域名稱解析到內網位址（DNS rebinding）",
};
