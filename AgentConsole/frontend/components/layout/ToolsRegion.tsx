"use client";

/**
 * Tools 區（UI-LAY-02）＝設計稿 Sidebar：導航六項＋「我的專案」rail。全站唯一一份，由 app/layout.tsx 組裝。
 * 響應式（PRD §8.3，三種形態都在本檔切換，不另開元件檔）：
 *   ≥1280：240px 完整側欄；768～1279：64px 圖示側欄（標籤改 title／aria-label，rail 隱藏）；
 *   <768：底部 Tab 導航（由 app/layout.tsx 的 flex-col-reverse 把本區塊排到內容下方）。
 * 側欄背景透明、無卡片無邊框（融入頁面底色）；active 項＝左側 4px 主色條＋tertiary 底。
 */
import { Activity, FolderOpen, LayoutDashboard, LayoutGrid, Play, Settings, Upload, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { StatusDot } from "@/components/ui/status-dot";
import { useCurrentProjectId } from "@/hooks/useCurrentProjectId";
import { useAllProjects } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { projectStatus } from "@/lib/domain/status";
import { cn } from "@/lib/utils";

type NavId = "dashboard" | "projects" | "import" | "execute" | "monitor" | "settings";

const NAV: ReadonlyArray<{ id: NavId; label: string; icon: LucideIcon }> = [
  { id: "dashboard", label: "儀表板", icon: LayoutDashboard },
  { id: "projects", label: "專案管理", icon: FolderOpen },
  { id: "import", label: "BRD/PRD 匯入", icon: Upload },
  { id: "execute", label: "執行中心", icon: Play },
  { id: "monitor", label: "監控中心", icon: Activity },
  { id: "settings", label: "系統設定", icon: Settings },
];

function activeNav(pathname: string): NavId {
  if (pathname === "/") return "dashboard";
  if (pathname.startsWith("/import")) return "import";
  if (pathname.startsWith("/settings")) return "settings";
  if (/^\/projects\/[^/]+\/execute/.test(pathname)) return "execute";
  if (/^\/projects\/[^/]+\/monitor/.test(pathname)) return "monitor";
  return "projects";
}

export function ToolsRegion() {
  const pathname = usePathname();
  const { status } = useAuth();
  const all = useAllProjects();
  const currentId = useCurrentProjectId();

  if (pathname === "/login" || status === "anon") return null;
  // 水合前保留版面寬度，避免已登入者重新整理時內容橫向跳動
  if (status === "loading") {
    return <aside data-region="tools" aria-hidden className="w-60 shrink-0 max-xl:w-16 max-md:hidden" />;
  }

  const active = activeNav(pathname);
  const hrefFor = (id: NavId): string => {
    switch (id) {
      case "dashboard":
        return "/";
      case "projects":
        return "/projects";
      case "import":
        return "/import";
      case "settings":
        return "/settings";
      case "execute":
      case "monitor":
        // 執行／監控都從專案進入；沒有任何專案時退回專案列表
        return currentId ? `/projects/${currentId}/${id}` : "/projects";
    }
  };
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
        {NAV.map(({ id, label, icon: Icon }) => {
          const isActive = active === id;
          return (
            <Link
              key={id}
              href={hrefFor(id)}
              aria-label={label}
              aria-current={isActive ? "page" : undefined}
              title={label}
              className={cn(
                "flex w-full items-center gap-2.5 border-l-4 px-3 py-[11px] text-left text-base font-medium text-wg-text transition-colors",
                "hover:bg-wg-tertiary max-xl:justify-center max-xl:px-0",
                "max-md:flex-1 max-md:flex-col max-md:gap-0.5 max-md:border-l-0 max-md:border-t-4 max-md:px-1 max-md:py-2",
                isActive ? "border-wg-primary bg-wg-tertiary" : "border-transparent bg-transparent",
              )}
            >
              <Icon size={18} aria-hidden className="max-md:size-5" />
              <span className="max-xl:hidden max-md:inline max-md:text-[10px] max-md:leading-tight">{label}</span>
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
