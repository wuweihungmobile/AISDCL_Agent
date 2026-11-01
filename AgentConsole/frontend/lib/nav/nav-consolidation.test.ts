import { Upload } from "lucide-react";
import { describe, expect, it } from "vitest";

import type { Role } from "@/lib/api/types";
import { DELIVERED_DISPLAY_IDS, DELIVERED_NAV_ROWS } from "@/tests/helpers/navDelivered";
import { NAV_REGISTRY, activeNavEntry, navHref, visibleNavEntries, type NavEntry } from "./registry";

/**
 * Console 側欄導覽整併（TCS-ConsoleNavConsolidation-20261101 F-904；AC-952-1；W-N1、W-N2；Console PRD §0.7，掌舵者 2026-11-01 裁決）：
 * `import` 列停用（`enabled: false`、不刪列）、`settings` order 80、`sysadmin` order 75 ⇒ 側欄八項，序為 儀表板、專案管理、執行中心、監控中心、議題中心、自我進化、系統管理、系統設定；
 * 停用列的 /import 路由與 match 認領不變（登記表層級仍只有 import 命中 /import），但可見項裡沒有任何項 active（也不 fallback 成專案管理）。
 * 本檔 AT：AT_952_1_1、AT_952_1_2、AT_952_1_E_1、AT_952_1_E_2（FN）；AT_952_1_3 要真渲染，住 components/layout/ToolsRegion.test.tsx。
 * 判定指令：npx vitest run lib/nav/nav-consolidation.test.ts -t "<AT 底線形>"
 * 期望值是 TCS 的字面事實（九列的逐欄值、八項顯示序），所以逐字釘；與 registry.test.ts 的「不釘項數」政策（OBS-SI-321）是兩件事——
 * 之後登記表在末尾多加新列，本檔「恰九列、恰八項」的期望要隨該功能的 TCS 勘誤一起改（那是有意識的變更）。
 */
const ROLES: ReadonlyArray<Role | undefined> = ["ADMIN", "OPERATOR", "VIEWER", undefined];
const ids = (list: ReadonlyArray<NavEntry>) => list.map((e) => e.id);
const labelsOf = (list: ReadonlyArray<NavEntry>) => list.map((e) => e.label);

/** 整併後的九列（陣列序不變）：[id, label, order, enabled, mobile]。 */
const ROWS: ReadonlyArray<readonly [id: string, label: string, order: number, enabled: boolean, mobile: boolean]> = [
  ["dashboard", "儀表板", 10, true, true],
  ["projects", "專案管理", 20, true, true],
  ["import", "BRD/PRD 匯入", 30, false, true],
  ["execute", "執行中心", 40, true, true],
  ["monitor", "監控中心", 50, true, true],
  ["settings", "系統設定", 80, true, true],
  ["self-improving", "自我進化", 70, true, false],
  ["issues", "議題中心", 55, true, false],
  ["sysadmin", "系統管理", 75, true, false],
];
/** 整併後側欄的顯示序（W-N2；不含停用的 import）。 */
const VISIBLE_IDS = ["dashboard", "projects", "execute", "monitor", "issues", "self-improving", "sysadmin", "settings"];
/** 整併後底部 Tab 顯示的五項（mobile 為 true 的可見項；⚖3 不補第六項）。 */
const MOBILE_LABELS = ["儀表板", "專案管理", "執行中心", "監控中心", "系統設定"];

/**
 * 每個登記項自己的頁面路徑（字串 href 直取、函式型以「有專案」解析）都恰被該項認領——沿 registry.test.ts 的 ownPathProblems 判準。
 * 在這裡重寫而不自 registry.test.ts 匯入：那個檔的函式沒有 export，且匯入測試檔會把它的整組 describe 一併註冊進本檔。
 */
const ownPath = (e: NavEntry): string => navHref(e, { currentProjectId: "p1" }).split(/[?#]/)[0];
function ownPathProblems(registry: ReadonlyArray<NavEntry>): string[] {
  const out: string[] = [];
  for (const e of registry) {
    const own = ownPath(e);
    const hits = ids(registry.filter((x) => x.match(own)));
    if (hits.length !== 1 || hits[0] !== e.id) out.push(`${e.id} 的頁面 ${own} 被 ${hits.length === 0 ? "無項" : hits.join("、")} 認領`);
  }
  return out;
}

describe("AT_952_1 登記表改值與側欄顯示序（W-N1、W-N2）", () => {
  it("AT_952_1_1 真登記表九列 id 依陣列序不變；[2] 是 import 且 enabled 為 false、其餘欄（label、href、match、order 30、mobile true、icon Upload、roles 缺）逐字不變；settings order 80、sysadmin order 75，其餘七列 order 不變；id 與 order 唯一、icon 互異", () => {
    // 九列 id 依陣列序（位置不變：[2] import、[5] settings、[6] self-improving、[7] issues、[8] sysadmin）
    expect(ids(NAV_REGISTRY)).toEqual(ROWS.map((r) => r[0]));
    // 逐列逐欄：id、label、order、enabled、mobile——只有 import.enabled、settings.order、sysadmin.order 三處與整併前不同
    expect(NAV_REGISTRY.map((e) => [e.id, e.label, e.order, e.enabled, e.mobile])).toEqual(ROWS.map((r) => [...r]));

    const imp = NAV_REGISTRY[2];
    expect(imp.id).toBe("import");
    expect(imp.enabled, "import 停用（不刪列）").toBe(false);
    expect(imp.label).toBe("BRD/PRD 匯入");
    expect(imp.href).toBe("/import");
    expect(navHref(imp, { currentProjectId: null })).toBe("/import");
    expect(navHref(imp, { currentProjectId: "p1" })).toBe("/import");
    expect(imp.order).toBe(30);
    expect(imp.mobile, "⚖5：停用列的 mobile 欄保留 true").toBe(true);
    expect(imp.icon).toBe(Upload);
    expect(imp.roles, "roles 缺＝所有已登入角色（停用前後都沒有 roles）").toBeUndefined();
    // match 以 /import 起頭：本身與其子路徑為真，別項的路徑為假
    for (const hit of ["/import", "/import/x"]) expect(imp.match(hit), hit).toBe(true);
    for (const miss of ["/", "/projects", "/settings", "/self-improving", "/issues", "/sysadmin", ""]) expect(imp.match(miss), JSON.stringify(miss)).toBe(false);

    // 兩個改值的列與其餘七列的 order（整併前：settings 60、sysadmin 65；其餘不變）
    const orderOf = (id: string) => (NAV_REGISTRY.find((e) => e.id === id) as NavEntry).order;
    expect(orderOf("settings")).toBe(80);
    expect(orderOf("sysadmin")).toBe(75);
    expect([orderOf("dashboard"), orderOf("projects"), orderOf("execute"), orderOf("monitor"), orderOf("issues"), orderOf("self-improving")]).toEqual([10, 20, 40, 50, 55, 70]);

    // 唯一性與互異（整張登記表）
    expect(new Set(ids(NAV_REGISTRY)).size).toBe(NAV_REGISTRY.length);
    expect(new Set(NAV_REGISTRY.map((e) => e.order)).size).toBe(NAV_REGISTRY.length);
    expect(new Set(NAV_REGISTRY.map((e) => e.icon)).size).toBe(NAV_REGISTRY.length);
  });

  it("AT_952_1_2 ADMIN、OPERATOR、VIEWER 與角色未知四種情況，visibleNavEntries 都回八項、id 序 dashboard、projects、execute、monitor、issues、self-improving、sysadmin、settings，不含 import；DELIVERED_DISPLAY_IDS 濾掉停用列後與之相等", () => {
    for (const role of ROLES) {
      const visible = visibleNavEntries(NAV_REGISTRY, role);
      expect(ids(visible), String(role)).toEqual(VISIBLE_IDS);
      expect(visible, String(role)).toHaveLength(8);
      expect(ids(visible), `${String(role)}：停用的 import 不在可見項`).not.toContain("import");
    }
    // 共用快照的顯示序（依 order 升冪）濾掉 enabled 為 false 的列後，就是上面那八項
    const enabledIds = new Set(DELIVERED_NAV_ROWS.filter((row) => row[4]).map((row) => row[0]));
    expect(DELIVERED_DISPLAY_IDS.filter((id) => enabledIds.has(id))).toEqual(VISIBLE_IDS);
    // 對照組（斷言有鑑別力）：import 若啟用，同一個函式就回九項、import 排在專案管理之後
    const reEnabled = NAV_REGISTRY.map((e) => (e.id === "import" ? { ...e, enabled: true } : e));
    expect(ids(visibleNavEntries(reEnabled, "OPERATOR")), "對照組：啟用 import 後會多一項").toEqual([
      "dashboard",
      "projects",
      "import",
      "execute",
      "monitor",
      "issues",
      "self-improving",
      "sysadmin",
      "settings",
    ]);
  });

  it("AT_952_1_E_1 可見項（OPERATOR）下 /import 與其子路徑沒有任何項 active；登記表層級以 /import 計算 match 的命中集合恰為 import；每列自己的頁面仍恰被自己認領（ownPathProblems 空）", () => {
    const visible = visibleNavEntries(NAV_REGISTRY, "OPERATOR");
    expect(activeNavEntry(visible, "/import")).toBeNull();
    expect(activeNavEntry(visible, "/import/x")).toBeNull();
    // 登記表層級（不看 enabled）：/import 仍只由 import 認領，match 互斥不變
    expect(ids(NAV_REGISTRY.filter((e) => e.match("/import")))).toEqual(["import"]);
    expect(ownPathProblems(NAV_REGISTRY)).toEqual([]);
    // 其餘入口的 active 不受影響（專案管理不吃掉 /import、儀表板仍只亮 /）
    expect(activeNavEntry(visible, "/projects")?.id).toBe("projects");
    expect(activeNavEntry(visible, "/")?.id).toBe("dashboard");
    // 對照組（斷言有鑑別力）：import 若啟用，/import 會亮它；match 永假則 ownPathProblems 回報「無項認領」
    const reEnabled = visibleNavEntries(
      NAV_REGISTRY.map((e) => (e.id === "import" ? { ...e, enabled: true } : e)),
      "OPERATOR",
    );
    expect(activeNavEntry(reEnabled, "/import")?.id, "對照組：啟用 import 後 /import 會亮它").toBe("import");
    expect(ownPathProblems(NAV_REGISTRY.map((e) => (e.id === "import" ? { ...e, match: () => false } : e)))).toEqual(["import 的頁面 /import 被 無項 認領"]);
  });

  it("AT_952_1_E_2 共用快照 DELIVERED_NAV_ROWS 與登記表前綴逐欄相等（id、label、order、mobile、enabled、roles）；快照第 3 列 enabled 為 false、settings 80、sysadmin 75；mobile 為 true 的可見項恰五項", () => {
    expect(NAV_REGISTRY.length, "登記表不得少於已交付列數").toBeGreaterThanOrEqual(DELIVERED_NAV_ROWS.length);
    expect(NAV_REGISTRY.slice(0, DELIVERED_NAV_ROWS.length).map((e) => [e.id, e.label, e.order, e.mobile, e.enabled, e.roles ?? null])).toEqual(DELIVERED_NAV_ROWS);
    // 快照自己的三處改值（整併前：import enabled true、settings 60、sysadmin 65）
    expect(DELIVERED_NAV_ROWS[2], "快照第 3 列").toEqual(["import", "BRD/PRD 匯入", 30, true, false, null]);
    expect(DELIVERED_NAV_ROWS[2][4], "快照第 3 列的 enabled").toBe(false);
    const snapshotOrder = (id: string) => (DELIVERED_NAV_ROWS.find((row) => row[0] === id) as (typeof DELIVERED_NAV_ROWS)[number])[2];
    expect(snapshotOrder("settings")).toBe(80);
    expect(snapshotOrder("sysadmin")).toBe(75);
    // 底部 Tab（<768）顯示的恰五項：mobile 為 true 的可見項（停用的 import 雖然 mobile 仍為 true，但不是可見項）
    for (const role of ROLES) {
      expect(labelsOf(visibleNavEntries(NAV_REGISTRY, role).filter((e) => e.mobile)), String(role)).toEqual(MOBILE_LABELS);
    }
  });
});
