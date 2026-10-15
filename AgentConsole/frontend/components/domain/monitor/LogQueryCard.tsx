"use client";

import { Search } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { useDebounced } from "@/hooks/useDebounced";
import { useProjectLogs } from "@/lib/api/queries";
import type { RangeId } from "@/lib/domain/metrics";
import { LOG_LEVEL_COLOR } from "@/lib/domain/status";
import { formatClock } from "@/lib/format";

type Level = "ALL" | "INFO" | "WARN" | "ERROR";
const PAGE_SIZE = 20;

/**
 * 「執行日誌查詢」卡（設計稿畫面 8；契約 §1.3.6、§4.3 M-13；PRD US-M-04）：
 * 右上等級下拉（全部／INFO／WARN／ERROR），另有關鍵字（去抖 400ms，不分大小寫）與任務 id 篩選、由新到舊、分頁；
 * 每列＝時間（muted）＋等級（顏色依等級、寬 48px）＋訊息，等寬字體、#F5F7F2 底。日誌由既有資料衍生、不含引擎原始 stdout。
 */
export function LogQueryCard({
  projectId,
  range,
  runId,
  pollMs,
}: {
  projectId: string;
  range: RangeId;
  runId: string | undefined;
  pollMs: number | false;
}) {
  const [level, setLevel] = useState<Level>("ALL");
  const [keyword, setKeyword] = useState("");
  const [taskId, setTaskId] = useState("");
  const [page, setPage] = useState(0);
  const debouncedKeyword = useDebounced(keyword.trim(), 400);
  const debouncedTask = useDebounced(taskId.trim(), 400);

  const q = useProjectLogs(
    projectId,
    {
      range,
      runId,
      level,
      q: debouncedKeyword || undefined,
      taskId: debouncedTask || undefined,
      order: "desc",
      page,
      size: PAGE_SIZE,
    },
    pollMs,
  );
  const data = q.data;
  const totalPages = Math.max(1, data?.totalPages ?? 1);

  // 篩選條件一變，回到第一頁
  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPage(0);
  };

  return (
    <Card className="px-[22px] py-5" data-testid="log-query-card">
      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-3">
        <CardTitle>執行日誌查詢</CardTitle>
        <div className="flex flex-wrap items-center gap-2.5">
          <label className="sr-only" htmlFor="log-level">
            日誌等級
          </label>
          <Select id="log-level" size="sm" value={level} onChange={(e) => reset(setLevel)(e.target.value as Level)} data-testid="log-level">
            <option value="ALL">全部</option>
            <option value="INFO">INFO</option>
            <option value="WARN">WARN</option>
            <option value="ERROR">ERROR</option>
          </Select>
          <div className="relative w-[200px] max-sm:w-full">
            <Search size={16} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-wg-muted" aria-hidden />
            <Input
              type="search"
              aria-label="搜尋日誌關鍵字"
              placeholder="關鍵字…"
              value={keyword}
              onChange={(e) => reset(setKeyword)(e.target.value)}
              className="min-h-9 py-1.5 pl-9 text-sm"
              data-testid="log-keyword"
            />
          </div>
          <Input
            aria-label="任務 id"
            placeholder="任務 id"
            value={taskId}
            onChange={(e) => reset(setTaskId)(e.target.value)}
            className="min-h-9 w-[200px] py-1.5 font-mono text-sm max-sm:w-full"
            data-testid="log-task"
          />
        </div>
      </div>

      {q.isError && !data ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} title="無法載入日誌" />
      ) : q.isPending ? (
        <Skeleton className="h-32" />
      ) : (
        <>
          <div className="rounded-md bg-wg-base px-3.5 py-3 font-mono text-[12.5px] leading-[1.9]" data-testid="log-rows" role="log" aria-label="執行日誌查詢結果">
            {data && data.content.length > 0 ? (
              data.content.map((l) => (
                <div key={l.id} className="flex gap-3" data-testid="log-row" data-level={l.level}>
                  <span className="shrink-0 text-wg-muted">{formatClock(l.timestamp)}</span>
                  <span className="w-12 shrink-0 font-semibold" style={{ color: LOG_LEVEL_COLOR[l.level] }}>
                    {l.level}
                  </span>
                  <span className="min-w-0 break-words">{l.message}</span>
                </div>
              ))
            ) : (
              <div className="text-wg-muted" data-testid="log-empty">
                沒有符合條件的日誌
              </div>
            )}
          </div>
          <div className="mt-2.5 flex items-center justify-between text-[13px] text-wg-muted">
            <span data-testid="log-total">共 {data?.totalElements ?? 0} 筆</span>
            <span className="flex items-center gap-2">
              <Button variant="ghost" size="sm" disabled={page <= 0} onClick={() => setPage((p) => Math.max(0, p - 1))} data-testid="log-prev">
                上一頁
              </Button>
              <span data-testid="log-page">
                {page + 1} / {totalPages}
              </span>
              <Button variant="ghost" size="sm" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)} data-testid="log-next">
                下一頁
              </Button>
            </span>
          </div>
        </>
      )}
    </Card>
  );
}
