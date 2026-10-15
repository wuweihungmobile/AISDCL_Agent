/**
 * 執行頁的「即時層」純邏輯（契約 §2、§2.5～§2.7）：把 SSE 事件變成畫面要的資料。不依賴 React、不碰網路。
 *
 * 兩條路：
 *  1. 即時日誌與任務狀態（只存在於串流）→ applyStreamEvents：reducer 式，一次吃一批事件、只複製一次。
 *  2. 批次本身的進度／狀態／Token／待審核項（REST 也有）→ patchRunDetail：直接改寫 TanStack Query 快取裡的
 *     ExecutionRunDetail，這樣畫面永遠只讀一份資料（REST 當底、SSE 當即時修補），REST 重抓時以最新者為準。
 *     版本戳＝lastEventSeq：事件 seq 小於快取內已知的最後 seq（例如 /metrics 與 /logs 兩條串流交錯、或 REST 剛重抓過）
 *     就不覆寫狀態類欄位，避免「舊事件把新狀態蓋回去」。
 */
import type {
  AlertEventData,
  ExecutionRunDetail,
  ExecutionStep,
  ExecutionStepStatus,
  LogEventData,
  LogLevel,
  StatusChangeEventData,
} from "@/lib/api/types";
import type { RunStreamEvent } from "@/lib/api/sse";
import { alertSeverity, runStatusMeta } from "@/lib/domain/status";

export type LogLineKind = "step" | "engine" | "status" | "alert" | "review";
/** DEBUG／INFO／WARN／ERROR／CRITICAL（契約 §2.5 `log.level`） */
export type LogLineLevel = LogEventData["level"];

export type LogLine = {
  /** 去重鍵：重連重播、REST 回補與即時事件可能送同一行 */
  key: string;
  /** 排序用：Bridge seq（Console 自產事件取錨點 seq） */
  seq: number;
  /** 同一 seq 內的先後（子序號；Bridge 事件為 0） */
  sub: number;
  ts: string;
  kind: LogLineKind;
  level: LogLineLevel;
  message: string;
  taskId?: string;
  stepStatus?: ExecutionStepStatus;
};

/** 引擎自己的 stdout 一行一則，量大；與重要行分開存，各自有上限。 */
export const MAX_LINES = 1000;
export const MAX_ENGINE_LINES = 1500;

export type TaskLive = { status: "RUNNING" | "COMPLETED" | "FAILED"; seq: number };

export type LiveState = {
  runId: string | null;
  /** 步驟摘要、狀態變化、告警、審核（依 seq 升冪） */
  lines: LogLine[];
  /** 引擎原始輸出（依 seq 升冪） */
  engine: LogLine[];
  /** 任務在串流裡看到的最新狀態（疊加到 DAG 上；以 seq 當版本戳） */
  taskStatus: Record<string, TaskLive>;
};

export function initialLive(runId: string | null): LiveState {
  return { runId, lines: [], engine: [], taskStatus: {} };
}

// ── 訊息樣板（契約 §2.5 與 §3.8.3 的 STEP 訊息）─────────────────────────────────
export type StepMessageInput = {
  status: ExecutionStepStatus;
  taskName?: string;
  stepId?: string;
  attempt?: number;
  errorMessage?: string | null;
  tokensUsed?: number | null;
};

export function stepMessage(s: StepMessageInput): string {
  const name = s.taskName ?? s.stepId ?? "（未命名任務）";
  const where = s.stepId ?? "";
  const nth = s.attempt ? `第 ${s.attempt} 次` : "";
  const inner = [where, nth].filter(Boolean).join("，");
  switch (s.status) {
    case "STARTED":
      return `開始：${name}（${inner}）`;
    case "RETRYING":
      return `重試：${name}（${inner}）`;
    case "COMPLETED":
      return `完成：${name}（${where}）${s.tokensUsed ? ` Token: ${s.tokensUsed}` : ""}`;
    case "FAILED":
      return `失敗：${name}（${inner}）${s.errorMessage ? `：${s.errorMessage}` : ""}`;
  }
}

const STEP_LEVEL: Record<ExecutionStepStatus, LogLevel> = {
  STARTED: "INFO",
  COMPLETED: "INFO",
  RETRYING: "WARN",
  FAILED: "ERROR",
};

/** REST 回補用：一列步驟（execution_steps）轉成與 SSE `log`（source=STEP）同形的資料，之後走同一條去重與顯示路徑。 */
export function stepToLogData(step: ExecutionStep): LogEventData {
  return {
    seq: step.stepNumber,
    ts: step.timestamp,
    source: "STEP",
    level: STEP_LEVEL[step.status],
    message: stepMessage({
      status: step.status,
      taskName: step.taskName,
      stepId: step.stepId,
      attempt: step.attempt,
      errorMessage: step.errorMessage,
      tokensUsed: step.tokensUsed,
    }),
    stepId: step.stepId,
    taskId: step.taskId,
    taskName: step.taskName,
    goalId: step.goalId,
    attempt: step.attempt,
    stepStatus: step.status,
    tokensUsed: step.tokensUsed,
  };
}

/** STEP 的事件狀態 → 任務在 DAG 上的即時狀態（STARTED／RETRYING 都是「進行中」）。 */
export function taskLiveFromStep(status: ExecutionStepStatus): TaskLive["status"] {
  return status === "COMPLETED" ? "COMPLETED" : status === "FAILED" ? "FAILED" : "RUNNING";
}

function statusLevel(runStatus: string): LogLineLevel {
  if (runStatus === "FAILED") return "ERROR";
  if (runStatus === "CANCELLED" || runStatus === "PAUSED") return "WARN";
  return "INFO";
}

function statusLine(d: StatusChangeEventData): LogLine {
  const label = runStatusMeta(d.runStatus, d.bridgeStatus).label;
  return {
    key: `status:${d.seq}`,
    seq: d.seq,
    sub: 0,
    ts: d.ts,
    kind: "status",
    level: statusLevel(d.runStatus),
    message: `狀態：${label}${d.reason ? `（${d.reason}）` : ""}`,
  };
}

function alertLine(d: AlertEventData, id: string | null): LogLine {
  const sev = d.severity;
  const key = d.origin === "CONSOLE" && typeof d.sub !== "number" ? `alert:tr:${d.code ?? ""}:${d.ts}` : `alert:${id ?? d.seq}`;
  return {
    key,
    seq: d.seq,
    sub: d.sub ?? 0,
    ts: d.ts,
    kind: "alert",
    level: sev === "CRITICAL" ? "ERROR" : sev === "WARNING" ? "WARN" : "INFO",
    message: `告警（${alertSeverity(sev).label}）：${d.message}`,
  };
}

function toLogLine(event: RunStreamEvent): LogLine | null {
  switch (event.name) {
    case "log": {
      const d = event.data;
      const engine = d.source === "ENGINE";
      return {
        key: `${engine ? "engine" : "step"}:${d.seq}`,
        seq: d.seq,
        sub: 0,
        ts: d.ts,
        kind: engine ? "engine" : "step",
        level: d.level,
        message: d.message,
        taskId: d.taskId,
        stepStatus: d.stepStatus,
      };
    }
    case "status-change":
      return statusLine(event.data);
    case "alert":
      return alertLine(event.data, event.id);
    case "review-request": {
      const d = event.data;
      return {
        key: `review:${d.review.id}`,
        seq: d.seq,
        sub: d.sub,
        ts: d.ts,
        kind: "review",
        level: "WARN",
        message: `待審核：${d.review.reason}`,
        taskId: d.review.taskId,
      };
    }
    default:
      return null; // /metrics 的三種事件不進日誌
  }
}

/** 引擎的還原告警（契約 §2.5：`origin=ENGINE`、`code=RESTORE`、severity=INFO）。 */
const isRestoreAlert = (d: AlertEventData): boolean => d.origin === "ENGINE" && d.code === "RESTORE";

const byOrder = (a: LogLine, b: LogLine) => a.seq - b.seq || a.sub - b.sub;

function insertSorted(list: LogLine[], line: LogLine): void {
  const last = list[list.length - 1];
  if (!last || byOrder(last, line) <= 0) {
    list.push(line);
    return;
  }
  // 重播／回補的舊行：找位置插入（陣列有上限，線性掃描可接受）
  let i = list.length - 1;
  while (i >= 0 && byOrder(list[i], line) > 0) i -= 1;
  list.splice(i + 1, 0, line);
}

/**
 * 套用一批串流事件：回傳新狀態（輸入不被修改）。
 * 重複的行（key 相同）略過；STEP 的 taskId＋stepStatus 同時更新任務即時狀態（seq 較舊者不覆寫）；
 * /metrics 的 progress-update 帶 currentStep 時，把該任務標為進行中（同樣受 seq 約束）。
 */
export function applyStreamEvents(state: LiveState, events: readonly RunStreamEvent[]): LiveState {
  if (events.length === 0) return state;
  const lines = state.lines.slice();
  const engine = state.engine.slice();
  const taskStatus = { ...state.taskStatus };
  const seen = new Set<string>([...lines, ...engine].map((l) => l.key));
  let changed = false;

  const stamp = (taskId: string | undefined, status: TaskLive["status"], seq: number) => {
    if (!taskId) return;
    const cur = taskStatus[taskId];
    if (cur && seq < cur.seq) return; // 較舊的事件不覆寫
    if (cur && cur.seq === seq && cur.status === status) return; // 重播的同一則：沒有變化
    taskStatus[taskId] = { status, seq };
    changed = true;
  };

  for (const event of events) {
    if (event.name === "progress-update") {
      const cs = event.data.currentStep;
      if (cs?.taskId) stamp(cs.taskId, "RUNNING", event.data.seq);
      continue;
    }
    const line = toLogLine(event);
    if (!line) continue;
    if (event.name === "alert" && isRestoreAlert(event.data) && !seen.has(line.key)) {
      // 還原（restore）：此前串流看到的任務狀態全部作廢——被還原掉的步驟要回到待處理，由 REST 的 DAG 當底、之後的步驟事件再逐步疊上去。
      // 只在「第一次見到」這則告警時清（重播同一則不可把還原之後累積的狀態清掉）。
      for (const id of Object.keys(taskStatus)) delete taskStatus[id];
      changed = true;
    }
    if (event.name === "log" && event.data.taskId && event.data.stepStatus) {
      stamp(event.data.taskId, taskLiveFromStep(event.data.stepStatus), event.data.seq);
    }
    if (seen.has(line.key)) continue;
    seen.add(line.key);
    insertSorted(line.kind === "engine" ? engine : lines, line);
    changed = true;
  }
  if (!changed) return state;

  const cappedLines = lines.length > MAX_LINES ? lines.slice(lines.length - MAX_LINES) : lines;
  const cappedEngine = engine.length > MAX_ENGINE_LINES ? engine.slice(engine.length - MAX_ENGINE_LINES) : engine;
  return { runId: state.runId, lines: cappedLines, engine: cappedEngine, taskStatus };
}

export type LiveAction = { type: "events"; runId: string | null; events: readonly RunStreamEvent[] };

/** useReducer 用：事件屬於別的批次（切換批次的瞬間）就從空白開始，不混進舊批次的內容。 */
export function liveReducer(state: LiveState, action: LiveAction): LiveState {
  const base = state.runId === action.runId ? state : initialLive(action.runId);
  return applyStreamEvents(base, action.events);
}

/** 顯示用：重要行，加上（選擇時）引擎原始輸出，依 (seq, sub) 合併。 */
export function visibleLines(state: LiveState, showEngine: boolean): LogLine[] {
  if (!showEngine || state.engine.length === 0) return state.lines;
  return [...state.lines, ...state.engine].sort(byOrder);
}

// ── 批次快取修補（REST 當底、SSE 當即時修補）────────────────────────────────────
/** 事件是否「比快取新或一樣新」：小於快取已知的最後 seq 就是舊事件。 */
function isFresh(detail: ExecutionRunDetail, seq: number): boolean {
  return seq >= (detail.lastEventSeq ?? 0);
}

/**
 * 把一則串流事件修補進批次詳情；回傳同一個物件＝沒有變化（呼叫端可據此略過 setQueryData）。
 * 只改「串流真的知道」的欄位；審核項以 id 去重、只加不刪（已處理的由 REST 重抓或使用者決定後移除）。
 */
export function patchRunDetail(detail: ExecutionRunDetail, event: RunStreamEvent): ExecutionRunDetail {
  switch (event.name) {
    case "status-change": {
      const d = event.data;
      if (!isFresh(detail, d.seq)) return detail;
      return {
        ...detail,
        status: d.runStatus,
        bridgeStatus: d.bridgeStatus,
        reason: d.reason || undefined,
        lastEventSeq: Math.max(detail.lastEventSeq ?? 0, d.seq),
        bridge: { ...detail.bridge, status: d.bridgeStatus },
      };
    }
    case "progress-update": {
      const d = event.data;
      if (!isFresh(detail, d.seq)) return detail;
      return {
        ...detail,
        status: d.runStatus,
        bridgeStatus: d.bridgeStatus,
        completedSteps: d.completedSteps,
        totalSteps: d.totalSteps,
        currentStep: d.currentStep,
        lastEventSeq: Math.max(detail.lastEventSeq ?? 0, d.seq),
        bridge: { ...detail.bridge, status: d.bridgeStatus },
      };
    }
    case "token-update": {
      const d = event.data;
      if (!isFresh(detail, d.seq)) return detail;
      return {
        ...detail,
        totalTokensUsed: d.tokensUsed,
        tokenBudget: d.tokenBudget ?? detail.tokenBudget,
        lastEventSeq: Math.max(detail.lastEventSeq ?? 0, d.seq),
      };
    }
    case "metric-update": {
      const d = event.data;
      if (!isFresh(detail, d.seq)) return detail;
      return {
        ...detail,
        totalTokensUsed: d.totalTokensUsed,
        elapsedSec: d.elapsedSec,
        lastEventSeq: Math.max(detail.lastEventSeq ?? 0, d.seq),
      };
    }
    case "review-request": {
      const review = event.data.review;
      if (review.status !== "PENDING") return detail;
      if (detail.pendingReviews.some((r) => r.id === review.id)) return detail;
      return { ...detail, pendingReviews: [...detail.pendingReviews, review] };
    }
    default:
      return detail;
  }
}

/** 這則事件之後，批次詳情應該向伺服器重抓嗎（終態的 completedAt／elapsedSec、審核項、告警後的狀態以 REST 為準）。 */
export function needsDetailRefresh(event: RunStreamEvent): boolean {
  if (event.name === "status-change") return true;
  if (event.name === "review-request") return true;
  if (event.name === "alert") return event.data.origin === "ENGINE" || typeof event.data.sub === "number";
  return false;
}

export type RefreshPlan = {
  /** 批次詳情（審核項、終態的 completedAt／elapsedSec） */
  detail: boolean;
  /** DAG 節點狀態（步驟完成或失敗、狀態變化） */
  dag: boolean;
  /** 通知摘要（待審核數、未確認告警數） */
  notifications: boolean;
  /** 批次列表與專案三層（狀態變化會讓專案 EXECUTING⇄READY⇄COMPLETED） */
  runs: boolean;
};

/** 一批事件之後要向伺服器重抓什麼：把「每則事件各觸發一次重抓」合併成一次。 */
export function refreshPlan(events: readonly RunStreamEvent[]): RefreshPlan {
  const plan: RefreshPlan = { detail: false, dag: false, notifications: false, runs: false };
  for (const e of events) {
    if (needsDetailRefresh(e)) plan.detail = true;
    if (e.name === "status-change") {
      plan.dag = true;
      plan.runs = true;
    }
    if (e.name === "log" && (e.data.stepStatus === "COMPLETED" || e.data.stepStatus === "FAILED")) plan.dag = true;
    if (e.name === "alert" && isRestoreAlert(e.data)) plan.dag = true; // 還原讓一批任務回到待處理
    if (e.name === "review-request" || (e.name === "alert" && needsDetailRefresh(e))) plan.notifications = true;
  }
  return plan;
}
