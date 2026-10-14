"use client";

import * as React from "react";
import { Check } from "lucide-react";
import { Checkbox as CheckboxPrimitive } from "radix-ui";

import { cn } from "@/lib/utils";

/**
 * 核取方塊（設計稿：18px 方塊、4px 圓角、1px 邊框，勾選＝主色底＋白勾）。
 * 基於 Radix Checkbox，支援鍵盤與 aria-checked。
 */
export function Checkbox({
  className,
  ...props
}: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        "inline-flex size-[18px] shrink-0 cursor-pointer items-center justify-center rounded-sm border border-wg-line bg-white text-white transition-colors data-[state=checked]:border-wg-primary data-[state=checked]:bg-wg-primary disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator data-slot="checkbox-indicator" className="flex items-center justify-center">
        <Check size={13} aria-hidden />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}

/** 唯讀的核取方塊（通過標準 checklist 渲染用；不是表單控制項）。 */
export function CheckBox({ checked, className }: { checked: boolean; className?: string }) {
  return (
    <span
      aria-hidden
      data-slot="check-box"
      data-checked={checked}
      className={cn(
        "inline-flex size-[18px] shrink-0 items-center justify-center rounded-sm border border-wg-line text-white",
        checked ? "border-wg-primary bg-wg-primary" : "bg-transparent",
        className,
      )}
    >
      {checked ? <Check size={13} /> : null}
    </span>
  );
}
