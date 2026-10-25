"use client";

/**
 * TanStack Query 層：查詢鍵、讀取 hooks、寫入 mutations。
 *  - 全部 client-side；查詢在已登入（status==="authed"）後才啟用。
 *  - 專案／目標／任務三層的計數互相牽動（goalsCount、tasksDone…），任何寫入成功就把三層快取全部標為過期，
 *    資料量小，換取「不會顯示過期計數」的簡單正確性。
 */
import { keepPreviousData, useInfiniteQuery, useMutation, useQueries, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthProvider";
import { bucketFor, rangeParams, type RangeId } from "@/lib/domain/metrics";
import { SI_CONSOLE_WRITES_LIMIT, SI_PAGE_LIMIT } from "@/lib/domain/si";
import { isRunTerminal } from "@/lib/domain/status";
import {
  acknowledgeAlert,
  cancelExecution,
  confirmImport,
  createGoal,
  createProject,
  createTask,
  deleteGoal,
  deleteProject,
  deleteTask,
  downloadProjectReport,
  editImportResult,
  executeProject,
  exportSettings,
  freezeProjectSddSpec,
  getExecution,
  getExecutionDag,
  getExecutionRtm,
  getGoal,
  getImport,
  getNotificationSummary,
  getPendingSignoffs,
  getProject,
  getProjectMetrics,
  getSddEngineStatus,
  getSiConsoleWrites,
  getSiEvents,
  getSiObservations,
  getSiProposals,
  getSiRuns,
  getSiStatus,
  getTask,
  getTaskTotals,
  getTaskTrend,
  getTokenTrend,
  importSettings,
  importText,
  listExecutionCheckpoints,
  listExecutionSteps,
  listGoals,
  listImports,
  listProjectAlerts,
  listProjectExecutions,
  listProjectLogs,
  listProjects,
  listSettings,
  listSettingsByCategory,
  listSettingsHistory,
  listTasks,
  parseImport,
  pauseExecution,
  postSiDecide,
  postSiObservation,
  postSiObservationClose,
  postSiObservationValidate,
  rejectImport,
  reorderGoals,
  resetCategory,
  resetSetting,
  restoreExecution,
  restoreProject,
  resumeExecution,
  retryTask,
  reviewExecution,
  signoffGoal,
  signoffImport,
  signoffProject,
  signoffTask,
  testConnection,
  updateGoal,
  updateProject,
  updateProjectSddBinding,
  updateSetting,
  updateTask,
  updateTokenGuard,
  uploadImport,
} from "./endpoints";
import type {
  Alert,
  Config,
  ConfigCategory,
  CreateGoalRequest,
  CreateProjectRequest,
  CreateTaskRequest,
  ExecutionRun,
  ExecutionRunDetail,
  ExecutionRunSummary,
  ExecutionStep,
  ImportRecordDetail,
  ListAlertsParams,
  ListExecutionsParams,
  ListImportsParams,
  ListLogsParams,
  ListProjectsParams,
  ListSettingsHistoryParams,
  ParseOptions,
  ParsedResult,
  ParseResult,
  ProjectDetail,
  ReportParams,
  ReviewDecision,
  SddEngineStatus,
  SddFreezeRequest,
  SiCloseRequest,
  SiDecideRequest,
  SiListParams,
  SiObservationRequest,
  SiPage,
  StartExecutionRequest,
  TestConnectionRequest,
  TextImportRequest,
  TokenGuardRequest,
  UpdateConfigRequest,
  UpdateGoalRequest,
  UpdateProjectRequest,
  UpdateTaskRequest,
} from "./types";

export const qk = {
  projects: (params: ListProjectsParams) => ["projects", "list", params] as const,
  allProjects: ["projects", "all"] as const,
  project: (id: string) => ["projects", "detail", id] as const,
  goals: (projectId: string) => ["goals", "list", projectId] as const,
  goal: (id: string) => ["goals", "detail", id] as const,
  tasks: (goalId: string) => ["tasks", "list", goalId] as const,
  task: (id: string) => ["tasks", "detail", id] as const,
  imports: (params: ListImportsParams) => ["imports", "list", params] as const,
  importDetail: (id: string) => ["imports", "detail", id] as const,
  notifications: ["notifications", "summary"] as const,
  /** 待審批清單掛在 "notifications" 底下：任何失效 ["notifications"] 的動作（簽核、確認告警、匯入變動）會連它一起重抓。 */
  pendingSignoffs: (limit: number) => ["notifications", "pending-signoffs", limit] as const,
  /**
   * project＝null：未帶 project（全域模式＝第一次請求取清單用；專案模式＝讓後端取專案的有效 FSM 專案）；其餘依 FSM 專案名各一份。
   * projectId（v1.5，§1.10.4）：專案模式的 Console 專案 id；全域模式為 null——兩種模式的回應不同，快取鍵必須分開。
   */
  sddEngine: (project: string | null, projectId: string | null = null) => ["sdd", "engine", project, projectId] as const,
  /**
   * 一個批次的追溯覆蓋（v1.5，§1.10.3）；不輪詢、不快取（staleTime 0），批次重新進入終態時重抓。
   * 🔴 刻意不放在 "executions" 家族底下：SSE 事件（終態回放）與任何控制動作都會 invalidateRuns，掛在那裡會讓已取得的報告被連帶重抓，
   * 破壞「進入終態後取一次」（E2E 實測：終態批次開頁，同一份報告被請求兩次）。
   */
  rtm: (runId: string) => ["rtm", runId] as const,
  settings: ["settings", "all"] as const,
  settingsCategory: (category: ConfigCategory) => ["settings", "category", category] as const,
  settingsHistory: (params: ListSettingsHistoryParams) => ["settings", "history", params] as const,
  executions: (projectId: string, params: ListExecutionsParams) => ["executions", "list", projectId, params] as const,
  execution: (runId: string) => ["executions", "detail", runId] as const,
  dag: (runId: string) => ["executions", "dag", runId] as const,
  checkpoints: (runId: string) => ["executions", "checkpoints", runId] as const,
  steps: (runId: string) => ["executions", "steps", runId] as const,
  metrics: (projectId: string, q: MonitorQuery) => ["monitor", "metrics", projectId, q] as const,
  tokenTrend: (projectId: string, q: MonitorQuery) => ["monitor", "token-trend", projectId, q] as const,
  taskTrend: (projectId: string, q: MonitorQuery) => ["monitor", "task-trend", projectId, q] as const,
  alerts: (projectId: string, params: ListAlertsParams) => ["monitor", "alerts", projectId, params] as const,
  logs: (projectId: string, q: LogQuery) => ["monitor", "logs", projectId, q] as const,
  taskTotals: (weekStartIso: string) => ["dashboard", "task-totals", weekStartIso] as const,
  /** SelfImproving 唯讀鏡像（P1b）：全部掛在 ["si"] 底下，頁首的「重新整理」以 siAll 重抓目前顯示的面板（type: active） */
  siAll: ["si"] as const,
  siStatus: ["si", "status"] as const,
  siObservations: ["si", "observations"] as const,
  siProposals: ["si", "proposals"] as const,
  siEvents: ["si", "events"] as const,
  siRuns: ["si", "runs"] as const,
  /** P2b 的對帳讀面也掛在 ["si"] 底下：頁首的「重新整理」與寫入成功後的失效都以 siAll 一併重抓它（只有 ADMIN 有這個查詢）。 */
  siConsoleWrites: ["si", "console-writes"] as const,
};

const POLL_MS = 30_000;

/**
 * 通知摘要輪詢間隔。契約 §0.4：限流鍵是 JWT subject，同一使用者所有頁面共用每分鐘 100 次，
 * 所以任何輪詢都不得小於 10 秒（NOTIFICATION_POLL_FLOOR_MS）；30 秒遠高於地板。
 * 分頁不可見時 TanStack Query 預設停止輪詢（refetchIntervalInBackground＝false），符合契約「頁面不可見時應停止輪詢」。
 */
export const NOTIFICATION_POLL_FLOOR_MS = 10_000;
export const NOTIFICATION_POLL_MS = 30_000;

/** 寫入成功後：三層快取全部標為過期（進行中的查詢會自動重抓）。 */
export function invalidateTree(qc: QueryClient): Promise<unknown> {
  return Promise.all([qc.invalidateQueries({ queryKey: ["projects"] }), qc.invalidateQueries({ queryKey: ["goals"] }), qc.invalidateQueries({ queryKey: ["tasks"] })]);
}

function useEnabled(extra = true): boolean {
  const { status } = useAuth();
  return status === "authed" && extra;
}

// ── 讀取 ────────────────────────────────────────────────────────────────
export function useProjects(params: ListProjectsParams) {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.projects(params),
    queryFn: ({ signal }) => listProjects(params, { signal }),
    enabled,
    placeholderData: keepPreviousData,
  });
}

/** 全部專案（最多 100 筆，依更新時間新到舊）：頂列 chips、側欄 rail、Dashboard KPI 與待審批共用同一份快取。 */
export function useAllProjects() {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.allProjects,
    queryFn: ({ signal }) => listProjects({ page: 0, size: 100, sort: "updatedAt,desc" }, { signal }),
    enabled,
    staleTime: 15_000,
    refetchInterval: POLL_MS,
  });
}

export function useProject(id: string | undefined) {
  const enabled = useEnabled(Boolean(id));
  return useQuery({
    queryKey: qk.project(id ?? ""),
    queryFn: ({ signal }) => getProject(id as string, { signal }),
    enabled,
  });
}

export function useGoals(projectId: string | undefined) {
  const enabled = useEnabled(Boolean(projectId));
  return useQuery({
    queryKey: qk.goals(projectId ?? ""),
    queryFn: ({ signal }) => listGoals(projectId as string, { signal }),
    enabled,
  });
}

export function useGoal(id: string | undefined) {
  const enabled = useEnabled(Boolean(id));
  return useQuery({
    queryKey: qk.goal(id ?? ""),
    queryFn: ({ signal }) => getGoal(id as string, { signal }),
    enabled,
  });
}

export function useTasks(goalId: string | undefined) {
  const enabled = useEnabled(Boolean(goalId));
  return useQuery({
    queryKey: qk.tasks(goalId ?? ""),
    queryFn: ({ signal }) => listTasks(goalId as string, { signal }),
    enabled,
  });
}

export function useTask(id: string | undefined) {
  const enabled = useEnabled(Boolean(id));
  return useQuery({
    queryKey: qk.task(id ?? ""),
    queryFn: ({ signal }) => getTask(id as string, { signal }),
    enabled,
  });
}

// ── 待人工審批清單（Dashboard「待人工審批」卡；契約 §1.8.1、§4.5 G-10；v1.4 D-18）──────────
/** 卡片清單最多取幾筆（契約 G-10 指定 `limit=50`；超過時卡片底部寫「僅列出最早的 N 筆，共 M 筆」）。 */
export const PENDING_SIGNOFF_LIMIT = 50;

/**
 * 跨專案的待簽核草案（專案、目標、任務、匯入記錄四種）：`counts.total` 與通知摘要的 `pendingSignoffs` 同判準、同數字
 * （後端以同一組述詞產生計數與清單）；清單依建立時間升冪。取代 v1.3 以前的 `useSignoffQueue`（前端用專案與目標 API 另外組的近似清單：
 * 沒有任務、沒有匯入記錄、也沒有已簽專案底下的草案，數字大於點得到的項目）。
 * 掛在 `["notifications"]` 查詢鍵底下，輪詢節奏與通知摘要相同；任何簽核成功都會把整個 notifications 家族標為過期、立即重抓。
 */
export function usePendingSignoffs(limit: number = PENDING_SIGNOFF_LIMIT) {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.pendingSignoffs(limit),
    queryFn: ({ signal }) => getPendingSignoffs({ limit }, { signal }),
    enabled,
    staleTime: NOTIFICATION_POLL_FLOOR_MS,
    refetchInterval: NOTIFICATION_POLL_MS,
  });
}

// ── 寫入 ────────────────────────────────────────────────────────────────
/**
 * 寫入成功後三層快取標為過期。`notifications: true`＝簽核類寫入：它會改變待簽核數，所以通知摘要（頂列徽章、Dashboard KPI）
 * 與待審批清單（卡片）一併重抓——否則要等下一輪 30 秒輪詢，卡片、徽章、KPI 會各自停在舊數字（契約 E2E-16 第 5 列）。
 */
function useWrite<TVars, TData>(fn: (vars: TVars) => Promise<TData>, opts: { notifications?: boolean } = {}) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => (opts.notifications ? Promise.all([invalidateTree(qc), qc.invalidateQueries({ queryKey: ["notifications"] })]) : invalidateTree(qc)),
  });
}

export const useCreateProject = () => useWrite((body: CreateProjectRequest) => createProject(body));
export const useUpdateProject = () => useWrite((v: { id: string; body: UpdateProjectRequest }) => updateProject(v.id, v.body));
export const useDeleteProject = () => useWrite((id: string) => deleteProject(id));
/** 復原軟刪除的專案（C-3）：成功後三層快取全部標為過期（專案、目標、任務一併回來）。 */
export const useRestoreProject = () => useWrite((id: string) => restoreProject(id));
export const useSignoffProject = () => useWrite((v: { id: string; approver: string }) => signoffProject(v.id, v.approver), { notifications: true });

export const useCreateGoal = () => useWrite((v: { projectId: string; body: CreateGoalRequest }) => createGoal(v.projectId, v.body));
export const useUpdateGoal = () => useWrite((v: { id: string; body: UpdateGoalRequest }) => updateGoal(v.id, v.body));
export const useDeleteGoal = () => useWrite((id: string) => deleteGoal(id));
export const useSignoffGoal = () => useWrite((v: { id: string; approver: string }) => signoffGoal(v.id, v.approver), { notifications: true });

export const useCreateTask = () => useWrite((v: { goalId: string; body: CreateTaskRequest }) => createTask(v.goalId, v.body));
export const useUpdateTask = () => useWrite((v: { id: string; body: UpdateTaskRequest }) => updateTask(v.id, v.body));
export const useDeleteTask = () => useWrite((id: string) => deleteTask(id));
export const useRetryTask = () => useWrite((id: string) => retryTask(id));
export const useSignoffTask = () => useWrite((v: { id: string; approver: string }) => signoffTask(v.id, v.approver), { notifications: true });

/**
 * 目標拖曳排序：先樂觀改寫專案詳情快取內的目標順序（畫面立即換位），
 * 再送 PUT /goals/reorder；失敗時重新抓取還原，並由呼叫端 toast 錯誤。
 */
export function useReorderGoals(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderedGoalIds: string[]) => reorderGoals(projectId, orderedGoalIds),
    onMutate: async (orderedGoalIds) => {
      await qc.cancelQueries({ queryKey: qk.project(projectId) });
      const previous = qc.getQueryData<ProjectDetail>(qk.project(projectId));
      if (previous) {
        const byId = new Map(previous.goals.map((g) => [g.id, g]));
        const goals = orderedGoalIds
          .map((id, index) => {
            const g = byId.get(id);
            return g ? { ...g, sortOrder: index } : undefined;
          })
          .filter((g): g is NonNullable<typeof g> => Boolean(g));
        qc.setQueryData<ProjectDetail>(qk.project(projectId), { ...previous, goals });
      }
      return { previous };
    },
    onError: (_error, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(qk.project(projectId), ctx.previous);
    },
    onSettled: () => invalidateTree(qc),
  });
}

// ══ 通知摘要（契約 §1.4）══════════════════════════════════════════════════════
/**
 * 跨專案的待辦計數：頂列 signoff 佇列鈕（pendingSignoffs）、通知鈴（pendingReviews＋unacknowledgedAlerts）、
 * Dashboard「待審批草案數」KPI 共用同一份快取；Bridge 連線點（bridgeConnected／bridgeCheckedAt）也讀這份。
 */
export function useNotificationSummary() {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.notifications,
    queryFn: ({ signal }) => getNotificationSummary({ signal }),
    enabled,
    // 元件重新掛載時，10 秒內不重抓（輪詢地板）
    staleTime: NOTIFICATION_POLL_FLOOR_MS,
    refetchInterval: NOTIFICATION_POLL_MS,
  });
}

// ══ BRD/PRD 匯入（契約 §1.1）═════════════════════════════════════════════════
/** 匯入記錄變動後：列表、詳情與通知摘要（pendingSignoffs 含 PARSED／REVIEWING 的匯入草案）都要重抓。 */
function invalidateImports(qc: QueryClient): Promise<unknown> {
  return Promise.all([qc.invalidateQueries({ queryKey: ["imports"] }), qc.invalidateQueries({ queryKey: ["notifications"] })]);
}

/** 把變動直接合併進已快取的匯入詳情（畫面立即更新，不等重抓）；快取裡沒有就略過，交給重抓。 */
function patchImportDetail(qc: QueryClient, id: string, patch: Partial<ImportRecordDetail>): void {
  qc.setQueryData<ImportRecordDetail>(qk.importDetail(id), (old) => (old ? { ...old, ...patch } : old));
}

/**
 * parse／PUT result 成功：狀態、樹與路徑更新；兩者都會撤銷 signoff 並清掉上一次的有界閘錯誤（契約 §1.1.3、§1.1.4）；
 * 記錄的 warnings 也以這次回傳的值覆寫（v1.2，C-10：重開記錄時黃色解析提示以記錄上的 warnings 為準）。
 */
function parseResultPatch(r: ParseResult): Partial<ImportRecordDetail> {
  return {
    status: r.status,
    signedOff: r.signedOff,
    signedOffBy: undefined,
    signedOffAt: undefined,
    parsedResult: r.parsedResult,
    parsePath: r.path,
    aiModel: r.aiModel,
    tokenUsed: r.tokenUsed,
    lastParseErrors: [],
    warnings: r.warnings ?? [],
  };
}

export function useImports(params: ListImportsParams) {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.imports(params),
    queryFn: ({ signal }) => listImports(params, { signal }),
    enabled,
    placeholderData: keepPreviousData,
  });
}

/** 匯入詳情；PARSING 中（例如重新整理後回到正在解析的記錄）以 10 秒（輪詢地板）追蹤到狀態改變。 */
export function useImportDetail(id: string | undefined) {
  const enabled = useEnabled(Boolean(id));
  return useQuery({
    queryKey: qk.importDetail(id ?? ""),
    queryFn: ({ signal }) => getImport(id as string, { signal }),
    enabled,
    refetchInterval: (query) => (query.state.data?.status === "PARSING" ? NOTIFICATION_POLL_FLOOR_MS : false),
  });
}

export function useUploadImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadImport(file),
    onSuccess: (record) => {
      // 先放一份基底詳情（原文要等重抓才有），讓接下來的解析流程馬上有東西可合併
      qc.setQueryData<ImportRecordDetail>(qk.importDetail(record.id), {
        ...record,
        sourceContent: "",
        parsedResult: null,
        warnings: [],
        parseOptions: null,
      });
      return invalidateImports(qc);
    },
  });
}

export function useImportText() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TextImportRequest) => importText(body),
    onSuccess: (record, body) => {
      qc.setQueryData<ImportRecordDetail>(qk.importDetail(record.id), {
        ...record,
        sourceContent: body.content,
        parsedResult: null,
        warnings: [],
        parseOptions: null,
      });
      return invalidateImports(qc);
    },
  });
}

/** 成功與失敗都要重抓：失敗的有界閘 422 會把 errors 寫進 lastParseErrors（契約 §1.1.3）。 */
export function useParseImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; options: ParseOptions }) => parseImport(v.id, v.options),
    // 伺服器在進入 PARSING 時就把本次選項存進記錄（不論成敗，契約 §1.1.3）；成功時先在快取內同步，失敗由 onSettled 重抓
    onSuccess: (result, v) => patchImportDetail(qc, v.id, { ...parseResultPatch(result), parseOptions: v.options }),
    onSettled: () => invalidateImports(qc),
  });
}

export function useEditImportResult() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; parsedResult: ParsedResult }) => editImportResult(v.id, v.parsedResult),
    onSuccess: (result, v) => patchImportDetail(qc, v.id, parseResultPatch(result)),
    onSettled: () => invalidateImports(qc),
  });
}

export function useSignoffImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; approver: string }) => signoffImport(v.id, v.approver),
    onSuccess: (record, v) =>
      patchImportDetail(qc, v.id, {
        status: record.status,
        signedOff: record.signedOff,
        signedOffBy: record.signedOffBy,
        signedOffAt: record.signedOffAt,
      }),
    onSettled: () => invalidateImports(qc),
  });
}

/** 確認匯入會建立專案／目標／任務：三層快取一併標為過期。 */
export function useConfirmImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => confirmImport(id),
    onSuccess: () => Promise.all([invalidateTree(qc), invalidateImports(qc)]),
  });
}

export function useRejectImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => rejectImport(id),
    onSuccess: (record, id) => patchImportDetail(qc, id, { status: record.status }),
    onSettled: () => invalidateImports(qc),
  });
}

// ══ 系統參數（契約 §1.5）═════════════════════════════════════════════════════
/** 全部參數（加密值遮罩）。ADMIN 揭露明文是一次性的 listSettingsByCategory({reveal:true})，不進快取。 */
export function useSettings() {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.settings,
    queryFn: ({ signal }) => listSettings({ signal }),
    enabled,
    staleTime: NOTIFICATION_POLL_FLOOR_MS,
  });
}

/** 單一分類（匯入頁讀 agent.defaultAutonomyLevel 當預設值；契約 §4.1 I-04）。 */
export function useSettingsCategory(category: ConfigCategory) {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.settingsCategory(category),
    queryFn: ({ signal }) => listSettingsByCategory(category, { signal }),
    enabled,
    staleTime: 60_000,
    retry: false,
  });
}

export function useSettingsHistory(params: ListSettingsHistoryParams) {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.settingsHistory(params),
    queryFn: ({ signal }) => listSettingsHistory(params, { signal }),
    enabled,
    placeholderData: keepPreviousData,
  });
}

/** 參數、分類與修改歷史快取全部標為過期（逐鍵儲存／重置做完後呼叫一次，避免每鍵各重抓一輪）。 */
export function invalidateSettings(qc: QueryClient): Promise<unknown> {
  return qc.invalidateQueries({ queryKey: ["settings"] });
}

/** 把伺服器回傳的最新參數直接合併進「全部參數」快取（以分類＋鍵對應）：畫面立即是新值，不等重抓、不閃回舊值。 */
function patchSettings(qc: QueryClient, updated: readonly Config[]): void {
  qc.setQueryData<Record<ConfigCategory, Config[]>>(qk.settings, (old) => {
    if (!old) return old;
    const next = { ...old };
    for (const u of updated) {
      next[u.category] = (next[u.category] ?? []).map((c) => (c.key === u.key ? u : c));
    }
    return next;
  });
}

/**
 * 設定寫入類 mutation 成功時只合併快取（patchSettings），不自動失效：設定頁逐鍵儲存時，
 * 由頁面在整批做完（或停在失敗那鍵）後呼叫 invalidateSettings 一次，讓修改歷史與其他分類快取一併更新。
 */
export function useUpdateSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { category: ConfigCategory; key: string; body: UpdateConfigRequest }) => updateSetting(v.category, v.key, v.body),
    onSuccess: (config) => patchSettings(qc, [config]),
  });
}
export function useUpdateTokenGuard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TokenGuardRequest) => updateTokenGuard(body),
    onSuccess: (configs) => patchSettings(qc, configs),
  });
}
export function useResetSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { category: ConfigCategory; key: string; confirm?: boolean }) => resetSetting(v.category, v.key, v.confirm),
    onSuccess: (config) => patchSettings(qc, [config]),
  });
}
export function useResetCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { category: ConfigCategory; confirm?: boolean }) => resetCategory(v.category, v.confirm),
    onSuccess: (configs) => patchSettings(qc, configs),
  });
}
export const useTestConnection = () => useMutation({ mutationFn: (body?: TestConnectionRequest) => testConnection(body) });
/** 匯出設定（ADMIN）：回 Blob＋檔名，由呼叫端觸發下載（apiDownload；不包封包）。 */
export const useExportSettings = () => useMutation({ mutationFn: () => exportSettings() });
export function useImportSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => importSettings(file),
    onSuccess: () => invalidateSettings(qc),
  });
}

// ══ 專案執行（契約 §1.2）═════════════════════════════════════════════════════
/** 批次詳情的保險輪詢：SSE 才是即時來源，這條只在 SSE 斷線時兜底；終態不輪詢。遠高於契約的 10 秒地板。 */
export const EXECUTION_POLL_MS = 15_000;
export const DAG_POLL_MS = 20_000;
export const STEPS_PAGE_SIZE = 200;
/** 時間軸最多取幾頁步驟（每頁 200）：避免超長批次拖垮輪詢與限流額度。 */
export const STEPS_MAX_PAGES = 5;

/** 批次的狀態或專案狀態改變後要重抓的東西：批次列表／詳情／DAG／專案三層（專案會 EXECUTING⇄READY）／通知摘要。 */
export function invalidateRuns(qc: QueryClient): Promise<unknown> {
  return Promise.all([qc.invalidateQueries({ queryKey: ["executions"] }), invalidateTree(qc), qc.invalidateQueries({ queryKey: ["notifications"] })]);
}

/** 專案的執行批次列表（預設最新在前）；執行頁與監控頁的批次下拉、Dashboard 的最新批次進度共用。 */
export function useProjectExecutions(projectId: string | undefined, params: ListExecutionsParams = { size: 20, sort: "startedAt,desc" }, opts: { pollMs?: number | false } = {}) {
  const enabled = useEnabled(Boolean(projectId));
  return useQuery({
    queryKey: qk.executions(projectId ?? "", params),
    queryFn: ({ signal }) => listProjectExecutions(projectId as string, params, { signal }),
    enabled,
    staleTime: 5_000,
    refetchInterval: opts.pollMs ?? false,
  });
}

/** 批次詳情（含待審核項與 Bridge 連線資訊）；SSE 事件會直接修補這份快取，這裡的輪詢只是兜底。 */
export function useExecution(runId: string | undefined | null) {
  const enabled = useEnabled(Boolean(runId));
  return useQuery({
    queryKey: qk.execution(runId ?? ""),
    queryFn: ({ signal }) => getExecution(runId as string, { signal }),
    enabled,
    staleTime: 2_000,
    refetchInterval: (query) => (isRunTerminal(query.state.data?.status) ? false : EXECUTION_POLL_MS),
  });
}

/** DAG（節點狀態是讀取當下的現況）；批次進行中才輪詢，即時變化靠 SSE 疊加。 */
export function useExecutionDag(runId: string | undefined | null, live: boolean) {
  const enabled = useEnabled(Boolean(runId));
  return useQuery({
    queryKey: qk.dag(runId ?? ""),
    queryFn: ({ signal }) => getExecutionDag(runId as string, { signal }),
    enabled,
    staleTime: 5_000,
    refetchInterval: live ? DAG_POLL_MS : false,
  });
}

/** 斷點列表：只在還原對話框開著時才查。 */
export function useCheckpoints(runId: string | undefined | null, open: boolean) {
  const enabled = useEnabled(Boolean(runId) && open);
  return useQuery({
    queryKey: qk.checkpoints(runId ?? ""),
    queryFn: ({ signal }) => listExecutionCheckpoints(runId as string, { signal }),
    enabled,
    staleTime: 0,
  });
}

/**
 * 一個批次的全部步驟事件（依 stepNumber＝事件 seq 升冪；事件時間軸的來源，契約 §4.3 M-12）：
 * 以 afterSeq 當游標逐頁取，最多 STEPS_MAX_PAGES 頁。
 */
export function useExecutionSteps(runId: string | undefined | null, pollMs: number | false = false) {
  const enabled = useEnabled(Boolean(runId));
  return useQuery({
    queryKey: qk.steps(runId ?? ""),
    queryFn: async ({ signal }): Promise<ExecutionStep[]> => {
      const out: ExecutionStep[] = [];
      let after = 0;
      for (let i = 0; i < STEPS_MAX_PAGES; i++) {
        const page = await listExecutionSteps(runId as string, { size: STEPS_PAGE_SIZE, afterSeq: after > 0 ? after : undefined }, { signal });
        out.push(...page.content);
        if (page.content.length < STEPS_PAGE_SIZE) break;
        after = page.content[page.content.length - 1].stepNumber;
      }
      return out;
    },
    enabled,
    staleTime: 5_000,
    refetchInterval: pollMs,
  });
}

/** 把控制端點回的快照（ExecutionRun）合併進批次詳情快取：按鈕立刻反映新狀態，不等重抓。 */
function patchDetailFromRun(qc: QueryClient, run: ExecutionRun): void {
  qc.setQueryData<ExecutionRunDetail>(qk.execution(run.id), (old) =>
    old
      ? {
          ...old,
          ...run,
          bridge: { ...old.bridge, status: run.bridgeStatus ?? old.bridge.status },
        }
      : old,
  );
}

/** 啟動執行：成功後批次列表、專案（EXECUTING）、通知摘要全部重抓；呼叫端拿回新批次就切過去。 */
export function useStartExecution() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { projectId: string; body: StartExecutionRequest }) => executeProject(v.projectId, v.body),
    onSuccess: () => invalidateRuns(qc),
  });
}

function useRunControl(fn: (runId: string) => Promise<ExecutionRun>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (run) => {
      patchDetailFromRun(qc, run);
      return invalidateRuns(qc);
    },
  });
}

export const usePauseExecution = () => useRunControl(pauseExecution);
export const useResumeExecution = () => useRunControl(resumeExecution);
export const useCancelExecution = () => useRunControl(cancelExecution);

/** 從歷史斷點還原：成功後原 SSE（終態 run 早已關閉）須重新連線，由 useRunStream 依批次狀態自行重連。 */
export function useRestoreExecution() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { runId: string; checkpointId: string }) => restoreExecution(v.runId, v.checkpointId),
    onSuccess: (run) => {
      patchDetailFromRun(qc, run);
      return invalidateRuns(qc);
    },
  });
}

/**
 * 審核：先樂觀把該審核項從待審核清單拿掉（失敗還原），成功後重抓。
 * 回傳 followUpRunId（SKIP／無還原點的 RETRY 會另開後續批次，契約 §1.2.11）。
 */
export function useReviewExecution() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { runId: string; reviewId: string; decision: ReviewDecision; comment?: string }) =>
      reviewExecution(v.runId, v.reviewId, { decision: v.decision, ...(v.comment ? { comment: v.comment } : {}) }),
    onMutate: async (v) => {
      await qc.cancelQueries({ queryKey: qk.execution(v.runId) });
      const previous = qc.getQueryData<ExecutionRunDetail>(qk.execution(v.runId));
      qc.setQueryData<ExecutionRunDetail>(qk.execution(v.runId), (old) => (old ? { ...old, pendingReviews: old.pendingReviews.filter((r) => r.id !== v.reviewId) } : old));
      return { previous };
    },
    onError: (_error, v, ctx) => {
      if (ctx?.previous) qc.setQueryData(qk.execution(v.runId), ctx.previous);
    },
    onSettled: () => invalidateRuns(qc),
  });
}

// ══ 專案監控（契約 §1.3）═════════════════════════════════════════════════════
/**
 * 監控頁的輪詢間隔：同一使用者所有頁面共用每分鐘 100 次（契約 §0.4 第 4 點），監控頁約 9 個端點一起輪詢，
 * 所以取 max(系統參數 monitor.refreshIntervalMs，15 秒)——契約只規定「不得小於」該參數，取大是允許的；
 * 參數讀不到（例如權限或尚未載入）時用 30 秒。頁面不可見時 TanStack Query 預設暫停輪詢。
 */
export const MONITOR_POLL_FLOOR_MS = 15_000;
export const MONITOR_DEFAULT_POLL_MS = 30_000;

export function useMonitorPollMs(): number {
  const settings = useSettingsCategory("monitor");
  const raw = settings.data?.find((c) => c.key === "refreshIntervalMs")?.value;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? Math.max(MONITOR_POLL_FLOOR_MS, n) : MONITOR_DEFAULT_POLL_MS;
}

/**
 * 監控查詢的「身分」：時間範圍用 id（1h／24h／7d／30d），不用 from／to 時間戳——
 * 時間戳每次都不同，放進查詢鍵會讓每次輪詢都變成新查詢；from／to 在 queryFn 內才依當下時間計算（rangeParams），視窗因此隨時間滾動。
 * runId 省略＝專案全部批次。
 */
export type MonitorQuery = { runId?: string; range: RangeId };
export type LogQuery = MonitorQuery & Pick<ListLogsParams, "level" | "q" | "taskId" | "order" | "page" | "size">;

export function useProjectMetrics(projectId: string | undefined, q: MonitorQuery, pollMs: number | false) {
  const enabled = useEnabled(Boolean(projectId));
  return useQuery({
    queryKey: qk.metrics(projectId ?? "", q),
    queryFn: ({ signal }) => getProjectMetrics(projectId as string, { runId: q.runId, ...rangeParams(q.range) }, { signal }),
    enabled,
    placeholderData: keepPreviousData,
    refetchInterval: pollMs,
  });
}

export function useTokenTrend(projectId: string | undefined, q: MonitorQuery, pollMs: number | false) {
  const enabled = useEnabled(Boolean(projectId));
  return useQuery({
    queryKey: qk.tokenTrend(projectId ?? "", q),
    queryFn: ({ signal }) => getTokenTrend(projectId as string, { runId: q.runId, ...rangeParams(q.range), bucket: bucketFor(q.range) }, { signal }),
    enabled,
    placeholderData: keepPreviousData,
    refetchInterval: pollMs,
  });
}

export function useTaskTrend(projectId: string | undefined, q: MonitorQuery, pollMs: number | false) {
  const enabled = useEnabled(Boolean(projectId));
  return useQuery({
    queryKey: qk.taskTrend(projectId ?? "", q),
    queryFn: ({ signal }) => getTaskTrend(projectId as string, { runId: q.runId, ...rangeParams(q.range), bucket: bucketFor(q.range) }, { signal }),
    enabled,
    placeholderData: keepPreviousData,
    refetchInterval: pollMs,
  });
}

export function useProjectAlerts(projectId: string | undefined, params: ListAlertsParams, pollMs: number | false) {
  const enabled = useEnabled(Boolean(projectId));
  return useQuery({
    queryKey: qk.alerts(projectId ?? "", params),
    queryFn: ({ signal }) => listProjectAlerts(projectId as string, params, { signal }),
    enabled,
    placeholderData: keepPreviousData,
    refetchInterval: pollMs,
  });
}

export function useProjectLogs(projectId: string | undefined, q: LogQuery, pollMs: number | false) {
  const enabled = useEnabled(Boolean(projectId));
  return useQuery({
    queryKey: qk.logs(projectId ?? "", q),
    queryFn: ({ signal }) => {
      const { range, ...rest } = q;
      return listProjectLogs(projectId as string, { ...rest, ...rangeParams(range) }, { signal });
    },
    enabled,
    placeholderData: keepPreviousData,
    refetchInterval: pollMs,
  });
}

// ══ AISDLC_SDD 引擎（監控頁「AISDLC_SDD 引擎」卡；契約 §1.7.1、§4.3 M-20；v1.4 D-16）═══════════════════
/** 契約 §1.7.1：前端 30 秒輪詢一次（FSM 檔只在 SDD runtime 執行時才變動，不需要 SSE；30 秒大於輪詢地板 10 秒）。分頁不可見時 TanStack Query 預設暫停。 */
export const SDD_POLL_MS = 30_000;

/**
 * project＝null：不帶 project 的請求，只取版本與 FSM 專案清單（`fsm` 為 null）；選定專案後帶 project 取該專案的 FSM 狀態。
 * 引擎不可用也回 200（`available=false`＋`reason`），所以 isError 只代表 console-api 自己連不上或回了非 2xx。
 * enabled＝false：不發請求、也不輪詢。pollWhile：依最近一份資料決定要不要繼續輪詢（回 false＝停；不給＝一直輪詢）——
 * 卡片選定專案後，不帶 project 的那一份只當「專案清單的底」留在快取，不必再打；清單還是空的（或引擎不可用）時才繼續輪詢等它復原。
 *
 * projectId（v1.5，§1.10.4）＝專案模式：讀「該 Console 專案的專案根」下的 FSM。這時 project＝null 的請求（只帶 projectId）後端會預設取
 * 專案的有效 FSM 專案（sddProject 有值取它，否則專案名），一個請求就帶回 fsm；project 有值＝同一個狀態目錄內改選別的 FSM 專案。
 * 專案不存在或已軟刪除回 404（isError）。兩種模式的快取鍵分開（qk.sddEngine）；節奏不變：每次輪詢只有一個請求。
 */
export function useSddEngine(project: string | null, opts: { pollMs?: number; enabled?: boolean; pollWhile?: (data: SddEngineStatus | undefined) => boolean; projectId?: string } = {}) {
  const authed = useEnabled();
  const interval = opts.pollMs ?? SDD_POLL_MS;
  const pollWhile = opts.pollWhile;
  const projectId = opts.projectId;
  return useQuery({
    queryKey: qk.sddEngine(project, projectId ?? null),
    queryFn: ({ signal }) => getSddEngineStatus({ project: project ?? undefined, projectId }, { signal }),
    enabled: authed && (opts.enabled ?? true),
    refetchInterval: pollWhile ? (query) => (pollWhile(query.state.data) ? interval : false) : interval,
  });
}

/**
 * 一個批次的追溯覆蓋（諮詢視圖；契約 §1.10.3、§4.7.2）：只在 `enabled`（批次進入終態且專案有規格綁定）時查一次——不輪詢、不快取（staleTime 0），
 * 批次因還原再度進入終態時（enabled 由 false 轉 true）重抓。不重試：404 `rtm_not_found` 是「沒有報告」的正常答案（面板顯示中性說明），
 * 422／502／504 由面板的「重試」鈕手動重抓。
 */
export function useExecutionRtm(runId: string | undefined | null, enabled: boolean) {
  const authed = useEnabled(Boolean(runId) && enabled);
  return useQuery({
    queryKey: qk.rtm(runId ?? ""),
    queryFn: ({ signal }) => getExecutionRtm(runId as string, { signal }),
    enabled: authed,
    staleTime: 0,
    retry: false,
    refetchOnWindowFocus: false,
    refetchInterval: false,
  });
}

/** SDD 寫入類動作成功後要重抓的東西：專案三層（綁定三欄在專案詳情）與 FSM 狀態（`["sdd"]` 家族）。 */
function invalidateSddGovernance(qc: QueryClient): Promise<unknown> {
  return Promise.all([invalidateTree(qc), qc.invalidateQueries({ queryKey: ["sdd"] })]);
}

/**
 * 核准凍結（人工閘；契約 §1.10.2）：成功後專案詳情（核准凍結第 5 項可能把標準鍵寫回 sddProject）與 FSM 狀態都標為過期、立即重抓，
 * 畫面不用等 30 秒輪詢。失敗不動快取（呼叫端依 reason 顯示訊息）。
 */
export function useFreezeProjectSdd() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { projectId: string; body: SddFreezeRequest }) => freezeProjectSddSpec(v.projectId, v.body),
    onSuccess: () => invalidateSddGovernance(qc),
  });
}

/** 編輯專案的 FSM 專案（契約 §1.10.7）：`sddProject` 為 null＝清除、回到「用預設」。成功後專案詳情與 FSM 狀態重抓（有效 FSM 專案變了）。 */
export function useUpdateSddBinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { projectId: string; sddProject: string | null }) => updateProjectSddBinding(v.projectId, v.sddProject),
    onSuccess: () => invalidateSddGovernance(qc),
  });
}

/**
 * 確認告警：先樂觀把快取內所有該專案告警列表裡的這一筆標成「已確認」（畫面立刻變「已確認」），
 * 失敗還原並由呼叫端 toast；結束後告警與通知摘要（未確認告警數）重抓。契約：冪等，已確認者再確認仍 204。
 */
export function useAcknowledgeAlert() {
  const qc = useQueryClient();
  const { username } = useAuth();
  return useMutation({
    mutationFn: (alertId: string) => acknowledgeAlert(alertId),
    onMutate: async (alertId) => {
      await qc.cancelQueries({ queryKey: ["monitor", "alerts"] });
      const snapshots = qc.getQueriesData<Alert[]>({ queryKey: ["monitor", "alerts"] });
      const now = new Date().toISOString();
      qc.setQueriesData<Alert[]>({ queryKey: ["monitor", "alerts"] }, (old) =>
        old?.map((a) => (a.id === alertId && !a.acknowledged ? { ...a, acknowledged: true, acknowledgedBy: username || undefined, acknowledgedAt: now } : a)),
      );
      return { snapshots };
    },
    onError: (_error, _alertId, ctx) => {
      for (const [key, data] of ctx?.snapshots ?? []) qc.setQueryData(key, data);
    },
    onSettled: () => Promise.all([qc.invalidateQueries({ queryKey: ["monitor", "alerts"] }), qc.invalidateQueries({ queryKey: ["notifications"] })]),
  });
}

/** 匯出報表：回 Blob＋檔名，由呼叫端觸發下載（apiDownload；不包封包）；CSV 與 PDF 都回 200（v1.2，C-4）。 */
export const useDownloadReport = () => useMutation({ mutationFn: (v: { projectId: string; params: ReportParams }) => downloadProjectReport(v.projectId, v.params) });

// ══ Dashboard 的跨專案聚合（契約 §4.5 G-07、G-08）═══════════════════════════════════
export const DASHBOARD_AGG_POLL_MS = 60_000;

/**
 * 「本週完成任務數」：GET /monitor/task-totals **一次**，取 `completed`（v1.2，C-1；契約 §1.3.8、§4.5 G-08）。
 * from＝本週一 00:00（本機時區）轉 ISO-8601、to 省略＝現在；輪詢每 60 秒 1 次，分頁隱藏時 TanStack Query 預設不輪詢。
 * 取代 v1.1 對各專案（最多 30 個）各打一次 task-trend 再加總的近似做法——那會讓單一總覽分頁穩態每分鐘約 31 次請求、
 * 佔每使用者每分鐘 100 次額度的三成（QA DEF-AC-009）；現在請求數與專案數無關。
 * `completed` 是步驟事件的列數，同一任務被還原重跑會重複計（語意同 task-trend）；畫面狀態由 isPending／isError 表達。
 */
export function useWeekCompletedTasks(weekStartIso: string) {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.taskTotals(weekStartIso),
    queryFn: ({ signal }) => getTaskTotals({ from: weekStartIso }, { signal }),
    enabled,
    staleTime: 30_000,
    refetchInterval: DASHBOARD_AGG_POLL_MS,
  });
}

/** 各「執行中」專案的最新批次（size=1）：Dashboard 的「執行中 run 數」與「進行中的執行」進度條。 */
export function useLatestRuns(projectIds: readonly string[]) {
  const enabled = useEnabled();
  const results = useQueries({
    queries: projectIds.map((id) => ({
      queryKey: qk.executions(id, { size: 1 }),
      queryFn: ({ signal }: { signal: AbortSignal }) => listProjectExecutions(id, { size: 1 }, { signal }),
      enabled,
      staleTime: 10_000,
      refetchInterval: DASHBOARD_AGG_POLL_MS / 2,
    })),
  });
  const byProject: Record<string, ExecutionRunSummary | undefined> = {};
  projectIds.forEach((id, i) => {
    byProject[id] = results[i]?.data?.content?.[0];
  });
  return { byProject, loading: enabled && results.some((r) => r.isPending) };
}

// ══ SelfImproving 唯讀鏡像（P1b；TCS-SelfImprovingMirror-P1b R11、R12、R15）══════════════════════════
/**
 * SI 查詢的共同設定，覆寫 Providers 的預設（5 秒 staleTime、5xx 重試一次）：
 *  - retry: false——失敗只呼叫一次，原因要讓人看到，不靠重試把錯誤藏起來；
 *  - staleTime: 0、gcTime: 0——不留過期快取：面板卸載即丟，重掛先顯示載入中，不先顯示上一次的資料；
 *  - 不輪詢、不因視窗聚焦重抓：資料只在「重新整理」或「重試」時更新（帳本是人與 agent 手動推進的，沒有即時串流）。
 */
export const SI_QUERY_OPTIONS = { retry: false, staleTime: 0, gcTime: 0, refetchInterval: false, refetchOnWindowFocus: false } as const;

/** 狀態橫幅：`status` 單頁。 */
export function useSiStatus() {
  const enabled = useEnabled();
  return useQuery({
    queryKey: qk.siStatus,
    queryFn: ({ signal }) => getSiStatus({ signal }),
    enabled,
    ...SI_QUERY_OPTIONS,
  });
}

/**
 * 游標分頁的清單查詢：第一頁只帶 `limit`，之後每頁帶 `since=<上一頁的 nextSince>` 與同一個 `limit`（R15）。
 * 只有「回應 truncated 為真且 nextSince 是數字」才有下一頁；合併（依身分鍵去重）由呼叫端用 lib/domain/si.ts 的 mergePages 做。
 */
function useSiPages<T>(queryKey: readonly string[], fetchPage: (opts: SiListParams & { signal?: AbortSignal }) => Promise<SiPage<T>>) {
  const enabled = useEnabled();
  return useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam, signal }) => fetchPage({ since: pageParam ?? undefined, limit: SI_PAGE_LIMIT, signal }),
    initialPageParam: null as number | null,
    getNextPageParam: (last) => (last.truncated && typeof last.nextSince === "number" ? last.nextSince : undefined),
    enabled,
    ...SI_QUERY_OPTIONS,
  });
}

export const useSiObservations = () => useSiPages(qk.siObservations, getSiObservations);
export const useSiProposals = () => useSiPages(qk.siProposals, getSiProposals);
export const useSiEvents = () => useSiPages(qk.siEvents, getSiEvents);
export const useSiRuns = () => useSiPages(qk.siRuns, getSiRuns);

// ══ SelfImproving 寫入載體（P2b；TCS-SelfImprovingDecide-P2b W16、W21）══════════════════════════════════
/**
 * 對帳讀面（Console 稽核列與帳本的對帳）：**只有 ADMIN 啟用**——非 ADMIN 零 `console-writes` 請求（W21；後端雖允許 VIEWER 以上讀，
 * Console 不給非 ADMIN 看，也不替他們多打一個請求）。沿用 SI_QUERY_OPTIONS：不重試、不留快取、不輪詢（頁首「重新整理」與寫入成功後才重抓）。
 */
export function useSiConsoleWrites() {
  const { role } = useAuth();
  const enabled = useEnabled(role === "ADMIN");
  return useQuery({
    queryKey: qk.siConsoleWrites,
    queryFn: ({ signal }) => getSiConsoleWrites({ limit: SI_CONSOLE_WRITES_LIMIT, signal }),
    enabled,
    ...SI_QUERY_OPTIONS,
  });
}

/**
 * 寫入載體的 mutation：成功後使全部 SI 查詢（觀察、提案、事件、運轉、狀態、對帳）失效重取，**不碰** `["notifications"]` 家族——
 * SelfImproving 的寫入不改變待簽核數，不該連帶重抓頂列徽章與 Dashboard。失效不等待重取完成（不回傳 promise）：收據要立刻顯示給使用者，
 * 不能被 Bridge 的 export 子行程拖慢；重取失敗各面板自己顯示錯誤態。
 * `invalidate: false` 給預檢：它零副作用（不寫 DB、不落檔），成功不代表任何資料變了，重取只是白白多打一輪請求。
 */
function useSiWrite<TVars, TData>(fn: (vars: TVars) => Promise<TData>, opts: { invalidate?: boolean } = {}) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      if (opts.invalidate !== false) void qc.invalidateQueries({ queryKey: qk.siAll });
    },
  });
}

export const useSiDecide = () => useSiWrite((v: { id: string; body: SiDecideRequest }) => postSiDecide(v.id, v.body));
export const useSiAddObservation = () => useSiWrite((body: SiObservationRequest) => postSiObservation(body));
export const useSiCloseObservation = () => useSiWrite((v: { id: string; body: SiCloseRequest }) => postSiObservationClose(v.id, v.body));
export const useSiValidateObservation = () => useSiWrite((body: SiObservationRequest) => postSiObservationValidate(body), { invalidate: false });
