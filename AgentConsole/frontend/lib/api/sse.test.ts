import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import {
  BACKFILL_AFTER_FAILURES,
  RunChannel,
  STREAM_EVENT_NAMES,
  buildStreamUrl,
  combineStreamStates,
  compareEventIds,
  defaultBackoffMs,
  isTerminalEvent,
  isTransientAlert,
  parseEventId,
  shouldReviveStream,
  type ChannelDeps,
  type RunStreamEvent,
  type StreamKind,
  type StreamState,
} from "./sse";

const RUN = "e5a7c3b9-2f1d-4b6a-8c0e-1d2f3a4b5c31";
const TS = "2026-10-15T08:30:13.482+00:00";

const log = (seq: number, message = `行 ${seq}`) => ({ seq, ts: TS, source: "STEP", level: "INFO", message });
const statusChange = (seq: number, runStatus: string) => ({ seq, ts: TS, runStatus, bridgeStatus: runStatus, reason: "" });
const progress = (seq: number, runStatus = "RUNNING") => ({
  seq,
  ts: TS,
  runStatus,
  bridgeStatus: runStatus,
  completedSteps: 1,
  totalSteps: 3,
  progressPct: 33.3,
});

type Harness = {
  channel: RunChannel;
  events: RunStreamEvent[];
  states: StreamState[];
  deps: { getToken: ReturnType<typeof vi.fn>; fetchRunStatus: ReturnType<typeof vi.fn>; backfill: ReturnType<typeof vi.fn> };
  es: () => FakeEventSource;
};

function harness(
  kind: StreamKind = "logs",
  overrides: Partial<ChannelDeps> = {},
  options: { maxFailures?: number; terminalGraceMs?: number } = {},
): Harness {
  const events: RunStreamEvent[] = [];
  const states: StreamState[] = [];
  const deps = {
    getToken: vi.fn(async (opts?: { force?: boolean }) => (opts?.force ? "tok-new" : "tok-1")),
    fetchRunStatus: vi.fn(async () => "RUNNING" as const),
    backfill: vi.fn(async () => {}),
  };
  const channel = new RunChannel(
    { runId: RUN, kind, base: "http://api.test", backoffMs: () => 1000, ...options },
    { EventSourceCtor: FakeEventSource, ...deps, ...overrides },
    { onEvent: (e) => events.push(e), onState: (s) => states.push(s) },
  );
  return { channel, events, states, deps, es: () => FakeEventSource.instances[FakeEventSource.instances.length - 1] };
}

/** 讓 connect() 內的 await getToken 結算（不動計時器）。 */
const settle = () => vi.advanceTimersByTimeAsync(0);

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

describe("事件 id（契約 §2.2）", () => {
  it("parseEventId：`41`→[41,0]、`41.2`→[41,2]；不合格式（含空字串、負數、多段）回 null", () => {
    expect(parseEventId("41")).toEqual([41, 0]);
    expect(parseEventId("41.2")).toEqual([41, 2]);
    expect(parseEventId("0")).toEqual([0, 0]);
    for (const bad of ["", "abc", "41.", ".1", "-1", "1.2.3", "4 1", null, undefined]) expect(parseEventId(bad as string), String(bad)).toBeNull();
  });

  it("compareEventIds 字典序：41 < 41.1 < 41.2 < 42；`10` 大於 `9`（不是字串比較）", () => {
    const order = ["41", "41.1", "41.2", "42"].map((s) => parseEventId(s)!);
    for (let i = 0; i < order.length - 1; i++) {
      expect(compareEventIds(order[i], order[i + 1])).toBeLessThan(0);
      expect(compareEventIds(order[i + 1], order[i])).toBeGreaterThan(0);
    }
    expect(compareEventIds(parseEventId("41.1")!, parseEventId("41.1")!)).toBe(0);
    expect(compareEventIds(parseEventId("10")!, parseEventId("9")!)).toBeGreaterThan(0);
  });

  it("buildStreamUrl：token 放網址並編碼；tail 只在 /logs 出現（/metrics 沒有這個參數）", () => {
    expect(buildStreamUrl({ base: "http://api.test", runId: RUN, kind: "logs", token: "a b+c" })).toBe(
      `http://api.test/api/v1/stream/executions/${RUN}/logs?access_token=a+b%2Bc`,
    );
    expect(buildStreamUrl({ base: "", runId: RUN, kind: "logs", token: "t", tail: 1000 })).toBe(
      `/api/v1/stream/executions/${RUN}/logs?access_token=t&tail=1000`,
    );
    expect(buildStreamUrl({ base: "", runId: RUN, kind: "metrics", token: "t", tail: 1000 })).toBe(
      `/api/v1/stream/executions/${RUN}/metrics?access_token=t`,
    );
  });

  it("終態事件：status-change／progress-update 帶終態 runStatus 才算；暫態告警＝origin=CONSOLE 且沒有 sub", () => {
    const ev = (name: string, data: object) => ({ name, id: null, data }) as unknown as RunStreamEvent;
    expect(isTerminalEvent(ev("status-change", statusChange(1, "COMPLETED")))).toBe(true);
    expect(isTerminalEvent(ev("status-change", statusChange(1, "PAUSED")))).toBe(false);
    expect(isTerminalEvent(ev("progress-update", progress(1, "CANCELLED")))).toBe(true);
    expect(isTerminalEvent(ev("log", log(1)))).toBe(false);
    expect(isTransientAlert(ev("alert", { seq: 4, origin: "CONSOLE", code: "BRIDGE_UNREACHABLE" }))).toBe(true);
    expect(isTransientAlert(ev("alert", { seq: 4, sub: 1, origin: "CONSOLE", rule: "TOKEN_BUDGET_WARNING" }))).toBe(false);
    expect(isTransientAlert(ev("alert", { seq: 4, origin: "ENGINE", code: "ESCALATION" }))).toBe(false);
  });
});

describe("RunChannel：連線與事件分派", () => {
  it("start：先換到 token 再建立 EventSource（網址帶 ?access_token=）；兩條串流各自只監聽自己的具名事件", async () => {
    const logs = harness("logs");
    logs.channel.start();
    expect(logs.channel.currentState).toBe("connecting");
    await settle();
    expect(logs.es().url).toBe(`http://api.test/api/v1/stream/executions/${RUN}/logs?access_token=tok-1`);
    expect(logs.es().names).toEqual([...STREAM_EVENT_NAMES.logs].sort());

    const metrics = harness("metrics");
    metrics.channel.start();
    await settle();
    expect(metrics.es().url).toContain("/metrics?access_token=tok-1");
    expect(metrics.es().names).toEqual(["metric-update", "progress-update", "token-update"]);
  });

  it("start 只生效一次；open → open 狀態；事件依具名分派，連同 id 與解析後的 data", async () => {
    const h = harness();
    h.channel.start();
    h.channel.start();
    await settle();
    expect(FakeEventSource.instances).toHaveLength(1);
    h.es().open();
    expect(h.channel.currentState).toBe("open");

    h.es().emit("log", log(17, "開始：初始化"), "17");
    h.es().emit("status-change", statusChange(41, "PAUSED"), "41");
    h.es().emit("review-request", { seq: 41, sub: 1, ts: TS, review: { id: "rv1" } }, "41.1");
    expect(h.events.map((e) => [e.name, e.id])).toEqual([
      ["log", "17"],
      ["status-change", "41"],
      ["review-request", "41.1"],
    ]);
    expect(h.events[0].data).toMatchObject({ seq: 17, message: "開始：初始化" });
    expect(h.channel.lastEventId).toBe("41.1");
  });

  it("沒收到 open 但收到事件（代理吃掉 open）：一樣算已連線", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().emit("log", log(1), "1");
    expect(h.channel.currentState).toBe("open");
  });

  it("損毀的 data 行略過，不影響後續事件", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().emit("log", "{not json", "5");
    h.es().emit("log", log(6), "6");
    expect(h.events.map((e) => e.id)).toEqual(["6"]);
  });
});

describe("RunChannel：去重（at-least-once，契約 §2.3 第 4 點）", () => {
  it("id 小於等於已處理的最大值一律忽略：重複、倒退都不會重複分派", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    for (const id of ["41", "42", "42", "41", "43"]) h.es().emit("log", log(Number(id)), id);
    expect(h.events.map((e) => e.id)).toEqual(["41", "42", "43"]);
  });

  it("子序號：41 → 41.1 → 41.2 → 42 依序接受；41.1 重播與 41 倒退都被忽略", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().emit("log", log(41), "41");
    h.es().emit("review-request", { seq: 41, sub: 1, ts: TS, review: { id: "a" } }, "41.1");
    h.es().emit("review-request", { seq: 41, sub: 1, ts: TS, review: { id: "a" } }, "41.1");
    h.es().emit("alert", { seq: 41, sub: 2, ts: TS, origin: "CONSOLE", rule: "TOKEN_BUDGET_WARNING", severity: "WARNING", message: "x" }, "41.2");
    h.es().emit("log", log(41), "41");
    h.es().emit("log", log(42), "42");
    expect(h.events.map((e) => e.id)).toEqual(["41", "41.1", "41.2", "42"]);
  });

  it("暫態告警不帶 id 行（瀏覽器沿用前一則的 lastEventId）：不能被當成重複而誤丟；之後的真事件照常去重", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().emit("log", log(42), "42");
    // 不帶 id：FakeEventSource 與瀏覽器一樣，lastEventId 仍是 "42"
    h.es().emit("alert", { seq: 42, ts: TS, origin: "CONSOLE", code: "BRIDGE_UNREACHABLE", severity: "WARNING", message: "Bridge 暫時無法連線" });
    h.es().emit("log", log(42), "42");
    h.es().emit("log", log(43), "43");
    expect(h.events.map((e) => `${e.name}:${e.id}`)).toEqual(["log:42", "alert:42", "log:43"]);
  });

  it("/logs 與 /metrics 是兩條獨立串流：各自記各自的最大 id，互不影響", async () => {
    const logs = harness("logs");
    const metrics = harness("metrics");
    logs.channel.start();
    metrics.channel.start();
    await settle();
    FakeEventSource.instances[0].emit("log", log(50), "50");
    FakeEventSource.instances[1].emit("progress-update", progress(10), "10.1");
    expect(logs.channel.lastEventId).toBe("50");
    expect(metrics.channel.lastEventId).toBe("10.1");
    // metrics 收斂快照 <S>.1／.2／.3 的 id 互異且嚴格遞增：三則都要收到（不被去重丟掉第二、三則）
    FakeEventSource.instances[1].emit("progress-update", progress(36), "36.1");
    FakeEventSource.instances[1].emit("token-update", { seq: 36, ts: TS, tokensUsed: 1240, delta: 1240, contextPct: 0.6 }, "36.2");
    FakeEventSource.instances[1].emit("metric-update", { seq: 36, sub: 3, ts: TS, completedTasks: 0, failedTasks: 0, totalTasks: 3, retriedTasks: 0, averageRetryCount: 0, totalTokensUsed: 1240, elapsedSec: 2 }, "36.3");
    expect(metrics.events.map((e) => e.id)).toEqual(["10.1", "36.1", "36.2", "36.3"]);
  });
});

describe("RunChannel：斷線回補順序（主控裁決補充；契約 §2.3 第 6 點、§2.8 第 4 點）", () => {
  it("第一次失敗：不建新連線、不走 REST——讓 EventSource 以 Last-Event-ID 自己重連", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().open();
    h.es().emit("log", log(7), "7");

    h.es().dropRetrying();
    await vi.advanceTimersByTimeAsync(5000);
    expect(h.channel.currentState).toBe("reconnecting");
    expect(FakeEventSource.instances).toHaveLength(1);
    expect(h.es().closed).toBe(false);
    expect(h.deps.backfill).not.toHaveBeenCalled();
    expect(h.deps.fetchRunStatus).not.toHaveBeenCalled();
  });

  it("連續第二次失敗：先關掉舊連線、以已處理的最大 seq（整數部分）走 REST 回補，退避後才重建（tail 放大、token 取新）", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().open();
    h.es().emit("review-request", { seq: 41, sub: 1, ts: TS, review: { id: "a" } }, "41.1");

    h.es().dropRetrying();
    h.es().dropRetrying(); // 同一個連線上的第二次失敗（瀏覽器重連仍失敗）
    expect(BACKFILL_AFTER_FAILURES).toBe(2);
    const first = FakeEventSource.instances[0];
    expect(first.closed).toBe(true);
    await settle();
    expect(h.deps.backfill).toHaveBeenCalledTimes(1);
    expect(h.deps.backfill).toHaveBeenCalledWith(41);
    // 回補完才進入退避；退避期間還沒有新連線
    expect(FakeEventSource.instances).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(1000);
    expect(FakeEventSource.instances).toHaveLength(2);
    expect(FakeEventSource.instances[1].url).toBe(`http://api.test/api/v1/stream/executions/${RUN}/logs?access_token=tok-1&tail=1000`);
    // 回補→重建：順序以呼叫序證明（先 backfill、後建立第二個連線）
    expect(h.deps.backfill.mock.invocationCallOrder[0]).toBeLessThan(h.deps.getToken.mock.invocationCallOrder[1]);
  });

  it("重建後仍沿用已處理的最大 id：新連線重播的舊事件被去重，只收新的", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().emit("log", log(40), "40");
    h.es().emit("log", log(41), "41");
    h.es().dropRetrying();
    h.es().dropRetrying();
    await vi.advanceTimersByTimeAsync(1000);
    const rebuilt = FakeEventSource.instances[1];
    rebuilt.open();
    for (const id of ["39", "40", "41", "42"]) rebuilt.emit("log", log(Number(id)), id);
    expect(h.events.map((e) => e.id)).toEqual(["40", "41", "42"]);
    expect(h.channel.currentState).toBe("open");
  });

  it("連上（open）就把失敗次數歸零：失敗→恢復→再失敗，不會誤觸 REST 回補", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().dropRetrying();
    h.es().open(); // 瀏覽器自己重連成功
    h.es().dropRetrying();
    await vi.advanceTimersByTimeAsync(5000);
    expect(h.deps.backfill).not.toHaveBeenCalled();
    expect(FakeEventSource.instances).toHaveLength(1);
  });

  it("回補本身失敗也不擋重連（回補是補強，不是前提）", async () => {
    const h = harness("logs", { backfill: vi.fn(async () => Promise.reject(new Error("steps 503"))) });
    h.channel.start();
    await settle();
    h.es().dropRetrying();
    h.es().dropRetrying();
    await vi.advanceTimersByTimeAsync(1000);
    expect(FakeEventSource.instances).toHaveLength(2);
  });

  it("重試用盡（連續失敗超過上限）：進入 failed、不再建立連線；reconnect() 可手動再試", async () => {
    const h = harness("logs", {}, { maxFailures: 2 });
    h.channel.start();
    await settle();
    h.es().dropRetrying();
    h.es().dropRetrying(); // failures=2：回補＋重建
    await vi.advanceTimersByTimeAsync(1000);
    expect(FakeEventSource.instances).toHaveLength(2);
    h.es().dropRetrying(); // failures=3 > 2
    await vi.advanceTimersByTimeAsync(60_000);
    expect(h.channel.currentState).toBe("failed");
    expect(FakeEventSource.instances).toHaveLength(2);

    h.channel.reconnect();
    await settle();
    expect(FakeEventSource.instances).toHaveLength(3);
  });
});

describe("RunChannel：401 換 token 重建（EventSource 看不到狀態碼，只看得到被放棄）", () => {
  it("連線被瀏覽器放棄（CLOSED）：先問 REST（順便換新 token）；run 還在跑 → 強制換新 token 重建，網址帶新 token", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    expect(FakeEventSource.instances[0].url).toContain("access_token=tok-1");

    h.es().dropClosed();
    await settle();
    expect(h.deps.fetchRunStatus).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1000);
    expect(h.deps.getToken).toHaveBeenLastCalledWith({ force: true });
    expect(FakeEventSource.instances).toHaveLength(2);
    expect(FakeEventSource.instances[1].url).toContain("access_token=tok-new");
    FakeEventSource.instances[1].open();
    expect(h.channel.currentState).toBe("open");
  });

  it("CLOSED 且 run 已終態（例如重連已終態的 run 收到 204）：收工，不重建", async () => {
    const h = harness("logs", { fetchRunStatus: vi.fn(async () => "COMPLETED" as const) });
    h.channel.start();
    await settle();
    h.es().dropClosed();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(h.channel.currentState).toBe("ended");
    expect(FakeEventSource.instances).toHaveLength(1);
  });

  it("REST 也問不到狀態（回 null 或丟錯）：保守地重建，而不是誤判成終態", async () => {
    const h = harness("logs", { fetchRunStatus: vi.fn(async () => Promise.reject(new Error("network"))) });
    h.channel.start();
    await settle();
    h.es().dropClosed();
    await vi.advanceTimersByTimeAsync(1000);
    expect(FakeEventSource.instances).toHaveLength(2);
  });

  it("連續第二次被放棄也會 REST 回補（失敗計數跨「瀏覽器放棄」累計）", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().dropClosed();
    await vi.advanceTimersByTimeAsync(1000);
    expect(h.deps.backfill).not.toHaveBeenCalled();
    FakeEventSource.instances[1].dropClosed();
    await vi.advanceTimersByTimeAsync(1000);
    expect(h.deps.backfill).toHaveBeenCalledTimes(1);
    expect(FakeEventSource.instances).toHaveLength(3);
  });

  it("換不到 token（登入已失效）：failed，不建立連線", async () => {
    const h = harness("logs", { getToken: vi.fn(async () => null) });
    h.channel.start();
    await settle();
    expect(h.channel.currentState).toBe("failed");
    expect(FakeEventSource.instances).toHaveLength(0);
  });
});

describe("RunChannel：終態、暫停與關閉（契約 §2.4）", () => {
  it("終態 status-change 之後伺服器還會送衍生事件（ESCALATED 的審核項）：不能一看到終態就關；伺服器關連線時才收工、不再重連", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().open();
    h.es().emit("status-change", statusChange(30, "FAILED"), "30");
    expect(h.channel.currentState).toBe("open");
    h.es().emit("review-request", { seq: 30, sub: 1, ts: TS, review: { id: "rv" } }, "30.1");
    expect(h.events.map((e) => e.name)).toEqual(["status-change", "review-request"]);

    h.es().dropRetrying(); // 伺服器關閉連線（瀏覽器視為「要重連」）
    expect(h.channel.currentState).toBe("ended");
    expect(h.es().closed).toBe(true);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(FakeEventSource.instances).toHaveLength(1);
    expect(h.deps.backfill).not.toHaveBeenCalled();
  });

  it("/metrics：progress-update 帶終態 runStatus 一樣算終態", async () => {
    const h = harness("metrics");
    h.channel.start();
    await settle();
    h.es().emit("progress-update", progress(9, "COMPLETED"), "9");
    h.es().emit("metric-update", { seq: 9, sub: 1, ts: TS, completedTasks: 3, failedTasks: 0, totalTasks: 3, retriedTasks: 0, averageRetryCount: 0, totalTokensUsed: 3720, elapsedSec: 5 }, "9.1");
    h.es().dropRetrying();
    expect(h.channel.currentState).toBe("ended");
    expect(h.events.map((e) => e.name)).toEqual(["progress-update", "metric-update"]);
  });

  it("終態後伺服器沒關連線：閒置超過寬限（預設 4 秒）自己收工；期間每來一則事件就重新計時", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().emit("status-change", statusChange(30, "COMPLETED"), "30");
    await vi.advanceTimersByTimeAsync(3000);
    h.es().emit("log", log(31), "31");
    await vi.advanceTimersByTimeAsync(3000);
    expect(h.channel.currentState).toBe("open"); // 距離最後一則才 3 秒
    await vi.advanceTimersByTimeAsync(1500);
    expect(h.channel.currentState).toBe("ended");
    expect(h.es().closed).toBe(true);
  });

  it("PAUSED 不結束串流：收到 status-change PAUSED 後連線照常維持", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().emit("status-change", statusChange(41, "PAUSED"), "41");
    await vi.advanceTimersByTimeAsync(60_000);
    expect(h.channel.currentState).toBe("open");
    expect(h.es().closed).toBe(false);
  });

  it("close（離頁）：關閉連線、狀態回 idle；之後舊連線的事件、錯誤與已排程的重建都不再生效", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().open();
    const first = h.es();
    first.dropRetrying();
    first.dropRetrying(); // 已排程重建（退避中）
    await settle();
    h.channel.close();
    expect(h.channel.currentState).toBe("idle");
    expect(first.closed).toBe(true);

    const seen = h.events.length;
    first.emit("log", log(99), "99");
    first.dropClosed();
    await vi.advanceTimersByTimeAsync(60_000);
    expect(h.events).toHaveLength(seen);
    expect(FakeEventSource.instances).toHaveLength(1);
    expect(h.channel.currentState).toBe("idle");
  });

  it("連線建立到一半就 close：等待中的 token 取得結果被丟棄，不會冒出連線", async () => {
    let release: (token: string) => void = () => {};
    const h = harness("logs", { getToken: vi.fn(() => new Promise<string | null>((resolve) => (release = resolve))) });
    h.channel.start();
    h.channel.close();
    release("late-token");
    await settle();
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("reconnect：終態收工後（restore 讓 run 重新執行）重新連線；沿用最大 id 去重，舊終態事件重播不會再把它收工；連線還活著時不做事", async () => {
    const h = harness();
    h.channel.start();
    await settle();
    h.es().emit("status-change", statusChange(30, "COMPLETED"), "30");
    h.es().dropRetrying();
    expect(h.channel.currentState).toBe("ended");

    h.channel.reconnect();
    await settle();
    expect(FakeEventSource.instances).toHaveLength(2);
    expect(FakeEventSource.instances[1].url).toContain("tail=1000");
    const second = FakeEventSource.instances[1];
    second.open();
    second.emit("status-change", statusChange(30, "COMPLETED"), "30"); // 重播的舊終態：被去重
    second.emit("status-change", statusChange(33, "RUNNING"), "33");
    await vi.advanceTimersByTimeAsync(30_000);
    expect(h.channel.currentState).toBe("open");
    expect(h.events.map((e) => e.id)).toEqual(["30", "33"]);

    h.channel.reconnect(); // 連線活著：no-op
    await settle();
    expect(FakeEventSource.instances).toHaveLength(2);
  });
});

describe("退避", () => {
  it("defaultBackoffMs：1→2→4→8→15 秒封頂", () => {
    expect([1, 2, 3, 4, 5, 9].map(defaultBackoffMs)).toEqual([1000, 2000, 4000, 8000, 15_000, 15_000]);
  });
});

describe("兩條串流合成一個狀態點，與「收工後是否該重連」", () => {
  it("combineStreamStates：任一失敗＝失敗；兩條都收工＝收工；重連／連線中優先於已連線；一條收工另一條還開著＝已連線", () => {
    expect(combineStreamStates("open", "open")).toBe("open");
    expect(combineStreamStates("open", "failed")).toBe("failed");
    expect(combineStreamStates("ended", "ended")).toBe("ended");
    expect(combineStreamStates("open", "ended")).toBe("open");
    expect(combineStreamStates("open", "reconnecting")).toBe("reconnecting");
    expect(combineStreamStates("connecting", "open")).toBe("connecting");
    expect(combineStreamStates("reconnecting", "connecting")).toBe("reconnecting");
    expect(combineStreamStates("idle", "idle")).toBe("idle");
  });

  it("shouldReviveStream：只有「有一條已收工、而 REST 說批次還沒結束」才重連；REST 未知或已終態都不重連", () => {
    expect(shouldReviveStream(["ended", "ended"], "RUNNING")).toBe(true);
    expect(shouldReviveStream(["open", "ended"], "PAUSED")).toBe(true);
    expect(shouldReviveStream(["ended", "ended"], "COMPLETED")).toBe(false);
    expect(shouldReviveStream(["ended", "ended"], "FAILED")).toBe(false);
    expect(shouldReviveStream(["ended", "ended"], undefined)).toBe(false);
    expect(shouldReviveStream(["ended", "ended"], null)).toBe(false);
    expect(shouldReviveStream(["open", "open"], "RUNNING")).toBe(false);
    expect(shouldReviveStream(["reconnecting", "failed"], "RUNNING")).toBe(false);
  });
});
