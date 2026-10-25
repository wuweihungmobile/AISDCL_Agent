"use client";

/**
 * 關閉觀察對話框（P2b；TCS-SelfImprovingDecide-P2b W20；PRD AC-SI-35-2）：ADMIN 對處置**恰為 open** 的觀察列選一個終值（七個，沒有 open）關閉它。
 *
 * 終值與附加欄位（表 M-C）：fixed／def／merged／proposed 帶 `ref`（格式依終值），deferred／retired／decided 帶 `text`（1～120 字元、不含豎線、控制字元與
 * 「之後再看」）；兩者恰擇一。終值與附加文字以全形冒號相接成處置字串——由 backend 組、前端只送 `{ terminal, ref?|text? }`。
 * 送出與成功態同決定對話框（請求中停用、連點只送一次；失敗 toast 且不關窗；成功顯示稽核編號、待入帳與入帳指令、不自動關閉）。
 * 列規則與前提（`retired` 的座標、該列是否仍為 open、`corrects` 之類）入帳時才由主機端 CLI 判，前端不複製（⚖15）。
 */
import { Send } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useSiCloseObservation } from "@/lib/api/queries";
import type { SiWriteReceipt } from "@/lib/api/types";
import { SI_CLOSE_TEXT_MAX, SI_TERMINALS, buildCloseRequest, closeRefHint, siWriteErrorText, terminalTakesRef, validateCloseForm } from "@/lib/domain/si";
import { SiWriteResult } from "./siParts";

/** 對話框的對象：要關閉的觀察號（呼叫端只對處置恰為 open 的列提供入口）。 */
export type CloseTarget = { obsId: string };

export function SiObsCloseDialog({ target, onClose }: { target: CloseTarget | null; onClose: () => void }) {
  return (
    <Dialog open={target !== null} onOpenChange={(next) => !next && onClose()}>
      {target ? (
        <DialogContent data-testid="si-obs-close-dialog" title={`關閉觀察：${target.obsId}`} description="自我進化觀察：簽成稽核檔落到主機端，入帳前尚未寫進帳本">
          <CloseBody target={target} onClose={onClose} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function CloseBody({ target, onClose }: { target: CloseTarget; onClose: () => void }) {
  const toast = useToast();
  const close = useSiCloseObservation();
  const sending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [terminal, setTerminal] = useState("");
  const [ref, setRef] = useState("");
  const [text, setText] = useState("");
  const [receipt, setReceipt] = useState<SiWriteReceipt | null>(null);

  const takesRef = terminalTakesRef(terminal);
  // 該終值用不到的欄位視為沒填（切換終值時隱藏欄位的殘值不會被送出、也不會被誤判成禁止欄）
  const form = { terminal, ref: takesRef ? ref : "", text: terminal !== "" && !takesRef ? text : "" };
  const errors = validateCloseForm(form);
  const blocked = Object.values(errors)[0] ?? null;

  function pick(next: string) {
    setTerminal(next);
    setRef("");
    setText("");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (sending.current || blocked !== null) return;
    sending.current = true;
    setBusy(true);
    try {
      setReceipt(await close.mutateAsync({ id: target.obsId, body: buildCloseRequest(form) }));
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
          <SiWriteResult testId="si-close-result" receipt={receipt} />
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
        <p className="text-sm">
          {"觀察 "}
          <code className="font-mono">{target.obsId}</code>
          {" 的處置目前為 open；選一個終值關閉它（終值不含 open）。"}
        </p>
        <Field label="終值">
          <Select value={terminal} onChange={(e) => pick(e.target.value)} data-testid="si-close-terminal">
            <option value="">請選擇終值</option>
            {SI_TERMINALS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </Field>
        {terminal !== "" && takesRef ? (
          <Field label="參照" hint={`（${closeRefHint(terminal)}）`} error={ref !== "" ? errors.ref : undefined}>
            <Input
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              autoComplete="off"
              className="font-mono"
              aria-invalid={ref !== "" && errors.ref ? true : undefined}
              data-testid="si-close-ref"
            />
          </Field>
        ) : null}
        {terminal !== "" && !takesRef ? (
          <Field label="說明" hint={`（1～${SI_CLOSE_TEXT_MAX} 字元；不可含豎線、換行與「之後再看」）`} error={text !== "" ? errors.text : undefined}>
            <Textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} aria-invalid={text !== "" && errors.text ? true : undefined} data-testid="si-close-text" />
          </Field>
        ) : null}
        {blocked ? (
          <p data-testid="si-close-blocked" className="text-sm text-wg-muted">
            {`尚不能送出：${blocked}`}
          </p>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          取消
        </Button>
        <Button type="submit" iconLeft={Send} loading={busy} disabled={blocked !== null} data-testid="si-close-submit">
          送出關閉
        </Button>
      </DialogFooter>
    </form>
  );
}
