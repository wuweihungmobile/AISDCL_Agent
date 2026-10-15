import { focusManager, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/lib/auth/AuthProvider";
import { clearSession, resetSessionCache, saveSession } from "@/lib/auth/store";
import { DASHBOARD_AGG_POLL_MS, NOTIFICATION_POLL_FLOOR_MS, NOTIFICATION_POLL_MS, useNotificationSummary, useWeekCompletedTasks } from "./queries";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

/**
 * 契約 §0.4：限流鍵是 JWT subject，同一使用者所有頁面共用每分鐘 100 次，
 * 所以通知摘要與任何輪詢間隔都不得小於 10 秒，且頁面不可見時應停止輪詢。
 */
let calls = 0;
let client: QueryClient;

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  calls = 0;
  client = new QueryClient();
  resetSessionCache();
  clearSession();
  saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role: "OPERATOR", username: "operator" });
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      calls += 1;
      return new Response(
        JSON.stringify({
          code: 200,
          message: "success",
          data: { pendingSignoffs: calls, pendingReviews: 0, unacknowledgedAlerts: 0 },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }),
  );
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  focusManager.setFocused(undefined);
  vi.useRealTimers();
});

describe("useNotificationSummary 的輪詢節奏", () => {
  it("間隔不低於契約地板 10 秒（輪詢地板常數只准往大調）", () => {
    expect(NOTIFICATION_POLL_FLOOR_MS).toBe(10_000);
    expect(NOTIFICATION_POLL_MS).toBeGreaterThanOrEqual(NOTIFICATION_POLL_FLOOR_MS);
  });

  it("每 30 秒重抓一次：29 秒內不會有第二次請求，過了 30 秒才有", async () => {
    const { result } = renderHook(() => useNotificationSummary(), { wrapper });
    await waitFor(() => expect(result.current.data?.pendingSignoffs).toBe(1));
    expect(calls).toBe(1);

    await vi.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS - 1_000);
    expect(calls).toBe(1);

    await vi.advanceTimersByTimeAsync(2_000);
    await waitFor(() => expect(calls).toBe(2));
    expect(result.current.data?.pendingSignoffs).toBe(2);
  });

  it("頁面不可見（失焦）時停止輪詢：過了好幾個週期也不再請求", async () => {
    const { result } = renderHook(() => useNotificationSummary(), { wrapper });
    await waitFor(() => expect(result.current.data?.pendingSignoffs).toBe(1));

    focusManager.setFocused(false);
    await vi.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS * 3);
    expect(calls).toBe(1);
  });
});

/**
 * C-1／DEF-AC-009：總覽頁的「本週完成」改打 GET /monitor/task-totals，每 60 秒 1 次；
 * 缺陷版本對每個專案各打一次 task-trend（單一分頁穩態每分鐘約 31 次，佔限流額度三成）。
 */
describe("useWeekCompletedTasks 的輪詢節奏（task-totals，每 60 秒 1 次）", () => {
  const WEEK = "2026-10-12T00:00:00.000Z";
  let urls: string[];

  beforeEach(() => {
    urls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string) => {
        urls.push(String(input));
        return new Response(
          JSON.stringify({
            code: 200,
            message: "success",
            data: { from: WEEK, to: WEEK, started: 5, completed: urls.length, failed: 0, retried: 0, projectsCounted: 3 },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }),
    );
  });

  it("輪詢間隔 60 秒（常數釘住），每次輪詢只有一個請求：59 秒內不會有第二次，過了 60 秒才有", async () => {
    expect(DASHBOARD_AGG_POLL_MS).toBe(60_000);
    const { result } = renderHook(() => useWeekCompletedTasks(WEEK), { wrapper });
    await waitFor(() => expect(result.current.data?.completed).toBe(1));
    expect(urls).toEqual([`/api/v1/monitor/task-totals?from=${encodeURIComponent(WEEK)}`]); // 只有 from；to 省略＝現在

    await vi.advanceTimersByTimeAsync(DASHBOARD_AGG_POLL_MS - 1_000);
    expect(urls).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(2_000);
    await waitFor(() => expect(urls).toHaveLength(2));
    expect(result.current.data?.completed).toBe(2);
    expect(urls.every((u) => u.startsWith("/api/v1/monitor/task-totals?"))).toBe(true); // 沒有任何 task-trend 扇出
  });

  it("頁面不可見（失焦）時停止輪詢：過了好幾個週期也不再請求", async () => {
    const { result } = renderHook(() => useWeekCompletedTasks(WEEK), { wrapper });
    await waitFor(() => expect(result.current.data?.completed).toBe(1));

    focusManager.setFocused(false);
    await vi.advanceTimersByTimeAsync(DASHBOARD_AGG_POLL_MS * 3);
    expect(urls).toHaveLength(1);
  });
});
