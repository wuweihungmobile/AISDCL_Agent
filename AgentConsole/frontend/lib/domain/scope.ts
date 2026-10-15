/**
 * 執行範圍選取模型（契約 §1.2.1「範圍解析」、§4.2 E-05、§4.6 G-E1；PRD US-E-02）。純函式、不依賴 React。
 *
 * 選取以「目標 id → true（整個目標）｜任務 id 陣列（只選其中幾個任務）」表示；沒出現＝沒選。
 * 轉成請求：
 *  - 全部「可執行」的目標都整個選了 → { mode: "ALL" }（ALL 時不可帶 goalIds／taskIds）；
 *  - 否則 { mode: "SELECTED", goalIds（整個選的目標）, taskIds（只選部分任務的目標底下被選的任務）}。
 * 已 COMPLETED／SKIPPED 的目標與任務不可選：後端在 SELECTED 裡遇到它們會回 409「所選任務或目標已完成」（契約 §1.2.1 第 7a 項）。
 */
import type { ExecutionScope, GoalBrief, TaskStatus, TaskSummary } from "@/lib/api/types";

export type Selection = Record<string, true | string[]>;
export type CheckState = "all" | "some" | "none";

export type ScopeGoal = Pick<GoalBrief, "id" | "name" | "status" | "signedOff" | "taskCount">;
export type ScopeTask = Pick<TaskSummary, "id" | "name" | "status" | "signedOff">;

const DONE_GOAL = new Set(["COMPLETED", "SKIPPED"]);
const DONE_TASK = new Set<TaskStatus>(["COMPLETED", "SKIPPED"]);

export const isGoalRunnable = (goal: Pick<ScopeGoal, "status">): boolean => !DONE_GOAL.has(goal.status);
export const isTaskRunnable = (task: Pick<ScopeTask, "status">): boolean => !DONE_TASK.has(task.status);

/** 預設：全部可執行的目標都整個選中（＝mode ALL）。 */
export function initialSelection(goals: readonly ScopeGoal[]): Selection {
  const sel: Selection = {};
  for (const g of goals) if (isGoalRunnable(g)) sel[g.id] = true;
  return sel;
}

export function goalCheckState(sel: Selection, goal: ScopeGoal): CheckState {
  const cur = sel[goal.id];
  if (cur === true) return "all";
  return cur && cur.length > 0 ? "some" : "none";
}

export function allCheckState(sel: Selection, goals: readonly ScopeGoal[]): CheckState {
  const runnable = goals.filter(isGoalRunnable);
  if (runnable.length === 0) return "none";
  const states = runnable.map((g) => goalCheckState(sel, g));
  if (states.every((s) => s === "all")) return "all";
  return states.every((s) => s === "none") ? "none" : "some";
}

/** 勾／取消整個目標：目前有選（整個或部分）→ 取消；沒選 → 整個選中。 */
export function toggleGoal(sel: Selection, goal: ScopeGoal): Selection {
  if (!isGoalRunnable(goal)) return sel;
  const next = { ...sel };
  if (next[goal.id] !== undefined) delete next[goal.id];
  else next[goal.id] = true;
  return next;
}

/** 勾「全部目標」：已全選 → 全部取消；否則全部可執行的目標整個選中。 */
export function toggleAll(sel: Selection, goals: readonly ScopeGoal[]): Selection {
  return allCheckState(sel, goals) === "all" ? {} : initialSelection(goals);
}

/**
 * 勾／取消單一任務。tasksOfGoal＝該目標底下已載入的任務（展開後才有）：
 *  - 整個目標原本是選中的：取消其中一個任務＝改成「其餘可執行任務」的陣列；
 *  - 部分選取：切換該任務；選滿所有可執行任務就收斂回「整個目標」，全取消就移除該目標。
 */
export function toggleTask(sel: Selection, goal: ScopeGoal, task: ScopeTask, tasksOfGoal: readonly ScopeTask[]): Selection {
  if (!isTaskRunnable(task)) return sel;
  const runnable = tasksOfGoal.filter(isTaskRunnable).map((t) => t.id);
  const cur = sel[goal.id];
  const picked = new Set<string>(cur === true ? runnable : (cur ?? []));
  if (picked.has(task.id)) picked.delete(task.id);
  else picked.add(task.id);
  const next = { ...sel };
  if (picked.size === 0) delete next[goal.id];
  else if (runnable.length > 0 && runnable.every((id) => picked.has(id))) next[goal.id] = true;
  else next[goal.id] = runnable.filter((id) => picked.has(id));
  return next;
}

/** 任務在選取模型裡的勾選狀態（任務沒被個別選、但整個目標選了＝勾）。 */
export function isTaskChecked(sel: Selection, goalId: string, taskId: string): boolean {
  const cur = sel[goalId];
  return cur === true || (Array.isArray(cur) && cur.includes(taskId));
}

export type BuiltScope = {
  /** 沒選任何東西時為 null（不可啟動） */
  scope: ExecutionScope | null;
  goalIds: string[];
  taskIds: string[];
};

export function buildScope(sel: Selection, goals: readonly ScopeGoal[]): BuiltScope {
  const goalIds: string[] = [];
  const taskIds: string[] = [];
  for (const g of goals) {
    if (!isGoalRunnable(g)) continue;
    const cur = sel[g.id];
    if (cur === true) goalIds.push(g.id);
    else if (cur) taskIds.push(...cur);
  }
  if (goalIds.length === 0 && taskIds.length === 0) return { scope: null, goalIds, taskIds };
  const runnable = goals.filter(isGoalRunnable);
  const everyGoalWhole = runnable.length > 0 && runnable.every((g) => sel[g.id] === true);
  if (everyGoalWhole) return { scope: { mode: "ALL" }, goalIds, taskIds };
  return { scope: { mode: "SELECTED", goalIds, taskIds }, goalIds, taskIds };
}

export type LockReport = {
  /** 專案本身未 signoff */
  projectUnsigned: boolean;
  /** 範圍內未 signoff 的目標（名稱） */
  unsignedGoals: string[];
  /** 範圍內未 signoff 的任務（已載入者；其餘由後端 409 的 details.unsignedTaskIds 補上） */
  unsignedTasks: string[];
  locked: boolean;
};

/**
 * 啟動鎖定判斷（契約 §4.2 E-02：專案、所選目標、所選任務皆 signedOff 才可啟動）。
 * 任務層級只看「已載入」的任務（展開過的目標）；沒載入的由後端 409 的 details 兜底。
 */
export function lockReport(
  projectSigned: boolean,
  goals: readonly ScopeGoal[],
  sel: Selection,
  tasksByGoal: Readonly<Record<string, readonly ScopeTask[] | undefined>>,
): LockReport {
  const unsignedGoals: string[] = [];
  const unsignedTasks: string[] = [];
  for (const g of goals) {
    const cur = sel[g.id];
    if (cur === undefined || !isGoalRunnable(g)) continue;
    // 只在「整個目標被選」時要求目標本身已 signoff；只選其中幾個任務時，不替後端多設一道（後端 409 會說明）
    if (cur === true && !g.signedOff) unsignedGoals.push(g.name);
    const tasks = tasksByGoal[g.id] ?? [];
    for (const t of tasks) {
      if (t.signedOff || !isTaskRunnable(t)) continue;
      if (cur === true || cur.includes(t.id)) unsignedTasks.push(t.name);
    }
  }
  return {
    projectUnsigned: !projectSigned,
    unsignedGoals,
    unsignedTasks,
    locked: !projectSigned || unsignedGoals.length > 0 || unsignedTasks.length > 0,
  };
}
