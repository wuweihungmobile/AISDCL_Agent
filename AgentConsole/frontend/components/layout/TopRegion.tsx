"use client";

/**
 * Top 區（UI-LAY-01）＝設計稿 Topbar 公告列＋Masthead 主導覽列。
 * 全站唯一一份：由 app/layout.tsx 組裝，任何頁面不得自帶（Architecture §5.2 硬規則）。
 *  - 公告列：說明文件／下載 CLI／GitHub／Engine Bridge 狀態；通知總覽／幫助中心／語言／使用者（含登出）。
 *  - Masthead：logo、搜尋列（Enter 或按鈕 → /projects?q=）、最近專案 chips、通知鈴、signoff 佇列鈕、「本頁說明」鈕（右側群組末端，只在已登入的分支內；見 PageHelpButton）。
 *    鈴與 signoff 鈕的徽章都來自 GET /notifications/summary（每 30 秒輪詢）：
 *    pendingSignoffs → signoff 鈕；pendingReviews＋unacknowledgedAlerts → 鈴（點開看三個數字，見 NotificationBell）。
 *  - 未登入（/login）只顯示品牌列，不顯示搜尋與動作。
 */
import { Bell, Bot, CircleHelp, ClipboardCheck, Globe, LogOut, Search } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { NotificationBell } from "@/components/domain/notifications/NotificationBell";
import { CountBadge } from "@/components/ui/badge";
import { SERVICE_LABEL, useBridgeStatus } from "@/hooks/useServiceStatus";
import { useAllProjects, useNotificationSummary } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { cn } from "@/lib/utils";

// 「本頁說明」鈕以 next/dynamic 載入（TCS-PageHelp D-PH-17）：說明文字本體、狀態釋義與對話框不進每條路由的首屏
const PageHelpButton = dynamic(() => import("@/components/domain/help/PageHelpButton").then((m) => m.PageHelpButton));

const SEP = <span className="opacity-35 max-md:hidden">|</span>;

export function TopRegion() {
  const pathname = usePathname();
  const router = useRouter();
  const { status, username, logout } = useAuth();
  const all = useAllProjects();
  const summary = useNotificationSummary();
  const pendingSignoffs = summary.data?.pendingSignoffs ?? 0;
  const bridge = useBridgeStatus();
  const [query, setQuery] = useState("");

  const isLogin = pathname === "/login";
  const authed = status === "authed";
  const showTools = !isLogin && status !== "anon";
  const recent = (all.data?.content ?? []).slice(0, 6);

  function submitSearch(e?: FormEvent) {
    e?.preventDefault();
    const q = query.trim();
    router.push(q ? `/projects?q=${encodeURIComponent(q)}` : "/projects");
  }

  return (
    <header data-region="top" className="shrink-0">
      {/* ░░ Topbar 公告列 ░░ */}
      <div className="h-[34px] bg-wg-topbar text-[length:var(--fs-caption)] text-white">
        <div className="mx-auto flex h-full max-w-[var(--container-max)] items-center justify-between px-6 max-md:px-4">
          <div className="flex items-center gap-4 opacity-95">
            <span className="max-md:hidden">說明文件</span>
            {SEP}
            <span className="max-md:hidden">下載 CLI</span>
            {SEP}
            <span className="max-md:hidden">GitHub</span>
            {SEP}
            <span className="opacity-80">Engine Bridge · {SERVICE_LABEL[bridge]}</span>
            <span aria-hidden className={cn("inline-block size-[7px] rounded-full", bridge === "online" ? "bg-wg-online" : "bg-white/40")} />
          </div>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5 max-md:hidden">
              <Bell size={14} aria-hidden />
              通知總覽
            </span>
            {SEP}
            <span className="inline-flex items-center gap-1.5 max-md:hidden">
              <CircleHelp size={14} aria-hidden />
              幫助中心
            </span>
            {SEP}
            <span className="inline-flex items-center gap-1.5 max-md:hidden">
              <Globe size={14} aria-hidden />
              繁體中文
            </span>
            {authed ? (
              <>
                {SEP}
                <span className="inline-flex items-center gap-1.5" data-testid="user-badge">
                  <span aria-hidden className="inline-flex size-[18px] items-center justify-center rounded-full bg-white text-[11px] font-semibold text-wg-primary">
                    {username.charAt(0).toUpperCase()}
                  </span>
                  {username}
                </span>
                {SEP}
                <button type="button" onClick={logout} className="inline-flex cursor-pointer items-center gap-1.5 border-none bg-transparent p-0 text-inherit transition-opacity hover:opacity-85">
                  <LogOut size={14} aria-hidden />
                  登出
                </button>
              </>
            ) : null}
          </div>
        </div>
      </div>

      {/* ░░ Masthead 主導覽列 ░░ */}
      <div className="bg-wg-header">
        <div className="mx-auto flex max-w-[var(--container-max)] items-center gap-8 px-6 pt-[18px] pb-4 max-md:flex-wrap max-md:gap-x-4 max-md:gap-y-3 max-md:px-4">
          {/* 名稱要含可見文字（WCAG 2.5.3 Label in Name；axe label-content-name-mismatch）：可見的是「AISDLC Console AGENT CONTROL PANEL」，再補一個「首頁」說明去處 */}
          <Link href="/" aria-label="AISDLC Console AGENT CONTROL PANEL 首頁" className="flex shrink-0 items-center gap-3 text-white">
            <span className="inline-flex size-[46px] items-center justify-center rounded-xl bg-white">
              <Bot size={28} className="text-wg-primary" aria-hidden />
            </span>
            <span className="flex flex-col items-start leading-[1.15]">
              {/* 兩段字之間放一個空白字元：版面上沒有差別（flex 欄的空白節點不佔位），但可見文字串起來才是「AISDLC Console AGENT CONTROL PANEL」，
                  名稱含可見文字的比對（axe label-content-name-mismatch）才認得 */}
              <span className="text-[21px] font-bold tracking-[0.3px]">AISDLC Console</span> {/* 主色底上的小字一律純白：任何 alpha／opacity 都會把對比壓到 4.5:1 以下（#498428 底，純白 4.55:1） */}
              <span className="text-[11px] tracking-[2px]">AGENT CONTROL PANEL</span>
            </span>
          </Link>

          {showTools ? (
            <>
              <div className="flex max-w-[760px] flex-1 flex-col gap-1.5 max-md:order-last max-md:basis-full">
                <form role="search" onSubmit={submitSearch} className="flex h-[46px] items-stretch overflow-hidden rounded-md bg-white">
                  {/* 焦點環沿用全域 :focus-visible；容器 overflow-hidden 會裁掉外擴的環，所以 offset 改 -2px 讓環畫在輸入框內側 */}
                  <input
                    type="search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="搜尋專案、目標、任務…"
                    aria-label="搜尋專案、目標、任務"
                    className="min-w-0 flex-1 border-none bg-transparent px-[18px] text-sm text-wg-text placeholder:text-wg-muted focus-visible:outline-offset-[-2px]"
                  />
                  <button
                    type="submit"
                    aria-label="搜尋"
                    className="flex cursor-pointer items-center justify-center border-none bg-wg-primary px-[26px] text-white transition-colors hover:bg-wg-primary-strong"
                  >
                    <Search size={20} aria-hidden />
                  </button>
                </form>
                {recent.length > 0 ? (
                  <nav aria-label="最近專案" className="flex flex-wrap gap-x-[18px] text-xs text-white">
                    {recent.map((p) => (
                      <Link key={p.id} href={`/projects/${p.id}`} className="transition-opacity hover:opacity-85">
                        {p.name}
                      </Link>
                    ))}
                  </nav>
                ) : null}
              </div>

              <div className="flex shrink-0 items-center gap-2.5">
                <NotificationBell summary={summary.data} />
                <Link
                  href="/#pending-signoff"
                  // 徽章上的可見數字必須出現在名稱裡（Label in Name）；括號會讓 axe 認不出數字，所以用空格分隔
                  aria-label={`待審批佇列 ${pendingSignoffs} 筆`}
                  title="待審批佇列"
                  className="relative inline-flex size-[52px] items-center justify-center rounded-full bg-white/[0.14] text-white transition-opacity hover:opacity-85"
                >
                  <ClipboardCheck size={26} aria-hidden />
                  {pendingSignoffs > 0 ? <CountBadge count={pendingSignoffs} size="lg" floating className="-top-0.5 -right-1" data-testid="signoff-badge" /> : null}
                </Link>
                <PageHelpButton />
              </div>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}
