"use client";

/**
 * 公開遠端庫的確認（軌道 B；FR-R2P-13-3；TCS-ResearchToPRD-P1-20261107 AT-961-17-4、17-E-1）：
 * 可見度切到「公開」時顯示警示「PRD 與證據矩陣將公開」，並要求重新輸入庫名；比對為逐字完全相等（不修剪、不正規化——
 * 差一個字元、大小寫、尾端空白、貼上的不可見字元都不符），所以這裡不對輸入做任何處理。警示用 Lucide 圖示，不只靠顏色。
 */
import { TriangleAlert } from "lucide-react";

import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { isRepoNameConfirmed } from "@/lib/domain/research";

export function PublicRepoConfirm({
  repoName,
  value,
  onChange,
  disabled = false,
  disabledTitle,
}: {
  /** 軌道 B 實際使用的庫名（省略時為專案名稱） */
  repoName: string;
  value: string;
  onChange: (next: string) => void;
  disabled?: boolean;
  disabledTitle?: string;
}) {
  const confirmed = isRepoNameConfirmed(repoName, value);
  return (
    <div data-testid="public-repo-confirm" data-confirmed={confirmed} className="flex flex-col gap-2 rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-3">
      <p role="note" className="flex items-center gap-2 text-sm font-semibold text-wg-warning-text">
        <TriangleAlert size={16} aria-hidden />
        PRD 與證據矩陣將公開
      </p>
      <Field label="重新輸入庫名" hint="須與庫名完全相同" error={value !== "" && !confirmed ? "與庫名不完全相同（大小寫、空白與不可見字元都要一致）" : undefined}>
        <Input value={value} disabled={disabled} title={disabled ? disabledTitle : undefined} autoComplete="off" spellCheck={false} onChange={(event) => onChange(event.target.value)} />
      </Field>
    </div>
  );
}
