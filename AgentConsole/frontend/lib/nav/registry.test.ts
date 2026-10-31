import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import type { Role } from "@/lib/api/types";
import { DELIVERED_NAV_ROWS } from "@/tests/helpers/navDelivered";
import { NAV_REGISTRY, activeNavEntry, navHref, visibleNavEntries, type NavEntry } from "./registry";

/**
 * 導覽登記表（TCS-SelfImprovingMirror-P1b R20、R21；Architecture §5.4、ADR-SI-13）：Tools 區的入口全部取自 NAV_REGISTRY，
 * 新增導覽項只加一列、不改任何元件。這裡鎖：登記表的內容、每列 href 都對應真實存在的路由頁、match 對代表路徑互斥、
 * ToolsRegion.tsx 只消費登記表（沒有入口常數與路徑分支），以及舊六項的行為不變（唯一差異：未知路徑不再亮「專案管理」）。
 *
 * 釘值政策（OBS-SI-321 根治）：本檔**不釘登記表的項數**，也不另持一份清單當期望值——
 *  · 唯一性、mobile 上限、icon 互異、href 對應真路由、match 互斥、「每項自己的頁面由自己認領」、ToolsRegion 不含任何入口標籤字面，
 *    一律以登記表自身的內容（`NAV_REGISTRY.length`、各列欄位）推導，對日後新增的列自動生效；
 *  · 「已交付列」只有一份快照 `DELIVERED_NAV_ROWS`（tests/helpers/navDelivered.ts；append-only 棘輪，四個導覽測試檔共用）：只比對登記表的前 N 列，所以新功能依慣例把列加在陣列**末尾**時不必改本檔；
 *    改動既有列的欄位、換位置、刪列才會紅——那是有意識的變更，要同步改這份快照；
 *  · 樣本列（負控）的 order 取登記表尚未用過的值（`FREE_ORDER`），登記表日後用到任何 order 都不會與樣本撞號。
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
  ["/issues", "issues"],
  ["/issues/x", "issues"],
  ["/sysadmin", "sysadmin"],
  ["/sysadmin/backup", "sysadmin"],
  ["/sysadmin-x", "none"],
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

/** 登記表尚未用過的 order（取最大值再加 10）：樣本列（負控）用它，登記表日後用到任何 order 都不會與樣本撞號。 */
const FREE_ORDER = Math.max(...NAV_REGISTRY.map((e) => e.order)) + 10;

/** 登記項自己的頁面路徑：字串 href 直取；函式型以「有專案」解析（無專案時退回 /projects 是別項的頁面，不是本項的）。 */
const ownPath = (e: NavEntry): string => navHref(e, { currentProjectId: "p1" }).split(/[?#]/)[0];

/** 每個登記項自己的頁面路徑都恰被該項認領（沒有別項同時命中、也不是沒人認領）；對日後新增的列自動生效。回傳違規說明。 */
function ownPathProblems(registry: ReadonlyArray<NavEntry>): string[] {
  const out: string[] = [];
  for (const e of registry) {
    const own = ownPath(e);
    const hits = ids(registry.filter((x) => x.match(own)));
    if (hits.length !== 1 || hits[0] !== e.id) out.push(`${e.id} 的頁面 ${own} 被 ${hits.length === 0 ? "無項" : hits.join("、")} 認領`);
  }
  return out;
}

describe("AT_932_6_1 登記表欄位值符合 R20（已交付列逐欄相符；唯一性與上限對整張登記表推導，不釘項數）", () => {
  it("AT_932_6_1 已交付列的 id、label、order、mobile 依序相符；整張登記表的 id 與 order 各自唯一，mobile 為 true 的項數不超過 6", () => {
    // 前綴比對：登記表在陣列末尾多加的列（新功能）不影響本斷言；少一列、改欄位、換位置才會紅
    expect(NAV_REGISTRY.length, "登記表不得少於已交付列數").toBeGreaterThanOrEqual(DELIVERED_NAV_ROWS.length);
    const delivered = NAV_REGISTRY.slice(0, DELIVERED_NAV_ROWS.length);
    expect(ids(delivered)).toEqual(DELIVERED_NAV_ROWS.map((r) => r[0]));
    expect(delivered.map((e) => e.label)).toEqual(DELIVERED_NAV_ROWS.map((r) => r[1]));
    expect(delivered.map((e) => e.order)).toEqual(DELIVERED_NAV_ROWS.map((r) => r[2]));
    expect(delivered.map((e) => e.mobile)).toEqual(DELIVERED_NAV_ROWS.map((r) => r[3]));
    expect(new Set(ids(NAV_REGISTRY)).size).toBe(NAV_REGISTRY.length);
    expect(new Set(NAV_REGISTRY.map((e) => e.order)).size).toBe(NAV_REGISTRY.length);
    expect(NAV_REGISTRY.filter((e) => e.mobile).length).toBeLessThanOrEqual(6);
  });

  it("AT_932_6_1 每項的型別：enabled 為布林、roles 缺或只含三種角色、match 為函式、href 為字串或函式、icon 為 React 元件且各項互異", () => {
    const roles: Role[] = ["ADMIN", "OPERATOR", "VIEWER"];
    for (const e of NAV_REGISTRY) {
      expect(typeof e.enabled, `${e.id}.enabled`).toBe("boolean");
      expect(e.roles === undefined || (Array.isArray(e.roles) && e.roles.every((r) => roles.includes(r))), `${e.id}.roles`).toBe(true);
      expect(typeof e.match, `${e.id}.match`).toBe("function");
      expect(["string", "function"], `${e.id}.href`).toContain(typeof e.href);
      const icon = e.icon as unknown;
      expect(typeof icon === "function" || (typeof icon === "object" && icon !== null && "$$typeof" in icon), `${e.id}.icon 不是 React 元件`).toBe(true);
    }
    expect(new Set(NAV_REGISTRY.map((e) => e.icon)).size).toBe(NAV_REGISTRY.length);
  });

  it("AT_932_6_1 第七項（自我進化）：href 為 /self-improving、roles 缺、enabled 為 true；execute 與 monitor 的 href(ctx) 無專案時回 /projects、有專案時帶專案 id；字串 href 的已交付七項依序相符", () => {
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
    // 前綴比對（append-safe）：字串型 href 的已交付七項依序相符；日後在末尾多加的列不影響
    const strings = NAV_REGISTRY.filter((e) => !["execute", "monitor"].includes(e.id));
    expect(strings.slice(0, 7).map((e) => e.href)).toEqual(["/", "/projects", "/import", "/settings", "/self-improving", "/issues", "/sysadmin"]);
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
    const base = { ...NAV_REGISTRY[0], id: "x", order: FREE_ORDER, mobile: false, match: () => false } satisfies NavEntry;
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

  it("AT_932_6_3 每個登記項自己的頁面路徑（字串 href 直取、函式型以有專案解析）恰被該項認領、沒有別項同時命中——登記表日後新增的列自動納入，不必另補代表路徑", () => {
    expect(ownPathProblems(NAV_REGISTRY)).toEqual([]);
    // 逐項明列（讀得到是哪一項、哪條路徑；項數不寫死）
    for (const e of NAV_REGISTRY) expect(ids(NAV_REGISTRY.filter((x) => x.match(ownPath(e)))), `${e.id} 的頁面 ${ownPath(e)}`).toEqual([e.id]);
  });

  it("AT_932_6_3 檢查函式的負控：match 永假（沒人認領自己的頁面）、match 過寬（連別項的頁面也認領）都被回報，各自指出是哪一項", () => {
    const sample = (patch: Partial<NavEntry>): NavEntry => ({ ...NAV_REGISTRY[0], id: "probe", href: "/probe", order: FREE_ORDER, mobile: false, ...patch });
    const never = ownPathProblems([...NAV_REGISTRY, sample({ match: () => false })]);
    expect(never).toEqual(["probe 的頁面 /probe 被 無項 認領"]);
    // match 永真：自己的頁面（/probe）只有它認領、不算違規；既有每一列的頁面都被它多認領一次 ⇒ 既有每列各被回報一次，且都點名 probe
    const greedy = ownPathProblems([...NAV_REGISTRY, sample({ match: () => true })]);
    expect(greedy).toHaveLength(NAV_REGISTRY.length);
    for (const line of greedy) expect(line.endsWith("、probe 認領"), line).toBe(true);
    expect(ownPathProblems(NAV_REGISTRY), "對照組：真登記表無違規").toEqual([]);
  });
});

/** ToolsRegion.tsx 不再持有入口常數與路徑分支（Architecture §5.2 硬規則 5 的機械檢查）。 */
function toolsRegionViolations(source: string): string[] {
  const found: string[] = [];
  if (source.includes("const NAV")) found.push("const NAV");
  if (source.includes("function activeNav")) found.push("function activeNav");
  if (source.includes("hrefFor")) found.push("hrefFor");
  // 標籤取自登記表本身（不另持清單）：登記表加了新列，ToolsRegion.tsx 也不得出現新列的標籤字面
  for (const { label } of NAV_REGISTRY) if (source.includes(label)) found.push(`入口標籤字面 ${label}`);
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
  const seventhOf = (patch: Partial<NavEntry>): NavEntry => ({ ...NAV_REGISTRY[0], id: "extra", order: FREE_ORDER, ...quiet, ...patch });
  const kindsOf = (registry: ReadonlyArray<NavEntry>) => [...new Set(registryProblems(registry, probes, routes).map((p) => p.kind))];

  it("AT_932_6_E_1 真登記表回空；六種自造違規各自回報恰對應的違規（一個樣本一種違規，互不掩蓋）", () => {
    expect(registryProblems(NAV_REGISTRY, probes, routes)).toEqual([]);
    const samples: Array<[string, ReadonlyArray<NavEntry>, Problem["kind"]]> = [
      ["重複 id", [...NAV_REGISTRY, seventhOf({ id: "dashboard" })], "duplicate-id"],
      ["重複 order", [...NAV_REGISTRY, seventhOf({ order: 20 })], "duplicate-order"],
      ["全部項 mobile 皆為 true", NAV_REGISTRY.map((e) => ({ ...e, mobile: true })), "mobile-overflow"],
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

// ── P2b（TCS-SelfImprovingDecide-P2b AT-950-10-E-1；W21）：新增四個寫入元件與對帳面板**沒有**動導覽登記表 ───────────────────────────────
// 為什麼重要：寫入入口是自我進化頁「裡面」的對話框與面板，不是新頁面——登記表多一列或少一列、第七項的欄位值變了，都代表 P2b 偷偷動了導覽（那是 P1b 的凍結面）。
// 零變更的最終證據是 V8 的 git diff --name-only；這裡是自動化的那一半。
describe("AT_950_10_E_1 導覽登記表：原八列不變，另加系統管理（第九列），ToolsRegion 無入口常數，新元件沒有新增導覽列", () => {
  it("AT_950_10_E_1 已交付各列（原八列加系統管理）各欄與先前的值相同（id、label、order、mobile、enabled、roles；快照 DELIVERED_NAV_ROWS），self-improving 仍在索引 6、mobile 仍為 false；登記表在末尾多加的新列不影響本斷言", () => {
    expect(NAV_REGISTRY.length, "登記表不得少於已交付列數").toBeGreaterThanOrEqual(DELIVERED_NAV_ROWS.length);
    expect(NAV_REGISTRY.slice(0, DELIVERED_NAV_ROWS.length).map((e) => [e.id, e.label, e.order, e.mobile, e.enabled, e.roles ?? null])).toEqual(DELIVERED_NAV_ROWS);
    expect(NAV_REGISTRY[6].href).toBe("/self-improving");
  });

  it("AT_950_10_E_1 ToolsRegion.tsx 不含入口常數（與 P1b 登記表測試共用 toolsRegionViolations 檢查函式）；自我進化的元件目錄沒有引用導覽登記表，也沒有自己的入口定義", () => {
    const tools = readFileSync(path.join(ROOT, "components", "layout", "ToolsRegion.tsx"), "utf-8");
    expect(toolsRegionViolations(tools)).toEqual([]);
    const dir = path.join(ROOT, "components", "domain", "si");
    const sources = readdirSync(dir).filter((n) => /\.tsx?$/.test(n) && !/\.test\.tsx?$/.test(n));
    expect(sources, "新元件都在這個目錄裡（防反空轉）").toEqual(expect.arrayContaining(["SiDecideDialog.tsx", "SiObsForm.tsx", "SiObsCloseDialog.tsx", "SiWritesPanel.tsx"]));
    for (const name of sources) {
      const text = readFileSync(path.join(dir, name), "utf-8");
      expect(text, `${name} 不得引用導覽登記表`).not.toMatch(/lib\/nav\/registry|NAV_REGISTRY/);
    }
    // layout.test.tsx 仍在（它對各入口的版面行為有自己的斷言，本檔不複寫）
    expect(statSync(path.join(ROOT, "components", "layout", "layout.test.tsx")).isFile()).toBe(true);
  });
});
