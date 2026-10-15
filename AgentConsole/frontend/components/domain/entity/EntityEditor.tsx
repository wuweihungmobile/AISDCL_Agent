"use client";

/**
 * 建立／編輯的「載入＋表單＋送出」整合層：Dialog（EntityDialog）與整頁路由（EntityFormPage）共用。
 * 編輯時先抓詳情（專案列表只有摘要，沒有說明與通過標準）；送出成功 → toast → onDone。
 */
import { Skeleton } from "@/components/ui/skeleton";
import { DialogBody } from "@/components/ui/dialog";
import { ErrorState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useCreateGoal, useCreateProject, useCreateTask, useGoal, useProject, useTask, useUpdateGoal, useUpdateProject, useUpdateTask } from "@/lib/api/queries";
import { GoalForm, ProjectForm, TaskForm } from "./EntityForms";
import {
  GOAL_DEFAULTS,
  PROJECT_DEFAULTS,
  TASK_DEFAULTS,
  toCreateGoal,
  toCreateProject,
  toCreateTask,
  toUpdateGoal,
  toUpdateProject,
  toUpdateTask,
  type GoalFormValues,
  type ProjectFormValues,
  type TaskFormValues,
} from "./schemas";

export type EntityKind = "project" | "goal" | "task";

export type EntityTarget =
  | { kind: "project"; mode: "create" }
  | { kind: "project"; mode: "edit"; id: string }
  | { kind: "goal"; mode: "create"; projectId: string }
  | { kind: "goal"; mode: "edit"; id: string; projectId: string }
  | { kind: "task"; mode: "create"; goalId: string; projectId: string }
  | { kind: "task"; mode: "edit"; id: string; goalId: string; projectId: string };

export type EntityDone = {
  kind: EntityKind;
  mode: "create" | "edit";
  id: string;
  name: string;
  target: EntityTarget;
};

export const ENTITY_LABEL: Record<EntityKind, string> = { project: "專案", goal: "目標", task: "任務" };

export function entityTitle(t: EntityTarget): string {
  return `${t.mode === "create" ? "新建" : "編輯"}${ENTITY_LABEL[t.kind]}`;
}

type EditorProps = {
  variant: "dialog" | "page";
  onDone: (done: EntityDone) => void;
  onCancel: () => void;
};

function FormSkeleton({ variant }: { variant: "dialog" | "page" }) {
  const body = (
    <div aria-busy="true" aria-label="表單載入中" className="flex flex-col gap-4">
      <Skeleton className="h-11 w-full" />
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-28 w-full" />
    </div>
  );
  return variant === "dialog" ? <DialogBody>{body}</DialogBody> : body;
}

function ProjectEditor({ target, variant, onDone, onCancel }: EditorProps & { target: Extract<EntityTarget, { kind: "project" }> }) {
  const toast = useToast();
  const id = target.mode === "edit" ? target.id : undefined;
  const detail = useProject(id);
  const create = useCreateProject();
  const update = useUpdateProject();

  if (target.mode === "edit") {
    if (detail.isError) return <ErrorState error={detail.error} onRetry={() => detail.refetch()} />;
    if (!detail.data) return <FormSkeleton variant={variant} />;
  }
  const d = detail.data;
  const defaults: ProjectFormValues = d
    ? {
        name: d.name,
        executionPath: d.executionPath,
        description: d.description ?? "",
        passCriteria: d.passCriteria,
        autonomyLevel: d.autonomyLevel,
      }
    : PROJECT_DEFAULTS;
  const locked = d?.status === "EXECUTING";

  async function onSubmit(values: ProjectFormValues) {
    if (target.mode === "create") {
      const r = await create.mutateAsync(toCreateProject(values));
      toast.success(`已建立專案「${r.name}」`);
      onDone({ kind: "project", mode: "create", id: r.id, name: r.name, target });
    } else {
      const r = await update.mutateAsync({ id: target.id, body: toUpdateProject(values, locked) });
      toast.success(`已更新專案「${r.name}」`);
      onDone({ kind: "project", mode: "edit", id: r.id, name: r.name, target });
    }
  }

  return <ProjectForm key={d?.id ?? "new"} mode={target.mode} variant={variant} defaultValues={defaults} lockedToNameAndDescription={locked} onSubmit={onSubmit} onCancel={onCancel} />;
}

function GoalEditor({ target, variant, onDone, onCancel }: EditorProps & { target: Extract<EntityTarget, { kind: "goal" }> }) {
  const toast = useToast();
  const id = target.mode === "edit" ? target.id : undefined;
  const detail = useGoal(id);
  const create = useCreateGoal();
  const update = useUpdateGoal();

  if (target.mode === "edit") {
    if (detail.isError) return <ErrorState error={detail.error} onRetry={() => detail.refetch()} />;
    if (!detail.data) return <FormSkeleton variant={variant} />;
  }
  const d = detail.data;
  const defaults: GoalFormValues = d ? { name: d.name, description: d.description ?? "", passCriteria: d.passCriteria, dependsOn: d.dependsOn } : GOAL_DEFAULTS;

  async function onSubmit(values: GoalFormValues) {
    if (target.mode === "create") {
      const r = await create.mutateAsync({ projectId: target.projectId, body: toCreateGoal(values) });
      toast.success(`已建立目標「${r.name}」`);
      onDone({ kind: "goal", mode: "create", id: r.id, name: r.name, target });
    } else {
      const r = await update.mutateAsync({ id: target.id, body: toUpdateGoal(values) });
      toast.success(`已更新目標「${r.name}」`);
      onDone({ kind: "goal", mode: "edit", id: r.id, name: r.name, target });
    }
  }

  return (
    <GoalForm
      key={d?.id ?? "new"}
      mode={target.mode}
      variant={variant}
      defaultValues={defaults}
      projectId={target.projectId}
      selfId={target.mode === "edit" ? target.id : undefined}
      onSubmit={onSubmit}
      onCancel={onCancel}
    />
  );
}

function TaskEditor({ target, variant, onDone, onCancel }: EditorProps & { target: Extract<EntityTarget, { kind: "task" }> }) {
  const toast = useToast();
  const id = target.mode === "edit" ? target.id : undefined;
  const detail = useTask(id);
  const create = useCreateTask();
  const update = useUpdateTask();

  if (target.mode === "edit") {
    if (detail.isError) return <ErrorState error={detail.error} onRetry={() => detail.refetch()} />;
    if (!detail.data) return <FormSkeleton variant={variant} />;
  }
  const d = detail.data;
  const defaults: TaskFormValues = d
    ? {
        name: d.name,
        description: d.description ?? "",
        passCriteria: d.passCriteria,
        maxRetries: d.maxRetries,
        evaluatorCommand: d.evaluatorCommand ?? "",
        expectedOutputRegex: d.expectedOutputRegex ?? "",
      }
    : TASK_DEFAULTS;

  async function onSubmit(values: TaskFormValues) {
    if (target.mode === "create") {
      const r = await create.mutateAsync({ goalId: target.goalId, body: toCreateTask(values) });
      toast.success(`已建立任務「${r.name}」`);
      onDone({ kind: "task", mode: "create", id: r.id, name: r.name, target });
    } else {
      const r = await update.mutateAsync({ id: target.id, body: toUpdateTask(values) });
      toast.success(`已更新任務「${r.name}」`);
      onDone({ kind: "task", mode: "edit", id: r.id, name: r.name, target });
    }
  }

  return <TaskForm key={d?.id ?? "new"} mode={target.mode} variant={variant} defaultValues={defaults} onSubmit={onSubmit} onCancel={onCancel} />;
}

export function EntityEditor({ target, ...rest }: EditorProps & { target: EntityTarget }) {
  switch (target.kind) {
    case "project":
      return <ProjectEditor target={target} {...rest} />;
    case "goal":
      return <GoalEditor target={target} {...rest} />;
    case "task":
      return <TaskEditor target={target} {...rest} />;
  }
}
