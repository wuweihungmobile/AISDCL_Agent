"use client";

/**
 * SCR 發起對話框（FR-R2P-19 UI 半；TCS-ResearchToPRD-P2-20261107 AT-962-15-*；IFACE-P2 §7）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **兩處入口同一元件**：看板與步驟 4 頁頂都用 `ScrLaunchButton`；自癒監視器與 SCG 登錄的「發起 SCR」直接受控開本對話框並預填 `sourceKind`。
 *  - **欄位邊界取自 `lib/domain/research.ts` 的單一常數**（reason 500、章節 20 項×200、證據連結 500）；證據連結只接受 https，以**獨立欄**送出（D-138 Q-12），
 *    顯示為純文字外部連結（`rel="noopener noreferrer"`），不附在 reason 末行；`reasonClass` 送中文原文。
 *  - **`HEALING_FAILED` 來源只顯示可複製指令**（200＋`recovery`），不顯示「已發起」成功態；MAJOR 成功導向後繼研究專案（D-145）。
 *  - **錯誤取登記表**：422 `violations[{field}]` 逐筆回到欄位下；其餘 reason 取 `RESEARCH_REASON_TEXT`（經 `researchErrorText`），不內嵌第二份。
 *  - 權限：OPERATOR 以上；VIEWER 的入口停用且 `title` 為唯讀說明，請求數為 0。
 */
import { FilePenLine } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { CopyCommand } from "@/components/domain/sdd/CopyCommand";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useOpenResearchScr, usePrdVersion, usePrdVersions } from "@/lib/api/queries";
import type { ResearchScrKind, ResearchScrOpenResult } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  BUILD_DISABLED_TEXT,
  READONLY_TITLE,
  SCR_KIND_TEXT,
  SCR_REASON_CLASSES,
  SCR_REASON_MAX,
  SCR_SOURCE_LABEL,
  researchErrorText,
  scrFormView,
  scrSectionOptions,
  scrViolationsByField,
} from "@/lib/domain/research";

export function ScrRequestDialog({ researchId, open, onOpenChange, sourceKind = "HUMAN" }: { researchId: string; open: boolean; onOpenChange: (open: boolean) => void; sourceKind?: string }) {
  const { canWrite } = useAuth();
  const router = useRouter();
  const open_ = useOpenResearchScr();
  const versions = usePrdVersions(open ? researchId : undefined);
  const latest = versions.data !== undefined && versions.data.length > 0 ? versions.data[versions.data.length - 1].versionNo : null;
  const prd = usePrdVersion(open ? researchId : undefined, latest);
  const options = useMemo(() => scrSectionOptions(prd.data?.content), [prd.data?.content]);

  const [kind, setKind] = useState<ResearchScrKind>("MINOR");
  const [source, setSource] = useState(sourceKind);
  const [reason, setReason] = useState("");
  const [reasonClass, setReasonClass] = useState<string>(SCR_REASON_CLASSES[0]);
  const [sections, setSections] = useState<string[]>([]);
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [result, setResult] = useState<ResearchScrOpenResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  const form = { kind, sourceKind: source, reason, reasonClass, affectedSections: sections, evidenceUrl };
  const view = scrFormView(form);
  const violations = scrViolationsByField(error);
  const fieldError = (key: keyof typeof view.errors, field: string): string | undefined => view.errors[key] ?? violations[field]?.join("；");

  function submit() {
    if (!canWrite || !view.valid) return;
    setError(null);
    open_.mutate(
      {
        id: researchId,
        body: {
          kind,
          sourceKind: source as "HUMAN",
          reason: reason.trim(),
          reasonClass,
          affectedSections: sections,
          ...(evidenceUrl.trim() === "" ? {} : { evidenceUrl: evidenceUrl.trim() }),
        },
      },
      {
        onSuccess: (data) => {
          setResult(data);
          if (kind === "MAJOR" && typeof data.successorResearchId === "string" && data.successorResearchId !== "") {
            router.push(`/research/${encodeURIComponent(data.successorResearchId)}`);
            onOpenChange(false);
          }
        },
        onError: (e) => setError(e),
      },
    );
  }

  const recovery = result?.recovery ?? null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title="發起規格變更（SCR）" description="規格變更請求：理由、分類與受影響章節" data-testid="scr-dialog">
        <DialogBody>
          {result !== null && recovery !== null ? (
            <div data-testid="scr-recovery" className="flex flex-col gap-3 text-sm">
              <p>自癒失敗來源不會直接發起：請在 Console 外依下列指令處理（目標：{recovery.target}）。</p>
              <CopyCommand shell="powershell" label="PowerShell" command={recovery.powershell} />
              <CopyCommand shell="posix" label="bash／zsh" command={recovery.posix} />
            </div>
          ) : result !== null ? (
            <p role="status" data-testid="scr-started" className="text-sm font-semibold">
              SCR 已發起
            </p>
          ) : (
            <>
              <fieldset className="flex flex-col gap-2">
                <legend className="text-sm font-medium">變更類型</legend>
                {(["MINOR", "MAJOR"] as const).map((k) => (
                  <label key={k} className="flex items-start gap-2 text-sm">
                    <input type="radio" name="scr-kind" value={k} checked={kind === k} onChange={() => setKind(k)} className="mt-1" />
                    <span>
                      <span className="font-semibold">{k === "MINOR" ? "小幅（MINOR）" : "大幅（MAJOR）"}</span>
                      <span className="block text-wg-muted" data-testid={`scr-kind-text-${k}`}>
                        {SCR_KIND_TEXT[k]}
                      </span>
                    </span>
                  </label>
                ))}
                {violations.kind !== undefined ? (
                  <p role="alert" className="text-sm text-wg-error">
                    {violations.kind.join("；")}
                  </p>
                ) : null}
              </fieldset>
              <Field label="來源" error={violations.sourceKind?.join("；")}>
                <Select value={source} onChange={(e) => setSource(e.target.value)} data-testid="scr-source">
                  {Object.entries(SCR_SOURCE_LABEL).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="變更理由" error={fieldError("reason", "reason")}>
                <Textarea value={reason} onChange={(e) => setReason(e.target.value)} aria-invalid={fieldError("reason", "reason") !== undefined && reason !== ""} />
              </Field>
              <p data-testid="scr-reason-counter" className="-mt-2 text-xs text-wg-muted">
                剩餘 {view.reasonRemaining} 字（上限 {SCR_REASON_MAX} 字）
              </p>
              <Field label="理由分類" error={view.errors.reasonClass ?? violations.reasonClass?.join("；")}>
                <Select value={reasonClass} onChange={(e) => setReasonClass(e.target.value)} data-testid="scr-reason-class">
                  {SCR_REASON_CLASSES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="受影響章節" as="group" error={fieldError("affectedSections", "affectedSections")}>
                <div data-testid="scr-sections" className="flex max-h-40 flex-col gap-1 overflow-y-auto rounded-md border border-wg-line p-2 text-sm">
                  {options.length === 0 ? <span className="text-wg-muted">（凍結 PRD 尚無可選章節）</span> : null}
                  {options.map((o) => (
                    <label key={o.value} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        value={o.value}
                        checked={sections.includes(o.value)}
                        onChange={(e) => setSections((cur) => (e.target.checked ? [...cur, o.value] : cur.filter((s) => s !== o.value)))}
                      />
                      {o.label}
                    </label>
                  ))}
                </div>
              </Field>
              <Field label="證據連結" hint="（選填，只接受 https）" error={fieldError("evidenceUrl", "evidenceUrl")}>
                <Input value={evidenceUrl} onChange={(e) => setEvidenceUrl(e.target.value)} inputMode="url" placeholder="https://" />
              </Field>
              {error !== null && Object.keys(violations).length === 0 ? (
                <p role="alert" data-testid="scr-error" className="text-sm text-wg-error">
                  {researchErrorText(error)}
                </p>
              ) : null}
            </>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {result === null ? "取消" : "關閉"}
          </Button>
          {result === null ? (
            <Button disabled={!canWrite || !view.valid} loading={open_.isPending} title={canWrite ? undefined : READONLY_TITLE} onClick={submit} data-testid="scr-submit">
              送出
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** 入口鈕（看板與步驟 4 頁頂共用）：OPERATOR 以上可點；VIEWER 停用並說明；規格變更進行中停用並顯示登記文案。 */
export function ScrLaunchButton({ researchId, sourceKind = "HUMAN", scrOpen = false, label = "發起規格變更（SCR）" }: { researchId: string; sourceKind?: string; scrOpen?: boolean; label?: string }) {
  const { canWrite } = useAuth();
  const [open, setOpen] = useState(false);
  const blocked = !canWrite ? READONLY_TITLE : scrOpen ? BUILD_DISABLED_TEXT.scrOpen : undefined;
  return (
    <>
      <Button variant="ghost" iconLeft={FilePenLine} disabled={blocked !== undefined} title={blocked} onClick={() => setOpen(true)} data-testid="scr-launch">
        {label}
      </Button>
      {open ? <ScrRequestDialog researchId={researchId} open={open} onOpenChange={setOpen} sourceKind={sourceKind} /> : null}
    </>
  );
}
