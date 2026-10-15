import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * 設計系統卡片：白底、12px 圓角、1px hairline 邊框、無陰影（深度只靠邊框與底色階差）。
 * 內距由使用處決定（設計稿各處為 16／18／20／22／24px 不等，不強行統一）。
 */
export function Card({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="card" className={cn("rounded-lg border border-wg-line bg-wg-surface", className)} {...props} />;
}

/** 卡片標題（設計稿 H3：18px／600） */
export function CardTitle({ className, ...props }: React.ComponentProps<"h3">) {
  return <h3 data-slot="card-title" className={cn("text-lg font-semibold", className)} {...props} />;
}
