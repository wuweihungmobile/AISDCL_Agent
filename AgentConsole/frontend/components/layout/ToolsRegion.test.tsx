import { readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToolsRegion } from "@/components/layout/ToolsRegion";
import type { Role } from "@/lib/api/types";
import { navHref, visibleNavEntries, type NavEntry } from "@/lib/nav/registry";
import { Providers, makeClient, signIn, stubApi } from "@/tests/helpers/api";
import { DELIVERED_MOBILE_LABELS, DELIVERED_NAV_ROWS } from "@/tests/helpers/navDelivered";

/**
 * Tools 區只消費導覽登記表（TCS-SelfImprovingMirror-P1b R21）：加一列即多一個入口、enabled 與 roles 決定可見、依 order 排序、
 * mobile 旗標落成 max-md:hidden、active 為依序第一個命中的可見項（未知路徑沒有任何 active）。
 * 以 vi.mock 把 NAV_REGISTRY 換成測試的登記表；元件本身不認得任何特定入口。
 * OBS-SI-321 根治：連結數、DOM 順序、max-md:hidden 的集合不再釘「九個連結」——期望值取自登記表自身（visibleNavEntries 與各列的 mobile 欄），
 * 已交付列只有一份共用快照（tests/helpers/navDelivered.ts）；測試標題沿 TCS 字樣不動。登記表在末尾多加一列新功能，本檔不必再改。
 */
const state = vi.hoisted(() => ({ pathname: "/", registry: null as unknown, real: null as unknown }));
vi.mock("next/navigation", () => ({
  usePathname: () => state.pathname,
  useRouter: () => ({ push: () => undefined, replace: () => undefined, back: () => undefined }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("@/lib/nav/registry", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/nav/registry")>();
  state.real = mod.NAV_REGISTRY;
  return {
    ...mod,
    get NAV_REGISTRY() {
      return (state.registry ?? mod.NAV_REGISTRY) as typeof mod.NAV_REGISTRY;
    },
  };
});

const REAL = () => state.real as ReadonlyArray<NavEntry>;
const labelOf = (id: string) => (REAL().find((e) => e.id === id) as NavEntry).label;

/** 沒有專案的列表回應（ToolsRegion 的「我的專案」rail 與目前專案推導會查它）。 */
function stubProjects() {
  stubApi((call) => (call.path === "/api/v1/projects" ? { data: { content: [], page: 0, size: 100, totalElements: 0, totalPages: 0 } } : { data: {} }));
}

function renderTools(role: Role = "OPERATOR", pathname = "/") {
  state.pathname = pathname;
  signIn(role);
  stubProjects();
  return render(
    <Providers client={makeClient()}>
      <ToolsRegion />
    </Providers>,
  );
}

const navLinks = () => within(screen.getByRole("navigation", { name: "主導覽" })).getAllByRole("link");
const labels = () => navLinks().map((a) => a.getAttribute("aria-label"));

/** 在真登記表之外加的測試項（match 預設為不命中）。 */
function extra(patch: Partial<NavEntry> & { id: string; order: number }): NavEntry {
  const icon = REAL()[0].icon;
  return { label: patch.id, icon, href: `/${patch.id}`, match: () => false, enabled: true, mobile: true, ...patch };
}

beforeEach(() => {
  state.registry = null;
  state.pathname = "/";
});

describe("AT_932_6_5 登記表加一列即出現入口，元件原始碼不變", () => {
  it("AT_932_6_5 多出一個名稱為示範功能、href 為 /demo 的連結，位置依 order 在議題中心與系統設定之間，其餘九個連結不變；/demo 時它為 active", () => {
    const demo = extra({ id: "demo", label: "示範功能", href: "/demo", order: 56, mobile: false, match: (p) => p === "/demo" });
    state.registry = [...REAL(), demo];
    renderTools("OPERATOR", "/");
    // 期望序＝真登記表對 OPERATOR 的可見項（已依 order 升冪），示範項插在第一個 order 比它大的項之前（不寫死整串標籤與項數）
    const base = visibleNavEntries(REAL(), "OPERATOR");
    const at = base.findIndex((e) => e.order > demo.order);
    const expected = at === -1 ? [...base, demo] : [...base.slice(0, at), demo, ...base.slice(at)];
    expect(labels()).toEqual(expected.map((e) => e.label));
    const links = navLinks();
    const demoAt = expected.indexOf(demo);
    expect(links[demoAt]).toHaveAttribute("href", "/demo");
    // 位置：在議題中心（order 55）之後、系統設定（order 60）之前
    expect(labels().indexOf("議題中心")).toBeLessThan(demoAt);
    expect(demoAt).toBeLessThan(labels().indexOf("系統設定"));
    // 其餘連結不變（標籤與 href；順序與真登記表的可見項相同）
    const others = links.filter((a) => a.getAttribute("aria-label") !== "示範功能");
    expect(others.map((a) => [a.getAttribute("aria-label"), a.getAttribute("href")])).toEqual(base.map((e) => [e.label, navHref(e, { currentProjectId: null })]));
  });

  it("AT_932_6_5 路徑為 /demo 時該連結的 aria-current 為 page（match 取自登記表那一列）；ToolsRegion.tsx 原始碼不含 demo（沒有任何針對新入口的程式碼）", () => {
    state.registry = [...REAL(), extra({ id: "demo", label: "示範功能", href: "/demo", order: 55, mobile: false, match: (p) => p === "/demo" })];
    renderTools("OPERATOR", "/demo");
    const nav = within(screen.getByRole("navigation", { name: "主導覽" }));
    expect(nav.getByRole("link", { name: "示範功能" })).toHaveAttribute("aria-current", "page");
    expect(navLinks().filter((a) => a.hasAttribute("aria-current"))).toHaveLength(1);
    const source = readFileSync(path.join(process.cwd(), "components", "layout", "ToolsRegion.tsx"), "utf-8");
    expect(source.includes("demo"), "元件原始碼不得針對新入口寫任何程式碼").toBe(false);
  });
});

describe("AT_932_6_6 enabled 為假或角色不符的項目不渲染", () => {
  // 額外項的 order 排在真登記表所有項之後（取最大值再加 1～3），所以不論登記表日後長到多少列，額外項都在 DOM 的最後
  const registry = () => {
    const top = Math.max(...REAL().map((e) => e.order));
    return [
      ...REAL(),
      extra({ id: "off", label: "停用項", order: top + 1, enabled: false }),
      extra({ id: "admin-only", label: "僅管理員", order: top + 2, roles: ["ADMIN"] }),
      extra({ id: "op-admin", label: "操作員以上", order: top + 3, roles: ["OPERATOR", "ADMIN"] }),
    ];
  };
  /** 真登記表對該角色的可見項標籤（enabled 為真、roles 缺或含該角色；依 order 升冪）。 */
  const original = (role: Role) => visibleNavEntries(REAL(), role).map((e) => e.label);

  it.each([
    ["VIEWER", []],
    ["OPERATOR", ["操作員以上"]],
    ["ADMIN", ["僅管理員", "操作員以上"]],
  ] as Array<[Role, string[]]>)("AT_932_6_6 %s 看得到的額外項：%j；roles 缺的既有九項三種角色都看得到；被隱藏的項目不在 DOM（不是 CSS 隱藏）", (role, visibleExtras) => {
    state.registry = registry();
    renderTools(role);
    expect(labels()).toEqual([...original(role), ...visibleExtras]);
    // roles 缺且 enabled 為真的既有項，三種角色都看得到（已交付的九項即屬此類）
    for (const e of REAL().filter((x) => x.enabled && x.roles === undefined)) expect(labels(), `${e.label} 三種角色都看得到`).toContain(e.label);
    for (const [, label] of DELIVERED_NAV_ROWS) expect(labels(), `已交付的 ${label}`).toContain(label);
    const nav = within(screen.getByRole("navigation", { name: "主導覽" }));
    for (const hidden of ["停用項", "僅管理員", "操作員以上"].filter((l) => !visibleExtras.includes(l))) {
      expect(nav.queryByRole("link", { name: hidden }), hidden).toBeNull();
      expect(screen.queryByText(hidden), `${hidden} 不得出現在 DOM（以 CSS 隱藏也不行）`).toBeNull();
    }
  });
});

describe("AT_932_6_7 入口依 order 升冪，同序依登記表原序", () => {
  it("AT_932_6_7 亂序提供的登記表：DOM 順序為 order 升冪；order 相同的兩項保持登記表原序；把某一項的 order 改成最小值後它移到最前", () => {
    const t2 = extra({ id: "t2", label: "同序後者", order: 35 });
    const t1 = extra({ id: "t1", label: "同序前者", order: 35 });
    // 陣列順序刻意打亂：t2 排在 t1 之前（同序者依登記表原序，所以 DOM 先 t2 後 t1）
    state.registry = [REAL()[5], t2, REAL()[0], REAL()[6], t1, REAL()[3], REAL()[1], REAL()[4], REAL()[2]];
    const view = renderTools();
    expect(labels()).toEqual(["儀表板", "專案管理", "BRD/PRD 匯入", "同序後者", "同序前者", "執行中心", "監控中心", "系統設定", "自我進化"]);
    view.unmount();

    // 改 order 即移動：把「系統設定」的 order 改成最小值
    state.registry = REAL().map((e) => (e.id === "settings" ? { ...e, order: 1 } : e));
    renderTools();
    expect(labels()[0]).toBe("系統設定");
    expect(labels()).toHaveLength(visibleNavEntries(REAL(), "OPERATOR").length);
  });
});

describe("AT_932_6_8 mobile 旗標以 max-md:hidden 落實", () => {
  const classOf = (label: string) => (within(screen.getByRole("navigation", { name: "主導覽" })).getByRole("link", { name: label }).className ?? "").split(/\s+/);

  it("AT_932_6_8 九個連結都在 DOM；只有 mobile 為 false 的自我進化、議題中心與系統管理帶 max-md:hidden；aria-label 與 title 恆等於 label", () => {
    renderTools();
    // 每個可見的登記項一個連結（不寫死項數）；已交付的九項都在 DOM
    expect(navLinks()).toHaveLength(visibleNavEntries(REAL(), "OPERATOR").length);
    for (const [, label] of DELIVERED_NAV_ROWS) expect(labels(), `已交付的 ${label} 在 DOM`).toContain(label);
    const mobileOf = (label: string) => (REAL().find((e) => e.label === label) as NavEntry).mobile;
    for (const link of navLinks()) {
      const label = link.getAttribute("aria-label");
      expect(link.getAttribute("title")).toBe(label);
      expect(link.textContent).toBe(label);
      // max-md:hidden 恰在登記表 mobile 為 false 的項上
      expect(classOf(label as string).includes("max-md:hidden"), `${label} 的 max-md:hidden`).toBe(mobileOf(label as string) === false);
    }
    // 已交付列：自我進化、議題中心、系統管理（mobile 為 false）帶 max-md:hidden，其餘六項不帶
    for (const [, label, , mobile] of DELIVERED_NAV_ROWS) expect(classOf(label).includes("max-md:hidden"), `已交付的 ${label}（mobile ${String(mobile)}）`).toBe(!mobile);
  });

  // TCS-SysAdminBackup-20261027 AT-BK-01-3-1（R-BK-03）：真登記表的九個連結；<768 的底部 Tab 不顯示的恰為三項，ToolsRegion.tsx 本身不認得任何特定入口（G-C3 另以 git diff 零差異鎖住）
  it("AT_BK_01_3_1 真登記表渲染 Tools 區：九個連結皆在 DOM；帶 max-md:hidden 的恰為自我進化、議題中心、系統管理三項，其餘六項不帶；每個連結的 aria-label 與 title 恆等於其 label；元件原始碼不含系統管理的任何字樣", () => {
    renderTools("VIEWER");
    const links = navLinks();
    const visible = visibleNavEntries(REAL(), "VIEWER");
    expect(links).toHaveLength(visible.length);
    const hidden = links.filter((a) => classOf(a.getAttribute("aria-label") as string).includes("max-md:hidden")).map((a) => a.getAttribute("aria-label"));
    // 帶 max-md:hidden 的恰為登記表 mobile 為 false 的項；已交付的三項（自我進化、議題中心、系統管理）在其中
    expect([...hidden].sort()).toEqual(
      visible
        .filter((e) => !e.mobile)
        .map((e) => e.label)
        .sort(),
    );
    expect(hidden).toEqual(expect.arrayContaining(DELIVERED_NAV_ROWS.filter((row) => !row[3]).map((row) => row[1])));
    // 其餘（mobile 為 true）依顯示序：登記表可見項的 mobile 為 true 者，也就是已交付的六項
    const shown = links.filter((a) => !classOf(a.getAttribute("aria-label") as string).includes("max-md:hidden")).map((a) => a.getAttribute("aria-label"));
    expect(shown).toEqual(visible.filter((e) => e.mobile).map((e) => e.label));
    expect(shown).toEqual(DELIVERED_MOBILE_LABELS);
    for (const link of links) {
      expect(link.getAttribute("title")).toBe(link.getAttribute("aria-label"));
      expect(link.textContent).toBe(link.getAttribute("aria-label"));
    }
    expect(within(screen.getByRole("navigation", { name: "主導覽" })).getByRole("link", { name: "系統管理" })).toHaveAttribute("href", "/sysadmin");
    const source = readFileSync(path.join(process.cwd(), "components", "layout", "ToolsRegion.tsx"), "utf-8");
    expect(source.includes("系統管理") || source.includes("sysadmin"), "ToolsRegion.tsx 是登記表驅動：不得針對新入口寫任何字樣").toBe(false);
  });

  it("AT_932_6_8 替身登記表把自我進化的 mobile 改為 true 後它不再帶 max-md:hidden；把既有項改為 false 後它帶；aria-label 與 title 不隨 mobile 改變", () => {
    state.registry = REAL().map((e) => (e.id === "self-improving" ? { ...e, mobile: true } : e.id === "import" ? { ...e, mobile: false } : e));
    renderTools();
    expect(classOf("自我進化")).not.toContain("max-md:hidden");
    expect(classOf("BRD/PRD 匯入")).toContain("max-md:hidden");
    expect(classOf("儀表板")).not.toContain("max-md:hidden");
    const imp = within(screen.getByRole("navigation", { name: "主導覽" })).getByRole("link", { name: "BRD/PRD 匯入" });
    expect(imp.getAttribute("title")).toBe("BRD/PRD 匯入");
    expect(imp.getAttribute("aria-label")).toBe("BRD/PRD 匯入");
  });
});

describe("AT_932_6_9 active 依序第一個命中，未知路徑不亮任何項", () => {
  const PATHS: Array<[string, string]> = [
    ["/", "dashboard"],
    ["/projects", "projects"],
    ["/projects/new", "projects"],
    ["/projects/p1", "projects"],
    ["/projects/p1/goals", "projects"],
    ["/projects/p1/execute", "execute"],
    ["/projects/p1/monitor", "monitor"],
    ["/import", "import"],
    ["/settings", "settings"],
    ["/settings/x", "settings"],
    ["/self-improving", "self-improving"],
    ["/self-improving/x", "self-improving"],
    ["/self-improving-x", "none"],
    ["/projects-x", "none"],
    ["/unknown", "none"],
    ["/api/health", "none"],
  ];

  it.each(PATHS)("AT_932_6_9 路徑 %s：aria-current 恰在 %s", (pathname, expected) => {
    renderTools("OPERATOR", pathname);
    const current = navLinks().filter((a) => a.hasAttribute("aria-current"));
    if (expected === "none") {
      // 尤其不是專案管理（舊行為的 fallback 已取消）
      expect(current).toHaveLength(0);
    } else {
      expect(current.map((a) => a.getAttribute("aria-label"))).toEqual([labelOf(expected)]);
      expect(current[0]).toHaveAttribute("aria-current", "page");
    }
  });

  it("AT_932_6_9 /login 時沒有主導覽；/projects/p2/goals 時專案管理為 active、執行中心指向網址中的專案（沿舊測試語意）", () => {
    const view = renderTools("OPERATOR", "/login");
    expect(screen.queryByRole("navigation", { name: "主導覽" })).toBeNull();
    view.unmount();
    renderTools("ADMIN", "/projects/p2/goals");
    const nav = within(screen.getByRole("navigation", { name: "主導覽" }));
    expect(nav.getByRole("link", { name: "專案管理" })).toHaveAttribute("aria-current", "page");
    expect(nav.getByRole("link", { name: "執行中心" })).toHaveAttribute("href", "/projects/p2/execute");
    expect(nav.getByRole("link", { name: "監控中心" })).toHaveAttribute("href", "/projects/p2/monitor");
  });
});
