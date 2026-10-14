"use client";

/**
 * Bottom 區（UI-LAY-04）：底部狀態列——console-api 與 Engine Bridge 連線狀態點、版本號，並宿主 Toast。
 * 設計稿沒有這一列（依掌舵者四區塊要求新增）；不放任何新功能。全站唯一一份，由 app/layout.tsx 組裝。
 */
import { ToastHost } from "@/components/ui/toast";
import {
  SERVICE_LABEL,
  useBridgeStatus,
  useConsoleApiStatus,
  type ServiceState,
} from "@/hooks/useServiceStatus";
import { cn } from "@/lib/utils";

const DOT: Record<ServiceState, string> = {
  online: "bg-wg-primary",
  offline: "bg-wg-error",
  checking: "bg-wg-warning animate-wg-blink",
  unknown: "bg-wg-disabled-text",
  idle: "bg-wg-disabled-text",
};

function Status({ name, state }: { name: string; state: ServiceState }) {
  return (
    <span className="inline-flex items-center gap-1.5" data-testid={`status-${name}`}>
      <span aria-hidden className={cn("inline-block size-2 rounded-full", DOT[state])} />
      {name} · {SERVICE_LABEL[state]}
    </span>
  );
}

export function BottomRegion() {
  const api = useConsoleApiStatus();
  const bridge = useBridgeStatus();
  const version = process.env.NEXT_PUBLIC_APP_VERSION ?? "dev";
  return (
    <footer
      data-region="bottom"
      className="flex h-8 shrink-0 items-center justify-between border-t border-wg-line bg-wg-surface px-6 text-xs text-wg-muted max-md:px-3"
    >
      <div className="flex items-center gap-5 max-md:gap-3">
        <Status name="console-api" state={api} />
        <Status name="Engine Bridge" state={bridge} />
      </div>
      <span data-testid="app-version">Console v{version}</span>
      <ToastHost />
    </footer>
  );
}
