/**
 * 匯入解析失敗的錯誤正規化（US-I-10；契約 §1.1.3、§3.3.5、§4.1 I-08／I-09）。
 *
 * 失敗長相有三種，畫面要用同一個清單元件完整列出、不截斷、不自動修剪：
 *   ① 422 `解析結果未通過有界閘`：errors[] 每項 {field,message,gate,detail,location?}（一次列出全部違規）；
 *   ② 400 Bean Validation：errors[] 每項 {field,message}（例如任務的 passCriteria 空白）；
 *   ③ 重新整理或從歷史重開後：GET /import/{id} 的 lastParseErrors[]（{gate,detail,location?}）。
 * 另有非閘的失敗（422 `SDD 規格檢查未通過`、409、502／504），只有標題與說明，沒有逐項清單。
 */
import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import type { GateError, GateName } from "@/lib/api/types";

/** 清單的一列：有界閘違規或欄位錯誤，原因全文都在 text（不截斷）。 */
export type ErrorRow = {
  /** 有界閘名稱（逐字常數）；一般欄位錯誤沒有 */
  gate?: string;
  /** 違規位置（例：goals[0].tasks[3].description）或欄位名 */
  location?: string;
  /** 給人看的完整原因 */
  text: string;
};

/** 閘別徽章的中文說明（鍵是契約 §3.3.5 的逐字常數）。 */
export const GATE_LABEL: Record<GateName, string> = {
  max_steps: "步驟上限（≤ 24）",
  cycle: "依賴成環（Kahn 無環）",
  empty_prompt: "prompt 不可為空",
  prompt_too_long: "prompt 過長",
  brain_unsupported: "模型不可用",
  brain_failed: "模型呼叫失敗",
};

export function gateLabel(gate: string | undefined): string | undefined {
  if (!gate) return undefined;
  return (GATE_LABEL as Record<string, string>)[gate] ?? gate;
}

/** lastParseErrors（GET /import/{id}）→ 清單列。 */
export function rowsFromGateErrors(errors: readonly GateError[] | undefined | null): ErrorRow[] {
  return (errors ?? []).map((e) => ({ gate: e.gate, location: e.location, text: e.detail }));
}

type ServerErrorItem = { field?: string; message?: string; gate?: string; detail?: string; location?: string };

/** ApiError.errors[]（FieldError 或帶 gate 的 GateFieldError）→ 清單列；原因優先取 detail（gate 的完整說明）。 */
export function rowsFromApiError(error: ApiError): ErrorRow[] {
  return (error.errors as ServerErrorItem[]).map((e) => ({
    gate: e.gate,
    location: e.location ?? e.field,
    text: e.detail ?? e.message ?? "",
  }));
}

/** 解析（或儲存編輯）失敗時，畫面需要的全部資訊。 */
export type ParseFailure = {
  /** 標題：reason 優先（逐字常數），否則 message */
  title: string;
  /** message（給人看的句子），與標題不同時另外顯示 */
  message?: string;
  rows: ErrorRow[];
  /** 其他說明行（例：SDD 規格被拒時 Bridge 的原因） */
  notes: string[];
  traceId?: string;
  /** 是否為有界閘拒絕（422 解析結果未通過有界閘） */
  gateRejected: boolean;
};

function detailString(details: Record<string, unknown> | undefined, key: string): string | undefined {
  const v = details?.[key];
  return typeof v === "string" && v.trim() ? v : undefined;
}

export function parseFailureFromError(error: unknown): ParseFailure {
  if (!(error instanceof ApiError)) {
    return {
      title: error instanceof Error ? error.message : "發生未知錯誤",
      rows: [],
      notes: [],
      gateRejected: false,
    };
  }
  const notes: string[] = [];
  if (error.reason === REASONS.IMPORT_SDD_SPEC_REJECTED) {
    const bridgeReason = detailString(error.details, "bridgeReason");
    const detail = detailString(error.details, "detail");
    if (bridgeReason) notes.push(`引擎回報：${bridgeReason}`);
    if (detail) notes.push(detail);
  }
  const title = error.reason ?? error.message;
  return {
    title,
    message: error.reason && error.message && error.message !== error.reason ? error.message : undefined,
    rows: rowsFromApiError(error),
    notes,
    traceId: error.traceId,
    gateRejected: error.reason === REASONS.IMPORT_GATE_REJECTED,
  };
}

/** 從重開的記錄還原「上一次被有界閘拒絕」的清單；沒有就回 null。 */
export function parseFailureFromRecord(lastParseErrors: readonly GateError[] | undefined | null): ParseFailure | null {
  if (!lastParseErrors || lastParseErrors.length === 0) return null;
  return {
    title: REASONS.IMPORT_GATE_REJECTED,
    message: "上一次解析未通過有界閘（重新整理或從歷史重開後還原）。",
    rows: rowsFromGateErrors(lastParseErrors),
    notes: [],
    gateRejected: true,
  };
}

// ── 違規位置 → 樹節點（標紅用）───────────────────────────────────────────

export type Highlights = {
  project: boolean;
  /** 目標索引 */
  goals: Set<number>;
  /** 任務位置 "目標索引.任務索引" */
  tasks: Set<string>;
};

/**
 * 把違規位置對回節點。位置字串形如 goals[0].tasks[2].description、goals[1].dependsOn、goals（整個清單）、
 * 400 欄位錯誤則帶前綴 parsedResult.（例：parsedResult.goals[0].tasks[1].passCriteria）。
 * 只有 `goals`（目標數量超限）或 sourceContent 這類沒有指到特定節點的位置不標紅。
 */
export function highlightsFromRows(rows: readonly ErrorRow[]): Highlights {
  const out: Highlights = { project: false, goals: new Set(), tasks: new Set() };
  for (const row of rows) {
    const loc = row.location ?? "";
    if (/(^|\.)project(\.|$)/.test(loc)) out.project = true;
    const m = /goals\[(\d+)\](?:\.tasks\[(\d+)\])?/.exec(loc);
    if (!m) continue;
    const goal = Number(m[1]);
    if (m[2] !== undefined) out.tasks.add(`${goal}.${Number(m[2])}`);
    else out.goals.add(goal);
  }
  return out;
}
