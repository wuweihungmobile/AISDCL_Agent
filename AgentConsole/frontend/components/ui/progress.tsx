"use client";

import * as React from "react";
import { Progress as ProgressPrimitive } from "radix-ui";

import { cn } from "@/lib/utils";

/**
 * 進度條（設計稿：高 7～8px、底 --color-bg-base、填色主色、寬度過場 .4s）。
 * 基於 Radix Progress，自帶 role="progressbar"／aria-valuenow；label 供螢幕閱讀器朗讀。
 */
export function Progress({
  value,
  label,
  className,
  barClassName,
}: {
  /** 0～100 */
  value: number;
  label: string;
  className?: string;
  barClassName?: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      value={clamped}
      aria-label={label}
      className={cn("relative h-2 w-full overflow-hidden rounded-full bg-wg-base", className)}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        className={cn("h-full bg-wg-primary transition-[width] duration-[400ms]", barClassName)}
        style={{ width: `${clamped}%` }}
      />
    </ProgressPrimitive.Root>
  );
}
