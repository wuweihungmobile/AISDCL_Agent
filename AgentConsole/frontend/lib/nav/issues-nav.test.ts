import { existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { NAV_REGISTRY, activeNavEntry, navHref, visibleNavEntries, type NavEntry } from "./registry";

/**
 * 議題中心的導覽接入（TCS-IssueCenter-20261027 R-IC-62；AT-IC-11-1-1、11-1-E-1、11-3-1）：登記表第八項 `issues` 加在陣列末尾、原七列的各欄與位置不變、
 * 顯示序由 order 決定（55 介於監控中心與系統設定之間）、href 對應存在的 app/issues/page.tsx、match 只命中 /issues 與其子路徑。
 * 既有導覽測試的釘值（registry.test.ts、ToolsRegion.test.tsx）隨之同步，不在本檔。
 * 2026-10-28（TCS-SysAdminBackup-20261027 R-BK-01）登記表加第九項 sysadmin：本檔的長度、id 清單、顯示序與 order／icon 集合大小隨之上修（8→9），
 * `NAV_REGISTRY[7]` 仍是 issues 的斷言與原七列的逐欄快照不動；第九項本身的斷言在 sysadmin-nav.test.ts。
 */
const ROOT = process.cwd();
const byId = (id: string) => NAV_REGISTRY.find((e) => e.id === id) as NavEntry;
const ids = (list: ReadonlyArray<NavEntry>) => list.map((e) => e.id);

describe("AT_IC_11_1 登記表第八項與顯示序", () => {
  it("AT_IC_11_1_1 NAV_REGISTRY 恰九項（原八項加 sysadmin）、id 依陣列序 dashboard、projects、import、execute、monitor、settings、self-improving、issues、sysadmin；issues 各欄符規格；顯示序完整九項；mobile 為 true 的項數 6", () => {
    expect(NAV_REGISTRY).toHaveLength(9);
    expect(ids(NAV_REGISTRY)).toEqual(["dashboard", "projects", "import", "execute", "monitor", "settings", "self-improving", "issues", "sysadmin"]);
    const issues = byId("issues");
    expect(issues).toMatchObject({ id: "issues", label: "議題中心", order: 55, href: "/issues", mobile: false, enabled: true });
    expect(issues.roles, "roles 缺＝所有已登入角色皆可見").toBeUndefined();
    expect(NAV_REGISTRY[7]).toBe(issues); // 加在陣列末尾
    expect(typeof issues.match).toBe("function");
    // 顯示序（依 order 升冪）：議題中心排在監控中心之後、系統設定之前，系統管理排在系統設定之後，自我進化仍在最後
    for (const role of ["ADMIN", "OPERATOR", "VIEWER", undefined] as const) {
      expect(ids(visibleNavEntries(NAV_REGISTRY, role)), String(role)).toEqual(["dashboard", "projects", "import", "execute", "monitor", "issues", "settings", "sysadmin", "self-improving"]);
    }
    expect(NAV_REGISTRY.filter((e) => e.mobile)).toHaveLength(6);
    expect(NAV_REGISTRY.filter((e) => e.mobile).map((e) => e.id)).toEqual(["dashboard", "projects", "import", "execute", "monitor", "settings"]);
    // order 與 id 各自唯一；圖示與原八個互異
    expect(new Set(NAV_REGISTRY.map((e) => e.order)).size).toBe(9);
    expect(new Set(NAV_REGISTRY.map((e) => e.icon)).size).toBe(9);
  });

  it("AT_IC_11_1_E_1 原七列逐欄快照：各欄與陣列位置全不變；self-improving 的 label「自我進化」、order 70、mobile false 不變", () => {
    const snapshot = (e: NavEntry) => ({
      id: e.id,
      label: e.label,
      order: e.order,
      enabled: e.enabled,
      mobile: e.mobile,
      roles: e.roles ?? null,
      hrefNoProject: navHref(e, { currentProjectId: null }),
      hrefProject: navHref(e, { currentProjectId: "p1" }),
    });
    expect(NAV_REGISTRY.slice(0, 7).map(snapshot)).toEqual([
      { id: "dashboard", label: "儀表板", order: 10, enabled: true, mobile: true, roles: null, hrefNoProject: "/", hrefProject: "/" },
      { id: "projects", label: "專案管理", order: 20, enabled: true, mobile: true, roles: null, hrefNoProject: "/projects", hrefProject: "/projects" },
      { id: "import", label: "BRD/PRD 匯入", order: 30, enabled: true, mobile: true, roles: null, hrefNoProject: "/import", hrefProject: "/import" },
      { id: "execute", label: "執行中心", order: 40, enabled: true, mobile: true, roles: null, hrefNoProject: "/projects", hrefProject: "/projects/p1/execute" },
      { id: "monitor", label: "監控中心", order: 50, enabled: true, mobile: true, roles: null, hrefNoProject: "/projects", hrefProject: "/projects/p1/monitor" },
      { id: "settings", label: "系統設定", order: 60, enabled: true, mobile: true, roles: null, hrefNoProject: "/settings", hrefProject: "/settings" },
      { id: "self-improving", label: "自我進化", order: 70, enabled: true, mobile: false, roles: null, hrefNoProject: "/self-improving", hrefProject: "/self-improving" },
    ]);
    expect(NAV_REGISTRY[6].id).toBe("self-improving");
    // 原七列的 match 對代表路徑的行為不變（議題中心的路徑不被它們吃掉）
    const probes: Array<[string, string | null]> = [
      ["/", "dashboard"],
      ["/projects", "projects"],
      ["/projects/p1/execute", "execute"],
      ["/projects/p1/monitor", "monitor"],
      ["/import", "import"],
      ["/settings", "settings"],
      ["/self-improving", "self-improving"],
      ["/self-improving/x", "self-improving"],
      ["/self-improving-x", null],
    ];
    for (const [pathname, expected] of probes) expect(activeNavEntry(visibleNavEntries(NAV_REGISTRY, "ADMIN"), pathname)?.id ?? null, pathname).toBe(expected);
  });
});

describe("AT_IC_11_3 路由與 match", () => {
  it("AT_IC_11_3_1 issues 的 href 對應存在的 app/issues/page.tsx；match 對 /issues、/issues/x 只命中本項、對 /self-improving 與相近路徑不命中", () => {
    expect(byId("issues").href).toBe("/issues");
    expect(existsSync(path.join(ROOT, "app", "issues", "page.tsx"))).toBe(true);
    const match = byId("issues").match;
    for (const hit of ["/issues", "/issues/x", "/issues/PROP-SI-004"]) {
      expect(match(hit), hit).toBe(true);
      expect(ids(NAV_REGISTRY.filter((e) => e.match(hit))), hit).toEqual(["issues"]);
    }
    for (const miss of ["/self-improving", "/self-improving/x", "/issues-x", "/issue", "/", "/projects", "/settings", ""]) expect(match(miss), miss).toBe(false);
    // 在可見項中 active 是第一個命中者：/issues 只亮議題中心，自我進化不亮
    const visible = visibleNavEntries(NAV_REGISTRY, "VIEWER");
    expect(activeNavEntry(visible, "/issues")?.id).toBe("issues");
    expect(activeNavEntry(visible, "/self-improving")?.id).toBe("self-improving");
  });
});
