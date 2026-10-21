/**
 * 領域型別別名：一律取自 openapi-typescript 產生的 schema.d.ts（單一出處），
 * 元件與 hooks 不直接碰 components["schemas"][...] 這種長字串。
 */
import type { components } from "./schema";
import type { components as components36 } from "./schema-p3-6";

type S = components["schemas"];
/** Phase 3～6 契約（openapi-p3-6.yaml 產生的 schema-p3-6.d.ts）；匯入、通知摘要、系統參數的型別住這裡 */
type S36 = components36["schemas"];

/** 專案列表項；`deletedAt` 是 v1.2（C-3）新增：只有 `GET /projects?deleted=true` 的列表項帶值，其餘缺席。 */
export type ProjectSummary = S["ProjectSummaryResponse"] & Pick<S36["ProjectSummaryResponse"], "deletedAt">;
/**
 * 專案詳情與專案回應：v1.5（整合輪 115；契約 §1.10.5、API-PRJ-07）新增 SDD 綁定三欄 `sddProject`／`sddSpecDir`／`sddSpecFile`
 * （皆 string｜null，null 與缺席等價；`ProjectSummaryResponse` 不帶）。Phase 1+2 的 schema.d.ts 由後端 /v3/api-docs 產生、尚未含這三欄，
 * 所以從契約產生的 schema-p3-6.d.ts 借這三欄（同 ProjectSummary 借 deletedAt 的做法）。
 */
export type ProjectDetail = S["ProjectDetailResponse"] & Pick<S36["ProjectDetailResponse"], "sddProject" | "sddSpecDir" | "sddSpecFile">;
export type ProjectResponse = S["ProjectResponse"] & Pick<S36["ProjectResponse"], "sddProject" | "sddSpecDir" | "sddSpecFile">;
export type GoalBrief = S["GoalBrief"];
export type GoalSummary = S["GoalSummaryResponse"];
export type GoalDetail = S["GoalDetailResponse"];
export type GoalResponse = S["GoalResponse"];
export type TaskBrief = S["TaskBrief"];
export type TaskSummary = S["TaskSummaryResponse"];
export type TaskDetail = S["TaskDetailResponse"];
export type TaskResponse = S["TaskResponse"];
export type ExecutionStepBrief = S["ExecutionStepBrief"];
export type TokenResponse = S["TokenResponse"];
export type FieldError = S["FieldError"];

export type CreateProjectRequest = S["CreateProjectRequest"];
export type UpdateProjectRequest = S["UpdateProjectRequest"];
export type CreateGoalRequest = S["CreateGoalRequest"];
export type UpdateGoalRequest = S["UpdateGoalRequest"];
export type CreateTaskRequest = S["CreateTaskRequest"];
export type UpdateTaskRequest = S["UpdateTaskRequest"];
export type ReorderRequest = S["ReorderRequest"];

export type ProjectStatus = ProjectSummary["status"];
export type GoalStatus = GoalSummary["status"];
export type TaskStatus = TaskSummary["status"];

/** 分頁資料（PRD §7.2；content／page／size／totalElements／totalPages；page 從 0 起算） */
export type PageData<T> = {
  content: T[];
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
};

export type Role = "ADMIN" | "OPERATOR" | "VIEWER";

/** 專案列表查詢參數（對應後端 GET /api/v1/projects） */
export type ListProjectsParams = {
  page?: number;
  size?: number;
  q?: string;
  status?: ProjectStatus;
  /** 欄位[,asc|desc]；欄位白名單 name／status／createdAt／updatedAt */
  sort?: string;
  /** true＝只列軟刪除的專案（v1.2，C-3；OPERATOR 以上，VIEWER 回 403）；省略／false＝只列未刪除者 */
  deleted?: boolean;
};

// ── Phase 3：BRD/PRD 匯入（契約 §1.1）────────────────────────────────────
export type ImportStatus = S36["ImportStatus"];
export type ImportSourceType = S36["ImportSourceType"];
export type ParsePath = S36["ParsePath"];
export type ImportRecord = S36["ImportRecordResponse"];
export type ImportRecordDetail = S36["ImportRecordDetailResponse"];
export type ParseResult = S36["ParseResultResponse"];
export type ParsedResult = S36["ParsedResult"];
export type ParsedProject = S36["ParsedProject"];
export type ParsedGoal = S36["ParsedGoal"];
export type ParsedTask = S36["ParsedTask"];
export type ParseOptions = S36["ParseOptions"];
export type ParseWarning = S36["ParseWarning"];
export type GateError = S36["GateError"];
export type GateName = S36["GateName"];
export type TextImportRequest = S36["TextImportRequest"];
export type EditParsedResultRequest = S36["EditParsedResultRequest"];

/** 匯入歷史查詢參數（對應後端 GET /api/v1/import；sort 欄位限 createdAt／status） */
export type ListImportsParams = {
  page?: number;
  size?: number;
  status?: ImportStatus;
  q?: string;
  sort?: string;
};

// ── 通知摘要（契約 §1.4）──────────────────────────────────────────────────
export type NotificationSummary = S36["NotificationSummaryResponse"];

// ── v1.4（W7 第二批）：待審批清單（§1.8.1，D-18）、AISDLC_SDD 引擎狀態（§1.7.1，D-16）、登出（§1.9.1，D-19）────
/** 待簽核草案的種類：專案、目標、任務、匯入記錄（判準與通知摘要的 pendingSignoffs 完全相同）。 */
export type PendingSignoffKind = S36["PendingSignoffKind"];
export type PendingSignoffItem = S36["PendingSignoffItem"];
/** `total` 恆等於通知摘要的 `pendingSignoffs`；`limit` 不影響它。 */
export type PendingSignoffCounts = S36["PendingSignoffCounts"];
export type PendingSignoffs = S36["PendingSignoffsResponse"];
/** `GET /engines/sdd` 的 data：引擎不可用也回 200，以 `available`／`reason` 判斷（回應欄位的值，不是 ApiError.reason）。 */
export type SddEngineStatus = S36["SddEngineStatusResponse"];
export type SddEngineReason = S36["SddEngineReason"];
export type SddVersion = S36["SddVersion"];
export type SddProjectEntry = S36["SddProjectEntry"];
export type SddFsmState = S36["SddFsmState"];
export type SddHumanPending = S36["SddHumanPending"];
export type LogoutRequest = S36["LogoutRequest"];

// ── v1.5（整合輪 115）：SDD 治理（契約 §1.10；API-SGN-06、API-PRJ-08、API-EXE-15／16、API-ENG-02）─────────────────
/** FSM 階段資訊（§3.1.5、§4.7.3）：`name` 的主路徑值 order 1～8，非主路徑（BLOCKED／TRANSIENT／OBSERVATION／UNKNOWN）order 為 0；日後新增的 name 要原樣顯示。 */
export type SddFsmPhase = S36["SddFsmPhase"];
/** ESCALATION 的恢復指令（Bridge 組字；Console 原樣顯示、不得自行組字，§1.10.4、§4.7.3）。 */
export type SddRecovery = S36["SddRecovery"];
/** 核准凍結的請求本文（§1.10.2）：approver 一律取 JWT subject，不在請求內；沒有 `binding` 欄。 */
export type SddFreezeRequest = S36["SddFreezeRequest"];
/** 編輯專案的 FSM 專案（§1.10.7）：`sddProject` 為 null＝清除、回到「用預設」（專案名）。 */
export type SddBindingRequest = S36["SddBindingRequest"];
/** 執行追溯覆蓋（§1.10.3；諮詢視圖，`advisory` 恆為 true）。 */
export type ExecutionRtm = S36["ExecutionRtmResponse"];
export type RtmAtCoverage = S36["RtmAtCoverage"];
export type RtmAcCoverage = S36["RtmAcCoverage"];
/** execute 的 201 的警告項（§1.10.6）：`code`／`cause` 日後新增的值要原樣顯示、不崩潰。 */
export type ExecutionWarning = S36["ExecutionWarning"];

// ── Phase 6：系統參數（契約 §1.5）─────────────────────────────────────────
export type Config = S36["ConfigResponse"];
export type ConfigCategory = Config["category"];
export type ConfigValueType = S36["ConfigValueType"];
export type ConfigEffect = S36["ConfigEffect"];
export type UpdateConfigRequest = S36["UpdateConfigRequest"];
export type TokenGuardRequest = S36["TokenGuardRequest"];
export type TestConnectionRequest = S36["TestConnectionRequest"];
export type ConnectionTestResult = S36["ConnectionTestResponse"];
export type ConfigHistory = S36["ConfigHistoryResponse"];
export type SettingsExportDocument = S36["SettingsExportDocument"];
export type ImportSettingsResult = S36["ImportSettingsResponse"];
export type ImportSettingsError = S36["ImportSettingsError"];

// ── Phase 4：專案執行（契約 §1.2）────────────────────────────────────────
export type RunStatus = S36["RunStatus"];
/** Bridge 的八態（PAUSING／CANCELLING 是過渡態，console-api 寫 PG 時折回 RUNNING，原值在 bridgeStatus） */
export type BridgeRunStatus = S36["BridgeRunStatus"];
export type ExecutionScope = S36["ExecutionScope"];
export type ScopeMode = S36["ScopeMode"];
export type StartExecutionRequest = S36["StartExecutionRequest"];
export type ExecutionRun = S36["ExecutionRunResponse"];
export type ExecutionRunSummary = S36["ExecutionRunSummaryResponse"];
export type ExecutionRunDetail = S36["ExecutionRunDetailResponse"];
export type CurrentStep = S36["CurrentStep"];
export type BridgeInfo = S36["BridgeInfo"];
/** 引擎行程樹的資源取樣（v1.3，D-12；契約 §1.2.3、§3.1.2）：只在 `GET /executions/{runId}` 的 `bridge.resources`，沒有資料時為 null 或缺席。 */
export type ResourceUsage = S36["ResourceUsage"];
/** 批次 spawn 時 Console 實際送進引擎的能力狀態（v1.3，D-11；契約 §1.2.1、§3.4.2）：建立時凍結，V10 之前的批次缺席或 null。 */
export type EngineCapabilities = S36["EngineCapabilities"];
export type EngineCapabilityState = S36["EngineCapabilityState"];
export type ExecutionStep = S36["ExecutionStepResponse"];
export type ExecutionStepStatus = S36["ExecutionStepStatus"];
export type Dag = S36["DagResponse"];
export type DagNode = S36["DagNode"];
export type DagEdge = S36["DagEdge"];
export type Checkpoint = S36["CheckpointResponse"];
export type ReviewKind = S36["ReviewKind"];
export type ReviewStatus = S36["ReviewStatus"];
export type ReviewDecision = S36["ReviewDecision"];
export type ReviewItem = S36["ReviewRequestResponse"];
export type ReviewBody = S36["ReviewRequest"];

/** 專案的執行批次列表查詢參數（契約 §1.2.2；sort 欄位限 startedAt／runNumber） */
export type ListExecutionsParams = {
  page?: number;
  size?: number;
  status?: RunStatus;
  sort?: string;
};

/** 步驟分頁查詢參數（契約 §1.2.7；afterSeq 是「嚴格大於」的事件 seq） */
export type ListStepsParams = {
  page?: number;
  size?: number;
  afterSeq?: number;
};

// ── Phase 5：專案監控（契約 §1.3）────────────────────────────────────────
export type ProjectMetrics = S36["ProjectMetricsResponse"];
export type MetricValue = S36["MetricValue"];
export type TaskDurationItem = S36["TaskDurationItem"];
export type RetryBucket = S36["RetryBucket"];
export type TokenTrendPoint = S36["TokenTrendPoint"];
export type TaskTrendPoint = S36["TaskTrendPoint"];
export type Alert = S36["AlertResponse"];
export type AlertRule = S36["AlertRule"];
export type AlertSeverity = S36["AlertSeverity"];
export type LogEntry = S36["LogEntryResponse"];
export type LogLevel = S36["LogLevel"];
export type LogSource = S36["LogSource"];
export type TrendBucket = "HOUR" | "DAY";

/** 監控各端點共通的視窗參數（契約 §1.3；from／to 為帶 offset 的 ISO-8601，缺省＝to 之前 24 小時～現在） */
export type MonitorRangeParams = {
  runId?: string;
  from?: string;
  to?: string;
};

export type MonitorTrendParams = MonitorRangeParams & { bucket?: TrendBucket };

/** 全域任務總計（契約 §1.3.8，v1.2，C-1）：跨全部未封存且未軟刪除的專案，視窗內各狀態的步驟列數，不分桶。 */
export type TaskTotals = S36["TaskTotalsResponse"];
/** from 必填（帶 offset 的 ISO-8601）；to 省略＝現在；to−from 不可超過 92 天，否則 400 `時間範圍不合法`。 */
export type TaskTotalsParams = { from: string; to?: string };

export type ListAlertsParams = {
  runId?: string;
  acknowledged?: boolean;
  limit?: number;
};

export type ListLogsParams = MonitorRangeParams & {
  level?: "ALL" | "INFO" | "WARN" | "ERROR";
  taskId?: string;
  q?: string;
  order?: "asc" | "desc";
  page?: number;
  size?: number;
};

export type ReportParams = MonitorRangeParams & { format?: "csv" | "pdf" };

// ── SSE 事件資料（契約 §2；data 是單行 JSON）──────────────────────────────
export type LogEventData = S36["LogEventData"];
export type StatusChangeEventData = S36["StatusChangeEventData"];
export type ReviewRequestEventData = S36["ReviewRequestEventData"];
export type AlertEventData = S36["AlertEventData"];
export type ProgressUpdateEventData = S36["ProgressUpdateEventData"];
export type TokenUpdateEventData = S36["TokenUpdateEventData"];
export type MetricUpdateEventData = S36["MetricUpdateEventData"];

/** 六個設定分類（順序＝契約：model,agent,execution,monitor,autoclaude,sdd） */
export const CONFIG_CATEGORIES: readonly ConfigCategory[] = ["model", "agent", "execution", "monitor", "autoclaude", "sdd"];

/** 設定修改歷史查詢參數（key 須與 category 併用，單獨給 key 後端回 400） */
export type ListSettingsHistoryParams = {
  category?: ConfigCategory;
  key?: string;
  page?: number;
  size?: number;
};

// ── SelfImproving 唯讀鏡像（P1b；TCS-SelfImprovingMirror-P1b R9、R11）──────────────────────
// 後端 `GET /api/v1/si/**` 原樣轉出根層 `si export` 的物件（只經欄名 snake_case→camelCase 對映；值一律不動，null 保留），
// 所以 schema.d.ts 只有「任意物件」，欄位形狀以這裡為準（出處：SelfImproving PRD §9.2〈export --json 輸出〉與入庫的黃金檔）。
// 日後根層加欄位時：已知欄位不受影響，不認得的欄位原樣保留在物件上（狀態橫幅的 `si-status-extra` 會顯示）。
/** `export --kind` 的五個值（Bridge 封閉集合）。 */
export type SiKind = "observations" | "events" | "proposals" | "runs" | "status";

/** `ne[]` 的一項：該欄位量不到（NOT-EVALUABLE）與原因，不得顯示成 0、無或通過。 */
export type SiNeEntry = { field: string; reason: string };
/** `problems[]` 的一項（例：壞列 ROW-ARITY）。 */
export type SiProblem = { subject: string; code: string; detail: string };

/** 每個 `export` 回應的外層；`items` 的元素形狀依 kind 而異。 */
export type SiPage<T> = {
  schemaRev: number;
  kind: SiKind;
  /** 子行程的產生時間（Bridge 的值，不是 backend 或瀏覽器時鐘）；時間窗的錨點 */
  generatedAt: string;
  /** git 不可用時為 null（同時 `ne` 有 `head_sha` 一項） */
  headSha: string | null;
  items: T[];
  /** 游標：下一頁的 `since`（嚴格大於）；末頁為 null */
  nextSince: number | null;
  truncated: boolean;
  ne: SiNeEntry[];
  problems: SiProblem[];
};

/** 觀察帳本的一列（九欄；`marks` 是原字串，`marksKv` 是解析後的鍵值，`line` 是帳本檔的行號）。 */
export type SiObservation = {
  id: string;
  time: string;
  context: string;
  symptom: string;
  evidence: string;
  category: string;
  severity: string;
  disposition: string;
  marks: string;
  marksKv: Record<string, string>;
  line: number;
  /** 模組桶：根層 P2 才有；缺席時前端不得自行推算（R17） */
  buckets?: string[];
  valid?: true;
};
/** 無法解析的帳本列（例：欄數不足）：只有行號與原文，永遠顯示、不受篩選影響。 */
export type SiInvalidRow = { line: number; raw: string; valid: false };
export type SiObservationRow = SiObservation | SiInvalidRow;

/** 事件帳本的一筆：`seq`／`t`／`kind`／`by` 是共同欄，其餘依 `kind` 而異（原樣保留）。 */
export type SiEvent = { seq: number; t: string; kind: string; by: string } & Record<string, unknown>;

export type SiProposal = {
  id: string;
  state: string;
  route: string;
  cls: string;
  action: string;
  run: string;
  rev: number;
  digest: string;
  target: string[];
  /** 本提案的 rN.patch 觸及的檔案；patch 讀不到或無法解析時為 null（量不到，根層 export 不附 ne 項），不是空集合 `[]`（R16） */
  touched: string[] | null;
  /** touched 的個數；touched 為 null 時同為 null（不是 0） */
  touchedCount: number | null;
  sources: string[];
  createdSeq: number;
  lastSeq: number;
  verdict: unknown;
  flags: unknown[];
  cooldown: unknown;
  /** `si card` 的逐字輸出；量不到時為 null（同時 `ne` 有對應項） */
  card: string | null;
};

export type SiRun = {
  id: string;
  openedSeq: number;
  closedSeq: number | null;
  trigger: string;
  headSha: string | null;
  research: { kind: string; seq: number } | null;
  propIds: string[];
  outcome: Record<string, string>;
};

/** `status` 的單一項（`items[0]`）；已知鍵見 SI_STATUS_KNOWN_KEYS，其餘鍵（如日後的 consolePending）原樣保留。 */
export type SiStatusItem = {
  eventsDetected: Array<{ trigger: string; subject: string; detail: string }>;
  unavailable: Array<{ trigger: string; reason: string }>;
  openRuns: unknown[];
  pendingProps: Array<{ id: string; rev: number; state: string; route: string; digest8: string }>;
  suspended: unknown;
  cooldowns: unknown[];
  skipReasons: Record<string, unknown>;
  /** 量不到時是 `{ status: "NOT-EVALUABLE", reason }` 物件 */
  capacity: unknown;
  frictionReconcile: unknown;
} & Record<string, unknown>;

/** 清單查詢的參數：`since` 為嚴格大於的游標（整數 ≥0）、`limit` 為整數 ≥1；undefined 不進網址。 */
export type SiListParams = { since?: number; limit?: number };
