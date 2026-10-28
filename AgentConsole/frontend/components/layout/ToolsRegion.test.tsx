import { readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToolsRegion } from "@/components/layout/ToolsRegion";
import type { Role } from "@/lib/api/types";
import type { NavEntry } from "@/lib/nav/registry";
import { Providers, makeClient, signIn, stubApi } from "@/tests/helpers/api";

/**
 * Tools 區只消費導覽登記表（TCS-SelfImprovingMirror-P1b R21）：加一列即多一個入口、enabled 與 roles 決定可見、依 order 排序、
 * mobile 旗標落成 max-md:hidden、active 為依序第一個命中的可見項（未知路徑沒有任何 active）。
 * 以 vi.mock 把 NAV_REGISTRY 換成測試的登記表；元件本身不認得任何特定入口。
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
    expect(labels()).toEqual(["儀表板", "專案管理", "BRD/PRD 匯入", "執行中心", "監控中心", "議題中心", "示範功能", "系統設定", "系統管理", "自我進化"]);
    const links = navLinks();
    expect(links[6]).toHaveAttribute("href", "/demo");
    // 其餘九個連結不變（標籤與 href）
    const others = links.filter((a) => a.getAttribute("aria-label") !== "示範功能");
    expect(others.map((a) => [a.getAttribute("aria-label"), a.getAttribute("href")])).toEqual([
      ["儀表板", "/"],
      ["專案管理", "/projects"],
      ["BRD/PRD 匯入", "/import"],
      ["執行中心", "/projects"],
      ["監控中心", "/projects"],
      ["議題中心", "/issues"],
      ["系統設定", "/settings"],
      ["系統管理", "/sysadmin"],
      ["自我進化", "/self-improving"],
    ]);
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
  const registry = () => [
    ...REAL(),
    extra({ id: "off", label: "停用項", order: 71, enabled: false }),
    extra({ id: "admin-only", label: "僅管理員", order: 72, roles: ["ADMIN"] }),
    extra({ id: "op-admin", label: "操作員以上", order: 73, roles: ["OPERATOR", "ADMIN"] }),
  ];
  const original = ["儀表板", "專案管理", "BRD/PRD 匯入", "執行中心", "監控中心", "議題中心", "系統設定", "系統管理", "自我進化"];

  it.each([
    ["VIEWER", []],
    ["OPERATOR", ["操作員以上"]],
    ["ADMIN", ["僅管理員", "操作員以上"]],
  ] as Array<[Role, string[]]>)("AT_932_6_6 %s 看得到的額外項：%j；roles 缺的既有九項三種角色都看得到；被隱藏的項目不在 DOM（不是 CSS 隱藏）", (role, visibleExtras) => {
    state.registry = registry();
    renderTools(role);
    expect(labels()).toEqual([...original, ...visibleExtras]);
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
    expect(labels()).toHaveLength(9);
  });
});

describe("AT_932_6_8 mobile 旗標以 max-md:hidden 落實", () => {
  const classOf = (label: string) => (within(screen.getByRole("navigation", { name: "主導覽" })).getByRole("link", { name: label }).className ?? "").split(/\s+/);

  it("AT_932_6_8 九個連結都在 DOM；只有 mobile 為 false 的自我進化、議題中心與系統管理帶 max-md:hidden；aria-label 與 title 恆等於 label", () => {
    renderTools();
    expect(navLinks()).toHaveLength(9);
    for (const link of navLinks()) {
      const label = link.getAttribute("aria-label");
      expect(link.getAttribute("title")).toBe(label);
      expect(link.textContent).toBe(label);
      expect(classOf(label as string).includes("max-md:hidden"), `${label} 的 max-md:hidden`).toBe(label === "自我進化" || label === "議題中心" || label === "系統管理");
    }
  });

  // TCS-SysAdminBackup-20261027 AT-BK-01-3-1（R-BK-03）：真登記表的九個連結；<768 的底部 Tab 不顯示的恰為三項，ToolsRegion.tsx 本身不認得任何特定入口（G-C3 另以 git diff 零差異鎖住）
  it("AT_BK_01_3_1 真登記表渲染 Tools 區：九個連結皆在 DOM；帶 max-md:hidden 的恰為自我進化、議題中心、系統管理三項，其餘六項不帶；每個連結的 aria-label 與 title 恆等於其 label；元件原始碼不含系統管理的任何字樣", () => {
    renderTools("VIEWER");
    const links = navLinks();
    expect(links).toHaveLength(9);
    const hidden = links.filter((a) => classOf(a.getAttribute("aria-label") as string).includes("max-md:hidden")).map((a) => a.getAttribute("aria-label"));
    expect(hidden.sort()).toEqual(["自我進化", "議題中心", "系統管理"].sort());
    const shown = links.filter((a) => !classOf(a.getAttribute("aria-label") as string).includes("max-md:hidden")).map((a) => a.getAttribute("aria-label"));
    expect(shown).toEqual(["儀表板", "專案管理", "BRD/PRD 匯入", "執行中心", "監控中心", "系統設定"]);
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
