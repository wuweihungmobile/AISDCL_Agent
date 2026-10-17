"use client";

/**
 * 「核准凍結」對話框（人工閘；契約 §1.10.2、§4.7.1；API-SGN-06）：OPERATOR 以上、FSM 在 HUMAN_PENDING 時由專案詳情的「SDD 治理」區打開（呼叫端控制）。
 * 說明文字「核准後 FSM 進入 SPEC_FROZEN，規格內容將被摘要綁定；此動作無法由 Console 退回」；
 * 「要凍結的規格文件」多行輸入（每行一個相對專案根的路徑，1～20 行；專案已有 sddSpecFile 時預填其相對路徑；前端只做格式檢查：相對路徑、不含 ..、不重複，
 * 是否含 TCS 與檔案是否存在由 Bridge 判定、錯誤原樣顯示）；理由欄必填（去前後空白後 1～500 字元、不得含換行，不合不得送出，即時顯示字數）；
 * 「核准人：<目前登入者>」唯讀——approver 取自 JWT subject，不由畫面指定。階段名稱（選填）收在「進階」，留白就不送（Bridge 用 Stage-<n>）；不送 expectedDigests。
 * 送出 `POST /projects/{id}/sdd/freeze`：成功 → toast「已核准凍結」並重取專案詳情與 engines/sdd；失敗依 reason 顯示（lib/domain/sddErrors.ts，逐字句子見契約 §4.7.1）。
 */
import { ShieldCheck } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useFreezeProjectSdd } from "@/lib/api/queries";
import type { ProjectDetail } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { describeSddError, type SddErrorView } from "@/lib/domain/sddErrors";
import { FREEZE_REASON_MAX, relativeSpecDoc, validateFreezeForm, type FreezeFormErrors } from "@/lib/domain/sddFreeze";
import { cn } from "@/lib/utils";

type Target = Pick<ProjectDetail, "id" | "name" | "executionPath" | "sddSpecFile">;

/** 本對話框自己有輸入欄的欄位：後端 400 的欄位錯誤落在這些欄位之下，其餘欄位的錯誤列在下方的訊息區。 */
const OWN_FIELDS = ["docs", "reason", "stage"] as const;

export function SddFreezeDialog({ project, open, onClose }: { project: Target; open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      {open ? (
        <DialogContent title="核准凍結規格" description="人工閘：核准後 FSM 進入 SPEC_FROZEN，規格內容將被摘要綁定">
          <FreezeBody project={project} onClose={onClose} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function FreezeBody({ project, onClose }: { project: Target; onClose: () => void }) {
  const { username } = useAuth();
  const toast = useToast();
  const freeze = useFreezeProjectSdd();
  const counterId = useId();
  const [reason, setReason] = useState("");
  const [docsText, setDocsText] = useState(() => relativeSpecDoc(project.sddSpecFile, project.executionPath) ?? "");
  const [stage, setStage] = useState("");
  const [errors, setErrors] = useState<FreezeFormErrors>({});
  const [failure, setFailure] = useState<SddErrorView | null>(null);
  const reasonLength = reason.trim().length;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setFailure(null);
    const checked = validateFreezeForm({ reason, docsText, stage });
    if (!checked.ok) {
      setErrors(checked.errors);
      return;
    }
    setErrors({});
    try {
      await freeze.mutateAsync({ projectId: project.id, body: checked.request });
      toast.success("已核准凍結");
      onClose();
    } catch (err) {
      const view = describeSddError(err, "freeze");
      const server: FreezeFormErrors = {};
      for (const key of OWN_FIELDS) if (view.fieldErrors[key]) server[key] = view.fieldErrors[key];
      setErrors(server);
      // 不在本對話框的欄位（例：expectedDigests）：照原樣列在下方，不吞掉
      const extra = Object.entries(view.fieldErrors)
        .filter(([key]) => !(OWN_FIELDS as readonly string[]).includes(key))
        .map(([key, message]) => `${key}：${message}`);
      const onlyOwnFields = Object.keys(server).length > 0 && view.lines.length === 0 && extra.length === 0;
      setFailure(onlyOwnFields ? null : { ...view, lines: [...view.lines, ...extra] });
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      <DialogBody>
        <p className="text-[15px] leading-[1.7]">
          核准專案「<b>{project.name}</b>」的規格凍結。核准後 FSM 進入 SPEC_FROZEN，規格內容將被摘要綁定；此動作無法由 Console 退回。
        </p>

        <Field label="要凍結的規格文件" hint="（每行一個相對專案根的路徑，1～20 行；須含至少一份 TCS）" error={errors.docs}>
          <Textarea
            className="font-mono text-sm"
            rows={4}
            value={docsText}
            onChange={(e) => setDocsText(e.target.value)}
            spellCheck={false}
            placeholder="docs/03_testing/contracts/TCS-xxx.md"
            aria-invalid={errors.docs ? true : undefined}
            data-testid="sdd-freeze-docs"
          />
        </Field>

        <div className="flex flex-col gap-1">
          <Field label="核准理由" hint="（必填）" error={errors.reason}>
            <Textarea
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              aria-invalid={errors.reason ? true : undefined}
              aria-describedby={counterId}
              placeholder="例：規格已由 SDD session 走完 SCG-0～3，核准凍結"
              data-testid="sdd-freeze-reason"
            />
          </Field>
          <p id={counterId} data-testid="sdd-freeze-reason-count" className={cn("text-right text-xs", reasonLength > FREEZE_REASON_MAX ? "text-wg-error" : "text-wg-muted")}>
            {reasonLength} / {FREEZE_REASON_MAX} 字元（去前後空白後計算；不得含換行）
          </p>
        </div>

        <details className="text-sm" data-testid="sdd-freeze-advanced">
          <summary className="cursor-pointer text-wg-muted transition-colors hover:text-wg-primary">進階：階段名稱（選填）</summary>
          <div className="mt-2">
            <Field label="階段名稱" hint="（留白＝系統用 Stage-<n>；英數字與 . _ -，1～64 字元）" error={errors.stage}>
              <Input value={stage} onChange={(e) => setStage(e.target.value)} autoComplete="off" aria-invalid={errors.stage ? true : undefined} data-testid="sdd-freeze-stage" />
            </Field>
          </div>
        </details>

        <p className="text-sm" data-testid="sdd-freeze-approver">
          核准人：<b>{username || "—"}</b>
          <span className="ml-1.5 text-wg-muted">（唯讀；取自登入身分，不由畫面指定）</span>
        </p>

        {failure ? (
          <div role="alert" data-testid="sdd-freeze-error" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-text">
            <p className="font-semibold text-wg-accent">{failure.title}</p>
            {failure.lines.map((line, i) => (
              <p key={`${i}-${line}`} className="mt-0.5 break-words">
                {line}
              </p>
            ))}
            {failure.traceId ? <p className="mt-1 font-mono text-xs text-wg-muted">traceId：{failure.traceId}</p> : null}
          </div>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={freeze.isPending}>
          取消
        </Button>
        <Button type="submit" iconLeft={ShieldCheck} loading={freeze.isPending}>
          核准凍結
        </Button>
      </DialogFooter>
    </form>
  );
}
