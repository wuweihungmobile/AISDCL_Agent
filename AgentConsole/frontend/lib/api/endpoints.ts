/**
 * 每個後端端點一個函式；名稱對應 PRD §7.1（API-PRJ／GOL／TSK／SGN／AUTH／IMP／SET／NTF）。
 * 型別來自 schema.d.ts（Phase 1+2）與 schema-p3-6.d.ts（Phase 3～6，依契約 openapi-p3-6.yaml 產生）；
 * 這裡不做快取、不碰 React，快取與失效策略在 lib/api/queries.ts（TanStack Query）。
 * Phase 3～6 的函式名取契約 YAML 的 operationId。
 */
import { apiDownload, apiRequest, apiRequestWithHeaders, type DownloadResult } from "./client";
import type {
  Alert,
  Checkpoint,
  Config,
  ConfigCategory,
  ConfigHistory,
  ConnectionTestResult,
  CreateGoalRequest,
  CreateProjectRequest,
  CreateTaskRequest,
  Dag,
  ExecutionRtm,
  ExecutionRun,
  ExecutionRunDetail,
  ExecutionRunSummary,
  ExecutionStep,
  GoalDetail,
  GoalResponse,
  GoalSummary,
  ImportRecord,
  ImportRecordDetail,
  ImportSettingsResult,
  IssueListPage,
  IssueListParams,
  IssuePage,
  IssuePriorityRequest,
  IssuePriorityResponse,
  ListAlertsParams,
  ListExecutionsParams,
  ListImportsParams,
  ListLogsParams,
  ListProjectsParams,
  ListSettingsHistoryParams,
  ListStepsParams,
  LogEntry,
  LogoutRequest,
  MonitorRangeParams,
  MonitorTrendParams,
  NotificationSummary,
  PageData,
  ParseOptions,
  ParseResult,
  ParsedResult,
  PendingSignoffs,
  ProjectDetail,
  ProjectMetrics,
  ProjectResponse,
  ProjectSummary,
  ReportParams,
  ReviewBody,
  SddBindingRequest,
  SddEngineStatus,
  SddFreezeRequest,
  SddFsmState,
  SiCloseRequest,
  SiConsoleWrites,
  SiDecideRequest,
  SiEvent,
  SiListParams,
  SiObservationRequest,
  SiObservationRow,
  SiPage,
  SiProposal,
  SiRun,
  SiStatusItem,
  SiValidation,
  SiWriteReceipt,
  StartExecutionRequest,
  TaskDetail,
  TaskResponse,
  TaskSummary,
  TaskTotals,
  TaskTotalsParams,
  TaskTrendPoint,
  TestConnectionRequest,
  TextImportRequest,
  TokenGuardRequest,
  TokenResponse,
  TokenTrendPoint,
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

/**
 * 登出並撤銷 refresh token（契約 §1.9.1；API-AUTH-03，v1.4 D-19）：免認證（登出時 access token 可能已過期，仍必須能撤銷），
 * 請求格式合法一律 204（有效、無效、過期、已撤銷、或是 access token 都一樣，不洩漏有效性）。
 * 不帶 token、不做 401 換新（auth:false）；呼叫端 AuthProvider.logout 以 fire-and-forget 呼叫，失敗也不阻擋本機登出。
 */
export function logout(refreshTokenValue: string): Promise<void> {
  const body: LogoutRequest = { refreshToken: refreshTokenValue };
  return apiRequest<void>("/api/v1/auth/logout", { method: "POST", body, auth: false });
}

// ── 專案（API-PRJ-01～05、API-SGN-02）────────────────────────────────────
export function createProject(body: CreateProjectRequest): Promise<ProjectResponse> {
  return apiRequest<ProjectResponse>("/api/v1/projects", { method: "POST", body });
}

export function listProjects(params: ListProjectsParams = {}, opts: Opts = {}): Promise<PageData<ProjectSummary>> {
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

/**
 * 復原軟刪除的專案（v1.2，C-3；契約 §1.6.1；OPERATOR 以上）：連同「同一次刪除」連帶軟刪的目標與任務一併回來，專案狀態還原為刪除前。
 * 409 `project_not_deleted`（沒有被刪除）／`restore_window_expired`（超過保留期，details.retentionDays）；404＝不存在或已被清除。
 */
export function restoreProject(id: string): Promise<ProjectDetail> {
  return apiRequest<ProjectDetail>(`/api/v1/projects/${id}/restore`, { method: "POST" });
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
export function listImports(params: ListImportsParams = {}, opts: Opts = {}): Promise<PageData<ImportRecord>> {
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

// ── 待審批清單（契約 §1.8.1；API-SGN-05，v1.4 D-18）──────────────────────────────
/** 跨專案列出待簽核的草案（專案、目標、任務、匯入記錄）；`limit` 只截斷 items（預設 50、1～200），不影響 counts。 */
export function getPendingSignoffs(params: { limit?: number } = {}, opts: Opts = {}): Promise<PendingSignoffs> {
  return apiRequest<PendingSignoffs>("/api/v1/signoffs/pending", { query: { limit: params.limit }, signal: opts.signal });
}

// ── AISDLC_SDD 引擎狀態（契約 §1.7.1；API-ENG-01，v1.4 D-16；v1.5 加 projectId，§1.10.4、API-ENG-02）──────────────
/**
 * 唯讀：版本、FSM 專案清單，帶 `project` 時另帶該專案的 FSM 狀態；引擎不可用也回 200（`available=false`＋`reason`）。
 * 省略 `project` 且省略 `projectId` → `fsm` 為 null（由前端依 `projects` 選一個再帶 `project` 重取）。
 * v1.5：帶 `projectId`（Console 專案 id）＝讀「該專案根目錄下」的 FSM（`root`＝專案的 executionPath；專案不存在或已軟刪除回 404）；
 * 這時省略 `project` 會預設取該專案的有效 FSM 專案（`sddProject` 有值取它，否則專案名），所以一個請求就帶回 fsm；
 * `project` 在這個模式是「同一個狀態目錄內改選別的 FSM 專案」。`project` 值原樣編碼交給後端（不淨化）。
 */
export function getSddEngineStatus(params: { project?: string; projectId?: string } = {}, opts: Opts = {}): Promise<SddEngineStatus> {
  return apiRequest<SddEngineStatus>("/api/v1/engines/sdd", { query: { projectId: params.projectId, project: params.project }, signal: opts.signal });
}

// ── SDD 治理（整合輪 115；契約 §1.10）──────────────────────────────────────────────
/**
 * 核准凍結（人工閘；OPERATOR 以上；契約 §1.10.2、API-SGN-06）：`HUMAN_PENDING`→`SPEC_FROZEN`。approver 不在請求內（一律取 JWT subject）、沒有 binding 欄。
 * 驗證順序固定：404 專案 → 400 欄位 → 503 sdd_write_disabled → 409 sdd_fsm_not_found → 409 sdd_binding_conflict → Bridge（409／422／502／503／504）。
 * 非冪等：FSM 已不在 HUMAN_PENDING（含已凍結）→ 409 sdd_fsm_state_conflict。成功 200 回凍結後的 FSM 狀態（與 engines/sdd 的 fsm 同形）。
 */
export function freezeProjectSddSpec(projectId: string, body: SddFreezeRequest): Promise<SddFsmState> {
  return apiRequest<SddFsmState>(`/api/v1/projects/${projectId}/sdd/freeze`, { method: "POST", body });
}

/**
 * 編輯專案的 FSM 專案（OPERATOR 以上；契約 §1.10.7、API-PRJ-08）：`sddProject` 為 null＝清除、回到「用預設」（專案名）。
 * 不檢查狀態檔是否存在、不呼叫 Bridge；唯一性衝突回 409 sdd_binding_conflict；相同值再送＝冪等。成功 200 回專案詳情。
 */
export function updateProjectSddBinding(projectId: string, sddProject: string | null): Promise<ProjectDetail> {
  const body: SddBindingRequest = { sddProject };
  return apiRequest<ProjectDetail>(`/api/v1/projects/${projectId}/sdd-binding`, { method: "PUT", body });
}

/**
 * 執行追溯覆蓋（諮詢視圖；VIEWER 以上；契約 §1.10.3、API-EXE-16）：AT／AC 覆蓋、失敗 AT、無法歸屬 AC 的 AT、`fullyCovered`，`advisory` 恆為 true。
 * 404 有兩種：批次不存在（無 reason）與批次存在但沒有報告（reason `rtm_not_found`）；422 報告壞掉；502／504 Bridge 失敗。不輪詢、不快取。
 */
export function getExecutionRtm(runId: string, opts: Opts = {}): Promise<ExecutionRtm> {
  return apiRequest<ExecutionRtm>(`/api/v1/executions/${runId}/rtm`, { signal: opts.signal });
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

export function listSettingsHistory(params: ListSettingsHistoryParams = {}, opts: Opts = {}): Promise<PageData<ConfigHistory>> {
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

// ── 專案執行（Phase 4；契約 §1.2；API-EXE-01～14）──────────────────────────────
/**
 * 啟動執行（OPERATOR）。body 可為 `{}`（全部省略＝專案預設）。
 * 驗證順序固定：404 → 400 → 409（執行中／狀態／未 signoff）→ 400 範圍 → 409 範圍 → 422 物化 → Bridge（409／422／502／504）。
 */
export function executeProject(projectId: string, body: StartExecutionRequest = {}): Promise<ExecutionRun> {
  return apiRequest<ExecutionRun>(`/api/v1/projects/${projectId}/execute`, { method: "POST", body });
}

/** 專案的執行批次列表（預設 startedAt,desc；執行頁挑目前批次、監控頁「執行批次」下拉與批次比較用）。 */
export function listProjectExecutions(projectId: string, params: ListExecutionsParams = {}, opts: Opts = {}): Promise<PageData<ExecutionRunSummary>> {
  return apiRequest<PageData<ExecutionRunSummary>>(`/api/v1/projects/${projectId}/executions`, {
    query: { ...params },
    signal: opts.signal,
  });
}

/** 執行狀態：Bridge 不可達時仍回 200（bridge.connected=false，進度為 DB 衍生值）。 */
export function getExecution(runId: string, opts: Opts = {}): Promise<ExecutionRunDetail> {
  return apiRequest<ExecutionRunDetail>(`/api/v1/executions/${runId}`, { signal: opts.signal });
}

/** 暫停（下一個步驟邊界生效）：回應 RUNNING＋bridgeStatus=PAUSING，PAUSED 由 SSE status-change 通知。 */
export function pauseExecution(runId: string): Promise<ExecutionRun> {
  return apiRequest<ExecutionRun>(`/api/v1/executions/${runId}/pause`, { method: "POST" });
}

/** 恢復（PAUSED 同進度接續）：後端會重驗範圍內 signoff。 */
export function resumeExecution(runId: string): Promise<ExecutionRun> {
  return apiRequest<ExecutionRun>(`/api/v1/executions/${runId}/resume`, { method: "POST" });
}

/** 取消：RUNNING／PAUSED 才可（其餘 409）；RUNNING 回 bridgeStatus=CANCELLING，PAUSED 即時 CANCELLED。 */
export function cancelExecution(runId: string): Promise<ExecutionRun> {
  return apiRequest<ExecutionRun>(`/api/v1/executions/${runId}/cancel`, { method: "POST" });
}

/** 步驟分頁（依 stepNumber 升冪；stepNumber 是事件 seq）：SSE 斷線回補用 afterSeq（嚴格大於）。 */
export function listExecutionSteps(runId: string, params: ListStepsParams = {}, opts: Opts = {}): Promise<PageData<ExecutionStep>> {
  return apiRequest<PageData<ExecutionStep>>(`/api/v1/executions/${runId}/steps`, {
    query: { ...params },
    signal: opts.signal,
  });
}

export function getExecutionDag(runId: string, opts: Opts = {}): Promise<Dag> {
  return apiRequest<Dag>(`/api/v1/executions/${runId}/dag`, { signal: opts.signal });
}

/** 斷點列表（舊→新；Bridge 於每個步驟完成時自動記錄）。 */
export function listExecutionCheckpoints(runId: string, opts: Opts = {}): Promise<Checkpoint[]> {
  return apiRequest<Checkpoint[]>(`/api/v1/executions/${runId}/checkpoints`, { signal: opts.signal });
}

/** 從歷史斷點還原（只限專案最新批次；PAUSED 與三個終態可）。終態 run 還原後原 SSE 已關閉，須重新連線。 */
export function restoreExecution(runId: string, checkpointId: string): Promise<ExecutionRun> {
  return apiRequest<ExecutionRun>(`/api/v1/executions/${runId}/restore/${checkpointId}`, { method: "POST" });
}

/**
 * 審核（204）。路徑的 stepId 是 review_requests.id（不是 playbook 的 step_id；契約 §0.6）。
 * SKIP 與「找不到還原點的 RETRY」會另開後續批次，其 id 在回應標頭 X-Follow-Up-Run-Id（否則為 null）。
 */
export async function reviewExecution(runId: string, reviewId: string, body: ReviewBody): Promise<{ followUpRunId: string | null }> {
  const { headers } = await apiRequestWithHeaders<void>(`/api/v1/executions/${runId}/review/${reviewId}`, {
    method: "POST",
    body,
  });
  return { followUpRunId: headers.get("X-Follow-Up-Run-Id") };
}

// ── 專案監控（Phase 5；契約 §1.3；API-MON-01～08）──────────────────────────────
export function getProjectMetrics(projectId: string, params: MonitorRangeParams = {}, opts: Opts = {}): Promise<ProjectMetrics> {
  return apiRequest<ProjectMetrics>(`/api/v1/monitor/projects/${projectId}/metrics`, {
    query: { ...params },
    signal: opts.signal,
  });
}

export function getTokenTrend(projectId: string, params: MonitorTrendParams = {}, opts: Opts = {}): Promise<TokenTrendPoint[]> {
  return apiRequest<TokenTrendPoint[]>(`/api/v1/monitor/projects/${projectId}/token-trend`, {
    query: { ...params },
    signal: opts.signal,
  });
}

export function getTaskTrend(projectId: string, params: MonitorTrendParams = {}, opts: Opts = {}): Promise<TaskTrendPoint[]> {
  return apiRequest<TaskTrendPoint[]>(`/api/v1/monitor/projects/${projectId}/task-trend`, {
    query: { ...params },
    signal: opts.signal,
  });
}

/**
 * 全域任務總計（契約 §1.3.8，v1.2，C-1；API-MON-08）：跨全部未封存且未軟刪除的專案，`[from, to)` 內 STARTED／COMPLETED／FAILED／RETRYING 的步驟列數
 * （與 task-trend 同一張表、同一判準，只是不分桶）。取代前端對每個專案各打一次 task-trend 再加總的做法（DEF-AC-009）。
 */
export function getTaskTotals(params: TaskTotalsParams, opts: Opts = {}): Promise<TaskTotals> {
  return apiRequest<TaskTotals>("/api/v1/monitor/task-totals", { query: { ...params }, signal: opts.signal });
}

/** 告警（由新到舊）；acknowledged 省略＝全部。 */
export function listProjectAlerts(projectId: string, params: ListAlertsParams = {}, opts: Opts = {}): Promise<Alert[]> {
  return apiRequest<Alert[]>(`/api/v1/monitor/projects/${projectId}/alerts`, {
    query: { ...params },
    signal: opts.signal,
  });
}

/** 確認告警（OPERATOR；204；冪等：已確認者再呼叫仍 204，不改寫第一次的確認者與時間）。 */
export function acknowledgeAlert(alertId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/monitor/alerts/${alertId}/acknowledge`, { method: "POST" });
}

/** 日誌查詢（由既有資料衍生，不含引擎原始 stdout）：等級、關鍵字、任務、排序與分頁。 */
export function listProjectLogs(projectId: string, params: ListLogsParams = {}, opts: Opts = {}): Promise<PageData<LogEntry>> {
  return apiRequest<PageData<LogEntry>>(`/api/v1/monitor/projects/${projectId}/logs`, {
    query: { ...params },
    signal: opts.signal,
  });
}

/**
 * 匯出報表：不包封包的檔案下載，CSV 與 PDF 都回 200（v1.2，C-4；契約 §1.3.7），檔名取自 Content-Disposition。
 * 契約要求呼叫端 CSV 送 Accept: text/csv、PDF 送 application/pdf（皆可用萬用型別；後端以 format 為準、不因 Accept 回 406）；
 * 補上 application/json 是為了讓錯誤封包（400／404）也能協商出來，否則 Spring 對「只接受單一檔案型別」的請求會把 JSON 錯誤封包變成 406。
 */
export function downloadProjectReport(projectId: string, params: ReportParams = {}): Promise<DownloadResult> {
  const fileType = params.format === "pdf" ? "application/pdf" : "text/csv";
  return apiDownload(`/api/v1/monitor/projects/${projectId}/report`, {
    query: { ...params },
    accept: `${fileType},application/json;q=0.9,*/*;q=0.8`,
  });
}

// ── SelfImproving 唯讀鏡像（P1b；TCS-SelfImprovingMirror-P1b R11）──────────────────────────────
// 六個 GET（P1b 的鏡像讀面；P2b 另加一個對帳讀面與四個 POST，見本節之後）：Console 是顯示面，頁面資料＝根層 `si export` 的輸出（backend 只改欄名）。
// 瀏覽器只呼叫 console-api 的 /api/v1/si/**，從不直連 Bridge（Architecture §10.1）。
type SiOpts = SiListParams & Opts;

/** 狀態橫幅：不收任何查詢參數（`since`、`limit` 會被 Bridge 以 422 擋下）。 */
export function getSiStatus(opts: Opts = {}): Promise<SiPage<SiStatusItem>> {
  return apiRequest<SiPage<SiStatusItem>>("/api/v1/si/status", { signal: opts.signal });
}

/** 觀察帳本：`since` 為嚴格大於的游標（取自上一頁的 `nextSince`），`limit` 為單頁筆數；undefined 不進網址。 */
export function getSiObservations(opts: SiOpts = {}): Promise<SiPage<SiObservationRow>> {
  return apiRequest<SiPage<SiObservationRow>>("/api/v1/si/observations", { query: { since: opts.since, limit: opts.limit }, signal: opts.signal });
}

export function getSiEvents(opts: SiOpts = {}): Promise<SiPage<SiEvent>> {
  return apiRequest<SiPage<SiEvent>>("/api/v1/si/events", { query: { since: opts.since, limit: opts.limit }, signal: opts.signal });
}

export function getSiProposals(opts: SiOpts = {}): Promise<SiPage<SiProposal>> {
  return apiRequest<SiPage<SiProposal>>("/api/v1/si/proposals", { query: { since: opts.since, limit: opts.limit }, signal: opts.signal });
}

/** 單筆提案：`id` 以 encodeURIComponent 編成單一路徑段；不收查詢參數；查無回 404 `si_not_found`。 */
export function getSiProposal(id: string, opts: Opts = {}): Promise<SiPage<SiProposal>> {
  return apiRequest<SiPage<SiProposal>>(`/api/v1/si/proposals/${seg(id)}`, { signal: opts.signal });
}

export function getSiRuns(opts: SiOpts = {}): Promise<SiPage<SiRun>> {
  return apiRequest<SiPage<SiRun>>("/api/v1/si/runs", { query: { since: opts.since, limit: opts.limit }, signal: opts.signal });
}

// ── SelfImproving 寫入載體（P2b；TCS-SelfImprovingDecide-P2b W16）──────────────────────────────
// 四個 POST（僅 ADMIN；帳號是否在 deciders 名單由 backend 判，403 `si_write_forbidden`）加一個對帳讀面。瀏覽器仍只呼叫 console-api：
// 稽核簽章在 backend、落檔在 Bridge，前端沒有任何金鑰。本文原樣 `JSON.stringify`（鍵集合＝呼叫端給的，不補預設值、不丟 undefined 以外的欄位）。

/** 決定：`id` 為 PROP 號（動詞 resume 為 RUN 號）；以 encodeURIComponent 編成單一路徑段。 */
export function postSiDecide(id: string, body: SiDecideRequest): Promise<SiWriteReceipt> {
  return apiRequest<SiWriteReceipt>(`/api/v1/si/proposals/${seg(id)}/decide`, { method: "POST", body });
}

/** 新增觀察（含更正：本文帶 `corrects`）。 */
export function postSiObservation(body: SiObservationRequest): Promise<SiWriteReceipt> {
  return apiRequest<SiWriteReceipt>("/api/v1/si/observations", { method: "POST", body });
}

/** 關閉觀察：`id` 為 OBS 號；本文為終值加 `ref` 或 `text`（恰擇一，依終值）。 */
export function postSiObservationClose(id: string, body: SiCloseRequest): Promise<SiWriteReceipt> {
  return apiRequest<SiWriteReceipt>(`/api/v1/si/observations/${seg(id)}/close`, { method: "POST", body });
}

/** 新增觀察的預檢（`obs-add --dry-run`）：零副作用，不寫 DB、不落檔；回預覽列與位元組數，或根層的拒收原因。 */
export function postSiObservationValidate(body: SiObservationRequest): Promise<SiValidation> {
  return apiRequest<SiValidation>("/api/v1/si/observations/validate", { method: "POST", body });
}

/** Console 稽核列與帳本的對帳（VIEWER 以上可讀，Console 只讓 ADMIN 看見）；`limit` 為 1～500，undefined 不進網址（backend 預設 100）。 */
export function getSiConsoleWrites(opts: { limit?: number } & Opts = {}): Promise<SiConsoleWrites> {
  return apiRequest<SiConsoleWrites>("/api/v1/si/console-writes", { query: { limit: opts.limit }, signal: opts.signal });
}

// ── 議題中心（TCS-IssueCenter-20261027 §C4；API-IC-01～04）──────────────────────────────────────────
// 兩個唯讀 GET（Bridge 原樣轉遞，每筆另有 Console 自有的 priority、priorityNote）加兩個僅 ADMIN 的優先順序寫入（PUT 設定、DELETE 清除）。
// 瀏覽器只呼叫 console-api 的 /api/v1/issues/**；議題中心不寫帳本，唯一的寫入是 Console 自有的優先順序。
type IssueOpts = IssueListParams & Opts;

/**
 * 議題清單（游標分頁）：`status`、`source` 是中文別名（逗號取聯集）；`since` 為嚴格大於的游標（取自上一頁的 `nextSince`），`limit` 為單頁筆數；
 * undefined 與空字串不進網址（所以「全部」分頁不帶 `status`）。回應含 `legend`、`summary`（整本帳計數，不受篩選與游標影響）。
 */
export function getIssues(opts: IssueOpts = {}): Promise<IssueListPage> {
  return apiRequest<IssueListPage>("/api/v1/issues", {
    query: { status: opts.status, source: opts.source, since: opts.since, limit: opts.limit },
    signal: opts.signal,
  });
}

/** 單筆議題（含 `raw`、`timeline`；沒有 `legend`、`summary`）：`id` 以 encodeURIComponent 編成單一路徑段；不收查詢參數；查無回 404 `si_not_found`。 */
export function getIssue(id: string, opts: Opts = {}): Promise<IssuePage> {
  return apiRequest<IssuePage>(`/api/v1/issues/${seg(id)}`, { signal: opts.signal });
}

/** 設定或更新優先順序（僅 ADMIN）：本文 `{ rank, note }` 原樣 `JSON.stringify`；成功回寫入的那一列。 */
export function putIssuePriority(id: string, body: IssuePriorityRequest): Promise<IssuePriorityResponse> {
  return apiRequest<IssuePriorityResponse>(`/api/v1/issues/${seg(id)}/priority`, { method: "PUT", body });
}

/** 清除優先順序（僅 ADMIN）：204、冪等（列不存在也 204）；不呼叫 Bridge，所以議題已結案或已不存在時仍清得掉遺留的列。 */
export function deleteIssuePriority(id: string): Promise<void> {
  return apiRequest<void>(`/api/v1/issues/${seg(id)}/priority`, { method: "DELETE" });
}
