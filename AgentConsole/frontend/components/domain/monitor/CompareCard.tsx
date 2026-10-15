"use client";

import { useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import type { ExecutionRunSummary } from "@/lib/api/types";
import { budgetUsagePct, formatDuration, formatMetricValue } from "@/lib/domain/metrics";
import { runStatusMeta } from "@/lib/domain/status";
import { formatDateTime, formatNumber } from "@/lib/format";

type Row = { key: string; label: string; value: (r: ExecutionRunSummary) => string };

const ROWS: readonly Row[] = [
  { key: "status", label: "狀態", value: (r) => runStatusMeta(r.status).label },
  { key: "level", label: "自治等級", value: (r) => `Level ${r.autonomyLevel}` },
  { key: "started", label: "開始時間", value: (r) => formatDateTime(r.startedAt) },
  { key: "duration", label: "時長", value: (r) => formatDuration(r.durationSec) },
  { key: "tokens", label: "Token 消耗", value: (r) => formatNumber(r.totalTokensUsed) },
  { key: "budget", label: "Token 預算使用率", value: (r) => formatMetricValue("percent", budgetUsagePct(r.totalTokensUsed, r.tokenBudget)) },
  { key: "tasks", label: "任務完成", value: (r) => `${r.tasksCompleted} / ${r.tasksTotal}` },
  { key: "failed", label: "失敗任務", value: (r) => String(r.tasksFailed) },
  { key: "success", label: "成功率", value: (r) => formatMetricValue("percent", r.successRate) },
];

const optionLabel = (r: ExecutionRunSummary) => `Run #${r.runNumber} · ${runStatusMeta(r.status).label}`;

/**
 * 「批次比較」卡（PRD US-M-06；契約 §1.2.2：批次列表每列帶 Token／時間／成功率，供比較）：選兩個批次橫向對比。
 * 取舍：任務書寫「用 metrics?runId= 各取一次」，契約 §1.2.2 已讓列表每列帶齊比較欄位——直接用列表，零額外請求
 * （metrics 預設只看最近 24 小時，拿來比較舊批次還會被視窗截掉）。預設比較最新兩個批次。
 */
export function CompareCard({ runs }: { runs: readonly ExecutionRunSummary[] }) {
  const [aId, setA] = useState<string | null>(null);
  const [bId, setB] = useState<string | null>(null);
  const a = runs.find((r) => r.id === aId) ?? runs[1];
  const b = runs.find((r) => r.id === bId) ?? runs[0];

  return (
    <Card className="px-[22px] py-5" data-testid="compare-card">
      <CardTitle className="mb-3.5">批次比較</CardTitle>
      {runs.length < 2 || !a || !b ? (
        <p className="py-4 text-center text-sm text-wg-muted" data-testid="compare-empty">
          至少需要兩個執行批次才能比較。
        </p>
      ) : (
        <>
          <div className="mb-3 flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2 text-wg-muted">
              批次 A
              <Select size="sm" value={a.id} onChange={(e) => setA(e.target.value)} data-testid="compare-a" aria-label="比較批次 A">
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {optionLabel(r)}
                  </option>
                ))}
              </Select>
            </label>
            <label className="flex items-center gap-2 text-wg-muted">
              批次 B
              <Select size="sm" value={b.id} onChange={(e) => setB(e.target.value)} data-testid="compare-b" aria-label="比較批次 B">
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {optionLabel(r)}
                  </option>
                ))}
              </Select>
            </label>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] border-collapse text-sm" data-testid="compare-table">
              <thead>
                <tr className="text-left text-wg-muted">
                  <th className="border-b border-wg-line py-2 pr-4 font-medium">指標</th>
                  <th className="border-b border-wg-line py-2 pr-4 font-medium">Run #{a.runNumber}</th>
                  <th className="border-b border-wg-line py-2 font-medium">Run #{b.runNumber}</th>
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => (
                  <tr key={row.key} data-testid={`compare-row-${row.key}`}>
                    <th scope="row" className="border-b border-wg-line py-2 pr-4 text-left font-normal text-wg-muted">
                      {row.label}
                    </th>
                    <td className="border-b border-wg-line py-2 pr-4 font-mono" data-col="a">
                      {row.value(a)}
                    </td>
                    <td className="border-b border-wg-line py-2 font-mono" data-col="b">
                      {row.value(b)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Card>
  );
}
