/**
 * 領域型別別名：一律取自 openapi-typescript 產生的 schema.d.ts（單一出處），
 * 元件與 hooks 不直接碰 components["schemas"][...] 這種長字串。
 */
import type { components } from "./schema";
import type { components as components36 } from "./schema-p3-6";

type S = components["schemas"];
/** Phase 3～6 契約（openapi-p3-6.yaml 產生的 schema-p3-6.d.ts）；匯入、通知摘要、系統參數的型別住這裡 */
type S36 = components36["schemas"];

export type ProjectSummary = S["ProjectSummaryResponse"];
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

/** 六個設定分類（順序＝契約：model,agent,execution,monitor,autoclaude,sdd） */
export const CONFIG_CATEGORIES: readonly ConfigCategory[] = [
  "model",
  "agent",
  "execution",
  "monitor",
  "autoclaude",
  "sdd",
];

/** 設定修改歷史查詢參數（key 須與 category 併用，單獨給 key 後端回 400） */
export type ListSettingsHistoryParams = {
  category?: ConfigCategory;
  key?: string;
  page?: number;
  size?: number;
};
