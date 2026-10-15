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
export type ProjectDetail = S["ProjectDetailResponse"];
export type ProjectResponse = S["ProjectResponse"];
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
