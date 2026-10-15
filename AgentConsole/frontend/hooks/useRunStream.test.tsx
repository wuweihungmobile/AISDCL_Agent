import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { qk } from "@/lib/api/queries";
import type { ExecutionRunDetail } from "@/lib/api/types";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { makeClient, signIn, stubApi } from "@/tests/helpers/api";
import { FLUSH_MS, MAX_REVIVES, REFRESH_DEBOUNCE_MS, REVIVE_DELAY_MS, useRunStream, type UseRunStreamOptions } from "./useRunStream";

const RUN_A = "e5a7c3b9-2f1d-4b6a-8c0e-1d2f3a4b5c31";
const RUN_B = "f6b8d4ca-3a2e-4c7b-9d1f-2e3a4b5c6d42";
const TASK = "c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21";
const TS = "2026-10-15T08:30:13.482+00:00";

function detail(id: string, patch: Partial<ExecutionRunDetail> = {}): ExecutionRunDetail {
  return {
    id,
    projectId: "p1",
    runNumber: 1,
    status: "RUNNING",
    bridgeStatus: "RUNNING",
    autonomyLevel: 4,
    scope: { mode: "ALL", goalIds: [], taskIds: [] },
    totalTokensUsed: 0,
    tokenBudget: 100000,
    startedAt: TS,
    completedSteps: 0,
    totalSteps: 3,
    lastEventSeq: 1,
    pendingReviews: [],
    bridge: { connected: true, status: "RUNNING", checkedAt: TS },
    ...patch,
  } as ExecutionRunDetail;
}

let client: QueryClient;
const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
const flushMicro = () => act(async () => void (await vi.advanceTimersByTimeAsync(0)));
const advance = (ms: number) => act(async () => void (await vi.advanceTimersByTimeAsync(ms)));

function mount(id: string | null, opts: UseRunStreamOptions = {}) {
  return renderHook((props: { id: string | null; opts: UseRunStreamOptions }) => useRunStream(props.id, { EventSourceCtor: FakeEventSource, ...props.opts }), {
    wrapper,
    initialProps: { id, opts },
  });
}

beforeEach(() => {
  FakeEventSource.reset();
  signIn("OPERATOR", "operator");
  client = makeClient();
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

describe("useRunStream：連線與事件", () => {
  it("同時連 /logs 與 /metrics（各自帶 token 的網址）；兩條都連上＝「已連線」", async () => {
    stubApi(() => undefined);
    const { result } = mount(RUN_A);
    expect(result.current.connection).toBe("connecting"); // effect 一掛上就開始連（先要換到 token，連線物件稍後才建立）
    expect(FakeEventSource.instances).toHaveLength(0);
    await flushMicro();
    expect(FakeEventSource.instances).toHaveLength(2);
    expect(FakeEventSource.lastOf("logs")?.url).toContain(`/api/v1/stream/executions/${RUN_A}/logs?access_token=a`);
    expect(FakeEventSource.lastOf("metrics")?.url).toContain(`/api/v1/stream/executions/${RUN_A}/metrics?access_token=a`);
    expect(result.current.connection).toBe("connecting");

    act(() => {
      FakeEventSource.lastOf("logs")!.open();
      FakeEventSource.lastOf("metrics")!.open();
    });
    expect(result.current.connection).toBe("open");
  });

  it("enabled=false 或沒有 runId：不連線", async () => {
    stubApi(() => undefined);
    mount(RUN_A, { enabled: false });
    mount(null);
    await flushMicro();
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("/logs 的日誌行進 live.lines（批次送進、重複的行只算一次）；STEP 的 taskId＋stepStatus 更新任務即時狀態", async () => {
    stubApi(() => undefined);
    const { result } = mount(RUN_A);
    await flushMicro();
    const logs = FakeEventSource.lastOf("logs")!;
    act(() => {
      logs.open();
      logs.emit("log", { seq: 5, ts: TS, source: "STEP", level: "INFO", message: "開始：初始化（G1-T1，第 1 次）", taskId: TASK, stepStatus: "STARTED" }, "5");
      logs.emit("log", { seq: 5, ts: TS, source: "STEP", level: "INFO", message: "開始：初始化（G1-T1，第 1 次）", taskId: TASK, stepStatus: "STARTED" }, "5");
      logs.emit("log", { seq: 6, ts: TS, source: "ENGINE", level: "INFO", message: "引擎輸出" }, "6");
    });
    expect(result.current.live.lines).toHaveLength(0); // 還在佇列裡，沒到批次間隔
    await advance(FLUSH_MS + 1);
    expect(result.current.live.lines.map((l) => l.message)).toEqual(["開始：初始化（G1-T1，第 1 次）"]);
    expect(result.current.live.engine).toHaveLength(1);
    expect(result.current.live.taskStatus[TASK]).toEqual({ status: "RUNNING", seq: 5 });
  });

  it("/metrics 的 progress／token／metric 直接修補批次詳情快取（畫面只讀快取一份）", async () => {
    stubApi(() => undefined);
    client.setQueryData(qk.execution(RUN_A), detail(RUN_A));
    mount(RUN_A);
    await flushMicro();
    const metrics = FakeEventSource.lastOf("metrics")!;
    act(() => {
      metrics.open();
      metrics.emit("progress-update", { seq: 20, ts: TS, runStatus: "RUNNING", bridgeStatus: "RUNNING", completedSteps: 2, totalSteps: 3, progressPct: 66.7, currentStep: { stepId: "G2-T1", stepNumber: 3, taskName: "實作", attempt: 1 } }, "20");
      metrics.emit("token-update", { seq: 20, ts: TS, tokensUsed: 2480, delta: 1240, contextPct: 1.2, tokenBudget: 100000, budgetUsageRate: 2.5 }, "20.1");
      metrics.emit("metric-update", { seq: 20, sub: 1, ts: TS, completedTasks: 2, failedTasks: 0, totalTasks: 3, retriedTasks: 0, averageRetryCount: 0, totalTokensUsed: 2480, elapsedSec: 9 }, "20.2");
    });
    await advance(FLUSH_MS + 1);
    expect(client.getQueryData<ExecutionRunDetail>(qk.execution(RUN_A))).toMatchObject({
      completedSteps: 2,
      totalSteps: 3,
      totalTokensUsed: 2480,
      elapsedSec: 9,
      lastEventSeq: 20,
      currentStep: { stepId: "G2-T1" },
    });
  });

  it("review-request 加進待審核清單；status-change 修補狀態，並在去抖後把批次詳情、DAG、批次列表標為過期（以伺服器為準重抓）", async () => {
    stubApi(() => undefined);
    client.setQueryData(qk.execution(RUN_A), detail(RUN_A));
    client.setQueryData(qk.dag(RUN_A), { runId: RUN_A, nodes: [], edges: [], statusAsOf: TS });
    client.setQueryData(qk.executions("p1", { size: 1 }), { content: [], page: 0, size: 1, totalElements: 0, totalPages: 0 });
    mount(RUN_A);
    await flushMicro();
    const logs = FakeEventSource.lastOf("logs")!;
    act(() => {
      logs.open();
      logs.emit("status-change", { seq: 41, ts: TS, runStatus: "PAUSED", bridgeStatus: "PAUSED", reason: "在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）" }, "41");
      logs.emit("review-request", { seq: 41, sub: 1, ts: TS, review: { id: "rv1", runId: RUN_A, kind: "TASK_CONFIRM", status: "PENDING", reason: "Level 1：請確認", requestedAt: TS, allowedDecisions: ["APPROVE", "REJECT"] } }, "41.1");
    });
    await advance(FLUSH_MS + 1);
    const patched = client.getQueryData<ExecutionRunDetail>(qk.execution(RUN_A))!;
    expect(patched.status).toBe("PAUSED");
    expect(patched.pendingReviews.map((r) => r.id)).toEqual(["rv1"]);
    expect(client.getQueryState(qk.execution(RUN_A))?.isInvalidated).toBe(false); // 去抖期間還沒標過期

    await advance(REFRESH_DEBOUNCE_MS + 1);
    expect(client.getQueryState(qk.execution(RUN_A))?.isInvalidated).toBe(true);
    expect(client.getQueryState(qk.dag(RUN_A))?.isInvalidated).toBe(true);
    expect(client.getQueryState(qk.executions("p1", { size: 1 }))?.isInvalidated).toBe(true);
  });

  it("沒有快取的批次詳情時，事件只進 live（不憑空造出詳情）", async () => {
    stubApi(() => undefined);
    mount(RUN_A);
    await flushMicro();
    const metrics = FakeEventSource.lastOf("metrics")!;
    act(() => metrics.emit("progress-update", { seq: 3, ts: TS, runStatus: "RUNNING", bridgeStatus: "RUNNING", completedSteps: 1, totalSteps: 3, progressPct: 33.3 }, "3.1"));
    await advance(FLUSH_MS + 1);
    expect(client.getQueryData(qk.execution(RUN_A))).toBeUndefined();
  });
});

describe("useRunStream：換批次、離頁與重連", () => {
  it("換批次：舊的兩條連線關閉、新批次重新連；live 從空白開始，不混進舊批次的日誌", async () => {
    stubApi(() => undefined);
    const { result, rerender } = mount(RUN_A);
    await flushMicro();
    const oldLogs = FakeEventSource.lastOf("logs")!;
    act(() => oldLogs.emit("log", { seq: 5, ts: TS, source: "STEP", level: "INFO", message: "A 批次" }, "5"));
    await advance(FLUSH_MS + 1);
    expect(result.current.live.lines).toHaveLength(1);

    rerender({ id: RUN_B, opts: {} });
    await flushMicro();
    expect(oldLogs.closed).toBe(true);
    expect(FakeEventSource.lastOf("logs")!.url).toContain(`/executions/${RUN_B}/logs`);
    expect(result.current.live.runId).toBe(RUN_B);
    expect(result.current.live.lines).toHaveLength(0);
    expect(result.current.connection).toBe("connecting");
  });

  it("離頁（unmount）：兩條連線都關閉，之後舊連線的事件不再生效、也不再重連", async () => {
    stubApi(() => undefined);
    const { result, unmount } = mount(RUN_A);
    await flushMicro();
    const [a, b] = FakeEventSource.instances;
    act(() => {
      a.open();
      b.open();
    });
    unmount();
    expect(a.closed).toBe(true);
    expect(b.closed).toBe(true);
    const before = result.current.live.lines.length;
    act(() => a.emit("log", { seq: 9, ts: TS, source: "STEP", level: "INFO", message: "離頁後" }, "9"));
    a.dropClosed();
    await advance(60_000);
    expect(result.current.live.lines.length).toBe(before);
    expect(FakeEventSource.instances).toHaveLength(2);
  });

  it("終態：伺服器送完 status-change 與衍生事件後關連線 → 兩條都收工，不再重連", async () => {
    stubApi(() => undefined);
    const { result } = mount(RUN_A, { runStatus: "COMPLETED" });
    await flushMicro();
    const logs = FakeEventSource.lastOf("logs")!;
    const metrics = FakeEventSource.lastOf("metrics")!;
    act(() => {
      logs.open();
      metrics.open();
      logs.emit("status-change", { seq: 30, ts: TS, runStatus: "COMPLETED", bridgeStatus: "COMPLETED", reason: "" }, "30");
      metrics.emit("progress-update", { seq: 30, ts: TS, runStatus: "COMPLETED", bridgeStatus: "COMPLETED", completedSteps: 3, totalSteps: 3, progressPct: 100 }, "30");
      logs.dropRetrying();
      metrics.dropRetrying();
    });
    expect(result.current.connection).toBe("ended");
    await advance(60_000);
    expect(FakeEventSource.instances).toHaveLength(2);
  });

  it("串流收工但 REST 說批次還沒結束（restore 讓終態 run 重新執行）：稍後自動重新連線（網址帶放大的 tail）", async () => {
    stubApi(() => undefined);
    const { result, rerender } = mount(RUN_A, { runStatus: "COMPLETED" });
    await flushMicro();
    const logs = FakeEventSource.lastOf("logs")!;
    const metrics = FakeEventSource.lastOf("metrics")!;
    act(() => {
      logs.emit("status-change", { seq: 30, ts: TS, runStatus: "COMPLETED", bridgeStatus: "COMPLETED", reason: "" }, "30");
      metrics.emit("progress-update", { seq: 30, ts: TS, runStatus: "COMPLETED", bridgeStatus: "COMPLETED", completedSteps: 3, totalSteps: 3, progressPct: 100 }, "30");
      logs.dropRetrying();
      metrics.dropRetrying();
    });
    expect(result.current.connection).toBe("ended");

    // 呼叫 restore 之後，REST 詳情回到 RUNNING
    rerender({ id: RUN_A, opts: { runStatus: "RUNNING" } });
    await advance(REVIVE_DELAY_MS + 10);
    expect(FakeEventSource.instances).toHaveLength(4);
    expect(FakeEventSource.lastOf("logs")!.url).toContain("tail=1000");
    expect(FakeEventSource.lastOf("metrics")!.url).not.toContain("tail=");
    expect(FakeEventSource.lastOf("logs")!.url).toContain(`/executions/${RUN_A}/logs`);
  });

  it(`自動重連有上限（${MAX_REVIVES} 次）：REST 一直說還沒結束、串流卻一再收工時不會無限重連`, async () => {
    stubApi(() => undefined);
    mount(RUN_A, { runStatus: "RUNNING" });
    await flushMicro();
    for (let i = 0; i < MAX_REVIVES + 3; i++) {
      const logs = FakeEventSource.lastOf("logs")!;
      const metrics = FakeEventSource.lastOf("metrics")!;
      act(() => {
        logs.emit("status-change", { seq: 30 + i * 10, ts: TS, runStatus: "COMPLETED", bridgeStatus: "COMPLETED", reason: "" }, String(30 + i * 10));
        metrics.emit("progress-update", { seq: 30 + i * 10, ts: TS, runStatus: "COMPLETED", bridgeStatus: "COMPLETED", completedSteps: 3, totalSteps: 3, progressPct: 100 }, `${30 + i * 10}.1`);
        logs.dropRetrying();
        metrics.dropRetrying();
      });
      await advance(REVIVE_DELAY_MS + 10);
    }
    // 起始 2 條＋最多 MAX_REVIVES 次重連（每次 2 條）
    expect(FakeEventSource.instances.length).toBeLessThanOrEqual(2 + MAX_REVIVES * 2);
    expect(FakeEventSource.instances.length).toBeGreaterThan(2);
  });

  it("手動 reconnect：串流已收工時重新連線；連線還活著時什麼都不做", async () => {
    stubApi(() => undefined);
    const { result } = mount(RUN_A);
    await flushMicro();
    act(() => {
      FakeEventSource.lastOf("logs")!.open();
      FakeEventSource.lastOf("metrics")!.open();
    });
    act(() => result.current.reconnect());
    await flushMicro();
    expect(FakeEventSource.instances).toHaveLength(2); // 活著：不重連

    act(() => {
      FakeEventSource.lastOf("logs")!.emit("status-change", { seq: 30, ts: TS, runStatus: "FAILED", bridgeStatus: "FAILED", reason: "引擎升級（ESCALATION）" }, "30");
      FakeEventSource.lastOf("metrics")!.emit("progress-update", { seq: 30, ts: TS, runStatus: "FAILED", bridgeStatus: "FAILED", completedSteps: 1, totalSteps: 3, progressPct: 33.3 }, "30");
      FakeEventSource.lastOf("logs")!.dropRetrying();
      FakeEventSource.lastOf("metrics")!.dropRetrying();
    });
    expect(result.current.connection).toBe("ended");
    act(() => result.current.reconnect());
    await flushMicro();
    expect(FakeEventSource.instances).toHaveLength(4);
  });
});

describe("useRunStream：斷線回補（連續失敗兩次以上才走 REST）", () => {
  it("第一次失敗只等瀏覽器自己重連；第二次起以已處理的最大 seq 走 GET steps?afterSeq=，回補的步驟進日誌，再重建連線", async () => {
    const { calls } = stubApi((c) => {
      if (c.path === `/api/v1/executions/${RUN_A}/steps`) {
        return {
          data: {
            content: [
              { id: "s1", runId: RUN_A, taskId: TASK, taskName: "初始化", goalId: "g1", stepNumber: 8, stepId: "G1-T1", attempt: 1, action: "G1-T1: 初始化", status: "COMPLETED", tokensUsed: 1240, timestamp: TS },
            ],
            page: 0,
            size: 200,
            totalElements: 1,
            totalPages: 1,
          },
        };
      }
      return undefined;
    });
    const { result } = mount(RUN_A);
    await flushMicro();
    const logs = FakeEventSource.lastOf("logs")!;
    act(() => {
      logs.open();
      logs.emit("log", { seq: 7, ts: TS, source: "STEP", level: "INFO", message: "開始：初始化（G1-T1，第 1 次）", taskId: TASK, stepStatus: "STARTED" }, "7");
    });
    act(() => logs.dropRetrying());
    await flushMicro();
    expect(calls.filter((c) => c.path.endsWith("/steps"))).toHaveLength(0);
    expect(FakeEventSource.instances).toHaveLength(2);

    act(() => logs.dropRetrying());
    await flushMicro();
    const stepCalls = calls.filter((c) => c.path.endsWith("/steps"));
    expect(stepCalls).toHaveLength(1);
    expect(stepCalls[0].query.get("afterSeq")).toBe("7");
    expect(stepCalls[0].query.get("size")).toBe("200");

    await advance(FLUSH_MS + 1);
    expect(result.current.live.lines.map((l) => l.message)).toEqual([
      "開始：初始化（G1-T1，第 1 次）",
      "完成：初始化（G1-T1） Token: 1240",
    ]);
    expect(result.current.live.taskStatus[TASK]).toEqual({ status: "COMPLETED", seq: 8 });

    await advance(2000); // 第二次失敗的退避＝2 秒
    expect(FakeEventSource.instances).toHaveLength(3);
    expect(FakeEventSource.lastOf("logs")!.url).toContain("tail=1000");
  });

  it("連線被瀏覽器放棄（401／404／204）：先 GET 批次狀態（寫回快取）；run 已終態就收工、不重建", async () => {
    const { calls } = stubApi((c) =>
      c.path === `/api/v1/executions/${RUN_A}` ? { data: detail(RUN_A, { status: "COMPLETED", bridgeStatus: "COMPLETED" }) } : undefined,
    );
    const { result } = mount(RUN_A);
    await flushMicro();
    act(() => FakeEventSource.lastOf("logs")!.dropClosed());
    await flushMicro();
    expect(calls.some((c) => c.path === `/api/v1/executions/${RUN_A}` && c.method === "GET")).toBe(true);
    expect(client.getQueryData<ExecutionRunDetail>(qk.execution(RUN_A))?.status).toBe("COMPLETED");
    expect(result.current.logsState).toBe("ended");
    await advance(30_000);
    expect(FakeEventSource.instances).toHaveLength(2);
  });
});
