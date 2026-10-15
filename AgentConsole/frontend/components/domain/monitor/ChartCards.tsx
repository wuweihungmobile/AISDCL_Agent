"use client";

import { useMemo } from "react";

import { ColumnChart, RatioChart, StatusBars } from "@/components/charts/SimpleCharts";
import { TokenTrendChart } from "@/components/charts/TokenTrendChart";
import { AreaChart } from "@/components/charts/tremor/AreaChart";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import type { ProjectMetrics, TaskTrendPoint, TokenTrendPoint, TrendBucket } from "@/lib/api/types";
import { durationColumns, formatDuration, groupTaskStatus, ratioRows, retryColumns, taskTrendRows, tokenTrendRows } from "@/lib/domain/metrics";

/** 「Token 使用趨勢」卡（設計稿畫面 8）：折線（累計）＋虛線預算線＋面積；圖例「預算線／Token 使用」靜態。 */
export function TokenTrendCard({
  points,
  bucket,
  loading,
  error,
  onRetry,
}: {
  points: readonly TokenTrendPoint[] | undefined;
  bucket: TrendBucket;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  const rows = useMemo(() => tokenTrendRows(points ?? [], bucket), [points, bucket]);
  return (
    <Card className="px-[22px] py-5" data-testid="token-trend-card">
      <div className="mb-3 flex items-center justify-between gap-3">
        <CardTitle>Token 使用趨勢</CardTitle>
        <div className="flex items-center gap-4 text-xs text-wg-muted" aria-hidden>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-0 w-5 border-t-2 border-dashed border-wg-line" />
            預算線
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-5 bg-wg-primary" />
            Token 使用
          </span>
        </div>
      </div>
      {error && !points ? (
        <ErrorState error={error} onRetry={onRetry} title="無法載入 Token 趨勢" />
      ) : loading && !points ? (
        <Skeleton className="h-[200px]" />
      ) : rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-wg-muted" data-testid="token-trend-empty">
          這段時間沒有 Token 使用紀錄
        </p>
      ) : (
        <TokenTrendChart rows={rows} />
      )}
    </Card>
  );
}

/** 兩欄：「任務狀態分佈」（水平 bar）與「執行時間分佈」（垂直柱）。 */
export function DistributionCards({ metrics, loading, error, onRetry }: { metrics: ProjectMetrics | undefined; loading: boolean; error: unknown; onRetry: () => void }) {
  return (
    <div className="grid grid-cols-2 gap-6 max-lg:grid-cols-1" data-testid="distribution-cards">
      <Card className="px-[22px] py-5" data-testid="status-distribution-card">
        <CardTitle className="mb-4">任務狀態分佈</CardTitle>
        {error && !metrics ? (
          <ErrorState error={error} onRetry={onRetry} />
        ) : loading && !metrics ? (
          <Skeleton className="h-[120px]" />
        ) : (
          <StatusBars rows={groupTaskStatus(metrics?.taskStatusDistribution ?? {})} />
        )}
      </Card>
      <Card className="px-[22px] py-5" data-testid="duration-card">
        <CardTitle className="mb-4">執行時間分佈</CardTitle>
        {error && !metrics ? (
          <ErrorState error={error} onRetry={onRetry} />
        ) : loading && !metrics ? (
          <Skeleton className="h-[140px]" />
        ) : (
          <ColumnChart columns={durationColumns(metrics?.taskDurations ?? [])} formatValue={formatDuration} ariaLabel="執行時間分佈圖" testId="duration-chart" empty="這段時間沒有完成的任務" />
        )}
      </Card>
    </div>
  );
}

/**
 * PRD §5.4.2 的趨勢圖（設計稿沒畫；契約 §4.3 M-11、§4.6 G-M2）：任務執行趨勢（堆疊面積）、成功／失敗比率（堆疊柱）、重試次數分佈（柱）。
 * 資料：GET task-trend 的每桶 completed／failed／retried，以及 metrics.retryDistribution。
 */
export function TrendCards({
  taskTrend,
  metrics,
  bucket,
  loading,
  error,
  onRetry,
}: {
  taskTrend: readonly TaskTrendPoint[] | undefined;
  metrics: ProjectMetrics | undefined;
  bucket: TrendBucket;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  const rows = useMemo(() => taskTrendRows(taskTrend ?? [], bucket), [taskTrend, bucket]);
  const ratios = useMemo(() => ratioRows(taskTrend ?? [], bucket), [taskTrend, bucket]);
  const summary = rows.map((r) => `${r.time} 完成 ${r.完成}、失敗 ${r.失敗}、重試 ${r.重試}`).join("；");
  return (
    <div className="grid grid-cols-3 gap-6 max-xl:grid-cols-1" data-testid="trend-cards">
      <Card className="min-w-0 px-[22px] py-5" data-testid="task-trend-card">
        <CardTitle className="mb-3">任務執行趨勢</CardTitle>
        {error && !taskTrend ? (
          <ErrorState error={error} onRetry={onRetry} />
        ) : loading && !taskTrend ? (
          <Skeleton className="h-[160px]" />
        ) : rows.length === 0 ? (
          <p className="py-8 text-center text-sm text-wg-muted">這段時間沒有任務事件</p>
        ) : (
          <div role="img" aria-label={`任務執行趨勢圖：${summary}`} data-testid="task-trend-chart">
            <AreaChart
              className="h-[160px]"
              data={rows}
              index="time"
              categories={["完成", "失敗", "重試"]}
              colors={["primary", "error", "warning"]}
              type="stacked"
              fill="solid"
              allowDecimals={false}
              yAxisWidth={32}
              showLegend
              legendPosition="center"
            />
          </div>
        )}
      </Card>
      <Card className="min-w-0 px-[22px] py-5" data-testid="ratio-card">
        <CardTitle className="mb-3">成功／失敗比率</CardTitle>
        {error && !taskTrend ? <ErrorState error={error} onRetry={onRetry} /> : loading && !taskTrend ? <Skeleton className="h-[160px]" /> : <RatioChart rows={ratios} />}
      </Card>
      <Card className="min-w-0 px-[22px] py-5" data-testid="retry-card">
        <CardTitle className="mb-3">重試次數分佈</CardTitle>
        <ColumnChart columns={retryColumns(metrics?.retryDistribution ?? [])} formatValue={(v) => `${v}`} ariaLabel="重試次數分佈圖" testId="retry-chart" empty="這段時間沒有任務資料" />
      </Card>
    </div>
  );
}
