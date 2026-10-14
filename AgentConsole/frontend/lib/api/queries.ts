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
  createGoal,
  createProject,
  createTask,
  deleteGoal,
  deleteProject,
  deleteTask,
  getGoal,
  getProject,
  getTask,
  listGoals,
  listProjects,
  listTasks,
  reorderGoals,
  retryTask,
  signoffGoal,
  signoffProject,
  signoffTask,
  updateGoal,
  updateProject,
  updateTask,
} from "./endpoints";
import type {
  CreateGoalRequest,
  CreateProjectRequest,
  CreateTaskRequest,
  ListProjectsParams,
  ProjectDetail,
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
};

const POLL_MS = 30_000;

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
 * 取捨：只對「草案專案」逐一查目標（草案通常很少）；已簽核專案底下以 draft 建立的目標不在此佇列
 * （後端 W3-B 的 GET /notifications/summary 落地後可改吃計數端點）。
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
