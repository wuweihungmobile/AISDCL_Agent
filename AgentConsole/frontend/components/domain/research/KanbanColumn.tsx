"use client";

/**
 * 看板單欄（FR-R2P-15-1；TCS-ResearchToPRD-P2-20261107 AT-962-11-2、11-6、11-E-2；IFACE-P2 §1.2）：欄名、完成徽章、事實列、深連結。
 *
 * 設計要點（為什麼這樣做）：
 *  - **量不到就說未知**：完成判定為 `unknown`（內環 FSM 衍生欄在 Bridge 不可達時是 null）時徽章寫「未知」，**不顯示成「已完成」也不顯示成進行中**；
 *    事實列的值為 null 時整列值寫「未知」，不用 0 或空白頂替（AT-962-11-E-2）。
 *  - **只連結、不控制**：深連結只用 `<Link>` 導到既有的執行中心與監控中心（帶 `?researchId=`），不呼叫任何執行控制端點、不用 `fetch`（AT-962-11-8 靜態掃描）。
 *    停用的連結不是按鈕（沿 `InnerLoopLinks`）：原因在 `title` 與文字，文案取登記處（`BUILD_DISABLED_TEXT`）。
 */
import { Activity, Play } from "lucide-react";
import Link from "next/link";

import type { KanbanDone } from "@/lib/domain/research";
import { cn } from "@/lib/utils";

export type KanbanFact = { label: string; value: string | number | null };
/** 深連結：`href` 為 null＝停用，`reason` 為停用原因（登記文案）。 */
export type KanbanLink = { href: string | null; reason: string | null };

const BADGE: Readonly<Record<string, { text: string; className: string }>> = {
  true: { text: "已完成", className: "border-wg-line bg-wg-surface-alt text-wg-text" },
  false: { text: "進行中", className: "border-wg-draft-border bg-wg-draft-bg text-wg-accent" },
  unknown: { text: "未知", className: "border-wg-error text-wg-error" },
};

function DeepLink({ label, icon: Icon, link, testId }: { label: string; icon: typeof Play; link: KanbanLink; testId: string }) {
  if (link.href !== null) {
    return (
      <Link href={link.href} data-testid={testId} className="inline-flex items-center gap-1 text-sm font-medium underline">
        <Icon size={14} aria-hidden />
        {label}
      </Link>
    );
  }
  return (
    <span data-testid={testId} aria-disabled="true" title={link.reason ?? undefined} className="inline-flex cursor-not-allowed items-center gap-1 text-sm text-wg-muted">
      <Icon size={14} aria-hidden />
      {label}
    </span>
  );
}

export function KanbanColumn({
  columnKey,
  label,
  done,
  facts,
  advisory = false,
  execute,
  monitor,
}: {
  columnKey: string;
  label: string;
  done: KanbanDone;
  facts: readonly KanbanFact[];
  /** 回歸驗收欄：RTM 是諮詢視圖，必須標出 */
  advisory?: boolean;
  execute: KanbanLink;
  monitor: KanbanLink;
}) {
  const badge = BADGE[String(done)];
  return (
    <section aria-label={label} data-testid={`kanban-col-${columnKey}`} data-done={String(done)} className="flex min-w-0 flex-col gap-3 rounded-md border border-wg-line bg-wg-surface p-4">
      <h4 className="flex flex-wrap items-center gap-2 text-base font-semibold">
        {label}
        <span data-testid={`kanban-badge-${columnKey}`} className={cn("rounded border px-2 py-0.5 text-xs font-medium", badge.className)}>
          {badge.text}
        </span>
        {advisory ? (
          <span data-testid="kanban-advisory" className="rounded border border-wg-line px-2 py-0.5 text-xs text-wg-muted">
            諮詢視圖
          </span>
        ) : null}
      </h4>
      <dl className="flex flex-col gap-1 text-sm">
        {facts.map((f) => (
          <div key={f.label} className="flex flex-wrap justify-between gap-2">
            <dt className="text-wg-muted">{f.label}</dt>
            <dd data-testid={`kanban-fact-${columnKey}`} className="break-all font-medium">
              {f.value === null ? "未知" : f.value}
            </dd>
          </div>
        ))}
      </dl>
      <div className="flex flex-wrap gap-3">
        <DeepLink label="執行中心" icon={Play} link={execute} testId={`kanban-exec-${columnKey}`} />
        <DeepLink label="監控中心" icon={Activity} link={monitor} testId={`kanban-monitor-${columnKey}`} />
      </div>
    </section>
  );
}
