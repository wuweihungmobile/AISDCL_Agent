"use client";

import { Card, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { StatusLabel } from "@/components/ui/status-dot";
import type { ExecutionRunDetail } from "@/lib/api/types";
import { isLive, isRunTerminal, runStatusMeta } from "@/lib/domain/status";
import { formatElapsed, formatNumber } from "@/lib/format";
import { EngineCapabilityChips } from "./parts";

/** Token 進度條的顏色（契約 §4.2 E-11、設計稿「Token 條超閾值變色」）：到警告閾值＝warning、超過預算＝error。 */
export function tokenTone(used: number, budget: number | null | undefined, warnThreshold: number): "normal" | "warn" | "over" {
  if (!budget || budget <= 0) return "normal";
  if (used > budget) return "over";
  return used >= budget * warnThreshold ? "warn" : "normal";
}

const TONE_BAR = { normal: undefined, warn: "bg-wg-warning", over: "bg-wg-error" } as const;

/**
 * 「執行進度」卡（設計稿畫面 7 右上）：Run #n、狀態（RUNNING 帶 wg-blink 閃點）、任務進度條（completedSteps／totalSteps）、
 * Token 進度條（totalTokensUsed／tokenBudget；≥ 警告閾值變 warning、超限變 error）、耗時。
 * 標題列下方是引擎能力晶片（自動突變、自演化；契約 E-21，v1.3；批次建立時凍結的值，缺席時整列不顯示）。
 * 資料全部來自批次詳情快取（REST 當底、SSE 即時修補），這裡只讀、不訂閱。
 */
export function ProgressCard({
  run,
  now,
  warnThreshold,
}: {
  run: ExecutionRunDetail | undefined;
  /** 進行中的批次耗時每秒跳動：由上層的 useNow 提供 */
  now: number;
  warnThreshold: number;
}) {
  if (!run) {
    return (
      <Card className="px-[22px] py-5" data-testid="progress-card">
        <CardTitle className="mb-2">執行進度</CardTitle>
        <p className="text-sm text-wg-muted">尚未啟動執行。設定左側的範圍與預算後按「啟動執行」。</p>
      </Card>
    );
  }
  const meta = runStatusMeta(run.status, run.bridgeStatus);
  const total = run.totalSteps;
  const done = run.completedSteps;
  const taskPct = total > 0 ? (done / total) * 100 : 0;
  const used = run.totalTokensUsed;
  const budget = run.tokenBudget ?? null;
  const tokenPct = budget && budget > 0 ? (used / budget) * 100 : 0;
  const tone = tokenTone(used, budget, warnThreshold);
  // 進行中（含暫停）：現在－開始時間每秒跳動；終態：伺服器給的 elapsedSec
  const ticking = !isRunTerminal(run.status);
  const elapsed = ticking ? Math.max(run.elapsedSec ?? 0, Math.floor((now - Date.parse(run.startedAt)) / 1000)) : run.elapsedSec;
  const step = run.currentStep;

  return (
    <Card className="px-[22px] py-5" data-testid="progress-card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <CardTitle>執行進度</CardTitle>
        <div className="flex items-center gap-3 text-sm text-wg-muted">
          <span data-testid="run-number">Run #{run.runNumber}</span>
          <span data-testid="run-status" data-status={run.status}>
            <StatusLabel meta={meta} live={isLive(run.status)} className="text-sm" />
          </span>
        </div>
      </div>

      <EngineCapabilityChips capabilities={run.engineCapabilities} className="mb-3" />

      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span data-testid="progress-tasks">
          {done} / {total} 任務完成
        </span>
        <span className="text-wg-muted">{taskPct.toFixed(1)}%</span>
      </div>
      <Progress value={taskPct} label="任務完成進度" />

      <div className="mt-4 mb-1 flex items-baseline justify-between text-sm">
        <span data-testid="progress-tokens" className="font-mono">
          Token: {formatNumber(used)} / {budget ? formatNumber(budget) : "不限"}
        </span>
        <span className="text-wg-muted" data-testid="progress-token-pct">
          {budget ? `${tokenPct.toFixed(1)}%` : "—"}
        </span>
      </div>
      <Progress value={tokenPct} label="Token 使用進度" barClassName={TONE_BAR[tone]} />
      {tone !== "normal" ? (
        <p data-testid="token-warning" className={tone === "over" ? "mt-1 text-xs text-wg-error" : "mt-1 text-xs text-wg-muted"}>
          {tone === "over" ? "Token 已超出預算" : `Token 使用量已達預算的 ${Math.round(warnThreshold * 100)}%`}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-wg-muted">
        <span data-testid="progress-elapsed">耗時：{formatElapsed(elapsed)}</span>
        {step ? (
          <span data-testid="progress-current" className="min-w-0 truncate">
            目前：{step.taskName}（{step.stepId}
            {step.attempt > 1 ? `，第 ${step.attempt} 次` : ""}）
          </span>
        ) : null}
      </div>
      {run.reason && (run.status === "FAILED" || run.status === "PAUSED" || run.status === "CANCELLED") ? (
        <p data-testid="run-reason" className="mt-2 text-[13px] text-wg-muted">
          {run.reason}
        </p>
      ) : null}
      {run.bridge && !run.bridge.connected ? (
        <p role="status" data-testid="bridge-down" className="mt-2 rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-1.5 text-[13px]">
          Engine Bridge 目前無法連線：進度為資料庫的衍生值，恢復連線後會自動更新。
        </p>
      ) : null}
    </Card>
  );
}
