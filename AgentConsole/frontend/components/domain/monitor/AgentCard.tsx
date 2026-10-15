"use client";

import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusDot } from "@/components/ui/status-dot";
import { useExecution } from "@/lib/api/queries";
import type { MetricValue } from "@/lib/api/types";
import { formatMetricValue } from "@/lib/domain/metrics";
import { isRunTerminal, runStatusMeta } from "@/lib/domain/status";

/**
 * 「Agent 即時狀態」卡（PRD US-M-10；契約 §4.3 M-19）：連線狀態指示燈（Engine Bridge 是否可達）、目前任務、可用率。
 * 資料：GET /executions/{runId}（bridge.connected／instance／status、currentStep；Bridge 不可達時仍回 200）＋ metrics.agentAvailability。
 * 「資源使用情況（CPU／記憶體）」Bridge 沒有此資料（ADR-001 G-18），不編造；RTM 判定 🟡。
 */
export function AgentCard({ runId, availability }: { runId: string | undefined; availability: MetricValue | undefined }) {
  const q = useExecution(runId);
  const run = q.data;
  const connected = run?.bridge.connected;
  const running = run ? !isRunTerminal(run.status) : false;

  let light: { color: string; label: string };
  if (!runId) light = { color: "var(--color-disabled-text)", label: "尚無執行批次" };
  else if (!run) light = { color: "var(--color-disabled-text)", label: q.isError ? "無法取得狀態" : "查詢中" };
  else if (connected === false) light = { color: "var(--color-error)", label: "Engine Bridge 未連線" };
  else if (running) light = { color: "var(--color-primary)", label: "已連線，執行中" };
  else light = { color: "var(--color-secondary)", label: "已連線，閒置" };

  return (
    <Card className="px-[22px] py-5" data-testid="agent-card">
      <CardTitle className="mb-3.5">Agent 即時狀態</CardTitle>
      {runId && !run && !q.isError ? (
        <Skeleton className="h-12" />
      ) : (
        <div className="grid grid-cols-4 gap-x-6 gap-y-3 max-lg:grid-cols-2">
          <div>
            <div className="text-xs text-wg-muted">連線狀態</div>
            <div className="mt-1 flex items-center gap-2 text-[15px] font-medium" data-testid="agent-light" data-connected={connected === undefined ? "unknown" : String(connected)}>
              <StatusDot color={light.color} size={10} live={running && connected !== false} />
              {light.label}
            </div>
          </div>
          <div>
            <div className="text-xs text-wg-muted">批次狀態</div>
            <div className="mt-1 text-[15px]" data-testid="agent-run-status">
              {run ? `Run #${run.runNumber} · ${runStatusMeta(run.status, run.bridgeStatus).label}` : "—"}
            </div>
          </div>
          <div>
            <div className="text-xs text-wg-muted">目前任務</div>
            <div className="mt-1 truncate text-[15px]" data-testid="agent-current" title={run?.currentStep?.taskName}>
              {run?.currentStep ? `${run.currentStep.taskName}（${run.currentStep.stepId}）` : "—"}
            </div>
          </div>
          <div>
            <div className="text-xs text-wg-muted">Agent 可用率</div>
            <div className="mt-1 text-[15px] font-medium" data-testid="agent-availability">
              {formatMetricValue("percent", availability?.value)}
            </div>
          </div>
        </div>
      )}
      <p className="mt-3 text-xs text-wg-muted" data-testid="agent-note">
        {run?.bridge.instance ? `Bridge 實例：${run.bridge.instance}。` : ""}
        資源使用情況（CPU／記憶體）：Engine Bridge 目前沒有提供這項資料，改以連線、目前任務與 Token 呈現。
      </p>
    </Card>
  );
}
