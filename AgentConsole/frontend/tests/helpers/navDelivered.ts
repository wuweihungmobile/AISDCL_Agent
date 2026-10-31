import type { Role } from "@/lib/api/types";

/**
 * 導覽登記表的「已交付列」快照（append-only 棘輪；OBS-SI-321 根治）——**全 repo 測試側唯一一份**登記表內容的副本：
 * registry.test.ts、issues-nav.test.ts、sysadmin-nav.test.ts、ToolsRegion.test.tsx 都從這裡取已交付列，不各持一份、不釘登記表的項數。
 *
 * 用法（前綴比對）：只比對登記表的前 `DELIVERED_NAV_ROWS.length` 列。新功能的導覽入口依慣例加在陣列**末尾**，所以在登記表多加一列時，
 * 這四個測試檔都不必改；改動既有列的欄位、換位置、刪列才會紅——那是有意識的變更，要同步改這份快照（連同該功能自己的 TCS 勘誤）。
 * 唯一性、mobile 上限、icon 互異、href 對應真路由、match 互斥一律以 `NAV_REGISTRY` 自身推導，不看這份快照。
 *
 * 欄位：[id, label, order, mobile, enabled, roles]；roles 缺＝null。
 */
export type DeliveredNavRow = readonly [id: string, label: string, order: number, mobile: boolean, enabled: boolean, roles: ReadonlyArray<Role> | null];

export const DELIVERED_NAV_ROWS: ReadonlyArray<DeliveredNavRow> = [
  ["dashboard", "儀表板", 10, true, true, null],
  ["projects", "專案管理", 20, true, true, null],
  ["import", "BRD/PRD 匯入", 30, true, true, null],
  ["execute", "執行中心", 40, true, true, null],
  ["monitor", "監控中心", 50, true, true, null],
  ["settings", "系統設定", 60, true, true, null],
  ["self-improving", "自我進化", 70, false, true, null],
  ["issues", "議題中心", 55, false, true, null],
  ["sysadmin", "系統管理", 65, false, true, null],
];

/** 已交付列的 id，依陣列序。 */
export const DELIVERED_NAV_IDS: ReadonlyArray<string> = DELIVERED_NAV_ROWS.map((row) => row[0]);

/** 已交付列的 id，依顯示序（order 升冪；同序依陣列序——Array.prototype.sort 是穩定排序）。 */
export const DELIVERED_DISPLAY_IDS: ReadonlyArray<string> = [...DELIVERED_NAV_ROWS].sort((a, b) => a[2] - b[2]).map((row) => row[0]);

/** 已交付列中 mobile 為 true 的 id（<768 的底部 Tab 顯示的那幾項），依顯示序。 */
export const DELIVERED_MOBILE_IDS: ReadonlyArray<string> = [...DELIVERED_NAV_ROWS]
  .sort((a, b) => a[2] - b[2])
  .filter((row) => row[3])
  .map((row) => row[0]);

/** 已交付列中 mobile 為 true 的 label，依顯示序（＝<768 底部 Tab 的六個入口）。 */
export const DELIVERED_MOBILE_LABELS: ReadonlyArray<string> = [...DELIVERED_NAV_ROWS]
  .sort((a, b) => a[2] - b[2])
  .filter((row) => row[3])
  .map((row) => row[1]);

/** 登記表的前 N 列（N＝已交付列數）：已交付列在陣列裡的位置不得變，所以用前綴切，不用 id 查表。 */
export function deliveredPrefix<T>(registry: ReadonlyArray<T>): T[] {
  return registry.slice(0, DELIVERED_NAV_ROWS.length);
}

/** 可見項清單裡屬於已交付列的那幾項，依其在清單中的順序（用來比對已交付列的相對顯示序；日後新增的列夾在中間也不影響）。 */
export function deliveredIdsIn(ids: ReadonlyArray<string>): string[] {
  return ids.filter((id) => DELIVERED_NAV_IDS.includes(id));
}
