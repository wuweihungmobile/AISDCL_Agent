/**
 * 系統參數操作失敗時給人看的原因（契約 §1.5、附錄 B「設定」區）。
 * 規則：reason（逐字常數）在前、欄位訊息在後；SSRF／allowlist 檢查失敗附上違規類別與 host；
 * 一律附 traceId（對照後端日誌）。
 */
import { ApiError, describeError } from "@/lib/api/client";
import { REASONS, URL_VIOLATION_LABEL } from "@/lib/api/reasons";

export function describeSettingsError(error: unknown): string {
  if (!(error instanceof ApiError)) return describeError(error);
  const trace = error.traceId ? `（traceId：${error.traceId}）` : "";

  if (error.status === 403) {
    return `${error.reason ?? error.message}：僅 ADMIN 可修改系統參數${trace}`;
  }

  if (error.reason === REASONS.SETTINGS_URL_REJECTED) {
    const violation = typeof error.details?.violation === "string" ? error.details.violation : undefined;
    const host = typeof error.details?.host === "string" ? error.details.host : undefined;
    const parts = [violation ? (URL_VIOLATION_LABEL[violation] ?? violation) : undefined, host ? `host：${host}` : undefined].filter(Boolean);
    return `${error.reason}${parts.length > 0 ? `（${parts.join("；")}）` : ""}${trace}`;
  }

  const fieldMessage = error.errors[0]?.message;
  const pieces = [error.reason ?? error.message];
  if (fieldMessage && !pieces[0].includes(fieldMessage)) pieces.push(fieldMessage);
  return `${pieces.join("：")}${trace}`;
}
