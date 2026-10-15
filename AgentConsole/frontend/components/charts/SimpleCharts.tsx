import type { Column, StatusGroupId } from "@/lib/domain/metrics";
import { cn } from "@/lib/utils";

/**
 * 設計稿畫面 8 的兩張小圖不是折線圖：「任務狀態分佈」是水平 bar、「執行時間分佈」是垂直柱——
 * 用純 HTML／CSS 畫（顏色一律走 token 類別），比拉進圖表庫輕，jsdom 也能直接測。
 * 每張圖都以 role="img" 提供文字替代說明並附螢幕閱讀器清單（UI-A11Y-04）。
 */

const GROUP_BAR: Record<StatusGroupId, string> = {
  done: "bg-wg-primary",
  running: "bg-wg-secondary",
  failed: "bg-wg-error",
  pending: "bg-wg-disabled-text",
};

/** 任務狀態分佈：完成／執行中／失敗／待處理 四條水平 bar（寬度以最大值為 100%）。 */
export function StatusBars({ rows }: { rows: ReadonlyArray<{ id: StatusGroupId; label: string; count: number }> }) {
  const max = Math.max(0, ...rows.map((r) => r.count));
  const summary = rows.map((r) => `${r.label} ${r.count}`).join("、");
  return (
    <div role="img" aria-label={`任務狀態分佈：${summary}`} data-testid="status-bars" className="flex flex-col gap-3">
      {rows.map((r) => (
        <div key={r.id} className="grid grid-cols-[64px_1fr_36px] items-center gap-3 text-[13px]" data-testid={`status-bar-${r.id}`}>
          <span className="text-wg-muted">
            {r.label} ({r.count})
          </span>
          <span className="h-2 overflow-hidden rounded-full bg-wg-base">
            <span className={cn("block h-full rounded-full transition-[width] duration-[400ms]", GROUP_BAR[r.id])} style={{ width: max > 0 ? `${(r.count / max) * 100}%` : "0%" }} />
          </span>
          <span className="text-right font-mono text-xs text-wg-muted">{r.count}</span>
        </div>
      ))}
      <ul className="sr-only">
        {rows.map((r) => (
          <li key={r.id}>
            {r.label}：{r.count} 個任務
          </li>
        ))}
      </ul>
    </div>
  );
}

/** 垂直柱（執行時間分佈、重試次數分佈）：最高的用主色，其餘 secondary（設計稿）。 */
export function ColumnChart({
  columns,
  formatValue,
  ariaLabel,
  testId,
  empty = "沒有資料",
}: {
  columns: readonly Column[];
  formatValue: (value: number) => string;
  ariaLabel: string;
  testId: string;
  empty?: string;
}) {
  if (columns.length === 0) return <p className="py-6 text-center text-sm text-wg-muted">{empty}</p>;
  const summary = columns.map((c) => `${c.label} ${formatValue(c.value)}`).join("、");
  return (
    <div role="img" aria-label={`${ariaLabel}：${summary}`} data-testid={testId} className="flex items-end gap-3">
      {columns.map((c, i) => (
        // 標籤可能重複（兩個任務同名、或範圍剛切換時的舊資料）：key 帶上順序
        <div key={`${i}:${c.label}`} className="flex min-w-0 flex-1 flex-col items-center gap-1" data-testid={`${testId}-col`}>
          <span className="text-xs text-wg-muted">{formatValue(c.value)}</span>
          <span className="flex h-[110px] w-full items-end justify-center">
            <span
              className={cn("block w-full max-w-[44px] rounded-sm transition-[height] duration-[400ms]", c.highlight ? "bg-wg-primary" : "bg-wg-secondary")}
              style={{ height: `${c.heightPct}%` }}
              data-highlight={c.highlight}
            />
          </span>
          <span className="max-w-full truncate text-[11px] text-wg-muted" title={c.label}>
            {c.label}
          </span>
        </div>
      ))}
      <ul className="sr-only">
        {columns.map((c, i) => (
          <li key={`${i}:${c.label}`}>
            {c.label}：{formatValue(c.value)}
          </li>
        ))}
      </ul>
    </div>
  );
}

export type RatioColumn = { label: string; success: number; failure: number; total: number };

/** 成功／失敗比率（UI-CHT-03）：每個時間桶一根堆疊柱，成功＝主色、失敗＝error，高度為 100%。 */
export function RatioChart({ rows }: { rows: readonly RatioColumn[] }) {
  if (rows.length === 0) return <p className="py-6 text-center text-sm text-wg-muted">這段時間沒有完成或失敗的任務</p>;
  const summary = rows.map((r) => `${r.label} 成功 ${r.success}% 失敗 ${r.failure}%`).join("；");
  return (
    <div role="img" aria-label={`成功失敗比率：${summary}`} data-testid="ratio-chart" className="flex items-end gap-2">
      {rows.map((r, i) => (
        <div key={`${i}:${r.label}`} className="flex min-w-0 flex-1 flex-col items-center gap-1" data-testid="ratio-col" title={`${r.label}：成功 ${r.success}%／失敗 ${r.failure}%（共 ${r.total}）`}>
          <span className="flex h-[110px] w-full max-w-[36px] flex-col-reverse overflow-hidden rounded-sm bg-wg-base">
            <span className="block w-full bg-wg-primary" style={{ height: `${r.success}%` }} />
            <span className="block w-full bg-wg-error" style={{ height: `${r.failure}%` }} />
          </span>
          <span className="max-w-full truncate text-[11px] text-wg-muted">{r.label}</span>
        </div>
      ))}
      <ul className="sr-only">
        {rows.map((r, i) => (
          <li key={`${i}:${r.label}`}>
            {r.label}：成功 {r.success}%、失敗 {r.failure}%（共 {r.total} 個任務）
          </li>
        ))}
      </ul>
    </div>
  );
}
