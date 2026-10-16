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

/**
 * 記下開啟這個對話框的元素：內容掛上的那一刻讀 document.activeElement（沒有就記 null：焦點在 <body>，例如 Safari 點擊按鈕不會讓它取得焦點）。
 * 用 insertion effect 而不是 Radix 的 onOpenAutoFocus：insertion effect 先於 layout 階段，此時內容裡的 autoFocus 屬性與子元件自己聚焦都還沒發生；
 * 內容一旦搶先聚焦，FocusScope 看到焦點已在內容內，根本不會發 onOpenAutoFocus。放在 Content 裡面，所以「條件渲染」與「常駐、只切 open」兩種寫法都只在開啟時掛上。
 */
function RememberOpener({ openerRef }: { openerRef: React.RefObject<HTMLElement | null> }) {
  React.useInsertionEffect(() => {
    const el = document.activeElement;
    openerRef.current = el instanceof HTMLElement && el !== document.body && el !== document.documentElement ? el : null;
  }, [openerRef]);
  return null;
}

/**
 * 焦點歸還（DEF-AC-011，WCAG 2.4.3）：Radix 的 DialogContent 關閉時一律 preventDefault，再只把焦點還給它自己的 DialogTrigger
 * （context.triggerRef）；本專案的對話框全由頁面狀態（open／target）控制、沒有 DialogTrigger，triggerRef 恆為 null，焦點就掉到 <body>。
 * 所以開啟時記下 document.activeElement（RememberOpener），關閉時（Esc、關閉鈕、取消鈕、呼叫端把 open 設回 false，一律走 FocusScope 卸載）
 * 還回去；所有呼叫端與日後新增的對話框一次受惠。
 * 呼叫端自己傳的 onOpenAutoFocus 原樣交給 Radix；onCloseAutoFocus 先被呼叫、再輪到歸還，呼叫 preventDefault() 即由呼叫端全權處理。
 * 開啟它的元素已不在 DOM 或已停用就不還（不會落在已拆下的節點），交回 Radix 預設行為，DialogTrigger 路徑照舊。
 */
export function DialogContent({
  className,
  children,
  title,
  description,
  onCloseAutoFocus,
  ...props
}: Omit<React.ComponentProps<typeof DialogPrimitive.Content>, "title"> & {
  /** 無障礙必備：對話框標題（同時顯示在頭部） */
  title: string;
  /** 給螢幕閱讀器的補充描述（不顯示） */
  description?: string;
}) {
  const openerRef = React.useRef<HTMLElement | null>(null);

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
        onCloseAutoFocus={(event) => {
          onCloseAutoFocus?.(event);
          if (event.defaultPrevented) return;
          const opener = openerRef.current;
          if (opener?.isConnected && !opener.matches(":disabled")) {
            event.preventDefault();
            opener.focus();
          }
        }}
      >
        <RememberOpener openerRef={openerRef} />
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
