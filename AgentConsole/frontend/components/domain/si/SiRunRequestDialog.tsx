"use client";

/**
 * 立即啟動對話框（P4；TCS-SelfImprovingSchedule W-S4、W-S6；PRD §0.11 校正 3、7）：ADMIN 請主機立即啟動一次自我進化運轉（觸發 a），送出成一份稽核檔，
 * 由主機端 CLI 入帳後由巡邏器在同一心跳執行——Console 不負責執行，也不宣稱「已啟動」：201 收據一律是「稽核檔已落地，待入帳」。
 * 主機端 `sched_blackout_local` 黑窗內送出的請求，會在黑窗結束後的下一心跳才執行（入帳得到的運轉被擋時只寫巡邏日誌、下一心跳再試）。
 *
 * **軟停用**（D-CS-5）：backend 沒有重送閘（兩次相同請求各得 201 與不同稽核編號），防連點與誤重送只靠這裡——對帳面板的查詢快取已有「待入帳的 run-request」時，
 * 主鈕停用並顯示稽核編號。**只讀既有快取、不發新請求**；快取缺席（沒有對帳面板、載入中或失敗）、對帳量不到、該列已入帳、或待入帳的只是排程設定時都不停用，以 backend 為準。
 * 主機端對多餘請求的消化＝已有未關運轉時改記 `sched.skip`（根層 R146 (b)）。送出與失敗呈現同排程設定對話框（送出中停用；失敗不關窗、逐字顯示）。
 */
import { Play } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { usePostSiRunRequest, useSiConsoleWritesCache, useSiStatus } from "@/lib/api/queries";
import type { SiWriteReceipt } from "@/lib/api/types";
import { SCHEDULE_NOTE_MAX, buildRunRequest, pendingRunRequest, scheduleFields, siScheduleErrorText, validateRunRequestForm } from "@/lib/domain/si";
import { SiWriteResult } from "./siParts";

export function SiRunRequestDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      {open ? (
        <DialogContent data-testid="si-run-request-dialog" title="立即啟動一次演化" description="請主機立即啟動一次自我進化運轉；簽成稽核檔落到主機端，入帳前尚未生效">
          <RunRequestBody onClose={onClose} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function RunRequestBody({ onClose }: { onClose: () => void }) {
  const post = usePostSiRunRequest();
  const status = useSiStatus();
  const view = scheduleFields(status.data?.items[0]?.schedule);
  const sending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<SiWriteReceipt | null>(null);

  // 軟停用：只讀對帳面板的查詢快取（不建立查詢、不發請求）；沒有快取或對帳不是 ok＝量不到，一律不停用
  const cache = useSiConsoleWritesCache();
  const pending = cache && cache.reconcile.status === "ok" ? pendingRunRequest(cache.items) : null;

  const errors = validateRunRequestForm({ note });
  const blocked = Object.values(errors)[0] ?? null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (sending.current || blocked !== null || pending !== null) return;
    sending.current = true;
    setBusy(true);
    setError(null);
    try {
      setReceipt(await post.mutateAsync(buildRunRequest({ note })));
    } catch (failure) {
      setError(siScheduleErrorText(failure));
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }

  if (receipt) {
    const beat = view.heartbeatMinutes === null ? "" : `（約 ${view.heartbeatMinutes} 分鐘內）`;
    return (
      <>
        <DialogBody>
          <SiWriteResult
            testId="si-run-request-result"
            receipt={receipt}
            meta
            extra={`若主機上的巡邏任務已武裝，下一次心跳${beat}會自動入帳並由巡邏器執行；Console 看不到該任務是否武裝，所以仍列出手動入帳指令。`}
          />
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            關閉
          </Button>
        </DialogFooter>
      </>
    );
  }

  return (
    <form onSubmit={submit} noValidate>
      <DialogBody>
        <p data-testid="si-run-request-summary" className="text-sm">
          本次會請主機立即跑一次自我進化（觸發
          a）。送出後只落稽核檔，入帳後由主機的巡邏器在同一次心跳執行。主機的黑窗時段內送出的請求，會等黑窗結束後的下一次心跳才執行；若主機已有未結束的運轉，這次請求會被略過並記一筆略過紀錄。
        </p>
        <Field label="備註" hint={`（選填，單行，至多 ${SCHEDULE_NOTE_MAX} 字元）`} error={errors.note}>
          <Input value={note} onChange={(e) => setNote(e.target.value)} aria-invalid={errors.note ? true : undefined} data-testid="si-run-request-note" />
        </Field>
        {blocked ? (
          <p data-testid="si-run-request-blocked" className="text-sm text-wg-muted">
            {`尚不能送出：${blocked}`}
          </p>
        ) : null}
        {error ? (
          <p role="alert" data-testid="si-run-request-error" className="text-sm break-words text-wg-error">
            {error}
          </p>
        ) : null}
      </DialogBody>
      <DialogFooter className="flex-wrap items-center">
        {pending ? (
          <p data-testid="si-run-request-dup" className="mr-auto text-xs break-all text-wg-muted">
            {`已送出待入帳（稽核編號 ${pending.auditRef}）`}
          </p>
        ) : null}
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          取消
        </Button>
        <Button type="submit" iconLeft={Play} loading={busy} disabled={blocked !== null || pending !== null} data-testid="si-run-request-submit">
          送出請求
        </Button>
      </DialogFooter>
    </form>
  );
}
