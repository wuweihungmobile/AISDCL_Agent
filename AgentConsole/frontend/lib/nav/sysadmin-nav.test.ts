import { existsSync } from "node:fs";
import path from "node:path";
import { Database, DatabaseBackup } from "lucide-react";
import { describe, expect, it } from "vitest";

import { DELIVERED_DISPLAY_IDS, DELIVERED_MOBILE_IDS, DELIVERED_NAV_IDS, DELIVERED_NAV_ROWS, deliveredIdsIn, deliveredPrefix } from "@/tests/helpers/navDelivered";
import { NAV_REGISTRY, activeNavEntry, navHref, visibleNavEntries, type NavEntry } from "./registry";

/**
 * 系統管理的導覽接入（TCS-SysAdminBackup-20261027 R-BK-01、R-BK-03、R-BK-61；AT-BK-01-1-1、01-1-2、01-1-E-1、01-2-2、01-3-E-1，載具 FN）：登記表第九項 `sysadmin` 加在陣列末尾
 * （index 8；label「系統管理」、href `/sysadmin`、order 65、mobile false、roles 缺、icon `Database`）、原八列的各欄與位置不變（self-improving 仍 `[6]`、issues 仍 `[7]`）、
 * 顯示序由 order 決定（settings 60、sysadmin 65、self-improving 70）、match 只命中 `/sysadmin` 與其子路徑。既有導覽測試（issues-nav.test.ts、registry.test.ts、ToolsRegion.test.tsx）當時要同步釘值（AT-BK-01-1-2）。
 * 判定指令：npx vitest run lib/nav/sysadmin-nav.test.ts -t "<AT 底線形>"
 * OBS-SI-321 根治：項數、id 清單、顯示序、order／icon 集合大小不再釘「恰九項」，改為已交付列的前綴快照（tests/helpers/navDelivered.ts，四個導覽測試檔共用）加上由登記表自身推導的唯一性斷言；
 * AT_BK_01_1_2 不再讀別檔原始碼比字面（那是第二份真相的鎖），改為直接以 NAV_REGISTRY 與共用快照核對「既有導覽測試所依賴的每個事實」。測試標題與 AT id 沿 TCS 字樣不動。
 * 之後登記表在末尾多加一列新功能，本檔不必再改。
 */
const ROOT = process.cwd();
const byId = (id: string) => NAV_REGISTRY.find((e) => e.id === id) as NavEntry;
const ids = (list: ReadonlyArray<NavEntry>) => list.map((e) => e.id);

describe("AT_BK_01_1 登記表第九項與顯示序", () => {
  it("AT_BK_01_1_1 NAV_REGISTRY 恰九項、id 依陣列序；[6] 是 self-improving、[7] 是 issues、[8] 是 sysadmin；sysadmin 各欄逐值（icon 是 Database、不是 DatabaseBackup）；四種角色的顯示序；order 唯一、icon 互異", () => {
    // 前綴比對（OBS-SI-321）：已交付九列的 id 依陣列序相符；登記表在末尾多加的列不影響本斷言
    expect(NAV_REGISTRY.length, "登記表不得少於已交付列數").toBeGreaterThanOrEqual(DELIVERED_NAV_IDS.length);
    expect(ids(deliveredPrefix(NAV_REGISTRY))).toEqual(DELIVERED_NAV_IDS);
    expect(NAV_REGISTRY[6].id).toBe("self-improving");
    expect(NAV_REGISTRY[7].id).toBe("issues");
    const sysadmin = byId("sysadmin");
    expect(NAV_REGISTRY[8]).toBe(sysadmin);
    expect(sysadmin).toMatchObject({ id: "sysadmin", label: "系統管理", href: "/sysadmin", order: 65, enabled: true, mobile: false });
    expect(sysadmin.roles, "roles 缺＝所有已登入角色皆可見").toBeUndefined();
    expect(sysadmin.icon).toBe(Database);
    expect(sysadmin.icon).not.toBe(DatabaseBackup);
    expect(typeof sysadmin.match).toBe("function");
    // 已交付九列在可見項中的相對顯示序不變（日後新增的列夾在中間也不影響）
    for (const role of ["ADMIN", "OPERATOR", "VIEWER", undefined] as const) {
      expect(deliveredIdsIn(ids(visibleNavEntries(NAV_REGISTRY, role))), String(role)).toEqual(DELIVERED_DISPLAY_IDS);
    }
    expect(new Set(ids(NAV_REGISTRY)).size).toBe(NAV_REGISTRY.length);
    expect(new Set(NAV_REGISTRY.map((e) => e.order)).size).toBe(NAV_REGISTRY.length);
    expect(new Set(NAV_REGISTRY.map((e) => e.icon)).size).toBe(NAV_REGISTRY.length);
    // 顯示序的 order：settings 60 < sysadmin 65 < self-improving 70
    expect([byId("settings").order, sysadmin.order, byId("self-improving").order]).toEqual([60, 65, 70]);
  });

  it("AT_BK_01_1_2 既有導覽測試已同步：issues-nav.test.ts 的長度、id 清單、顯示序含 sysadmin 且 NAV_REGISTRY[7] 斷言仍在；registry.test.ts 的 AT_950_10_E_1 改述為「原八列不變，另加系統管理」並補第九列；ToolsRegion.test.tsx 補了九個連結與 max-md:hidden 判準", () => {
    // OBS-SI-321：不再讀別檔原始碼比字面（那是第二份真相的鎖）——既有導覽測試所依賴的每個事實，改直接從 NAV_REGISTRY 與共用的已交付快照核對。
    // issues-nav.test.ts 依賴的事實：登記表含第九列 sysadmin（索引 8，已交付九列的最後一列）、NAV_REGISTRY[7] 仍是 issues、
    // 三種角色與未知角色的顯示序都含 sysadmin（系統設定之後、自我進化之前）、order 與 icon 集合大小等於登記表長度
    expect(NAV_REGISTRY[8].id).toBe("sysadmin");
    expect(DELIVERED_NAV_IDS[DELIVERED_NAV_IDS.length - 1]).toBe("sysadmin");
    expect(NAV_REGISTRY[7].id).toBe("issues");
    for (const role of ["ADMIN", "OPERATOR", "VIEWER", undefined] as const) {
      const display = ids(visibleNavEntries(NAV_REGISTRY, role));
      expect(deliveredIdsIn(display), String(role)).toEqual(DELIVERED_DISPLAY_IDS);
      expect(
        display.indexOf("settings") < display.indexOf("sysadmin") && display.indexOf("sysadmin") < display.indexOf("self-improving"),
        `${String(role)}：系統管理排在系統設定之後、自我進化之前`,
      ).toBe(true);
    }
    expect(new Set(NAV_REGISTRY.map((e) => e.order)).size).toBe(NAV_REGISTRY.length);
    expect(new Set(NAV_REGISTRY.map((e) => e.icon)).size).toBe(NAV_REGISTRY.length);

    // registry.test.ts（AT_950_10_E_1「原八列不變，另加系統管理」）依賴的事實：登記表第九列的各欄＝共用快照的第九列、
    // /sysadmin 與 /sysadmin/backup 由系統管理認領、/sysadmin-x 無人認領、字串型 href 含 /issues 與 /sysadmin（依序）
    const rows = NAV_REGISTRY.map((e) => [e.id, e.label, e.order, e.mobile, e.enabled, e.roles ?? null]);
    expect(rows[8]).toEqual(DELIVERED_NAV_ROWS[8]);
    expect(DELIVERED_NAV_ROWS[8][0]).toBe("sysadmin");
    const visible = visibleNavEntries(NAV_REGISTRY, "ADMIN");
    expect(activeNavEntry(visible, "/sysadmin")?.id).toBe("sysadmin");
    expect(activeNavEntry(visible, "/sysadmin/backup")?.id).toBe("sysadmin");
    expect(activeNavEntry(visible, "/sysadmin-x")).toBeNull();
    const stringHrefs = NAV_REGISTRY.map((e) => e.href).filter((h): h is string => typeof h === "string");
    expect(stringHrefs.indexOf("/issues")).toBeGreaterThanOrEqual(0);
    expect(stringHrefs.indexOf("/sysadmin")).toBeGreaterThan(stringHrefs.indexOf("/issues"));

    // ToolsRegion.test.tsx 依賴的事實：三種角色的可見項都含「系統管理」，且其 mobile 為 false（元件據此落成 max-md:hidden）；被同步的三個測試檔仍在
    for (const role of ["ADMIN", "OPERATOR", "VIEWER"] as const)
      expect(
        visibleNavEntries(NAV_REGISTRY, role).map((e) => e.label),
        role,
      ).toContain("系統管理");
    expect(byId("sysadmin").mobile).toBe(false);
    for (const segments of [
      ["lib", "nav", "issues-nav.test.ts"],
      ["lib", "nav", "registry.test.ts"],
      ["components", "layout", "ToolsRegion.test.tsx"],
    ]) {
      expect(existsSync(path.join(ROOT, ...segments)), segments.join("/")).toBe(true);
    }
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
    // 已交付列中 mobile 為 true 的恰為前六項（依序）；整張登記表為 true 的項數不超過 6（新功能預設 false，窄螢幕實測後才升）；sysadmin 的 mobile 為 false
    const mobile = NAV_REGISTRY.filter((e) => e.mobile);
    expect(ids(deliveredPrefix(NAV_REGISTRY).filter((e) => e.mobile))).toEqual(DELIVERED_MOBILE_IDS);
    expect(mobile.length).toBeLessThanOrEqual(6);
    expect(byId("sysadmin").mobile).toBe(false);
  });
});
