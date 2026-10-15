import * as React from "react";
import { AlertTriangle, Inbox } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, describeError } from "@/lib/api/client";

/** 空狀態（沒有資料時的占位；可附一個行動按鈕）。 */
export function EmptyState({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div data-slot="empty-state" className="flex flex-col items-center gap-2 px-4 py-10 text-center text-wg-muted">
      <Inbox size={32} aria-hidden />
      <p className="text-[15px] font-medium text-wg-text">{title}</p>
      {description ? <p className="text-sm">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

/** 錯誤狀態：顯示後端訊息與 traceId（方便對照後端日誌），可重試。 */
export function ErrorState({ error, onRetry, title = "載入失敗" }: { error: unknown; onRetry?: () => void; title?: string }) {
  const traceId = error instanceof ApiError ? error.traceId : undefined;
  const message = error instanceof ApiError ? (error.reason ? `${error.message}：${error.reason}` : error.message) : describeError(error);
  return (
    <Card data-slot="error-state" role="alert" className="flex items-start gap-3 border-wg-draft-border bg-wg-draft-bg p-5">
      <AlertTriangle size={22} className="mt-0.5 shrink-0 text-wg-accent" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-wg-accent">{title}</p>
        <p className="mt-1 text-sm text-wg-text">{message}</p>
        {traceId ? <p className="mt-1 font-mono text-xs text-wg-muted">traceId：{traceId}</p> : null}
      </div>
      {onRetry ? (
        <Button variant="ghost" size="sm" onClick={onRetry}>
          重試
        </Button>
      ) : null}
    </Card>
  );
}

/** 頁面級骨架（標題＋兩張卡）；各頁自己的細部骨架在頁面內組合 Skeleton。 */
export function PageSkeleton() {
  return (
    <div aria-busy="true" aria-label="頁面載入中" className="flex flex-col gap-4">
      <Skeleton className="h-4 w-28" />
      <Skeleton className="h-10 w-80 max-w-full" />
      <Skeleton className="h-4 w-72 max-w-full" />
      <div className="mt-2 grid gap-6 md:grid-cols-2">
        <Skeleton className="h-44 rounded-lg" />
        <Skeleton className="h-44 rounded-lg" />
      </div>
      <Skeleton className="h-56 rounded-lg" />
    </div>
  );
}
