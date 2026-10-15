import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { ApiError, describeError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";

/**
 * 把後端 400 的 errors[{field,message}] 對應到表單欄位（PRD §7.2、Architecture §5.3）。
 * 回傳「沒有對得上欄位」的訊息，由表單以橫幅顯示（409 狀態衝突、無欄位的 400、網路錯誤…）；
 * 全部都對得上欄位時回 null。
 *  - mapMessage：欄位訊息的後處理（例：把依賴成環訊息裡的 UUID 換成目標名稱）。
 */
export function applyServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly string[],
  mapMessage?: (field: string, message: string, error: ApiError) => string,
): string | null {
  if (!(error instanceof ApiError)) {
    return error instanceof Error ? error.message : "儲存失敗";
  }
  const unmapped: string[] = [];
  for (const fe of error.errors) {
    const text = mapMessage ? mapMessage(fe.field, fe.message, error) : fe.message;
    if (fields.includes(fe.field)) {
      setError(fe.field as Path<T>, { type: "server", message: text });
    } else {
      unmapped.push(text);
    }
  }
  if (error.errors.length > 0 && unmapped.length === 0) return null;
  const head = unmapped.length > 0 ? unmapped.join("；") : error.message;
  const reason = error.reason && !head.includes(error.reason) ? `（${error.reason}）` : "";
  const trace = error.traceId ? `（traceId：${error.traceId}）` : "";
  return `${head}${reason}${trace}`;
}

/**
 * 復原專案失敗時給人看的原因（C-3；契約 §1.6.1）——三種前提不符各有白話說明：
 *  - 409 `project_not_deleted`：專案目前沒有被刪除（可能已被其他人復原）；
 *  - 409 `restore_window_expired`：刪除已超過保留期（`details.retentionDays` 天），無法復原；
 *  - 404：專案不存在或已被清除排程實體刪除。
 * 其餘（403 權限不足、網路錯誤…）照 describeError。
 */
export function describeRestoreError(error: unknown): string {
  if (error instanceof ApiError) {
    const trace = error.traceId ? `（traceId：${error.traceId}）` : "";
    if (error.reason === REASONS.PROJECT_NOT_DELETED) {
      return `這個專案目前沒有被刪除（可能已被其他人復原），不需要復原。${trace}`;
    }
    if (error.reason === REASONS.RESTORE_WINDOW_EXPIRED) {
      const days = error.details?.retentionDays;
      return `這個專案刪除已超過保留期${typeof days === "number" ? `（${days} 天）` : ""}，無法復原。${trace}`;
    }
    if (error.status === 404) {
      return `找不到這個專案：它可能已被永久清除，無法復原。${trace}`;
    }
  }
  return describeError(error);
}

/**
 * 刪除目標／任務失敗時給人看的原因（C-8；契約 §1.6.3、QA O-05）：專案有進行中批次（INITIALIZING／RUNNING／PAUSED，
 * 含 Bridge 的 PAUSING／CANCELLING）時後端回 409 `project_executing`——顯示白話原因與下一步，而不是只丟英文識別字；
 * 其他錯誤（含既有的 409 `RUNNING 狀態的任務不可刪除`）照 describeError。
 */
export function describeDeleteError(error: unknown): string {
  if (error instanceof ApiError && error.reason === REASONS.PROJECT_EXECUTING) {
    const trace = error.traceId ? `（traceId：${error.traceId}）` : "";
    return `專案目前有進行中的執行批次（執行中、暫停中或正在取消），無法刪除目標或任務；請等批次結束，或到執行頁取消批次後再刪除。${trace}`;
  }
  return describeError(error);
}
