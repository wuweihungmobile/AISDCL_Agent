"use client";

import * as React from "react";
import { X } from "lucide-react";
import { Dialog as DialogPrimitive } from "radix-ui";

import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/utils";

/**
 * 設計稿 Dialog：遮罩 rgba(42,54,38,.32)、白卡 560px／12px 圓角／1px 邊框／無陰影、最大高 88vh 可捲動；
 * 頭部＝標題＋關閉 IconButton，身體 22/24 內距，底部＝取消＋儲存。基於 Radix Dialog（焦點鎖、Esc、aria）。
 */
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({
  className,
  children,
  title,
  description,
  ...props
}: Omit<React.ComponentProps<typeof DialogPrimitive.Content>, "title"> & {
  /** 無障礙必備：對話框標題（同時顯示在頭部） */
  title: string;
  /** 給螢幕閱讀器的補充描述（不顯示） */
  description?: string;
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay data-slot="dialog-overlay" className="fixed inset-0 z-[80] bg-wg-overlay" />
      <DialogPrimitive.Content
        data-slot="dialog-content"
        className={cn(
          "fixed top-1/2 left-1/2 z-[81] flex max-h-[88vh] w-[560px] max-w-[calc(100%-48px)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-y-auto rounded-lg border border-wg-line bg-wg-surface data-[state=open]:animate-wg-fade",
          className,
        )}
        {...props}
        {...(description ? {} : { "aria-describedby": undefined })}
      >
        <div className="flex items-center justify-between border-b border-wg-line px-6 py-5">
          <DialogPrimitive.Title className="text-xl font-semibold">{title}</DialogPrimitive.Title>
          <DialogPrimitive.Close asChild>
            <IconButton icon={X} label="關閉" size={36} />
          </DialogPrimitive.Close>
        </div>
        {description ? <DialogPrimitive.Description className="sr-only">{description}</DialogPrimitive.Description> : null}
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogBody({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("flex flex-col gap-4 px-6 py-[22px]", className)} {...props} />;
}

export function DialogFooter({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("flex justify-end gap-2.5 border-t border-wg-line px-6 py-4", className)} {...props} />;
}
