import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import type { LucideIcon } from "lucide-react";
import { Slot } from "radix-ui";

import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/spinner";

/**
 * 設計系統 Button（_ds/components/buttons/Button.jsx 的 Tailwind 版）：
 *  solid＝主色實底；accent＝警示橘紅實底（刪除等破壞性動作）；ghost＝無底，hover 才現底色。
 *  尺寸：sm 6/16、md 8/20、lg 12/28（padding），文字 14／14／16px，圖示 16／18／20px。
 *  扁平：無陰影、無位移、無按壓縮放；hover 只改色。
 */
const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center whitespace-nowrap rounded-md border border-transparent font-medium leading-[1.2] transition-all duration-200 ease-out disabled:cursor-not-allowed disabled:bg-wg-disabled-bg disabled:text-wg-disabled-text [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        solid: "bg-wg-primary text-white hover:bg-wg-primary-strong",
        accent: "bg-wg-accent text-white hover:bg-wg-accent-strong",
        ghost: "bg-transparent text-wg-text hover:bg-wg-base hover:text-wg-primary",
      },
      size: {
        sm: "gap-1.5 px-4 py-1.5 text-sm",
        md: "gap-2 px-5 py-2 text-sm",
        lg: "gap-2 px-7 py-3 text-base",
      },
    },
    defaultVariants: { variant: "solid", size: "md" },
  },
);

const ICON_PX = { sm: 16, md: 18, lg: 20 } as const;

export type ButtonProps = React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    iconLeft?: LucideIcon;
    iconRight?: LucideIcon;
    /** 進行中：顯示轉圈並停用 */
    loading?: boolean;
  };

export function Button({
  className,
  variant,
  size,
  asChild = false,
  iconLeft: IconLeft,
  iconRight: IconRight,
  loading = false,
  disabled,
  children,
  type = "button",
  ...props
}: ButtonProps) {
  const px = ICON_PX[size ?? "md"];
  if (asChild) {
    // asChild：樣式與屬性交給唯一的子元素（例如 <Link>）；圖示要放進子元素內部，才會和文字一起落在連結裡
    const child = React.isValidElement<{ children?: React.ReactNode }>(children) ? children : null;
    return (
      <Slot.Root data-slot="button" className={cn(buttonVariants({ variant, size }), className)} {...props}>
        {child
          ? React.cloneElement(
              child,
              undefined,
              <>
                {IconLeft ? <IconLeft size={px} aria-hidden /> : null}
                {child.props.children}
                {IconRight ? <IconRight size={px} aria-hidden /> : null}
              </>,
            )
          : children}
      </Slot.Root>
    );
  }
  return (
    <button
      data-slot="button"
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    >
      {loading ? <Spinner size={px} tone="onSolid" /> : IconLeft ? <IconLeft size={px} aria-hidden /> : null}
      {children}
      {IconRight ? <IconRight size={px} aria-hidden /> : null}
    </button>
  );
}

export { buttonVariants };
