"use client";

/**
 * 專案／目標／任務的建立與編輯表單（Dialog 與整頁 new／edit 路由共用同一組元件）。
 * react-hook-form ＋ zod；錯誤訊息繁中；後端 400 的 errors[] 以 applyServerErrors 對應回欄位。
 * 說明描述與通過標準使用 Markdown 編輯器（Split View、工具列、匯入／匯出 .md）。
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { Check } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Controller, useForm, type Control, type FieldValues, type Path } from "react-hook-form";

import { DialogBody, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { StatusLabel } from "@/components/ui/status-dot";
import { useToast } from "@/components/ui/toast";
import { MarkdownEditor } from "@/components/markdown/MarkdownEditor";
import { ApiError } from "@/lib/api/client";
import { useGoals } from "@/lib/api/queries";
import { goalStatus } from "@/lib/domain/status";
import { cn } from "@/lib/utils";
import { applyServerErrors } from "./apiErrors";
import { goalSchema, projectSchema, taskSchema, type GoalFormValues, type ProjectFormValues, type TaskFormValues } from "./schemas";

type Variant = "dialog" | "page";

type CommonProps<V> = {
  mode: "create" | "edit";
  variant: Variant;
  defaultValues: V;
  /** 送出；丟出 ApiError 時由表單對應回欄位／橫幅 */
  onSubmit: (values: V) => Promise<void>;
  onCancel: () => void;
};

// ── 共用小件 ────────────────────────────────────────────────────────────
function MarkdownField<T extends FieldValues>({
  control,
  name,
  label,
  placeholder,
  exportName,
  variant,
  error,
  disabled,
}: {
  control: Control<T>;
  name: Path<T>;
  label: string;
  placeholder: string;
  exportName: string;
  variant: Variant;
  error?: string;
  disabled?: boolean;
}) {
  const toast = useToast();
  return (
    <Field label={label} hint="(Markdown)" as="group" error={error}>
      <Controller
        control={control}
        name={name}
        render={({ field }) =>
          disabled ? (
            <Input value={String(field.value ?? "")} disabled readOnly aria-label={label} />
          ) : (
            <MarkdownEditor
              value={String(field.value ?? "")}
              onChange={field.onChange}
              label={label}
              placeholder={placeholder}
              height={variant === "dialog" ? 200 : 320}
              exportName={exportName}
              onNotify={(m, tone) => (tone === "success" ? toast.success(m) : toast.error(m))}
            />
          )
        }
      />
    </Field>
  );
}

function FormShell({
  variant,
  mode,
  onCancel,
  isSubmitting,
  formError,
  onSubmit,
  children,
}: {
  variant: Variant;
  mode: "create" | "edit";
  onCancel: () => void;
  isSubmitting: boolean;
  formError: string | null;
  onSubmit: (e?: React.BaseSyntheticEvent) => Promise<void>;
  children: ReactNode;
}) {
  const buttons = (
    <>
      <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
        取消
      </Button>
      <Button type="submit" iconLeft={Check} loading={isSubmitting}>
        {mode === "create" ? "建立" : "儲存"}
      </Button>
    </>
  );
  return (
    <form onSubmit={onSubmit} noValidate className={cn(variant === "dialog" && "flex min-h-0 flex-col")}>
      {variant === "dialog" ? (
        <>
          <DialogBody>
            {children}
            {formError ? <FormErrorBanner message={formError} /> : null}
          </DialogBody>
          <DialogFooter>{buttons}</DialogFooter>
        </>
      ) : (
        <>
          <div className="flex flex-col gap-4">
            {children}
            {formError ? <FormErrorBanner message={formError} /> : null}
          </div>
          <div className="mt-6 flex justify-end gap-2.5">{buttons}</div>
        </>
      )}
    </form>
  );
}

function FormErrorBanner({ message }: { message: string }) {
  return (
    <p role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
      {message}
    </p>
  );
}

// ── 專案 ────────────────────────────────────────────────────────────────
const PROJECT_FIELDS = ["name", "executionPath", "description", "passCriteria", "autonomyLevel"] as const;

export function ProjectForm({
  mode,
  variant,
  defaultValues,
  onSubmit,
  onCancel,
  lockedToNameAndDescription = false,
}: CommonProps<ProjectFormValues> & {
  /** 專案 EXECUTING 時只能改名稱與說明（後端 409 的前端體驗層） */
  lockedToNameAndDescription?: boolean;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProjectFormValues>({ resolver: zodResolver(projectSchema), defaultValues });

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (e) {
      setFormError(applyServerErrors(e, setError, PROJECT_FIELDS));
    }
  });
  const locked = lockedToNameAndDescription;

  return (
    <FormShell variant={variant} mode={mode} onCancel={onCancel} isSubmitting={isSubmitting} formError={formError} onSubmit={submit}>
      {locked ? <FormErrorBanner message="專案執行中：只能修改名稱與說明，其他欄位已鎖定。" /> : null}
      <Field label="專案名稱" error={errors.name?.message}>
        <Input placeholder="輸入名稱…" aria-invalid={errors.name ? true : undefined} {...register("name")} />
      </Field>
      <Field label="執行路徑" error={errors.executionPath?.message}>
        <Input placeholder="/home/user/projects/…" disabled={locked} aria-invalid={errors.executionPath ? true : undefined} {...register("executionPath")} />
      </Field>
      <MarkdownField control={control} name="description" label="說明描述" placeholder="## 概述…" exportName="專案說明" variant={variant} error={errors.description?.message} />
      <MarkdownField
        control={control}
        name="passCriteria"
        label="通過標準"
        placeholder="- 所有單元測試通過…"
        exportName="專案通過標準"
        variant={variant}
        error={errors.passCriteria?.message}
        disabled={locked}
      />
      <Field label="自治等級" hint="(1-10)" error={errors.autonomyLevel?.message}>
        <Input type="number" min={1} max={10} step={1} disabled={locked} aria-invalid={errors.autonomyLevel ? true : undefined} {...register("autonomyLevel", { valueAsNumber: true })} />
      </Field>
    </FormShell>
  );
}

// ── 目標 ────────────────────────────────────────────────────────────────
const GOAL_FIELDS = ["name", "description", "passCriteria", "dependsOn"] as const;

/** 前置依賴多選：同專案其他目標的核取清單（成環時顯示後端 400 原因） */
function DependsOnField({ control, projectId, selfId, error }: { control: Control<GoalFormValues>; projectId: string; selfId?: string; error?: string }) {
  const goals = useGoals(projectId);
  const others = (goals.data ?? []).filter((g) => g.id !== selfId);
  return (
    <Field label="前置依賴" hint="(選填；完成前置目標後才會輪到本目標)" as="group" error={error}>
      <Controller
        control={control}
        name="dependsOn"
        render={({ field }) => (
          <div data-testid="depends-on-list" className="flex max-h-44 flex-col gap-2.5 overflow-y-auto rounded-md border border-wg-line bg-white px-4 py-3">
            {goals.isLoading ? (
              <p className="text-sm text-wg-muted">載入目標清單…</p>
            ) : others.length === 0 ? (
              <p className="text-sm text-wg-muted">此專案沒有其他目標可作為前置依賴</p>
            ) : (
              others.map((g) => {
                const checked = field.value.includes(g.id);
                return (
                  <label key={g.id} className="flex cursor-pointer items-center gap-2.5 text-sm">
                    <Checkbox checked={checked} onCheckedChange={(next) => field.onChange(next === true ? [...field.value, g.id] : field.value.filter((id) => id !== g.id))} />
                    <span className="min-w-0 flex-1 truncate">{g.name}</span>
                    <StatusLabel meta={goalStatus(g.status)} dot={8} className="text-xs" />
                  </label>
                );
              })
            )}
          </div>
        )}
      />
    </Field>
  );
}

export function GoalForm({ mode, variant, defaultValues, onSubmit, onCancel, projectId, selfId }: CommonProps<GoalFormValues> & { projectId: string; selfId?: string }) {
  const [formError, setFormError] = useState<string | null>(null);
  const goals = useGoals(projectId);
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<GoalFormValues>({ resolver: zodResolver(goalSchema), defaultValues });

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (e) {
      // 成環訊息內含 UUID：換成目標名稱（「A → B → A」）
      const nameOf = (id: string) => goals.data?.find((g) => g.id === id)?.name ?? id;
      setFormError(
        applyServerErrors(e, setError, GOAL_FIELDS, (field, message, err) => {
          if (field !== "dependsOn") return message;
          const cycle = err.details?.cycle;
          if (Array.isArray(cycle)) {
            return `${err.reason ?? "依賴成環"}：${cycle.map((id) => nameOf(String(id))).join(" → ")}`;
          }
          return err.reason ? `${err.reason}：${message}` : message;
        }),
      );
    }
  });

  return (
    <FormShell variant={variant} mode={mode} onCancel={onCancel} isSubmitting={isSubmitting} formError={formError} onSubmit={submit}>
      <Field label="目標名稱" error={errors.name?.message}>
        <Input placeholder="輸入名稱…" aria-invalid={errors.name ? true : undefined} {...register("name")} />
      </Field>
      <MarkdownField control={control} name="description" label="說明描述" placeholder="## 概述…" exportName="目標說明" variant={variant} error={errors.description?.message} />
      <MarkdownField
        control={control}
        name="passCriteria"
        label="通過標準"
        placeholder="- [ ] 所有核心模組通過單元測試"
        exportName="目標通過標準"
        variant={variant}
        error={errors.passCriteria?.message}
      />
      <DependsOnField control={control} projectId={projectId} selfId={selfId} error={errors.dependsOn?.message} />
    </FormShell>
  );
}

// ── 任務 ────────────────────────────────────────────────────────────────
const TASK_FIELDS = ["name", "description", "passCriteria", "maxRetries", "evaluatorCommand", "expectedOutputRegex"] as const;

export function TaskForm({ mode, variant, defaultValues, onSubmit, onCancel }: CommonProps<TaskFormValues>) {
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<TaskFormValues>({ resolver: zodResolver(taskSchema), defaultValues });

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (e) {
      setFormError(
        applyServerErrors(e, setError, TASK_FIELDS, (field, message, err: ApiError) => {
          const violations = err.details?.violations;
          if (field === "evaluatorCommand" && Array.isArray(violations) && violations.length > 0) {
            return `含禁用字元：${violations.map((v) => `「${String(v)}」`).join(" ")}（NFR-SEC-03）`;
          }
          return message;
        }),
      );
    }
  });

  return (
    <FormShell variant={variant} mode={mode} onCancel={onCancel} isSubmitting={isSubmitting} formError={formError} onSubmit={submit}>
      <Field label="任務名稱" error={errors.name?.message}>
        <Input placeholder="輸入名稱…" aria-invalid={errors.name ? true : undefined} {...register("name")} />
      </Field>
      <MarkdownField control={control} name="description" label="說明描述" placeholder="## 概述…" exportName="任務說明" variant={variant} error={errors.description?.message} />
      <MarkdownField control={control} name="passCriteria" label="通過標準" placeholder="- 端點回傳符合統一回應格式" exportName="任務通過標準" variant={variant} error={errors.passCriteria?.message} />
      <Field label="最大重試次數" error={errors.maxRetries?.message}>
        <Input type="number" min={0} step={1} aria-invalid={errors.maxRetries ? true : undefined} {...register("maxRetries", { valueAsNumber: true })} />
      </Field>
      <Field label="驗證命令" hint="(evaluatorCommand，選填)" error={errors.evaluatorCommand?.message}>
        <Input placeholder="pytest -q" className="font-mono text-sm" aria-invalid={errors.evaluatorCommand ? true : undefined} {...register("evaluatorCommand")} />
      </Field>
      <Field label="期望輸出 Regex" hint="(expectedOutputRegex，選填)" error={errors.expectedOutputRegex?.message}>
        <Input placeholder="^OK$" className="font-mono text-sm" aria-invalid={errors.expectedOutputRegex ? true : undefined} {...register("expectedOutputRegex")} />
      </Field>
    </FormShell>
  );
}
