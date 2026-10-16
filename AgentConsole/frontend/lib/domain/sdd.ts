/**
 * 監控頁「AISDLC_SDD 引擎」卡的顯示規則（契約 §1.7.1、§4.3 M-20；v1.4 D-16，API-ENG-01）。純函式、不依賴 React。
 * 唯讀：Console 不寫 SDD 目錄與 FSM 狀態檔；FSM 的巢狀內容（decisionTrace、humanPending.items…）是「檔案寫什麼就是什麼」，
 * 保留 snake_case 鍵與原值，畫面顯示不轉譯、不重排欄位，使「FSM 檔 ↔ API ↔ 畫面」可逐值比對（NFR-OBS-01、E2E-15 第 5 列）。
 */
import type { SddEngineReason, SddFsmState, SddHumanPending, SddProjectEntry } from "@/lib/api/types";
import { formatClock, formatDate } from "@/lib/format";

/**
 * `reason` 的中文文案（契約 M-20；回應欄位的值，不是 ApiError.reason）：
 * 前三個是引擎不可用（available=false）；後兩個是「引擎可用、但所選專案取不到 FSM」（available=true、fsm=null）。
 */
export const SDD_REASON_MESSAGE: Record<SddEngineReason, string> = {
  bridge_unreachable: "Engine Bridge 無法連線",
  sdd_unavailable: "找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）",
  bridge_error: "Engine Bridge 回應異常",
  fsm_not_found: "找不到所選專案的 FSM 狀態檔",
  fsm_state_unreadable: "FSM 狀態檔無法讀取",
};

/** `available=true` 且 `projects=[]`：SDD 目錄存在、但 SDD runtime 還沒跑過（正常狀態，不是錯誤）。 */
export const SDD_EMPTY_MESSAGE = "尚無 FSM 狀態檔（SDD runtime 執行後才會產生）";

/** 後端日後新增 reason 值：照樣顯示（附原值），不崩潰也不吞掉。 */
export function sddReasonMessage(reason: string | null | undefined): string | null {
  if (!reason) return null;
  return (SDD_REASON_MESSAGE as Record<string, string>)[reason] ?? `引擎回報：${reason}`;
}

/**
 * 預設選哪個 FSM 專案（契約 M-20）：上次選的且仍在清單內者（localStorage 記住，只是方便），否則清單第一個；沒有專案回 null。
 * 清單順序＝Bridge 順序（專案名不分大小寫升冪），不重排。
 */
export function pickSddProject(projects: readonly Pick<SddProjectEntry, "project">[] | undefined, preferred: string | null): string | null {
  if (!projects || projects.length === 0) return null;
  if (preferred && projects.some((p) => p.project === preferred)) return preferred;
  return projects[0].project;
}

/** 巢狀內容的欄位值轉成可顯示的字串：字串與數字照原值、布林轉字、其餘（缺值、null、物件）顯示「—」。 */
export function sddText(value: unknown): string {
  if (typeof value === "string") return value === "" ? "—" : value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "—";
}

/** FSM 檔裡的時間（ISO-8601 字串，原樣）轉本機時區的「2026-10-16 09:02:03」；解析不了就顯示原字串、缺值顯示「—」。 */
export function sddTime(value: unknown): string {
  if (typeof value !== "string" || value === "") return "—";
  const date = formatDate(value);
  return date === "—" ? value : `${date} ${formatClock(value)}`;
}

/** 「Sprint N」；缺值（null）顯示「—」。 */
export function sddSprint(sprint: number | null | undefined): string {
  return typeof sprint === "number" ? `Sprint ${sprint}` : "—";
}

/**
 * 待人工（契約 M-20）：count＝0 顯示「無」、1 顯示「等待人工確認」（並可展開看 items[0].entered_at）。
 * 現行 FSM 的 human_pending_tracking 是單一映射，count 實務上只會是 0 或 1；若日後 schema 改成多筆，count 大於 1 時註明件數。
 * enteredAt＝每個項目的 entered_at（轉本機時區；缺值「—」），最多列 5 個（API 的 items 本來就只回尾 5 筆）。
 */
export function sddHumanPending(hp: SddHumanPending | undefined): { count: number; label: string; enteredAt: string[] } {
  const count = hp?.count ?? 0;
  const label = count <= 0 ? "無" : count === 1 ? "等待人工確認" : `等待人工確認（${count} 項）`;
  return { count, label, enteredAt: count > 0 ? (hp?.items ?? []).slice(0, 5).map((item) => sddTime(item?.entered_at)) : [] };
}

export type SddDecisionRow = { ts: string; from: string; to: string; reason: string };

/**
 * 最近決策（契約 M-20）：`decisionTrace` 是 API 給的尾 5 筆（舊→新），卡片倒序顯示（新→舊），每筆 `from → to` 與 `reason`；
 * 這裡再保險取最後 `limit` 筆（API 已截，缺席或不是陣列時當作空）。
 */
export function sddRecentDecisions(trace: SddFsmState["decisionTrace"] | undefined, limit = 5): SddDecisionRow[] {
  if (!Array.isArray(trace)) return [];
  return trace
    .slice(-limit)
    .reverse()
    .map((d) => ({ ts: sddTime(d?.ts), from: sddText(d?.from), to: sddText(d?.to), reason: sddText(d?.reason) }));
}
