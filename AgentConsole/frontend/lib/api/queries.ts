"use client";

/**
 * TanStack Query 層：查詢鍵、讀取 hooks、寫入 mutations。
 *  - 全部 client-side；查詢在已登入（status==="authed"）後才啟用。
 *  - 專案／目標／任務三層的計數互相牽動（goalsCount、tasksDone…），任何寫入成功就把三層快取全部標為過期，
 *    資料量小，換取「不會顯示過期計數」的簡單正確性。
 */
import {
  keepPreviousData,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthProvider";
import {
  confirmImport,
  createGoal,
  createProject,
  createTask,
  deleteGoal,
  deleteProject,
  deleteTask,
  editImportResult,
  exportSettings,
  getGoal,
  getImport,
  getNotificationSummary,
  getProject,
  getTask,
  importSettings,
  importText,
  listGoals,
  listImports,
  listProjects,
  listSettings,
  listSettingsByCategory,
  listSettingsHistory,
  listTasks,
  parseImport,
  rejectImport,
  reorderGoals,
  resetCategory,
  resetSetting,
  retryTask,
  signoffGoal,
  signoffImport,
  signoffProject,
  signoffTask,
  testConnection,
  updateGoal,
  updateProject,
  updateSetting,
  updateTask,
  updateTokenGuard,
  uploadImport,
} from "./endpoints";
import type {
  Config,
  ConfigCategory,
  CreateGoalRequest,
  CreateProjectRequest,
  CreateTaskRequest,
  ImportRecordDetail,
  ListImportsParams,
  ListProjectsParams,
  ListSettingsHistoryParams,
  ParseOptions,
  ParsedResult,
  ParseResult,
  ProjectDetail,
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
  settings: ["settings", "all"] as const,
  settingsCategory: (category: ConfigCategory) => ["settings", "category", category] as const,
  settingsHistory: (params: ListSettingsHistoryParams) => ["settings", "history", params] as const,
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
  return Promise.all([
    qc.invalidateQueries({ queryKey: ["projects"] }),
    qc.invalidateQueries({ queryKey: ["goals"] }),
    qc.invalidateQueries({ queryKey: ["tasks"] }),
  ]);
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

// ── 待人工審批佇列（頂列 signoff 鈕徽章、Dashboard「待人工審批」卡共用）──────────
export type SignoffItem = {
  kind: "project" | "goal";
  id: string;
  projectId: string;
  name: string;
  meta: string;
};

/**
 * signedOff=false 的專案，加上這些草案專案底下 signedOff=false 的目標。
 * 取捨：只對「草案專案」逐一查目標（草案通常很少）；已簽核專案底下以 draft 建立的目標不在此佇列。
 * 計數已改走 GET /notifications/summary 的 pendingSignoffs（頂列徽章與 Dashboard KPI 用它，跨專案且含任務與匯入草案）；
 * 本 hook 只剩「待人工審批」卡的清單用途（可直接點「審批」的專案／目標）。
 */
export function useSignoffQueue(): { items: SignoffItem[]; count: number; isLoading: boolean } {
  const all = useAllProjects();
  const enabled = useEnabled();
  const drafts = (all.data?.content ?? []).filter((p) => !p.signedOff);
  const goalQueries = useQueries({
    queries: drafts.map((p) => ({
      queryKey: qk.goals(p.id),
      queryFn: ({ signal }: { signal: AbortSignal }) => listGoals(p.id, { signal }),
      enabled,
      staleTime: 15_000,
    })),
  });

  const items: SignoffItem[] = [];
  drafts.forEach((p, idx) => {
    items.push({
      kind: "project",
      id: p.id,
      projectId: p.id,
      name: p.name,
      meta: `AI 草案 · ${p.goalsCount} 目標 / ${p.tasksCount} 任務`,
    });
    for (const g of goalQueries[idx]?.data ?? []) {
      if (!g.signedOff) {
        items.push({
          kind: "goal",
          id: g.id,
          projectId: p.id,
          name: g.name,
          meta: `目標草案 · ${p.name} · ${g.taskCount} 任務`,
        });
      }
    }
  });
  return {
    items,
    count: items.length,
    isLoading: all.isLoading || goalQueries.some((q) => q.isLoading),
  };
}

// ── 寫入 ────────────────────────────────────────────────────────────────
function useWrite<TVars, TData>(fn: (vars: TVars) => Promise<TData>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => invalidateTree(qc),
  });
}

export const useCreateProject = () => useWrite((body: CreateProjectRequest) => createProject(body));
export const useUpdateProject = () =>
  useWrite((v: { id: string; body: UpdateProjectRequest }) => updateProject(v.id, v.body));
export const useDeleteProject = () => useWrite((id: string) => deleteProject(id));
export const useSignoffProject = () =>
  useWrite((v: { id: string; approver: string }) => signoffProject(v.id, v.approver));

export const useCreateGoal = () =>
  useWrite((v: { projectId: string; body: CreateGoalRequest }) => createGoal(v.projectId, v.body));
export const useUpdateGoal = () =>
  useWrite((v: { id: string; body: UpdateGoalRequest }) => updateGoal(v.id, v.body));
export const useDeleteGoal = () => useWrite((id: string) => deleteGoal(id));
export const useSignoffGoal = () =>
  useWrite((v: { id: string; approver: string }) => signoffGoal(v.id, v.approver));

export const useCreateTask = () =>
  useWrite((v: { goalId: string; body: CreateTaskRequest }) => createTask(v.goalId, v.body));
export const useUpdateTask = () =>
  useWrite((v: { id: string; body: UpdateTaskRequest }) => updateTask(v.id, v.body));
export const useDeleteTask = () => useWrite((id: string) => deleteTask(id));
export const useRetryTask = () => useWrite((id: string) => retryTask(id));
export const useSignoffTask = () =>
  useWrite((v: { id: string; approver: string }) => signoffTask(v.id, v.approver));

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
  return Promise.all([
    qc.invalidateQueries({ queryKey: ["imports"] }),
    qc.invalidateQueries({ queryKey: ["notifications"] }),
  ]);
}

/** 把變動直接合併進已快取的匯入詳情（畫面立即更新，不等重抓）；快取裡沒有就略過，交給重抓。 */
function patchImportDetail(qc: QueryClient, id: string, patch: Partial<ImportRecordDetail>): void {
  qc.setQueryData<ImportRecordDetail>(qk.importDetail(id), (old) => (old ? { ...old, ...patch } : old));
}

/** parse／PUT result 成功：狀態、樹與路徑更新；兩者都會撤銷 signoff 並清掉上一次的有界閘錯誤（契約 §1.1.3、§1.1.4）。 */
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
      qc.setQueryData<ImportRecordDetail>(qk.importDetail(record.id), { ...record, sourceContent: "", parsedResult: null });
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
    onSuccess: (result, v) => patchImportDetail(qc, v.id, parseResultPatch(result)),
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
    mutationFn: (v: { category: ConfigCategory; key: string; body: UpdateConfigRequest }) =>
      updateSetting(v.category, v.key, v.body),
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
    mutationFn: (v: { category: ConfigCategory; key: string; confirm?: boolean }) =>
      resetSetting(v.category, v.key, v.confirm),
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
export const useTestConnection = () =>
  useMutation({ mutationFn: (body?: TestConnectionRequest) => testConnection(body) });
/** 匯出設定（ADMIN）：回 Blob＋檔名，由呼叫端觸發下載（apiDownload；不包封包）。 */
export const useExportSettings = () => useMutation({ mutationFn: () => exportSettings() });
export function useImportSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => importSettings(file),
    onSuccess: () => invalidateSettings(qc),
  });
}
