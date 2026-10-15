import { ArrowLeft, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** 「← 返回…」連結（設計稿：14px、muted、左箭頭 16px，下距 14px）。 */
export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="mb-3.5 inline-flex items-center gap-1.5 text-sm text-wg-muted transition-colors hover:text-wg-primary">
      <ArrowLeft size={16} aria-hidden />
      {children}
    </Link>
  );
}

/**
 * 頁面標題列（設計稿：H2 30px／700＋副標 15px muted；右側放主要動作）。
 * icon＝標題前的 26px 主色線性圖示（執行／監控／設定頁）。
 */
export function PageTitle({ title, subtitle, icon: Icon, actions, className }: { title: ReactNode; subtitle?: ReactNode; icon?: LucideIcon; actions?: ReactNode; className?: string }) {
  return (
    <div className={cn("mb-5 flex flex-wrap items-end justify-between gap-4", className)}>
      <div>
        <h2 className="flex items-center gap-2.5 text-[30px] font-bold max-md:text-2xl">
          {Icon ? <Icon size={26} className="shrink-0 text-wg-primary" aria-hidden /> : null}
          {title}
        </h2>
        {subtitle ? <p className="mt-1 text-[15px] text-wg-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2.5">{actions}</div> : null}
    </div>
  );
}
