"use client";

import { useEffect, useState } from "react";

/** 輸入穩定 delayMs 毫秒後才更新的值（關鍵字搜尋：每打一個字就打一次後端會吃掉限流額度）。 */
export function useDebounced<T>(value: T, delayMs = 400): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
