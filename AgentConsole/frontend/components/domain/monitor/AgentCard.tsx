"use client";

import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusDot } from "@/components/ui/status-dot";
import { useExecution } from "@/lib/api/queries";
import type { ExecutionRunDetail, MetricValue } from "@/lib/api/types";
import { formatMetricValue } from "@/lib/domain/metrics";
import { isRunTerminal, runStatusMeta } from "@/lib/domain/status";
import { formatClock, formatResourceUsage } from "@/lib/format";

/**
 * 「資源使用」格的內容（契約 §4.3 M-19）：`CPU 12.3%・記憶體 345 MB・3 行程`；沒有資料一律單一「—」。
 * 「沒有資料」＝批次詳情還沒回來、`bridge.connected=false`、批次已終態（詳情輪詢在終態後停止，最後一次抓到的數字不得繼續顯示）、
 * 或 `bridge.resources` 為 null／缺席。另外把 PAUSED 也算進去：Bridge 的 pause 會終止整棵引擎行程樹（契約 §3.1.2），
 * 暫停中伺服器回 null；SSE 的 status 事件先把快取改成 PAUSED、REST 重抓要等一個去抖週期，這段空檔不能繼續顯示暫停前的舊數字。
 */
function resourceView(run: ExecutionRunDetail | undefined): { text: string; sampledAt: string | undefined } {
  const none = { text: formatResourceUsage(null), sampledAt: undefined };
  if (!run || run.bridge.connected === false || isRunTerminal(run.status) || run.status === "PAUSED") return none;
  const resources = run.bridge.resources;
  const text = formatResourceUsage(resources);
  return text === none.text ? none : { text, sampledAt: resources?.sampledAt };
}

/**
 * 「Agent 即時狀態」卡（PRD US-M-10；契約 §4.3 M-19）：連線狀態指示燈（Engine Bridge 是否可達）、目前任務、可用率、資源使用。
 * 資料：GET /executions/{runId}（bridge.connected／instance／status／resources、currentStep；Bridge 不可達時仍回 200）＋ metrics.agentAvailability。
 * 資源使用（v1.3，D-12）：Bridge 背景以 psutil 取樣引擎行程樹（約每 5 秒），console-api 投影成 bridge.resources，
 * 前端隨批次詳情輪詢（15 秒）顯示，數字最舊約 20 秒；v1.2 的「Bridge 沒有此資料」說明句已移除。
 */
export function AgentCard({ runId, availability }: { runId: string | undefined; availability: MetricValue | undefined }) {
  const q = useExecution(runId);
  const run = q.data;
  const connected = run?.bridge.connected;
  const running = run ? !isRunTerminal(run.status) : false;
  const resource = resourceView(run);

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
          {/* 第二列整列：既有四格的位置與樣式不動；取樣時間放 tooltip（契約建議，非驗收項） */}
          <div className="col-span-full">
            <div className="text-xs text-wg-muted">資源使用</div>
            <div className="mt-1 text-[15px]" data-testid="agent-resources" title={resource.sampledAt ? `取樣時間 ${formatClock(resource.sampledAt)}` : undefined}>
              {resource.text}
            </div>
          </div>
        </div>
      )}
      {/* 只留 Bridge 實例資訊（契約 M-19）；沒有實例時段落是空的、整段隱藏，但元素仍在，讓「沒有舊說明句」的斷言有東西可斷言 */}
      <p className="mt-3 text-xs text-wg-muted empty:hidden" data-testid="agent-note">
        {run?.bridge.instance ? `Bridge 實例：${run.bridge.instance}。` : null}
      </p>
    </Card>
  );
}
