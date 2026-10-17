import { focusManager, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/lib/auth/AuthProvider";
import { clearSession, resetSessionCache, saveSession } from "@/lib/auth/store";
import {
  DASHBOARD_AGG_POLL_MS,
  NOTIFICATION_POLL_FLOOR_MS,
  NOTIFICATION_POLL_MS,
  PENDING_SIGNOFF_LIMIT,
  SDD_POLL_MS,
  useNotificationSummary,
  usePendingSignoffs,
  useSddEngine,
  useWeekCompletedTasks,
} from "./queries";

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

/**
 * v1.4 的兩個新輪詢來源（契約 §0.4：同一使用者所有頁面共用每分鐘 100 次，每多一個輪詢來源就多吃額度，所以節奏要釘住）：
 * 待審批清單（儀表板「待人工審批」卡，GET /signoffs/pending）與 AISDLC_SDD 引擎（監控頁卡，GET /engines/sdd）都是每 30 秒 1 次、每次輪詢 1 個請求。
 */
function stubJsonByUrl(urls: string[], dataOf: (n: number) => unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string) => {
      urls.push(String(input));
      return new Response(JSON.stringify({ code: 200, message: "success", data: dataOf(urls.length) }), { status: 200, headers: { "content-type": "application/json" } });
    }),
  );
}

describe("usePendingSignoffs 的輪詢節奏（GET /signoffs/pending，每 30 秒 1 次）", () => {
  let urls: string[];

  beforeEach(() => {
    urls = [];
    stubJsonByUrl(urls, (n) => ({ counts: { projects: n, goals: 0, tasks: 0, imports: 0, total: n }, items: [] }));
  });

  it("與通知摘要同節奏（不低於地板 10 秒）、帶 limit=50；29 秒內不會有第二次請求，過了 30 秒才有", async () => {
    expect(PENDING_SIGNOFF_LIMIT).toBe(50); // 契約 G-10 指定
    const { result } = renderHook(() => usePendingSignoffs(), { wrapper });
    await waitFor(() => expect(result.current.data?.counts.total).toBe(1));
    expect(urls).toEqual(["/api/v1/signoffs/pending?limit=50"]);

    await vi.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS - 1_000);
    expect(urls).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(2_000);
    await waitFor(() => expect(urls).toHaveLength(2));
    expect(result.current.data?.counts.total).toBe(2);
  });

  it("頁面不可見（失焦）時停止輪詢：過了好幾個週期也不再請求", async () => {
    const { result } = renderHook(() => usePendingSignoffs(), { wrapper });
    await waitFor(() => expect(result.current.data?.counts.total).toBe(1));

    focusManager.setFocused(false);
    await vi.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS * 3);
    expect(urls).toHaveLength(1);
  });
});

describe("useSddEngine 的輪詢節奏（GET /engines/sdd，每 30 秒 1 次）", () => {
  let urls: string[];

  beforeEach(() => {
    urls = [];
    stubJsonByUrl(urls, (n) => ({ available: true, reason: null, version: { latest: `v${n}`, root: "/sdd" }, projects: [], fsm: null, checkedAt: "2026-10-16T08:00:00Z" }));
  });

  it("輪詢間隔 30 秒（常數釘住、不低於地板 10 秒）：不帶 project 的請求網址沒有 query；29 秒內不會有第二次請求，過了 30 秒才有", async () => {
    expect(SDD_POLL_MS).toBe(30_000);
    expect(SDD_POLL_MS).toBeGreaterThanOrEqual(NOTIFICATION_POLL_FLOOR_MS);
    const { result } = renderHook(() => useSddEngine(null), { wrapper });
    await waitFor(() => expect(result.current.data?.version?.latest).toBe("v1"));
    expect(urls).toEqual(["/api/v1/engines/sdd"]);

    await vi.advanceTimersByTimeAsync(SDD_POLL_MS - 1_000);
    expect(urls).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(2_000);
    await waitFor(() => expect(urls).toHaveLength(2));
    expect(result.current.data?.version?.latest).toBe("v2");
  });

  it("帶 project 時只在網址加 ?project=（FSM 專案名原樣編碼）；每次輪詢仍只有一個請求", async () => {
    const { result } = renderHook(() => useSddEngine("e2e-alpha"), { wrapper });
    await waitFor(() => expect(result.current.data?.version?.latest).toBe("v1"));
    await vi.advanceTimersByTimeAsync(SDD_POLL_MS + 1_000);
    await waitFor(() => expect(urls).toHaveLength(2));
    expect(urls).toEqual(["/api/v1/engines/sdd?project=e2e-alpha", "/api/v1/engines/sdd?project=e2e-alpha"]);
  });

  it("專案模式（v1.5，契約 §1.10.4）：projectId 單獨＝?projectId=；再帶 project＝&project=；每次輪詢仍只有一個請求；與全域模式的快取互不干擾", async () => {
    const P = "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02";
    const { result } = renderHook(() => useSddEngine(null, { projectId: P }), { wrapper });
    await waitFor(() => expect(result.current.data?.version?.latest).toBe("v1"));
    await vi.advanceTimersByTimeAsync(SDD_POLL_MS + 1_000);
    await waitFor(() => expect(urls).toHaveLength(2));
    expect(urls).toEqual([`/api/v1/engines/sdd?projectId=${P}`, `/api/v1/engines/sdd?projectId=${P}`]);

    const picked = renderHook(() => useSddEngine("other-fsm", { projectId: P }), { wrapper });
    await waitFor(() => expect(picked.result.current.data?.version?.latest).toBeDefined());
    expect(urls[urls.length - 1]).toBe(`/api/v1/engines/sdd?projectId=${P}&project=other-fsm`);

    // 全域模式的 useSddEngine(null) 是另一個快取鍵：不會拿到專案模式那份，也不會被它的輪詢帶動
    const before = urls.length;
    renderHook(() => useSddEngine(null), { wrapper });
    await waitFor(() => expect(urls.length).toBe(before + 1));
    expect(urls[urls.length - 1]).toBe("/api/v1/engines/sdd");
  });

  it("pollWhile 回 false（已選定專案、清單已有內容）就不再輪詢這一份；enabled＝false 連第一次請求都不發", async () => {
    const { result } = renderHook(() => useSddEngine(null, { pollWhile: () => false }), { wrapper });
    await waitFor(() => expect(result.current.data?.version?.latest).toBe("v1"));
    await vi.advanceTimersByTimeAsync(SDD_POLL_MS * 3);
    expect(urls).toHaveLength(1);

    renderHook(() => useSddEngine("e2e-bravo", { enabled: false }), { wrapper });
    await vi.advanceTimersByTimeAsync(SDD_POLL_MS * 2);
    expect(urls).toHaveLength(1);
  });

  it("pollMs 可放慢（監控頁的輪詢設定調得比 30 秒慢時跟著慢）；頁面不可見（失焦）時停止輪詢", async () => {
    const { result } = renderHook(() => useSddEngine(null, { pollMs: 60_000 }), { wrapper });
    await waitFor(() => expect(result.current.data?.version?.latest).toBe("v1"));
    await vi.advanceTimersByTimeAsync(59_000);
    expect(urls).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(2_000);
    await waitFor(() => expect(urls).toHaveLength(2));

    focusManager.setFocused(false);
    await vi.advanceTimersByTimeAsync(SDD_POLL_MS * 4);
    expect(urls).toHaveLength(2);
  });
});
