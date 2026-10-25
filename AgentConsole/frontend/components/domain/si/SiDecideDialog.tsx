"use client";

/**
 * 決定對話框（P2b；TCS-SelfImprovingDecide-P2b W18；PRD AC-SI-33-1）：ADMIN 對待決卡下九種決定之一，或對橫幅暫停的運轉下「恢復」。
 *
 * 設計要點（為什麼這樣做）：
 *  - **預設拒絕**：動詞下拉預設不選；沒有批次或全部核准，一次一張卡、一個動詞。動詞集合由 `decideVerbOptions` 依卡片情境給（表 M-V）。
 *  - **綁定開啟當下的卡面 digest**：呼叫端在點擊當下傳入提案快照，送出的 `digest` 取自快照、不取自之後重抓的清單——掌舵者看到的卡面與簽進稽核的是同一份；
 *    卡面若在這段時間變了，入帳時根層 CLI 以 STALE-CARD 拒收（前端不判新鮮度，⚖15）。恢復綁運轉號、沒有 digest。
 *  - 必填欄依動詞（表 M-D）：缺欄時送出鈕停用並顯示原因（不是靜默停用）；verdict 為 NE 的晉升（晉升後式）須勾選「已知悉未驗採納」。
 *  - 送出＝單次 `postSiDecide`：請求中停用（連點只送一次；以 ref 同步擋，不靠重繪）；失敗以 toast 顯示原因逐字、對話框不關；成功顯示稽核編號、待入帳字樣與兩個入帳指令，
 *    對話框不自動關閉（關掉＝收據消失）。成功後表單收起（避免對同一張卡重複送出第二筆決定）；關閉後重開同一張卡不沿用上次結果（內容元件隨對話框卸載）。
 */
import { Send } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useSiDecide } from "@/lib/api/queries";
import type { SiProposal, SiWriteReceipt } from "@/lib/api/types";
import { DECIDE_FIELDS, SI_REASON_CLASSES, SI_REASON_MAX, buildDecideRequest, decideVerbOptions, digest8, isDecideKind, siWriteErrorText, validateDecideForm } from "@/lib/domain/si";
import { SiWriteResult } from "./siParts";

/** 對話框的對象：提案卡（點擊當下的快照，綁其卡面 digest）或橫幅暫停的運轉（恢復；沒有 digest）。 */
export type DecideTarget = { kind: "prop"; proposal: SiProposal } | { kind: "run"; run: string };

export function SiDecideDialog({ target, onClose }: { target: DecideTarget | null; onClose: () => void }) {
  return (
    <Dialog open={target !== null} onOpenChange={(next) => !next && onClose()}>
      {target ? (
        <DialogContent
          data-testid="si-decide-dialog"
          title={target.kind === "prop" ? `決定：${target.proposal.id}` : `恢復運轉：${target.run}`}
          description="自我進化決定：簽成稽核檔落到主機端，入帳前尚未生效；預設不選動詞，沒有批次核准"
        >
          <DecideBody target={target} onClose={onClose} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function DecideBody({ target, onClose }: { target: DecideTarget; onClose: () => void }) {
  const toast = useToast();
  const decide = useSiDecide();
  const sending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [dkind, setDkind] = useState("");
  const [reason, setReason] = useState("");
  const [reasonClass, setReasonClass] = useState("");
  const [unverifiedAck, setUnverifiedAck] = useState(false);
  const [receipt, setReceipt] = useState<SiWriteReceipt | null>(null);

  const subject = target.kind === "prop" ? target.proposal.id : target.run;
  /** 開啟當下的卡面 digest（恢復沒有）。 */
  const boundDigest = target.kind === "prop" ? target.proposal.digest : "";
  const verbs = useMemo(() => decideVerbOptions(target.kind === "prop" ? target.proposal : { suspended: { run: target.run } }), [target]);
  const selected = verbs.find((v) => v.dkind === dkind);
  const need = isDecideKind(dkind) ? DECIDE_FIELDS[dkind] : null;

  // 表單送給驗證與請求組裝的值：該動詞用不到的欄位一律視為沒填（切換動詞時隱藏欄位的殘值不會被送出、也不會被誤判成禁止欄）
  const form = {
    dkind,
    digest: need?.digest ? boundDigest : "",
    reason: need?.reason ? reason : "",
    reasonClass: need?.reasonClass ? reasonClass : "",
    unverifiedAck: selected?.needsAck === true && unverifiedAck,
  };
  const errors = validateDecideForm(form, { needsAck: selected?.needsAck === true });
  const blocked = Object.values(errors)[0] ?? null;

  function pick(next: string) {
    setDkind(next);
    setReason("");
    setReasonClass("");
    setUnverifiedAck(false);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (sending.current || blocked !== null) return;
    sending.current = true;
    setBusy(true);
    try {
      setReceipt(await decide.mutateAsync({ id: subject, body: buildDecideRequest(form) }));
    } catch (error) {
      toast.error(siWriteErrorText(error));
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }

  if (receipt) {
    return (
      <>
        <DialogBody>
          <SiWriteResult testId="si-decide-result" receipt={receipt} />
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
        <dl className="grid grid-cols-[6rem_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-wg-muted">{target.kind === "prop" ? "提案" : "運轉"}</dt>
          <dd className="font-mono break-all">{subject}</dd>
          {target.kind === "prop" ? (
            <>
              <dt className="text-wg-muted">狀態</dt>
              <dd>{`${target.proposal.state}｜verdict ${target.proposal.verdict === null || target.proposal.verdict === undefined ? "無" : String(target.proposal.verdict)}`}</dd>
              <dt className="text-wg-muted">卡面 digest</dt>
              <dd>
                <code data-testid="si-decide-digest" title={boundDigest} className="font-mono">
                  {digest8(boundDigest)}
                </code>
                <span className="ml-2 text-xs text-wg-muted">送出時綁定此值；卡面若已變動，入帳時由主機端 CLI 拒收</span>
              </dd>
            </>
          ) : (
            <>
              <dt className="text-wg-muted">說明</dt>
              <dd>橫幅顯示此運轉因連續壞窗而暫停；恢復須先人工檢視壞窗，並寫下理由。</dd>
            </>
          )}
        </dl>

        <Field label="決定動詞">
          <Select value={dkind} onChange={(e) => pick(e.target.value)} data-testid="si-decide-verb">
            <option value="">請選擇動詞</option>
            {verbs.map((v) => (
              <option key={v.dkind} value={v.dkind}>
                {v.label}
              </option>
            ))}
          </Select>
        </Field>

        {need?.reason ? (
          <Field label="理由" hint={`（1～${SI_REASON_MAX} 字元，單行）`} error={reason !== "" ? errors.reason : undefined}>
            <Textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} aria-invalid={reason !== "" && errors.reason ? true : undefined} data-testid="si-decide-reason" />
          </Field>
        ) : null}

        {need?.reasonClass ? (
          <Field label="理由類別">
            <Select value={reasonClass} onChange={(e) => setReasonClass(e.target.value)} data-testid="si-decide-class">
              <option value="">請選擇類別</option>
              {SI_REASON_CLASSES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </Field>
        ) : null}

        {selected?.needsAck ? (
          <label className="flex cursor-pointer items-start gap-2 text-sm">
            <Checkbox checked={unverifiedAck} onCheckedChange={(v) => setUnverifiedAck(v === true)} data-testid="si-decide-ack" aria-label="已知悉此提案未經驗證即採納" className="mt-0.5" />
            <span>已知悉此提案的驗證結果為 NE（量不到），仍要晉升（未驗採納）。</span>
          </label>
        ) : null}

        {blocked ? (
          <p data-testid="si-decide-blocked" className="text-sm text-wg-muted">
            {`尚不能送出：${blocked}`}
          </p>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          取消
        </Button>
        <Button type="submit" iconLeft={Send} loading={busy} disabled={blocked !== null} data-testid="si-decide-submit">
          送出決定
        </Button>
      </DialogFooter>
    </form>
  );
}
