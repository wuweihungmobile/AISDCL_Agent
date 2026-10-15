"use client";

import { CircleAlert, CircleCheck, Info } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Toast（設計稿：底部置中、--color-text-main 深底白字、8px 圓角、check-circle 綠勾）。
 * 一次只顯示一則（與設計稿一致）；成功 2.4 秒、錯誤 6 秒（要讓人看完 traceId）後自動消失。
 * ToastProvider 持有狀態；ToastHost 由 BottomRegion 渲染（Toast 宿主住底部區塊）。
 * shadcn 的 toast 元件只支援 Base UI 基底（CLI 回報），sonner 與設計稿視覺不同，故自行實作。
 */
export type ToastTone = "success" | "error" | "info";
type ToastState = { id: number; message: string; tone: ToastTone } | null;

type ToastContextValue = {
  toast: ToastState;
  show: (message: string, tone?: ToastTone) => void;
  dismiss: () => void;
};

const ToastContext = React.createContext<ToastContextValue | null>(null);

const DURATION: Record<ToastTone, number> = { success: 2400, info: 3200, error: 6000 };

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = React.useState<ToastState>(null);
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const counter = React.useRef(0);

  const dismiss = React.useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    setToast(null);
  }, []);

  const show = React.useCallback((message: string, tone: ToastTone = "success") => {
    if (timer.current) clearTimeout(timer.current);
    counter.current += 1;
    setToast({ id: counter.current, message, tone });
    timer.current = setTimeout(() => {
      setToast(null);
      timer.current = null;
    }, DURATION[tone]);
  }, []);

  React.useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const value = React.useMemo(() => ({ toast, show, dismiss }), [toast, show, dismiss]);
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

function useToastContext(): ToastContextValue {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast 必須在 <ToastProvider> 之內使用");
  return ctx;
}

/** 顯示 toast：const { success, error, info } = useToast() */
export function useToast() {
  const { show } = useToastContext();
  return React.useMemo(
    () => ({
      success: (message: string) => show(message, "success"),
      error: (message: string) => show(message, "error"),
      info: (message: string) => show(message, "info"),
    }),
    [show],
  );
}

const ICON = { success: CircleCheck, error: CircleAlert, info: Info } as const;
// toast 是深底（bg-wg-text）：圖示要用深底上的亮色。error 用 terminal-accent（5.08:1）；淺底用的 accent 已加深成 #B93F22，在深底只剩 2.30:1（低於非文字的 3:1，DEF-AC-004）
const ICON_COLOR = {
  success: "text-wg-online",
  error: "text-wg-terminal-accent",
  info: "text-wg-secondary",
} as const;

export function ToastHost() {
  const { toast } = useToastContext();
  const Icon = toast ? ICON[toast.tone] : null;
  return (
    <div data-slot="toast-host" role="status" aria-live="polite" className="pointer-events-none fixed bottom-7 left-1/2 z-[90] -translate-x-1/2">
      {toast && Icon ? (
        <div key={toast.id} className="pointer-events-auto flex max-w-[min(560px,calc(100vw-32px))] items-center gap-2 rounded-md bg-wg-text px-[22px] py-3 text-sm text-white animate-wg-fade">
          <Icon size={18} className={cn("shrink-0", ICON_COLOR[toast.tone])} aria-hidden />
          <span className="break-words">{toast.message}</span>
        </div>
      ) : null}
    </div>
  );
}
