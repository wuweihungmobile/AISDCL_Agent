/**
 * 領域型別別名：一律取自 openapi-typescript 產生的 schema.d.ts（單一出處），
 * 元件與 hooks 不直接碰 components["schemas"][...] 這種長字串。
 */
import type { components } from "./schema";

type S = components["schemas"];

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
