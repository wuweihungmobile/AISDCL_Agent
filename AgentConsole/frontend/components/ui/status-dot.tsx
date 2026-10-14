import * as React from "react";

import type { StatusMeta } from "@/lib/domain/status";
import { cn } from "@/lib/utils";

/** 狀態圓點：顏色取自 lib/domain/status.ts（token 引用）；live＝進行中的呼吸動畫（wg-blink 1.4s）。 */
export function StatusDot({
  color,
  size = 8,
  live = false,
  className,
}: {
  color: string;
  size?: number;
  live?: boolean;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      data-slot="status-dot"
      className={cn("inline-block shrink-0 rounded-full", live && "animate-wg-blink", className)}
      style={{ width: size, height: size, background: color }}
    />
  );
}

/** 圓點＋中文標籤（列表與詳情標題列共用）。 */
export function StatusLabel({
  meta,
  dot = 8,
  live = false,
  className,
}: {
  meta: StatusMeta;
  dot?: number;
  live?: boolean;
  className?: string;
}) {
  return (
    <span
      data-slot="status-label"
      className={cn("inline-flex items-center gap-1.5 text-wg-muted", className)}
    >
      <StatusDot color={meta.color} size={dot} live={live} />
      {meta.label}
    </span>
  );
}
