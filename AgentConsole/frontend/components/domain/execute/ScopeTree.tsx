"use client";

import { ChevronDown, ChevronRight } from "lucide-react";

import { Tag } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { taskStatus } from "@/lib/domain/status";
import {
  allCheckState,
  goalCheckState,
  isGoalRunnable,
  isTaskChecked,
  isTaskRunnable,
  toggleAll,
  toggleGoal,
  toggleTask,
  type CheckState,
  type ScopeGoal,
  type ScopeTask,
  type Selection,
} from "@/lib/domain/scope";

const toChecked = (state: CheckState): boolean | "indeterminate" => (state === "all" ? true : state === "some" ? "indeterminate" : false);

/**
 * 執行範圍 checkbox 樹（設計稿畫面 7「執行範圍」；契約 §4.2 E-05、§4.6 G-E1）：
 * 「全部目標」→ 各目標（顯示「(N tasks)」）→ 展開看任務。全選＝mode ALL；其餘＝SELECTED（goalIds／taskIds，見 lib/domain/scope.ts）。
 * 已完成／跳過的目標與任務不可選（後端在 SELECTED 遇到會 409「所選任務或目標已完成」）。
 */
export function ScopeTree({
  goals,
  selection,
  onChange,
  expanded,
  onToggleExpand,
  tasksByGoal,
  tasksLoading,
  disabled,
}: {
  goals: readonly ScopeGoal[];
  selection: Selection;
  onChange: (next: Selection) => void;
  expanded: ReadonlySet<string>;
  onToggleExpand: (goalId: string) => void;
  tasksByGoal: Readonly<Record<string, readonly ScopeTask[] | undefined>>;
  tasksLoading: Readonly<Record<string, boolean>>;
  disabled: boolean;
}) {
  if (goals.length === 0) {
    return <p className="text-sm text-wg-muted">這個專案還沒有目標，沒有可執行的範圍。</p>;
  }
  const all = allCheckState(selection, goals);
  return (
    <div data-testid="scope-tree" role="group" aria-label="執行範圍" className="flex flex-col gap-1.5">
      <label className="flex cursor-pointer items-center gap-2.5 py-1 text-[15px] font-medium">
        <Checkbox
          className="size-5"
          checked={toChecked(all)}
          disabled={disabled}
          onCheckedChange={() => onChange(toggleAll(selection, goals))}
          data-testid="scope-all"
          aria-label="全部目標"
        />
        全部目標
      </label>
      {goals.map((g, i) => {
        const state = goalCheckState(selection, g);
        const runnable = isGoalRunnable(g);
        const open = expanded.has(g.id);
        const tasks = tasksByGoal[g.id];
        return (
          <div key={g.id} className="pl-6" data-testid={`scope-goal-row-${g.id}`}>
            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label={open ? `收合任務：${g.name}` : `展開任務：${g.name}`}
                aria-expanded={open}
                data-testid={`scope-expand-${g.id}`}
                onClick={() => onToggleExpand(g.id)}
                className="inline-flex size-5 shrink-0 cursor-pointer items-center justify-center rounded-sm border-none bg-transparent p-0 text-wg-muted transition-colors hover:text-wg-primary"
              >
                {open ? <ChevronDown size={16} aria-hidden /> : <ChevronRight size={16} aria-hidden />}
              </button>
              <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2.5 py-1 text-[15px]">
                <Checkbox
                  className="size-5"
                  checked={toChecked(state)}
                  disabled={disabled || !runnable}
                  onCheckedChange={() => onChange(toggleGoal(selection, g))}
                  data-testid={`scope-goal-${g.id}`}
                  aria-label={`選取目標：${g.name}`}
                />
                <span className="min-w-0 truncate">
                  目標 {i + 1}: {g.name}
                </span>
                <span className="shrink-0 text-[13px] text-wg-muted">({g.taskCount} tasks)</span>
                {!g.signedOff ? <Tag>未審批</Tag> : null}
                {!runnable ? <span className="shrink-0 text-xs text-wg-muted">已完成，不可選</span> : null}
              </label>
            </div>
            {open ? (
              <div className="mt-0.5 mb-1.5 flex flex-col gap-1 pl-[30px]" data-testid={`scope-tasks-${g.id}`}>
                {tasksLoading[g.id] && !tasks ? <span className="text-xs text-wg-muted">載入任務…</span> : null}
                {tasks && tasks.length === 0 ? <span className="text-xs text-wg-muted">這個目標沒有任務。</span> : null}
                {(tasks ?? []).map((t) => (
                  <label key={t.id} className="flex cursor-pointer items-center gap-2 py-0.5 text-sm">
                    <Checkbox
                      className="size-[18px]"
                      checked={isTaskChecked(selection, g.id, t.id)}
                      disabled={disabled || !isTaskRunnable(t) || !runnable}
                      onCheckedChange={() => onChange(toggleTask(selection, g, t, tasks ?? []))}
                      data-testid={`scope-task-${t.id}`}
                      aria-label={`選取任務：${t.name}`}
                    />
                    <span className="min-w-0 truncate">{t.name}</span>
                    <span className="shrink-0 text-xs text-wg-muted">{taskStatus(t.status).label}</span>
                    {!t.signedOff ? <Tag>未審批</Tag> : null}
                  </label>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
