import http from "node:http";
import type { AddressInfo } from "node:net";

import type { MockHandler, MockReply } from "./mockApi";

/**
 * 執行頁 route mock 用的「假引擎」：在記憶體裡模擬契約 §1.2／§2／§3.5～§3.6 的行為子集，
 * 讓 Playwright 驅動 UI 時看到與真後端同形的 REST 回應與 SSE 事件流（id 規則、Last-Event-ID 重放、收斂快照、終態 204、401 都照契約）。
 *
 * REST 走 page.route 的 mock；SSE 則是測試行程裡一台真的 node:http 伺服器（listen 在隨機埠）——page.route 的 fulfill 做不到
 * 「連線一直開著、事件陸續送達」，而前端的連線狀態點、斷線重連、401 換 token 都依賴一條真的持續連線。mock 對串流路徑只做 route.continue 改網址轉過來。
 *
 * 時間由測試掌控（沒有計時器自己前進）：測試呼叫 startNext()／finishCurrent()／failCurrent() 推進一步，事件立刻推給已連線的訂閱者。
 * 夾具＝契約 §5.0.3 的 PRJ-A：G1「基礎」(T1 初始化、T2 設定)、G2「核心」(T3 實作)，每個成功的步驟 1,240 Token。
 */
export const PROJECT_ID = "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02";
export const GOAL_IDS = ["a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e11", "a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e12"] as const;

type TaskDef = { id: string; name: string; goalIdx: 0 | 1; stepId: string };
export const TASKS: readonly TaskDef[] = [
  { id: "c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21", name: "初始化", goalIdx: 0, stepId: "G1-T1" },
  { id: "c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c22", name: "設定", goalIdx: 0, stepId: "G1-T2" },
  { id: "c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c23", name: "實作", goalIdx: 1, stepId: "G2-T1" },
];
const GOAL_NAMES = ["基礎", "核心"] as const;
export const TOKENS_PER_STEP = 1240;

type Ev = { id: string; name: string; data: Record<string, unknown> };
type Review = {
  id: string;
  runId: string;
  kind: "TASK_CONFIRM" | "GOAL_CONFIRM" | "GOAL_COMPLETED" | "ESCALATED";
  status: "PENDING" | "APPROVED" | "REJECTED" | "RETRIED" | "SKIPPED";
  taskId?: string;
  goalId?: string;
  taskName?: string;
  goalName?: string;
  reason: string;
  requestedAt: string;
  allowedDecisions: string[];
  decidedBy?: string;
  comment?: string;
};
type StepRow = {
  id: string;
  runId: string;
  taskId: string;
  taskName: string;
  goalId: string;
  stepNumber: number;
  stepId: string;
  attempt: number;
  action: string;
  status: string;
  tokensUsed?: number;
  errorMessage?: string;
  timestamp: string;
};
type Checkpoint = { id: string; runId: string; name: string; createdAt: string; isAutomatic: boolean; stepIdx: number; stepId: string; completedSteps: number };

export type RunStatus = "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "CANCELLED";

/** 引擎能力狀態（契約 §1.2.1、§3.4.2；v1.3，D-11）。 */
export type CapabilityState = "ENABLED" | "OFF" | "UNAVAILABLE_NO_API_KEY";
export type Capabilities = { autoMutation: CapabilityState; selfEvolution: CapabilityState };

/**
 * 契約 §3.4.2 決策表（兩個旗標都是預設的假）：自動突變只由等級 ≥ 6 要求、需要金鑰；
 * 自演化沒有開關——有金鑰恆 ENABLED（只提案），沒有金鑰時等級 ≥ 7 要求者報 UNAVAILABLE_NO_API_KEY，否則 OFF。
 */
export function capabilitiesFor(level: number, apiKey: boolean): Capabilities {
  return {
    autoMutation: level >= 6 ? (apiKey ? "ENABLED" : "UNAVAILABLE_NO_API_KEY") : "OFF",
    selfEvolution: apiKey ? "ENABLED" : level >= 7 ? "UNAVAILABLE_NO_API_KEY" : "OFF",
  };
}

/** 引擎行程樹的資源取樣（契約 §3.1.2）：sampledAt 由假引擎在每次回詳情時補上現在時間（真後端保證取樣不超過 15 秒）。 */
export type ResourceSample = { cpuPercent: number; memoryBytes: number; processCount: number };

export type Run = {
  id: string;
  runNumber: number;
  level: number;
  /** 建立批次當下凍結的引擎能力（契約 §1.2.1）；legacyRuns 時缺席（模擬 V10 之前的批次） */
  engineCapabilities?: Capabilities;
  budget: number | null;
  status: RunStatus;
  bridgeStatus: string;
  startedAt: string;
  completedAt?: string;
  tokens: number;
  /** 已完成的步驟數（也是下一個要跑的步驟位置，0 起算） */
  cursor: number;
  /** 正在跑的步驟位置；沒有為 null */
  current: number | null;
  /** 這個批次的任務（playbook 順序）：任務位置 → TASKS 的索引 */
  scope: number[];
  seq: number;
  logs: Ev[];
  metrics: Ev[];
  reviews: Review[];
  steps: StepRow[];
  checkpoints: Checkpoint[];
  reason?: string;
  pauseRequested: boolean;
  taskStatus: Record<string, string>;
  reviewSub: number;
};

const iso = () => new Date().toISOString();
let uid = 0;
const nextUuid = (prefix: string) => {
  uid += 1;
  return `${prefix}-0000-4000-8000-${String(uid).padStart(12, "0")}`;
};

/** `41`→[41,0]、`41.2`→[41,2]（契約 §2.2）。 */
const parseId = (id: string | undefined | null): [number, number] | null => {
  const m = id ? /^(\d+)(?:\.(\d+))?$/.exec(id) : null;
  return m ? [Number(m[1]), m[2] ? Number(m[2]) : 0] : null;
};
const greater = (a: [number, number], b: [number, number]) => (a[0] !== b[0] ? a[0] > b[0] : a[1] > b[1]);

const TERMINAL: readonly RunStatus[] = ["COMPLETED", "FAILED", "CANCELLED"];

/** SSE 框架（冒號後不加空白，與 Spring SseEmitter 的實際輸出一致；契約 §2.1）。 */
const frameOf = (e: Ev) => `id:${e.id}\nevent:${e.name}\ndata:${JSON.stringify(e.data)}\n\n`;

/** 終態事件：/logs 的終態 status-change、/metrics 的終態 progress-update（之後伺服器關閉連線）。 */
const isTerminalEvent = (kind: "logs" | "metrics", e: Ev): boolean => (kind === "logs" ? e.name === "status-change" : e.name === "progress-update") && TERMINAL.includes(e.data.runStatus as RunStatus);

export type EngineOptions = {
  signedOff?: boolean;
  /** Console 的 model.apiKey 有沒有設（決定批次的 engineCapabilities；預設 true＝開發機常態）。 */
  apiKey?: boolean;
  /** 模擬 V10 之前建立的批次：回應不帶 engineCapabilities（契約 §1.2.1：缺席時前端不顯示晶片）。 */
  legacyRuns?: boolean;
};

/** 一次串流連線的紀錄（含被拒絕的）：測試用它斷言 Last-Event-ID、token 與結果。 */
export type SseAttempt = { kind: "logs" | "metrics"; runId: string; lastEventId: string | null; token: string | null; status: number };

type Conn = { res: http.ServerResponse; run: Run; kind: "logs" | "metrics" };

/** signInAs() 寫進 session 的 access token（mockApi.ts）。 */
export const FIRST_TOKEN = "mock-access-token";

/** 假引擎＋假 console-api。`engine.handler` 交給 installApiMock；測試用其餘方法推進批次。 */
export class Engine {
  readonly runs: Run[] = []; // 最新在前
  project = { signedOff: true, status: "READY" };
  readonly sseConnections: SseAttempt[] = [];
  /** 串流伺服器目前接受的 access token（/auth/refresh 換發新的、舊的在過期前仍有效；expireTokens() 全部作廢） */
  private readonly validTokens = new Set<string>([FIRST_TOKEN]);
  private tokenGen = 1;
  private server: http.Server | null = null;
  private base = "";
  private readonly conns = new Set<Conn>();
  private refuse = 0;
  /** 後端整個不可用（nginx 在上游掛掉時立即回 502）：REST、換新與串流一律 502 */
  private outage = false;
  /**
   * 引擎行程樹的資源取樣（契約 §3.1.2、§1.2.3）：undefined＝舊版 Bridge，`bridge.resources` 鍵缺席；null＝沒有資料；物件＝有取樣。
   * 只有 RUNNING 的批次回得出數字（暫停中與終態沒有存活的引擎行程樹，真後端回 null）。
   */
  resources: ResourceSample | null | undefined = undefined;
  private readonly apiKey: boolean;
  private readonly legacyRuns: boolean;

  constructor(opts: EngineOptions = {}) {
    this.project.signedOff = opts.signedOff ?? true;
    this.apiKey = opts.apiKey ?? true;
    this.legacyRuns = opts.legacyRuns ?? false;
  }

  get latest(): Run {
    return this.runs[0];
  }

  // ── 事件工具 ─────────────────────────────────────────────────────────────
  private bridgeSeq(run: Run): number {
    run.seq += 1;
    return run.seq;
  }

  private log(run: Run, name: string, data: Record<string, unknown>, id: string): void {
    const ev = { id, name, data };
    run.logs.push(ev);
    this.emit(run, "logs", ev);
  }

  private metric(run: Run, name: string, data: Record<string, unknown>, id: string): void {
    const ev = { id, name, data };
    run.metrics.push(ev);
    this.emit(run, "metrics", ev);
  }

  private progressData(run: Run, seq: number): Record<string, unknown> {
    const total = run.scope.length;
    const cur = run.current !== null ? TASKS[run.scope[run.current]] : undefined;
    return {
      seq,
      ts: iso(),
      runStatus: run.status,
      bridgeStatus: run.bridgeStatus,
      completedSteps: run.cursor,
      totalSteps: total,
      progressPct: total ? Math.round((run.cursor / total) * 1000) / 10 : 0,
      ...(cur
        ? { currentStep: { stepId: this.stepIdOf(run, run.current as number), stepNumber: (run.current as number) + 1, taskId: cur.id, taskName: cur.name, goalId: GOAL_IDS[cur.goalIdx], attempt: 1 } }
        : {}),
    };
  }

  /** 每個批次的 step_id 獨立編號（契約 §3.4.4）：這裡沿用夾具的 G<目標>-T<序>，後續批次只有一個目標時重編為 G1。 */
  private stepIdOf(run: Run, pos: number): string {
    const task = TASKS[run.scope[pos]];
    if (run.runNumber === 1 || run.scope.every((i) => TASKS[i].goalIdx === TASKS[run.scope[0]].goalIdx) === false) return task.stepId;
    return `G1-T${pos + 1}`;
  }

  private statusEvent(run: Run, reason = ""): number {
    const seq = this.bridgeSeq(run);
    this.log(run, "status-change", { seq, ts: iso(), runStatus: run.status, bridgeStatus: run.bridgeStatus, reason }, String(seq));
    this.metric(run, "progress-update", this.progressData(run, seq), String(seq));
    if (TERMINAL.includes(run.status)) this.metric(run, "metric-update", this.metricData(run, seq, 1), `${seq}.1`);
    return seq;
  }

  private metricData(run: Run, seq: number, sub: number): Record<string, unknown> {
    return {
      seq,
      sub,
      ts: iso(),
      completedTasks: run.cursor,
      failedTasks: run.steps.filter((s) => s.status === "FAILED").length,
      totalTasks: run.scope.length,
      retriedTasks: 0,
      averageRetryCount: 0,
      totalTokensUsed: run.tokens,
      tokenBudgetUsageRate: run.budget ? Math.round((run.tokens / run.budget) * 1000) / 10 : null,
      elapsedSec: Math.max(1, Math.round((Date.now() - Date.parse(run.startedAt)) / 1000)),
    };
  }

  private addReview(run: Run, kind: Review["kind"], taskIdx: number, reason: string, allowed: string[]): Review {
    const anchor = run.seq;
    run.reviewSub += 1;
    const task = TASKS[taskIdx];
    const review: Review = {
      id: nextUuid("f0b1c2d3"),
      runId: run.id,
      kind,
      status: "PENDING",
      taskId: task.id,
      goalId: GOAL_IDS[task.goalIdx],
      taskName: task.name,
      goalName: GOAL_NAMES[task.goalIdx],
      reason,
      requestedAt: iso(),
      allowedDecisions: allowed,
    };
    run.reviews.push(review);
    this.log(run, "review-request", { seq: anchor, sub: run.reviewSub, ts: iso(), review }, `${anchor}.${run.reviewSub}`);
    return review;
  }

  private createRun(level: number, budget: number | null, scope: number[]): Run {
    const run: Run = {
      id: nextUuid("e5a7c3b9"),
      runNumber: this.runs.length + 1,
      level,
      ...(this.legacyRuns ? {} : { engineCapabilities: capabilitiesFor(level, this.apiKey) }),
      budget,
      status: "RUNNING",
      bridgeStatus: "RUNNING",
      startedAt: iso(),
      tokens: 0,
      cursor: 0,
      current: null,
      scope,
      seq: 0,
      logs: [],
      metrics: [],
      reviews: [],
      steps: [],
      checkpoints: [],
      pauseRequested: false,
      taskStatus: Object.fromEntries(TASKS.map((t) => [t.id, "PENDING"])),
      reviewSub: 0,
    };
    for (const i of scope) run.taskStatus[TASKS[i].id] = "QUEUED";
    this.runs.unshift(run);
    this.project.status = "EXECUTING";
    this.statusEvent(run);
    return run;
  }

  /** 測試用：不經 UI 直接開一個批次（等同 POST execute 成功），用來預先佈置「頁面載入時批次已在進行」的情境。 */
  begin(level = 4, opts: { budget?: number | null; scope?: number[] } = {}): Run {
    return this.createRun(level, opts.budget === undefined ? 100000 : opts.budget, opts.scope ?? TASKS.map((_, i) => i));
  }

  // ── 測試驅動：推進一步 ────────────────────────────────────────────────────
  /** 開始下一個步驟（STARTED＋目前步驟的進度）。 */
  startNext(run: Run = this.latest): void {
    if (run.status !== "RUNNING" || run.current !== null || run.cursor >= run.scope.length) throw new Error("startNext：批次不在可開始下一步的狀態");
    const pos = run.cursor;
    const task = TASKS[run.scope[pos]];
    const seq = this.bridgeSeq(run);
    run.current = pos;
    run.taskStatus[task.id] = "RUNNING";
    const stepId = this.stepIdOf(run, pos);
    this.log(
      run,
      "log",
      {
        seq,
        ts: iso(),
        source: "STEP",
        level: "INFO",
        message: `開始：${task.name}（${stepId}，第 1 次）`,
        stepId,
        stepNumber: pos + 1,
        taskId: task.id,
        taskName: task.name,
        goalId: GOAL_IDS[task.goalIdx],
        attempt: 1,
        stepStatus: "STARTED",
      },
      String(seq),
    );
    run.steps.push({
      id: nextUuid("5b1d5b1d"),
      runId: run.id,
      taskId: task.id,
      taskName: task.name,
      goalId: GOAL_IDS[task.goalIdx],
      stepNumber: seq,
      stepId,
      attempt: 1,
      action: `${stepId}: ${task.name}`,
      status: "STARTED",
      timestamp: iso(),
    });
    this.metric(run, "progress-update", this.progressData(run, seq), String(seq));
    const engineSeq = this.bridgeSeq(run);
    this.log(run, "log", { seq: engineSeq, ts: iso(), source: "ENGINE", level: "INFO", message: `claude 執行 ${stepId}…` }, String(engineSeq));
  }

  /** 目前步驟成功：token → COMPLETED → 檢查點；之後依自治等級與暫停要求決定繼續、暫停（建審核項）或整批完成。 */
  finishCurrent(run: Run = this.latest): void {
    if (run.status !== "RUNNING" || run.current === null) throw new Error("finishCurrent：沒有進行中的步驟");
    const pos = run.current;
    const task = TASKS[run.scope[pos]];
    const stepId = this.stepIdOf(run, pos);

    const tokenSeq = this.bridgeSeq(run);
    run.tokens += TOKENS_PER_STEP;
    this.metric(
      run,
      "token-update",
      {
        seq: tokenSeq,
        ts: iso(),
        tokensUsed: run.tokens,
        delta: TOKENS_PER_STEP,
        contextPct: 0.6,
        tokenBudget: run.budget,
        budgetUsageRate: run.budget ? Math.round((run.tokens / run.budget) * 1000) / 10 : null,
        taskId: task.id,
      },
      String(tokenSeq),
    );
    this.metric(run, "metric-update", this.metricData(run, tokenSeq, 1), `${tokenSeq}.1`);

    const seq = this.bridgeSeq(run);
    run.cursor = pos + 1;
    run.current = null;
    run.taskStatus[task.id] = "COMPLETED";
    this.log(
      run,
      "log",
      {
        seq,
        ts: iso(),
        source: "STEP",
        level: "INFO",
        message: `完成：${task.name}（${stepId}） Token: ${TOKENS_PER_STEP}`,
        stepId,
        stepNumber: pos + 1,
        taskId: task.id,
        taskName: task.name,
        goalId: GOAL_IDS[task.goalIdx],
        attempt: 1,
        stepStatus: "COMPLETED",
        tokensUsed: TOKENS_PER_STEP,
      },
      String(seq),
    );
    run.steps.push({
      id: nextUuid("5b1d5b1d"),
      runId: run.id,
      taskId: task.id,
      taskName: task.name,
      goalId: GOAL_IDS[task.goalIdx],
      stepNumber: seq,
      stepId,
      attempt: 1,
      action: `${stepId}: ${task.name}`,
      status: "COMPLETED",
      tokensUsed: TOKENS_PER_STEP,
      timestamp: iso(),
    });
    const nextStepId = run.cursor < run.scope.length ? this.stepIdOf(run, run.cursor) : "";
    run.checkpoints.push({
      id: nextUuid("9d4e9d4e"),
      runId: run.id,
      name: `after-${stepId}`,
      createdAt: iso(),
      isAutomatic: true,
      stepIdx: run.cursor,
      stepId: nextStepId,
      completedSteps: run.cursor,
    });
    this.metric(run, "progress-update", this.progressData(run, seq), String(seq));
    this.metric(run, "metric-update", this.metricData(run, seq, 1), `${seq}.1`);

    if (run.cursor >= run.scope.length) {
      run.status = "COMPLETED";
      run.bridgeStatus = "COMPLETED";
      run.completedAt = iso();
      this.project.status = "COMPLETED";
      this.closeGateReviews(run, "執行已結束");
      this.statusEvent(run);
      return;
    }

    const nextIdx = run.scope[run.cursor];
    const lastOfGoal = TASKS[run.scope[pos]].goalIdx !== TASKS[nextIdx].goalIdx;
    if (run.pauseRequested) {
      run.pauseRequested = false;
      run.status = "PAUSED";
      run.bridgeStatus = "PAUSED";
      this.project.status = "READY";
      this.statusEvent(run, `在步驟邊界暫停（已完成 ${run.cursor} 步，續跑點：${nextStepId}）`);
      return;
    }
    const gate =
      run.level === 1
        ? ({ kind: "TASK_CONFIRM", reason: `Level 1：請確認是否繼續執行任務「${TASKS[nextIdx].name}」`, allowed: ["APPROVE", "REJECT"], taskIdx: nextIdx } as const)
        : run.level === 2 && lastOfGoal
          ? ({ kind: "GOAL_CONFIRM", reason: `Level 2：請確認是否開始目標「${GOAL_NAMES[TASKS[nextIdx].goalIdx]}」`, allowed: ["APPROVE", "REJECT"], taskIdx: nextIdx } as const)
          : run.level === 3 && lastOfGoal
            ? ({ kind: "GOAL_COMPLETED", reason: `目標「${GOAL_NAMES[task.goalIdx]}」已完成，等待人類審核`, allowed: ["APPROVE", "REJECT", "RETRY"], taskIdx: run.scope[pos] } as const)
            : null;
    if (!gate) return;
    run.status = "PAUSED";
    run.bridgeStatus = "PAUSED";
    this.project.status = "READY";
    this.statusEvent(run, `在步驟邊界暫停（已完成 ${run.cursor} 步，續跑點：${nextStepId}）`);
    this.addReview(run, gate.kind, gate.taskIdx, gate.reason, [...gate.allowed]);
  }

  /** 目前步驟失敗（重試用盡）：RETRYING → FAILED → ESCALATION 告警 → run FAILED → ESCALATED 審核項（契約 §5 E2E-05）。 */
  failCurrent(run: Run = this.latest, errorMessage = "評估未通過"): void {
    if (run.status !== "RUNNING" || run.current === null) throw new Error("failCurrent：沒有進行中的步驟");
    const pos = run.current;
    const task = TASKS[run.scope[pos]];
    const stepId = this.stepIdOf(run, pos);
    const retrySeq = this.bridgeSeq(run);
    this.log(
      run,
      "log",
      {
        seq: retrySeq,
        ts: iso(),
        source: "STEP",
        level: "WARN",
        message: `重試：${task.name}（${stepId}，第 2 次）`,
        stepId,
        stepNumber: pos + 1,
        taskId: task.id,
        taskName: task.name,
        goalId: GOAL_IDS[task.goalIdx],
        attempt: 2,
        stepStatus: "RETRYING",
      },
      String(retrySeq),
    );
    run.steps.push({
      id: nextUuid("5b1d5b1d"),
      runId: run.id,
      taskId: task.id,
      taskName: task.name,
      goalId: GOAL_IDS[task.goalIdx],
      stepNumber: retrySeq,
      stepId,
      attempt: 2,
      action: `${stepId}: ${task.name}`,
      status: "RETRYING",
      timestamp: iso(),
    });
    const failSeq = this.bridgeSeq(run);
    run.taskStatus[task.id] = "ESCALATED";
    this.log(
      run,
      "log",
      {
        seq: failSeq,
        ts: iso(),
        source: "STEP",
        level: "ERROR",
        message: `失敗：${task.name}（${stepId}，第 2 次）：${errorMessage}`,
        stepId,
        stepNumber: pos + 1,
        taskId: task.id,
        taskName: task.name,
        goalId: GOAL_IDS[task.goalIdx],
        attempt: 2,
        stepStatus: "FAILED",
      },
      String(failSeq),
    );
    run.steps.push({
      id: nextUuid("5b1d5b1d"),
      runId: run.id,
      taskId: task.id,
      taskName: task.name,
      goalId: GOAL_IDS[task.goalIdx],
      stepNumber: failSeq,
      stepId,
      attempt: 2,
      action: `${stepId}: ${task.name}`,
      status: "FAILED",
      errorMessage,
      timestamp: iso(),
    });
    const alertSeq = this.bridgeSeq(run);
    this.log(run, "alert", { seq: alertSeq, ts: iso(), origin: "ENGINE", code: "ESCALATION", severity: "CRITICAL", message: `引擎升級（ESCALATION）：${errorMessage}`, stepId }, String(alertSeq));
    run.status = "FAILED";
    run.bridgeStatus = "FAILED";
    run.completedAt = iso();
    run.current = null;
    this.project.status = "FAILED";
    run.reason = `引擎升級（ESCALATION）：${errorMessage}`;
    this.statusEvent(run, run.reason);
    this.addReview(run, "ESCALATED", run.scope[pos], `任務「${task.name}」重試 1 次仍失敗，需要人類介入：${run.reason}`, ["RETRY", "SKIP", "REJECT"]);
  }

  // ── 控制動作（REST）──────────────────────────────────────────────────────
  private closeGateReviews(run: Run, comment: string): void {
    for (const r of run.reviews) {
      if (r.status === "PENDING" && r.kind !== "ESCALATED") {
        r.status = "REJECTED";
        r.decidedBy = "system";
        r.comment = comment;
      }
    }
  }

  private resumeRun(run: Run, decidedBy: string, comment: string): void {
    run.status = "RUNNING";
    run.bridgeStatus = "RUNNING";
    this.project.status = "EXECUTING";
    for (const r of run.reviews) {
      if (r.status === "PENDING" && r.kind !== "ESCALATED") {
        r.status = "APPROVED";
        r.decidedBy = decidedBy;
        r.comment = comment;
      }
    }
    this.statusEvent(run);
  }

  private cancelRun(run: Run): void {
    if (run.status === "RUNNING") {
      run.bridgeStatus = "CANCELLING";
      const s = this.bridgeSeq(run);
      this.log(run, "status-change", { seq: s, ts: iso(), runStatus: "RUNNING", bridgeStatus: "CANCELLING", reason: "收到取消要求" }, String(s));
      this.metric(run, "progress-update", this.progressData(run, s), String(s));
    }
    run.status = "CANCELLED";
    run.bridgeStatus = "CANCELLED";
    run.completedAt = iso();
    run.current = null;
    this.project.status = "READY";
    for (const i of run.scope) if (run.taskStatus[TASKS[i].id] !== "COMPLETED") run.taskStatus[TASKS[i].id] = "CANCELLED";
    this.closeGateReviews(run, "執行已取消");
    this.statusEvent(run);
  }

  private restoreRun(run: Run, cp: Checkpoint): void {
    run.cursor = cp.stepIdx;
    run.current = null;
    run.status = "RUNNING";
    run.bridgeStatus = "RUNNING";
    run.completedAt = undefined;
    run.reason = undefined;
    this.project.status = "EXECUTING";
    run.scope.forEach((taskIdx, pos) => {
      if (pos >= run.cursor) run.taskStatus[TASKS[taskIdx].id] = "QUEUED";
    });
    for (const r of run.reviews) {
      if (r.status === "PENDING" && r.kind !== "ESCALATED") {
        r.status = "REJECTED";
        r.decidedBy = "system";
        r.comment = "執行已還原";
      }
    }
    const a = this.bridgeSeq(run);
    this.log(run, "alert", { seq: a, ts: iso(), origin: "ENGINE", code: "RESTORE", severity: "INFO", message: `已從斷點 ${cp.name} 還原` }, String(a));
    this.statusEvent(run);
  }

  // ── REST／SSE 處理 ───────────────────────────────────────────────────────
  private summary(r: Run) {
    const total = r.scope.length;
    // 相異任務數（還原重跑時同一任務可能有多列步驟）
    const completed = new Set(r.steps.filter((s) => s.status === "COMPLETED").map((s) => s.taskId)).size;
    const failed = new Set(r.steps.filter((s) => s.status === "FAILED").map((s) => s.taskId)).size;
    return {
      id: r.id,
      projectId: PROJECT_ID,
      runNumber: r.runNumber,
      status: r.status,
      // 批次列表項帶 bridgeStatus（契約 §1.2.2，C-11）：PAUSING／CANCELLING 在列表就看得到
      bridgeStatus: r.bridgeStatus,
      autonomyLevel: r.level,
      scopeMode: "ALL",
      totalTokensUsed: r.tokens,
      tokenBudget: r.budget ?? undefined,
      startedAt: r.startedAt,
      completedAt: r.completedAt,
      durationSec: Math.max(1, Math.round(((r.completedAt ? Date.parse(r.completedAt) : Date.now()) - Date.parse(r.startedAt)) / 1000)),
      tasksTotal: total,
      tasksCompleted: completed,
      tasksFailed: failed,
      // tasksCompleted÷(tasksCompleted＋tasksFailed)×100（小數 1 位）；兩者皆 0 為 null（契約 §1.2.2）
      successRate: completed + failed > 0 ? Math.round((completed / (completed + failed)) * 1000) / 10 : null,
    };
  }

  private detail(r: Run) {
    const cur = r.current !== null ? TASKS[r.scope[r.current]] : undefined;
    // 資源取樣：舊版 Bridge（resources 未設）鍵缺席；有設的也只有 RUNNING 回得出數字，暫停中與終態回 null（契約 §3.1.2）
    const resources = this.resources === undefined ? undefined : this.resources !== null && r.status === "RUNNING" ? { ...this.resources, sampledAt: iso() } : null;
    return {
      id: r.id,
      projectId: PROJECT_ID,
      runNumber: r.runNumber,
      status: r.status,
      bridgeStatus: r.bridgeStatus,
      autonomyLevel: r.level,
      ...(r.engineCapabilities ? { engineCapabilities: r.engineCapabilities } : {}),
      scope: { mode: "ALL", goalIds: [], taskIds: [] },
      totalTokensUsed: r.tokens,
      tokenBudget: r.budget ?? undefined,
      startedAt: r.startedAt,
      completedAt: r.completedAt,
      currentStep: cur
        ? { stepId: this.stepIdOf(r, r.current as number), stepNumber: (r.current as number) + 1, taskId: cur.id, taskName: cur.name, goalId: GOAL_IDS[cur.goalIdx], attempt: 1 }
        : undefined,
      completedSteps: r.cursor,
      totalSteps: r.scope.length,
      lastEventSeq: r.seq,
      reason: r.reason,
      elapsedSec: Math.max(1, Math.round(((r.completedAt ? Date.parse(r.completedAt) : Date.now()) - Date.parse(r.startedAt)) / 1000)),
      pendingReviews: r.reviews.filter((x) => x.status === "PENDING"),
      bridge: { connected: true, instance: "e2e-bridge", status: r.bridgeStatus, runKnown: true, checkedAt: iso(), ...(resources === undefined ? {} : { resources }) },
    };
  }

  private dag(r: Run) {
    const goalIdxs = [...new Set(r.scope.map((i) => TASKS[i].goalIdx))];
    const nodes = [
      ...goalIdxs.map((g, seq) => {
        const statuses = r.scope.filter((i) => TASKS[i].goalIdx === g).map((i) => r.taskStatus[TASKS[i].id]);
        const status = statuses.every((s) => s === "COMPLETED")
          ? "COMPLETED"
          : statuses.some((s) => s === "ESCALATED" || s === "FAILED")
            ? "FAILED"
            : statuses.some((s) => s === "RUNNING" || s === "COMPLETED")
              ? "IN_PROGRESS"
              : "PENDING";
        return { id: GOAL_IDS[g], kind: "GOAL", label: GOAL_NAMES[g], status, sequence: seq + 1 };
      }),
      ...r.scope.map((i, pos) => ({
        id: TASKS[i].id,
        kind: "TASK",
        label: TASKS[i].name,
        status: r.taskStatus[TASKS[i].id],
        goalId: GOAL_IDS[TASKS[i].goalIdx],
        stepId: this.stepIdOf(r, pos),
        sequence: pos + 1,
      })),
    ];
    const edges = [
      ...(goalIdxs.length > 1 ? [{ from: GOAL_IDS[0], to: GOAL_IDS[1], kind: "DEPENDENCY" }] : []),
      ...r.scope.map((i) => ({ from: GOAL_IDS[TASKS[i].goalIdx], to: TASKS[i].id, kind: "CONTAINS" })),
    ];
    return { runId: r.id, nodes, edges, statusAsOf: iso() };
  }

  private page<T>(content: T[], size = 20) {
    return { content, page: 0, size, totalElements: content.length, totalPages: 1 };
  }

  private projectDetail() {
    const latest = this.runs[0];
    const taskStatus = (id: string) => latest?.taskStatus[id] ?? "PENDING";
    const goals = GOAL_IDS.map((gid, g) => {
      const mine = TASKS.filter((t) => t.goalIdx === g);
      const done = mine.filter((t) => taskStatus(t.id) === "COMPLETED").length;
      return {
        id: gid,
        name: GOAL_NAMES[g],
        status: done === mine.length ? "COMPLETED" : done > 0 ? "IN_PROGRESS" : "PENDING",
        sortOrder: g,
        signedOff: this.project.signedOff,
        taskCount: mine.length,
        completedTaskCount: done,
      };
    });
    return {
      id: PROJECT_ID,
      name: "AISDLC Core Platform",
      executionPath: "/work/core",
      passCriteria: "- ok",
      status: this.project.status,
      autonomyLevel: 4,
      signedOff: this.project.signedOff,
      goalsCount: 2,
      tasksCount: 3,
      tasksDone: TASKS.filter((t) => taskStatus(t.id) === "COMPLETED").length,
      createdAt: "2026-10-15T00:00:00Z",
      updatedAt: iso(),
      createdBy: "admin",
      goals,
    };
  }

  private findRun(path: string): Run | undefined {
    const m = /\/(?:executions|stream\/executions)\/([^/]+)/.exec(path);
    return m ? this.runs.find((r) => r.id === m[1]) : undefined;
  }

  private notFound(): MockReply {
    return { status: 404, error: { message: "執行批次不存在或已刪除" } };
  }

  // ── 串流伺服器（真的 HTTP；契約 §2）─────────────────────────────────────────
  /** 啟動串流伺服器（隨機埠）；之後 handler 對 /api/v1/stream/ 的請求改網址轉到這裡。 */
  async listen(): Promise<void> {
    const server = http.createServer((req, res) => this.onStreamRequest(req, res));
    await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
    this.server = server;
    this.base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  }

  async close(): Promise<void> {
    for (const c of this.conns) c.res.destroy();
    this.conns.clear();
    const server = this.server;
    this.server = null;
    if (!server) return;
    await new Promise<void>((resolve) => {
      server.close(() => resolve());
      server.closeAllConnections();
    });
  }

  /** 目前還開著的串流連線數（/logs 與 /metrics 各一條，所以頁面正常連線時是 2）。 */
  get openStreams(): number {
    return this.conns.size;
  }

  /** 模擬網路中斷／伺服器重啟：把所有串流連線直接切斷（瀏覽器會自動重連並帶 Last-Event-ID）。 */
  dropStreams(): void {
    for (const c of this.conns) c.res.destroy();
    this.conns.clear();
  }

  /** 接下來的 n 個串流請求回 503（模擬後端暫時不可用；EventSource 不會自己重連，前端要自己處理）。 */
  refuseStreams(n: number): void {
    this.refuse = n;
  }

  /** 模擬 access token 過期：串流伺服器在下一次 /auth/refresh 之前，對任何現有 token 都回 401。 */
  expireTokens(): void {
    this.validTokens.clear();
  }

  /**
   * 模擬後端整個暫時不可用（DEF-AC-007：經 nginx 部署、backend 重啟的那幾秒，上游不可用時 nginx 立即回 502）：
   * `/api/v1/**` 的 REST 與 `POST /auth/refresh` 回 502（HTML 本文），串流請求也回 502（EventSource 看到非 200＝放棄）。
   * 不會自己切斷既有連線：要同時模擬「連線被切斷」請另呼叫 dropStreams()。
   */
  setOutage(on: boolean): void {
    this.outage = on;
  }

  /** 假 nginx 的 502：本文是 HTML（不是 console-api 的 JSON 封包），前端不得拿它當登入失效。 */
  private badGateway(): MockReply {
    return { status: 502, raw: "<html><body>502 Bad Gateway</body></html>", headers: { "content-type": "text/html" } };
  }

  private emit(run: Run, kind: "logs" | "metrics", ev: Ev): void {
    for (const c of this.conns) {
      if (c.run !== run || c.kind !== kind || c.res.writableEnded) continue;
      c.res.write(frameOf(ev));
      if (isTerminalEvent(kind, ev)) this.closeSoon(c);
    }
  }

  /** 終態：伺服器送完衍生事件後關閉連線（契約 §2.4）；稍等一下，讓同一個 tick 內接著產生的衍生事件先寫出去。 */
  private closeSoon(c: Conn): void {
    setTimeout(() => {
      this.conns.delete(c);
      if (!c.res.writableEnded) c.res.end();
    }, 150);
  }

  /** 新連線先送的事件：/logs＝Last-Event-ID 之後的全部（沒帶＝最後 200 則，§2.3）；/metrics＝收斂快照三則（§2.6）。 */
  private initialEvents(run: Run, kind: "logs" | "metrics", last: [number, number] | null): Ev[] {
    if (kind === "logs") return last ? run.logs.filter((e) => greater(parseId(e.id) as [number, number], last)) : run.logs.slice(-200);
    const s = run.seq;
    return [
      { id: `${s}.1`, name: "progress-update", data: this.progressData(run, s) },
      {
        id: `${s}.2`,
        name: "token-update",
        data: {
          seq: s,
          ts: iso(),
          tokensUsed: run.tokens,
          delta: run.tokens,
          contextPct: 0.6,
          tokenBudget: run.budget,
          budgetUsageRate: run.budget ? Math.round((run.tokens / run.budget) * 1000) / 10 : null,
        },
      },
      { id: `${s}.3`, name: "metric-update", data: this.metricData(run, s, 3) },
    ];
  }

  private onStreamRequest(req: http.IncomingMessage, res: http.ServerResponse): void {
    const cors = { "access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-expose-headers": "X-Trace-Id" };
    if (req.method === "OPTIONS") {
      res.writeHead(204, cors);
      res.end();
      return;
    }
    const url = new URL(req.url ?? "/", this.base);
    const m = /^\/api\/v1\/stream\/executions\/([^/]+)\/(logs|metrics)$/.exec(url.pathname);
    const kind = (m?.[2] ?? "logs") as "logs" | "metrics";
    const lastRaw = typeof req.headers["last-event-id"] === "string" ? req.headers["last-event-id"] : null;
    const token = url.searchParams.get("access_token");
    const attempt: SseAttempt = { kind, runId: m?.[1] ?? "", lastEventId: lastRaw, token, status: 200 };
    this.sseConnections.push(attempt);
    const reject = (status: number, message: string, extra: Record<string, string> = {}) => {
      attempt.status = status;
      res.writeHead(status, { ...cors, ...extra, "content-type": "application/json" });
      res.end(JSON.stringify({ code: status, message, errors: [], timestamp: iso(), traceId: `tr-sse-${status}` }));
    };

    if (this.outage) return reject(502, "Bad Gateway");
    const run = m ? this.runs.find((r) => r.id === m[1]) : undefined;
    if (!run) return reject(404, `執行批次不存在或已刪除：${m?.[1] ?? ""}`);
    // 串流開始前驗 token（契約 §2.1）：無效或過期＝401 JSON，EventSource 只看得到「連線被放棄」
    if (!token || !this.validTokens.has(token)) return reject(401, "access token 無效或已過期");
    if (this.refuse > 0) {
      this.refuse -= 1;
      return reject(503, "服務暫時不可用", { "retry-after": "1" });
    }

    const last = parseId(lastRaw);
    const terminal = TERMINAL.includes(run.status);
    const events = this.initialEvents(run, kind, last);
    // 重連一個已終態、且已看完的 run：HTTP 204（EventSource 收到 204 不再重連；契約 §2.4）
    const caughtUp = kind === "logs" ? events.length === 0 : last !== null && !greater([run.seq, 3], last);
    if (terminal && caughtUp) {
      attempt.status = 204;
      res.writeHead(204, cors);
      res.end();
      return;
    }
    res.writeHead(200, { ...cors, "content-type": "text/event-stream;charset=UTF-8", "cache-control": "no-cache, no-store", "x-accel-buffering": "no" });
    res.write(`retry:300\n\n${events.map(frameOf).join("")}`);
    const conn: Conn = { res, run, kind };
    this.conns.add(conn);
    res.on("close", () => this.conns.delete(conn));
    if (terminal) this.closeSoon(conn);
  }
  readonly handler: MockHandler = async (call) => {
    const { method, path } = call;
    const body = (call.body ?? {}) as Record<string, unknown>;

    // ── 後端不可用（setOutage）：除串流外的 /api/v1/** 一律 502；串流由串流伺服器自己回 502 ──
    if (this.outage && !path.startsWith("/api/v1/stream/")) return this.badGateway();

    // ── 認證：換發 token（前端在 SSE 連線被放棄時會強制換新；契約 §0.4）──
    if (method === "POST" && path === "/api/v1/auth/refresh") {
      this.tokenGen += 1;
      const accessToken = `${FIRST_TOKEN}-${this.tokenGen}`;
      this.validTokens.add(accessToken);
      return { data: { accessToken, refreshToken: `mock-refresh-token-${this.tokenGen}`, expiresIn: 3600, tokenType: "Bearer" } };
    }

    // ── 共用（頂列、側欄）──
    if (method === "GET" && path === "/api/v1/projects") return { data: this.page([{ ...this.projectDetail(), goals: undefined }], 100) };
    if (method === "GET" && path === "/api/v1/notifications/summary") {
      const pendingReviews = this.runs.reduce((n, r) => n + r.reviews.filter((x) => x.status === "PENDING").length, 0);
      return { data: { pendingSignoffs: this.project.signedOff ? 0 : 1, pendingReviews, unacknowledgedAlerts: 0, bridgeConnected: true, bridgeCheckedAt: iso() } };
    }
    if (method === "GET" && path === "/api/v1/settings/execution") {
      const cfg = (key: string, value: string, valueType: string) => ({
        id: nextUuid("c0ffee00"),
        category: "execution",
        key,
        value,
        valueType,
        defaultValue: value,
        description: key,
        isEncrypted: false,
        hasValue: true,
        effect: "CONSOLE",
        updatedAt: iso(),
      });
      return { data: [cfg("globalTokenBudget", "100000", "LONG"), cfg("tokenBudgetWarningThreshold", "0.8", "FLOAT")] };
    }

    // ── 專案與目標（Phase 2）──
    if (method === "GET" && path === `/api/v1/projects/${PROJECT_ID}`) return { data: this.projectDetail() };
    if (method === "POST" && path === `/api/v1/projects/${PROJECT_ID}/signoff`) {
      this.project.signedOff = true;
      return { data: { ...this.projectDetail(), goals: undefined, signedOffBy: body.approver } };
    }
    const goalTasks = /^\/api\/v1\/goals\/([^/]+)\/tasks$/.exec(path);
    if (method === "GET" && goalTasks) {
      const g = GOAL_IDS.indexOf(goalTasks[1] as (typeof GOAL_IDS)[number]);
      const latest = this.runs[0];
      return {
        data: TASKS.filter((t) => t.goalIdx === g).map((t, i) => ({
          id: t.id,
          goalId: goalTasks[1],
          name: t.name,
          sortOrder: i,
          status: latest?.taskStatus[t.id] ?? "PENDING",
          retryCount: 0,
          maxRetries: 1,
          signedOff: true,
          updatedAt: iso(),
        })),
      };
    }

    // ── 執行（Phase 4）──
    if (method === "POST" && path === `/api/v1/projects/${PROJECT_ID}/execute`) {
      if (!this.project.signedOff) {
        return {
          status: 409,
          error: {
            message: "草案未經人工審批，禁止執行",
            reason: "未經人工審批的草案不可執行",
            details: { unsignedProjectId: PROJECT_ID, unsignedGoalIds: [...GOAL_IDS], unsignedTaskIds: TASKS.map((t) => t.id) },
          },
        };
      }
      if (this.project.status === "EXECUTING") return { status: 409, error: { message: "專案正在執行中", reason: "專案正在執行中", details: { projectId: PROJECT_ID, runId: this.latest?.id } } };
      const scopeBody = (body.scope ?? {}) as { mode?: string; goalIds?: string[]; taskIds?: string[] };
      let idxs = TASKS.map((_, i) => i);
      if (scopeBody.mode === "SELECTED") {
        idxs = idxs.filter((i) => (scopeBody.goalIds ?? []).includes(GOAL_IDS[TASKS[i].goalIdx]) || (scopeBody.taskIds ?? []).includes(TASKS[i].id));
      }
      const done = this.latest
        ? new Set(
            Object.entries(this.latest.taskStatus)
              .filter(([, s]) => s === "COMPLETED")
              .map(([id]) => id),
          )
        : new Set<string>();
      idxs = idxs.filter((i) => !done.has(TASKS[i].id));
      if (idxs.length === 0) return { status: 409, error: { message: "沒有可執行的任務", reason: "沒有可執行的任務" } };
      const run = this.createRun(Number(body.autonomyLevel ?? 4), typeof body.tokenBudget === "number" ? body.tokenBudget : 100000, idxs);
      return {
        status: 201,
        data: {
          id: run.id,
          projectId: PROJECT_ID,
          runNumber: run.runNumber,
          status: run.status,
          bridgeStatus: run.bridgeStatus,
          autonomyLevel: run.level,
          ...(run.engineCapabilities ? { engineCapabilities: run.engineCapabilities } : {}),
          scope: { mode: scopeBody.mode ?? "ALL", goalIds: scopeBody.goalIds ?? [], taskIds: scopeBody.taskIds ?? [] },
          totalTokensUsed: 0,
          tokenBudget: run.budget ?? undefined,
          startedAt: run.startedAt,
        },
      };
    }
    if (method === "GET" && path === `/api/v1/projects/${PROJECT_ID}/executions`) return { data: this.page(this.runs.map((r) => this.summary(r))) };

    const run = this.findRun(path);
    const sub = /\/(?:executions|stream\/executions)\/[^/]+\/?(.*)$/.exec(path)?.[1] ?? "";
    if (path.includes("/executions/") && !run) return this.notFound();
    if (run) {
      if (method === "GET" && path.startsWith("/api/v1/stream/")) {
        if (!this.server) throw new Error("Engine.listen() 尚未呼叫：串流伺服器沒有啟動");
        const qs = call.query.toString();
        return { proxyTo: `${this.base}${path}${qs ? `?${qs}` : ""}` };
      }
      if (method === "GET" && sub === "") return { data: this.detail(run) };
      if (method === "GET" && sub === "dag") return { data: this.dag(run) };
      if (method === "GET" && sub === "checkpoints") return { data: run.checkpoints };
      if (method === "GET" && sub === "steps") {
        const after = Number(call.query.get("afterSeq") ?? 0);
        return {
          data: this.page(
            run.steps.filter((s) => s.stepNumber > after),
            200,
          ),
        };
      }
      const snapshot = () => ({
        id: run.id,
        projectId: PROJECT_ID,
        runNumber: run.runNumber,
        status: run.status,
        bridgeStatus: run.bridgeStatus,
        autonomyLevel: run.level,
        ...(run.engineCapabilities ? { engineCapabilities: run.engineCapabilities } : {}),
        scope: { mode: "ALL", goalIds: [], taskIds: [] },
        totalTokensUsed: run.tokens,
        tokenBudget: run.budget ?? undefined,
        startedAt: run.startedAt,
        completedAt: run.completedAt,
      });
      const stateError = (action: string): MockReply => ({
        status: 409,
        error: { message: "目前執行狀態不允許此操作", reason: "目前執行狀態不允許此操作", details: { action, runStatus: run.status, bridgeStatus: run.bridgeStatus } },
      });
      if (method === "POST" && sub === "pause") {
        if (run.status !== "RUNNING") return stateError("pause");
        run.pauseRequested = true;
        run.bridgeStatus = "PAUSING";
        const s = this.bridgeSeq(run);
        this.log(run, "status-change", { seq: s, ts: iso(), runStatus: "RUNNING", bridgeStatus: "PAUSING", reason: "已要求暫停" }, String(s));
        this.metric(run, "progress-update", this.progressData(run, s), String(s));
        if (run.current === null) {
          // 剛好在步驟邊界：直接停下
          run.pauseRequested = false;
          run.status = "PAUSED";
          run.bridgeStatus = "PAUSED";
          this.project.status = "READY";
          this.statusEvent(run, `在步驟邊界暫停（已完成 ${run.cursor} 步）`);
        }
        return { data: snapshot() };
      }
      if (method === "POST" && sub === "resume") {
        if (run.status !== "PAUSED") return stateError("resume");
        this.resumeRun(run, "operator", "以手動恢復處理");
        return { data: snapshot() };
      }
      if (method === "POST" && sub === "cancel") {
        if (run.status !== "RUNNING" && run.status !== "PAUSED") return stateError("cancel");
        this.cancelRun(run);
        return { data: snapshot() };
      }
      const restore = /^restore\/([^/]+)$/.exec(sub);
      if (method === "POST" && restore) {
        const cp = run.checkpoints.find((c) => c.id === restore[1]);
        if (!cp) return { status: 404, error: { message: `checkpoint 不存在或不屬於此執行：${restore[1]}` } };
        if (run.status === "RUNNING") return stateError("restore");
        this.restoreRun(run, cp);
        return { data: snapshot() };
      }
      const review = /^review\/([^/]+)$/.exec(sub);
      if (method === "POST" && review) {
        const r = run.reviews.find((x) => x.id === review[1]);
        if (!r) return { status: 404, error: { message: `審核項不存在或不屬於此執行：${review[1]}` } };
        const decision = String(body.decision);
        if (r.status !== "PENDING") return { status: 409, error: { message: "審核項已被處理", reason: "審核項已處理", details: { status: r.status, decidedBy: r.decidedBy } } };
        if (!r.allowedDecisions.includes(decision))
          return { status: 409, error: { message: "此審核項不允許該決定", reason: "此審核項不允許該決定", details: { kind: r.kind, decision, allowedDecisions: r.allowedDecisions } } };
        r.comment = typeof body.comment === "string" ? body.comment : undefined;
        r.decidedBy = "operator";
        if (r.kind !== "ESCALATED") {
          if (run.status !== "PAUSED") return stateError("review");
          if (decision === "APPROVE") {
            r.status = "APPROVED";
            this.resumeRun(run, "operator", r.comment ?? "");
            r.comment = r.comment;
          } else if (decision === "REJECT") {
            r.status = "REJECTED";
            this.cancelRun(run);
          }
          return { status: 204 };
        }
        // ESCALATED（run 已 FAILED）
        if (decision === "REJECT") {
          r.status = "REJECTED";
          return { status: 204 };
        }
        if (decision === "RETRY") {
          const failedPos = run.scope.findIndex((i) => TASKS[i].id === r.taskId);
          const cp = [...run.checkpoints].reverse().find((c) => c.stepIdx === failedPos);
          if (cp) {
            r.status = "RETRIED";
            this.restoreRun(run, cp);
            return { status: 204 };
          }
          // 第一步失敗：沒有更早的檢查點 → 另開後續批次
          r.status = "RETRIED";
          const follow = this.createRun(run.level, run.budget, run.scope.slice());
          return { status: 204, headers: { "X-Follow-Up-Run-Id": follow.id } };
        }
        // SKIP：失敗任務標跳過，以其餘任務另開後續批次
        r.status = "SKIPPED";
        run.taskStatus[r.taskId as string] = "SKIPPED";
        const rest = run.scope.filter((i) => TASKS[i].id !== r.taskId && run.taskStatus[TASKS[i].id] !== "COMPLETED");
        const follow = this.createRun(run.level, run.budget, rest);
        return { status: 204, headers: { "X-Follow-Up-Run-Id": follow.id } };
      }
    }
    return undefined;
  };
}
