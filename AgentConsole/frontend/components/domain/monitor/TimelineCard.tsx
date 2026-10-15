"use client";

import { useMemo } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { useExecutionSteps } from "@/lib/api/queries";
import { timelineItems, type TimelineTone } from "@/lib/domain/metrics";
import { cn } from "@/lib/utils";

const DOT: Record<TimelineTone, string> = {
  start: "bg-wg-secondary",
  done: "bg-wg-primary",
  failed: "bg-wg-error",
  retry: "bg-wg-warning",
};

const LEGEND: ReadonlyArray<{ tone: TimelineTone; label: string }> = [
  { tone: "start", label: "開始" },
  { tone: "done", label: "完成" },
  { tone: "failed", label: "失敗" },
  { tone: "retry", label: "重試" },
];

/**
 * 「事件時間軸」卡（PRD §5.4.5、契約 §4.3 M-12；設計稿沒畫，補上）：一個批次的步驟事件（開始／完成／失敗／重試）水平排列。
 * 來源＝GET /executions/{runId}/steps（task-trend 沒有 events[]，主控裁決）；選「全部批次」時取最新一筆批次。
 */
export function TimelineCard({ runId, pollMs, runLabel }: { runId: string | undefined; pollMs: number | false; runLabel?: string }) {
  const q = useExecutionSteps(runId, pollMs);
  const items = useMemo(() => timelineItems(q.data ?? []), [q.data]);
  return (
    <Card className="px-[22px] py-5" data-testid="timeline-card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <CardTitle>事件時間軸</CardTitle>
        <div className="flex items-center gap-3 text-xs text-wg-muted" aria-hidden>
          {runLabel ? <span data-testid="timeline-run">{runLabel}</span> : null}
          {LEGEND.map((l) => (
            <span key={l.tone} className="inline-flex items-center gap-1.5">
              <span className={cn("inline-block size-2.5 rounded-full", DOT[l.tone])} />
              {l.label}
            </span>
          ))}
        </div>
      </div>
      {!runId ? (
        <p className="py-6 text-center text-sm text-wg-muted" data-testid="timeline-empty">
          尚無執行批次
        </p>
      ) : q.isError && !q.data ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} title="無法載入步驟事件" />
      ) : q.isPending ? (
        <Skeleton className="h-16" />
      ) : items.length === 0 ? (
        <p className="py-6 text-center text-sm text-wg-muted" data-testid="timeline-empty">
          這個批次還沒有步驟事件
        </p>
      ) : (
        <div className="overflow-x-auto pb-2" data-testid="timeline-scroll">
          <ol className="relative flex w-max min-w-full items-start gap-0 pt-1" aria-label="事件時間軸">
            {/* 軸線：貫穿所有節點的中心 */}
            <span aria-hidden className="absolute top-[9px] right-4 left-4 h-0.5 bg-wg-line" />
            {items.map((it) => (
              <li key={it.id} className="relative flex w-[88px] shrink-0 flex-col items-center gap-1.5 text-center" data-testid="timeline-item" data-tone={it.tone} title={it.title}>
                <span className={cn("relative z-10 inline-block size-3 rounded-full border-2 border-wg-surface", DOT[it.tone])} />
                <span className="text-xs font-medium">{it.label}</span>
                <span className="font-mono text-[11px] text-wg-muted">{it.time}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </Card>
  );
}
