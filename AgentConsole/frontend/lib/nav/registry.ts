/**
 * 導覽登記表（TCS-SelfImprovingMirror-P1b R20、R21；Architecture §5.4；PRD ADR-SI-13）：Tools 區的每個入口都是這裡的一列，
 * `components/layout/ToolsRegion.tsx` 只消費這張表（不持有入口常數、不寫路徑分支）——**新增功能的導覽入口只加一列，不改任何元件**。
 *
 * 規則（元件端用下面三個以登記表為參數的純函式，測試可注入自訂登記表）：
 *  - 可見項＝`enabled` 為真，且（`roles` 缺，或 `roles` 含目前角色；角色未知時帶 `roles` 的項不可見）；依 `order` 升冪，同序依登記表原序；
 *  - active＝在可見項中依序第一個 `match(pathname)` 為真者，沒有命中就沒有任何項 active——**未知路徑不 fallback 成「專案管理」**（舊行為的改變，
 *    PRD AC-SI-32-6 (f)；所以 `projects` 必須明寫自己的判斷式，並排除 execute／monitor 以免被它吃掉）；
 *  - `mobile` 為 false 的項在 <768 的底部 Tab 不顯示（元件以 `max-md:hidden` 隱藏，DOM 內仍在）；`mobile` 為 true 的項數不得超過 6；
 *  - `href` 為字串直取、為函式則以 `{ currentProjectId }` 呼叫（執行／監控都從專案進入，沒有專案時退回專案列表）。
 * registry.test.ts 鎖：九項內容、每列 href 對應存在的 app/**\/page.tsx、match 對代表路徑互斥、ToolsRegion 只消費、舊六項行為不變。
 */
import { Activity, Database, Dna, FolderOpen, LayoutDashboard, ListChecks, Play, Settings, Upload, type LucideIcon } from "lucide-react";

import type { Role } from "@/lib/api/types";

export type NavCtx = { currentProjectId: string | null };

export type NavEntry = {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string | ((ctx: NavCtx) => string);
  match: (pathname: string) => boolean;
  order: number;
  /** 缺＝所有已登入角色皆可見 */
  roles?: ReadonlyArray<Role>;
  enabled: boolean;
  /** false＝<768 的底部 Tab 不顯示（其餘兩種形態照常顯示） */
  mobile: boolean;
};

const EXECUTE = /^\/projects\/[^/]+\/execute/;
const MONITOR = /^\/projects\/[^/]+\/monitor/;

export const NAV_REGISTRY: ReadonlyArray<NavEntry> = [
  { id: "dashboard", label: "儀表板", icon: LayoutDashboard, href: "/", match: (pathname) => pathname === "/", order: 10, enabled: true, mobile: true },
  {
    id: "projects",
    label: "專案管理",
    icon: FolderOpen,
    href: "/projects",
    // 以 /projects 全等或 /projects/ 起頭；排除 /projects/<id>/execute 與 /projects/<id>/monitor，讓它們在「第一個命中者」規則下不被專案管理吃掉（/projects-x 不命中）
    match: (pathname) => (pathname === "/projects" || pathname.startsWith("/projects/")) && !EXECUTE.test(pathname) && !MONITOR.test(pathname),
    order: 20,
    enabled: true,
    mobile: true,
  },
  { id: "import", label: "BRD/PRD 匯入", icon: Upload, href: "/import", match: (pathname) => pathname.startsWith("/import"), order: 30, enabled: true, mobile: true },
  {
    id: "execute",
    label: "執行中心",
    icon: Play,
    // 執行／監控都從專案進入；沒有任何專案時退回專案列表
    href: (ctx) => (ctx.currentProjectId ? `/projects/${ctx.currentProjectId}/execute` : "/projects"),
    match: (pathname) => EXECUTE.test(pathname),
    order: 40,
    enabled: true,
    mobile: true,
  },
  {
    id: "monitor",
    label: "監控中心",
    icon: Activity,
    href: (ctx) => (ctx.currentProjectId ? `/projects/${ctx.currentProjectId}/monitor` : "/projects"),
    match: (pathname) => MONITOR.test(pathname),
    order: 50,
    enabled: true,
    mobile: true,
  },
  { id: "settings", label: "系統設定", icon: Settings, href: "/settings", match: (pathname) => pathname.startsWith("/settings"), order: 60, enabled: true, mobile: true },
  // 第七項：自我進化（P1b）。底部 Tab 已有六項，所以 mobile 為 false（768 以上兩種形態照常顯示）
  {
    id: "self-improving",
    label: "自我進化",
    icon: Dna,
    href: "/self-improving",
    match: (pathname) => pathname === "/self-improving" || pathname.startsWith("/self-improving/"),
    order: 70,
    enabled: true,
    mobile: false,
  },
  // 第八項：議題中心（TCS-IssueCenter-20261027 R-IC-62）。加在陣列**末尾**（原七列的陣列位置與索引不變，`NAV_REGISTRY[6]` 仍是 self-improving）；
  // 顯示序由 order 決定：55 介於監控中心 50 與系統設定 60，所以排在自我進化（70）之前。底部 Tab 已有六項，所以 mobile 為 false（先例同 self-improving）。
  {
    id: "issues",
    label: "議題中心",
    icon: ListChecks,
    href: "/issues",
    match: (pathname) => pathname === "/issues" || pathname.startsWith("/issues/"),
    order: 55,
    enabled: true,
    mobile: false,
  },
  // 第九項：系統管理（TCS-SysAdminBackup-20261027 R-BK-01）。同樣加在陣列**末尾**（原八列的陣列位置與索引不變，`NAV_REGISTRY[6]` 仍是 self-improving、`[7]` 仍是 issues）；
  // 顯示序由 order 決定：65 介於系統設定 60 與自我進化 70，所以排在系統設定之後、自我進化之前。底部 Tab 已有六項，所以 mobile 為 false（先例同 self-improving、issues）。
  // 圖示 Database（與 DatabaseBackup 互異；九個圖示皆不重複）。
  {
    id: "sysadmin",
    label: "系統管理",
    icon: Database,
    href: "/sysadmin",
    match: (pathname) => pathname === "/sysadmin" || pathname.startsWith("/sysadmin/"),
    order: 65,
    enabled: true,
    mobile: false,
  },
];

/** 目前角色看得到的入口，依 order 升冪（同序依登記表原序：Array.prototype.sort 是穩定排序）。回傳新陣列，不改動傳入的登記表。 */
export function visibleNavEntries(registry: ReadonlyArray<NavEntry>, role: Role | undefined): NavEntry[] {
  return registry.filter((entry) => entry.enabled && (entry.roles === undefined || (role !== undefined && entry.roles.includes(role)))).sort((a, b) => a.order - b.order);
}

/** 目前路徑 active 的入口：可見項中依序第一個 match 為真者；沒有命中回 null（沒有任何項 active）。 */
export function activeNavEntry(visible: ReadonlyArray<NavEntry>, pathname: string): NavEntry | null {
  return visible.find((entry) => entry.match(pathname)) ?? null;
}

export function navHref(entry: NavEntry, ctx: NavCtx): string {
  return typeof entry.href === "string" ? entry.href : entry.href(ctx);
}
