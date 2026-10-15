"use client";

import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { TokenTrendRow } from "@/lib/domain/metrics";
import { cn } from "@/lib/utils";

/** 12000 → 12K；其餘原值（座標軸刻度用）。 */
export function formatTokensShort(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${+(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1000) return `${+(v / 1000).toFixed(1)}K`;
  return String(v);
}

type TipProps = { active?: boolean; label?: string; payload?: Array<{ dataKey?: string; value?: number | null }> };

function TrendTooltip({ active, label, payload }: TipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const get = (key: string) => payload.find((p) => p.dataKey === key)?.value;
  const used = get("used");
  const budget = get("budget");
  return (
    <div className="rounded-md border border-wg-line bg-wg-surface px-3 py-2 text-sm">
      <p className="mb-1 font-medium text-wg-text">{label}</p>
      <p className="text-wg-text">Token 使用：{used === undefined || used === null ? "—" : used.toLocaleString("en-US")}</p>
      {budget !== undefined && budget !== null ? <p className="text-wg-muted">預算線：{budget.toLocaleString("en-US")}</p> : null}
    </div>
  );
}

/**
 * Token 使用趨勢（設計稿畫面 8；契約 §4.3 M-08；PRD US-M-02）：
 * 主色折線畫累計使用量（cumulativeTokens）、opacity .08 的面積填充、虛線預算線（border 色）、軸標籤 11px。
 * 顏色一律走 className 的 token（stroke-wg-*／fill-wg-*），元件內沒有色碼；與專案其他圖表（Tremor Raw）同一套手法。
 * 圖表以 role="img" 提供文字替代說明（UI-A11Y-04），並附螢幕閱讀器專用的清單。
 */
export function TokenTrendChart({ rows, className }: { rows: readonly TokenTrendRow[]; className?: string }) {
  const hasBudget = rows.some((r) => r.budget !== null);
  const last = rows[rows.length - 1];
  const summary =
    rows.length === 0
      ? "沒有資料"
      : `${rows.length} 個時間點，最新累計 ${last.used.toLocaleString("en-US")} Token${last.budget ? `，預算 ${last.budget.toLocaleString("en-US")}` : ""}`;
  return (
    <div>
      <div role="img" aria-label={`Token 使用趨勢圖：${summary}`} data-testid="token-trend-chart" className={cn("h-[200px] w-full", className)}>
        <ResponsiveContainer>
          <ComposedChart data={rows as TokenTrendRow[]} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid className="stroke-wg-line" horizontal vertical={false} />
            <XAxis dataKey="time" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} className="fill-wg-muted" fill="" stroke="" minTickGap={24} />
            <YAxis
              width={48}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11 }}
              className="fill-wg-muted"
              fill=""
              stroke=""
              tickFormatter={formatTokensShort}
              allowDecimals={false}
              domain={[0, "auto"]}
            />
            <Tooltip content={<TrendTooltip />} cursor={{ className: "stroke-wg-line", strokeWidth: 1 }} />
            {hasBudget ? (
              <Line
                type="stepAfter"
                dataKey="budget"
                name="預算線"
                className="stroke-wg-line"
                stroke=""
                strokeWidth={1.5}
                strokeDasharray="6 4"
                dot={false}
                activeDot={false}
                isAnimationActive={false}
                connectNulls
              />
            ) : null}
            <Area
              type="monotone"
              dataKey="used"
              name="Token 使用"
              className="fill-wg-primary stroke-wg-primary"
              stroke=""
              fill=""
              fillOpacity={0.08}
              strokeWidth={2.5}
              dot={rows.length <= 1 ? { r: 4, className: "fill-wg-primary stroke-wg-surface" } : false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <ul className="sr-only">
        {rows.map((r, i) => (
          // 範圍剛切換時（保留上一份資料）不同時間點可能被標成同一個標籤：key 帶上順序，避免重複 key
          <li key={`${i}:${r.time}`}>
            {r.time}：累計 {r.used} Token{r.budget ? `，預算 ${r.budget}` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}
