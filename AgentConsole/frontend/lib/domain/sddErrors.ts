/**
 * SDD 治理相關錯誤的白話對映（契約 §1.10.2、§1.10.7、§1.10.8、§3.2、附錄 B.5；整合輪 115）。純函式、不依賴 React。
 *  - reason 是前後端共用的逐字常數（lib/api/reasons.ts），程式判斷一律比對 reason，**不拿 message 判斷**；
 *  - details 的鍵固定（契約各端點小節）；缺值一律顯示「—」，不顯示 undefined、null；
 *  - 同一個 reason 在不同情境（核准凍結、編輯綁定、啟動批次、匯入）說法不同，由 scope 決定；
 *  - 400 的 `errors[]` 以欄位名分流到 fieldErrors（對話框顯示在對應欄位下），其餘進 lines。
 */
import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import { sddText } from "./sdd";

export type SddErrorScope = "freeze" | "binding" | "execute" | "import";

export type SddErrorView = {
  /** 一句話標題（白話；已把英文 reason 對映成中文，原始 reason 在 code） */
  title: string;
  /** 補充說明，每行一條 */
  lines: string[];
  /** 400 的欄位錯誤：欄位名 → 訊息（只收 `errors[]` 裡有 field 的項目；同欄位只留第一筆） */
  fieldErrors: Record<string, string>;
  /** 後端 reason（逐字；沒有時 undefined） */
  code?: string;
  traceId?: string;
};

/** Bridge 自己的錯誤 reason（`details.bridgeReason`；契約附錄 B.5〈Bridge 自己的錯誤封包 reason〉＋§1.10.2 對映表）→ 白話。 */
export const SDD_BRIDGE_REASON_LABEL: Readonly<Record<string, string>> = {
  sdd_write_disabled: "引擎橋接未設定 SDD 寫入權杖",
  sdd_write_forbidden: "引擎橋接拒絕了寫入權杖（console-api 與 Bridge 的權杖設定不一致，請管理員檢查）",
  fsm_state_conflict: "FSM 狀態不符",
  fsm_not_found: "找不到 FSM 狀態檔",
  fsm_state_unreadable: "FSM 狀態檔無法讀取",
  spec_digest_changed: "規格內容與摘要不符",
  sanitization_failed: "路徑或名稱未通過引擎橋接的檢查（不在允許的根目錄內、或已不存在）",
  sdd_invalid_argument: "引數不合規格（核准人、理由或文件路徑）",
  sdd_block_invalid: "SDD 批次區塊結構不合（console-api 缺陷，請回報 traceId）",
  spec_not_frozen: "規格尚未凍結（或不在凍結清單內）",
  spec_ambiguous: "同一目錄有多份規格，無法決定要用哪一份",
  rtm_unreadable: "追溯報告檔壞掉（YAML 損毀或缺 summary）",
  sdd_cli_usage: "引擎橋接呼叫 SDD CLI 的參數有誤（橋接端缺陷，請回報 traceId）",
  sdd_cli_failed: "SDD CLI 執行失敗或無法啟動",
  sdd_cli_timeout: "SDD CLI 執行逾時（超過 20 秒）",
};

/** 422 `引擎拒絕此請求` 的 `details.violations[].rule` → 白話（契約 §4.7.1 的例：`docs`／`missing_tcs`）。 */
export const SDD_VIOLATION_RULE_LABEL: Readonly<Record<string, string>> = {
  missing_tcs: "規格文件須含至少一份 TCS",
};

/** 引擎回報的 `bridgeReason` 白話；沒有值回 null，字典沒有的新值原樣回（不崩潰也不吞掉）。 */
export function sddBridgeReasonText(reason: unknown): string | null {
  if (typeof reason !== "string" || reason.trim() === "") return null;
  return SDD_BRIDGE_REASON_LABEL[reason] ?? reason;
}

/** 專案 id 的前 8 碼（給人認得出來就好）。 */
export const shortId = (id: unknown): string => (typeof id === "string" && id !== "" ? id.slice(0, 8) : "—");

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);

/** `violations[]`：每項 `{field, rule, detail?}` 轉成「field／rule「白話」 detail」；字串項原樣；其他略過。 */
function violationLines(violations: unknown): string[] {
  if (!Array.isArray(violations)) return [];
  const out: string[] = [];
  for (const v of violations) {
    if (typeof v === "string" && v.trim() !== "") out.push(v);
    else if (isRecord(v)) {
      const rule = typeof v.rule === "string" ? v.rule : undefined;
      const label = rule ? SDD_VIOLATION_RULE_LABEL[rule] : undefined;
      const extra = [v.detail, v.message].find((x): x is string => typeof x === "string" && x.trim() !== "");
      out.push(`${sddText(v.field)}／${sddText(rule)}${label ? `「${label}」` : ""}${extra ? ` ${extra}` : ""}`);
    }
  }
  return out;
}

/** `details.expectedState`（字串或陣列）→ 「A、B」；缺席 null。 */
function expectedStates(details: Record<string, unknown>): string | null {
  const v = details.expectedState;
  if (typeof v === "string" && v !== "") return v;
  if (Array.isArray(v)) {
    const names = v.filter((x): x is string => typeof x === "string" && x !== "");
    return names.length > 0 ? names.join("、") : null;
  }
  return null;
}

const DIGEST_PAIR_TEXT: Readonly<Record<string, string>> = {
  expected_vs_file: "規格檔在凍結前已被改動，請重新確認內容",
  frozen_vs_file: "凍結後規格檔內容已變更（與凍結時記錄的摘要不符），須在 SDD session 重新凍結",
  import_vs_file: "規格檔內容與匯入時不同，請重新匯入規格",
};

/**
 * 把 ApiError（或其他錯誤）轉成可顯示的內容。永遠回一個 view（認不得的 reason 退回「message＋reason」的一般顯示，帶 traceId）。
 * 契約各情境的逐字句子（§4.7.1）：
 *  freeze：sdd_fsm_state_conflict「FSM 目前不在 HUMAN_PENDING（目前：<currentState>）」、sdd_fsm_not_found「找不到 FSM 專案狀態檔（<sddProject>）；請先在專案根的 SDD session 建立」、
 *   sdd_binding_conflict「同一個專案根下已有另一個專案綁定了這個 FSM 專案」、sdd_spec_digest_changed「規格檔在凍結前已被改動，請重新確認內容」、
 *   sdd_write_disabled「SDD 寫入功能未啟用（需管理員設定寫入權杖）」、422 引擎拒絕此請求顯示 violations 的 field／rule；
 *  binding：400 在欄位下顯示 errors[0].message、sdd_binding_conflict「同一個專案根下已有另一個專案（<holderProjectId 前 8 碼>）綁定了這個 FSM 專案」。
 */
export function describeSddError(error: unknown, scope: SddErrorScope): SddErrorView {
  if (!(error instanceof ApiError)) {
    return { title: error instanceof Error ? error.message : "發生未知錯誤", lines: [], fieldErrors: {} };
  }
  const d = error.details ?? {};
  const lines: string[] = [];
  const fieldErrors: Record<string, string> = {};
  for (const e of error.errors) {
    if (e.field && !(e.field in fieldErrors)) fieldErrors[e.field] = e.message;
  }
  const done = (title: string): SddErrorView => ({ title, lines, fieldErrors, code: error.reason, traceId: error.traceId });
  const bridgeLine = () => {
    const text = sddBridgeReasonText(d.bridgeReason);
    if (text) lines.push(`引擎回報：${text}`);
  };

  switch (error.reason) {
    case REASONS.SDD_FSM_STATE_CONFLICT: {
      const current = sddText(d.currentState);
      if (scope !== "execute") return done(`FSM 目前不在 HUMAN_PENDING（目前：${current}）`);
      lines.push(`目前狀態：${current}`);
      const expected = expectedStates(d);
      if (expected) lines.push(`可啟動批次的狀態：${expected}`);
      if (d.cause === "foreign_delegation") lines.push("FSM 正由外來委派佔用（不是 Console 的批次），請在 SDD session 處理後再試。");
      if (typeof d.runId === "string") lines.push(`佔用中的批次：${shortId(d.runId)}（${sddText(d.runStatus)}）`);
      if (current === "ESCALATION" || current === "ESCALATION_FINAL") lines.push("請先在 SDD session 依恢復指令處理（Console 不提供恢復動作；指令見專案詳情的「SDD 治理」區或監控頁 SDD 卡）。");
      return done("FSM 狀態不允許啟動 SDD 批次");
    }
    case REASONS.SDD_FSM_NOT_FOUND:
      return done(`找不到 FSM 專案狀態檔（${sddText(d.sddProject)}）；請先在專案根的 SDD session 建立`);
    case REASONS.SDD_SPEC_DIGEST_CHANGED: {
      const pair = typeof d.pair === "string" ? d.pair : undefined;
      const title = scope === "freeze" ? DIGEST_PAIR_TEXT.expected_vs_file : ((pair && DIGEST_PAIR_TEXT[pair]) ?? "規格檔內容已變更，請重新確認");
      if (typeof d.doc === "string") lines.push(`檔案：${d.doc}`);
      return done(title);
    }
    case REASONS.SDD_WRITE_DISABLED:
      return done("SDD 寫入功能未啟用（需管理員設定寫入權杖）");
    case REASONS.SDD_BINDING_CONFLICT: {
      const cause = typeof d.cause === "string" ? d.cause : undefined;
      if (cause === "target_bound_differently") {
        if (typeof d.sddProject === "string") lines.push(`目標專案目前綁定的 FSM 專案：${d.sddProject}`);
        return done("目標專案已綁定了不同的 FSM 專案或規格根，這份規格不能併入它");
      }
      if (cause === "request_differs_from_target") {
        if (typeof d.field === "string") lines.push(`不一致的欄位：${d.field}`);
        return done("使用「匯入到既有專案」時，執行路徑與 SDD 綁定一律取自目標專案，請求帶的值與它不同");
      }
      if (typeof d.holderProjectId === "string" && scope !== "freeze") return done(`同一個專案根下已有另一個專案（${shortId(d.holderProjectId)}）綁定了這個 FSM 專案`);
      if (typeof d.holderProjectId === "string") lines.push(`已綁定的專案：${shortId(d.holderProjectId)}`);
      return done("同一個專案根下已有另一個專案綁定了這個 FSM 專案");
    }
    case REASONS.EXEC_ENGINE_REJECTED: {
      lines.push(...violationLines(d.violations));
      bridgeLine();
      if (lines.length === 0 && typeof d.detail === "string") lines.push(d.detail);
      return done(scope === "freeze" ? "引擎拒絕了這次核准凍結" : "引擎拒絕此請求");
    }
    case REASONS.IMPORT_SDD_SPEC_REJECTED: {
      bridgeLine();
      if (typeof d.detail === "string" && d.detail.trim() !== "") lines.push(d.detail);
      return done("SDD 規格檢查未通過");
    }
    case REASONS.BRIDGE_ERROR: {
      bridgeLine();
      if (typeof d.bridgeStatus === "number") lines.push(`引擎橋接回應狀態：${d.bridgeStatus}`);
      return done("引擎橋接服務錯誤");
    }
    case REASONS.BRIDGE_UNREACHABLE:
    case REASONS.BRIDGE_TIMEOUT:
      return done(error.reason);
    case REASONS.ACCESS_DENIED:
      return done("權限不足：這個動作需要 OPERATOR 以上的角色");
  }

  // 其他（含 400 的 Bean Validation、404、429…）：一般顯示——欄位錯誤分流到 fieldErrors，沒有欄位的項目與 message 進 lines
  for (const e of error.errors) if (!e.field) lines.push(e.message);
  const generic = error.reason ?? error.message;
  if (error.reason && error.message && error.message !== error.reason) lines.unshift(error.message);
  return done(error.status === 400 && Object.keys(fieldErrors).length > 0 ? "輸入內容有誤，請修正後再送出" : generic);
}

/** 啟動批次時會出現的 SDD 相關 reason（契約 §1.2.1 的 v1.5 加註）：startErrors 以它決定要不要走本檔的白話對映。 */
export const SDD_EXECUTE_REASONS: readonly string[] = [
  REASONS.SDD_FSM_STATE_CONFLICT,
  REASONS.SDD_FSM_NOT_FOUND,
  REASONS.SDD_SPEC_DIGEST_CHANGED,
  REASONS.SDD_WRITE_DISABLED,
  REASONS.IMPORT_SDD_SPEC_REJECTED,
];
