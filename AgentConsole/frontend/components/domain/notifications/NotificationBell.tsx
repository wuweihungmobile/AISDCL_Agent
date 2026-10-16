"use client";

/**
 * 頂列通知鈴（契約 §4.5 G-01）：紅色徽章＝待審核項目＋未確認告警（前端加總）；
 * 點開一個小面板列出三個數字與連結（契約 G-G2：沒有通知列表頁，暫以鈴的計數取代）。
 * 資料來源是 GET /notifications/summary（useNotificationSummary，頂列已輪詢，這裡只讀、不另外請求）。
 * 這支檔不是版面區塊（四區塊只在 app/layout.tsx 組裝）；TopRegion 引用它。
 */
import { AlertTriangle, Bell, ClipboardCheck, ListChecks, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Popover } from "radix-ui";

import { CountBadge } from "@/components/ui/badge";
import type { NotificationSummary } from "@/lib/api/types";
import { projectIdFromPath } from "@/lib/nav/lastProject";

type Row = { id: string; label: string; icon: LucideIcon; count: number | undefined; href: string; hint?: string };

/**
 * 契約 §4.6 G-G4（已知限制，v1.4 維持 v1.3 的行為；主控裁決 Q5）：通知摘要只有三個**全部專案合計**的計數、沒有 projectId，
 * 所以「待審核項目」「未確認告警」兩個連結只能依「路由上的 projectId」落點——人在專案頁（/projects/{id}/…）→ 該專案的執行頁／監控頁，
 * 其他頁面（Dashboard、專案列表…）→ 專案列表（/projects），不猜「最近造訪」或「列表第一筆」；E2E-16 第 6 列同此。
 * 連結文案因此只說「這是全部專案的合計」與落點在哪，不把計數說成屬於某個專案。
 */
export function NotificationBell({ summary }: { summary: NotificationSummary | undefined }) {
  const projectId = projectIdFromPath(usePathname());
  const reviews = summary?.pendingReviews;
  const alerts = summary?.unacknowledgedAlerts;
  const bellCount = (reviews ?? 0) + (alerts ?? 0);

  const execHref = projectId ? `/projects/${projectId}/execute` : "/projects";
  const monitorHref = projectId ? `/projects/${projectId}/monitor` : "/projects";
  const scopeHint = (page: string) => (projectId ? `數字是全部專案的合計；點進去前往這個專案的${page}` : "數字是全部專案的合計；點進去前往專案列表，請自行挑選有待辦的專案");
  const rows: Row[] = [
    { id: "signoffs", label: "待簽核草案", icon: ClipboardCheck, count: summary?.pendingSignoffs, href: "/#pending-signoff", hint: "前往儀表板的「待人工審批」卡" },
    { id: "reviews", label: "待審核項目", icon: ListChecks, count: reviews, href: execHref, hint: scopeHint("執行頁") },
    { id: "alerts", label: "未確認告警", icon: AlertTriangle, count: alerts, href: monitorHref, hint: scopeHint("監控頁") },
  ];

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          // 徽章上的可見數字必須出現在名稱裡（WCAG 2.5.3 Label in Name；axe label-content-name-mismatch）；括號會讓 axe 認不出數字，所以用空格分隔
          aria-label={bellCount > 0 ? `通知 ${bellCount} 筆待處理` : "通知"}
          title="通知"
          data-testid="bell-trigger"
          className="relative inline-flex size-11 cursor-pointer items-center justify-center rounded-full border-none bg-transparent text-white transition-opacity hover:opacity-85"
        >
          <Bell size={24} aria-hidden />
          {bellCount > 0 ? <CountBadge count={bellCount} floating className="top-0 right-0" data-testid="bell-badge" /> : null}
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
            {rows.map(({ id, label, icon: Icon, count, href, hint }) => (
              <li key={id} className="border-t border-wg-line first:border-t-0">
                <Popover.Close asChild>
                  <Link href={href} title={hint} data-testid={`notification-${id}`} className="flex items-center gap-2.5 py-2.5 text-sm transition-colors hover:text-wg-primary">
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
          <p className="mt-2 text-xs text-wg-muted" data-testid="notification-scope-note">
            待審核項目與未確認告警是全部專案的合計；在專案頁點進去前往該專案，其他頁面前往專案列表。
          </p>
          <p className="mt-1 text-xs text-wg-muted">每 30 秒自動更新；頁面不可見時暫停。</p>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
