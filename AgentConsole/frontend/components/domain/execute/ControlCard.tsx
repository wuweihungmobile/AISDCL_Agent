"use client";

import { History, Pause, Play, RotateCw, Square, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { ExecutionWarningView } from "@/lib/domain/executionWarnings";
import type { ControlAction, ControlButton } from "@/lib/domain/runControl";
import type { LockReport, ScopeGoal, ScopeTask, Selection } from "@/lib/domain/scope";
import { autonomyHint, autonomyLabel } from "@/lib/domain/status";
import { ExecutionWarningsPanel, StartErrorPanel } from "./parts";
import { ScopeTree } from "./ScopeTree";
import type { StartErrorView } from "./startErrors";

const ICON: Record<ControlAction, LucideIcon> = {
  start: Play,
  pause: Pause,
  resume: RotateCw,
  cancel: Square,
  restore: History,
};

export type ControlCardProps = {
  goals: readonly ScopeGoal[];
  tasksByGoal: Readonly<Record<string, readonly ScopeTask[] | undefined>>;
  tasksLoading: Readonly<Record<string, boolean>>;
  expanded: ReadonlySet<string>;
  onToggleExpand: (goalId: string) => void;
  selection: Selection;
  onSelection: (next: Selection) => void;
  level: number;
  onLevel: (level: number) => void;
  budget: string;
  onBudget: (value: string) => void;
  budgetError?: string;
  taskLimit: string;
  onTaskLimit: (value: string) => void;
  goalLimit: string;
  onGoalLimit: (value: string) => void;
  /** 有批次進行中：範圍、等級、預算是給「下一個批次」用的，先停用以免誤會 */
  frozen: boolean;
  buttons: readonly ControlButton[];
  pendingAction: ControlAction | null;
  onAction: (action: ControlAction) => void;
  lock: LockReport;
  startError: StartErrorView | null;
  /** 剛啟動的批次在 201 帶回的警告（契約 §1.10.6）；沒有警告或不是剛啟動的批次＝省略或空陣列 */
  warnings?: readonly ExecutionWarningView[];
  onApprove: () => void;
};

/**
 * 「執行控制」卡（設計稿畫面 7 左上）：自治等級、Token 預算（等寬 20px／700）、執行範圍 checkbox 樹、按鈕列依批次狀態切換。
 * 按鈕的啟用與文字由 lib/domain/runControl.ts 的狀態機決定（元件只負責呈現）。
 */
export function ControlCard(props: ControlCardProps) {
  const { lock, frozen } = props;
  const unsignedNames = [...lock.unsignedGoals.map((n) => `目標「${n}」`), ...lock.unsignedTasks.map((n) => `任務「${n}」`)];
  return (
    <Card className="px-[22px] py-5" data-testid="control-card">
      <CardTitle className="mb-4">執行控制</CardTitle>

      <div className="mb-4 grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">自治等級</span>
          <Select value={String(props.level)} onChange={(e) => props.onLevel(Number(e.target.value))} disabled={frozen} data-testid="exec-level">
            {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>
                {autonomyLabel(n)}
              </option>
            ))}
          </Select>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Token 預算</span>
          <Input
            inputMode="numeric"
            value={props.budget}
            onChange={(e) => props.onBudget(e.target.value)}
            disabled={frozen}
            aria-invalid={props.budgetError ? true : undefined}
            placeholder="沿用系統預設"
            data-testid="exec-budget"
            className="font-mono text-[20px] font-bold"
          />
        </label>
      </div>
      <p className="-mt-2 mb-3 text-xs text-wg-muted" data-testid="autonomy-hint">
        {autonomyHint(props.level)}
      </p>
      {props.budgetError ? (
        <p role="alert" className="-mt-1 mb-3 text-[13px] text-wg-error">
          {props.budgetError}
        </p>
      ) : null}

      <details className="mb-4 text-sm" data-testid="limits-details">
        <summary className="cursor-pointer text-wg-muted transition-colors hover:text-wg-primary">進階：單一任務／單一目標 Token 上限（選填）</summary>
        <div className="mt-2 grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          <label className="flex flex-col gap-1">
            <span className="text-[13px]">單一任務上限</span>
            <Input
              inputMode="numeric"
              value={props.taskLimit}
              onChange={(e) => props.onTaskLimit(e.target.value)}
              disabled={frozen}
              placeholder="不限"
              data-testid="exec-task-limit"
              className="font-mono"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[13px]">單一目標上限</span>
            <Input
              inputMode="numeric"
              value={props.goalLimit}
              onChange={(e) => props.onGoalLimit(e.target.value)}
              disabled={frozen}
              placeholder="不限"
              data-testid="exec-goal-limit"
              className="font-mono"
            />
          </label>
        </div>
        <p className="mt-1.5 text-xs text-wg-muted">超過上限會產生 Token 超限告警並自動暫停（US-E-10）。</p>
      </details>

      <div className="mb-1.5 text-sm font-medium">執行範圍</div>
      <ScopeTree
        goals={props.goals}
        selection={props.selection}
        onChange={props.onSelection}
        expanded={props.expanded}
        onToggleExpand={props.onToggleExpand}
        tasksByGoal={props.tasksByGoal}
        tasksLoading={props.tasksLoading}
        disabled={frozen}
      />
      {!lock.projectUnsigned && unsignedNames.length > 0 ? (
        <p role="status" data-testid="scope-unsigned" className="mt-2 rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-[13px] text-wg-text">
          範圍內有未 signoff 的項目：{unsignedNames.join("、")}。啟動前請先審批，否則後端回 409。
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2.5" data-testid="control-buttons">
        {props.buttons.map((b) => {
          const Icon = ICON[b.action];
          const primary = b.action === "start" || b.action === "resume";
          return (
            <Button
              key={b.action}
              variant={primary ? "solid" : "ghost"}
              iconLeft={Icon}
              disabled={!b.enabled}
              loading={props.pendingAction === b.action}
              title={b.hint}
              data-testid={`control-${b.action}`}
              onClick={() => props.onAction(b.action)}
            >
              {b.label}
            </Button>
          );
        })}
      </div>

      {props.startError ? <StartErrorPanel view={props.startError} onApprove={props.startError.unsigned ? props.onApprove : undefined} /> : null}
      <ExecutionWarningsPanel warnings={props.warnings ?? []} />
    </Card>
  );
}
