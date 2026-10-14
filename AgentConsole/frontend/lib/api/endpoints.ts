/**
 * 每個後端端點一個函式；名稱對應 PRD §7.1（API-PRJ／GOL／TSK／SGN／AUTH）。
 * 型別來自 schema.d.ts（openapi-typescript 產生）；這裡不做快取、不碰 React，
 * 快取與失效策略在 lib/api/queries.ts（TanStack Query）。
 */
import { apiRequest } from "./client";
import type {
  CreateGoalRequest,
  CreateProjectRequest,
  CreateTaskRequest,
  GoalDetail,
  GoalResponse,
  GoalSummary,
  ListProjectsParams,
  PageData,
  ProjectDetail,
  ProjectResponse,
  ProjectSummary,
  TaskDetail,
  TaskResponse,
  TaskSummary,
  TokenResponse,
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
