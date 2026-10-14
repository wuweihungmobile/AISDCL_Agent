"use client";

import { Card, CardTitle } from "@/components/ui/card";
import type { ProjectSummary } from "@/lib/api/types";
import { PROJECT_STATUS } from "@/lib/domain/status";
import { AreaChart } from "./tremor/AreaChart";

const ORDER = ["DRAFT", "READY", "EXECUTING", "COMPLETED", "FAILED", "ARCHIVED"] as const;

/** 各狀態的專案數（依 PROJECT_STATUS 順序）；純函式，方便測試。 */
export function statusDistribution(projects: Pick<ProjectSummary, "status">[]) {
  return ORDER.map((s) => ({
    status: PROJECT_STATUS[s].label,
    專案數: projects.filter((p) => p.status === s).length,
  }));
}

/**
 * Dashboard 的圖表 spike（W3-A）：Tremor Raw AreaChart 於 Tailwind 4 build＋render 通過（ADR-002 §圖表）。
 * 資料先用「專案狀態分佈」；真指標（Token 趨勢、任務分佈）W4 接監控 API。
 * 設計系統禁用漸層 → fill="solid"。UI-A11Y-04：圖表以 role="img"＋aria-label 提供文字替代說明，並附螢幕閱讀器專用清單。
 */
export function ProjectStatusChart({ projects }: { projects: Pick<ProjectSummary, "status">[] }) {
  const data = statusDistribution(projects);
  const summary = data.map((d) => `${d.status} ${d.專案數}`).join("、");
  return (
    <Card className="mt-6 px-[22px] py-5" data-testid="status-chart-card">
      <CardTitle className="mb-3.5">專案狀態分佈</CardTitle>
      <div role="img" aria-label={`專案狀態分佈圖：${summary}`}>
        <AreaChart
          className="h-52"
          data={data}
          index="status"
          categories={["專案數"]}
          colors={["primary"]}
          fill="solid"
          showLegend={false}
          allowDecimals={false}
          yAxisWidth={48}
          valueFormatter={(v) => `${v} 個`}
        />
      </div>
      <ul className="sr-only">
        {data.map((d) => (
          <li key={d.status}>
            {d.status}：{d.專案數} 個專案
          </li>
        ))}
      </ul>
    </Card>
  );
}
