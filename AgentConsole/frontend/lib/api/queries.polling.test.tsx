import { focusManager, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/lib/auth/AuthProvider";
import { clearSession, resetSessionCache, saveSession } from "@/lib/auth/store";
import { NOTIFICATION_POLL_FLOOR_MS, NOTIFICATION_POLL_MS, useNotificationSummary } from "./queries";

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
