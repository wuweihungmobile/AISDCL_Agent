"use client";

import { ApiError } from "@/lib/api/client";
import { useAllProjects, useNotificationSummary } from "@/lib/api/queries";
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

export type BridgeLinkInfo = {
  state: ServiceState;
  /** 最近一次探測的時間（ISO）；從未探測為 null */
  checkedAt: string | null;
};

/**
 * Engine Bridge 連線狀態＝GET /notifications/summary 的 bridgeConnected／bridgeCheckedAt（契約 §1.4.1、§4.5 G-03）：
 * console-api 每 30 秒對 Bridge 的 /health 探測一次的最近結果；`/actuator/health` 只代表 console-api 自己，所以不用它。
 * 與頂列通知鈴、signoff 徽章共用同一份通知摘要快取（每 30 秒輪詢、頁面不可見時暫停），不另外打請求。
 *  - true＝已連線（綠點）；false＝未連線（紅點）；
 *  - null／缺席＝「未知」灰點——從未探測過（console-api 剛啟動、探測環還沒跑；B1 階段兩欄恆為 null），不假裝「已連線」；
 *  - 摘要還沒回來＝檢查中；摘要查詢失敗＝未知（拿不到資料就不下判斷）。
 */
export function useBridgeInfo(): BridgeLinkInfo {
  const { status } = useAuth();
  const q = useNotificationSummary();
  if (status === "anon") return { state: "idle", checkedAt: null };
  if (q.data) {
    const connected = q.data.bridgeConnected;
    const checkedAt = q.data.bridgeCheckedAt ?? null;
    if (connected === true) return { state: "online", checkedAt };
    if (connected === false) return { state: "offline", checkedAt };
    return { state: "unknown", checkedAt };
  }
  if (q.isError) return { state: "unknown", checkedAt: null };
  return { state: "checking", checkedAt: null };
}

export function useBridgeStatus(): ServiceState {
  return useBridgeInfo().state;
}

export const SERVICE_LABEL: Record<ServiceState, string> = {
  checking: "檢查中",
  online: "已連線",
  offline: "未連線",
  unknown: "未知",
  idle: "未登入",
};
