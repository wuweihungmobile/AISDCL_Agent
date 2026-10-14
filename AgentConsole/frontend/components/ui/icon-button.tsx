import * as React from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * 設計系統 IconButton：純圖示按鈕，必帶 label（aria-label＋title）。
 * ghost＝透明、hover 變主色字；solid＝主色圓鈕；circular＝半透明白圓鈕（用在深色頂列）。
 */
export type IconButtonProps = Omit<React.ComponentProps<"button">, "children"> & {
  icon: LucideIcon;
  label: string;
  variant?: "ghost" | "solid" | "circular";
  size?: number;
  iconSize?: number;
};

export function IconButton({
  icon: Icon,
  label,
  variant = "ghost",
  size = 40,
  iconSize,
  className,
  style,
  type = "button",
  ...props
}: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      data-slot="icon-button"
      className={cn(
        "relative inline-flex shrink-0 cursor-pointer items-center justify-center border-none p-0 transition-all duration-200 ease-out disabled:cursor-not-allowed disabled:text-wg-disabled-text",
        variant === "ghost" && "rounded-md bg-transparent text-wg-text hover:text-wg-primary",
        variant === "solid" && "rounded-full bg-wg-primary text-white hover:bg-wg-primary-strong",
        variant === "circular" && "rounded-full bg-white/80 text-wg-text hover:bg-white/95",
        className,
      )}
      style={{ width: size, height: size, ...style }}
      {...props}
    >
      <Icon size={iconSize ?? Math.round(size * 0.55)} aria-hidden />
    </button>
  );
}
