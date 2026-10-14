"use client";

import { ApiError } from "@/lib/api/client";
import { useAllProjects } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";

export type ServiceState = "checking" | "online" | "offline" | "unknown" | "idle";

/**
 * console-api 連線狀態：沿用 useAllProjects（每 30 秒輪詢）的結果，不另開探測端點——
 * 成功＝online；網路層失敗（ApiError.status===0）或 5xx＝offline；尚未有結果＝checking；未登入＝idle。
 */
export function useConsoleApiStatus(): ServiceState {
  const { status } = useAuth();
  const q = useAllProjects();
  if (status === "anon") return "idle";
  if (q.isSuccess) return "online";
  if (q.isError) {
    const e = q.error;
    return e instanceof ApiError && (e.status === 0 || e.status >= 500) ? "offline" : "online";
  }
  return q.isFetching || q.isPending ? "checking" : "unknown";
}

/**
 * Engine Bridge 連線狀態。
 * 目前沒有任何對瀏覽器開放的 Bridge 狀態來源：後端 /actuator/health 為 show-details: never，
 * 監控 API（Phase 5）才會提供「console-api 對 Bridge /health 的定期探測」。
 * 在那之前誠實回報 unknown（顯示「待接線」），不假裝「已連線」。接線時只需改這個 hook。
 */
export function useBridgeStatus(): ServiceState {
  return "unknown";
}

export const SERVICE_LABEL: Record<ServiceState, string> = {
  checking: "檢查中",
  online: "已連線",
  offline: "未連線",
  unknown: "待接線",
  idle: "未登入",
};
