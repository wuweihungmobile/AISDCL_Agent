/**
 * 專案 6／目標 5／任務 11／匯入記錄 6 個狀態的中文標籤與顏色——全站單一出處（設計稿 README〈狀態 enum〉；
 * 匯入記錄的六態在設計稿沒有定稿，標籤與顏色由本檔決定，契約 §1.1 只定義狀態值）。
 * Phase 4～5 補：執行批次 RunStatus（含 Bridge 過渡態的顯示）、審核項 ReviewKind／決定、步驟事件、告警嚴重度與規則、日誌等級色。
 * 顏色一律引用設計 token（styles/tokens.css），不寫死色碼：
 *   #7A8775＝--color-text-muted　#80B155＝--color-secondary　#498428＝--color-primary
 *   #D35B58＝--color-error　#A6B0A1＝--color-disabled-text　#F5A623＝--color-warning　#E55B3C＝--color-accent
 * （lib/domain/status.test.ts 解析 token 檔後逐一核對成設計稿的色碼。）
 * 偏離只有三格：--color-text-muted（#5F6B5A）、--color-accent（#B93F22）、--color-error（#B8433F）為了 WCAG AA 對比，
 * 在 styles/tokens.console.css 的「無障礙覆寫」一節改深（W5 C-18；原因與數字見該檔）。
 */
import type {
  AlertRule,
  AlertSeverity,
  BridgeRunStatus,
  EngineCapabilities,
  EngineCapabilityState,
  ExecutionStepStatus,
  GoalStatus,
  ImportStatus,
  ProjectStatus,
  ReviewDecision,
  ReviewKind,
  RunStatus,
  TaskStatus,
} from "@/lib/api/types";

export type StatusMeta = {
  /** 繁體中文標籤 */
  label: string;
  /** CSS 顏色（token 的 var() 引用），可直接用在 style.background／color */
  color: string;
};

const MUTED = "var(--color-text-muted)";
const SECONDARY = "var(--color-secondary)";
const PRIMARY = "var(--color-primary)";
const ERROR = "var(--color-error)";
const DISABLED = "var(--color-disabled-text)";
const WARNING = "var(--color-warning)";
const ACCENT = "var(--color-accent)";

export const PROJECT_STATUS: Record<ProjectStatus, StatusMeta> = {
  DRAFT: { label: "草稿", color: MUTED },
  READY: { label: "就緒", color: SECONDARY },
  EXECUTING: { label: "執行中", color: PRIMARY },
  COMPLETED: { label: "完成", color: PRIMARY },
  FAILED: { label: "失敗", color: ERROR },
  ARCHIVED: { label: "封存", color: DISABLED },
};

export const GOAL_STATUS: Record<GoalStatus, StatusMeta> = {
  PENDING: { label: "待處理", color: DISABLED },
  IN_PROGRESS: { label: "進行中", color: PRIMARY },
  COMPLETED: { label: "完成", color: PRIMARY },
  FAILED: { label: "失敗", color: ERROR },
  SKIPPED: { label: "跳過", color: DISABLED },
};

export const TASK_STATUS: Record<TaskStatus, StatusMeta> = {
  PENDING: { label: "待處理", color: DISABLED },
  QUEUED: { label: "排程中", color: SECONDARY },
  BLOCKED: { label: "阻塞", color: WARNING },
  RUNNING: { label: "執行中", color: PRIMARY },
  VALIDATING: { label: "驗證中", color: SECONDARY },
  COMPLETED: { label: "完成", color: PRIMARY },
  FAILED: { label: "失敗", color: ERROR },
  ESCALATED: { label: "待人工", color: ACCENT },
  PAUSED: { label: "暫停", color: MUTED },
  SKIPPED: { label: "跳過", color: DISABLED },
  CANCELLED: { label: "取消", color: DISABLED },
};

/**
 * 匯入記錄（契約 §1.1 狀態機）：UPLOADED→PARSING→PARSED→REVIEWING→IMPORTED／REJECTED；解析失敗退回 UPLOADED。
 * 顏色語意：灰＝還沒動作；淺綠＝進行中；黃＝等人工審核；主色＝完成；淡灰＝已放棄。
 */
export const IMPORT_STATUS: Record<ImportStatus, StatusMeta> = {
  UPLOADED: { label: "已上傳", color: MUTED },
  PARSING: { label: "解析中", color: SECONDARY },
  PARSED: { label: "已解析", color: WARNING },
  REVIEWING: { label: "審核中", color: WARNING },
  IMPORTED: { label: "已匯入", color: PRIMARY },
  REJECTED: { label: "已放棄", color: DISABLED },
};

/**
 * 執行批次（契約附錄 A.1；PRD §5.3.5 的六態，寫入 PG 的值域）。
 * PAUSING／CANCELLING 是 Bridge 的過渡態，console-api 折回 RUNNING、原值放 bridgeStatus（契約 §0.6）：
 * 顯示請用 runStatusMeta(status, bridgeStatus)，它會把「RUNNING＋PAUSING」標成「暫停中」。
 */
export const RUN_STATUS: Record<RunStatus, StatusMeta> = {
  INITIALIZING: { label: "啟動中", color: SECONDARY },
  RUNNING: { label: "執行中", color: PRIMARY },
  PAUSED: { label: "已暫停", color: WARNING },
  COMPLETED: { label: "已完成", color: PRIMARY },
  FAILED: { label: "失敗", color: ERROR },
  CANCELLED: { label: "已取消", color: DISABLED },
};

/** Bridge 過渡態在 RUNNING 底下的顯示（契約 §1.2.4～1.2.6：pause 回 RUNNING＋PAUSING、cancel 回 RUNNING＋CANCELLING）。 */
export const BRIDGE_TRANSITION: Partial<Record<BridgeRunStatus, StatusMeta>> = {
  PAUSING: { label: "暫停中", color: WARNING },
  CANCELLING: { label: "取消中", color: DISABLED },
};

/** 終態（SSE 送完該 status 之後伺服器關閉連線；重連已終態的 run 回 204；契約 §2.4）。 */
export const RUN_TERMINAL: readonly RunStatus[] = ["COMPLETED", "FAILED", "CANCELLED"];

export function isRunTerminal(status: string | undefined | null): boolean {
  return status === "COMPLETED" || status === "FAILED" || status === "CANCELLED";
}

/** 審核項種類（契約 §3.6.2；V3 的四種 CHECK，不擴充）。 */
export const REVIEW_KIND: Record<ReviewKind, StatusMeta> = {
  TASK_CONFIRM: { label: "確認任務", color: WARNING },
  GOAL_CONFIRM: { label: "確認目標", color: WARNING },
  GOAL_COMPLETED: { label: "目標完成審核", color: WARNING },
  ESCALATED: { label: "需人工介入", color: ACCENT },
};

/** 審核決定的按鈕文字（設計稿：通過／重試／跳過／拒絕）。 */
export const REVIEW_DECISION_LABEL: Record<ReviewDecision, string> = {
  APPROVE: "通過",
  RETRY: "重試",
  SKIP: "跳過",
  REJECT: "拒絕",
};

/** 設計稿四顆按鈕的固定順序：通過(solid)／重試／跳過／拒絕。 */
export const REVIEW_DECISION_ORDER: readonly ReviewDecision[] = ["APPROVE", "RETRY", "SKIP", "REJECT"];

/** 步驟事件狀態（契約 §1.2.7：Bridge 實際寫入的四種，沒有 IN_PROGRESS）。 */
export const STEP_STATUS: Record<ExecutionStepStatus, StatusMeta> = {
  STARTED: { label: "開始", color: SECONDARY },
  COMPLETED: { label: "完成", color: PRIMARY },
  FAILED: { label: "失敗", color: ERROR },
  RETRYING: { label: "重試", color: WARNING },
};

/** 告警嚴重度（持久化只用 WARNING／CRITICAL；SSE 另有 INFO，例如 RESTORE）。 */
export const ALERT_SEVERITY: Record<AlertSeverity | "INFO", StatusMeta> = {
  INFO: { label: "資訊", color: SECONDARY },
  WARNING: { label: "警告", color: WARNING },
  CRITICAL: { label: "嚴重", color: ERROR },
};

/**
 * 告警規則名稱是「文字」，放在告警底（--color-alert-bg）上：不能直接用上面狀態點的顏色
 * （WARNING 的 --color-warning 只有 1.9:1、INFO 的 --color-secondary 只有 2.3:1；DEF-AC-004），改用文字專用的深色。
 */
export function alertSeverityTextColor(severity: string): string {
  if (severity === "CRITICAL") return ERROR;
  if (severity === "WARNING") return "var(--color-warning-text)";
  if (severity === "INFO") return "var(--color-primary-strong)";
  return MUTED;
}

/** 告警規則名稱（PRD §5.4.4 六條＋引擎原生兩條；契約 §3.7）。 */
export const ALERT_RULE_LABEL: Record<AlertRule, string> = {
  TOKEN_BUDGET_WARNING: "Token 預算警告",
  TOKEN_BUDGET_EXCEEDED: "Token 預算超限",
  CONSECUTIVE_FAILURES: "連續任務失敗",
  AGENT_UNRESPONSIVE: "Agent 無回應",
  TASK_DURATION_EXCEEDED: "執行時間過長",
  HIGH_RETRY_RATE: "高重試率",
  ENGINE_ESCALATION: "引擎升級",
  ENGINE_TOKEN_HALT: "引擎 Token 停機",
};

/** 自治等級（PRD §5.3.2；Level 6～10 是 Advanced Autonomy）。 */
const AUTONOMY_NAMES: Record<number, string> = {
  1: "Manual Confirm",
  2: "Goal Confirm",
  3: "Review & Approve",
  4: "Exception Only",
  5: "Full Autonomy",
};

export function autonomyLabel(level: number): string {
  return `Level ${level} · ${AUTONOMY_NAMES[level] ?? "Advanced"}`;
}

const AUTONOMY_HINTS: Record<number, string> = {
  1: "每個任務執行前需人類確認",
  2: "每個目標開始前需人類確認",
  3: "自動執行；目標完成與任務失敗時需人類審核",
  4: "全自動執行，僅重試失敗後升級給人類",
  5: "全自動執行；任何失敗都升級給人類",
};

/**
 * 自治等級的一句說明。Level 6～10（契約 §3.6.1，v1.3 改寫）：審核閘行為同 Level 5；差異只在引擎能力旗標——
 * 等級 ≥ 6 要求自動突變、≥ 7 要求自演化，兩者都需要模型金鑰，沒有金鑰也不報錯，結果如實顯示在批次的引擎能力晶片。
 * （v1.2 的寫法是「目前不另傳給引擎」，已被推翻。）
 */
export function autonomyHint(level: number): string {
  return AUTONOMY_HINTS[level] ?? "進階自治：審核閘行為同 Level 5（只有失敗才升級給人類）；Level 6 以上另要求自動突變、Level 7 以上另要求自演化（都需要模型金鑰），實際結果見批次的引擎能力晶片";
}

/**
 * 引擎能力晶片（契約 §1.2.1、§3.4.2、§4.2 E-21；v1.3，D-11）：「自動突變」「自演化」各三態。
 * 值描述的是「這個批次 spawn 時 Console 實際送進引擎的」與「引擎因此會做的」，不是使用者設了什麼（兩者在 selfEvolution 上會不同）；
 * 文字、色調與 tooltip 由本表決定，契約只定義值域與語意。
 * 🔴 selfEvolution 的 ENABLED 必須讓人看得出「只提案、不自動套用」：引擎沒有演化開關，有金鑰就會在失敗型升級時由 Brain 產生演化提案，
 * 只寫進引擎日誌、不套用也不重載；所以等級 3、有金鑰的批次也會顯示「已啟用」，tooltip 要講清楚它與設定和等級無關。
 */
export type EngineCapabilityKey = keyof EngineCapabilities;
export type EngineCapabilityTone = "on" | "off" | "unavailable";
export type EngineCapabilityView = { text: string; hint: string; tone: EngineCapabilityTone };

/** 兩枚晶片的固定順序（契約 E-21：自動突變、自演化）。 */
export const ENGINE_CAPABILITY_KEYS: readonly EngineCapabilityKey[] = ["autoMutation", "selfEvolution"];

const ENGINE_CAPABILITY_TONE: Record<EngineCapabilityState, EngineCapabilityTone> = { ENABLED: "on", OFF: "off", UNAVAILABLE_NO_API_KEY: "unavailable" };

const ENGINE_CAPABILITY_TEXT: Record<EngineCapabilityKey, Record<EngineCapabilityState, { text: string; hint: string }>> = {
  autoMutation: {
    ENABLED: { text: "自動突變：已啟用", hint: "Brain 逐步校正：失敗步驟先由 Brain 改寫再重試（Brain 呼叫失敗則該步驟直接升級）" },
    OFF: { text: "自動突變：關閉", hint: "沒有啟用 Brain 逐步校正：失敗步驟照舊自動重試" },
    UNAVAILABLE_NO_API_KEY: { text: "自動突變：無金鑰不可用", hint: "有人要求 Brain 逐步校正（系統參數或自治等級 6 以上），但 Console 沒有金鑰可送：批次照常執行，只是沒有 Brain" },
  },
  selfEvolution: {
    ENABLED: { text: "自演化（僅提案）：已啟用", hint: "僅提案、不自動套用：引擎沒有演化開關，有金鑰時失敗型升級會由 Brain 產生演化提案，只寫進引擎日誌、不套用也不重載；與設定和自治等級無關" },
    OFF: { text: "自演化：關閉", hint: "沒有金鑰且沒人要求：沒有 AI 演化提案" },
    UNAVAILABLE_NO_API_KEY: { text: "自演化：無金鑰不可用", hint: "有人要求演化（系統參數或自治等級 7 以上），但沒有金鑰：AI 演化提案不會發生" },
  },
};

const ENGINE_CAPABILITY_NAME: Record<EngineCapabilityKey, string> = { autoMutation: "自動突變", selfEvolution: "自演化" };

/** 一枚晶片的文字、tooltip 與色調；後端若新增狀態值，顯示原值、用中性色，不崩潰。 */
export function engineCapabilityView(key: EngineCapabilityKey, state: string): EngineCapabilityView {
  const known = (ENGINE_CAPABILITY_TEXT[key] as Record<string, { text: string; hint: string }>)[state];
  if (!known) return { text: `${ENGINE_CAPABILITY_NAME[key]}：${state}`, hint: "", tone: "off" };
  return { ...known, tone: ENGINE_CAPABILITY_TONE[state as EngineCapabilityState] };
}

/**
 * 日誌等級顏色（設計稿監控頁：等級文字依等級著色、寬 48px）。
 * 這些是「文字」，列放在 bg-base 上，所以不能直接用狀態點的顏色（DEF-AC-004）：
 * INFO 用 primary-strong（bg-base 上 6.02:1；主色只有 4.22:1）、WARN 用 warning-text（5.49:1；warning 本色只有 1.87:1）。
 */
export const LOG_LEVEL_COLOR: Record<string, string> = {
  DEBUG: MUTED,
  INFO: "var(--color-primary-strong)",
  WARN: "var(--color-warning-text)",
  ERROR: ERROR,
  CRITICAL: ERROR,
};

const FALLBACK: StatusMeta = { label: "未知", color: MUTED };

/** 後端若新增狀態值，前端不至於崩潰：顯示原值、用灰點。 */
function lookup<K extends string>(table: Record<K, StatusMeta>, status: string): StatusMeta {
  return (table as Record<string, StatusMeta>)[status] ?? { ...FALLBACK, label: status || FALLBACK.label };
}

export const projectStatus = (status: string): StatusMeta => lookup(PROJECT_STATUS, status);
export const goalStatus = (status: string): StatusMeta => lookup(GOAL_STATUS, status);
export const taskStatus = (status: string): StatusMeta => lookup(TASK_STATUS, status);
export const importStatus = (status: string): StatusMeta => lookup(IMPORT_STATUS, status);
export const reviewKind = (kind: string): StatusMeta => lookup(REVIEW_KIND, kind);
export const stepStatus = (status: string): StatusMeta => lookup(STEP_STATUS, status);
export const alertSeverity = (severity: string): StatusMeta => lookup(ALERT_SEVERITY, severity);

/** 執行批次的顯示狀態：RUNNING＋Bridge 過渡態（PAUSING／CANCELLING）要顯示成「暫停中」「取消中」。 */
export function runStatusMeta(status: string, bridgeStatus?: string | null): StatusMeta {
  if (status === "RUNNING" && bridgeStatus && bridgeStatus in BRIDGE_TRANSITION) {
    return BRIDGE_TRANSITION[bridgeStatus as BridgeRunStatus] as StatusMeta;
  }
  return lookup(RUN_STATUS, status);
}

/** 專案列表的狀態 tab（設計稿：全部／草稿／就緒／執行中／完成／失敗；封存不列） */
export const PROJECT_STATUS_TABS: ReadonlyArray<{ id: "ALL" | ProjectStatus; label: string }> = [
  { id: "ALL", label: "全部" },
  { id: "DRAFT", label: "草稿" },
  { id: "READY", label: "就緒" },
  { id: "EXECUTING", label: "執行中" },
  { id: "COMPLETED", label: "完成" },
  { id: "FAILED", label: "失敗" },
];

/** 只有 FAILED／ESCALATED 的任務可以手動重試（後端同規則，其餘回 409）。 */
export function isRetryable(status: string): boolean {
  return status === "FAILED" || status === "ESCALATED";
}

/** 狀態點需要「呼吸」動畫的狀態（進行中的工作） */
export function isLive(status: string): boolean {
  return status === "EXECUTING" || status === "IN_PROGRESS" || status === "RUNNING" || status === "PARSING" || status === "INITIALIZING";
}

/**
 * 匯入記錄可以從歷史列表「重新開啟審核」的狀態（契約 §1.1 表）：
 * UPLOADED（尚未解析或解析失敗）、PARSED、REVIEWING 仍有下一步可做；
 * PARSING 進行中不開、IMPORTED／REJECTED 是終態。
 */
export function isImportReopenable(status: string): boolean {
  return status === "UPLOADED" || status === "PARSED" || status === "REVIEWING";
}
