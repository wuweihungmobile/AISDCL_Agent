"use client";

/**
 * Tools 區（UI-LAY-02）＝設計稿 Sidebar：導覽入口＋「我的專案」rail。全站唯一一份，由 app/layout.tsx 組裝。
 * 導覽入口一律取自 lib/nav/registry.ts 的登記表（本檔只消費：可見項、排序、active、href、<768 是否顯示都由登記表與其純函式決定）——
 * 新增功能的入口只加登記表一列，不改這個元件。
 * 響應式（PRD §8.3，三種形態都在本檔切換，不另開元件檔）：
 *   ≥1280：240px 完整側欄；768～1279：64px 圖示側欄（標籤改 title／aria-label，rail 隱藏）；
 *   <768：底部 Tab 導航（由 app/layout.tsx 的 flex-col-reverse 把本區塊排到內容下方；登記表 mobile 為 false 的入口以 max-md:hidden 隱藏）。
 * 側欄背景透明、無卡片無邊框（融入頁面底色）；active 項＝左側 4px 主色條＋tertiary 底。
 */
import { LayoutGrid } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { StatusDot } from "@/components/ui/status-dot";
import { useCurrentProjectId } from "@/hooks/useCurrentProjectId";
import { useAllProjects } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { projectStatus } from "@/lib/domain/status";
import { NAV_REGISTRY, activeNavEntry, navHref, visibleNavEntries } from "@/lib/nav/registry";
import { cn } from "@/lib/utils";

export function ToolsRegion() {
  const pathname = usePathname();
  const { status, role } = useAuth();
  const all = useAllProjects();
  const currentId = useCurrentProjectId();

  if (pathname === "/login" || status === "anon") return null;
  // 水合前保留版面寬度，避免已登入者重新整理時內容橫向跳動
  if (status === "loading") {
    return <aside data-region="tools" aria-hidden className="w-60 shrink-0 max-xl:w-16 max-md:hidden" />;
  }

  const entries = visibleNavEntries(NAV_REGISTRY, role);
  const active = activeNavEntry(entries, pathname);
  const rail = (all.data?.content ?? []).slice(0, 6);

  return (
    <aside
      data-region="tools"
      className={cn(
        "shrink-0 overflow-y-auto pr-1",
        "w-60 max-xl:w-16",
        "max-md:w-full max-md:overflow-x-auto max-md:overflow-y-hidden max-md:border-t max-md:border-wg-line max-md:bg-wg-surface max-md:p-0",
      )}
    >
      <div className="flex items-center gap-2 px-3 pt-1.5 pb-3.5 text-wg-text max-xl:hidden">
        <LayoutGrid size={20} aria-hidden />
        <span className="text-lg font-semibold">導航</span>
      </div>
      <hr className="mb-2 h-px border-0 bg-wg-line max-xl:hidden" />

      <nav aria-label="主導覽" className="max-md:flex max-md:justify-around">
        {entries.map((entry) => {
          const isActive = active?.id === entry.id;
          const Icon = entry.icon;
          return (
            <Link
              key={entry.id}
              href={navHref(entry, { currentProjectId: currentId })}
              aria-label={entry.label}
              aria-current={isActive ? "page" : undefined}
              title={entry.label}
              className={cn(
                "flex w-full items-center gap-2.5 border-l-4 px-3 py-[11px] text-left text-base font-medium text-wg-text transition-colors",
                "hover:bg-wg-tertiary max-xl:justify-center max-xl:px-0",
                "max-md:flex-1 max-md:flex-col max-md:gap-0.5 max-md:border-l-0 max-md:border-t-4 max-md:px-1 max-md:py-2",
                isActive ? "border-wg-primary bg-wg-tertiary" : "border-transparent bg-transparent",
                // 登記表 mobile 為 false 的入口：<768 的底部 Tab 不顯示（DOM 內仍在，768 以上兩種形態照常顯示）
                !entry.mobile && "max-md:hidden",
              )}
            >
              <Icon size={18} aria-hidden className="max-md:size-5" />
              <span className="max-xl:hidden max-md:inline max-md:text-[10px] max-md:leading-tight">{entry.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-5 max-xl:hidden" data-testid="project-rail">
        <div className="px-3 pt-1.5 pb-2.5 text-xs tracking-[1px] text-wg-muted uppercase">我的專案</div>
        <hr className="mb-1 h-px border-0 bg-wg-line" />
        {rail.length === 0 ? (
          <p className="px-3 py-2.5 text-[13px] text-wg-muted">尚無專案</p>
        ) : (
          rail.map((p) => (
            <Link
              key={p.id}
              href={`/projects/${p.id}`}
              className="flex w-full items-center gap-2.5 border-l-4 border-transparent px-3 py-[9px] text-left text-sm text-wg-text transition-colors hover:bg-wg-tertiary"
            >
              <StatusDot color={projectStatus(p.status).color} />
              <span className="truncate">{p.name}</span>
            </Link>
          ))
        )}
      </div>
    </aside>
  );
}
