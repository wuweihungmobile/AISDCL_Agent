"use client";

import { Check } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ApiError, describeError } from "@/lib/api/client";
import { useSignoffGoal, useSignoffImport, useSignoffProject, useSignoffTask } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";

/** kind="import"＝BRD/PRD 匯入草案（POST /import/{id}/signoff，契約 §1.1.5）；其餘為 Phase 2 的專案／目標／任務。 */
export type SignoffTarget = { kind: "project" | "goal" | "task" | "import"; id: string; name: string };

const LABEL = { project: "專案", goal: "目標", task: "任務", import: "匯入草案" } as const;

/** Signoff 對話框：approver 預設帶目前使用者名稱（不可匿名、不可空白）；確認 → POST signoff → toast「已 signoff」。 */
export function SignoffDialog({ target, onClose }: { target: SignoffTarget | null; onClose: () => void }) {
  return (
    <Dialog open={target !== null} onOpenChange={(open) => !open && onClose()}>
      {target ? (
        <DialogContent title={`審批 signoff：${LABEL[target.kind]}`} description="人工 signoff 硬閘：審批者不可匿名">
          <SignoffBody key={`${target.kind}:${target.id}`} target={target} onClose={onClose} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function SignoffBody({ target, onClose }: { target: SignoffTarget; onClose: () => void }) {
  const { username } = useAuth();
  const toast = useToast();
  const project = useSignoffProject();
  const goal = useSignoffGoal();
  const task = useSignoffTask();
  const importRecord = useSignoffImport();
  const [approver, setApprover] = useState(username);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [pending, setPending] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const name = approver.trim();
    if (!name) {
      setFieldError("審批者不可為空（人工 signoff 不可匿名）");
      return;
    }
    setFieldError(undefined);
    setError(null);
    setPending(true);
    try {
      const vars = { id: target.id, approver: name };
      if (target.kind === "project") await project.mutateAsync(vars);
      else if (target.kind === "goal") await goal.mutateAsync(vars);
      else if (target.kind === "import") await importRecord.mutateAsync(vars);
      else await task.mutateAsync(vars);
      toast.success(`已 signoff：${target.name}`);
      onClose();
    } catch (err) {
      const approverErr = err instanceof ApiError ? err.errors.find((x) => x.field === "approver") : undefined;
      if (approverErr) setFieldError(approverErr.message);
      else setError(describeError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      <DialogBody>
        <p className="text-[15px] leading-[1.7]">
          確認審批{LABEL[target.kind]}「<b>{target.name}</b>」？審批後才可{target.kind === "import" ? "確認匯入並執行" : "執行"}；審批動作會記錄審批者與時間。
        </p>
        <Field label="審批者" error={fieldError}>
          <Input value={approver} onChange={(e) => setApprover(e.target.value)} autoComplete="off" aria-invalid={fieldError ? true : undefined} />
        </Field>
        {error ? (
          <p role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
            {error}
          </p>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={pending}>
          取消
        </Button>
        <Button type="submit" iconLeft={Check} loading={pending}>
          確認 signoff
        </Button>
      </DialogFooter>
    </form>
  );
}
