import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * 超大扁平分頁器（設計稿：44px 方鈕、8px 圓角；目前頁＝主色底白字，其餘透明＋muted 字）。
 * page 以 1 起算（後端是 0 起算，換算由呼叫端負責）。
 */
export function Pagination({ page, totalPages, onPageChange, className }: { page: number; totalPages: number; onPageChange: (page: number) => void; className?: string }) {
  const pages = Array.from({ length: Math.max(1, totalPages) }, (_, i) => i + 1);
  const btn = "inline-flex size-11 cursor-pointer items-center justify-center rounded-md border-none text-xl transition-colors disabled:cursor-not-allowed disabled:opacity-40";
  return (
    <nav aria-label="分頁" className={cn("flex items-center justify-center gap-3", className)} data-slot="pagination">
      <button type="button" aria-label="上一頁" className={cn(btn, "bg-transparent text-wg-muted hover:text-wg-primary")} disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        <ChevronLeft size={22} aria-hidden />
      </button>
      {pages.map((n) => (
        <button
          key={n}
          type="button"
          aria-label={`第 ${n} 頁`}
          aria-current={n === page ? "page" : undefined}
          className={cn(btn, n === page ? "bg-wg-primary text-white" : "bg-transparent text-wg-muted hover:text-wg-primary")}
          onClick={() => onPageChange(n)}
        >
          {n}
        </button>
      ))}
      <button type="button" aria-label="下一頁" className={cn(btn, "bg-transparent text-wg-muted hover:text-wg-primary")} disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
        <ChevronRight size={22} aria-hidden />
      </button>
    </nav>
  );
}
