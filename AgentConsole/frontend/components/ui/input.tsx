import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * 表單欄位共用外觀（設計稿 .wg-input）：高 ≥44px、8px 圓角、1px 邊框、15px 字；
 * focus 邊框轉主色，外框由全域 :focus-visible 的 2px 主色焦點環提供（不寫 outline-none）。
 */
export const fieldClass =
  "w-full min-h-11 rounded-md border border-wg-line bg-white px-4 py-2.5 text-[15px] text-wg-text placeholder:text-wg-muted transition-colors focus:border-wg-primary aria-invalid:border-wg-error disabled:cursor-not-allowed disabled:bg-wg-disabled-bg disabled:text-wg-disabled-text";

export function Input({ className, type = "text", ...props }: React.ComponentProps<"input">) {
  return <input data-slot="input" type={type} className={cn(fieldClass, className)} {...props} />;
}
