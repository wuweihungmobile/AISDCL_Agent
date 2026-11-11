/**
 * 真實的每分鐘重繪 hook（TCS-SiFlowVisibility W-F5、AT-966-11-1～11-3 的時間前進；SCG-4 審查 Q-01）：
 * 其他測試一律以 `tests/helpers/siClock.ts` 的替身取代它（假計時器會讓 waitFor 停擺），所以這支**不經替身**直接驗真實的計時機制——
 * 掛載後每 60 秒值前進 60 秒、未滿 60 秒不變、unmount 後計時器被清掉。這是「假計時器例外」：本檔是唯一對 `useMinuteTick` 用假計時器的地方。
 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MINUTE_TICK_MS, useMinuteTick } from "./useMinuteTick";

afterEach(() => {
  vi.useRealTimers();
});

describe("useMinuteTick 真實計時機制", () => {
  it("週期常數為 60 秒", () => {
    expect(MINUTE_TICK_MS).toBe(60_000);
  });

  it("掛載後每 60 秒值前進、未滿 60 秒不變", () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] });
    vi.setSystemTime(1_000_000_000_000);
    const { result } = renderHook(() => useMinuteTick());
    const start = result.current;
    expect(start).toBe(1_000_000_000_000);
    act(() => void vi.advanceTimersByTime(59_999));
    expect(result.current, "未滿 60 秒不變").toBe(start);
    act(() => void vi.advanceTimersByTime(1));
    expect(result.current, "滿 60 秒前進 60 秒").toBe(start + 60_000);
    act(() => void vi.advanceTimersByTime(60_000));
    expect(result.current, "再滿 60 秒再前進").toBe(start + 120_000);
  });

  it("unmount 後計時器被清除，不再觸發更新", () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] });
    const { unmount } = renderHook(() => useMinuteTick());
    expect(vi.getTimerCount()).toBe(1);
    unmount();
    expect(vi.getTimerCount(), "unmount 後不得殘留計時器").toBe(0);
    expect(() => act(() => void vi.advanceTimersByTime(10 * 60_000))).not.toThrow();
  });
});
