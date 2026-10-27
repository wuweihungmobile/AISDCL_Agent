import { cpSync, mkdirSync, mkdtempSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { NAV_REGISTRY, type NavEntry } from "@/lib/nav/registry";
import { HELP_PAGES, HELP_ROUTES, NO_STATE_PAGES, PENDING_HELP_PAGES, helpForPath } from "./registry";
import type { HelpId } from "./types";

/**
 * 說明登記表與路由三道雙向鎖（TCS-PageHelp-20261027 R-PH-02～R-PH-05、R-PH-07、R-PH-35；載具 HR，輪 1a 建、每棒下修 PENDING_CEILING）：
 *  - AT-PH-03-1-1、1-E-1、08-1-1、08-1-E-1：路由鎖（app/**\/page.tsx 的路由樣板減 /login ＝ HELP_ROUTES 的鍵；缺與多都紅，訊息含修法）；
 *  - AT-PH-03-2-1、2-E-1、08-2-1、08-2-E-1：導覽鎖（NAV_REGISTRY 每個啟用項的 href 兩種解析都經 helpForPath 得到說明 id）；
 *  - AT-PH-03-3-1、3-2、3-E-1：helpForPath（靜態段優先於動態段、去尾斜線、大小寫敏感；與 pending 無關）；
 *  - AT-PH-03-4-1、4-E-1：頁檔鎖（lib/help 的頁檔 id 集合＝HELP_PAGES 的鍵 ∪ PENDING_HELP_PAGES，兩者互斥，每檔 id 等於檔名）；
 *  - AT-PH-03-6-1、6-2：分輪棘輪（PENDING_CEILING）與 pending 的處置（路由鎖在所有輪次成立、內容類檢查豁免且豁免清單印出）。
 * 斷言一律由登記表、路由表、導覽登記表推導，不寫死件數（姊妹案「系統管理／資料庫備份」會增加路由與導覽項，先後落地兩序皆綠）；唯一的釘值是下方 ROUTE_TABLE 的必備子集（只准增不准減）。
 * 判定指令：npx vitest run lib/help/registry.test.ts -t "<AT 底線形>"
 */

/**
 * 分輪棘輪（D-PH-14）：`PENDING_HELP_PAGES.length` 不得超過它。初值＝PRD 十六頁中尚未寫的頁數（輪 1a：13）＋姊妹案暫列的 pending 頁數（0）。
 * 只准下修：每一棒把寫好的頁移出 pending 時同 commit 下修；輪 2 → 3、輪 3 出口 → 0（G-F8）；上修只有姊妹案重填 pending 且同 commit 於 PR 說明 WHY。
 */
const PENDING_CEILING = 0;

const ROOT = process.cwd();
const HELP_DIR = path.join(ROOT, "lib", "help");
const FIX_HINT = "在 lib/help/<id>.ts 新增並於 registry.ts 登記";

/** PRD §4 的 19 條路由→說明 id（TCS §5.3 ROUTE_TABLE；只准增不准減；具體路徑把 [projectId]→p1、[goalId]→g1、[taskId]→t1）。 */
const ROUTE_TABLE: ReadonlyArray<readonly [template: string, id: HelpId]> = [
  ["/", "dashboard"],
  ["/projects", "projects"],
  ["/projects/[projectId]", "project-detail"],
  ["/projects/[projectId]/goals", "goals"],
  ["/projects/[projectId]/goals/[goalId]", "goal-detail"],
  ["/projects/[projectId]/goals/[goalId]/tasks", "tasks"],
  ["/projects/[projectId]/goals/[goalId]/tasks/[taskId]", "task-detail"],
  ["/projects/new", "project-form"],
  ["/projects/[projectId]/edit", "project-form"],
  ["/projects/[projectId]/goals/new", "goal-form"],
  ["/projects/[projectId]/goals/[goalId]/edit", "goal-form"],
  ["/projects/[projectId]/goals/[goalId]/tasks/new", "task-form"],
  ["/projects/[projectId]/goals/[goalId]/tasks/[taskId]/edit", "task-form"],
  ["/projects/[projectId]/execute", "execute"],
  ["/projects/[projectId]/monitor", "monitor"],
  ["/import", "import"],
  ["/settings", "settings"],
  ["/self-improving", "self-improving"],
  ["/issues", "issues"],
];
const concretePath = (template: string): string => template.replace("[projectId]", "p1").replace("[goalId]", "g1").replace("[taskId]", "t1");

const pageIds = (): Set<string> => new Set<string>([...Object.keys(HELP_PAGES), ...PENDING_HELP_PAGES]);

// ── app/**/page.tsx → 路由樣板（沿 lib/nav/registry.test.ts:46-68 的 walker）──────────────────

/** 括號群組 (name) 不進網址、動態段保留方括號名、根路由是 `/`；回傳排序後的樣板清單。 */
function routeTemplates(appDir: string): string[] {
  const routes: string[] = [];
  const walk = (dir: string, segments: string[]) => {
    for (const name of readdirSync(dir)) {
      const full = path.join(dir, name);
      if (statSync(full).isDirectory()) walk(full, /^\(.*\)$/.test(name) ? segments : [...segments, name]);
      else if (name === "page.tsx") routes.push(segments.length === 0 ? "/" : `/${segments.join("/")}`);
    }
  };
  walk(appDir, []);
  return routes.sort();
}

/** 路由鎖：缺（新頁沒說明）與多（說明指向不存在的頁）都回報；缺的訊息含修法。 */
function routeProblems(templates: readonly string[], helpKeys: readonly string[], exclude: readonly string[]): string[] {
  const out: string[] = [];
  for (const template of templates) if (!exclude.includes(template) && !helpKeys.includes(template)) out.push(`路由 ${template} 沒有說明項：${FIX_HINT}`);
  for (const key of helpKeys) if (!templates.includes(key) || exclude.includes(key)) out.push(`HELP_ROUTES 的鍵 ${key} 沒有對應的頁面（或在排除名單內），請把這一列拿掉`);
  return out;
}

// ── 導覽登記表 → helpForPath ──────────────────────────────────────────────────────────

type NavLike = Pick<NavEntry, "id" | "href" | "enabled">;

/** 一個導覽項的 href 解析（字串直取；函式型以無專案與有專案兩種呼叫），去掉 ?、# 後的路徑。 */
function navPaths(entry: NavLike): string[] {
  const hrefs = typeof entry.href === "string" ? [entry.href] : [entry.href({ currentProjectId: null }), entry.href({ currentProjectId: "p1" })];
  return hrefs.map((href) => href.split(/[?#]/)[0]);
}

/** 導覽鎖：每個啟用項的每種 href 解析都要解得到說明 id；停用項豁免。 */
function navProblems(registry: readonly NavLike[], resolve: (pathname: string) => string | null): string[] {
  const out: string[] = [];
  for (const entry of registry) {
    if (!entry.enabled) continue;
    for (const pathname of navPaths(entry)) if (resolve(pathname) === null) out.push(`導覽項 ${entry.id} 的 href ${pathname} 沒有說明項：${FIX_HINT}`);
  }
  return out;
}

// ── 頁檔鎖 ────────────────────────────────────────────────────────────────────────────

const RESERVED_FILES = new Set(["types", "states", "registry", "lint", "common"]);

/** lib/help 扣掉保留名與測試檔後的頁檔名（不含副檔名）。 */
function pageFileNames(dir: string): string[] {
  return readdirSync(dir)
    .filter((name) => name.endsWith(".ts") && !name.endsWith(".test.ts"))
    .map((name) => name.slice(0, -".ts".length))
    .filter((name) => !RESERVED_FILES.has(name))
    .sort();
}

/** 頁檔鎖：頁檔集合＝已寫 ∪ pending、兩者互斥、檔內 id 等於檔名。 */
function pageFileProblems(fileNames: readonly string[], helpKeys: readonly string[], pending: readonly string[], ids: Readonly<Record<string, string | undefined>>): string[] {
  const out: string[] = [];
  const registered = new Set([...helpKeys, ...pending]);
  for (const name of fileNames) if (!registered.has(name)) out.push(`多一個頁檔 ${name}：它沒有登記在 HELP_PAGES 或 PENDING_HELP_PAGES`);
  for (const id of registered) if (!fileNames.includes(id)) out.push(`少一個頁檔 ${id}：已登記卻沒有 lib/help/${id}.ts`);
  for (const name of fileNames) if (ids[name] !== name) out.push(`頁檔 ${name} 的 id 欄是 ${String(ids[name])}，必須等於檔名`);
  for (const id of helpKeys) if (pending.includes(id)) out.push(`${id} 同時在 HELP_PAGES 與 PENDING_HELP_PAGES`);
  return out;
}

// ── AC-PH-03-1、08-1：路由鎖 ──────────────────────────────────────────────────────────

describe("AT_PH_03_1 路由鎖（R-PH-02）", () => {
  it("AT_PH_03_1_1 app/**/page.tsx 的路由樣板減 /login 與 HELP_ROUTES 的鍵集合相等；路由數大於 10；/login 不在其中；每個值都是已登記的說明 id", () => {
    const templates = routeTemplates(path.join(ROOT, "app"));
    expect(templates.length, "防反空轉：路由數").toBeGreaterThan(10);
    expect(templates).toContain("/login");
    const expected = templates.filter((template) => template !== "/login");
    expect(Object.keys(HELP_ROUTES).sort()).toEqual(expected);
    expect(routeProblems(templates, Object.keys(HELP_ROUTES), ["/login"])).toEqual([]);
    expect(Object.keys(HELP_ROUTES)).not.toContain("/login");
    const ids = pageIds();
    for (const [template, id] of Object.entries(HELP_ROUTES)) expect(ids.has(id), `${template} → ${id} 不在 HELP_PAGES 或 PENDING_HELP_PAGES`).toBe(true);
  });

  it("AT_PH_03_1_E_1 routeProblems 與 walker 的負控（合成目錄樹）：路由群組不進網址、動態段保留方括號名、根路由是 /；缺一個鍵、多一個鍵各回非空；/login 在排除名單內不算缺；缺的訊息含修法", () => {
    const tmp = mkdtempSync(path.join(tmpdir(), "help-routes-"));
    try {
      const app = path.join(tmp, "app");
      for (const rel of ["(app)/x", "[id]", "."]) mkdirSync(path.join(app, rel), { recursive: true });
      for (const rel of ["(app)/x/page.tsx", "[id]/page.tsx", "page.tsx"]) writeFileSync(path.join(app, rel), "export default function Page() { return null; }\n", "utf-8");
      const templates = routeTemplates(app);
      expect(templates).toEqual(["/", "/[id]", "/x"]);

      expect(routeProblems(templates, ["/", "/[id]", "/x"], [])).toEqual([]);
      const missing = routeProblems(templates, ["/", "/x"], []);
      expect(missing).toHaveLength(1);
      expect(missing[0]).toContain("/[id]");
      expect(missing[0]).toContain(FIX_HINT);
      const extra = routeProblems(templates, ["/", "/[id]", "/x", "/ghost"], []);
      expect(extra).toHaveLength(1);
      expect(extra[0]).toContain("/ghost");
      // 排除名單：/[id] 在排除名單內就不算缺；排除名單內的路由若還登記在表裡，算多
      expect(routeProblems(templates, ["/", "/x"], ["/[id]"])).toEqual([]);
      expect(routeProblems(templates, ["/", "/[id]", "/x"], ["/[id]"])).toHaveLength(1);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });

  it("AT_PH_08_1_1 把真 app 樹複製到暫存目錄再加 app/zzz/page.tsx：路由鎖回非空並含 /zzz 與修法；未加檔的複本回空（對照組，證明紅是新頁造成的；不動工作樹）", () => {
    const tmp = mkdtempSync(path.join(tmpdir(), "help-newpage-"));
    try {
      const copy = path.join(tmp, "app");
      cpSync(path.join(ROOT, "app"), copy, { recursive: true });
      const helpKeys = Object.keys(HELP_ROUTES);
      expect(routeProblems(routeTemplates(copy), helpKeys, ["/login"]), "對照組：未加新頁").toEqual([]);

      mkdirSync(path.join(copy, "zzz"), { recursive: true });
      writeFileSync(path.join(copy, "zzz", "page.tsx"), "export default function Page() { return null; }\n", "utf-8");
      const problems = routeProblems(routeTemplates(copy), helpKeys, ["/login"]);
      expect(problems).toHaveLength(1);
      expect(problems[0]).toContain("/zzz");
      expect(problems[0]).toContain(FIX_HINT);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });

  it("AT_PH_08_1_E_1 自 HELP_ROUTES 的鍵集合拿掉一個鍵：回非空並指出缺的路由，不影響其他路由的判定", () => {
    const templates = routeTemplates(path.join(ROOT, "app"));
    const helpKeys = Object.keys(HELP_ROUTES);
    expect(helpKeys).toContain("/import");
    const problems = routeProblems(
      templates,
      helpKeys.filter((key) => key !== "/import"),
      ["/login"],
    );
    expect(problems).toHaveLength(1);
    expect(problems[0]).toContain("/import");
    expect(problems[0]).toContain(FIX_HINT);
  });
});

// ── AC-PH-03-2、08-2：導覽鎖 ──────────────────────────────────────────────────────────

describe("AT_PH_03_2 導覽鎖（R-PH-03）", () => {
  it("AT_PH_03_2_1 NAV_REGISTRY 每個啟用項的 href（字串直取；函式型以無專案與 p1 兩種呼叫）都經 helpForPath 得到說明 id；檢查的解析數不少於啟用項數；停用項不納入", () => {
    const enabled = NAV_REGISTRY.filter((entry) => entry.enabled);
    expect(enabled.length, "防反空轉：啟用項數").toBeGreaterThanOrEqual(1);
    const resolutions = enabled.flatMap(navPaths);
    expect(resolutions.length, "檢查的解析數不少於啟用項數").toBeGreaterThanOrEqual(enabled.length);
    expect(resolutions.length, "函式型 href 每項有兩種解析").toBe(enabled.reduce((n, entry) => n + (typeof entry.href === "string" ? 1 : 2), 0));
    for (const pathname of resolutions) expect(helpForPath(pathname), pathname).not.toBeNull();
    expect(navProblems(NAV_REGISTRY, helpForPath)).toEqual([]);
  });

  it("AT_PH_03_2_E_1 navProblems 負控：href 指向 /login、函式型 href 有一個分支指向未知路徑各回非空並含該項 id；停用項豁免；合規登記表回空", () => {
    const resolve = (pathname: string) => helpForPath(pathname);
    const login: NavLike = { id: "x-login", href: "/login", enabled: true };
    const branch: NavLike = { id: "x-branch", href: (ctx) => (ctx.currentProjectId ? "/unknown" : "/projects"), enabled: true };
    const disabled: NavLike = { id: "x-off", href: "/unknown", enabled: false };
    const fine: NavLike = { id: "x-fine", href: (ctx) => (ctx.currentProjectId ? `/projects/${ctx.currentProjectId}/execute` : "/projects"), enabled: true };
    expect(navProblems([login], resolve).join("\n")).toContain("x-login");
    expect(navProblems([branch], resolve).join("\n")).toContain("x-branch");
    expect(navProblems([disabled], resolve)).toEqual([]);
    expect(navProblems([fine], resolve)).toEqual([]);
    expect(navProblems([], resolve)).toEqual([]);
  });

  it("AT_PH_08_2_1 真登記表加一項 enabled:true、href:/login 的合成登記表：回非空並含該項 id；真登記表回空（對照組）", () => {
    expect(navProblems(NAV_REGISTRY, helpForPath), "對照組").toEqual([]);
    const withBadItem: NavLike[] = [...NAV_REGISTRY, { id: "zz", href: "/login", enabled: true }];
    const problems = navProblems(withBadItem, helpForPath);
    expect(problems).toHaveLength(1);
    expect(problems[0]).toContain("zz");
    expect(problems[0]).toContain(FIX_HINT);
  });

  it("AT_PH_08_2_E_1 新項 enabled:false 回空（停用項豁免）；新項 href 為函式且兩種解析都有說明回空", () => {
    expect(navProblems([...NAV_REGISTRY, { id: "zz", href: "/login", enabled: false }], helpForPath)).toEqual([]);
    expect(navProblems([...NAV_REGISTRY, { id: "zz", href: (ctx) => (ctx.currentProjectId ? `/projects/${ctx.currentProjectId}/monitor` : "/projects"), enabled: true }], helpForPath)).toEqual([]);
  });
});

// ── AC-PH-03-3：helpForPath ────────────────────────────────────────────────────────────

/** 測試內獨立比對器（不用 registry.ts 的實作）：逐段比對（靜態段相等或動態段非空），回傳所有符合的樣板，靜態段多的在前。 */
function independentMatches(pathname: string, templates: readonly string[]): string[] {
  if (!pathname.startsWith("/")) return [];
  const raw = pathname.split("/").slice(1);
  const concrete = raw.length > 0 && raw[raw.length - 1] === "" ? raw.slice(0, -1) : raw;
  const staticCount = (template: string) => template.split("/").filter((segment) => segment !== "" && !segment.startsWith("[")).length;
  return templates
    .filter((template) => {
      const segments = template === "/" ? [] : template.split("/").slice(1);
      return segments.length === concrete.length && segments.every((segment, i) => (segment.startsWith("[") ? concrete[i] !== "" : segment === concrete[i]));
    })
    .sort((a, b) => staticCount(b) - staticCount(a));
}

describe("AT_PH_03_3 helpForPath（R-PH-04）", () => {
  it("AT_PH_03_3_1 PRD AC-PH-03-3 的代表路徑逐字：靜態段優先、去尾斜線；空字串、未知路徑、前綴相似與 /login 回 null", () => {
    expect(helpForPath("/")).toBe("dashboard");
    expect(helpForPath("/projects/new")).toBe("project-form");
    expect(helpForPath("/projects/p1")).toBe("project-detail");
    expect(helpForPath("/projects/p1/edit")).toBe("project-form");
    expect(helpForPath("/projects/p1/goals/g1/tasks/t1/edit")).toBe("task-form");
    expect(helpForPath("/projects/p1/")).toBe("project-detail");
    for (const pathname of ["", "/unknown", "/projects-x", "/login"]) expect(helpForPath(pathname), JSON.stringify(pathname)).toBeNull();
  });

  it("AT_PH_03_3_2 ROUTE_TABLE 的 19 條具體路徑逐一等於表中 id；HELP_ROUTES 含這 19 個樣板且 id 相同；每條路徑最具體的符合樣板唯一；helpForPath 等於獨立比對器的結果", () => {
    expect(ROUTE_TABLE).toHaveLength(19);
    const templates = Object.keys(HELP_ROUTES);
    for (const [template, id] of ROUTE_TABLE) {
      expect(HELP_ROUTES[template], `HELP_ROUTES[${template}]`).toBe(id);
      const pathname = concretePath(template);
      expect(helpForPath(pathname), pathname).toBe(id);
      // 獨立比對：符合的樣板至少一個，最具體者（靜態段最多）唯一，且它的 id 就是 helpForPath 的結果
      const matches = independentMatches(pathname, templates);
      expect(matches.length, `${pathname} 至少符合一個樣板`).toBeGreaterThanOrEqual(1);
      const staticCount = (t: string) => t.split("/").filter((segment) => segment !== "" && !segment.startsWith("[")).length;
      const best = matches.filter((t) => staticCount(t) === staticCount(matches[0]));
      expect(best, `${pathname} 最具體的符合樣板必須唯一`).toHaveLength(1);
      expect(HELP_ROUTES[best[0]], pathname).toBe(helpForPath(pathname));
    }
    // 每一條登記的路由（含姊妹案新增者）也都過同一組判準
    for (const template of templates) {
      const pathname = concretePath(template);
      const matches = independentMatches(pathname, templates);
      expect(HELP_ROUTES[matches[0]], pathname).toBe(helpForPath(pathname));
    }
  });

  it("AT_PH_03_3_E_1 邊界路徑：URL 編碼與中文的動態段、大小寫敏感、多一段、/issues/x、靜態段 new 優先；待寫頁的路由仍回其 id", () => {
    expect(helpForPath("/projects/%E4%B8%AD/goals")).toBe("goals");
    expect(helpForPath("/projects/中文/goals")).toBe("goals");
    expect(helpForPath("/Projects")).toBeNull();
    expect(helpForPath("/projects/p1/goals/g1/tasks/t1/edit/x")).toBeNull();
    expect(helpForPath("/issues/x")).toBeNull();
    expect(helpForPath("/projects/new")).toBe("project-form");
    expect(helpForPath("/projects/p1/goals/new")).toBe("goal-form");
    expect(helpForPath("/projects/p1/goals/g1/tasks/new")).toBe("task-form");
    // 空的動態段不算（連續斜線）
    expect(helpForPath("/projects//goals")).toBeNull();
    // 與 PENDING_HELP_PAGES 無關：待寫頁的路由照樣回它的 id（路由鎖在所有輪次都成立）
    for (const id of PENDING_HELP_PAGES) {
      const template = Object.keys(HELP_ROUTES).find((key) => HELP_ROUTES[key] === id);
      expect(template, `待寫頁 ${id} 在 HELP_ROUTES 有路由`).toBeDefined();
      expect(helpForPath(concretePath(template as string)), id).toBe(id);
    }
  });
});

// ── AC-PH-03-4：頁檔鎖 ────────────────────────────────────────────────────────────────

describe("AT_PH_03_4 頁檔鎖（R-PH-05）", () => {
  it("AT_PH_03_4_1 lib/help 扣掉保留名與測試檔的頁檔，id 集合＝HELP_PAGES 的鍵 ∪ PENDING_HELP_PAGES、兩者互斥；每個頁檔模組恰匯出一個帶 id 的 PageHelp 且 id 等於檔名", async () => {
    const names = pageFileNames(HELP_DIR);
    expect(names.length, "防反空轉：頁檔數（輪 1 的先導頁至少三個）").toBeGreaterThanOrEqual(3);
    const ids: Record<string, string | undefined> = {};
    for (const name of names) {
      // 不用 import.meta.glob（tsc 缺 vite/client 型別）；動態位址 Vite 會印 dynamic-import-vars 警告，屬已知、不影響 rc，故加 @vite-ignore
      const mod = (await import(/* @vite-ignore */ `./${name}`)) as Record<string, unknown>;
      expect(Object.keys(mod), `${name} 恰匯出一個值`).toHaveLength(1);
      const page = Object.values(mod)[0] as { id?: unknown };
      expect(typeof page === "object" && page !== null && "id" in page, `${name} 匯出的值帶 id 欄`).toBe(true);
      ids[name] = typeof page.id === "string" ? page.id : undefined;
    }
    expect(pageFileProblems(names, Object.keys(HELP_PAGES), PENDING_HELP_PAGES, ids)).toEqual([]);
    expect(names).toEqual([...pageIds()].sort());
    for (const id of PENDING_HELP_PAGES) expect(Object.keys(HELP_PAGES), `${id} 不得同時已寫`).not.toContain(id);
  });

  it("AT_PH_03_4_E_1 pageFileProblems 負控：多一個頁檔、少一個頁檔、檔內 id 與檔名不符、同一 id 同在兩個集合各回非空；合規輸入回空", () => {
    const ids = { a: "a", b: "b", c: "c" };
    expect(pageFileProblems(["a", "b", "c"], ["a", "b"], ["c"], ids)).toEqual([]);
    expect(pageFileProblems(["a", "b", "c", "extra"], ["a", "b"], ["c"], { ...ids, extra: "extra" }).join("\n")).toContain("extra");
    expect(pageFileProblems(["a", "b"], ["a", "b"], ["c"], ids).join("\n")).toContain("少一個頁檔 c");
    expect(pageFileProblems(["a", "b", "c"], ["a", "b"], ["c"], { ...ids, b: "zzz" }).join("\n")).toContain("頁檔 b");
    expect(pageFileProblems(["a", "b", "c"], ["a", "b", "c"], ["c"], ids).join("\n")).toContain("同時在 HELP_PAGES 與 PENDING_HELP_PAGES");
    expect(pageFileProblems(["a", "b", "c"], ["a", "b"], ["c"], { a: "a", b: "b", c: undefined }).join("\n")).toContain("頁檔 c");
  });
});

// ── AC-PH-03-6：分輪棘輪與 pending ────────────────────────────────────────────────────

describe("AT_PH_03_6 分輪棘輪（R-PH-07）", () => {
  it("AT_PH_03_6_1 PENDING_HELP_PAGES 的件數不超過 PENDING_CEILING（非負整數）；無重複且全部屬於頁檔 id 集合；與 HELP_PAGES 互斥", () => {
    expect(Number.isInteger(PENDING_CEILING) && PENDING_CEILING >= 0, "PENDING_CEILING 是非負整數").toBe(true);
    expect(PENDING_HELP_PAGES.length).toBeLessThanOrEqual(PENDING_CEILING);
    expect(new Set(PENDING_HELP_PAGES).size, "pending 無重複").toBe(PENDING_HELP_PAGES.length);
    const fileIds = new Set(pageFileNames(HELP_DIR));
    for (const id of PENDING_HELP_PAGES) expect(fileIds.has(id), `${id} 的頁檔存在`).toBe(true);
    for (const id of PENDING_HELP_PAGES) expect(HELP_PAGES[id], `${id} 不得同時已寫`).toBeUndefined();
    // NO_STATE_PAGES 也只放說明 id，且無重複
    expect(new Set(NO_STATE_PAGES).size).toBe(NO_STATE_PAGES.length);
    for (const id of NO_STATE_PAGES) expect(pageIds().has(id), `${id} 在 NO_STATE_PAGES 卻不是說明 id`).toBe(true);
  });

  it("AT_PH_03_6_2 pending 頁的 id 仍出現在 HELP_ROUTES 的值中（路由鎖在所有輪次成立）；HELP_PAGES 不含 pending id；內容類測試的語料只取 HELP_PAGES，被豁免的 id 清單在此印出", () => {
    const routed = new Set<string>(Object.values(HELP_ROUTES));
    for (const id of PENDING_HELP_PAGES) expect(routed.has(id), `${id} 的路由要在 HELP_ROUTES 內`).toBe(true);
    expect(Object.keys(HELP_PAGES).filter((id) => PENDING_HELP_PAGES.includes(id as HelpId))).toEqual([]);
    for (const [id, page] of Object.entries(HELP_PAGES)) expect(page?.id, `HELP_PAGES 的鍵 ${id} 等於 PageHelp.id`).toBe(id);
    // 豁免是明列的，不是靜默略過：把被豁免的 id 清單印出來
    console.info(`[page-help] 內容類檢查豁免的待寫頁（${PENDING_HELP_PAGES.length}）：${PENDING_HELP_PAGES.join("、") || "（無）"}`);
  });
});
