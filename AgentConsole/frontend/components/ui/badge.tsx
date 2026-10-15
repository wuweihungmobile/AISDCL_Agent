import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * 計數徽章（設計稿：通知鈴／signoff 佇列／待人工審批旁的紅色圓形數字）。
 * 底色 --color-accent；floating＝絕對定位在父層右上角並帶 2px 同色邊（與頂列底色融為一體）。
 */
export function CountBadge({
  count,
  floating = false,
  size = "md",
  className,
  ...props
}: Omit<React.ComponentProps<"span">, "children"> & {
  count: number;
  floating?: boolean;
  size?: "sm" | "md" | "lg";
}) {
  return (
    <span
      data-slot="count-badge"
      className={cn(
        "inline-flex items-center justify-center rounded-full bg-wg-accent font-bold text-white",
        size === "sm" && "h-[18px] min-w-[18px] px-[5px] text-[11px] font-semibold",
        size === "md" && "h-5 min-w-5 px-1.5 text-xs",
        size === "lg" && "h-[22px] min-w-[22px] px-1.5 text-xs",
        floating && "absolute border-2 border-wg-header",
        className,
      )}
      {...props}
    >
      {count}
    </span>
  );
}

/** 扁平標籤（設計稿「未審批」：#fdeee9 底、accent 字、4px 圓角）。 */
export function Tag({ tone = "draft", className, ...props }: React.ComponentProps<"span"> & { tone?: "draft" }) {
  return (
    <span data-slot="tag" data-tone={tone} className={cn("inline-flex shrink-0 items-center rounded-sm bg-wg-draft-bg px-[7px] py-0.5 text-xs font-semibold text-wg-accent", className)} {...props} />
  );
}
