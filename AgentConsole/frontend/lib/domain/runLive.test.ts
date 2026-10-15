import { describe, expect, it } from "vitest";

import type { RunStreamEvent } from "@/lib/api/sse";
import type { ExecutionRunDetail, ExecutionStep } from "@/lib/api/types";
import {
  MAX_ENGINE_LINES,
  MAX_LINES,
  applyStreamEvents,
  initialLive,
  liveReducer,
  needsDetailRefresh,
  patchRunDetail,
  refreshPlan,
  stepMessage,
  stepToLogData,
  taskLiveFromStep,
  visibleLines,
} from "./runLive";

const TS = "2026-10-15T08:30:13.482+00:00";
const T1 = "c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21";
const T2 = "c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c22";

type E = RunStreamEvent;
const stepLog = (seq: number, stepStatus: "STARTED" | "COMPLETED" | "FAILED" | "RETRYING", taskId = T1, message = `步驟 ${seq}`): E => ({
  name: "log",
  id: String(seq),
  data: { seq, ts: TS, source: "STEP", level: "INFO", message, taskId, stepStatus },
});
const engineLog = (seq: number, message = `引擎 ${seq}`): E => ({ name: "log", id: String(seq), data: { seq, ts: TS, source: "ENGINE", level: "INFO", message } });
type RunStatusLiteral = "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED";
type BridgeStatusLiteral = RunStatusLiteral | "PAUSING" | "CANCELLING";
const statusChange = (seq: number, runStatus: RunStatusLiteral, bridgeStatus: BridgeStatusLiteral = runStatus, reason = ""): E => ({
  name: "status-change",
  id: String(seq),
  data: { seq, ts: TS, runStatus, bridgeStatus, reason },
});
const progress = (seq: number, patch: object = {}): E =>
  ({
    name: "progress-update",
    id: `${seq}.1`,
    data: { seq, ts: TS, runStatus: "RUNNING", bridgeStatus: "RUNNING", completedSteps: 1, totalSteps: 3, progressPct: 33.3, ...patch },
  }) as E;

function detail(patch: Partial<ExecutionRunDetail> = {}): ExecutionRunDetail {
  return {
    id: "run1",
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
    lastEventSeq: 10,
    pendingReviews: [],
    bridge: { connected: true, status: "RUNNING", checkedAt: TS },
    ...patch,
  } as ExecutionRunDetail;
}

describe("STEP 訊息樣板（契約 §2.5；REST 回補與 SSE 即時行長得一樣）", () => {
  it("四種步驟狀態的中文訊息逐字對應契約", () => {
    const base = { taskName: "初始化", stepId: "G1-T1", attempt: 1 };
    expect(stepMessage({ ...base, status: "STARTED" })).toBe("開始：初始化（G1-T1，第 1 次）");
    expect(stepMessage({ ...base, status: "RETRYING", attempt: 2 })).toBe("重試：初始化（G1-T1，第 2 次）");
    expect(stepMessage({ ...base, status: "COMPLETED", tokensUsed: 1240 })).toBe("完成：初始化（G1-T1） Token: 1240");
    expect(stepMessage({ ...base, status: "COMPLETED" })).toBe("完成：初始化（G1-T1）");
    expect(stepMessage({ ...base, status: "FAILED", attempt: 2, errorMessage: "評估未通過" })).toBe("失敗：初始化（G1-T1，第 2 次）：評估未通過");
    expect(stepMessage({ status: "STARTED" })).toContain("（未命名任務）");
  });

  it("一列 ExecutionStep 轉成與 SSE log（source=STEP）同形的資料：seq＝stepNumber、等級依狀態、帶 taskId 與 stepStatus", () => {
    const step = {
      id: "s1",
      runId: "run1",
      taskId: T1,
      taskName: "初始化",
      goalId: "g1",
      stepNumber: 17,
      stepId: "G1-T1",
      attempt: 1,
      action: "G1-T1: 初始化",
      status: "FAILED",
      errorMessage: "boom",
      timestamp: TS,
    } as ExecutionStep;
    expect(stepToLogData(step)).toMatchObject({
      seq: 17,
      source: "STEP",
      level: "ERROR",
      message: "失敗：初始化（G1-T1，第 1 次）：boom",
      taskId: T1,
      stepStatus: "FAILED",
    });
    expect(stepToLogData({ ...step, status: "RETRYING" }).level).toBe("WARN");
    expect(stepToLogData({ ...step, status: "STARTED" }).level).toBe("INFO");
    expect(taskLiveFromStep("STARTED")).toBe("RUNNING");
    expect(taskLiveFromStep("RETRYING")).toBe("RUNNING");
    expect(taskLiveFromStep("COMPLETED")).toBe("COMPLETED");
    expect(taskLiveFromStep("FAILED")).toBe("FAILED");
  });
});

describe("applyStreamEvents：即時日誌", () => {
  it("同一行（重播或與 REST 回補重疊）只出現一次；舊 seq 的行插回正確位置；輸入狀態不被修改", () => {
    const s0 = initialLive("run1");
    const s1 = applyStreamEvents(s0, [stepLog(5, "STARTED"), stepLog(7, "COMPLETED")]);
    expect(s0.lines).toHaveLength(0);
    const s2 = applyStreamEvents(s1, [stepLog(7, "COMPLETED"), stepLog(6, "RETRYING"), stepLog(5, "STARTED")]);
    expect(s2.lines.map((l) => l.seq)).toEqual([5, 6, 7]);
    expect(s1.lines.map((l) => l.seq)).toEqual([5, 7]);
  });

  it("沒有任何變化時回傳同一個物件（React 不重繪）", () => {
    const s1 = applyStreamEvents(initialLive("run1"), [stepLog(5, "STARTED")]);
    expect(applyStreamEvents(s1, [])).toBe(s1);
    expect(applyStreamEvents(s1, [stepLog(5, "STARTED")])).toBe(s1);
    // /metrics 的事件不進日誌
    expect(applyStreamEvents(s1, [{ name: "token-update", id: "8.2", data: { seq: 8, ts: TS, tokensUsed: 1, delta: 1, contextPct: 0 } }])).toBe(s1);
  });

  it("狀態變化以強調行插入（含 Bridge 過渡態的中文）；終態失敗是 ERROR、暫停是 WARN", () => {
    const s = applyStreamEvents(initialLive("r"), [
      statusChange(8, "RUNNING", "PAUSING"),
      statusChange(9, "PAUSED", "PAUSED", "在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）"),
      statusChange(10, "FAILED", "FAILED", "引擎升級（ESCALATION）"),
    ]);
    expect(s.lines.map((l) => [l.kind, l.level, l.message])).toEqual([
      ["status", "INFO", "狀態：暫停中"],
      ["status", "WARN", "狀態：已暫停（在步驟邊界暫停（已完成 1 步，續跑點：G1-T2））"],
      ["status", "ERROR", "狀態：失敗（引擎升級（ESCALATION））"],
    ]);
  });

  it("告警與審核請求也進日誌：嚴重度對映等級；暫態告警（沒有 sub）依 code 與時間去重", () => {
    const alert = (seq: number, patch: object): E =>
      ({
        name: "alert",
        id: patch["sub" as keyof typeof patch] ? `${seq}.${(patch as { sub: number }).sub}` : String(seq),
        data: { seq, ts: TS, origin: "ENGINE", severity: "CRITICAL", message: "引擎升級", ...patch },
      }) as E;
    const review: E = {
      name: "review-request",
      id: "41.1",
      data: {
        seq: 41,
        sub: 1,
        ts: TS,
        review: { id: "rv1", runId: "r", kind: "TASK_CONFIRM", status: "PENDING", reason: "Level 1：請確認是否繼續執行任務「設定」", requestedAt: TS, allowedDecisions: ["APPROVE", "REJECT"] },
      },
    };
    const transient = alert(42, { origin: "CONSOLE", code: "BRIDGE_UNREACHABLE", severity: "WARNING", message: "Bridge 暫時無法連線" });
    const s = applyStreamEvents(initialLive("r"), [alert(40, {}), review, alert(41, { origin: "CONSOLE", sub: 2, severity: "WARNING", message: "Token 使用量已達預算的 83%" }), transient, transient]);
    expect(s.lines.map((l) => [l.kind, l.level, l.message])).toEqual([
      ["alert", "ERROR", "告警（嚴重）：引擎升級"],
      ["review", "WARN", "待審核：Level 1：請確認是否繼續執行任務「設定」"],
      ["alert", "WARN", "告警（警告）：Token 使用量已達預算的 83%"],
      ["alert", "WARN", "告警（警告）：Bridge 暫時無法連線"],
    ]);
  });

  it("引擎原始輸出與重要行分開存：預設只看重要行，打開開關才依 (seq, sub) 合併顯示", () => {
    const s = applyStreamEvents(initialLive("r"), [stepLog(1, "STARTED"), engineLog(2), stepLog(3, "COMPLETED"), engineLog(4)]);
    expect(s.lines.map((l) => l.seq)).toEqual([1, 3]);
    expect(s.engine.map((l) => l.seq)).toEqual([2, 4]);
    expect(visibleLines(s, false).map((l) => l.seq)).toEqual([1, 3]);
    expect(visibleLines(s, true).map((l) => l.seq)).toEqual([1, 2, 3, 4]);
  });

  it("兩個緩衝區各有上限：超過只留最新的（舊的丟）", () => {
    const many = Array.from({ length: MAX_LINES + 25 }, (_, i) => stepLog(i + 1, "STARTED", T1, `行 ${i + 1}`));
    const engine = Array.from({ length: MAX_ENGINE_LINES + 10 }, (_, i) => engineLog(100_000 + i));
    const s = applyStreamEvents(initialLive("r"), [...many, ...engine]);
    expect(s.lines).toHaveLength(MAX_LINES);
    expect(s.lines[0].seq).toBe(26);
    expect(s.lines[MAX_LINES - 1].seq).toBe(MAX_LINES + 25);
    expect(s.engine).toHaveLength(MAX_ENGINE_LINES);
    expect(s.engine[0].seq).toBe(100_010);
  });
});

describe("applyStreamEvents：任務即時狀態（DAG 疊加用）", () => {
  it("STEP 的 taskId＋stepStatus 更新任務狀態：STARTED→進行中、COMPLETED→完成、FAILED→失敗", () => {
    let s = applyStreamEvents(initialLive("r"), [stepLog(1, "STARTED", T1)]);
    expect(s.taskStatus[T1]).toEqual({ status: "RUNNING", seq: 1 });
    s = applyStreamEvents(s, [stepLog(2, "COMPLETED", T1), stepLog(3, "STARTED", T2), stepLog(4, "FAILED", T2)]);
    expect(s.taskStatus[T1].status).toBe("COMPLETED");
    expect(s.taskStatus[T2]).toEqual({ status: "FAILED", seq: 4 });
  });

  it("較舊的事件不覆寫較新的狀態（兩條串流交錯或重播時不閃回）", () => {
    let s = applyStreamEvents(initialLive("r"), [stepLog(10, "COMPLETED", T1)]);
    s = applyStreamEvents(s, [stepLog(9, "STARTED", T1)]);
    expect(s.taskStatus[T1]).toEqual({ status: "COMPLETED", seq: 10 });
    // /metrics 的 progress-update 帶 currentStep：較舊（seq 9）不覆寫、較新（seq 11，例如重試）才覆寫
    s = applyStreamEvents(s, [progress(9, { currentStep: { stepId: "G1-T1", stepNumber: 1, taskId: T1, taskName: "初始化", attempt: 1 } })]);
    expect(s.taskStatus[T1].status).toBe("COMPLETED");
    s = applyStreamEvents(s, [progress(11, { currentStep: { stepId: "G1-T1", stepNumber: 1, taskId: T1, taskName: "初始化", attempt: 2 } })]);
    expect(s.taskStatus[T1]).toEqual({ status: "RUNNING", seq: 11 });
  });

  it("還原告警（ENGINE／RESTORE）作廢此前累積的任務狀態；重播同一則不會把還原之後累積的狀態清掉；別種告警不清", () => {
    const restore: E = { name: "alert", id: "20", data: { seq: 20, ts: TS, origin: "ENGINE", code: "RESTORE", severity: "INFO", message: "已從斷點 after-G1-T1 還原" } };
    let s = applyStreamEvents(initialLive("r"), [stepLog(2, "COMPLETED", T1), stepLog(4, "FAILED", T2)]);
    expect(Object.keys(s.taskStatus)).toHaveLength(2);
    s = applyStreamEvents(s, [restore]);
    expect(s.taskStatus).toEqual({}); // 被還原掉的步驟回到待處理（畫面改由 REST 的 DAG 當底）
    expect(s.lines.at(-1)?.message).toContain("已從斷點 after-G1-T1 還原"); // 告警行照常顯示
    s = applyStreamEvents(s, [stepLog(22, "STARTED", T2)]);
    s = applyStreamEvents(s, [restore]); // 重播同一則：不再清
    expect(s.taskStatus[T2]).toEqual({ status: "RUNNING", seq: 22 });
    const escalation: E = { name: "alert", id: "23", data: { seq: 23, ts: TS, origin: "ENGINE", code: "ESCALATION", severity: "CRITICAL", message: "x" } };
    const consoleRestore: E = { name: "alert", id: "24.1", data: { seq: 24, sub: 1, ts: TS, origin: "CONSOLE", code: "RESTORE", severity: "INFO", message: "y" } };
    expect(applyStreamEvents(s, [escalation, consoleRestore]).taskStatus[T2]).toEqual({ status: "RUNNING", seq: 22 });
  });
  it("只有 taskId 沒有 stepStatus 的 log、沒有 currentStep 的 progress-update：不產生任務狀態", () => {
    const s = applyStreamEvents(initialLive("r"), [{ name: "log", id: "3", data: { seq: 3, ts: TS, source: "STEP", level: "INFO", message: "x", taskId: T1 } }, progress(4)]);
    expect(s.taskStatus).toEqual({});
  });
});

describe("patchRunDetail：SSE 事件修補批次詳情快取（REST 當底）", () => {
  it("status-change：狀態、Bridge 狀態、原因與 bridge.status 一併更新，lastEventSeq 前進", () => {
    const next = patchRunDetail(detail(), statusChange(41, "PAUSED", "PAUSED", "在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）"));
    expect(next).toMatchObject({ status: "PAUSED", bridgeStatus: "PAUSED", lastEventSeq: 41, reason: "在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）" });
    expect(next.bridge.status).toBe("PAUSED");
  });

  it("progress-update：完成數、總數、目前步驟；currentStep 不在時清空", () => {
    const cs = { stepId: "G1-T2", stepNumber: 2, taskId: T2, taskName: "設定", attempt: 1 };
    const a = patchRunDetail(detail({ lastEventSeq: 20 }), progress(25, { completedSteps: 2, currentStep: cs }));
    expect(a).toMatchObject({ completedSteps: 2, totalSteps: 3, currentStep: cs, lastEventSeq: 25 });
    const b = patchRunDetail(a, progress(26, { completedSteps: 3 }));
    expect(b.currentStep).toBeUndefined();
    expect(b.completedSteps).toBe(3);
  });

  it("token-update：累計 Token 與預算；預算缺席時保留原值。metric-update：已耗時與總 Token", () => {
    const a = patchRunDetail(detail(), { name: "token-update", id: "36.2", data: { seq: 36, ts: TS, tokensUsed: 1240, delta: 1240, contextPct: 0.6, tokenBudget: 200000, budgetUsageRate: 0.6 } });
    expect(a).toMatchObject({ totalTokensUsed: 1240, tokenBudget: 200000 });
    const b = patchRunDetail(a, { name: "token-update", id: "37.2", data: { seq: 37, ts: TS, tokensUsed: 2480, delta: 1240, contextPct: 1.2 } });
    expect(b).toMatchObject({ totalTokensUsed: 2480, tokenBudget: 200000 });
    const c = patchRunDetail(b, {
      name: "metric-update",
      id: "37.3",
      data: { seq: 37, sub: 3, ts: TS, completedTasks: 1, failedTasks: 0, totalTasks: 3, retriedTasks: 0, averageRetryCount: 0, totalTokensUsed: 2480, elapsedSec: 7 },
    });
    expect(c).toMatchObject({ elapsedSec: 7, totalTokensUsed: 2480 });
  });

  it("版本戳：seq 小於快取已知的最後 seq 的狀態類事件一律不覆寫（回傳同一物件）；seq 相同則套用（冪等）", () => {
    const d = detail({ lastEventSeq: 50, status: "PAUSED", completedSteps: 2 });
    expect(patchRunDetail(d, statusChange(49, "RUNNING"))).toBe(d);
    expect(patchRunDetail(d, progress(40))).toBe(d);
    expect(patchRunDetail(d, { name: "token-update", id: "1.2", data: { seq: 1, ts: TS, tokensUsed: 1, delta: 1, contextPct: 0 } })).toBe(d);
    expect(patchRunDetail(d, statusChange(50, "PAUSED")).status).toBe("PAUSED");
    expect(patchRunDetail(d, progress(50, { runStatus: "PAUSED", bridgeStatus: "PAUSED", completedSteps: 2 })).completedSteps).toBe(2);
  });

  it("review-request：加進待審核清單（以 id 去重、只收 PENDING）；其他事件原樣回傳", () => {
    const review = { id: "rv1", runId: "run1", kind: "TASK_CONFIRM" as const, status: "PENDING" as const, reason: "x", requestedAt: TS, allowedDecisions: ["APPROVE" as const, "REJECT" as const] };
    const ev: E = { name: "review-request", id: "41.1", data: { seq: 41, sub: 1, ts: TS, review } };
    const a = patchRunDetail(detail(), ev);
    expect(a.pendingReviews.map((r) => r.id)).toEqual(["rv1"]);
    expect(patchRunDetail(a, ev)).toBe(a);
    const decided: E = { ...ev, data: { ...ev.data, review: { ...review, id: "rv2", status: "APPROVED" } } } as E;
    expect(patchRunDetail(a, decided)).toBe(a);
    const d = detail();
    expect(patchRunDetail(d, stepLog(5, "STARTED"))).toBe(d);
    expect(patchRunDetail(d, engineLog(6))).toBe(d);
  });

  it("liveReducer：事件屬於別的批次（切換批次的瞬間）就從空白開始，不混進舊批次的內容", () => {
    const a = liveReducer(initialLive("run-a"), { type: "events", runId: "run-a", events: [stepLog(1, "STARTED")] });
    expect(a.lines).toHaveLength(1);
    const b = liveReducer(a, { type: "events", runId: "run-b", events: [stepLog(2, "STARTED", T2)] });
    expect(b.runId).toBe("run-b");
    expect(b.lines.map((l) => l.seq)).toEqual([2]);
    expect(Object.keys(b.taskStatus)).toEqual([T2]);
  });

  it("refreshPlan：一批事件合併成一次重抓計畫（狀態變化→詳情＋DAG＋批次列表；步驟完成→DAG；審核／告警→通知摘要）", () => {
    expect(refreshPlan([stepLog(1, "STARTED"), engineLog(2), progress(3)])).toEqual({ detail: false, dag: false, notifications: false, runs: false });
    expect(refreshPlan([stepLog(1, "COMPLETED")])).toEqual({ detail: false, dag: true, notifications: false, runs: false });
    expect(refreshPlan([stepLog(1, "FAILED")]).dag).toBe(true);
    expect(refreshPlan([statusChange(5, "PAUSED")])).toEqual({ detail: true, dag: true, notifications: false, runs: true });
    const review: E = { name: "review-request", id: "5.1", data: { seq: 5, sub: 1, ts: TS, review: {} as never } };
    expect(refreshPlan([review])).toEqual({ detail: true, dag: false, notifications: true, runs: false });
    const engineAlert: E = { name: "alert", id: "6", data: { seq: 6, ts: TS, origin: "ENGINE", severity: "CRITICAL", message: "x" } };
    expect(refreshPlan([engineAlert]).notifications).toBe(true);
    // 引擎的還原告警：一批任務回到待處理，DAG 要重抓；別的引擎告警（升級）不必
    const restoreAlert: E = { name: "alert", id: "7", data: { seq: 7, ts: TS, origin: "ENGINE", code: "RESTORE", severity: "INFO", message: "已還原" } };
    expect(refreshPlan([restoreAlert])).toMatchObject({ detail: true, dag: true, notifications: true });
    expect(refreshPlan([engineAlert]).dag).toBe(false); // 多則事件合併：任何一則需要就要
    expect(refreshPlan([stepLog(1, "STARTED"), review, stepLog(2, "COMPLETED")])).toEqual({ detail: true, dag: true, notifications: true, runs: false });
  });

  it("需要向伺服器重抓的事件：狀態變化、審核請求、持久化或引擎告警；日誌行與進度快照不必", () => {
    expect(needsDetailRefresh(statusChange(1, "RUNNING"))).toBe(true);
    expect(needsDetailRefresh({ name: "review-request", id: "1.1", data: { seq: 1, sub: 1, ts: TS, review: {} as never } })).toBe(true);
    expect(needsDetailRefresh({ name: "alert", id: "5", data: { seq: 5, ts: TS, origin: "ENGINE", severity: "CRITICAL", message: "x" } })).toBe(true);
    expect(needsDetailRefresh({ name: "alert", id: "5.1", data: { seq: 5, sub: 1, ts: TS, origin: "CONSOLE", severity: "WARNING", message: "x" } })).toBe(true);
    expect(needsDetailRefresh({ name: "alert", id: "5", data: { seq: 5, ts: TS, origin: "CONSOLE", code: "BRIDGE_UNREACHABLE", severity: "WARNING", message: "x" } })).toBe(false);
    expect(needsDetailRefresh(stepLog(1, "STARTED"))).toBe(false);
    expect(needsDetailRefresh(progress(1))).toBe(false);
  });
});
