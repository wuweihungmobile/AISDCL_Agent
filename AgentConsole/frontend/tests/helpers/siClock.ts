/**
 * 可控的「每分鐘重繪」時鐘（TCS-SiFlowVisibility AT-966-11-1～11-3 的時間前進案例）：
 * 測試檔以 `vi.mock("@/components/domain/si/useMinuteTick", async () => (await import("@/tests/helpers/siClock")).clockMock())` 換掉真實的 setInterval 版本，
 * 再用 `advanceMinutes` 前進——只重繪、不發網路請求，與正式的 `useMinuteTick` 行為相同，但不依賴假計時器（假計時器會讓 testing-library 的 waitFor 停擺）。
 * 不被 vitest 收集（tests/ 目錄）。
 */
import { act } from "@testing-library/react";
import { useSyncExternalStore } from "react";

export const clock = { now: Date.now(), subs: new Set<() => void>() };

export function clockMock() {
  return {
    MINUTE_TICK_MS: 60_000,
    useMinuteTick: () =>
      useSyncExternalStore(
        (cb) => {
          clock.subs.add(cb);
          return () => {
            clock.subs.delete(cb);
          };
        },
        () => clock.now,
        () => clock.now,
      ),
  };
}

/** 測試開頭呼叫：把時鐘對齊真實現在（之後資料抵達時刻 ≥ 它，與正式行為同向）。 */
export function resetClock(): void {
  clock.now = Date.now();
}

/** 前進 N 分鐘並通知所有訂閱者重繪（包在 act 內）。 */
export function advanceMinutes(minutes: number): void {
  act(() => {
    clock.now += minutes * 60_000;
    for (const notify of [...clock.subs]) notify();
  });
}
