import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import type { Role } from "@/lib/api/types";
import { NAV_REGISTRY, activeNavEntry, navHref, visibleNavEntries, type NavEntry } from "./registry";

/**
 * 導覽登記表（TCS-SelfImprovingMirror-P1b R20、R21；Architecture §5.4、ADR-SI-13）：Tools 區的入口全部取自 NAV_REGISTRY，
 * 新增導覽項只加一列、不改任何元件。這裡鎖：登記表的內容、每列 href 都對應真實存在的路由頁、match 對代表路徑互斥、
 * ToolsRegion.tsx 只消費登記表（沒有入口常數與路徑分支），以及舊六項的行為不變（唯一差異：未知路徑不再亮「專案管理」）。
 */
const ROOT = process.cwd();

/** 代表路徑表：每個路徑期望命中的登記項 id（none＝沒有任何項命中）。 */
const PATHS: Array<[pathname: string, expected: string]> = [
  ["/", "dashboard"],
  ["/projects", "projects"],
  ["/projects/new", "projects"],
  ["/projects/p1", "projects"],
  ["/projects/p1/edit", "projects"],
  ["/projects/p1/goals", "projects"],
  ["/projects/p1/goals/g1/tasks/t1/edit", "projects"],
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
  ["/login", "none"],
  ["/api/health", "none"],
  ["", "none"],
];

const ids = (list: ReadonlyArray<NavEntry>) => list.map((e) => e.id);
const probes = PATHS.map(([p]) => p);

// ── app/**/page.tsx → 路由樣式 ───────────────────────────────────────────────

function pageRoutes(): string[][] {
  const routes: string[][] = [];
  const walk = (dir: string, segments: string[]) => {
    for (const name of readdirSync(dir)) {
      const full = path.join(dir, name);
      if (statSync(full).isDirectory()) {
        // 路由群組 (name) 不進網址
        walk(full, /^\(.*\)$/.test(name) ? segments : [...segments, name]);
      } else if (name === "page.tsx") {
        routes.push(segments);
      }
    }
  };
  walk(path.join(ROOT, "app"), []);
  return routes;
}

/** 方括號段為單段萬用；根路由 `/` 的樣式是空陣列。 */
function routeExists(pathname: string, routes: string[][]): boolean {
  const parts = pathname.split("/").filter((s, i) => !(i === 0 && s === ""));
  const concrete = pathname === "/" ? [] : parts;
  return routes.some((pattern) => pattern.length === concrete.length && pattern.every((seg, i) => (/^\[[^\]]+\]$/.test(seg) ? concrete[i] !== "" : seg === concrete[i])));
}

// ── 登記表檢查函式（測試內；對自造的壞登記表要回報）─────────────────────────────────

type Problem = { kind: "duplicate-id" | "duplicate-order" | "bad-order" | "mobile-overflow" | "bad-href" | "match-overlap"; detail: string };

function registryProblems(registry: ReadonlyArray<NavEntry>, pathProbes: ReadonlyArray<string>, routes: string[][]): Problem[] {
  const out: Problem[] = [];
  const seenIds = new Set<string>();
  const seenOrders = new Set<number>();
  for (const e of registry) {
    if (seenIds.has(e.id)) out.push({ kind: "duplicate-id", detail: e.id });
    seenIds.add(e.id);
    if (typeof e.order !== "number" || !Number.isFinite(e.order)) out.push({ kind: "bad-order", detail: `${e.id}：${String(e.order)}` });
    else {
      if (seenOrders.has(e.order)) out.push({ kind: "duplicate-order", detail: `${e.id}：${e.order}` });
      seenOrders.add(e.order);
    }
    const resolved = typeof e.href === "string" ? [e.href] : [e.href({ currentProjectId: null }), e.href({ currentProjectId: "p1" })];
    for (const href of resolved) {
      const pathname = href.split(/[?#]/)[0];
      if (!pathname.startsWith("/") || !routeExists(pathname, routes)) out.push({ kind: "bad-href", detail: `${e.id}：${href}` });
    }
  }
  if (registry.filter((e) => e.mobile === true).length > 6) out.push({ kind: "mobile-overflow", detail: "mobile 為 true 的項超過 6" });
  for (const probe of pathProbes) {
    const hits = registry.filter((e) => e.match(probe));
    if (hits.length > 1) out.push({ kind: "match-overlap", detail: `${probe} 被 ${ids(hits).join("、")} 同時命中` });
  }
  return out;
}

describe("AT_932_6_1 登記表恰七項且欄位值符合 R20", () => {
  it("AT_932_6_1 id、label、order、mobile 依序相符，id 與 order 各自唯一，mobile 為 true 的項數不超過 6", () => {
    expect(NAV_REGISTRY).toHaveLength(7);
    expect(ids(NAV_REGISTRY)).toEqual(["dashboard", "projects", "import", "execute", "monitor", "settings", "self-improving"]);
    expect(NAV_REGISTRY.map((e) => e.label)).toEqual(["儀表板", "專案管理", "BRD/PRD 匯入", "執行中心", "監控中心", "系統設定", "自我進化"]);
    expect(NAV_REGISTRY.map((e) => e.order)).toEqual([10, 20, 30, 40, 50, 60, 70]);
    expect(new Set(ids(NAV_REGISTRY)).size).toBe(7);
    expect(new Set(NAV_REGISTRY.map((e) => e.order)).size).toBe(7);
    expect(NAV_REGISTRY.map((e) => e.mobile)).toEqual([true, true, true, true, true, true, false]);
    expect(NAV_REGISTRY.filter((e) => e.mobile).length).toBeLessThanOrEqual(6);
  });

  it("AT_932_6_1 每項的型別：enabled 為布林、roles 缺或只含三種角色、match 為函式、href 為字串或函式、icon 為 React 元件且七項互異", () => {
    const roles: Role[] = ["ADMIN", "OPERATOR", "VIEWER"];
    for (const e of NAV_REGISTRY) {
      expect(typeof e.enabled, `${e.id}.enabled`).toBe("boolean");
      expect(e.roles === undefined || (Array.isArray(e.roles) && e.roles.every((r) => roles.includes(r))), `${e.id}.roles`).toBe(true);
      expect(typeof e.match, `${e.id}.match`).toBe("function");
      expect(["string", "function"], `${e.id}.href`).toContain(typeof e.href);
      const icon = e.icon as unknown;
      expect(typeof icon === "function" || (typeof icon === "object" && icon !== null && "$$typeof" in icon), `${e.id}.icon 不是 React 元件`).toBe(true);
    }
    expect(new Set(NAV_REGISTRY.map((e) => e.icon)).size).toBe(7);
  });

  it("AT_932_6_1 第七項（自我進化）：href 為 /self-improving、roles 缺、enabled 為 true；execute 與 monitor 的 href(ctx) 無專案時回 /projects、有專案時帶專案 id；其餘五項為字串", () => {
    const seventh = NAV_REGISTRY[6];
    expect(seventh.href).toBe("/self-improving");
    expect(seventh.roles).toBeUndefined();
    expect(seventh.enabled).toBe(true);
    const byId = (id: string) => NAV_REGISTRY.find((e) => e.id === id) as NavEntry;
    for (const id of ["execute", "monitor"]) {
      const entry = byId(id);
      expect(typeof entry.href).toBe("function");
      expect(navHref(entry, { currentProjectId: null })).toBe("/projects");
      expect(navHref(entry, { currentProjectId: "p1" })).toBe(`/projects/p1/${id}`);
    }
    const strings = NAV_REGISTRY.filter((e) => !["execute", "monitor"].includes(e.id));
    expect(strings.map((e) => e.href)).toEqual(["/", "/projects", "/import", "/settings", "/self-improving"]);
  });
});

describe("AT_932_6_2 每列 href 都對應存在的 app/**/page.tsx", () => {
  const routes = pageRoutes();

  it("AT_932_6_2 路由表非空且含 /、/projects、/projects/p1/execute、/self-improving 四個樣式；真登記表的字串與函式型 href 各分支都指向真路由", () => {
    expect(routes.length).toBeGreaterThan(10);
    for (const p of ["/", "/projects", "/projects/p1/execute", "/self-improving"]) expect(routeExists(p, routes), p).toBe(true);
    expect(routeExists("/nope", routes)).toBe(false);
    expect(registryProblems(NAV_REGISTRY, probes, routes)).toEqual([]);
    // 逐項明列：每個解析結果都有對應的路由樣式
    for (const e of NAV_REGISTRY) {
      for (const ctx of [{ currentProjectId: null }, { currentProjectId: "p1" }]) expect(routeExists(navHref(e, ctx).split(/[?#]/)[0], routes), `${e.id} → ${navHref(e, ctx)}`).toBe(true);
    }
  });

  it("AT_932_6_2 檢查函式的負控：指向不存在路由、函式型 href 的任一分支壞掉、空字串 href 都被回報", () => {
    const base = { ...NAV_REGISTRY[0], id: "x", order: 80, mobile: false, match: () => false } satisfies NavEntry;
    const kinds = (entry: NavEntry) => registryProblems([...NAV_REGISTRY, entry], probes, routes).map((p) => p.kind);
    expect(kinds({ ...base, href: "/nope" })).toEqual(["bad-href"]);
    expect(kinds({ ...base, href: (ctx) => (ctx.currentProjectId ? "/nowhere/x" : "/projects") })).toEqual(["bad-href"]);
    expect(kinds({ ...base, href: (ctx) => (ctx.currentProjectId ? "/projects/p1/execute" : "/nowhere") })).toEqual(["bad-href"]);
    expect(kinds({ ...base, href: "" })).toEqual(["bad-href"]);
    expect(kinds({ ...base, href: "/projects?tab=1#x" })).toEqual([]);
  });
});

describe("AT_932_6_3 match 對代表路徑互斥", () => {
  it("AT_932_6_3 每個代表路徑被命中的登記項恰為期望的單一項或無項；沒有路徑被兩項同時命中", () => {
    for (const [pathname, expected] of PATHS) {
      const hits = ids(NAV_REGISTRY.filter((e) => e.match(pathname)));
      expect(hits, `路徑 ${JSON.stringify(pathname)}`).toEqual(expected === "none" ? [] : [expected]);
    }
  });

  it("AT_932_6_3 邊界：/projects/p1/execute 只命中 execute（projects 的 match 對它為假）；/self-improving-x 與 /projects-x 不命中任何項", () => {
    const entry = (id: string) => NAV_REGISTRY.find((e) => e.id === id) as NavEntry;
    expect(entry("projects").match("/projects/p1/execute")).toBe(false);
    expect(entry("projects").match("/projects/p1/monitor")).toBe(false);
    expect(entry("execute").match("/projects/p1/execute")).toBe(true);
    expect(NAV_REGISTRY.filter((e) => e.match("/self-improving-x"))).toEqual([]);
    expect(NAV_REGISTRY.filter((e) => e.match("/projects-x"))).toEqual([]);
  });
});

/** ToolsRegion.tsx 不再持有入口常數與路徑分支（Architecture §5.2 硬規則 5 的機械檢查）。 */
function toolsRegionViolations(source: string): string[] {
  const found: string[] = [];
  if (source.includes("const NAV")) found.push("const NAV");
  if (source.includes("function activeNav")) found.push("function activeNav");
  if (source.includes("hrefFor")) found.push("hrefFor");
  for (const label of ["儀表板", "專案管理", "BRD/PRD 匯入", "執行中心", "監控中心", "系統設定", "自我進化"]) if (source.includes(label)) found.push(`入口標籤字面 ${label}`);
  if (/pathname\.startsWith\(\s*["'`]/.test(source)) found.push("以 pathname.startsWith 接路徑字面值");
  if (!/from\s+["']@\/lib\/nav\/registry["']/.test(source)) found.push("沒有自 @/lib/nav/registry 的 import");
  return found;
}

describe("AT_932_6_4 ToolsRegion.tsx 只消費登記表", () => {
  it("AT_932_6_4 不含 const NAV、function activeNav、hrefFor 與入口標籤字面，含自登記表的 import，以登記表參數化函式取得可見項與 active", () => {
    const source = readFileSync(path.join(ROOT, "components", "layout", "ToolsRegion.tsx"), "utf-8");
    expect(toolsRegionViolations(source)).toEqual([]);
    expect(source).toContain("NAV_REGISTRY");
    expect(source).toMatch(/visibleNavEntries\(\s*NAV_REGISTRY/);
    expect(source).toContain("activeNavEntry(");
    expect(source).toContain("navHref(");
  });

  it("AT_932_6_4 檢查函式的負控：違規原始碼逐一回非空，合規原始碼回空", () => {
    const compliant = 'import { NAV_REGISTRY, visibleNavEntries } from "@/lib/nav/registry";\nconst entries = visibleNavEntries(NAV_REGISTRY, role);';
    expect(toolsRegionViolations(compliant)).toEqual([]);
    const bad = [
      `${compliant}\nconst NAV = [{ id: "x" }];`,
      `${compliant}\nfunction activeNav(p: string) { return p; }`,
      `${compliant}\nconst href = hrefFor(id);`,
      `${compliant}\nconst label = "專案管理";`,
      `${compliant}\nif (pathname.startsWith("/import")) return 1;`,
      "const entries = [];",
    ];
    for (const sample of bad) expect(toolsRegionViolations(sample), sample).not.toEqual([]);
  });
});

describe("AT_932_6_E_1 登記表檢查函式的違規樣本各自觸發", () => {
  const routes = pageRoutes();
  const quiet = { match: () => false, mobile: false } as const;
  const seventhOf = (patch: Partial<NavEntry>): NavEntry => ({ ...NAV_REGISTRY[0], id: "extra", order: 80, ...quiet, ...patch });
  const kindsOf = (registry: ReadonlyArray<NavEntry>) => [...new Set(registryProblems(registry, probes, routes).map((p) => p.kind))];

  it("AT_932_6_E_1 真登記表回空；六種自造違規各自回報恰對應的違規（一個樣本一種違規，互不掩蓋）", () => {
    expect(registryProblems(NAV_REGISTRY, probes, routes)).toEqual([]);
    const samples: Array<[string, ReadonlyArray<NavEntry>, Problem["kind"]]> = [
      ["重複 id", [...NAV_REGISTRY, seventhOf({ id: "dashboard" })], "duplicate-id"],
      ["重複 order", [...NAV_REGISTRY, seventhOf({ order: 20 })], "duplicate-order"],
      ["七項 mobile 皆為 true", NAV_REGISTRY.map((e) => ({ ...e, mobile: true })), "mobile-overflow"],
      ["href 指向不存在的路由", [...NAV_REGISTRY, seventhOf({ href: "/nope" })], "bad-href"],
      ["兩項 match 同時命中同一代表路徑", [...NAV_REGISTRY, seventhOf({ match: (p: string) => p === "/" })], "match-overlap"],
      ["order 非數字", [...NAV_REGISTRY, seventhOf({ order: Number.NaN })], "bad-order"],
    ];
    for (const [name, registry, expected] of samples) expect(kindsOf(registry), name).toEqual([expected]);
  });
});

// ── 舊六項行為（改動前的 ToolsRegion.tsx；逐字搬來當對照基準）──────────────────────

type LegacyId = "dashboard" | "projects" | "import" | "execute" | "monitor" | "settings";
function legacyActive(pathname: string): LegacyId {
  if (pathname === "/") return "dashboard";
  if (pathname.startsWith("/import")) return "import";
  if (pathname.startsWith("/settings")) return "settings";
  if (/^\/projects\/[^/]+\/execute/.test(pathname)) return "execute";
  if (/^\/projects\/[^/]+\/monitor/.test(pathname)) return "monitor";
  return "projects";
}
function legacyHref(id: LegacyId, currentId: string | null): string {
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
      return currentId ? `/projects/${currentId}/${id}` : "/projects";
  }
}

describe("AT_932_6_E_2 舊六項的 active 與 href 行為不變，唯一差異明列", () => {
  const visible = visibleNavEntries(NAV_REGISTRY, "ADMIN");
  const newActive = (pathname: string) => activeNavEntry(visible, pathname)?.id ?? null;

  it("AT_932_6_E_2 已知前綴的路徑：新登記表的 active 與舊 activeNav 全部相同", () => {
    const known = [
      "/",
      "/import",
      "/import/x",
      "/settings",
      "/settings/x",
      "/projects",
      "/projects/new",
      "/projects/p1",
      "/projects/p1/goals",
      "/projects/p1/edit",
      "/projects/p1/execute",
      "/projects/p1/monitor",
      "/projects/p1/execute/x",
    ];
    for (const pathname of known) expect(newActive(pathname), pathname).toBe(legacyActive(pathname));
  });

  it("AT_932_6_E_2 唯一差異：舊行為下不屬於任何已知前綴的路徑（/unknown、/foo/bar）fallback 成 projects，新行為為無 active", () => {
    for (const pathname of ["/unknown", "/foo/bar"]) {
      expect(legacyActive(pathname), `${pathname} 的舊行為`).toBe("projects");
      expect(newActive(pathname), `${pathname} 的新行為`).toBeNull();
    }
    // 第七項的入口：/self-improving 由第七項認領（舊行為會 fallback 成 projects）
    expect(newActive("/self-improving")).toBe("self-improving");
    expect(legacyActive("/self-improving")).toBe("projects");
  });

  it("AT_932_6_E_2 六項的 href：無專案與有專案時與舊 hrefFor 完全相同", () => {
    for (const id of ["dashboard", "projects", "import", "execute", "monitor", "settings"] as const) {
      const entry = NAV_REGISTRY.find((e) => e.id === id) as NavEntry;
      for (const currentId of [null, "p1"]) expect(navHref(entry, { currentProjectId: currentId }), `${id} / ${String(currentId)}`).toBe(legacyHref(id, currentId));
    }
  });
});

describe("登記表的純函式（R21）", () => {
  const entry = (patch: Partial<NavEntry> & { id: string; order: number }): NavEntry => ({ ...NAV_REGISTRY[0], label: patch.id, href: `/${patch.id}`, match: () => false, ...patch });

  it("可見項＝enabled 為真，且 roles 缺或含目前角色；角色未知時帶 roles 的項不可見；依 order 升冪、同序依登記表原序", () => {
    const registry = [
      entry({ id: "late", order: 50 }),
      entry({ id: "first-35", order: 35 }),
      entry({ id: "second-35", order: 35 }),
      entry({ id: "off", order: 1, enabled: false }),
      entry({ id: "admin-only", order: 2, roles: ["ADMIN"] }),
      entry({ id: "op-admin", order: 3, roles: ["OPERATOR", "ADMIN"] }),
    ];
    expect(ids(visibleNavEntries(registry, "VIEWER"))).toEqual(["first-35", "second-35", "late"]);
    expect(ids(visibleNavEntries(registry, "OPERATOR"))).toEqual(["op-admin", "first-35", "second-35", "late"]);
    expect(ids(visibleNavEntries(registry, "ADMIN"))).toEqual(["admin-only", "op-admin", "first-35", "second-35", "late"]);
    expect(ids(visibleNavEntries(registry, undefined))).toEqual(["first-35", "second-35", "late"]);
    // 不改動傳入的登記表（回傳的是新陣列）
    expect(ids(registry)).toEqual(["late", "first-35", "second-35", "off", "admin-only", "op-admin"]);
  });

  it("active＝在可見項中依序第一個 match 為真者；沒有命中就沒有 active；不可見的項不會被亮", () => {
    const registry = [
      entry({ id: "hidden", order: 1, enabled: false, match: () => true }),
      entry({ id: "a", order: 2, match: (p) => p.startsWith("/x") }),
      entry({ id: "b", order: 3, match: (p) => p.startsWith("/x") }),
    ];
    const visible = visibleNavEntries(registry, "ADMIN");
    expect(activeNavEntry(visible, "/x/1")?.id).toBe("a");
    expect(activeNavEntry(visible, "/y")).toBeNull();
  });

  it("href：字串直取；函式以 { currentProjectId } 呼叫", () => {
    expect(navHref(entry({ id: "s", order: 1, href: "/fixed" }), { currentProjectId: "p9" })).toBe("/fixed");
    expect(navHref(entry({ id: "f", order: 1, href: (ctx) => `/p/${String(ctx.currentProjectId)}` }), { currentProjectId: "p9" })).toBe("/p/p9");
  });
});
