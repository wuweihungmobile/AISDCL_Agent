"use client";

/**
 * 巡邏快照的共用讀取（巡邏狀態卡、提案詳情的「下一步」、待入帳面板三處共用同一個查詢鍵，所以只發一個請求）：
 * 回傳查詢本身、快照 `report`（不是物件＝null）、Bridge 的讀取時間 `readAt`、新鮮度（含 `useMinuteTick` 的時間前進）。
 * 純讀：沒有任何寫入或額外請求。
 */
import { useSiPatrol } from "@/lib/api/queries";
import { patrolFreshness, type Freshness } from "@/lib/domain/siFlow";
import { useMinuteTick } from "./useMinuteTick";

export type PatrolView = {
  q: ReturnType<typeof useSiPatrol>;
  report: Record<string, unknown> | null;
  readAt: unknown;
  freshness: Freshness | null;
  /** 這一分鐘的瀏覽器現在（毫秒）與資料抵達瀏覽器的時刻，供相對時間換算 */
  nowMs: number;
  receivedAtMs: number;
};

export function usePatrolView(): PatrolView {
  const q = useSiPatrol();
  const nowMs = useMinuteTick();
  const data = q.data;
  const report = data && typeof data.report === "object" && data.report !== null && !Array.isArray(data.report) ? data.report : null;
  const freshness = report ? patrolFreshness(report, data?.readAt, q.dataUpdatedAt, nowMs) : null;
  return { q, report, readAt: data?.readAt, freshness, nowMs, receivedAtMs: q.dataUpdatedAt };
}
