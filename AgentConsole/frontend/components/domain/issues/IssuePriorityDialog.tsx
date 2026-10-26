"use client";

/**
 * 優先順序對話框（TCS-IssueCenter-20261027 R-IC-70；PRD §7）：ADMIN 對**可排**的列設定順位（1～9999，1 最先；可與其他議題重複）與備註（至多 200 個 code point）。
 * 「儲存」＝PUT、「清除」＝DELETE（冪等）。優先順序是 Console 自有的資料，不寫帳本。
 *
 * 設計要點（為什麼這樣做）：
 *  - **以回應為準、不樂觀**：送出後到回應回來之前，清單的列序與順位欄都不動；成功才由 `useSetIssuePriority`／`useClearIssuePriority` 把回應寫進快取（列依新順位重排）；
 *    失敗什麼都不動。
 *  - **表單先擋 backend 必拒的形態**（B-22；`validatePriorityForm`）：順位去前後空白後須為半形數字且 1～9999、備註至多 200 個 code point 且不含控制字元。
 *    不合不送請求，並就地說明（送出鈕停用＋「尚不能送出」原因；欄位下方的錯誤只在該欄有輸入時才出現）。backend 仍是權威：
 *    409（議題狀態已不可排）與 422 等失敗以逐字原因顯示在對話框內，對話框不關。
 *  - 送出中停用（連點只送一次；以 ref 同步擋，不靠重繪）。清除只在目前有順位時可按。
 */
import { Eraser, Save } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useClearIssuePriority, useSetIssuePriority } from "@/lib/api/queries";
import { ISSUE_NOTE_MAX, ISSUE_RANK_MAX, ISSUE_RANK_MIN, buildPriorityRequest, issueWriteErrorText, validatePriorityForm } from "@/lib/domain/issues";

/** 對話框的對象：議題編號與點擊當下的順位、備註（清單項的值；沒有順位為 null）。 */
export type PriorityTarget = { id: string; priority: number | null; note: string | null };

export function IssuePriorityDialog({ target, onClose }: { target: PriorityTarget | null; onClose: () => void }) {
  return (
    <Dialog open={target !== null} onOpenChange={(next) => !next && onClose()}>
      {target ? (
        <DialogContent data-testid="issue-priority-dialog" title={`優先順序：${target.id}`} description="設定這個議題的優先順序：順位 1 最先；儲存後依伺服器回應重排">
          <PriorityBody target={target} onClose={onClose} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function PriorityBody({ target, onClose }: { target: PriorityTarget; onClose: () => void }) {
  const toast = useToast();
  const save = useSetIssuePriority();
  const clear = useClearIssuePriority();
  const sending = useRef(false);
  const [busy, setBusy] = useState<"save" | "clear" | null>(null);
  const [rank, setRank] = useState(target.priority === null ? "" : String(target.priority));
  const [note, setNote] = useState(target.note ?? "");
  const [failure, setFailure] = useState<string | null>(null);

  const form = { rank, note };
  const errors = validatePriorityForm(form);
  const blocked = errors.rank ?? errors.note ?? null;

  /** 同一時間只送一個請求（儲存與清除互斥）；成功關窗並提示，失敗把逐字原因留在窗內。 */
  async function run(kind: "save" | "clear", send: () => Promise<unknown>, done: string) {
    if (sending.current) return;
    sending.current = true;
    setBusy(kind);
    setFailure(null);
    try {
      await send();
      toast.success(done);
      onClose();
    } catch (error) {
      setFailure(issueWriteErrorText(error));
    } finally {
      sending.current = false;
      setBusy(null);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (blocked !== null) return;
    void run("save", () => save.mutateAsync({ id: target.id, body: buildPriorityRequest(form) }), `已儲存 ${target.id} 的優先順序`);
  }

  return (
    <form onSubmit={submit} noValidate>
      <DialogBody>
        <Field label="順位" hint={`（${ISSUE_RANK_MIN}～${ISSUE_RANK_MAX} 的整數，1 最先；可與其他議題重複）`} error={rank.trim() !== "" ? errors.rank : undefined}>
          <Input
            value={rank}
            onChange={(e) => setRank(e.target.value)}
            inputMode="numeric"
            autoComplete="off"
            autoFocus
            aria-invalid={rank.trim() !== "" && errors.rank ? true : undefined}
            data-testid="issue-priority-rank"
          />
        </Field>
        <Field label="備註" hint={`（選填，至多 ${ISSUE_NOTE_MAX} 個字元，單行）`} error={note !== "" ? errors.note : undefined}>
          <Input value={note} onChange={(e) => setNote(e.target.value)} autoComplete="off" aria-invalid={note !== "" && errors.note ? true : undefined} data-testid="issue-priority-note" />
        </Field>
        {blocked ? (
          <p data-testid="issue-priority-blocked" className="text-sm text-wg-muted">
            {`尚不能送出：${blocked}`}
          </p>
        ) : null}
        {failure ? (
          <p role="alert" data-testid="issue-priority-error" className="text-sm text-wg-error">
            {failure}
          </p>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button
          variant="ghost"
          iconLeft={Eraser}
          className="mr-auto"
          loading={busy === "clear"}
          disabled={busy !== null || target.priority === null}
          onClick={() => void run("clear", () => clear.mutateAsync(target.id), `已清除 ${target.id} 的優先順序`)}
          data-testid="issue-priority-clear"
        >
          清除順位
        </Button>
        <Button variant="ghost" onClick={onClose} disabled={busy !== null}>
          取消
        </Button>
        <Button type="submit" iconLeft={Save} loading={busy === "save"} disabled={blocked !== null || busy !== null} data-testid="issue-priority-save">
          儲存
        </Button>
      </DialogFooter>
    </form>
  );
}
