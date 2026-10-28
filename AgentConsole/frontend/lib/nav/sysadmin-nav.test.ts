import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { Database, DatabaseBackup } from "lucide-react";
import { describe, expect, it } from "vitest";

import { NAV_REGISTRY, activeNavEntry, navHref, visibleNavEntries, type NavEntry } from "./registry";

/**
 * 系統管理的導覽接入（TCS-SysAdminBackup-20261027 R-BK-01、R-BK-03、R-BK-61；AT-BK-01-1-1、01-1-2、01-1-E-1、01-2-2、01-3-E-1，載具 FN）：登記表第九項 `sysadmin` 加在陣列末尾
 * （index 8；label「系統管理」、href `/sysadmin`、order 65、mobile false、roles 缺、icon `Database`）、原八列的各欄與位置不變（self-improving 仍 `[6]`、issues 仍 `[7]`）、
 * 顯示序由 order 決定（settings 60、sysadmin 65、self-improving 70）、match 只命中 `/sysadmin` 與其子路徑。既有導覽測試（issues-nav.test.ts、registry.test.ts、ToolsRegion.test.tsx）的釘值隨之同步，
 * 本檔以讀原始碼的方式核對它們確實同步了（AT-BK-01-1-2）。
 * 判定指令：npx vitest run lib/nav/sysadmin-nav.test.ts -t "<AT 底線形>"
 */
const ROOT = process.cwd();
const byId = (id: string) => NAV_REGISTRY.find((e) => e.id === id) as NavEntry;
const ids = (list: ReadonlyArray<NavEntry>) => list.map((e) => e.id);

describe("AT_BK_01_1 登記表第九項與顯示序", () => {
  it("AT_BK_01_1_1 NAV_REGISTRY 恰九項、id 依陣列序；[6] 是 self-improving、[7] 是 issues、[8] 是 sysadmin；sysadmin 各欄逐值（icon 是 Database、不是 DatabaseBackup）；四種角色的顯示序；order 唯一、icon 互異", () => {
    expect(NAV_REGISTRY).toHaveLength(9);
    expect(ids(NAV_REGISTRY)).toEqual(["dashboard", "projects", "import", "execute", "monitor", "settings", "self-improving", "issues", "sysadmin"]);
    expect(NAV_REGISTRY[6].id).toBe("self-improving");
    expect(NAV_REGISTRY[7].id).toBe("issues");
    const sysadmin = byId("sysadmin");
    expect(NAV_REGISTRY[8]).toBe(sysadmin);
    expect(sysadmin).toMatchObject({ id: "sysadmin", label: "系統管理", href: "/sysadmin", order: 65, enabled: true, mobile: false });
    expect(sysadmin.roles, "roles 缺＝所有已登入角色皆可見").toBeUndefined();
    expect(sysadmin.icon).toBe(Database);
    expect(sysadmin.icon).not.toBe(DatabaseBackup);
    expect(typeof sysadmin.match).toBe("function");
    for (const role of ["ADMIN", "OPERATOR", "VIEWER", undefined] as const) {
      expect(ids(visibleNavEntries(NAV_REGISTRY, role)), String(role)).toEqual(["dashboard", "projects", "import", "execute", "monitor", "issues", "settings", "sysadmin", "self-improving"]);
    }
    expect(new Set(NAV_REGISTRY.map((e) => e.order)).size).toBe(9);
    expect(new Set(NAV_REGISTRY.map((e) => e.icon)).size).toBe(9);
    // 顯示序的 order：settings 60 < sysadmin 65 < self-improving 70
    expect([byId("settings").order, sysadmin.order, byId("self-improving").order]).toEqual([60, 65, 70]);
  });

  it("AT_BK_01_1_2 既有導覽測試已同步：issues-nav.test.ts 的長度、id 清單、顯示序含 sysadmin 且 NAV_REGISTRY[7] 斷言仍在；registry.test.ts 的 AT_950_10_E_1 改述為「原八列不變，另加系統管理」並補第九列；ToolsRegion.test.tsx 補了九個連結與 max-md:hidden 判準", () => {
    const read = (...segments: string[]) => readFileSync(path.join(ROOT, ...segments), "utf-8");
    const issuesNav = read("lib", "nav", "issues-nav.test.ts");
    expect(issuesNav).toContain("expect(NAV_REGISTRY).toHaveLength(9);");
    expect(issuesNav).toContain('["dashboard", "projects", "import", "execute", "monitor", "settings", "self-improving", "issues", "sysadmin"]');
    expect(issuesNav).toContain('["dashboard", "projects", "import", "execute", "monitor", "issues", "settings", "sysadmin", "self-improving"]');
    expect(issuesNav).toContain("expect(NAV_REGISTRY[7]).toBe(issues);");
    expect(issuesNav).toContain("expect(new Set(NAV_REGISTRY.map((e) => e.order)).size).toBe(9);");
    expect(issuesNav).toContain("expect(new Set(NAV_REGISTRY.map((e) => e.icon)).size).toBe(9);");

    const registryTest = read("lib", "nav", "registry.test.ts");
    expect(registryTest).toContain("原八列不變，另加系統管理");
    expect(registryTest).toContain('["sysadmin", "系統管理", 65, false, true, null]');
    expect(registryTest).toContain('["/sysadmin", "sysadmin"]');
    expect(registryTest).toContain('["/sysadmin/backup", "sysadmin"]');
    expect(registryTest).toContain('["/sysadmin-x", "none"]');
    expect(registryTest).toContain('"/issues", "/sysadmin"]');

    const toolsTest = read("components", "layout", "ToolsRegion.test.tsx");
    expect(toolsTest).toContain("expect(navLinks()).toHaveLength(9);");
    expect(toolsTest).toContain('label === "系統管理"');
    expect(toolsTest).toContain('"系統設定", "系統管理", "自我進化"');
    expect(toolsTest).toContain("AT_BK_01_3_1");
  });

  it("AT_BK_01_1_E_1 原八列逐欄快照（id、label、order、enabled、mobile、roles、無專案與有專案的 href）與位置不變；match 探針：/sysadmin 與其子路徑只亮系統管理、相近路徑不亮、issues 與 self-improving 不被吃掉、沒有路徑被兩項同時命中", () => {
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
    expect(NAV_REGISTRY.slice(0, 8).map(snapshot)).toEqual([
      { id: "dashboard", label: "儀表板", order: 10, enabled: true, mobile: true, roles: null, hrefNoProject: "/", hrefProject: "/" },
      { id: "projects", label: "專案管理", order: 20, enabled: true, mobile: true, roles: null, hrefNoProject: "/projects", hrefProject: "/projects" },
      { id: "import", label: "BRD/PRD 匯入", order: 30, enabled: true, mobile: true, roles: null, hrefNoProject: "/import", hrefProject: "/import" },
      { id: "execute", label: "執行中心", order: 40, enabled: true, mobile: true, roles: null, hrefNoProject: "/projects", hrefProject: "/projects/p1/execute" },
      { id: "monitor", label: "監控中心", order: 50, enabled: true, mobile: true, roles: null, hrefNoProject: "/projects", hrefProject: "/projects/p1/monitor" },
      { id: "settings", label: "系統設定", order: 60, enabled: true, mobile: true, roles: null, hrefNoProject: "/settings", hrefProject: "/settings" },
      { id: "self-improving", label: "自我進化", order: 70, enabled: true, mobile: false, roles: null, hrefNoProject: "/self-improving", hrefProject: "/self-improving" },
      { id: "issues", label: "議題中心", order: 55, enabled: true, mobile: false, roles: null, hrefNoProject: "/issues", hrefProject: "/issues" },
    ]);

    const visible = visibleNavEntries(NAV_REGISTRY, "ADMIN");
    const active = (pathname: string) => activeNavEntry(visible, pathname)?.id ?? null;
    for (const hit of ["/sysadmin", "/sysadmin/backup", "/sysadmin/x"]) {
      expect(active(hit), hit).toBe("sysadmin");
      expect(ids(NAV_REGISTRY.filter((e) => e.match(hit))), hit).toEqual(["sysadmin"]);
    }
    for (const miss of ["/sysadmin-x", "/system", "/sysadmin_backup", "/sysadmins", "/", "/projects", ""]) expect(active(miss), JSON.stringify(miss)).not.toBe("sysadmin");
    expect(active("/sysadmin-x")).toBeNull();
    expect(active("/system")).toBeNull();
    expect(active("/sysadmin_backup")).toBeNull();
    expect(active("/issues")).toBe("issues");
    expect(active("/issues/x")).toBe("issues");
    expect(active("/self-improving")).toBe("self-improving");
    // 沒有任何代表路徑被兩項同時命中
    for (const pathname of [
      "/",
      "/projects",
      "/projects/p1/execute",
      "/projects/p1/monitor",
      "/import",
      "/settings",
      "/self-improving",
      "/issues",
      "/sysadmin",
      "/sysadmin/backup",
      "/sysadmin-x",
      "/unknown",
      "/login",
    ]) {
      expect(NAV_REGISTRY.filter((e) => e.match(pathname)).length, pathname).toBeLessThanOrEqual(1);
    }
    // href 對應真實存在的路由頁
    expect(byId("sysadmin").href).toBe("/sysadmin");
    expect(existsSync(path.join(ROOT, "app", "sysadmin", "page.tsx"))).toBe(true);
    expect(existsSync(path.join(ROOT, "app", "sysadmin", "backup", "page.tsx"))).toBe(true);
  });
});

describe("AT_BK_01_2 導覽可見與 active", () => {
  it("AT_BK_01_2_2 ADMIN、OPERATOR、VIEWER 的可見項皆含 sysadmin（label「系統管理」）；/sysadmin 與 /sysadmin/backup 的 active 皆為 sysadmin，其餘八項皆不 active", () => {
    for (const role of ["ADMIN", "OPERATOR", "VIEWER"] as const) {
      const visible = visibleNavEntries(NAV_REGISTRY, role);
      expect(visible.find((e) => e.id === "sysadmin")?.label, role).toBe("系統管理");
      for (const pathname of ["/sysadmin", "/sysadmin/backup"]) {
        expect(activeNavEntry(visible, pathname)?.id, `${role} ${pathname}`).toBe("sysadmin");
        expect(
          visible.filter((e) => e.match(pathname)).map((e) => e.id),
          `${role} ${pathname}：其餘八項皆不 active`,
        ).toEqual(["sysadmin"]);
      }
    }
  });
});

describe("AT_BK_01_3 行動版 Tab", () => {
  it("AT_BK_01_3_E_1 mobile 為 true 的項數恰 6、id 依序為 dashboard、projects、import、execute、monitor、settings；sysadmin 的 mobile 為 false", () => {
    const mobile = NAV_REGISTRY.filter((e) => e.mobile);
    expect(mobile).toHaveLength(6);
    expect(ids(mobile)).toEqual(["dashboard", "projects", "import", "execute", "monitor", "settings"]);
    expect(byId("sysadmin").mobile).toBe(false);
  });
});
