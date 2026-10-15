"use client";

/**
 * 頂列通知鈴（契約 §4.5 G-01）：紅色徽章＝待審核項目＋未確認告警（前端加總）；
 * 點開一個小面板列出三個數字與連結（契約 G-G2：沒有通知列表頁，暫以鈴的計數取代）。
 * 資料來源是 GET /notifications/summary（useNotificationSummary，頂列已輪詢，這裡只讀、不另外請求）。
 * 這支檔不是版面區塊（四區塊只在 app/layout.tsx 組裝）；TopRegion 引用它。
 */
import { AlertTriangle, Bell, ClipboardCheck, ListChecks, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Popover } from "radix-ui";

import { CountBadge } from "@/components/ui/badge";
import { useCurrentProjectId } from "@/hooks/useCurrentProjectId";
import type { NotificationSummary } from "@/lib/api/types";

type Row = { id: string; label: string; icon: LucideIcon; count: number | undefined; href: string };

export function NotificationBell({ summary }: { summary: NotificationSummary | undefined }) {
  const projectId = useCurrentProjectId();
  const reviews = summary?.pendingReviews;
  const alerts = summary?.unacknowledgedAlerts;
  const bellCount = (reviews ?? 0) + (alerts ?? 0);

  // 待審核項目與告警都屬於「某個專案的執行／監控頁」；沒有目前專案時退回專案列表
  const execHref = projectId ? `/projects/${projectId}/execute` : "/projects";
  const monitorHref = projectId ? `/projects/${projectId}/monitor` : "/projects";
  const rows: Row[] = [
    { id: "signoffs", label: "待簽核草案", icon: ClipboardCheck, count: summary?.pendingSignoffs, href: "/#pending-signoff" },
    { id: "reviews", label: "待審核項目", icon: ListChecks, count: reviews, href: execHref },
    { id: "alerts", label: "未確認告警", icon: AlertTriangle, count: alerts, href: monitorHref },
  ];

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          aria-label={bellCount > 0 ? `通知（${bellCount} 筆待處理）` : "通知"}
          title="通知"
          data-testid="bell-trigger"
          className="relative inline-flex size-11 cursor-pointer items-center justify-center rounded-full border-none bg-transparent text-white transition-opacity hover:opacity-85"
        >
          <Bell size={24} aria-hidden />
          {bellCount > 0 ? (
            <CountBadge count={bellCount} floating className="top-0 right-0" data-testid="bell-badge" />
          ) : null}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={8}
          aria-label="通知摘要"
          data-testid="notification-panel"
          className="z-[70] w-[300px] max-w-[calc(100vw-32px)] rounded-lg border border-wg-line bg-wg-surface p-4 text-wg-text data-[state=open]:animate-wg-fade"
        >
          <div className="mb-2 text-base font-semibold">通知摘要</div>
          <ul className="flex flex-col">
            {rows.map(({ id, label, icon: Icon, count, href }) => (
              <li key={id} className="border-t border-wg-line first:border-t-0">
                <Popover.Close asChild>
                  <Link
                    href={href}
                    data-testid={`notification-${id}`}
                    className="flex items-center gap-2.5 py-2.5 text-sm transition-colors hover:text-wg-primary"
                  >
                    <Icon size={18} className="shrink-0 text-wg-primary" aria-hidden />
                    <span className="flex-1">{label}</span>
                    <span className="font-mono text-[15px] font-semibold" data-testid={`notification-${id}-count`}>
                      {count ?? "—"}
                    </span>
                  </Link>
                </Popover.Close>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-wg-muted">每 30 秒自動更新；頁面不可見時暫停。</p>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
