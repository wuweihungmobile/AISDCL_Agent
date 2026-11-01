import { describe, expect, it } from "vitest";

import { HELP_PAGES, HELP_ROUTES, NO_STATE_PAGES, PENDING_HELP_PAGES, helpForPath } from "@/lib/help/registry";
import { DELIVERED_NAV_ROWS } from "@/tests/helpers/navDelivered";
import { NAV_REGISTRY, activeNavEntry, navHref, visibleNavEntries, type NavEntry } from "./registry";

/**
 * 執行中心／監控中心的無專案入口頁——導覽登記表那一半（TCS-ExecMonitorEntry-20261101 F-905、AC-953-1、AC-953-3；W-E2；Console PRD §0.8，掌舵者 2026-11-01 真機回報）：
 * 側欄「執行中心」「監控中心」在沒有目的專案時，改退回各自的入口頁 /execute、/monitor（原本退回 /projects，使用者點了只落在專案管理的空狀態，網址、標題與 active 項都不是他要的）；
 * 有專案時照舊直達 /projects/<id>/execute、/projects/<id>/monitor。入口頁只在「深連結或零專案」時出現，三層解析（useCurrentProjectId）不變。
 * 本檔 AT：AT_953_1_1、AT_953_1_2、AT_953_1_E_1（登記表）、AT_953_3_1（每頁說明接入）；入口頁元件的 AT 住 components/domain/entry/CenterEntryView.test.tsx。
 * 判定指令：npx vitest run lib/nav/exec-monitor-entry.test.ts -t "<AT 底線形>"
 */
const byId = (id: string) => NAV_REGISTRY.find((e) => e.id === id) as NavEntry;
const ids = (list: ReadonlyArray<NavEntry>) => list.map((e) => e.id);
/** 登記表層級（不看可見性、角色）命中某路徑的項 id。 */
const hitsOf = (pathname: string) => ids(NAV_REGISTRY.filter((e) => e.match(pathname)));

/** 登記項自己的頁面路徑：字串 href 直取；函式型以「有專案」解析（沿 registry.test.ts 的 ownPath；無專案的入口路徑另由本檔 AT_953_1_2 逐項釘住認領）。 */
const ownPath = (e: NavEntry): string => navHref(e, { currentProjectId: "p1" }).split(/[?#]/)[0];

/** 每個登記項自己的頁面路徑都恰被該項認領（沒有別項同時命中、也不是沒人認領）；沿 registry.test.ts 的 ownPathProblems 判準，這裡是同一支判準的副本（測試內助手，不改原檔）。 */
function ownPathProblems(registry: ReadonlyArray<NavEntry>): string[] {
  const out: string[] = [];
  for (const e of registry) {
    const own = ownPath(e);
    const hits = ids(registry.filter((x) => x.match(own)));
    if (hits.length !== 1 || hits[0] !== e.id) out.push(`${e.id} 的頁面 ${own} 被 ${hits.length === 0 ? "無項" : hits.join("、")} 認領`);
  }
  return out;
}

describe("AT_953_1 登記表：無專案退回入口頁、入口路徑認領（W-E2）", () => {
  it("AT_953_1_1 執行中心與監控中心的 href：沒有專案時是 /execute、/monitor（不再退回 /projects），有專案時仍帶專案 id", () => {
    for (const id of ["execute", "monitor"] as const) {
      const entry = byId(id);
      expect(typeof entry.href, `${id}.href 仍是函式型（有專案與無專案兩個分支）`).toBe("function");
      expect(navHref(entry, { currentProjectId: null }), `${id} 沒有專案`).toBe(`/${id}`);
      expect(navHref(entry, { currentProjectId: "p1" }), `${id} 有專案`).toBe(`/projects/p1/${id}`);
    }
  });

  it("AT_953_1_2 OPERATOR 可見項在 /execute、/monitor 上 active 的恰為執行中心、監控中心；登記表層級各只命中一項；/execute/x、/executes、/monitoring 沒有任何項命中（不 fallback 成專案管理）；每項自己的頁面仍恰被自己認領", () => {
    const visible = visibleNavEntries(NAV_REGISTRY, "OPERATOR");
    expect(activeNavEntry(visible, "/execute")?.id).toBe("execute");
    expect(activeNavEntry(visible, "/monitor")?.id).toBe("monitor");
    expect(hitsOf("/execute")).toEqual(["execute"]);
    expect(hitsOf("/monitor")).toEqual(["monitor"]);
    // ⚖6：入口頁沒有子頁，match 只認精確路徑——子路徑與相近字串一律不認領，也不被專案管理吃掉
    for (const miss of ["/execute/x", "/executes", "/monitoring"]) {
      expect(hitsOf(miss), miss).toEqual([]);
      expect(activeNavEntry(visible, miss), miss).toBeNull();
    }
    expect(ownPathProblems(NAV_REGISTRY)).toEqual([]);
    // 對照組：判準本身有鑑別力——把執行中心的 match 換成永假，它自己的頁面就沒人認領
    const broken = NAV_REGISTRY.map((e) => (e.id === "execute" ? { ...e, match: () => false } : e));
    expect(ownPathProblems(broken)).toEqual(["execute 的頁面 /projects/p1/execute 被 無項 認領"]);
  });

  it("AT_953_1_E_1 本鍵不改任何快照欄：已交付列前綴的 id、label、order、mobile、enabled、roles 與共用快照相同；專案管理不認 /execute 與 /monitor；專案頁 /projects/p1/execute 與 /monitor 仍只亮各自的項", () => {
    const rows = NAV_REGISTRY.slice(0, DELIVERED_NAV_ROWS.length).map((e) => [e.id, e.label, e.order, e.mobile, e.enabled, e.roles ?? null]);
    expect(rows).toEqual(DELIVERED_NAV_ROWS);
    expect(byId("projects").match("/execute")).toBe(false);
    expect(byId("projects").match("/monitor")).toBe(false);
    expect(hitsOf("/projects/p1/execute")).toEqual(["execute"]);
    expect(hitsOf("/projects/p1/monitor")).toEqual(["monitor"]);
  });
});

describe("AT_953_3 每頁說明接入（W-E3）", () => {
  it("AT_953_3_1 /execute、/monitor 解析到 execute-entry、monitor-entry；兩頁已寫（固定頁名「執行中心」「監控中心」、states 為空且登記在 NO_STATE_PAGES）、不走 pending；專案頁的說明不被入口頁取代", () => {
    const cases = [
      { route: "/execute", id: "execute-entry", title: "執行中心" },
      { route: "/monitor", id: "monitor-entry", title: "監控中心" },
    ] as const;
    for (const { route, id, title } of cases) {
      expect(HELP_ROUTES[route], `HELP_ROUTES[${route}]`).toBe(id);
      expect(helpForPath(route), `helpForPath(${route})`).toBe(id);
      const page = HELP_PAGES[id];
      expect(page?.id, `${id} 已寫入 HELP_PAGES`).toBe(id);
      expect(page?.title).toBe(title);
      expect(page?.states, `${id} 沒有會變動的狀態`).toEqual([]);
      expect(NO_STATE_PAGES, `${id} 登記在 NO_STATE_PAGES（states 為空者必在此）`).toContain(id);
    }
    expect(PENDING_HELP_PAGES, "兩頁直接寫實，不走 pending").toEqual([]);
    // ⚖4：入口頁的說明是新增兩條，不是改掉專案頁的——專案執行頁、專案監控頁各自的說明不變
    expect(helpForPath("/projects/p1/execute")).toBe("execute");
    expect(helpForPath("/projects/p1/monitor")).toBe("monitor");
  });
});
