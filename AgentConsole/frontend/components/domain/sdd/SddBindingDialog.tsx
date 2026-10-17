"use client";

/**
 * 「編輯 SDD 專案」對話框（契約 §1.10.7、§4.7.1；API-PRJ-08；ADR-XPLAT-016 §7.2「可編輯」「改綁」）：OPERATOR 以上才會被打開（呼叫端控制）。
 * 一個輸入欄（自由輸入，1～100 字元、無控制字元；留空並儲存＝清除，回到「用預設」＝專案名）；值交給引擎橋接淨化後生效。
 * 送出 `PUT /projects/{id}/sdd-binding`：成功 → toast「已更新 SDD 專案」並重取專案詳情與 engines/sdd；
 * 失敗：400 在欄位下顯示 `errors[0].message`；`sdd_binding_conflict`「同一個專案根下已有另一個專案（<holderProjectId 前 8 碼>）綁定了這個 FSM 專案」；
 * 其餘照一般錯誤顯示 message 與 traceId。不檢查狀態檔是否存在、不呼叫 Bridge（填錯的名字只會讓卡片顯示「找不到所選專案的 FSM 狀態檔」，不留下任何寫入）。
 */
import { Save } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useUpdateSddBinding } from "@/lib/api/queries";
import type { ProjectDetail } from "@/lib/api/types";
import { describeSddError, type SddErrorView } from "@/lib/domain/sddErrors";
import { SDD_PROJECT_MAX, validateSddProjectInput } from "@/lib/domain/sddFreeze";

type Target = Pick<ProjectDetail, "id" | "name" | "sddProject">;

export function SddBindingDialog({ project, open, onClose }: { project: Target; open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      {open ? (
        <DialogContent title="編輯 SDD 專案" description="自由輸入 FSM 專案名；留空並儲存會清除綁定、回到預設（專案名）">
          <BindingBody project={project} onClose={onClose} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function BindingBody({ project, onClose }: { project: Target; onClose: () => void }) {
  const toast = useToast();
  const update = useUpdateSddBinding();
  const [text, setText] = useState(project.sddProject ?? "");
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [failure, setFailure] = useState<SddErrorView | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setFailure(null);
    const checked = validateSddProjectInput(text);
    if (!checked.ok) {
      setFieldError(checked.error);
      return;
    }
    setFieldError(undefined);
    try {
      await update.mutateAsync({ projectId: project.id, sddProject: checked.value });
      toast.success("已更新 SDD 專案");
      onClose();
    } catch (err) {
      const view = describeSddError(err, "binding");
      if (view.fieldErrors.sddProject) {
        // 400：欄位下顯示 errors[0].message；沒有欄位的其餘項目才另外列在下方
        setFieldError(view.fieldErrors.sddProject);
        setFailure(view.lines.length > 0 ? view : null);
      } else {
        setFailure(view);
      }
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      <DialogBody>
        <p className="text-[15px] leading-[1.7]">
          設定專案「<b>{project.name}</b>」對應的 FSM 專案。值會交給引擎橋接淨化後生效；改綁不搬移 FSM 狀態檔，也不影響進行中的批次。
        </p>
        <Field label="SDD 專案" hint={`（1～${SDD_PROJECT_MAX} 字元；留空並儲存＝清除，回到「用預設」＝專案名）`} error={fieldError}>
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            className="font-mono text-sm"
            aria-invalid={fieldError ? true : undefined}
            data-testid="sdd-binding-input"
          />
        </Field>
        {failure ? (
          <div role="alert" data-testid="sdd-binding-error" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-text">
            <p className="font-semibold text-wg-accent">{failure.title}</p>
            {failure.lines.map((line, i) => (
              <p key={`${i}-${line}`} className="mt-0.5">
                {line}
              </p>
            ))}
            {failure.traceId ? <p className="mt-1 font-mono text-xs text-wg-muted">traceId：{failure.traceId}</p> : null}
          </div>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={update.isPending}>
          取消
        </Button>
        <Button type="submit" iconLeft={Save} loading={update.isPending}>
          儲存
        </Button>
      </DialogFooter>
    </form>
  );
}
