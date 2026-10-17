/**
 * 執行詳情「追溯覆蓋（諮詢）」面板的顯示規則（契約 §1.10.3、§4.7.2；整合輪 115，G-05、UI-SDD-02）。純函式、不依賴 React。
 * 🔴 諮詢視圖：「AT 通過」只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘，所以標題旁恆有「諮詢視圖」徽章與固定說明。
 * 缺值一律顯示單一的「—」；空陣列（確定沒有）顯示「無」，缺席才是「—」。
 * 口徑提醒（§1.10.3 邊界①）：有無法歸屬 AC 的 AT 時，`at.total`（含）與 `ac.total`（不含）的分母口徑不同——這裡不拿兩者互推。
 */
import type { ExecutionRtm } from "@/lib/api/types";
import { SDD_DASH } from "./sdd";

export const RTM_TITLE = "追溯覆蓋";
export const RTM_ADVISORY_BADGE = "諮詢視圖";
export const RTM_ADVISORY_NOTE = "AT 通過只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘。";
/** 批次非終態時只顯示這一行（不呼叫端點）。 */
export const RTM_NOT_TERMINAL_NOTE = "批次結束後才會有追溯覆蓋報告";
/** 404 `rtm_not_found`：中性文字，不是錯誤樣式。 */
export const RTM_NOT_FOUND_NOTE = "此批次沒有追溯覆蓋報告";
export const RTM_NOT_FOUND_HINT = "常見原因：批次沒有啟用 SDD 治理，或批次不是正常走完（失敗、取消與額度停機都不會寫報告）。";
export const RTM_WEAK_NOTE = "規格的 Then 沒有可推導的引號字面值，驗收可能偏鬆";
export const RTM_UNMAPPED_NOTE = "這些 AT 的編號不符 AT-NNN-Y-… 文法或 AC 對不上，已計入 AT 總數但不計入任何 AC";

/** `sha256:` 加 12 碼十六進位＝19 碼。 */
export const RTM_DIGEST_SHOWN = 19;

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** 百分比（Bridge 原值 0～100、1 位小數）：「100.0%」；缺值「—」。 */
function pct(v: unknown): string {
  return isNum(v) ? `${v.toFixed(1)}%` : SDD_DASH;
}

/** 「4／4（100.0%）」：兩個計數都是數字才有；缺席「—」。 */
function ratio(passed: unknown, total: unknown, percent: unknown): string {
  return isNum(passed) && isNum(total) ? `${passed}／${total}（${pct(percent)}）` : SDD_DASH;
}

/** 逗號分隔的 id 清單：空陣列「無」、缺席「—」。 */
function idList(ids: unknown): string {
  if (!Array.isArray(ids)) return SDD_DASH;
  const names = ids.filter((x): x is string => typeof x === "string" && x !== "");
  return names.length === 0 && ids.length === 0 ? "無" : names.length === 0 ? SDD_DASH : names.join(", ");
}

const nonEmpty = (ids: unknown): boolean => Array.isArray(ids) && ids.length > 0;

export type RtmView = {
  /** `advisory=true`（恆為真）時必顯「諮詢視圖」徽章 */
  advisory: boolean;
  /** 「4／4（100.0%）」 */
  at: string;
  /** `at.unmapped > 0` 時：「其中 <n> 個無法歸屬到 AC」 */
  atNote: string | null;
  ac: string;
  /** SCG-5 覆蓋（機器判斷，仍是諮詢） */
  scg5: string;
  /** 規格摘要：前 19 碼加「…」，全值放 tooltip（title）；空字串「—」 */
  specDigest: { text: string; full: string | null };
  scenario: string;
  failed: string;
  weak: string;
  weakNote: string | null;
  unmapped: string;
  unmappedNote: string | null;
};

function scg5Text(r: Partial<ExecutionRtm>): string {
  if (typeof r.fullyCovered !== "boolean") return SDD_DASH;
  if (r.fullyCovered) return "AC 已達 100% 覆蓋";
  const acFull = isNum(r.ac?.total) && isNum(r.ac?.covered) && r.ac.total > 0 && r.ac.covered >= r.ac.total;
  if (acFull && nonEmpty(r.unmappedAtIds)) return "AC 已達 100%，但有無法歸屬的 AT，不視為全覆蓋";
  return "AC 未達 100% 覆蓋";
}

export function rtmView(report: Partial<ExecutionRtm> | null | undefined): RtmView {
  const r = report ?? {};
  const digest = typeof r.specDigest === "string" ? r.specDigest : "";
  const unmappedCount = isNum(r.at?.unmapped) ? r.at.unmapped : 0;
  return {
    // 契約 §1.10.3：advisory 恆為 true（型別就是常數 true）；欄位缺席也當諮詢，絕不讓缺欄位變成「正式報告」
    advisory: true,
    at: ratio(r.at?.passed, r.at?.total, r.at?.pct),
    atNote: unmappedCount > 0 ? `其中 ${unmappedCount} 個無法歸屬到 AC` : null,
    ac: ratio(r.ac?.covered, r.ac?.total, r.ac?.pct),
    scg5: scg5Text(r),
    specDigest: digest === "" ? { text: SDD_DASH, full: null } : { text: digest.length > RTM_DIGEST_SHOWN ? `${digest.slice(0, RTM_DIGEST_SHOWN)}…` : digest, full: digest },
    scenario: typeof r.scenario === "string" && r.scenario !== "" ? r.scenario : SDD_DASH,
    failed: idList(r.failedAtIds),
    weak: idList(r.weakRegexAtIds),
    weakNote: nonEmpty(r.weakRegexAtIds) ? RTM_WEAK_NOTE : null,
    unmapped: idList(r.unmappedAtIds),
    unmappedNote: nonEmpty(r.unmappedAtIds) ? RTM_UNMAPPED_NOTE : null,
  };
}
