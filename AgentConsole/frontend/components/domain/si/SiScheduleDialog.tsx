"use client";

/**
 * 排程設定對話框（P4；TCS-SelfImprovingSchedule W-S2、W-S3、W-S6；PRD §0.11 校正 4～6）：ADMIN 啟用或停用自動演化排程、改週期，送出成一份稽核檔，
 * 由主機端 CLI 入帳後才生效。啟停與改週期是同一個動作（`sched set` 一次帶 `enabled` 與 `periodMinutes`），所以同一個對話框、兩鍵皆必備——
 * **停用方向也要帶界內週期**（D-CS-6，不開例外）；現值落在界外時預填值標紅並提示先改成界內週期，不放行（D-CS-12）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **界只來自橫幅的 `schedule.periodMin／periodMax`**（呼叫 `validateScheduleForm` 時傳入；元件與純函式內沒有任何界值常數）：界取不到（缺席、非整數、min 大於 max）
 *    ＝送出停用並說明「量不到界值」，以 backend 為準。前端只先擋、backend 的序 5′ 才是權威。
 *  - **不宣稱已生效**：201 收據一律是「稽核檔已落地，待入帳」，並說明巡邏心跳若已武裝會自動入帳；Console 看不到該任務是否武裝，所以仍列出手動入帳指令（L-SI-1）。
 *  - 送出中停用（連點只送一次；以 ref 同步擋）；失敗不關窗、表單內容保留，reason、message、violations、cause 逐字顯示（純文字）。
 *  - 內容元件隨對話框卸載：關閉後重開不沿用上次結果，也不以瀏覽器儲存另存任何草稿或界值。
 */
import { Send } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { usePostSiScheduleSet, useSiStatus } from "@/lib/api/queries";
import type { SiWriteReceipt } from "@/lib/api/types";
import { SCHEDULE_NOTE_MAX, buildScheduleRequest, periodHint, scheduleFields, siScheduleErrorText, validateScheduleForm } from "@/lib/domain/si";
import { SiWriteResult } from "./siParts";

/** 對話框的對象：開啟時預選的啟用狀態（啟用／停用鈕帶「與現值相反」，改週期鈕帶現值）。 */
export type ScheduleTarget = { enabled: boolean };

export function SiScheduleDialog({ target, onClose }: { target: ScheduleTarget | null; onClose: () => void }) {
  return (
    <Dialog open={target !== null} onOpenChange={(next) => !next && onClose()}>
      {target ? (
        <DialogContent data-testid="si-schedule-dialog" title="設定自動演化排程" description="自動演化排程：啟用或停用、改週期；簽成稽核檔落到主機端，入帳前尚未生效">
          <ScheduleBody target={target} onClose={onClose} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function ScheduleBody({ target, onClose }: { target: ScheduleTarget; onClose: () => void }) {
  const post = usePostSiScheduleSet();
  const status = useSiStatus();
  // 界與現值只讀橫幅同一個查詢（不另存第二份）；查詢沒有資料時界為 null＝量不到界值
  const view = scheduleFields(status.data?.items[0]?.schedule);
  const sending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [enabled, setEnabled] = useState(target.enabled);
  const [periodText, setPeriodText] = useState(view.periodMinutes === null ? "" : String(view.periodMinutes));
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<SiWriteReceipt | null>(null);

  const form = { enabled, periodText, reason };
  const errors = validateScheduleForm(form, view.bounds);
  const blocked = Object.values(errors)[0] ?? null;
  const trimmed = periodText.trim();
  const valid = /^[0-9]+$/.test(trimmed) && Number(trimmed) >= 1;
  // 現值落在界外：預填值標紅並提示先改成界內週期（D-CS-12），不放行
  const periodError =
    errors.periodMinutes && view.periodMinutes !== null && trimmed === String(view.periodMinutes) && view.bounds
      ? `${errors.periodMinutes}（目前的週期落在界外，請先改成界內週期）`
      : errors.periodMinutes;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (sending.current || blocked !== null) return;
    sending.current = true;
    setBusy(true);
    setError(null);
    try {
      setReceipt(await post.mutateAsync(buildScheduleRequest(form)));
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
          <SiWriteResult testId="si-schedule-result" receipt={receipt} meta extra={`若主機上的巡邏任務已武裝，下一次心跳${beat}會自動入帳；Console 看不到該任務是否武裝，所以仍列出手動入帳指令。`} />
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
        <p data-testid="si-schedule-summary" className="text-sm">
          {`本次會把排程改成：${enabled ? "啟用" : "停用"}，${valid ? `週期 ${Number(trimmed)} 分鐘（${periodHint(Number(trimmed))}）` : "週期尚未填妥"}。送出後只落稽核檔，入帳後才生效。`}
        </p>

        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <Checkbox checked={enabled} onCheckedChange={(v) => setEnabled(v === true)} data-testid="si-schedule-enabled" aria-label="啟用排程" />
          <span>{enabled ? "啟用排程" : "停用排程（週期仍須填寫）"}</span>
        </label>

        <Field label="週期（分鐘）" hint={view.bounds ? `（${view.bounds.periodMin}～${view.bounds.periodMax}）` : undefined} error={periodError}>
          <div className="flex items-center gap-3">
            <Input inputMode="numeric" value={periodText} onChange={(e) => setPeriodText(e.target.value)} aria-invalid={errors.periodMinutes ? true : undefined} data-testid="si-schedule-period" />
            <span data-testid="si-schedule-hint" className="text-sm whitespace-nowrap text-wg-muted">
              {valid ? periodHint(Number(trimmed)) : ""}
            </span>
          </div>
        </Field>

        <Field label="理由" hint={`（選填，單行，至多 ${SCHEDULE_NOTE_MAX} 字元）`} error={errors.reason}>
          <Textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} aria-invalid={errors.reason ? true : undefined} data-testid="si-schedule-reason" />
        </Field>

        {blocked ? (
          <p data-testid="si-schedule-blocked" className="text-sm text-wg-muted">
            {`尚不能送出：${blocked}`}
          </p>
        ) : null}
        {error ? (
          <p role="alert" data-testid="si-schedule-error" className="text-sm break-words text-wg-error">
            {error}
          </p>
        ) : null}
      </DialogBody>
      <DialogFooter className="flex-wrap items-center">
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          取消
        </Button>
        <Button type="submit" iconLeft={Send} loading={busy} disabled={blocked !== null} data-testid="si-schedule-submit">
          送出設定
        </Button>
      </DialogFooter>
    </form>
  );
}
