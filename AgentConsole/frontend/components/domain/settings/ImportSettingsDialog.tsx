"use client";

/**
 * 匯入設定對話框（US-S-06；契約 §1.5.10）：選 JSON 檔（≤1MB）→ 上傳 → 顯示 applied／skipped／errors[]。
 * 部分失敗仍是 200，逐筆原因在 errors[]（`category.key — reason`）；加密參數的 `<encrypted>` 佔位值會被略過（計入 skipped）。
 */
import { CircleCheckBig, FileText, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { describeError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import { useImportSettings } from "@/lib/api/queries";
import type { ImportSettingsResult } from "@/lib/api/types";
import { formatBytes } from "@/lib/format";

/** 設定檔上限 1MB（契約 §1.5.10） */
export const MAX_SETTINGS_FILE_BYTES = 1024 * 1024;

/** 前端預檢：副檔名須為 .json、大小 ≤1MB；通過回 null，否則回契約 reason 逐字。 */
export function validateSettingsFile(file: { name: string; size: number }): string | null {
  if (!file.name.toLowerCase().endsWith(".json")) return REASONS.SETTINGS_FILE_NOT_JSON;
  if (file.size > MAX_SETTINGS_FILE_BYTES) return REASONS.SETTINGS_FILE_TOO_LARGE;
  return null;
}

export function ImportSettingsDialog({
  open,
  onClose,
  onApplied,
}: {
  open: boolean;
  onClose: () => void;
  /** 匯入完成（200）後呼叫：頁面清掉本地草稿，改看伺服器值 */
  onApplied: (result: ImportSettingsResult) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      {open ? (
        <DialogContent title="匯入設定" description="選擇由「匯出設定」產生的 JSON 檔並匯入">
          <ImportBody onClose={onClose} onApplied={onApplied} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function ImportBody({ onClose, onApplied }: { onClose: () => void; onApplied: (r: ImportSettingsResult) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const importer = useImportSettings();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportSettingsResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function choose(next: File | undefined) {
    if (!next) return;
    setResult(null);
    setError(null);
    const reason = validateSettingsFile(next);
    setFileError(reason);
    setFile(reason ? null : next);
  }

  async function submit() {
    if (!file) return;
    setError(null);
    try {
      const r = await importer.mutateAsync(file);
      setResult(r);
      onApplied(r);
    } catch (e) {
      setError(describeError(e));
    }
  }

  return (
    <>
      <DialogBody>
        <p className="text-sm leading-relaxed text-wg-muted">
          選擇由「匯出設定」產生的 JSON 檔（≤ 1MB）。每筆設定會逐一驗證後在同一交易套用；加密參數的{" "}
          <code className="font-mono text-xs">&lt;encrypted&gt;</code> 佔位值不會被匯入。
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={input}
            type="file"
            accept=".json,application/json"
            className="sr-only"
            tabIndex={-1}
            aria-label="選擇設定檔"
            data-testid="settings-file-input"
            onChange={(e) => {
              choose(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <Button variant="ghost" iconLeft={FileText} onClick={() => input.current?.click()}>
            選擇檔案
          </Button>
          {file ? (
            <span data-testid="settings-selected-file" className="text-sm break-all">
              {file.name}（{formatBytes(file.size)}）
            </span>
          ) : (
            <span className="text-sm text-wg-muted">尚未選擇檔案</span>
          )}
        </div>
        {fileError ? (
          <p role="alert" className="text-[13px] text-wg-error">
            {fileError}
          </p>
        ) : null}
        {error ? (
          <p role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
            {error}
          </p>
        ) : null}
        {result ? (
          <div role="status" data-testid="settings-import-result" className="rounded-md border border-wg-line bg-wg-base px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <CircleCheckBig size={18} className="text-wg-primary" aria-hidden />
              <span>
                已套用 <b data-testid="import-applied">{result.applied}</b> 項、略過 <b data-testid="import-skipped">{result.skipped}</b> 項
                {result.errors.length > 0 ? (
                  <>
                    、失敗 <b data-testid="import-failed">{result.errors.length}</b> 項
                  </>
                ) : null}
              </span>
            </div>
            {result.errors.length > 0 ? (
              <ul data-testid="settings-import-errors" className="mt-2 flex flex-col gap-1.5">
                {result.errors.map((e, i) => (
                  <li key={`${e.category}.${e.key}-${i}`} data-testid="settings-import-error" className="text-[13px] break-words text-wg-error">
                    <code className="font-mono text-xs">
                      {e.category}.{e.key}
                    </code>
                    {" — "}
                    {e.reason}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={importer.isPending}>
          {result ? "關閉" : "取消"}
        </Button>
        <Button iconLeft={Upload} loading={importer.isPending} disabled={!file} onClick={submit}>
          匯入
        </Button>
      </DialogFooter>
    </>
  );
}
