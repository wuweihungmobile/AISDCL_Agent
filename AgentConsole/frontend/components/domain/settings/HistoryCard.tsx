"use client";

/**
 * 修改歷史卡（設計稿畫面 9；US-S-07；契約 §1.5.8）：等寬字體逐列 `時間 │ 參數 │ 舊值 → 新值 │ @使用者`，由新到舊，分頁。
 * 顯示目前分類 tab 的歷史（page 以 1 起算，後端 0 起算）。加密參數的新舊值後端一律回遮罩，這裡原樣顯示。
 */
import { ClipboardList } from "lucide-react";
import { useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { useSettingsHistory } from "@/lib/api/queries";
import type { ConfigCategory } from "@/lib/api/types";
import { formatHistoryLine } from "./settingsModel";

const PAGE_SIZE = 20;

export function HistoryCard({ category }: { category: ConfigCategory }) {
  const [page, setPage] = useState(1);
  const query = useSettingsHistory({ category, page: page - 1, size: PAGE_SIZE });
  const data = query.data;
  const totalPages = Math.max(1, data?.totalPages ?? 1);

  return (
    <Card className="mt-6 px-[22px] py-5" data-testid="settings-history">
      <div className="mb-3 flex items-center gap-2">
        <ClipboardList size={20} className="text-wg-primary" aria-hidden />
        <CardTitle>修改歷史</CardTitle>
        {data ? <span className="text-xs text-wg-muted">共 {data.totalElements} 筆</span> : null}
      </div>
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} title="無法載入修改歷史" />
      ) : !data ? (
        <div aria-busy="true" aria-label="修改歷史載入中" className="flex flex-col gap-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-5" />
          ))}
        </div>
      ) : data.content.length === 0 ? (
        <EmptyState title="這個分類還沒有修改紀錄" />
      ) : (
        <ol className="flex flex-col gap-1.5 font-mono text-xs leading-relaxed">
          {data.content.map((h) => {
            const line = formatHistoryLine(h);
            return (
              <li key={h.id} data-testid="history-line" className="flex flex-wrap gap-x-2 gap-y-0.5 break-all">
                <span>{line.time}</span>
                <span aria-hidden className="text-wg-muted">│</span>
                <span className="text-wg-primary">{line.param}</span>
                <span aria-hidden className="text-wg-muted">│</span>
                <span>{line.change}</span>
                <span aria-hidden className="text-wg-muted">│</span>
                <span className="text-wg-muted">{line.by}</span>
              </li>
            );
          })}
        </ol>
      )}
      {totalPages > 1 ? <Pagination className="mt-4" page={page} totalPages={totalPages} onPageChange={setPage} /> : null}
    </Card>
  );
}
