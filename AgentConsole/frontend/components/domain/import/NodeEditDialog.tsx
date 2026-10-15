"use client";

/**
 * 步驟 2 的節點編輯對話框（560px，設計稿〈全域覆蓋層〉）：編輯專案、新增／編輯目標、新增／編輯任務。
 * 改動只落在本地的編輯樹（dispatch），按外層的「儲存編輯」才會 PUT /import/{id}/result。
 * 新增時節點尚未進樹：取消就什麼都沒發生（不會留下空白節點）。
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { Check } from "lucide-react";
import { useMemo, type ReactNode } from "react";
import { Controller, useForm, type Control, type FieldValues, type Path } from "react-hook-form";

import { MarkdownEditor } from "@/components/markdown/MarkdownEditor";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { goalNodeSchema, parseMaxRetries, projectNodeSchema, taskNodeSchema, type GoalNodeValues, type ProjectNodeValues, type TaskNodeValues } from "./nodeSchemas";
import { blankGoal, blankTask, type Tree, type TreeAction } from "./tree";

export type NodeTarget = { kind: "project" } | { kind: "goal"; mode: "create" | "edit"; key: string } | { kind: "task"; mode: "create" | "edit"; goalKey: string; uid: string };

export function nodeDialogTitle(target: NodeTarget): string {
  if (target.kind === "project") return "編輯專案";
  const noun = target.kind === "goal" ? "目標" : "任務";
  return `${target.mode === "create" ? "新增" : "編輯"}${noun}`;
}

export function NodeEditDialog({ target, tree, dispatch, onClose }: { target: NodeTarget | null; tree: Tree; dispatch: (action: TreeAction) => void; onClose: () => void }) {
  return (
    <Dialog open={target !== null} onOpenChange={(open) => !open && onClose()}>
      {target ? (
        <DialogContent title={nodeDialogTitle(target)} description={`${nodeDialogTitle(target)}：填寫後按確定，儲存編輯時才會送到後端`}>
          {target.kind === "project" ? (
            <ProjectBody tree={tree} dispatch={dispatch} onClose={onClose} />
          ) : target.kind === "goal" ? (
            <GoalBody key={target.key} target={target} tree={tree} dispatch={dispatch} onClose={onClose} />
          ) : (
            <TaskBody key={target.uid} target={target} tree={tree} dispatch={dispatch} onClose={onClose} />
          )}
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

// ── 共用小件 ────────────────────────────────────────────────────────────

function MarkdownField<T extends FieldValues>({ control, name, label, placeholder, error }: { control: Control<T>; name: Path<T>; label: string; placeholder: string; error?: string }) {
  const toast = useToast();
  return (
    <Field label={label} hint="(Markdown)" as="group" error={error}>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <MarkdownEditor
            value={String(field.value ?? "")}
            onChange={field.onChange}
            label={label}
            placeholder={placeholder}
            height={160}
            exportName={label}
            onNotify={(m, tone) => (tone === "success" ? toast.success(m) : toast.error(m))}
          />
        )}
      />
    </Field>
  );
}

function Shell({ onSubmit, onClose, children }: { onSubmit: (e?: React.BaseSyntheticEvent) => Promise<void>; onClose: () => void; children: ReactNode }) {
  return (
    <form onSubmit={onSubmit} noValidate className="flex min-h-0 flex-col">
      <DialogBody>{children}</DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose}>
          取消
        </Button>
        <Button type="submit" iconLeft={Check}>
          確定
        </Button>
      </DialogFooter>
    </form>
  );
}

type BodyProps = {
  tree: Tree;
  dispatch: (action: TreeAction) => void;
  onClose: () => void;
};

// ── 專案 ────────────────────────────────────────────────────────────────

function ProjectBody({ tree, dispatch, onClose }: BodyProps) {
  const p = tree.project;
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ProjectNodeValues>({
    resolver: zodResolver(projectNodeSchema),
    defaultValues: {
      name: p.name,
      executionPath: p.executionPath,
      description: p.description,
      passCriteria: p.passCriteria,
      autonomyLevel: p.autonomyLevel,
    },
  });
  const submit = handleSubmit((v) => {
    dispatch({
      type: "editProject",
      patch: {
        name: v.name.trim(),
        executionPath: v.executionPath.trim(),
        description: v.description,
        passCriteria: v.passCriteria,
        autonomyLevel: v.autonomyLevel,
      },
    });
    onClose();
  });
  return (
    <Shell onSubmit={submit} onClose={onClose}>
      <Field label="專案名稱" error={errors.name?.message}>
        <Input aria-invalid={errors.name ? true : undefined} {...register("name")} />
      </Field>
      <Field label="執行路徑" error={errors.executionPath?.message}>
        <Input className="font-mono text-sm" aria-invalid={errors.executionPath ? true : undefined} {...register("executionPath")} />
      </Field>
      <MarkdownField control={control} name="description" label="說明描述" placeholder="## 概述…" error={errors.description?.message} />
      <MarkdownField control={control} name="passCriteria" label="通過標準" placeholder="- 所有單元測試通過…" error={errors.passCriteria?.message} />
      <Field label="自治等級" hint="(1-10)" error={errors.autonomyLevel?.message}>
        <Input type="number" min={1} max={10} step={1} aria-invalid={errors.autonomyLevel ? true : undefined} {...register("autonomyLevel", { valueAsNumber: true })} />
      </Field>
    </Shell>
  );
}

// ── 目標 ────────────────────────────────────────────────────────────────

function GoalBody({ target, tree, dispatch, onClose }: BodyProps & { target: Extract<NodeTarget, { kind: "goal" }> }) {
  const existing = tree.goals.find((g) => g.key === target.key);
  const others = useMemo(() => tree.goals.filter((g) => g.key !== target.key), [tree.goals, target.key]);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<GoalNodeValues>({
    resolver: zodResolver(goalNodeSchema),
    defaultValues: {
      name: existing?.name ?? "",
      description: existing?.description ?? "",
      passCriteria: existing?.passCriteria ?? "",
      dependsOn: existing?.dependsOn ?? [],
    },
  });
  const submit = handleSubmit((v) => {
    const values = { name: v.name.trim(), description: v.description, passCriteria: v.passCriteria, dependsOn: v.dependsOn };
    if (target.mode === "create") {
      // 新目標附一個空白任務（契約要求每個目標至少 1 個任務）；任務由使用者接著編輯
      dispatch({ type: "addGoal", goal: { ...blankGoal(target.key, `${target.key}-t0`), ...values } });
    } else {
      dispatch({ type: "editGoal", key: target.key, patch: values });
    }
    onClose();
  });
  return (
    <Shell onSubmit={submit} onClose={onClose}>
      <Field label="目標名稱" error={errors.name?.message}>
        <Input aria-invalid={errors.name ? true : undefined} {...register("name")} />
      </Field>
      <MarkdownField control={control} name="description" label="說明描述" placeholder="## 概述…" error={errors.description?.message} />
      <MarkdownField control={control} name="passCriteria" label="通過標準" placeholder="- [ ] 所有核心模組通過單元測試" error={errors.passCriteria?.message} />
      <Field label="前置依賴" hint="(選填；完成前置目標後才會輪到本目標，成環時儲存會被後端擋下)" as="group" error={errors.dependsOn?.message}>
        <Controller
          control={control}
          name="dependsOn"
          render={({ field }) => (
            <div data-testid="node-depends-on" className="flex max-h-40 flex-col gap-2.5 overflow-y-auto rounded-md border border-wg-line bg-white px-4 py-3">
              {others.length === 0 ? (
                <p className="text-sm text-wg-muted">此樹沒有其他目標可作為前置依賴</p>
              ) : (
                others.map((g) => (
                  <label key={g.key} className="flex cursor-pointer items-center gap-2.5 text-sm">
                    <Checkbox checked={field.value.includes(g.key)} onCheckedChange={(next) => field.onChange(next === true ? [...field.value, g.key] : field.value.filter((k) => k !== g.key))} />
                    <span className="min-w-0 flex-1 truncate">{g.name || "（未命名目標）"}</span>
                  </label>
                ))
              )}
            </div>
          )}
        />
      </Field>
    </Shell>
  );
}

// ── 任務 ────────────────────────────────────────────────────────────────

function TaskBody({ target, tree, dispatch, onClose }: BodyProps & { target: Extract<NodeTarget, { kind: "task" }> }) {
  const existing = tree.goals.find((g) => g.key === target.goalKey)?.tasks.find((t) => t.uid === target.uid);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<TaskNodeValues>({
    resolver: zodResolver(taskNodeSchema),
    defaultValues: {
      name: existing?.name ?? "",
      description: existing?.description ?? "",
      passCriteria: existing?.passCriteria ?? "",
      evaluatorCommand: existing?.evaluatorCommand ?? "",
      expectedOutputRegex: existing?.expectedOutputRegex ?? "",
      // 契約 §0.2：null 與缺席等價；`=== undefined` 會把 null 顯示成字面「null」並讓 zod 擋住「確定」（DEF-AC-001）
      maxRetries: existing?.maxRetries == null ? "" : String(existing.maxRetries),
    },
  });
  const submit = handleSubmit((v) => {
    const patch = {
      name: v.name.trim(),
      description: v.description,
      passCriteria: v.passCriteria,
      evaluatorCommand: v.evaluatorCommand.trim(),
      expectedOutputRegex: v.expectedOutputRegex.trim(),
      maxRetries: parseMaxRetries(v.maxRetries),
    };
    if (target.mode === "create") {
      dispatch({ type: "addTask", goalKey: target.goalKey, task: { ...blankTask(target.uid), ...patch } });
    } else {
      dispatch({ type: "editTask", goalKey: target.goalKey, uid: target.uid, patch });
    }
    onClose();
  });
  return (
    <Shell onSubmit={submit} onClose={onClose}>
      <Field label="任務名稱" error={errors.name?.message}>
        <Input aria-invalid={errors.name ? true : undefined} {...register("name")} />
      </Field>
      <MarkdownField control={control} name="description" label="說明描述" placeholder="## 概述…" error={errors.description?.message} />
      <MarkdownField control={control} name="passCriteria" label="通過標準" placeholder="- 端點回傳符合統一回應格式" error={errors.passCriteria?.message} />
      <Field label="驗證命令" hint="(evaluatorCommand，選填)" error={errors.evaluatorCommand?.message}>
        <Input className="font-mono text-sm" placeholder="pytest -q" aria-invalid={errors.evaluatorCommand ? true : undefined} {...register("evaluatorCommand")} />
      </Field>
      <Field label="期望輸出 Regex" hint="(expectedOutputRegex，選填)" error={errors.expectedOutputRegex?.message}>
        <Input className="font-mono text-sm" placeholder="^OK$" aria-invalid={errors.expectedOutputRegex ? true : undefined} {...register("expectedOutputRegex")} />
      </Field>
      <Field label="最大重試次數" hint="(選填，0～20；空白沿用預設)" error={errors.maxRetries?.message}>
        <Input inputMode="numeric" aria-invalid={errors.maxRetries ? true : undefined} {...register("maxRetries")} />
      </Field>
    </Shell>
  );
}
