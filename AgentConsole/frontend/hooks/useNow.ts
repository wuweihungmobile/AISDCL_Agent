"use client";

import { useEffect, useState } from "react";

/**
 * 每 intervalMs 毫秒更新一次的「現在」（epoch 毫秒）：進行中的批次耗時要每秒跳動，但伺服器的 elapsedSec 只在事件與輪詢時更新。
 * enabled=false 時不排計時器（終態批次、背景分頁不需要）；元件卸載時清掉。
 */
export function useNow(enabled: boolean, intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!enabled) return;
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [enabled, intervalMs]);
  return now;
}
