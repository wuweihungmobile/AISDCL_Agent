"use client";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import type { MetricValue, ProjectMetrics } from "@/lib/api/types";
import { PRIMARY_KPIS, SECONDARY_KPIS, deltaTone, formatDelta, formatMetricValue, type DeltaTone, type KpiDef } from "@/lib/domain/metrics";
import { cn } from "@/lib/utils";

const TONE_CLASS: Record<DeltaTone, string> = {
  good: "text-wg-primary",
  bad: "text-wg-error",
  warn: "text-wg-accent",
  flat: "text-wg-muted",
};

const EMPTY: MetricValue = { value: null };

function KpiCard({ def, metric }: { def: KpiDef; metric: MetricValue | undefined }) {
  const m = metric ?? EMPTY;
  const delta = formatDelta(def.kind, m.delta);
  return (
    <Card className="p-5" data-testid={`kpi-${def.key}`}>
      <div className="text-sm text-wg-muted">{def.label}</div>
      <div className="mt-2 text-[30px] leading-none font-bold" data-testid={`kpi-${def.key}-value`}>
        {formatMetricValue(def.kind, m.value)}
      </div>
      {/* 契約：沒有比較值（delta 為 null）就不顯示這一行，不編造 */}
      {delta ? (
        <div className={cn("mt-2 text-[13px]", TONE_CLASS[deltaTone(def.better, m.delta)])} data-testid={`kpi-${def.key}-delta`}>
          {delta}
        </div>
      ) : null}
    </Card>
  );
}

/**
 * 指標卡（設計稿畫面 8：完成率／任務成功率／重試率／Token 消耗，數值 30px／700）＋PRD §5.4.2 另外六項（較小的指標列）。
 * delta 取契約給的前一視窗比較值（delta＝value−previousValue；百分比為百分點）；顏色依語意：成功率升＝好、重試率升＝壞。
 */
export function KpiCards({ metrics, loading, error, onRetry }: { metrics: ProjectMetrics | undefined; loading: boolean; error: unknown; onRetry: () => void }) {
  if (error && !metrics) return <ErrorState error={error} onRetry={onRetry} title="無法載入指標" />;
  if (loading && !metrics) {
    return (
      <div className="grid grid-cols-4 gap-6 max-xl:grid-cols-2 max-md:grid-cols-1">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-[112px] rounded-lg" />
        ))}
      </div>
    );
  }
  return (
    <div data-testid="kpi-cards">
      <div className="grid grid-cols-4 gap-6 max-xl:grid-cols-2 max-md:grid-cols-1">
        {PRIMARY_KPIS.map((def) => (
          <KpiCard key={def.key} def={def} metric={metrics?.[def.key]} />
        ))}
      </div>
      <Card className="mt-4 px-5 py-4" data-testid="kpi-secondary">
        <div className="grid grid-cols-6 gap-x-6 gap-y-3 max-xl:grid-cols-3 max-md:grid-cols-2">
          {SECONDARY_KPIS.map((def) => {
            const m = metrics?.[def.key] ?? EMPTY;
            const delta = formatDelta(def.kind, m.delta);
            return (
              <div key={def.key} data-testid={`kpi-${def.key}`}>
                <div className="text-xs text-wg-muted">{def.label}</div>
                <div className="mt-0.5 text-lg font-semibold" data-testid={`kpi-${def.key}-value`}>
                  {formatMetricValue(def.kind, m.value)}
                </div>
                {delta ? <div className={cn("text-xs", TONE_CLASS[deltaTone(def.better, m.delta)])}>{delta}</div> : null}
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
