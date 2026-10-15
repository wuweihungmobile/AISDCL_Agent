import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * 原生 <select>（設計稿 .wg-sel：去外觀＋自訂下拉箭頭，箭頭樣式住 app/globals.css）。
 * 刻意不用 Radix Select：設計稿是原生控制項，原生 select 對鍵盤、行動裝置與 E2E（selectOption）都最穩。
 *  size="sm"＝工具列用（14px 字、8/36/8/14 內距）；size="md"＝表單用（15px 字、11px 垂直內距）。
 */
export function Select({ className, size = "md", ...props }: Omit<React.ComponentProps<"select">, "size"> & { size?: "sm" | "md" }) {
  return (
    <select
      data-slot="select"
      className={cn(
        "wg-sel rounded-md border border-wg-line bg-white text-wg-text transition-colors focus:border-wg-primary aria-invalid:border-wg-error disabled:cursor-not-allowed disabled:bg-wg-disabled-bg disabled:text-wg-disabled-text",
        size === "sm" ? "py-2 pr-9 pl-3.5 text-sm" : "w-full py-[11px] pr-9 pl-3.5 text-[15px]",
        className,
      )}
      {...props}
    />
  );
}
