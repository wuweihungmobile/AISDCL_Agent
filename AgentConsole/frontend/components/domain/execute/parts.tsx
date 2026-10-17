"use client";

import { AlertTriangle, Info, Lock, RefreshCw, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import type { StreamState } from "@/lib/api/sse";
import type { EngineCapabilities, ExecutionRunSummary } from "@/lib/api/types";
import type { ExecutionWarningView } from "@/lib/domain/executionWarnings";
import { ENGINE_CAPABILITY_KEYS, engineCapabilityView, runStatusMeta, type EngineCapabilityTone } from "@/lib/domain/status";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { StartErrorView } from "./startErrors";

/**
 * 執行鎖定橫幅（設計稿畫面 7 `execSignoffBlocked`）：lock 圖示＋「執行已鎖定 — 草案未 signoff，啟動回 409 Conflict」＋「前往審批」。
 * 專案本身未 signoff 才顯示；目標／任務層級的未審批由控制卡內的提示列說明。
 */
export function LockBanner({ onApprove, canApprove }: { onApprove: () => void; canApprove: boolean }) {
  return (
    <div role="status" data-testid="execute-lock-banner" className="mb-5 flex items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-[18px] py-3.5 max-md:flex-wrap">
      <Lock size={22} className="shrink-0 text-wg-accent" aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="font-semibold text-wg-accent">執行已鎖定 — 草案未 signoff，啟動回 409 Conflict</div>
        <div className="text-[13px] text-wg-muted">此專案 signed_off=false，未經掌舵者審批前禁止執行（後端會二次校驗，前端停用只是體驗）。</div>
      </div>
      <Button iconLeft={ShieldCheck} onClick={onApprove} disabled={!canApprove} title={canApprove ? undefined : "權限不足（唯讀角色不可審批）"}>
        前往審批
      </Button>
    </div>
  );
}

const SSE_LABEL: Record<StreamState, string> = {
  idle: "未連線",
  connecting: "連線中",
  open: "已連線",
  reconnecting: "重新連線中",
  ended: "已結束",
  failed: "連線失敗",
};

const SSE_DOT: Record<StreamState, string> = {
  idle: "bg-wg-disabled-text",
  connecting: "bg-wg-warning animate-wg-blink",
  open: "bg-wg-primary",
  reconnecting: "bg-wg-warning animate-wg-blink",
  ended: "bg-wg-disabled-text",
  failed: "bg-wg-error",
};

/** 「SSE 串流」狀態點＝客戶端連線狀態（契約 §2.8 第 6 點，不是伺服器欄位）；重試用盡時附「重新連線」。 */
export function SseDot({ state, onReconnect, className }: { state: StreamState; onReconnect?: () => void; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs text-wg-muted", className)} data-testid="sse-status" data-state={state}>
      <span aria-hidden className={cn("inline-block size-2 shrink-0 rounded-full", SSE_DOT[state])} />
      SSE 串流 · {SSE_LABEL[state]}
      {state === "failed" && onReconnect ? (
        <button
          type="button"
          onClick={onReconnect}
          className="inline-flex cursor-pointer items-center gap-1 rounded-sm border-none bg-transparent p-0 text-wg-primary transition-opacity hover:opacity-85"
        >
          <RefreshCw size={12} aria-hidden />
          重新連線
        </button>
      ) : null}
    </span>
  );
}

/** 啟動失敗的說明（409／400／422／502 的 reason 與 details 轉成人話；契約附錄 B.2「執行」列）。 */
export function StartErrorPanel({ view, onApprove }: { view: StartErrorView; onApprove?: () => void }) {
  return (
    <div role="alert" data-testid="start-error" className="mt-4 flex items-start gap-2.5 rounded-md border border-wg-draft-border bg-wg-draft-bg px-3.5 py-3 text-sm">
      <AlertTriangle size={18} className="mt-0.5 shrink-0 text-wg-accent" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-wg-accent">啟動失敗：{view.title}</p>
        {view.lines.map((line) => (
          <p key={line} className="mt-0.5 text-wg-text">
            {line}
          </p>
        ))}
        {view.traceId ? <p className="mt-1 font-mono text-xs text-wg-muted">traceId：{view.traceId}</p> : null}
        {view.unsigned && onApprove ? (
          <Button variant="ghost" size="sm" className="mt-2" onClick={onApprove}>
            前往審批
          </Button>
        ) : null}
      </div>
    </div>
  );
}

/**
 * 啟動成功（201）帶回的警告（契約 §1.10.6、§1.2.1 的 v1.5 加註；整合輪 115，API-EXE-15）：批次已啟動，警告不阻擋，但要讓人看見——
 * 例如「本批次沒有啟用 SDD 治理」（沒有預檢、沒有 FSM 同步、事後也不會有追溯報告；附 cause 與後端的 detail）。
 * 只有 execute 的 201 帶 warnings，所以這個清單只在剛啟動的那個批次上顯示（切到別的批次就不顯示）。
 */
export function ExecutionWarningsPanel({ warnings }: { warnings: readonly ExecutionWarningView[] }) {
  if (warnings.length === 0) return null;
  return (
    <div role="status" data-testid="execution-warnings" className="mt-4 rounded-md border border-wg-alert-border bg-wg-alert-bg px-3.5 py-3 text-sm">
      <div className="flex items-center gap-2 font-semibold">
        <Info size={18} className="shrink-0 text-wg-warning" aria-hidden />
        啟動警告（共 {warnings.length} 項；批次已啟動，不阻擋）
      </div>
      <ul className="mt-2 flex flex-col gap-2">
        {warnings.map((w) => (
          <li key={w.key} data-testid="execution-warning" data-code={w.code} className="min-w-0">
            <p className="font-medium break-words">{w.title}</p>
            {w.cause ? (
              <p data-testid="execution-warning-cause" className="mt-0.5 text-wg-muted">
                原因：{w.cause}
              </p>
            ) : null}
            {w.detail ? (
              <p data-testid="execution-warning-detail" className="mt-0.5 break-words text-wg-muted">
                {w.detail}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** 批次列表項是否處於 Bridge 過渡態（RUNNING＋PAUSING／CANCELLING；契約 §1.2.2 的 bridgeStatus，C-11）。 */
export function isBridgeTransition(run: Pick<ExecutionRunSummary, "status" | "bridgeStatus">): boolean {
  return run.status === "RUNNING" && (run.bridgeStatus === "PAUSING" || run.bridgeStatus === "CANCELLING");
}

/**
 * Bridge 過渡態晶片（契約 §1.2.2，C-11）：批次列表項帶 bridgeStatus，RUNNING＋PAUSING／CANCELLING 時顯示「暫停中」「取消中」，
 * 讓使用者在批次下拉與批次比較看得到「正在處理中」；其餘狀態不顯示。
 */
export function BridgeChip({ run, className }: { run: Pick<ExecutionRunSummary, "status" | "bridgeStatus">; className?: string }): ReactNode {
  if (!isBridgeTransition(run)) return null;
  return (
    <span
      data-testid="bridge-chip"
      data-bridge={run.bridgeStatus ?? undefined}
      className={cn("inline-flex shrink-0 items-center rounded-sm border border-wg-alert-border bg-wg-alert-bg px-[7px] py-0.5 text-xs font-semibold text-wg-text", className)}
    >
      {runStatusMeta(run.status, run.bridgeStatus).label}
    </span>
  );
}

/** 三態的晶片色：已啟用＝主色邊＋tertiary 底（同 DAG 進行中節點）；關閉＝灰；無金鑰不可用＝告警底（同 BridgeChip，字用 text 色以過 WCAG AA）。 */
const CAPABILITY_TONE_CLASS: Record<EngineCapabilityTone, string> = {
  on: "border-wg-primary bg-wg-tertiary text-wg-text",
  off: "border-wg-line bg-wg-base text-wg-muted",
  unavailable: "border-wg-alert-border bg-wg-alert-bg text-wg-text",
};

/**
 * 引擎能力晶片「自動突變」「自演化」（契約 §4.2 E-21，v1.3 D-11；設計稿沒畫）：每枚三態＝已啟用／關閉／無金鑰不可用，
 * 值取自 `ExecutionRunResponse.engineCapabilities`（批次建立時凍結，切換批次後取該批次的值）。
 * 欄位缺席或為 null（V10 之前的批次）整列不顯示——不猜測；文字、色調、tooltip 由 lib/domain/status.ts 的字典決定。
 * 🔴 自演化的「已啟用」晶片文字帶「（僅提案）」、tooltip 說明不自動套用，不能讓人誤以為引擎會自己改自己。
 */
export function EngineCapabilityChips({ capabilities, className }: { capabilities: EngineCapabilities | null | undefined; className?: string }): ReactNode {
  if (!capabilities) return null;
  const chips = ENGINE_CAPABILITY_KEYS.flatMap((key) => {
    const state = capabilities[key];
    return state ? [{ key, state, view: engineCapabilityView(key, state) }] : [];
  });
  if (chips.length === 0) return null;
  return (
    <div role="group" aria-label="引擎能力" data-testid="engine-capabilities" className={cn("flex flex-wrap items-center gap-2", className)}>
      {chips.map(({ key, state, view }) => (
        <span
          key={key}
          data-testid="engine-capability"
          data-capability={key}
          data-state={state}
          title={view.hint || undefined}
          className={cn("inline-flex items-center rounded-sm border px-[7px] py-0.5 text-xs font-semibold", CAPABILITY_TONE_CLASS[view.tone])}
        >
          {view.text}
        </span>
      ))}
    </div>
  );
}

/** 執行批次下拉（預設最新；「Run #3 · 執行中 · 2026-10-15 14:32」）；過渡態批次的狀態字樣是「暫停中」「取消中」，選中時另附晶片。 */
export function RunSelect({
  runs,
  value,
  onChange,
  label = "執行批次",
  allOption,
  className,
}: {
  runs: readonly ExecutionRunSummary[];
  value: string;
  onChange: (runId: string) => void;
  label?: string;
  /** 監控頁多一個「全部批次」選項（value 為空字串） */
  allOption?: string;
  className?: string;
}): ReactNode {
  const selected = runs.find((r) => r.id === value);
  return (
    <label className={cn("inline-flex items-center gap-2 text-sm text-wg-muted", className)}>
      {label}
      <Select size="sm" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label} data-testid="run-select" disabled={runs.length === 0 && !allOption}>
        {allOption ? <option value="">{allOption}</option> : null}
        {runs.length === 0 && !allOption ? <option value="">尚無執行批次</option> : null}
        {runs.map((r, i) => (
          <option key={r.id} value={r.id}>
            Run #{r.runNumber}
            {i === 0 ? "（最新）" : ""} · {runStatusMeta(r.status, r.bridgeStatus).label} · {formatDateTime(r.startedAt)}
          </option>
        ))}
      </Select>
      {selected ? <BridgeChip run={selected} /> : null}
    </label>
  );
}
