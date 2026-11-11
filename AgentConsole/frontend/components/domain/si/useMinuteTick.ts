"use client";

/**
 * 每分鐘本地重繪一次（TCS-SiFlowVisibility W-F5、W-F12）：回傳「現在」的毫秒時間戳，**只重繪、不發任何網路請求**。
 * 用途：巡邏快照放著不動時，相對時間（「上次心跳：N 分鐘前」）與過時警示要隨時間前進，不能停在讀取當時的數字——畫面不能說謊。
 * 這不是輪詢：資料仍只在「重新整理」或重試時重抓（沿 SI_QUERY_OPTIONS）。
 */
import { useEffect, useState } from "react";

export const MINUTE_TICK_MS = 60_000;

export function useMinuteTick(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), MINUTE_TICK_MS);
    return () => clearInterval(id);
  }, []);
  return now;
}
