import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { ApiError } from "@/lib/api/client";

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
