/**
 * execute 的 201 回應 `warnings[]` 的白話（契約 §1.10.6、附錄 B.5〈回應本文的警告碼〉；整合輪 115，API-EXE-15）。純函式、不依賴 React。
 * 只有 execute 的 201 帶 `warnings`（pause／resume／cancel／restore 與 GET 不帶）；缺席＝沒有警告。
 * `code`／`cause` 日後新增的值照樣顯示（附原值）、不崩潰也不吞掉；`detail` 是後端給人看的中文說明，原樣顯示。
 */
import { EXECUTION_WARNING_CODES } from "@/lib/api/reasons";
import type { ExecutionWarning } from "@/lib/api/types";

/** `sdd_governance_inactive` 的 `cause`（契約 §1.10.5 批次資格五條件各自不成立）→ 白話。 */
export const GOVERNANCE_INACTIVE_CAUSE_TEXT: Readonly<Record<string, string>> = {
  not_bound: "專案尚未綁定規格（還沒有用路徑 A 匯入過規格）",
  token_not_configured: "後端沒有設定 SDD 寫入權杖",
  mixed_scope: "範圍內有非 SDD 來源的任務",
  spec_mismatch: "範圍內的任務來自不同的規格（內容摘要不同）",
  duplicate_step_id: "範圍內有任務的 stepId 重複",
};

const CODE_TITLE: Readonly<Record<string, string>> = {
  [EXECUTION_WARNING_CODES.SDD_GOVERNANCE_INACTIVE]: "本批次沒有啟用 SDD 治理（沒有預檢、沒有 FSM 同步，事後也不會有追溯報告）",
  [EXECUTION_WARNING_CODES.SDD_FROZEN_DIGEST_ABSENT]: "已啟用 SDD 治理，但凍結時沒有記錄內容摘要（放行，但無法偵測凍結後改檔）",
};

export type ExecutionWarningView = {
  /** React key：序號加 code 加 cause（同一個 code 可能出現多次） */
  key: string;
  code: string;
  /** 一句話：字典有的給白話，沒有的原樣顯示 code */
  title: string;
  /** `cause` 白話（沒有 cause 為 null；字典沒有的新值原樣） */
  cause: string | null;
  /** 後端給人看的中文說明；沒有為空字串（畫面不顯示） */
  detail: string;
};

export function executionWarningViews(warnings: readonly ExecutionWarning[] | null | undefined): ExecutionWarningView[] {
  if (!Array.isArray(warnings)) return [];
  return warnings.flatMap((w, index) => {
    if (typeof w !== "object" || w === null) return [];
    const code = typeof w.code === "string" && w.code !== "" ? w.code : "—";
    const cause = typeof w.cause === "string" && w.cause !== "" ? w.cause : null;
    return [
      {
        key: `${index}-${code}-${cause ?? ""}`,
        code,
        title: CODE_TITLE[code] ?? code,
        cause: cause === null ? null : (GOVERNANCE_INACTIVE_CAUSE_TEXT[cause] ?? cause),
        detail: typeof w.detail === "string" ? w.detail.trim() : "",
      },
    ];
  });
}

/** 啟動成功 toast 的後綴：有警告時「（另有 N 則警告，見執行控制卡）」，沒有為空字串（toast 一次只顯示一則，所以併進同一句）。 */
export function warningsToastSuffix(count: number): string {
  return count > 0 ? `（另有 ${count} 則警告，見執行控制卡）` : "";
}
