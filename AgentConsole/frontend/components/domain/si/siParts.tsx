"use client";

/**
 * SelfImproving 頁的共用小件（P1b；TCS-SelfImprovingMirror-P1b R12、R14～R17）：載入態、錯誤態、ne／problems 清單、載入更多、
 * 篩選下拉、展開鈕、分頁標籤筆數回報；P2b 另加稽核檔收據與入帳指令（三個寫入元件與對帳面板共用）。
 * 全部只輸出 React 文字節點（R18：帳本字串不經 HTML 或 Markdown 渲染），**沒有任何寫入控制項、表單或 mutation**（寫入形態只住三個寫入元件，W22）。
 */
import { ChevronDown, ChevronRight } from "lucide-react";
import { useEffect } from "react";

import { CopyCommand } from "@/components/domain/sdd/CopyCommand";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Select } from "@/components/ui/select";
import { ErrorState } from "@/components/ui/states";
import type { SiNeEntry, SiProblem, SiWriteKind, SiWriteReceipt } from "@/lib/api/types";
import { formatNe, formatProblem, ingestCommands, siErrorParts, siErrorSummary } from "@/lib/domain/si";

/** 面板載入中：`role="status"`、文字含「載入中」（R12）。 */
export function SiLoading({ what }: { what: string }) {
  return (
    <div role="status" data-testid="si-loading" className="px-1 py-6 text-sm text-wg-muted">
      {`${what}載入中…`}
    </div>
  );
}

/**
 * 面板錯誤態（R12、R19）：只顯示錯誤，**不渲染資料**（即使快取殘留上一次成功的資料）；reason、detail、cause 逐字，沒有空表或零筆字樣。
 * 一句摘要之外，後端回的 reason（例 `si_unavailable`）、Bridge 的 detail（`rc=<n>; stderr=…`）與 cause 都原樣顯示，方便對照 Bridge 的日誌。
 */
export function SiError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const { reason, detail, cause } = siErrorParts(error);
  return (
    <div data-testid="si-error" className="flex flex-col gap-2">
      <ErrorState error={error} title="自我進化資料無法取得" />
      <div className="flex flex-col gap-1.5 rounded-md border border-wg-line bg-wg-surface px-4 py-3 text-sm">
        <p data-testid="si-error-summary" className="font-medium text-wg-text">
          {siErrorSummary(error)}
        </p>
        {reason ? (
          <p className="text-wg-muted">
            {"reason："}
            <code data-testid="si-error-reason" className="font-mono text-wg-text">
              {reason}
            </code>
          </p>
        ) : null}
        {cause ? (
          <p className="text-wg-muted">
            {"cause："}
            <code data-testid="si-error-cause" className="font-mono text-wg-text">
              {cause}
            </code>
          </p>
        ) : null}
        {detail ? (
          <p className="text-wg-muted">
            {"detail："}
            <code data-testid="si-error-detail" className="font-mono break-all whitespace-pre-wrap text-wg-text">
              {detail}
            </code>
          </p>
        ) : null}
        <div>
          <Button variant="ghost" size="sm" data-testid="si-retry" onClick={onRetry}>
            重試
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * 該面板回應的 `ne[]`（量不到的欄位與原因）與 `problems[]`（例：壞列 ROW-ARITY）。為空時不顯示該區（不顯示「0 項」）；
 * 量不到一律以「量不到（NOT-EVALUABLE）」加原因呈現，不得顯示成 0、無或通過（R16）。
 */
export function SiNotes({ ne, problems }: { ne: ReadonlyArray<SiNeEntry>; problems: ReadonlyArray<SiProblem> }) {
  if (ne.length === 0 && problems.length === 0) return null;
  return (
    <div className="mb-3 flex flex-col gap-2 text-sm">
      {ne.length > 0 ? (
        <div data-testid="si-ne-list" className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2">
          <p className="font-medium text-wg-warning-text">量不到（NOT-EVALUABLE）的欄位</p>
          <ul className="mt-1 list-disc pl-5">
            {ne.map((entry, i) => (
              <li key={`${entry.field}-${i}`} className="break-all">
                {formatNe(entry)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {problems.length > 0 ? (
        <div data-testid="si-problems-list" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2">
          <p className="font-medium text-wg-accent">帳本問題</p>
          <ul className="mt-1 list-disc pl-5">
            {problems.map((problem, i) => (
              <li key={`${problem.subject}-${problem.code}-${i}`} className="break-all">
                {formatProblem(problem)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

/**
 * 載入更多（R15）：有下一頁游標時顯示按鈕；回應標示 truncated 卻沒有游標（契約被違反，不該發生）時大聲說，
 * 不假裝已載入全部。按鈕在取下一頁時停用但名稱不變。
 */
export function SiLoadMore({
  hasNext,
  truncated,
  fetching,
  onLoadMore,
  label = "載入更多",
  testId = "si-load-more",
}: {
  hasNext: boolean;
  truncated: boolean;
  fetching: boolean;
  onLoadMore: () => void;
  label?: string;
  testId?: string;
}) {
  if (hasNext) {
    return (
      <div className="mt-3">
        <Button variant="ghost" size="sm" data-testid={testId} disabled={fetching} onClick={onLoadMore}>
          {label}
        </Button>
      </div>
    );
  }
  if (truncated) {
    return (
      <p role="alert" data-testid="si-cursor-missing" className="mt-3 text-sm text-wg-accent">
        回應標示尚有更多資料，但沒有下一頁的游標（nextSince）：無法載入更多，目前顯示的不是全部。
      </p>
    );
  }
  return null;
}

/** 篩選只作用於已載入的頁（先分頁、後篩選）：truncated 時說明，避免把「已載入範圍內的結果」讀成全帳本。 */
export function SiScopeNote({ loaded }: { loaded: number }) {
  return (
    <p data-testid="si-filter-scope-note" className="mb-2 text-xs text-wg-muted">
      {`篩選只作用於已載入的 ${loaded} 筆，尚有更多未載入`}
    </p>
  );
}

export type SiOption = { value: string; label: string };

/** 「全部」＋各值（值取自已載入資料的相異值，不寫死列舉）。 */
export function withAll(values: ReadonlyArray<string>): SiOption[] {
  return [{ value: "", label: "全部" }, ...values.map((v) => ({ value: v, label: v }))];
}

/**
 * 原生 `<select>`（R17）：`aria-label` 即欄名，預設選項「全部」；可見標題是同一個字的裝飾，不重複朗讀。
 * 選項取自已載入的資料：重新整理後若目前選的值已不在資料裡，仍保留該值當選項——控制項要如實反映仍在生效的篩選，
 * 不能顯示成「全部」卻繼續篩（那會讓人把「沒有符合」讀成「帳本沒有這些資料」）。
 */
export function FilterSelect({
  label,
  value,
  options,
  onChange,
  disabled = false,
  testId,
}: {
  label: string;
  value: string;
  options: ReadonlyArray<SiOption>;
  onChange: (value: string) => void;
  disabled?: boolean;
  testId: string;
}) {
  const shown = options.some((o) => o.value === value) ? options : [...options, { value, label: value }];
  return (
    <div className="flex items-center gap-2 text-sm">
      <span aria-hidden className="text-wg-muted">
        {label}
      </span>
      <Select size="sm" aria-label={label} data-testid={testId} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
        {shown.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
    </div>
  );
}

/** 展開／收合鈕：名稱固定為 `展開 <名>`（狀態用 aria-expanded 表達，名稱不隨狀態改變）。 */
export function ExpandToggle({ name, expanded, controls, onToggle }: { name: string; expanded: boolean; controls: string; onToggle: () => void }) {
  return <IconButton icon={expanded ? ChevronDown : ChevronRight} label={`展開 ${name}`} size={28} iconSize={16} aria-expanded={expanded} aria-controls={controls} onClick={onToggle} />;
}

/**
 * 面板把「已載入筆數」回報給分頁列（標籤帶筆數，truncated 時加 `+`；R14）。面板卸載或不是 ok 態時回報 null——
 * 錯誤態與載入中的分頁標籤不帶筆數（不把量不到顯示成 0 筆）。
 */
export function useReportTabCount(report: (text: string | null) => void, text: string | null): void {
  useEffect(() => {
    report(text);
    return () => report(null);
  }, [report, text]);
}

/** 分頁標籤的筆數字樣：`(12)`；尚有未載入的頁時 `(5+)`。 */
export function countText(loaded: number, truncated: boolean): string {
  return `(${loaded}${truncated ? "+" : ""})`;
}

/**
 * 入帳指令（P2b；W17、W18）：PowerShell 與 POSIX 各一個 CopyCommand，兩段字串相同（`ingestCommands`）。Console 不執行它、也不替換任何佔位：
 * 入帳只有掌舵者在主機端（monorepo 根、已設 `AUTOSDD_SI_AUDIT_KEY` 的 shell）用根層 CLI 做——pull 模式，金鑰不出現在指令。
 * 頁面可同時有多組（對話框的收據與對帳面板的各待入帳列），CopyCommand 的 testid 沿用 `sdd-recovery-*`，測試以 `within(對話框或列)` 取。
 */
export function SiIngestCommands({ kind, subject, auditRef }: { kind: SiWriteKind; subject: string | null | undefined; auditRef: string }) {
  const commands = ingestCommands(kind, subject, auditRef);
  return (
    <div data-testid="si-ingest-commands" className="flex flex-col gap-3">
      <CopyCommand shell="powershell" label="PowerShell" command={commands.powershell} />
      <CopyCommand shell="posix" label="POSIX（bash／zsh）" command={commands.posix} />
    </div>
  );
}

/**
 * 寫入成功的收據（待入帳）：稽核編號、說明與入帳指令。對話框不自動關閉——掌舵者要先複製指令（關掉＝收據消失，只能到對帳面板再找）。
 * `testId` 是各對話框自己的結果容器（`si-decide-result`、`si-obs-result`、`si-close-result`）。
 */
export function SiWriteResult({ testId, receipt }: { testId: string; receipt: SiWriteReceipt }) {
  return (
    <div data-testid={testId} className="rounded-md border border-wg-line bg-wg-base px-4 py-3">
      <p className="font-semibold">稽核檔已落地，待入帳</p>
      <p className="mt-1 text-sm">
        {"稽核編號："}
        <code data-testid="si-audit-ref" className="font-mono break-all">
          {receipt.auditRef}
        </code>
      </p>
      <p className="mt-1 text-[13px] text-wg-muted">Console 不寫帳本：請在 monorepo 根、已設主機端 AUTOSDD_SI_AUDIT_KEY 的 shell 執行下列指令入帳（金鑰不出現在指令；入帳前這筆寫入尚未生效）。</p>
      <div className="mt-3">
        <SiIngestCommands kind={receipt.kind} subject={receipt.subject} auditRef={receipt.auditRef} />
      </div>
    </div>
  );
}
