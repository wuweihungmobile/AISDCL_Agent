"use client";

/**
 * SCG 登錄對話框（FR-R2P-15-6；TCS-ResearchToPRD-P2-20261107 AT-962-4-7、4-8、4-E-6～4-E-9；IFACE-P2 §2.1）：僅 ADMIN 登錄 SCG-4（PR_REVIEW）、SCG-5（RTM_VERIFY）的人工結果與 RELEASE_READY 的 FAIL。
 *
 * 設計要點（為什麼這樣做）：
 *  - **判定住 `gateRegisterView`**：RELEASE_READY 只有 FAIL（PASS 由建立 Tag 完成）；FAIL 必填理由（1～500）；報告參照 ≤300；PR_REVIEW 必須勾「我確認審查者未參與規格與實作」，
 *    未勾時送出鈕停用、請求數 0（Console 不判斷獨立性，只記錄聲明；其餘 gate 不要求）。
 *  - **規格變更中停用**：`scrOpen` 時整個送出停用並顯示 `BUILD_DISABLED_TEXT.scrOpen`（與後端 409 `scr_open` 一致）。
 *  - **升級不提供恢復按鈕**：登錄結果讓狀態機進入升級狀態時只顯示「已升級，等待人工處理」並引導到決策彈窗；恢復只准在 Console 外執行（根鐵律）。
 *  - **錯誤取登記表**（`gateErrorView` → `researchErrorText`）：409 unmet 逐項中文、422 `digest_mismatch` 列每個漂移路徑並提供「發起 SCR」（`sourceKind` 預填 SCG4）、403 取通用權限不足文案。
 *  - 成功與失敗後 `useRegisterResearchGate` 都使看板重抓（不顯示過期值）。純文字渲染。
 */
import { ClipboardCheck } from "lucide-react";
import { useState } from "react";

import { ScrRequestDialog } from "@/components/domain/research/ScrRequestDialog";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useRegisterResearchGate } from "@/lib/api/queries";
import type { ResearchGateName, ResearchGateRegisterResult, ResearchGateResult } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { BUILD_DISABLED_TEXT, GATE_INDEPENDENCE_TEXT, GATE_LABEL, GATE_REASON_MAX, GATE_REPORT_REF_MAX, READONLY_TITLE, gateErrorView, gateRegisterView } from "@/lib/domain/research";

const GATES: ResearchGateName[] = ["PR_REVIEW", "RTM_VERIFY", "RELEASE_READY"];

export function GateRegisterDialog({ researchId, scrOpen }: { researchId: string; scrOpen: boolean }) {
  const { role } = useAuth();
  const register = useRegisterResearchGate();
  const [open, setOpen] = useState(false);
  const [scrOpenDialog, setScrOpenDialog] = useState(false);
  const [gate, setGate] = useState<ResearchGateName>("PR_REVIEW");
  const [result, setResult] = useState<ResearchGateResult>("PASS");
  const [reason, setReason] = useState("");
  const [reportRef, setReportRef] = useState("");
  const [independent, setIndependent] = useState(false);
  const [done, setDone] = useState<ResearchGateRegisterResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  const isAdmin = role === "ADMIN";
  const triggerTitle = isAdmin ? undefined : role === "VIEWER" ? READONLY_TITLE : "權限不足：僅 ADMIN 可登錄 SCG";
  const effectiveResult: ResearchGateResult = gate === "RELEASE_READY" ? "FAIL" : result;
  const view = gateRegisterView({ gate, result: effectiveResult, reason, reportRef, independent });
  const blocked = scrOpen ? BUILD_DISABLED_TEXT.scrOpen : null;
  const canSubmit = isAdmin && view.canSubmit && !scrOpen;
  const errorView = error === null ? null : gateErrorView(error);

  function submit() {
    if (!canSubmit) return;
    setError(null);
    register.mutate(
      {
        id: researchId,
        body: {
          gate,
          result: effectiveResult,
          reason: reason.trim(),
          ...(reportRef.trim() === "" ? {} : { reviewReportRef: reportRef.trim() }),
          reviewerIndependent: gate === "PR_REVIEW",
        },
      },
      { onSuccess: (data) => setDone(data), onError: (e) => setError(e) },
    );
  }

  return (
    <>
      <Button variant="ghost" iconLeft={ClipboardCheck} disabled={!isAdmin} title={triggerTitle} onClick={() => setOpen(true)} data-testid="gate-register-trigger">
        登錄 SCG
      </Button>
      <Dialog open={open && isAdmin} onOpenChange={setOpen}>
        <DialogContent title="登錄 SCG" description="登錄 SCG-4、SCG-5 的人工審查結果" data-testid="gate-dialog">
          <DialogBody>
            {blocked !== null ? (
              <p role="note" data-testid="gate-scr-open" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm">
                {blocked}
              </p>
            ) : null}
            <Field label="關卡">
              <Select
                value={gate}
                onChange={(e) => {
                  setGate(e.target.value as ResearchGateName);
                  setDone(null);
                  setError(null);
                }}
                data-testid="gate-select"
              >
                {GATES.map((g) => (
                  <option key={g} value={g}>
                    {GATE_LABEL[g]}
                  </option>
                ))}
              </Select>
            </Field>
            <fieldset className="flex flex-col gap-1">
              <legend className="text-sm font-medium">結果</legend>
              {view.resultOptions.map((r) => (
                <label key={r} className="flex items-center gap-2 text-sm">
                  <input type="radio" name="gate-result" value={r} checked={effectiveResult === r} onChange={() => setResult(r)} />
                  {r === "PASS" ? "通過（PASS）" : "未通過（FAIL）"}
                </label>
              ))}
              {gate === "RELEASE_READY" ? (
                <p data-testid="gate-release-note" className="text-[13px] text-wg-muted">
                  PASS 由建立 Tag 完成，這裡只能登錄 FAIL。
                </p>
              ) : null}
            </fieldset>
            <Field label="理由" hint={view.reasonRequired ? "（FAIL 必填）" : "（選填）"} error={view.reasonError ?? undefined}>
              <Textarea value={reason} onChange={(e) => setReason(e.target.value)} />
            </Field>
            <p data-testid="gate-reason-counter" className="-mt-2 text-xs text-wg-muted">
              {[...reason.trim()].length}／{GATE_REASON_MAX} 字（1 至 {GATE_REASON_MAX}）
            </p>
            <Field label="審查報告參照" hint={`（選填，最多 ${GATE_REPORT_REF_MAX} 字）`} error={view.reportRefError ?? undefined}>
              <Input value={reportRef} onChange={(e) => setReportRef(e.target.value)} />
            </Field>
            {view.independenceRequired ? (
              <div className="flex flex-col gap-1">
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" checked={independent} onChange={(e) => setIndependent(e.target.checked)} data-testid="gate-independent" className="mt-1" />
                  {GATE_INDEPENDENCE_TEXT}
                </label>
                {view.independenceError !== null ? (
                  <p data-testid="gate-independent-required" role="note" className="text-[13px] text-wg-muted">
                    {view.independenceError}
                  </p>
                ) : null}
              </div>
            ) : null}

            {done !== null ? (
              <div role="status" data-testid="gate-done" className="flex flex-col gap-1 text-sm">
                <p>
                  已登錄：下一個狀態是 <span className="font-semibold">{done.nextState}</span>
                </p>
                {done.escalated ? (
                  <p data-testid="gate-escalated" className="font-semibold text-wg-accent">
                    已升級，等待人工處理：請到決策彈窗處理；恢復指令只顯示、不提供恢復按鈕，請在 Console 外執行。
                  </p>
                ) : null}
              </div>
            ) : null}
            {errorView !== null ? (
              <div role="alert" data-testid="gate-error" className="flex flex-col gap-2 rounded-md border border-wg-error px-3 py-2 text-sm">
                <p>{errorView.text}</p>
                {errorView.unmet.length > 0 ? (
                  <ul className="list-disc pl-5" data-testid="gate-unmet">
                    {errorView.unmet.map((u) => (
                      <li key={u}>{u}</li>
                    ))}
                  </ul>
                ) : null}
                {errorView.drift.length > 0 ? (
                  <ul className="list-disc pl-5 font-mono text-xs" data-testid="gate-drift">
                    {errorView.drift.map((p) => (
                      <li key={p}>{p}</li>
                    ))}
                  </ul>
                ) : null}
                {errorView.offerScr ? (
                  <Button variant="ghost" size="sm" onClick={() => setScrOpenDialog(true)} data-testid="gate-offer-scr">
                    發起 SCR
                  </Button>
                ) : null}
              </div>
            ) : null}
          </DialogBody>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              關閉
            </Button>
            <Button disabled={!canSubmit} loading={register.isPending} onClick={submit} data-testid="gate-submit">
              送出
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {scrOpenDialog ? <ScrRequestDialog researchId={researchId} open={scrOpenDialog} onOpenChange={setScrOpenDialog} sourceKind="SCG4" /> : null}
    </>
  );
}
