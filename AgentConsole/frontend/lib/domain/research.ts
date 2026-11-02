/**
 * ResearchToPRD（研發工作流）的純函式與常數（TCS-ResearchToPRD-P0-20261102 §5.1、§7；PRD FR-R2P-01、21、22、23；API 契約 §1.3、§1.4）。
 * 全檔不讀瀏覽器儲存、不碰 DOM、不發請求：元件只負責把這裡的結果畫出來。
 *
 * 邊界（為什麼這樣切）：
 *  - **流程游標由後端原樣給**：`flow_step`／`flow_phase`／`flow_status` 只由 Bridge 在引擎動作的同一交易寫入，前端沒有「推進游標」的函式，也不自行衍生 `flow_status`
 *    （D-59(3)）；這裡只做顯示用的整形（五步列的狀態、可達性、燈號、等待時數）。
 *  - **一個詞彙一個出處**：`FLOW_STATUS_LABEL`、`FLOW_PHASE_LABEL` 是 `researchFlow` 狀態說明表的上游常數（lib/help/states.ts 與 stateSources.ts 以它的鍵集合為準）。
 *  - **審查預算只認 FSM 視圖**：剩餘預算＝`max(0, REVIEW_RETRY_LIMIT − currentCount)`，`currentCount` 唯一來源是 `retryHistory.gates.SCG_VALIDATION.currentCount`，
 *    不取審查輪列的 `fsmRetryCount`（那是該輪 gate 當下的回傳值，人工恢復後不歸零，兩者不是同一件事；D-60）。
 *  - **研究的 reason 不進 `REASONS`**：`lib/api/reasons.ts` 與凍結契約附錄 B 雙向鎖，多一個常數即紅；研究 reason 放在這裡的 `RESEARCH_REASONS`（⚖12，先例 SI_REASONS）。
 */
import { z } from "zod";

import { ApiError, describeError } from "@/lib/api/client";
import type {
  Config,
  ResearchCreateRequest,
  ResearchDepthLevel,
  ResearchDerivedFlowPhase,
  ResearchEvent,
  ResearchFlowPhase,
  ResearchFlowStatus,
  ResearchFlowStepId,
  ResearchFlowStepState,
  ResearchFsmView,
  ResearchProjectDetail,
  ResearchProjectSummary,
  ResearchReconcileResult,
  ResearchReviewRound,
} from "@/lib/api/types";
import type { StatusMeta } from "@/lib/domain/status";

// ── 五步（FR-R2P-01）──────────────────────────────────────────────────────────────

/** 工作流五步，順序固定（增減步驟＝PRD 修訂）。 */
export const FLOW_STEP_IDS: readonly ResearchFlowStepId[] = ["topic", "studio", "route", "build", "deliver"];

/** 步驟名稱（PRD §7.2 示意版面：研究、規格工作室、分流、拆解與執行、交付）。 */
export const FLOW_STEP_LABEL: Readonly<Record<ResearchFlowStepId, string>> = {
  topic: "研究",
  studio: "規格工作室",
  route: "分流",
  build: "拆解與執行",
  deliver: "交付",
};

/** 步驟狀態的文字（可及名稱必須含它，不只靠顏色；AC-R2P-01-1）。 */
export const STEP_STATE_LABEL: Readonly<Record<ResearchFlowStepState, string>> = { DONE: "已完成", CURRENT: "進行中", BLOCKED: "受阻", TODO: "待做" };

/** 進行中的步驟遇到這三種 `flow_status` 時改標「受阻」。 */
export const BLOCKING_FLOW_STATUSES: readonly ResearchFlowStatus[] = ["BLOCKED", "ESCALATED", "FAILED"];

export function isFlowStepId(value: unknown): value is ResearchFlowStepId {
  return typeof value === "string" && (FLOW_STEP_IDS as readonly string[]).includes(value);
}

/** 0 起算的步驟序（topic＝0）。 */
export function stepIndex(step: ResearchFlowStepId): number {
  return FLOW_STEP_IDS.indexOf(step);
}

/** 顯示用的步驟序號（topic＝1）。 */
export function stepNumber(step: ResearchFlowStepId): number {
  return stepIndex(step) + 1;
}

export type ResearchStepView = { id: ResearchFlowStepId; number: number; label: string; state: ResearchFlowStepState };

/**
 * 五步列的狀態（AC-R2P-01-1）：序號小於目前步＝已完成、等於＝進行中、大於＝待做；`status` 為 BLOCKED／ESCALATED／FAILED 時第 k 項改標受阻。
 * 恆回五項；`current` 取 `flow.effective.step`（步驟 1～3 即 DB 游標，之後由後端衍生）。
 */
export function deriveSteps(current: ResearchFlowStepId, status: ResearchFlowStatus): ResearchStepView[] {
  const k = stepIndex(current);
  const blocked = BLOCKING_FLOW_STATUSES.includes(status);
  return FLOW_STEP_IDS.map((id, i) => ({
    id,
    number: i + 1,
    label: FLOW_STEP_LABEL[id],
    state: i < k ? "DONE" : i > k ? "TODO" : blocked ? "BLOCKED" : "CURRENT",
  }));
}

/** 網址 `?step=` 的步驟只在「不超前於 furthestStep」時可達（AC-R2P-01-8）。 */
export function stepReachable(step: ResearchFlowStepId, furthest: ResearchFlowStepId): boolean {
  return stepIndex(step) <= stepIndex(furthest);
}

/**
 * 解析網址的 `?step=`：合法且可達就照它顯示；超前、缺少或不是五步之一，一律顯示游標所在步並要求把網址導回（`redirect`）。
 * `furthest` 若小於 `current`（資料不一致）以 `current` 為準，所以游標所在步永遠可達。
 */
export function resolveViewStep(param: string | null | undefined, current: ResearchFlowStepId, furthest: ResearchFlowStepId): { step: ResearchFlowStepId; redirect: boolean } {
  const reach = stepIndex(furthest) >= stepIndex(current) ? furthest : current;
  if (isFlowStepId(param) && stepReachable(param, reach)) return { step: param, redirect: false };
  return { step: current, redirect: true };
}

/** 已完成的步驟（序號小於游標所在步）只能唯讀檢視（AC-R2P-01-4）。 */
export function isCompletedStep(viewed: ResearchFlowStepId, current: ResearchFlowStepId): boolean {
  return stepIndex(viewed) < stepIndex(current);
}

// ── 狀態詞彙（researchFlow 狀態說明表的上游）──────────────────────────────────────────

/** `flow_status` 八個 DB 值加衍生的 PAUSED（只出現在 `flow.effective`）。 */
export const FLOW_STATUS_LABEL: Readonly<Record<ResearchFlowStatus, string>> = {
  IDLE: "閒置",
  RUNNING: "執行中",
  WAITING_HUMAN: "等待人工",
  BLOCKED: "受阻",
  ESCALATED: "待人工處理",
  FAILED: "失敗",
  CANCELLED: "已取消",
  COMPLETED: "已完成",
  PAUSED: "已暫停",
};

/** `flow_phase` 十三個 DB 值加五個衍生相態（`FLOW_PHASE_DERIVED`；衍生值不落 DB）。 */
export const FLOW_PHASE_LABEL: Readonly<Record<ResearchFlowPhase | ResearchDerivedFlowPhase, string>> = {
  INGESTED: "議題已受理",
  RESEARCHING: "研究中",
  EVIDENCE_READY: "證據已備妥",
  DRAFTING: "草擬中",
  REVIEWING: "審查中",
  REVISING: "修訂中",
  GATE0_PENDING: "等待核准",
  FROZEN: "規格已凍結",
  ROUTING: "分流中",
  ROUTED: "已分流",
  TCS_DRAFTING: "測試規格草擬中",
  TCS_PENDING: "測試規格待核准",
  SCR_OPEN: "規格變更中",
  BUILDING: "建置中",
  HEALING: "自癒中",
  AWAITING_HUMAN: "等待人工審核",
  RELEASE_PENDING: "待發布",
  DELIVERED: "已交付",
};

/** 衍生相態（由 `ResearchFlowPolicy` 自 FSM 與 `execution_runs` 即時推算，不落 DB）。 */
export const FLOW_PHASE_DERIVED: readonly ResearchDerivedFlowPhase[] = ["BUILDING", "HEALING", "AWAITING_HUMAN", "RELEASE_PENDING", "DELIVERED"];

/** 兩張詞彙表合起來的鍵（`researchFlow` 狀態說明表的鍵集合；status 與 phase 的值域不相交）。 */
export const FLOW_VOCABULARY_KEYS: readonly string[] = [...Object.keys(FLOW_STATUS_LABEL), ...Object.keys(FLOW_PHASE_LABEL)];

/** 未登記的值顯示原值、不丟例外（後端日後新增值時畫面不崩潰）。 */
export function flowStatusLabel(status: string): string {
  return (FLOW_STATUS_LABEL as Readonly<Record<string, string | undefined>>)[status] ?? status;
}

export function flowPhaseLabel(phase: string): string {
  return (FLOW_PHASE_LABEL as Readonly<Record<string, string | undefined>>)[phase] ?? phase;
}

/** `researchFlow` 表的「狀態」欄名稱：先認 flow_status、再認 flow_phase，都不是就顯示原值。 */
export function flowVocabularyLabel(key: string): string {
  const status = (FLOW_STATUS_LABEL as Readonly<Record<string, string | undefined>>)[key];
  if (status !== undefined) return status;
  return flowPhaseLabel(key);
}

// ── 工作流頁首的狀態燈（FR-R2P-22；AC-R2P-22-2）─────────────────────────────────────────

export type LampKind = "Escalated" | "Healing" | "Running" | "Paused" | "Idle";

/** 優先序由高到低（Escalated 高於 Healing 高於 Running 高於 Paused 高於 Idle）。 */
export const LAMP_ORDER: readonly LampKind[] = ["Escalated", "Healing", "Running", "Paused", "Idle"];

/** 燈號以文字標籤為準，顏色只作輔助（顏色一律取設計 token）。 */
export const LAMP_META: Readonly<Record<LampKind, StatusMeta>> = {
  Escalated: { label: "待人工", color: "var(--color-accent)" },
  Healing: { label: "自癒中", color: "var(--color-warning)" },
  Running: { label: "執行中", color: "var(--color-primary)" },
  Paused: { label: "已暫停", color: "var(--color-text-muted)" },
  Idle: { label: "閒置", color: "var(--color-disabled-text)" },
};

export type LampRun = "none" | "RUNNING" | "PAUSED";
export type LampFsm = "ok" | "ESCALATION";
export type LampTasks = { escalated: boolean; retrying: boolean; reviewEscalated: boolean };

/**
 * 燈號規則（純函式、窮舉表測試）：FSM ESCALATION、任務 ESCALATED 或審查 ESCALATE 任一即 Escalated；
 * 其次 RUNNING 且有任務在重試或修正＝Healing；RUNNING＝Running；PAUSED＝Paused（SA 增補第五態，D-20 SA-06）；其餘 Idle。
 */
export function lampOf(run: LampRun, fsm: LampFsm, tasks: LampTasks): LampKind {
  if (fsm === "ESCALATION" || tasks.escalated || tasks.reviewEscalated) return "Escalated";
  if (run === "RUNNING" && tasks.retrying) return "Healing";
  if (run === "RUNNING") return "Running";
  if (run === "PAUSED") return "Paused";
  return "Idle";
}

/**
 * 頁首由研究專案詳情取燈號輸入：run 與 FSM 都取自後端已衍生的 `flow.effective.status`（不另打請求、不自行衍生）；
 * 衍生相態 HEALING 即「RUNNING 且有任務在重試」。P0 沒有任務，所以 `escalated` 與 `reviewEscalated` 恆為假（未處理的升級由 FSM 態表達，不靠審查輪列：
 * 人工恢復後最新輪仍是 ESCALATE，但升級已解除）。
 */
export function lampInputsOf(project: Pick<ResearchProjectDetail, "flow">): { run: LampRun; fsm: LampFsm; tasks: LampTasks } {
  const { status, phase } = project.flow.effective;
  return {
    run: status === "RUNNING" ? "RUNNING" : status === "PAUSED" ? "PAUSED" : "none",
    fsm: status === "ESCALATED" ? "ESCALATION" : "ok",
    tasks: { escalated: false, retrying: phase === "HEALING", reviewEscalated: false },
  };
}

// ── Token 速率與預算（FR-R2P-22；AC-R2P-22-3）───────────────────────────────────────────

/** 速率視窗：近 5 分鐘（增量除以 5 即 tokens／分）。 */
export const TOKEN_RATE_WINDOW_MS = 5 * 60 * 1000;
const TOKEN_RATE_WINDOW_MINUTES = 5;

/** 系統參數 `execution.tokenBudgetWarningThreshold` 的初值（V2__seed_system_configs.sql）；參數缺席或不合法時採用。 */
export const DEFAULT_BUDGET_WARN_AT = 0.8;

type RunSample = { stageRunId: string; at: number; tokens: number };

/** `research.run` 事件的取樣：`payload.tokensUsed`（該 stage run 的累計值）、`payload.stageRunId`；缺欄或時間解不出的事件不入樣。 */
function runSamples(events: ReadonlyArray<Pick<ResearchEvent, "eventType" | "occurredAt" | "payload">>): RunSample[] {
  const out: RunSample[] = [];
  for (const event of events) {
    if (event.eventType !== "research.run") continue;
    const { stageRunId, tokensUsed } = event.payload;
    const at = Date.parse(event.occurredAt);
    if (typeof stageRunId !== "string" || stageRunId === "" || typeof tokensUsed !== "number" || !Number.isFinite(tokensUsed) || tokensUsed < 0 || Number.isNaN(at)) continue;
    out.push({ stageRunId, at, tokens: tokensUsed });
  }
  return out;
}

/**
 * 近 5 分鐘的 token 速率（tokens／分）：每個 stage run 取視窗內最後一筆累計值，減去視窗開始前最後一筆（沒有則從 0 起算——run 的計數從 0 開始，
 * 視窗內才出現第一筆事件的 run 就是視窗內才開始的），各 run 的增量加總後除以 5。視窗內沒有任何事件回 null（畫面顯示「—」，不是 0）。
 * 與 `research_stage_runs.tokens_used`（Phase 0）的差分一致，不新增遙測來源。
 */
export function tokenRate(events: ReadonlyArray<Pick<ResearchEvent, "eventType" | "occurredAt" | "payload">>, now: number): number | null {
  const windowStart = now - TOKEN_RATE_WINDOW_MS;
  const samples = runSamples(events).filter((s) => s.at <= now);
  const inWindow = samples.filter((s) => s.at > windowStart);
  if (inWindow.length === 0) return null;
  let total = 0;
  for (const stageRunId of new Set(inWindow.map((s) => s.stageRunId))) {
    const mine = samples.filter((s) => s.stageRunId === stageRunId);
    const latest = mine.filter((s) => s.at > windowStart).reduce((a, s) => (s.at >= a.at ? s : a));
    const before = mine.filter((s) => s.at <= windowStart);
    const baseline = before.length === 0 ? 0 : before.reduce((a, s) => (s.at >= a.at ? s : a)).tokens;
    total += Math.max(0, latest.tokens - baseline);
  }
  return total / TOKEN_RATE_WINDOW_MINUTES;
}

/** 速率的顯示字串：`600 tokens/min`；null 顯示「—」。 */
export function formatTokenRate(rate: number | null): string {
  return rate === null ? "—" : `${Math.round(rate).toLocaleString("en-US")} tokens/min`;
}

/** 這個研究專案至今用掉的 token：各 stage run 的最大累計值加總（只取 `research.run` 事件）。 */
export function tokensUsedTotal(events: ReadonlyArray<Pick<ResearchEvent, "eventType" | "occurredAt" | "payload">>): number {
  const peak = new Map<string, number>();
  for (const s of runSamples(events)) peak.set(s.stageRunId, Math.max(peak.get(s.stageRunId) ?? 0, s.tokens));
  let total = 0;
  for (const tokens of peak.values()) total += tokens;
  return total;
}

/** 預算：該研究專案 run 的 `token_budget`，沒有（或不是正數）就取系統參數 `execution.globalTokenBudget`；兩者都沒有回 null（顯示「—」，不當成 0）。 */
export function resolveBudget(runBudget: number | null | undefined, systemBudget: number | null | undefined): number | null {
  const positive = (n: number | null | undefined): n is number => typeof n === "number" && Number.isFinite(n) && n > 0;
  if (positive(runBudget)) return runBudget;
  return positive(systemBudget) ? systemBudget : null;
}

/** 自「execution」分類的參數取預算與警示閾值（`globalTokenBudget`、`tokenBudgetWarningThreshold`；缺或不合法時預算 null、閾值取初值 0.8）。 */
export function executionBudgetSettings(configs: ReadonlyArray<Pick<Config, "key" | "value">>): { globalTokenBudget: number | null; warnAt: number } {
  const valueOf = (key: string): number => {
    const raw = configs.find((c) => c.key === key)?.value;
    return raw === undefined || raw.trim() === "" ? Number.NaN : Number(raw);
  };
  const budget = valueOf("globalTokenBudget");
  const warn = valueOf("tokenBudgetWarningThreshold");
  return { globalTokenBudget: Number.isFinite(budget) && budget > 0 ? budget : null, warnAt: Number.isFinite(warn) && warn > 0 && warn <= 1 ? warn : DEFAULT_BUDGET_WARN_AT };
}

export type BudgetState = { budget: number | null; ratio: number | null; percent: number | null; level: "unknown" | "ok" | "warn" };

/** 預算進度：用量達預算的 `warnAt` 倍以上為警示（`warn`）；沒有預算為 `unknown`。`percent` 為整數百分比（可超過 100，畫面進度條自行夾到 100）。 */
export function budgetState(used: number, budget: number | null | undefined, warnAt: number): BudgetState {
  if (typeof budget !== "number" || !Number.isFinite(budget) || budget <= 0) return { budget: null, ratio: null, percent: null, level: "unknown" };
  const ratio = used / budget;
  return { budget, ratio, percent: Math.round(ratio * 100), level: ratio >= warnAt - 1e-9 ? "warn" : "ok" };
}

// ── 審查預算（FSM `SCG_VALIDATION` 三次；D-24、D-60）─────────────────────────────────────

/** FSM `RETRY_LIMITS["SCG_VALIDATION"]`（第 3 次 FAIL＝ESCALATION；ADR-XPLAT-017 D6）。審查預算的唯一常數，剩餘預算與畫面說明都取它。 */
export const REVIEW_RETRY_LIMIT = 3;

/** 剩餘預算＝`max(0, 3 − currentCount)`；`currentCount` 超過上限（異常值）仍夾到 0、不為負。 */
export function remainingReviewBudget(currentCount: number): number {
  return Math.max(0, REVIEW_RETRY_LIMIT - currentCount);
}

/** 審查預算的已用次數：只取 FSM 視圖的 `retryHistory.gates.SCG_VALIDATION.currentCount`（缺席當 0；不取輪列的 `fsmRetryCount`）。 */
export function reviewRetryCount(fsm: Pick<ResearchFsmView, "retryHistory"> | null | undefined): number {
  return fsm?.retryHistory?.gates?.SCG_VALIDATION?.currentCount ?? 0;
}

// ── Gate 0 等待提醒（D-48(3)；AC-R2P-09-10）──────────────────────────────────────────

/** 等待滿這麼多小時顯示提醒橫幅（只顯示；不轉 REMINDER、不自動核准、不自動升級）。 */
export const GATE0_WAIT_BANNER_HOURS = 72;

/**
 * 等待的起點＝最近一個 `fsmGateResult` 為 PASS 的審查輪的 `finishedAt`（POST_HUMAN 通過輪的 `fsmGateResult` 為 null，不作起點）；沒有回 null。
 * 「最近」以 `roundNo` 最大者為準。
 */
export function gate0WaitStart(rounds: ReadonlyArray<Pick<ResearchReviewRound, "roundNo" | "fsmGateResult" | "finishedAt">>): string | null {
  const passed = rounds.filter((r) => r.fsmGateResult === "PASS");
  if (passed.length === 0) return null;
  return passed.reduce((a, r) => (r.roundNo >= a.roundNo ? r : a)).finishedAt;
}

/** 已等待的整點小時數（向下取整；入參為 `finishedAt` 與 now）。起點解不出回 null；時鐘偏差造成的負值夾到 0。 */
export function gateWaitedHours(finishedAt: string, now: number): number | null {
  const start = Date.parse(finishedAt);
  if (Number.isNaN(start)) return null;
  return Math.max(0, Math.floor((now - start) / 3_600_000));
}

/** 工作室的等待資訊：FSM 現態不是 HUMAN_PENDING 或沒有起點時不顯示（回 null）。 */
export function gate0WaitView(
  fsmState: string | null | undefined,
  rounds: ReadonlyArray<Pick<ResearchReviewRound, "roundNo" | "fsmGateResult" | "finishedAt">>,
  now: number,
): { hours: number; overdue: boolean } | null {
  if (fsmState !== "HUMAN_PENDING") return null;
  const start = gate0WaitStart(rounds);
  if (start === null) return null;
  const hours = gateWaitedHours(start, now);
  return hours === null ? null : { hours, overdue: hours >= GATE0_WAIT_BANNER_HOURS };
}

// ── 四方雷達（FR-R2P-09）────────────────────────────────────────────────────────────

/** 雷達四軸的順序與中文軸名（PRD 線框：架構／商業／QA／資安；PRODUCT 的 agent 是 pm-po）。 */
export const RADAR_AXES: ReadonlyArray<{ dimension: "ARCHITECTURE" | "PRODUCT" | "QA" | "SECURITY"; label: string }> = [
  { dimension: "ARCHITECTURE", label: "架構" },
  { dimension: "PRODUCT", label: "商業" },
  { dimension: "QA", label: "QA" },
  { dimension: "SECURITY", label: "資安" },
];

/** 一輪的雷達資料：固定四軸、依序；該維度沒有分數回 null（不補 0）。 */
export function scoreRadar(round: Pick<ResearchReviewRound, "scores">): Array<{ dimension: string; label: string; score: number | null }> {
  return RADAR_AXES.map(({ dimension, label }) => ({ dimension, label, score: round.scores.find((s) => s.dimension === dimension)?.score ?? null }));
}

// ── 行級 diff（FR-R2P-09；AC-R2P-09-2、09-8）──────────────────────────────────────────

export type DiffLine = {
  kind: "add" | "remove" | "same";
  text: string;
  /** 在 A 版的行號（1 起算）；新增行為 null */
  aLine: number | null;
  /** 在 B 版的行號（1 起算）；刪除行為 null */
  bLine: number | null;
};

/** 最短編輯距離的搜尋上限：超過就退回「整段刪除加整段新增」（仍是合法編輯序列，只是不最小），避免兩份完全不同的大文件耗盡記憶體。 */
export const DIFF_MAX_EDITS = 2000;

/** 換行正規化後逐行切開（CRLF 與 LF 等價）；空字串沒有任何行；結尾的換行不多算一個空行。 */
export function splitLines(text: string): string[] {
  if (text === "") return [];
  const lines = text.split(/\r?\n/);
  if (lines[lines.length - 1] === "") lines.pop();
  return lines;
}

type EditOp = { kind: "add" | "remove" | "same"; a: number | null; b: number | null };

/** Myers 最短編輯序列（O(ND)）；最短編輯距離超過 `maxEdits` 回 null。回傳元素是 a 與 b 的「中段」索引（0 起算）。 */
function myersOps(a: readonly string[], b: readonly string[], maxEdits: number): EditOp[] | null {
  const n = a.length;
  const m = b.length;
  const max = Math.min(n + m, maxEdits);
  const offset = max + 1;
  const v = new Int32Array(2 * max + 3);
  const trace: Int32Array[] = [];
  let reached = false;
  for (let d = 0; d <= max && !reached; d += 1) {
    trace.push(v.slice(offset - d - 1, offset + d + 2));
    for (let k = -d; k <= d; k += 2) {
      let x = k === -d || (k !== d && v[offset + k - 1] < v[offset + k + 1]) ? v[offset + k + 1] : v[offset + k - 1] + 1;
      let y = x - k;
      while (x < n && y < m && a[x] === b[y]) {
        x += 1;
        y += 1;
      }
      v[offset + k] = x;
      if (x >= n && y >= m) {
        reached = true;
        break;
      }
    }
  }
  if (!reached) return null;
  const ops: EditOp[] = [];
  let x = n;
  let y = m;
  for (let d = trace.length - 1; d >= 0; d -= 1) {
    const snapshot = trace[d];
    const at = (k: number): number => snapshot[k + d + 1];
    const k = x - y;
    const prevK = k === -d || (k !== d && at(k - 1) < at(k + 1)) ? k + 1 : k - 1;
    const prevX = at(prevK);
    const prevY = prevX - prevK;
    while (x > prevX && y > prevY) {
      x -= 1;
      y -= 1;
      ops.push({ kind: "same", a: x, b: y });
    }
    if (d > 0) ops.push(x === prevX ? { kind: "add", a: null, b: prevY } : { kind: "remove", a: prevX, b: null });
    x = prevX;
    y = prevY;
  }
  return ops.reverse();
}

/** 同一段連續的變更內，刪除排在新增之前（各自保持原順序）。 */
function removesBeforeAdds(ops: readonly EditOp[]): EditOp[] {
  const out: EditOp[] = [];
  let i = 0;
  while (i < ops.length) {
    if (ops[i].kind === "same") {
      out.push(ops[i]);
      i += 1;
      continue;
    }
    let j = i;
    while (j < ops.length && ops[j].kind !== "same") j += 1;
    const block = ops.slice(i, j);
    out.push(...block.filter((op) => op.kind === "remove"), ...block.filter((op) => op.kind === "add"));
    i = j;
  }
  return out;
}

/** a 對 b 的編輯序列：先削掉共同的開頭與結尾（常見的「只改幾處」幾乎不用搜尋），中段交給 Myers，超過上限退回整段刪加。 */
function editScript(a: readonly string[], b: readonly string[]): EditOp[] {
  let head = 0;
  while (head < a.length && head < b.length && a[head] === b[head]) head += 1;
  let tail = 0;
  while (tail < a.length - head && tail < b.length - head && a[a.length - 1 - tail] === b[b.length - 1 - tail]) tail += 1;
  const midA = a.slice(head, a.length - tail);
  const midB = b.slice(head, b.length - tail);
  const shift = (op: EditOp): EditOp => ({ kind: op.kind, a: op.a === null ? null : op.a + head, b: op.b === null ? null : op.b + head });
  const fallback = (): EditOp[] => [...midA.map((_, i): EditOp => ({ kind: "remove", a: i, b: null })), ...midB.map((_, i): EditOp => ({ kind: "add", a: null, b: i }))];
  const middle = midA.length === 0 || midB.length === 0 ? fallback() : (myersOps(midA, midB, DIFF_MAX_EDITS) ?? fallback());
  return [
    ...Array.from({ length: head }, (_, i): EditOp => ({ kind: "same", a: i, b: i })),
    ...removesBeforeAdds(middle).map(shift),
    ...Array.from({ length: tail }, (_, i): EditOp => ({ kind: "same", a: a.length - tail + i, b: b.length - tail + i })),
  ];
}

/** 逐行比較兩份行陣列：先比內容、內容相同再比行數（短者小）。 */
function compareLineArrays(a: readonly string[], b: readonly string[]): number {
  const common = Math.min(a.length, b.length);
  for (let i = 0; i < common; i += 1) if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
  return a.length === b.length ? 0 : a.length < b.length ? -1 : 1;
}

/**
 * 行級 diff（無 DOM、確定性）：回 A→B 的逐行結果，每行標 `same`／`remove`／`add` 與兩邊行號；同一段變更內刪除在前、新增在後。
 * **A→B 與 B→A 互為反向**：兩個方向共用同一份編輯序列（內容較小者為前，另一個方向把 add 與 remove 對調），所以 A→B 的新增行恰是 B→A 的刪除行
 * （相同行重複出現時逐「索引」也成立，不只是文字集合）。空白差異算差異（行內容逐字比對）；空輸入沒有任何行。
 */
export function diffLines(a: string, b: string): DiffLine[] {
  const linesA = splitLines(a);
  const linesB = splitLines(b);
  const flipped = compareLineArrays(linesA, linesB) > 0;
  const script = flipped ? editScript(linesB, linesA) : editScript(linesA, linesB);
  const ops = flipped ? removesBeforeAdds(script.map((op): EditOp => ({ kind: op.kind === "add" ? "remove" : op.kind === "remove" ? "add" : "same", a: op.b, b: op.a }))) : script;
  return ops.map((op) => ({
    kind: op.kind,
    text: op.a !== null ? linesA[op.a] : linesB[op.b as number],
    aLine: op.a === null ? null : op.a + 1,
    bLine: op.b === null ? null : op.b + 1,
  }));
}

// ── 對帳（FR-R2P-23；AC-R2P-23-1、23-2）──────────────────────────────────────────────

/** 對帳六項檢查的中文名稱（契約 `ReconcileResult.checks[].name`；⚖16 固定六項）。 */
export const RECONCILE_CHECK_LABEL: Readonly<Record<string, string>> = {
  fsm_flow_mapping: "狀態機與流程游標的對映",
  prd_sha256: "PRD 檔案",
  review_card: "審查卡",
  evidence_matrix: "證據矩陣",
  task_decomposition: "任務拆解",
  route_decision: "分流決定",
};

export type ReconcileDriftView = {
  /** 檔案漂移（`fsm_flow_mapping` 以外的 drift）：檔名與雙方的 sha256 */
  files: Array<{ check: string; label: string; path: string; expectedSha256?: string; actualSha256?: string }>;
  /** 狀態機與流程游標的對映不合（顯示警示，不是檔案） */
  fsmMapping: boolean;
  /** 量不到的檢查（`NOT_EVALUABLE`）：不判成一致也不判成漂移，另行說明 */
  notEvaluable: string[];
};

/**
 * 對帳結果轉成畫面要的三塊：檔案漂移（以資料庫為準，只顯示、不修）、狀態機對映警示、量不到的檢查。
 * 全部 ok 時三塊皆空；漂移只來自 `status === "drift"` 的檢查，量不到的檢查不算漂移（⚖16：量不到不得 false-green，也不得 false-red）。
 */
export function reconcileDriftView(result: ResearchReconcileResult): ReconcileDriftView {
  const view: ReconcileDriftView = { files: [], fsmMapping: false, notEvaluable: [] };
  for (const check of result.checks) {
    const label = RECONCILE_CHECK_LABEL[check.name] ?? check.name;
    if (check.status === "NOT_EVALUABLE") view.notEvaluable.push(label);
    if (check.status !== "drift") continue;
    if (check.name === "fsm_flow_mapping") view.fsmMapping = true;
    else for (const d of check.drift ?? []) view.files.push({ check: check.name, label, path: d.path, expectedSha256: d.expectedSha256, actualSha256: d.actualSha256 });
  }
  return view;
}

// ── 清單頁（FR-R2P-01；頁面 0）──────────────────────────────────────────────────────

export type ProjectBadgeId = "active" | "frozen" | "delivered" | "scr" | "init_failed" | "archived";

/** 狀態徽章（PRD 頁面 0：進行中／Gate 0 已核准／已交付／SCR 進行中／初始化失敗／已封存）。 */
export const PROJECT_BADGE_LABEL: Readonly<Record<ProjectBadgeId, string>> = {
  active: "進行中",
  frozen: "Gate 0 已核准",
  delivered: "已交付",
  scr: "SCR 進行中",
  init_failed: "初始化失敗",
  archived: "已封存",
};

/** 帶時區的時間顯示（本機時區；例「2026-11-02 10:00 UTC+08:00」）；解不出回「—」。清單與工作區的更新時間一律用它，不顯示 naive 時間。 */
export function formatInstant(iso: string | null | undefined): string {
  const d = iso ? new Date(iso) : null;
  if (d === null || Number.isNaN(d.getTime())) return "—";
  const pad = (n: number): string => String(n).padStart(2, "0");
  const offset = -d.getTimezoneOffset();
  const abs = Math.abs(offset);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())} UTC${offset >= 0 ? "+" : "-"}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
}

/** 初始化失敗（`flow_status=FAILED` 且 `flow_detail` 以 `init_failed:` 起頭）：只有這種狀態可「重試初始化」（D-65(4)）。 */
export function isInitFailed(project: Pick<ResearchProjectSummary, "flowStatus" | "flowDetail">): boolean {
  return project.flowStatus === "FAILED" && project.flowDetail.startsWith("init_failed:");
}

/**
 * 清單列的狀態徽章：已封存＞初始化失敗＞SCR 進行中＞已交付＞Gate 0 已核准（游標已越過規格工作室＝Gate 0 已核准，因為游標是在核准成功時才進到 route）＞進行中。
 */
export function projectBadge(project: Pick<ResearchProjectSummary, "archivedAt" | "flowStatus" | "flowDetail" | "flowPhase" | "flowStep">): ProjectBadgeId {
  if (project.archivedAt !== null) return "archived";
  if (isInitFailed(project)) return "init_failed";
  if (project.flowPhase === "SCR_OPEN") return "scr";
  if (project.flowPhase === "DELIVERED" || (project.flowStep === "deliver" && project.flowStatus === "COMPLETED")) return "delivered";
  return stepIndex(project.flowStep) >= stepIndex("route") ? "frozen" : "active";
}

/** 主連結文字：「繼續（第 k 步：名稱）」。 */
export function continueLabel(step: ResearchFlowStepId): string {
  return `繼續（第 ${stepNumber(step)} 步：${FLOW_STEP_LABEL[step]}）`;
}

export type ProjectFilter = { q: string; status: "all" | ProjectBadgeId; step: "all" | ResearchFlowStepId };

/** 清單篩選（全在已載入的清單上做）：「全部」不含已封存；搜尋比對 `RP-NNNN`、名稱與代號（不分大小寫）。 */
export function filterProjects<T extends Pick<ResearchProjectSummary, "rpNo" | "title" | "slug" | "archivedAt" | "flowStatus" | "flowDetail" | "flowPhase" | "flowStep">>(
  projects: readonly T[],
  filter: ProjectFilter,
): T[] {
  const needle = filter.q.trim().toLowerCase();
  return projects.filter((p) => {
    const badge = projectBadge(p);
    if (filter.status === "all" ? badge === "archived" : badge !== filter.status) return false;
    if (filter.step !== "all" && p.flowStep !== filter.step) return false;
    return needle === "" || [p.rpNo, p.title, p.slug].some((text) => text.toLowerCase().includes(needle));
  });
}

// ── 新建研究專案（FR-R2P-03；PRD §5.1.2；契約 §1.2）────────────────────────────────────

export const TOPIC_MAX = 500;
export const TITLE_MAX = 200;
/** 檢索範圍清單（`inScope`／`outOfScope`）每項的字數上限（契約 §1.2）。 */
export const SCOPE_ITEM_MAX = 200;
/** 清單的「命題摘要」（`title`）取命題第一行的前這麼多字，超過加「…」。 */
export const TITLE_SUMMARY_LENGTH = 60;
export const SLUG_MAX = 30;
/** `^[a-z0-9][a-z0-9-]{0,29}$`（DB CHECK 與 FSM 鍵 `research-<slug>` 的長度上界）。 */
export const SLUG_PATTERN = /^[a-z0-9][a-z0-9-]{0,29}$/;

export const DEPTH_OPTIONS: ReadonlyArray<{ id: ResearchDepthLevel; label: string; hint: string }> = [
  { id: "QUICK", label: "快速", hint: "每層取少量來源，適合先摸個底" },
  { id: "STANDARD", label: "標準", hint: "預設值，來源數與耗時適中" },
  { id: "DEEP", label: "深入", hint: "每層取較多來源，耗時與 token 最多" },
];

/** 來源層的四個勾選（`layers.*`）；`industry` 是 Web 層，Web 層未啟用（`capabilities.webLayerEnabled` 為假）時停用。 */
export const LAYER_OPTIONS: ReadonlyArray<{ id: "academic" | "industry" | "oss" | "community"; label: string }> = [
  { id: "academic", label: "論文" },
  { id: "industry", label: "官方文獻與業界" },
  { id: "oss", label: "開源 Repo" },
  { id: "community", label: "社群" },
];

/** 適用性軸的預設全六軸（框架模板的軸登錄表；`issue_scope.applicability_axes` 只能取其子集）。 */
export const DEFAULT_APPLICABILITY_AXES: readonly string[] = ["技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本"];
export const DEFAULT_RECENCY_YEARS = 3;

/** 沒有任何 ASCII 英數的命題（例如純中文）所用的代號前綴（⚖22）。 */
export const FALLBACK_SLUG_PREFIX = "rp-";

/**
 * 由命題自動產生代號：ASCII 英數轉小寫、其餘字元（連續者）以一個連字號連接、去頭尾連字號、截至 30 字元（截斷後再去尾端連字號）。
 * 命題沒有任何 ASCII 英數時退回 `rp-` 加四位小寫英數（取命題內容的雜湊——同一個命題恆得同一個代號，輸入時不會閃動；撞號時由後端回 409 `slug_in_use`，使用者改名即可）。
 */
export function slugFromTopic(topic: string): string {
  const base = topic
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, SLUG_MAX)
    .replace(/-+$/g, "");
  if (base !== "") return base;
  let hash = 2166136261;
  for (const ch of topic.trim()) hash = Math.imul(hash ^ (ch.codePointAt(0) ?? 0), 16777619) >>> 0;
  return `${FALLBACK_SLUG_PREFIX}${hash.toString(36).padStart(4, "0").slice(-4)}`;
}

/** 清單的「命題摘要」：命題第一個非空行的前 60 字（超過加「…」）。 */
export function topicSummary(topic: string): string {
  const first = (topic.split(/\r?\n/).find((line) => line.trim() !== "") ?? "").trim();
  const chars = Array.from(first);
  return chars.length > TITLE_SUMMARY_LENGTH ? `${chars.slice(0, TITLE_SUMMARY_LENGTH).join("")}…` : first;
}

/** 新建表單的 zod 驗證（前端只為更早給回饋；後端輸入閘與 Bridge 入口各再擋一次）。 */
export const createResearchSchema = z.object({
  topic: z
    .string()
    .trim()
    .min(1, "命題不能為空")
    .max(TOPIC_MAX, `命題最多 ${TOPIC_MAX} 個字元`)
    .refine((v) => !v.includes("\u0000"), "命題不可含 NUL 字元"),
  slug: z.string().regex(SLUG_PATTERN, "代號須為小寫英數與連字號、1 至 30 字，且以英數開頭"),
  depthLevel: z.enum(["QUICK", "STANDARD", "DEEP"], { error: "請選擇檢索深度" }),
  layers: z.object({ academic: z.boolean(), industry: z.boolean(), oss: z.boolean(), community: z.boolean() }).refine((l) => l.academic || l.industry || l.oss || l.community, "至少要勾選一個來源層"),
});
export type CreateResearchForm = z.infer<typeof createResearchSchema>;

/** 逐欄的第一則錯誤訊息（欄名＝表單欄位：topic、slug、depthLevel、layers）；沒有錯誤回空物件。 */
export function createResearchErrors(form: unknown): Partial<Record<"topic" | "slug" | "depthLevel" | "layers", string>> {
  const result = createResearchSchema.safeParse(form);
  const out: Partial<Record<"topic" | "slug" | "depthLevel" | "layers", string>> = {};
  if (result.success) return out;
  for (const issue of result.error.issues) {
    const key = String(issue.path[0]) as "topic" | "slug" | "depthLevel" | "layers";
    if (out[key] === undefined) out[key] = issue.message;
  }
  return out;
}

/**
 * 表單轉請求本文：`title` 取命題摘要；表單沒有收的範圍欄位用預設——`inScope` 至少一項（框架模板要求），取命題本身（截至每項上限 200 字）；
 * `outOfScope` 與 `techStack` 為空、`recencyYears` 取 3、適用性軸全六軸。欄位名一律 camelCase。
 */
export function toCreateRequest(form: CreateResearchForm): ResearchCreateRequest {
  const topic = form.topic.trim();
  return {
    slug: form.slug,
    title: topicSummary(topic).slice(0, TITLE_MAX),
    topic,
    scope: {
      layers: { ...form.layers },
      techStack: "",
      inScope: [Array.from(topic).slice(0, SCOPE_ITEM_MAX).join("")],
      outOfScope: [],
      recencyYears: DEFAULT_RECENCY_YEARS,
      applicabilityAxes: [...DEFAULT_APPLICABILITY_AXES],
    },
    depthLevel: form.depthLevel,
  };
}

// ── 錯誤原因（契約 §0.2、§1.4；TCS §5.1「錯誤 reason」）────────────────────────────────

/**
 * 研究 reason 的前端常數（P0 的十八個，與契約、PRD §9.3、後端 `ErrorReasons` 的 `RESEARCH_` 常數集合相等；AT-960-5-6 比對三處）。
 * 刻意不放進 lib/api/reasons.ts 的 REASONS：REASONS 與凍結契約附錄 B 雙向鎖（reasons.test.ts），多一個前端常數即紅（⚖12）。
 */
export const RESEARCH_REASONS = {
  WRITE_DISABLED: "research_write_disabled",
  WRITE_FORBIDDEN: "research_write_forbidden",
  REQUIRES_DB: "research_requires_db",
  DB_BLOCKED: "db_blocked",
  NOT_FOUND: "research_not_found",
  SLUG_IN_USE: "slug_in_use",
  STAGE_CONFLICT: "stage_conflict",
  PRD_VERSION_CONFLICT: "prd_version_conflict",
  REVIEW_NOT_PASSED: "review_not_passed",
  SPEC_DIGEST_CHANGED: "spec_digest_changed",
  FSM_STATE_CONFLICT: "fsm_state_conflict",
  ESCALATED: "escalated",
  SPEC_FROZEN: "spec_frozen",
  LAYER_UNAVAILABLE: "layer_unavailable",
  SANITIZATION_FAILED: "sanitization_failed",
  TERMS_ACK_REQUIRED: "terms_ack_required",
  BRIDGE_UNREACHABLE: "bridge_unreachable",
  BRIDGE_TIMEOUT: "bridge_timeout",
} as const;

/** 唯讀角色的停用說明（沿 TCS-ExecMonitorEntry W-E1 先例）：所有寫入類控件停用時 `title` 一律是它。 */
export const READONLY_TITLE = "權限不足（唯讀角色）";

const REASON_TEXT: Readonly<Record<string, string>> = {
  [RESEARCH_REASONS.WRITE_DISABLED]: "研究寫入面未啟用：Console 或 Bridge 沒有設定研究寫入權杖，請洽管理員",
  [RESEARCH_REASONS.WRITE_FORBIDDEN]: "權限不足：這個動作不在您的角色範圍內",
  [RESEARCH_REASONS.REQUIRES_DB]: "研究功能需要 Bridge 連上資料庫，目前沒有連線，所以沒有任何檔案或資料被寫入",
  [RESEARCH_REASONS.DB_BLOCKED]: "資料庫暫時不可用，已暫停寫入；恢復後會自動補寫",
  [RESEARCH_REASONS.NOT_FOUND]: "找不到這個研究專案（可能已封存或不存在）",
  [RESEARCH_REASONS.SLUG_IN_USE]: "這個代號已被未封存的研究專案使用，請換一個",
  [RESEARCH_REASONS.STAGE_CONFLICT]: "目前狀態不允許這個動作（可能已有進行中的階段），請重新整理後再試",
  [RESEARCH_REASONS.PRD_VERSION_CONFLICT]: "PRD 已有更新的版本，請重新整理後再存",
  [RESEARCH_REASONS.REVIEW_NOT_PASSED]: "最新版本沒有通過的審查輪，不能核准",
  [RESEARCH_REASONS.SPEC_DIGEST_CHANGED]: "要凍結的檔案在確認之後被改過，請重新整理後再確認",
  [RESEARCH_REASONS.FSM_STATE_CONFLICT]: "狀態機目前的狀態不允許這個動作，請重新整理後再試",
  [RESEARCH_REASONS.ESCALATED]: "審查已升級給人工，請先處理升級",
  [RESEARCH_REASONS.SPEC_FROZEN]: "規格已凍結，不能再修改",
  [RESEARCH_REASONS.LAYER_UNAVAILABLE]: "「官方文獻與業界」層目前未啟用，請取消勾選",
  [RESEARCH_REASONS.SANITIZATION_FAILED]: "路徑或名稱沒有通過安全檢查",
  [RESEARCH_REASONS.TERMS_ACK_REQUIRED]: "這個來源需要先勾選已接受服務條款",
  [RESEARCH_REASONS.BRIDGE_UNREACHABLE]: "連不上 Engine Bridge，請確認它是否在線",
  [RESEARCH_REASONS.BRIDGE_TIMEOUT]: "Engine Bridge 回應逾時，請稍後再試",
};

/** 研究端點錯誤的白話原因（依 `reason`；沒有對映時退回通用訊息）。 */
export function researchErrorText(error: unknown): string {
  if (error instanceof ApiError && error.reason !== undefined && REASON_TEXT[error.reason] !== undefined) return REASON_TEXT[error.reason];
  return describeError(error);
}
