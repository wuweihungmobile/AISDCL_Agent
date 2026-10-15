/**
 * 每個後端端點一個函式；名稱對應 PRD §7.1（API-PRJ／GOL／TSK／SGN／AUTH／IMP／SET／NTF）。
 * 型別來自 schema.d.ts（Phase 1+2）與 schema-p3-6.d.ts（Phase 3～6，依契約 openapi-p3-6.yaml 產生）；
 * 這裡不做快取、不碰 React，快取與失效策略在 lib/api/queries.ts（TanStack Query）。
 * Phase 3～6 的函式名取契約 YAML 的 operationId。
 */
import { apiDownload, apiRequest, type DownloadResult } from "./client";
import type {
  Config,
  ConfigCategory,
  ConfigHistory,
  ConnectionTestResult,
  CreateGoalRequest,
  CreateProjectRequest,
  CreateTaskRequest,
  GoalDetail,
  GoalResponse,
  GoalSummary,
  ImportRecord,
  ImportRecordDetail,
  ImportSettingsResult,
  ListImportsParams,
  ListProjectsParams,
  ListSettingsHistoryParams,
  NotificationSummary,
  PageData,
  ParseOptions,
  ParseResult,
  ParsedResult,
  ProjectDetail,
  ProjectResponse,
  ProjectSummary,
  TaskDetail,
  TaskResponse,
  TaskSummary,
  TestConnectionRequest,
  TextImportRequest,
  TokenGuardRequest,
  TokenResponse,
  UpdateConfigRequest,
  UpdateGoalRequest,
  UpdateProjectRequest,
  UpdateTaskRequest,
} from "./types";

type Opts = { signal?: AbortSignal };

// ── 認證（API-AUTH-01／02）──────────────────────────────────────────────
export function login(username: string, password: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
}

export function refreshToken(refreshTokenValue: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/api/v1/auth/refresh", {
    method: "POST",
    body: { refreshToken: refreshTokenValue },
    auth: false,
  });
}

// ── 專案（API-PRJ-01～05、API-SGN-02）────────────────────────────────────
export function createProject(body: CreateProjectRequest): Promise<ProjectResponse> {
  return apiRequest<ProjectResponse>("/api/v1/projects", { method: "POST", body });
}

export function listProjects(
  params: ListProjectsParams = {},
  opts: Opts = {},
): Promise<PageData<ProjectSummary>> {
  return apiRequest<PageData<ProjectSummary>>("/api/v1/projects", {
    query: { ...params },
    signal: opts.signal,
  });
}

export function getProject(id: string, opts: Opts = {}): Promise<ProjectDetail> {
  return apiRequest<ProjectDetail>(`/api/v1/projects/${id}`, { signal: opts.signal });
}

export function updateProject(id: string, body: UpdateProjectRequest): Promise<ProjectResponse> {
  return apiRequest<ProjectResponse>(`/api/v1/projects/${id}`, { method: "PUT", body });
}

export function deleteProject(id: string): Promise<void> {
  return apiRequest<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
}

export function signoffProject(id: string, approver: string): Promise<ProjectResponse> {
  return apiRequest<ProjectResponse>(`/api/v1/projects/${id}/signoff`, {
    method: "POST",
    body: { approver },
  });
}

// ── 目標（API-GOL-01～06、API-SGN-03）────────────────────────────────────
export function createGoal(projectId: string, body: CreateGoalRequest): Promise<GoalResponse> {
  return apiRequest<GoalResponse>(`/api/v1/projects/${projectId}/goals`, { method: "POST", body });
}

export function listGoals(projectId: string, opts: Opts = {}): Promise<GoalSummary[]> {
  return apiRequest<GoalSummary[]>(`/api/v1/projects/${projectId}/goals`, { signal: opts.signal });
}

export function getGoal(id: string, opts: Opts = {}): Promise<GoalDetail> {
  return apiRequest<GoalDetail>(`/api/v1/goals/${id}`, { signal: opts.signal });
}

export function updateGoal(id: string, body: UpdateGoalRequest): Promise<GoalResponse> {
  return apiRequest<GoalResponse>(`/api/v1/goals/${id}`, { method: "PUT", body });
}

export function deleteGoal(id: string): Promise<void> {
  return apiRequest<void>(`/api/v1/goals/${id}`, { method: "DELETE" });
}

/** 調整目標順序：orderedGoalIds 必須恰好是該專案下全部目標（後端校驗，回 204）。 */
export function reorderGoals(projectId: string, orderedGoalIds: string[]): Promise<void> {
  return apiRequest<void>("/api/v1/goals/reorder", {
    method: "PUT",
    body: { projectId, orderedGoalIds },
  });
}

export function signoffGoal(id: string, approver: string): Promise<GoalResponse> {
  return apiRequest<GoalResponse>(`/api/v1/goals/${id}/signoff`, {
    method: "POST",
    body: { approver },
  });
}

// ── 任務（API-TSK-01～06、API-SGN-04）────────────────────────────────────
export function createTask(goalId: string, body: CreateTaskRequest): Promise<TaskResponse> {
  return apiRequest<TaskResponse>(`/api/v1/goals/${goalId}/tasks`, { method: "POST", body });
}

export function listTasks(goalId: string, opts: Opts = {}): Promise<TaskSummary[]> {
  return apiRequest<TaskSummary[]>(`/api/v1/goals/${goalId}/tasks`, { signal: opts.signal });
}

export function getTask(id: string, opts: Opts = {}): Promise<TaskDetail> {
  return apiRequest<TaskDetail>(`/api/v1/tasks/${id}`, { signal: opts.signal });
}

export function updateTask(id: string, body: UpdateTaskRequest): Promise<TaskResponse> {
  return apiRequest<TaskResponse>(`/api/v1/tasks/${id}`, { method: "PUT", body });
}

export function deleteTask(id: string): Promise<void> {
  return apiRequest<void>(`/api/v1/tasks/${id}`, { method: "DELETE" });
}

/** 只允許 FAILED／ESCALATED：retryCount+1、轉 QUEUED；其他狀態後端回 409。 */
export function retryTask(id: string): Promise<TaskResponse> {
  return apiRequest<TaskResponse>(`/api/v1/tasks/${id}/retry`, { method: "POST" });
}

export function signoffTask(id: string, approver: string): Promise<TaskResponse> {
  return apiRequest<TaskResponse>(`/api/v1/tasks/${id}/signoff`, {
    method: "POST",
    body: { approver },
  });
}

// ── BRD/PRD 匯入（Phase 3；契約 §1.1；API-IMP-01～10、API-SGN-01）──────────────
export function listImports(
  params: ListImportsParams = {},
  opts: Opts = {},
): Promise<PageData<ImportRecord>> {
  return apiRequest<PageData<ImportRecord>>("/api/v1/import", { query: { ...params }, signal: opts.signal });
}

/** 上傳檔案（.md／.pdf／.docx，≤10MB）：multipart 欄位 `file`；成功 201 回 UPLOADED 的匯入記錄。 */
export function uploadImport(file: File): Promise<ImportRecord> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<ImportRecord>("/api/v1/import/upload", { method: "POST", body: form });
}

/** 貼上純文字（1～2,000,000 字元）；成功 201 回 UPLOADED 的匯入記錄。 */
export function importText(body: TextImportRequest): Promise<ImportRecord> {
  return apiRequest<ImportRecord>("/api/v1/import/text", { method: "POST", body });
}

export function getImport(id: string, opts: Opts = {}): Promise<ImportRecordDetail> {
  return apiRequest<ImportRecordDetail>(`/api/v1/import/${id}`, { signal: opts.signal });
}

/** 觸發 AI 解析（同步；最長約 model.timeout 秒）。有界閘未過回 422，errors[] 帶 gate／detail／location。 */
export function parseImport(id: string, body: ParseOptions): Promise<ParseResult> {
  return apiRequest<ParseResult>(`/api/v1/import/${id}/parse`, { method: "POST", body });
}

/** 編輯解析結果（整樹覆寫）：狀態轉 REVIEWING，並撤銷既有 signoff。 */
export function editImportResult(id: string, parsedResult: ParsedResult): Promise<ParseResult> {
  return apiRequest<ParseResult>(`/api/v1/import/${id}/result`, { method: "PUT", body: { parsedResult } });
}

/** 人工 signoff 硬閘：approver 必填、不可匿名；只批准，不落庫（confirm 才建立專案）。 */
export function signoffImport(id: string, approver: string): Promise<ImportRecord> {
  return apiRequest<ImportRecord>(`/api/v1/import/${id}/signoff`, { method: "POST", body: { approver } });
}

/** 確認匯入：須已 signoff；單一交易建立專案／目標／任務，成功 201 回 ProjectResponse。 */
export function confirmImport(id: string): Promise<ProjectResponse> {
  return apiRequest<ProjectResponse>(`/api/v1/import/${id}/confirm`, { method: "POST" });
}

/** 放棄匯入：非終態且非 PARSING 的記錄轉 REJECTED。 */
export function rejectImport(id: string): Promise<ImportRecord> {
  return apiRequest<ImportRecord>(`/api/v1/import/${id}/reject`, { method: "POST" });
}

// ── 通知摘要（契約 §1.4；API-NTF-01）────────────────────────────────────────
export function getNotificationSummary(opts: Opts = {}): Promise<NotificationSummary> {
  return apiRequest<NotificationSummary>("/api/v1/notifications/summary", { signal: opts.signal });
}

// ── 系統參數（Phase 6；契約 §1.5；API-SET-01～09）──────────────────────────────
type SettingsReadOpts = Opts & {
  /** true＝揭露加密參數明文（僅 ADMIN；其他角色 403，每次寫審計） */
  reveal?: boolean;
};

const seg = encodeURIComponent;

export function listSettings(opts: SettingsReadOpts = {}): Promise<Record<ConfigCategory, Config[]>> {
  return apiRequest<Record<ConfigCategory, Config[]>>("/api/v1/settings", {
    query: { reveal: opts.reveal ? true : undefined },
    signal: opts.signal,
  });
}

export function listSettingsByCategory(category: ConfigCategory, opts: SettingsReadOpts = {}): Promise<Config[]> {
  return apiRequest<Config[]>(`/api/v1/settings/${seg(category)}`, {
    query: { reveal: opts.reveal ? true : undefined },
    signal: opts.signal,
  });
}

/** 更新單鍵（ADMIN）；加密參數須帶 confirm=true，否則 409。 */
export function updateSetting(category: ConfigCategory, key: string, body: UpdateConfigRequest): Promise<Config> {
  return apiRequest<Config>(`/api/v1/settings/${seg(category)}/${seg(key)}`, { method: "PUT", body });
}

/** 原子更新 Token Guard 群組（compact／halt 一併提交，後端跨鍵校驗 halt > compact）。 */
export function updateTokenGuard(body: TokenGuardRequest): Promise<Config[]> {
  return apiRequest<Config[]>("/api/v1/settings/execution/token-guard", { method: "PUT", body });
}

/** 重置單鍵為預設值；加密參數須 confirm=true。 */
export function resetSetting(category: ConfigCategory, key: string, confirm = false): Promise<Config> {
  return apiRequest<Config>(`/api/v1/settings/${seg(category)}/${seg(key)}/reset`, {
    method: "POST",
    query: { confirm: confirm ? true : undefined },
  });
}

/** 重置整個分類（同交易）；加密參數預設略過，要連同重置須 confirm=true。 */
export function resetCategory(category: ConfigCategory, confirm = false): Promise<Config[]> {
  return apiRequest<Config[]>(`/api/v1/settings/${seg(category)}/reset`, {
    method: "POST",
    query: { confirm: confirm ? true : undefined },
  });
}

/** 測試模型連線（ADMIN）：可帶表單內尚未儲存的 apiUrl／apiKey／model；省略的欄位取已儲存值。 */
export function testConnection(body?: TestConnectionRequest): Promise<ConnectionTestResult> {
  return apiRequest<ConnectionTestResult>("/api/v1/settings/test-connection", { method: "POST", body });
}

export function listSettingsHistory(
  params: ListSettingsHistoryParams = {},
  opts: Opts = {},
): Promise<PageData<ConfigHistory>> {
  return apiRequest<PageData<ConfigHistory>>("/api/v1/settings/history", {
    query: { ...params },
    signal: opts.signal,
  });
}

/** 匯出設定（ADMIN）：回 JSON 檔（不包封包）；加密參數的 value 固定為 `<encrypted>`。 */
export function exportSettings(): Promise<DownloadResult> {
  return apiDownload("/api/v1/settings/export", { method: "POST" });
}

/** 匯入設定（ADMIN）：multipart 欄位 `file`（≤1MB 的 JSON）；部分失敗仍是 200，逐筆結果在 errors[]。 */
export function importSettings(file: File): Promise<ImportSettingsResult> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<ImportSettingsResult>("/api/v1/settings/import", { method: "POST", body: form });
}
