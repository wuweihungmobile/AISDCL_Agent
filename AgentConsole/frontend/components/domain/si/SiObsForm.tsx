"use client";

/**
 * 新增觀察與更正表單（P2b；TCS-SelfImprovingDecide-P2b W19；PRD AC-SI-35-1、35-2）：ADMIN 新增一列觀察，或從既有觀察列「更正」（`corrects` 預填且唯讀）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **即時拒收**：三個字串欄一出現豎線（觀察列是 Markdown 九欄表）或控制字元（換行、TAB）就在欄位下顯示錯誤、停用送出——這些是「根層入帳時不拒、事後 `check` 才轉紅」的形態，
 *    不能等到簽進稽核檔才發現。欄位用多行輸入框，正是為了讓貼上的換行看得見、被擋下（單行輸入框會靜默吞掉換行）。第一次輸入前不顯示必填紅字，只在送出鈕旁說明原因。
 *  - **邊打邊估**：`estimateRowBytes` 以與根層 CLI 相同的九欄組列規則估計入帳列的位元組數，顯示在估計值與上限（`rowMaxBytes`，預檢回來前用 700）旁；
 *    估計值大於上限只警示、不阻擋（⚖26：僅供提示，權威是預檢與 CLI）；含豎線或控制字元者不給估計值。三欄位元組和超過 700 是必要條件，才會停用送出。
 *  - **先預檢再寫入**：送出＝先 `postSiObservationValidate`（零副作用）；`ok=false` 顯示 findings（code 與 detail 逐字，純文字）並**不**送寫入；`ok=true` 顯示預覽列與位元組後才送
 *    `postSiObservation`；預檢回 422 或 503 一律以 toast 顯示原因、不送。請求中停用、連點只送一次。
 *  - 成功顯示稽核編號、待入帳字樣與入帳指令，對話框不自動關閉；表單收起（避免重複送出），預覽列保留在收據上方。
 */
import { Send } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useSiAddObservation, useSiValidateObservation } from "@/lib/api/queries";
import type { SiValidation, SiWriteReceipt } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  EMPTY_OBSERVATION_FORM,
  GUARD_FACE,
  SI_CATEGORIES,
  SI_EXPOSURES,
  SI_FACES,
  SI_OBS_FIELD_MAX,
  SI_ROW_MAX_DEFAULT,
  SI_SEVERITIES,
  buildObservationRequest,
  estimateRowBytes,
  siWriteErrorText,
  validateObservationForm,
  type ObservationForm,
} from "@/lib/domain/si";
import { SiWriteResult } from "./siParts";

/** 表單的對象：新增一列，或更正既有的一列（`corrects` 預填且唯讀）。 */
export type ObsFormTarget = { mode: "new" } | { mode: "correct"; corrects: string };

export function SiObsForm({ target, onClose }: { target: ObsFormTarget | null; onClose: () => void }) {
  return (
    <Dialog open={target !== null} onOpenChange={(next) => !next && onClose()}>
      {target ? (
        <DialogContent
          data-testid="si-obs-dialog"
          title={target.mode === "correct" ? `更正觀察：${target.corrects}` : "新增觀察"}
          description="自我進化觀察：先預檢、再簽成稽核檔落到主機端，入帳前尚未寫進帳本"
        >
          <ObsBody target={target} onClose={onClose} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function ObsBody({ target, onClose }: { target: ObsFormTarget; onClose: () => void }) {
  const { username } = useAuth();
  const toast = useToast();
  const validate = useSiValidateObservation();
  const add = useSiAddObservation();
  const sending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<ObservationForm>({ ...EMPTY_OBSERVATION_FORM, corrects: target.mode === "correct" ? target.corrects : "" });
  /** 使用者動過任何欄位之後才顯示欄位錯誤（第一次輸入前不在空表單上鋪滿必填紅字）。 */
  const [dirty, setDirty] = useState(false);
  const [validation, setValidation] = useState<SiValidation | null>(null);
  const [receipt, setReceipt] = useState<SiWriteReceipt | null>(null);

  const errors = validateObservationForm(form);
  const invalid = Object.keys(errors).length > 0;
  const estimate = estimateRowBytes(form, { user: username });
  const maxBytes = validation?.rowMaxBytes ?? SI_ROW_MAX_DEFAULT;

  function set<K extends keyof ObservationForm>(key: K, value: ObservationForm[K]) {
    setDirty(true);
    setForm((prev) => ({ ...prev, [key]: value, ...(key === "face" && value !== GUARD_FACE ? { exposure: "" } : {}) }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (sending.current || invalid) return;
    sending.current = true;
    setBusy(true);
    try {
      const body = buildObservationRequest(form);
      const checked = await validate.mutateAsync(body);
      setValidation(checked);
      if (!checked.ok) return; // findings 顯示在下方；不送寫入，改正後再送
      setReceipt(await add.mutateAsync(body));
    } catch (error) {
      toast.error(siWriteErrorText(error));
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }

  // 預檢不通過時 `row` 是空字串（沒有預覽列可看）：只有真的有預覽列才顯示這一塊
  const preview =
    validation && validation.row !== "" ? (
      <div data-testid="si-obs-preview" className="rounded-md border border-wg-line bg-wg-base px-3 py-2 text-sm">
        <p className="text-wg-muted">{`預覽列（${validation.rowBytes} 位元組／上限 ${validation.rowMaxBytes ?? "量不到"}）`}</p>
        <pre className="mt-1 font-mono text-xs break-all whitespace-pre-wrap">{validation.row}</pre>
      </div>
    ) : null;

  if (receipt) {
    return (
      <>
        <DialogBody>
          {preview}
          <SiWriteResult testId="si-obs-result" receipt={receipt} />
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            關閉
          </Button>
        </DialogFooter>
      </>
    );
  }

  const shown = (field: keyof ObservationForm) => (dirty ? errors[field] : undefined);
  const textField = (field: "context" | "symptom" | "evidence", label: string, testId: string) => (
    <Field label={label} hint={`（1～${SI_OBS_FIELD_MAX} 字元；不可含豎線與換行）`} error={shown(field)}>
      <Textarea rows={2} className="min-h-11" value={form[field]} onChange={(e) => set(field, e.target.value)} aria-invalid={shown(field) ? true : undefined} data-testid={testId} />
    </Field>
  );
  const choice = (field: "category" | "severity" | "face" | "exposure", label: string, options: ReadonlyArray<string>, testId: string) => (
    <Field label={label} error={shown(field)}>
      <Select value={form[field]} onChange={(e) => set(field, e.target.value)} aria-invalid={shown(field) ? true : undefined} data-testid={testId}>
        <option value="">請選擇</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </Select>
    </Field>
  );

  return (
    <form data-testid="si-obs-form" onSubmit={submit} noValidate>
      <DialogBody>
        {target.mode === "correct" ? (
          <Field label="被更正的觀察" hint="（唯讀；新列的標記欄會帶 rel=corrects）">
            <Input value={form.corrects} readOnly className="font-mono" data-testid="si-obs-corrects" />
          </Field>
        ) : null}
        {textField("context", "情境", "si-obs-context")}
        {textField("symptom", "症狀", "si-obs-symptom")}
        {textField("evidence", "證據座標", "si-obs-evidence")}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {choice("category", "分類", SI_CATEGORIES, "si-obs-category")}
          {choice("severity", "嚴重度", SI_SEVERITIES, "si-obs-severity")}
          {choice("face", "面", SI_FACES, "si-obs-face")}
        </div>
        {form.face === GUARD_FACE ? choice("exposure", "暴露度", SI_EXPOSURES, "si-obs-exposure") : null}
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <Checkbox checked={form.externalDerived} onCheckedChange={(v) => set("externalDerived", v === true)} data-testid="si-obs-external" aria-label="外部衍生" />
          外部衍生（由外部資料衍生的列；提案不把它算作內部來源）
        </label>

        <p data-testid="si-obs-estimate" className="text-sm text-wg-muted">
          {estimate === null ? (
            "無法估計：欄位含豎線或控制字元，這份輸入會被拒收"
          ) : (
            <>
              {`預估入帳列 ${estimate} 位元組／上限 ${maxBytes}（僅供提示，以預檢為準）`}
              {estimate > maxBytes ? <span className="ml-1 text-wg-warning-text">估計值超過上限，入帳可能被拒收</span> : null}
            </>
          )}
        </p>

        {invalid ? (
          <p data-testid="si-obs-blocked" className="text-sm text-wg-muted">
            {`尚不能送出：${Object.values(errors)[0]}`}
          </p>
        ) : null}

        {preview}
        {validation && !validation.ok ? (
          <div data-testid="si-obs-findings" role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm">
            <p className="font-semibold text-wg-accent">預檢不通過，未送出；請依下列原因修改後再送</p>
            <ul className="mt-1 list-disc pl-5">
              {validation.findings.map((f, i) => (
                <li key={`${i}-${f.code}`} className="break-words">
                  <code className="font-mono">{f.code}</code>
                  {`：${f.detail}`}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          取消
        </Button>
        <Button type="submit" iconLeft={Send} loading={busy} disabled={invalid} data-testid="si-obs-submit">
          預檢並送出
        </Button>
      </DialogFooter>
    </form>
  );
}
