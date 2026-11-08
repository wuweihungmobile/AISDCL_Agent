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
  ResearchAllowlistRequest,
  ResearchCapabilities,
  ResearchCreateRequest,
  ResearchDecomposition,
  ResearchDepthLevel,
  ResearchDerivedFlowPhase,
  ResearchEvent,
  ResearchEvidenceItem,
  ResearchEvidenceMatrix,
  ResearchFlowPhase,
  ResearchFlowStatus,
  ResearchFlowStepId,
  ResearchFlowStepState,
  ResearchGateName,
  ResearchGateResult,
  ResearchKanban,
  ResearchScrKind,
  ResearchFsmView,
  ResearchPlacementTarget,
  ResearchProjectDetail,
  ResearchProjectSummary,
  ResearchReconcileResult,
  ResearchReviewRound,
  ResearchRouteAction,
  ResearchRouteConfirmRequest,
  ResearchRouteDecision,
  ResearchRouteRequest,
  ResearchRouteTrack,
  ResearchRouteVisibility,
  ResearchSource,
  ResearchSourceLayer,
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

/**
 * `flow_phase` 十三個 DB 值加六個衍生相態（`FLOW_PHASE_DERIVED`；衍生值不落 DB）。P1 補 `BUILD_READY`「可開始建置」並把 `SCR_OPEN` 定為「SCR 進行中」（D-114）。
 * 衍生相態 `PAUSED`（「已暫停」）與衍生狀態 `PAUSED` 同名同義：詞彙只登記一次在 `FLOW_STATUS_LABEL`（兩表鍵不相交、`researchFlow` 狀態表的鍵集合不重複），
 * `flowPhaseLabel("PAUSED")` 退到狀態表取同一個標籤。
 */
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
  SCR_OPEN: "SCR 進行中",
  BUILD_READY: "可開始建置",
  BUILDING: "建置中",
  HEALING: "自癒中",
  AWAITING_HUMAN: "等待人工審核",
  RELEASE_PENDING: "待發布",
  DELIVERED: "已交付",
};

/** 衍生相態（由 `ResearchFlowPolicy` 自 FSM 與 `execution_runs` 即時推算，不落 DB）。 */
export const FLOW_PHASE_DERIVED: readonly ResearchDerivedFlowPhase[] = ["BUILDING", "HEALING", "AWAITING_HUMAN", "RELEASE_PENDING", "DELIVERED", "BUILD_READY"];

/** 兩張詞彙表合起來的鍵（`researchFlow` 狀態說明表的鍵集合；status 與 phase 的值域不相交）。 */
export const FLOW_VOCABULARY_KEYS: readonly string[] = [...Object.keys(FLOW_STATUS_LABEL), ...Object.keys(FLOW_PHASE_LABEL)];

/** 未登記的值顯示原值、不丟例外（後端日後新增值時畫面不崩潰）。 */
export function flowStatusLabel(status: string): string {
  return (FLOW_STATUS_LABEL as Readonly<Record<string, string | undefined>>)[status] ?? status;
}

export function flowPhaseLabel(phase: string): string {
  return (FLOW_PHASE_LABEL as Readonly<Record<string, string | undefined>>)[phase] ?? (phase === "PAUSED" ? FLOW_STATUS_LABEL.PAUSED : phase);
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
  /** P2 第七項（FR-R2P-23、AC-23-4）：交付快照 `traceability_matrix.json` 的 sha256 對帳 */
  delivery: "交付",
};

export type ReconcileDriftView = {
  /** 檔案漂移（`fsm_flow_mapping` 以外的 drift）：檔名與雙方的 sha256 */
  files: Array<{ check: string; label: string; path: string; expectedSha256?: string; actualSha256?: string }>;
  /** 狀態機與流程游標的對映不合（顯示警示，不是檔案） */
  fsmMapping: boolean;
  /** 量不到的檢查（`NOT_EVALUABLE`）：不判成一致也不判成漂移，另行說明 */
  notEvaluable: string[];
  /** 有任一檔案漂移或狀態機對映不合（`pending_correction` 不算，AT-961-20-E-2） */
  hasDrift: boolean;
  /** 有檢查為第三態 `pending_correction`（待校正：不是漂移，按「重新對帳」校正；D-121、D-125） */
  pendingCorrection: boolean;
};

/**
 * 對帳結果轉成畫面要的幾塊：檔案漂移（以資料庫為準，只顯示、不修）、狀態機對映警示、量不到的檢查、待校正。
 * 全部 ok 時皆空；漂移只來自 `status === "drift"` 的檢查，量不到的檢查不算漂移（⚖16：量不到不得 false-green，也不得 false-red）；
 * 第三態 `pending_correction`（P1 起 `fsm_flow_mapping` 可回，D-121）既不算漂移也不算一致：只標 `pendingCorrection`。
 * `status` 的型別尚未含第三態（FE-D1 已定稿的 `ResearchReconcileCheck`），所以以字串比對。
 */
export function reconcileDriftView(result: ResearchReconcileResult): ReconcileDriftView {
  const view: ReconcileDriftView = { files: [], fsmMapping: false, notEvaluable: [], hasDrift: false, pendingCorrection: false };
  for (const check of result.checks) {
    const label = RECONCILE_CHECK_LABEL[check.name] ?? check.name;
    const status: string = check.status;
    if (status === "NOT_EVALUABLE") view.notEvaluable.push(label);
    if (status === "pending_correction") view.pendingCorrection = true;
    if (status !== "drift") continue;
    if (check.name === "fsm_flow_mapping") view.fsmMapping = true;
    else for (const d of check.drift ?? []) view.files.push({ check: check.name, label, path: d.path, expectedSha256: d.expectedSha256, actualSha256: d.actualSha256 });
  }
  view.hasDrift = view.files.length > 0 || view.fsmMapping;
  return view;
}

// ── 清單頁（FR-R2P-01；頁面 0）──────────────────────────────────────────────────────

export type ProjectBadgeId = "active" | "frozen" | "delivered" | "scr" | "failed" | "init_failed" | "archived";

/**
 * 狀態徽章（PRD 頁面 0：進行中／Gate 0 已核准／已交付／SCR 進行中／初始化失敗／已封存；INT-14⑥ 加「失敗」）。
 * 「失敗」＝階段執行失敗或被取消（D-77：兩者游標一律 `flow_status=FAILED`，原因放 `flow_detail`）；初始化失敗另有自己的徽章與重試路徑。
 */
export const PROJECT_BADGE_LABEL: Readonly<Record<ProjectBadgeId, string>> = {
  active: "進行中",
  frozen: "Gate 0 已核准",
  delivered: "已交付",
  scr: "SCR 進行中",
  failed: "失敗",
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
 * 階段失敗或被取消（不含初始化失敗）：游標 `flow_status` 為 `FAILED`（D-77：失敗與取消一律 FAILED，取消的 `flow_detail` 為 `cancelled`）；
 * 舊版 Bridge 留在資料庫裡的 `CANCELLED` 游標同樣不是「進行中」，一併算（資料庫的 `flow_status` 列舉仍含它）。
 */
export function isStageFailed(project: Pick<ResearchProjectSummary, "flowStatus" | "flowDetail">): boolean {
  return (project.flowStatus === "FAILED" && !isInitFailed(project)) || project.flowStatus === "CANCELLED";
}

/**
 * 清單列的狀態徽章：已封存＞初始化失敗＞失敗（階段失敗或取消）＞SCR 進行中＞已交付＞Gate 0 已核准（游標已越過規格工作室＝Gate 0 已核准，因為游標是在核准成功時才進到 route）＞進行中。
 * 失敗與取消不得標成「進行中」（INT-14⑥：使用者會以為引擎還在跑）。
 */
export function projectBadge(project: Pick<ResearchProjectSummary, "archivedAt" | "flowStatus" | "flowDetail" | "flowPhase" | "flowStep">): ProjectBadgeId {
  if (project.archivedAt !== null) return "archived";
  if (isInitFailed(project)) return "init_failed";
  if (isStageFailed(project)) return "failed";
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
 * 研究 reason 的前端常數（三十七個＝P0 二十二＋P1 十三＋P2 二；與後端 `ErrorReasons` 的 `RESEARCH_` 常數集合、契約 §0.2 勘誤後的清單相等；AT-960-5-6 比對三處）：
 * P0 契約原列十八個中的十七個，加 Bridge 專屬的五個（`allowlist_exists`、`init_failed`、`not_implemented`、`digest_mismatch`、`missing_digests`；F-09、INT-13）。
 * 契約原列的 `spec_digest_changed`（409）已被 D-72 的 `digest_mismatch`／`missing_digests`（422）取代、Bridge 對研究端點不再回它，所以不再是前端常數。
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
  FSM_STATE_CONFLICT: "fsm_state_conflict",
  ESCALATED: "escalated",
  SPEC_FROZEN: "spec_frozen",
  LAYER_UNAVAILABLE: "layer_unavailable",
  SANITIZATION_FAILED: "sanitization_failed",
  TERMS_ACK_REQUIRED: "terms_ack_required",
  BRIDGE_UNREACHABLE: "bridge_unreachable",
  BRIDGE_TIMEOUT: "bridge_timeout",
  ALLOWLIST_EXISTS: "allowlist_exists",
  INIT_FAILED: "init_failed",
  NOT_IMPLEMENTED: "not_implemented",
  DIGEST_MISMATCH: "digest_mismatch",
  MISSING_DIGESTS: "missing_digests",
  // P1 九個（IFACE §2；D-111：`not_implemented` 保留供 P2 骨架）
  ROUTE_UNSUPPORTED_IN_DEPLOYMENT: "route_unsupported_in_deployment",
  ROUTE_CONFLICT: "route_conflict",
  BRANCH_EXISTS: "branch_exists",
  TARGET_NOT_EMPTY: "target_not_empty",
  PUBLIC_CONFIRMATION_REQUIRED: "public_confirmation_required",
  ROUTE_STEP_FAILED: "route_step_failed",
  SCR_OPEN: "scr_open",
  SCR_LIMIT: "scr_limit",
  DECOMPOSITION_STALE: "decomposition_stale",
  // P0 二審尾巴 R-2 的四個（⚖P1-25；`invalid_request` 改 RESEARCH_ 前綴常數）
  COMPILE_FAILED: "compile_failed",
  SDD_CLI_FAILED: "sdd_cli_failed",
  FSM_STATE_UNREADABLE: "fsm_state_unreadable",
  INVALID_REQUEST: "invalid_request",
  // P2 兩個（D-138 Q-14：四方鎖 37；字面逐字等於後端 `ErrorReasons`）
  TAG_EXISTS: "tag_exists",
  DELIVERY_STEP_FAILED: "delivery_step_failed",
} as const;

/** 唯讀角色的停用說明（沿 TCS-ExecMonitorEntry W-E1 先例）：所有寫入類控件停用時 `title` 一律是它。 */
export const READONLY_TITLE = "權限不足（唯讀角色）";

/** 研究 reason 的白話文案（單一登記處；元件一律取這裡，不內嵌第二份）。 */
export const RESEARCH_REASON_TEXT: Readonly<Record<string, string>> = {
  [RESEARCH_REASONS.WRITE_DISABLED]: "研究寫入面未啟用：Console 或 Bridge 沒有設定研究寫入權杖，請洽管理員",
  [RESEARCH_REASONS.WRITE_FORBIDDEN]: "權限不足：這個動作不在您的角色範圍內",
  [RESEARCH_REASONS.REQUIRES_DB]: "研究功能需要 Bridge 連上資料庫，目前沒有連線，所以沒有任何檔案或資料被寫入",
  [RESEARCH_REASONS.DB_BLOCKED]: "資料庫暫時不可用，已暫停寫入；恢復後會自動補寫",
  [RESEARCH_REASONS.NOT_FOUND]: "找不到這個研究專案（可能已封存或不存在）",
  [RESEARCH_REASONS.SLUG_IN_USE]: "這個代號已被未封存的研究專案使用，請換一個",
  [RESEARCH_REASONS.STAGE_CONFLICT]: "目前狀態不允許這個動作（可能已有進行中的階段），請重新整理後再試",
  [RESEARCH_REASONS.PRD_VERSION_CONFLICT]: "PRD 已有更新的版本，請重新整理後再存",
  [RESEARCH_REASONS.REVIEW_NOT_PASSED]: "最新版本沒有通過的審查輪，不能核准",
  [RESEARCH_REASONS.FSM_STATE_CONFLICT]: "狀態機目前的狀態不允許這個動作，請重新整理後再試",
  [RESEARCH_REASONS.ESCALATED]: "審查已升級給人工，請先處理升級",
  [RESEARCH_REASONS.SPEC_FROZEN]: "規格已凍結，不能再修改",
  [RESEARCH_REASONS.LAYER_UNAVAILABLE]: "「官方文獻與業界」層目前未啟用，請取消勾選",
  [RESEARCH_REASONS.SANITIZATION_FAILED]: "路徑或名稱沒有通過安全檢查",
  [RESEARCH_REASONS.TERMS_ACK_REQUIRED]: "這個來源需要先勾選已接受服務條款",
  [RESEARCH_REASONS.BRIDGE_UNREACHABLE]: "連不上 Engine Bridge，請確認它是否在線",
  [RESEARCH_REASONS.BRIDGE_TIMEOUT]: "Engine Bridge 回應逾時，請稍後再試",
  [RESEARCH_REASONS.ALLOWLIST_EXISTS]: "這個網域在同一種清單中已有條目，請直接啟用或停用既有的條目",
  [RESEARCH_REASONS.INIT_FAILED]: "專案初始化沒有完成（工作區、檔案或狀態機其中一步失敗），專案已標為初始化失敗，請按「重試初始化」補建",
  [RESEARCH_REASONS.NOT_IMPLEMENTED]: "這個功能尚未開放（後續階段提供）",
  [RESEARCH_REASONS.DIGEST_MISMATCH]: "核准時的摘要與現檔不符，請重新整理後再核准",
  [RESEARCH_REASONS.MISSING_DIGESTS]: "核准請求沒有附上任何檔案摘要，無法確認您看到的內容；請重新整理後再核准",
  [RESEARCH_REASONS.ROUTE_UNSUPPORTED_IN_DEPLOYMENT]: "這個部署環境不支援分流，缺少必要的工具或權限；請改用本機模式，或看預演列出的缺項",
  [RESEARCH_REASONS.ROUTE_CONFLICT]: "這個研究專案已有進行中或已完成的分流，請重新整理後再看",
  [RESEARCH_REASONS.BRANCH_EXISTS]: "這個分支名稱已存在，請換一個分支名稱",
  [RESEARCH_REASONS.TARGET_NOT_EMPTY]: "目標資料夾已存在而且不是空的，請換一個專案名稱",
  [RESEARCH_REASONS.PUBLIC_CONFIRMATION_REQUIRED]: "公開的遠端庫需要重新輸入庫名確認，輸入的庫名必須與庫名完全相同",
  [RESEARCH_REASONS.ROUTE_STEP_FAILED]: "分流有一步失敗了，已完成的步驟會保留；請看失敗步驟的原因，修好後按「重試失敗步驟」",
  [RESEARCH_REASONS.SCR_OPEN]: "規格變更請求進行中，這個動作暫時不能做；請先完成或撤回變更",
  [RESEARCH_REASONS.SCR_LIMIT]: "同一個研究專案的小幅規格變更已達上限，請改走大幅變更",
  [RESEARCH_REASONS.DECOMPOSITION_STALE]: "PRD 已更新，拆解已過期；請重新拆解並再簽核",
  [RESEARCH_REASONS.COMPILE_FAILED]: "提示詞編譯失敗，請洽管理員",
  [RESEARCH_REASONS.SDD_CLI_FAILED]: "狀態機命令列執行失敗，請稍後再試或洽管理員",
  [RESEARCH_REASONS.FSM_STATE_UNREADABLE]: "讀不到狀態機的現態，請確認狀態目錄是否正常",
  [RESEARCH_REASONS.INVALID_REQUEST]: "送出的內容沒有通過檢查，請依欄位提示修正",
  [RESEARCH_REASONS.TAG_EXISTS]: "這個 Tag 名稱已存在（不是本專案已記錄的），請換一個版本號",
  [RESEARCH_REASONS.DELIVERY_STEP_FAILED]: "交付有一步失敗了，已完成的步驟會保留（不自動回滾）；請看失敗步驟的原因，修好後可重送同一個動作",
};

/** 交付失敗步驟（`delivery_step_failed` 的 `details.failure_step`）中文。 */
export const DELIVERY_STEP_LABEL: Readonly<Record<string, string>> = { push: "推送到遠端", pr_create: "建立 PR", fsm_release: "狀態機進入 RELEASE", tag: "建立 Tag" };

/** 研究端點錯誤的白話原因（依 `reason`；沒有對映時退回通用訊息）。`route_step_failed` 另帶失敗步驟名（取 `details.failureStep` 對映 `ROUTE_STEP_LABEL`）。 */
export function researchErrorText(error: unknown): string {
  if (error instanceof ApiError && error.reason !== undefined && RESEARCH_REASON_TEXT[error.reason] !== undefined) {
    if (error.reason === RESEARCH_REASONS.ROUTE_STEP_FAILED) {
      const raw = error.details?.failureStep ?? error.details?.failure_step;
      if (typeof raw === "string" && raw !== "") return `分流在「${routeStepLabel(raw)}」這一步失敗了，已完成的步驟會保留；請看失敗原因，修好後按「重試失敗步驟」`;
    }
    if (error.reason === RESEARCH_REASONS.DELIVERY_STEP_FAILED) {
      const step = error.details?.failureStep ?? error.details?.failure_step;
      if (typeof step === "string" && step !== "") return `交付在「${DELIVERY_STEP_LABEL[step] ?? step}」這一步失敗了，已完成的步驟會保留；請看失敗原因，修好後可重送同一個動作`;
    }
    return RESEARCH_REASON_TEXT[error.reason];
  }
  return describeError(error);
}

// ══ 研究面板（PKG-FE-B）：事件時間軸、證據矩陣、議題面板、研究來源設定 ═══════════════════════════════════
// 以下全是純函式與常數（不讀瀏覽器全域、不發請求）；元件只負責把結果畫出來。

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const isSeq = (value: unknown): value is number => typeof value === "number" && Number.isSafeInteger(value) && value >= 1;

// ── 事件時間軸與串流去重（FR-R2P-06；AC-R2P-06-1～06-4；TCS AT-960-10-4～10-8）──────────────────

/**
 * 研究串流的具名事件（契約 §3）。EventSource 只把「有人 addEventListener 的事件名」交給程式，所以**全部都要訂閱**——連 P1、P2 才會出現的、
 * 與目前畫面不顯示的也一樣：沒訂閱的事件仍佔用 seq，下一則收到的事件就會被誤判成「序號不連續」而白白全量重抓。
 */
export const RESEARCH_SSE_EVENT_TYPES: readonly string[] = [
  "research.step",
  "research.run",
  "research.source",
  "research.evidence",
  "research.prd",
  "research.review",
  "research.review_invalid",
  "research.defect",
  "research.gate",
  "research.reconcile",
  "research.route",
  "research.scr",
  "research.delivery",
  "research.alert",
];
/** 傳輸層訊號（不是 `research_events` 列、不帶 `id:`、不佔 seq）：伺服器重播不完整時送出，客戶端收到即全量重抓。 */
export const RESEARCH_REPLAY_GAP_EVENT = "research.replay_gap";
export const RESEARCH_HEARTBEAT_EVENT = "heartbeat";

/** 研究串流網址（EventSource 不能帶標頭，token 放網址；API-RP-06）：`base` 為後端 origin（不含 `/api/v1`，全棧同源為空字串）。 */
export function buildResearchStreamUrl(base: string, researchId: string, token: string): string {
  return `${base}/api/v1/stream/research/${encodeURIComponent(researchId)}?access_token=${encodeURIComponent(token)}`;
}

/**
 * 串流上的事件：`data` 是 ResearchEvent JSON；`emittedAt`（選填）是伺服器送出的時間，量測「事件到畫面」延遲用——帶 offset 的 ISO-8601 字串，或 epoch 毫秒（數字）。
 * 契約 §1.3 的 DTO 沒有此欄、後端測試替身把它放在 `payload.emitted_at`（epoch 毫秒），所以解析時頂層 `emittedAt` 與 `payload.emitted_at`／`payload.emittedAt` 都認（見 `parseTimelineEvent`）。
 */
export type TimelineEvent = ResearchEvent & { emittedAt?: string | number | null };

/** 事件的送出時間：頂層 `emittedAt` 優先，其次 `payload.emitted_at`、`payload.emittedAt`；只認字串或有限數字，其餘當沒有。 */
function emittedAtOf(raw: Record<string, unknown>, payload: Record<string, unknown>): string | number | null {
  for (const candidate of [raw.emittedAt, payload.emitted_at, payload.emittedAt]) {
    if (typeof candidate === "string" && candidate !== "") return candidate;
    if (typeof candidate === "number" && Number.isFinite(candidate)) return candidate;
  }
  return null;
}

/**
 * 解析串流訊息：序號以 `data.seq` 為準（瀏覽器的 `lastEventId` 在事件沒有 `id:` 行時沿用前一則的值，不能當身分），沒有合法 seq 才退用 `id`。
 * 形狀不合（不是物件、沒有 `eventType`、序號解不出）回 null——呼叫端略過，不讓一行損毀的資料掛掉整條串流。
 */
export function parseTimelineEvent(raw: unknown, id?: string | null): TimelineEvent | null {
  if (!isRecord(raw) || typeof raw.eventType !== "string" || raw.eventType === "") return null;
  const fromId = typeof id === "string" && /^\d+$/.test(id) ? Number(id) : null;
  const seq = isSeq(raw.seq) ? raw.seq : fromId;
  if (!isSeq(seq)) return null;
  const payload = isRecord(raw.payload) ? raw.payload : {};
  return {
    seq,
    eventType: raw.eventType,
    step: (typeof raw.step === "string" ? raw.step : "topic") as ResearchFlowStepId,
    actor: typeof raw.actor === "string" ? raw.actor : "",
    refKind: typeof raw.refKind === "string" ? raw.refKind : null,
    refId: typeof raw.refId === "string" ? raw.refId : null,
    payload,
    occurredAt: typeof raw.occurredAt === "string" ? raw.occurredAt : "",
    emittedAt: emittedAtOf(raw, payload),
  };
}

/** `research.replay_gap` 的資料 `{fromSeq, toSeq}`：缺漏的序號範圍；形狀不合回 null（訊號本身仍要觸發重抓，只是沒有範圍）。 */
export function parseReplayGap(raw: unknown): { fromSeq: number; toSeq: number } | null {
  return isRecord(raw) && isSeq(raw.fromSeq) && isSeq(raw.toSeq) ? { fromSeq: raw.fromSeq, toSeq: raw.toSeq } : null;
}

export type IncomingSeq = "duplicate" | "next" | "gap";

/** 新到事件相對「已處理的最大 seq」：小於等於＝重複（至少一次送達的重播）、恰好加一＝接續、更大＝缺口（要全量重抓）。 */
export function classifyIncomingSeq(lastSeq: number, seq: number): IncomingSeq {
  if (seq <= lastSeq) return "duplicate";
  return seq === lastSeq + 1 ? "next" : "gap";
}

/** 兩份事件依 seq 聯集：升冪、同 seq 只留一筆（`base`＝資料庫的 REST 結果，優先於串流上收到的）。 */
export function mergeEventsBySeq<T extends { seq: number }>(base: readonly T[], incoming: readonly T[]): T[] {
  const bySeq = new Map<number, T>();
  for (const event of incoming) bySeq.set(event.seq, event);
  for (const event of base) bySeq.set(event.seq, event);
  return [...bySeq.values()].sort((a, b) => a.seq - b.seq);
}

/** 自 seq 1 起連續的最長前綴（事件帳的 seq 自 1 起連續；缺口之後的事件一律不渲染——缺口補上前不得顯示殘缺的時間軸）。輸入須已依 seq 升冪、去重。 */
export function contiguousPrefix<T extends { seq: number }>(sorted: readonly T[]): T[] {
  const out: T[] = [];
  for (const event of sorted) {
    if (event.seq !== out.length + 1) break;
    out.push(event);
  }
  return out;
}

export type TimelineView<T> = {
  /** 要渲染的事件：嚴格遞增、自 1 起連續、沒有重複 */
  visible: T[];
  /** 已收到但因缺口或障壁而扣住的事件數 */
  held: number;
  /** 第一個沒有渲染的 seq（缺口的起點；全部都渲染了為 null） */
  gapFrom: number | null;
  /** 已處理（載入或收到）的最大 seq（含扣住的）：下一則串流事件相對它判重複、接續或缺口 */
  lastSeq: number;
};

/**
 * REST 結果與串流事件合成要渲染的時間軸。`barrier` 非 null＝正在全量重抓：只渲染 seq 不超過它的事件（重抓完成前不渲染缺口或訊號之後的事件），
 * 重抓完成後由呼叫端放掉障壁，兩邊依 seq 去重合併。
 */
export function timelineView<T extends { seq: number }>(rest: readonly T[], live: readonly T[], barrier: number | null = null): TimelineView<T> {
  const merged = mergeEventsBySeq(rest, live);
  const lastSeq = merged.length === 0 ? 0 : merged[merged.length - 1].seq;
  const allowed = barrier === null ? merged : merged.filter((event) => event.seq <= barrier);
  const visible = contiguousPrefix(allowed);
  const held = merged.length - visible.length;
  return { visible, held, gapFrom: held > 0 ? visible.length + 1 : null, lastSeq };
}

/** 時間軸最多渲染最近幾筆（其餘折疊，按鈕展開）；事件帳整份重抓上限約 10,000 筆，全部渲染會拖慢頁面。 */
export const TIMELINE_RENDER_LIMIT = 500;

export type EventTone = "normal" | "good" | "warn" | "error";
export type EventKind = "step" | "run" | "source" | "evidence" | "prd" | "review" | "defect" | "gate" | "reconcile" | "alert" | "other";
/**
 * 一筆事件在時間軸上的呈現：`headline` 是固定用語、`subject` 是動態主文（來源標題、論點、無效原因、警示說明…；外部衍生，元件一律當純文字渲染）、
 * `meta` 是短的附註；`url` 只在來源事件有（是否成連結由 `safeExternalHref` 決定）。
 */
export type EventLine = { kind: EventKind; headline: string; subject: string; meta: string[]; tone: EventTone; url?: string };

export const STAGE_LABEL: Readonly<Record<string, string>> = { RESEARCH: "研究", DRAFT: "草擬", REVIEW: "審查", REVISE: "修訂", ITERATE: "迭代", TCS_DRAFT: "測試規格草擬" };
export const RUN_STATUS_LABEL: Readonly<Record<string, string>> = {
  QUEUED: "排隊中",
  RUNNING: "執行中",
  SUCCEEDED: "已完成",
  FAILED: "失敗",
  CANCELLED: "已取消",
  BLOCKED_DB: "資料庫阻塞",
};
export const SOURCE_LAYER_LABEL: Readonly<Record<ResearchSourceLayer, string>> = { ACADEMIC: "學術層", INDUSTRY: "產業層", OSS: "開源層", COMMUNITY: "社群層" };
export const REVIEW_VERDICT_LABEL: Readonly<Record<string, string>> = { PASS: "通過", REVISE: "需修訂", ESCALATE: "升級人工" };
export const ALERT_KIND_LABEL: Readonly<Record<string, string>> = { BLOCKED_DB: "資料庫阻塞", ESCALATED: "待人工處理", QUOTA: "額度", DENIED_FETCH: "外呼被拒", STAGE_FAILED: "階段失敗" };
export const EVIDENCE_STRENGTH_LABEL: Readonly<Record<ResearchEvidenceItem["strength"], string>> = { STRONG: "強", MEDIUM: "中", WEAK: "弱", CANDIDATE: "候選" };

const labelOf = (table: Readonly<Record<string, string>>, key: string): string => table[key] ?? key;
const payloadText = (payload: Record<string, unknown>, key: string): string => {
  const value = payload[key];
  return typeof value === "string" ? value : typeof value === "number" || typeof value === "boolean" ? String(value) : "";
};
const payloadNumber = (payload: Record<string, unknown>, key: string): number | null => {
  const value = payload[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
};
const compact = (parts: ReadonlyArray<string | false | null | undefined>): string[] => parts.filter((part): part is string => typeof part === "string" && part !== "");

/** 事件在時間軸上的呈現（契約 §3 各事件的 payload；缺欄一律略過、不丟例外，未知的事件型別只顯示型別名）。 */
export function describeResearchEvent(event: Pick<ResearchEvent, "eventType" | "payload">): EventLine {
  const p = event.payload;
  switch (event.eventType) {
    case "research.step": {
      const step = payloadText(p, "flowStep");
      const status = payloadText(p, "flowStatus");
      return {
        kind: "step",
        headline: "流程推進",
        subject: compact([payloadText(p, "flowPhase") !== "" && flowPhaseLabel(payloadText(p, "flowPhase")), status !== "" && `（${flowStatusLabel(status)}）`]).join(""),
        meta: compact([isFlowStepId(step) ? `第 ${stepNumber(step)} 步「${FLOW_STEP_LABEL[step]}」` : step, payloadText(p, "flowDetail")]),
        tone: status === "FAILED" ? "error" : status === "BLOCKED" || status === "ESCALATED" ? "warn" : "normal",
      };
    }
    case "research.run": {
      const status = payloadText(p, "status");
      const round = payloadNumber(p, "roundNo");
      const attempt = payloadNumber(p, "attempt");
      const tokens = payloadNumber(p, "tokensUsed");
      return {
        kind: "run",
        headline: `${labelOf(STAGE_LABEL, payloadText(p, "stage"))}階段`,
        subject: status === "" ? "" : labelOf(RUN_STATUS_LABEL, status),
        meta: compact([round !== null && round > 0 && `第 ${round} 輪`, attempt !== null && `第 ${attempt} 次嘗試`, tokens !== null && `累計 ${tokens.toLocaleString("en-US")} tokens`]),
        tone: status === "FAILED" ? "error" : status === "SUCCEEDED" ? "good" : status === "BLOCKED_DB" ? "warn" : "normal",
      };
    }
    case "research.source": {
      const layer = payloadText(p, "layer");
      const outcome = payloadText(p, "fetchOutcome");
      const url = payloadText(p, "url");
      return {
        kind: "source",
        headline: `取得來源 ${payloadText(p, "sourceNo")}`.trim(),
        subject: payloadText(p, "title"),
        meta: compact([
          labelOf(SOURCE_LAYER_LABEL, layer),
          payloadText(p, "tier") !== "" && `分級 ${payloadText(p, "tier")}`,
          payloadText(p, "verification") !== "" && `查證 ${payloadText(p, "verification")}`,
          outcome !== "" && `抓取 ${outcome}`,
        ]),
        tone: outcome === "" || outcome === "OK" ? "normal" : "warn",
        ...(url === "" ? {} : { url }),
      };
    }
    case "research.evidence": {
      const strength = payloadText(p, "strength");
      return {
        kind: "evidence",
        headline: `證據列 ${payloadText(p, "evidenceNo")}`.trim(),
        subject: payloadText(p, "claim"),
        meta: compact([payloadText(p, "sourceNo") !== "" && `來源 ${payloadText(p, "sourceNo")}`, strength !== "" && `強度 ${labelOf(EVIDENCE_STRENGTH_LABEL, strength)}`]),
        tone: "normal",
      };
    }
    case "research.prd":
      return {
        kind: "prd",
        headline: "PRD 新版本",
        subject: payloadText(p, "semver"),
        meta: compact([payloadText(p, "authorKind") === "AGENT" ? "AI 起草" : payloadText(p, "authorKind") === "HUMAN" ? "人工編輯" : payloadText(p, "authorKind"), payloadText(p, "author")]),
        tone: "normal",
      };
    case "research.review": {
      const verdict = payloadText(p, "verdict");
      const weighted = payloadNumber(p, "weightedScore");
      const min = payloadNumber(p, "minDimensionScore");
      const round = payloadNumber(p, "roundNo");
      return {
        kind: "review",
        headline: round === null ? "審查完成" : `第 ${round} 輪審查完成`,
        subject: labelOf(REVIEW_VERDICT_LABEL, verdict),
        meta: compact([weighted === null ? "前置檢查未過，未計分" : `加權 ${weighted.toFixed(2)}`, min !== null && `最低維度 ${min}`]),
        tone: verdict === "PASS" ? "good" : verdict === "ESCALATE" ? "error" : "warn",
      };
    }
    case "research.review_invalid":
      return {
        kind: "review",
        headline: "審查輸出無效",
        subject: payloadText(p, "reason"),
        meta: compact([payloadNumber(p, "roundNo") !== null && `第 ${payloadText(p, "roundNo")} 輪`, payloadNumber(p, "attempt") !== null && `第 ${payloadText(p, "attempt")} 次嘗試`]),
        tone: "error",
      };
    case "research.defect":
      return {
        kind: "defect",
        headline: `缺陷 ${payloadText(p, "defectNo")}`.trim(),
        subject: compact([payloadText(p, "severity"), payloadText(p, "dimension")]).join(" · "),
        meta: compact([payloadText(p, "status")]),
        tone: payloadText(p, "severity") === "P1" ? "error" : "normal",
      };
    case "research.gate":
      return {
        kind: "gate",
        headline: "Gate 決定",
        subject: payloadText(p, "decision"),
        meta: compact([payloadText(p, "gate"), payloadText(p, "decidedBy") !== "" && `決定者 ${payloadText(p, "decidedBy")}`]),
        tone: "normal",
      };
    case "research.reconcile": {
      const consistent = p.consistent === true;
      const drift = payloadNumber(p, "driftCount");
      return { kind: "reconcile", headline: "對帳", subject: consistent ? "一致" : "發現不一致", meta: compact([drift !== null && `${drift} 項漂移`]), tone: consistent ? "good" : "warn" };
    }
    case "research.alert": {
      const kind = payloadText(p, "kind");
      return { kind: "alert", headline: `警示：${labelOf(ALERT_KIND_LABEL, kind)}`, subject: payloadText(p, "detail"), meta: [], tone: kind === "STAGE_FAILED" ? "error" : "warn" };
    }
    default:
      return { kind: "other", headline: event.eventType, subject: "", meta: [], tone: "normal" };
  }
}

// ── 事件到畫面的延遲（AC-R2P-06-1；AT-960-10-7）────────────────────────────────────────

const HAS_OFFSET = /(Z|[+-]\d{2}:?\d{2})$/i;
const instantMs = (value: string | number | Date): number => {
  if (typeof value === "number") return value;
  if (value instanceof Date) return value.getTime();
  return HAS_OFFSET.test(value) ? Date.parse(value) : Number.NaN;
};

/**
 * 事件自產生到畫面顯示的延遲（毫秒）：`renderedAt`（前端記下的 `rendered_at`）減 `emittedAt`（伺服器送出時間）；字串形式的時間戳都要帶 offset，數字是 epoch 毫秒（本身就是絕對瞬間）。
 * 沒有 `emittedAt`、或任一方沒有 offset／解不出，回 null——量不到就是量不到、不是 0，呼叫端計入 `unmeasured`。時鐘偏差造成的負值照實回傳、不夾 0。
 */
export function renderLatencyMs(event: { emittedAt?: string | number | null }, renderedAt: string | number | Date): number | null {
  if (event.emittedAt === undefined || event.emittedAt === null || event.emittedAt === "") return null;
  const emitted = instantMs(event.emittedAt);
  const rendered = instantMs(renderedAt);
  return Number.isNaN(emitted) || Number.isNaN(rendered) ? null : rendered - emitted;
}

/** 最近秩（nearest-rank）百分位：升冪後取第 ⌈p×n⌉ 個；沒有樣本回 null。 */
export function percentile(values: readonly number[], p: number): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const rank = Math.min(sorted.length, Math.max(1, Math.ceil(p * sorted.length - 1e-9)));
  return sorted[rank - 1];
}

export type LatencySummary = { measured: number; unmeasured: number; p95: number | null };

/** 延遲樣本的摘要：null 的樣本（量不到）不入 P95、計入 `unmeasured`。 */
export function latencySummary(samples: ReadonlyArray<number | null>): LatencySummary {
  const measured = samples.filter((sample): sample is number => sample !== null);
  return { measured: measured.length, unmeasured: samples.length - measured.length, p95: percentile(measured, 0.95) };
}

// ── 證據矩陣（FR-R2P-05、06；AT-960-10-6；PRD §5.1.1 步驟 1 條件）──────────────────────────────

/** 步驟 1 的證據閘：最新矩陣至少這麼多列「層級 V2 以上、非 UNANCHORED、非線索」才可生成 PRD 初稿（初值、未校準；PRD §5.1.1）。 */
export const MIN_EVIDENCE_ROWS = 3;
/** 解析不出 host 的被拒外呼，入庫列的 host 取此保留字（D-66）；顯示時原樣、不轉空白、不加連結。 */
export const RESEARCH_UNPARSED_HOST = "(unparsed)";

/** 合格的證據列：查證層級 V2 以上、Bridge 錨定檢查沒有標 UNANCHORED、來源不是線索（`clueOnly`）。來源清單裡找不到的列視為非線索（沒有反證）。 */
export function qualifiedEvidenceRows<I extends Pick<ResearchEvidenceItem, "sourceNo" | "f7Verification" | "unanchored">>(
  items: readonly I[],
  sources: ReadonlyArray<Pick<ResearchSource, "sourceNo" | "clueOnly">>,
): I[] {
  const clues = new Set(sources.filter((s) => s.clueOnly).map((s) => s.sourceNo));
  return items.filter((item) => (item.f7Verification === "V2" || item.f7Verification === "V3") && !item.unanchored && !clues.has(item.sourceNo));
}

export type EvidenceGate = { ok: boolean; qualified: number; required: number; text: string };

/** 證據閘（步驟 1 的條件之一）：不過時 `text` 說明缺什麼。 */
export function evidenceGate(items: readonly ResearchEvidenceItem[], sources: ReadonlyArray<Pick<ResearchSource, "sourceNo" | "clueOnly">>): EvidenceGate {
  const qualified = qualifiedEvidenceRows(items, sources).length;
  const ok = qualified >= MIN_EVIDENCE_ROWS;
  return {
    ok,
    qualified,
    required: MIN_EVIDENCE_ROWS,
    text: ok ? `證據已足夠：${qualified} 列合格` : `證據不足：目前只有 ${qualified} 列合格（層級 V2 以上、已錨定、非線索），至少需要 ${MIN_EVIDENCE_ROWS} 列`,
  };
}

/** UNANCHORED 的列數（數字在抓取原文比對不到者；Bridge 入庫時計算）。 */
export function unanchoredCount(items: ReadonlyArray<Pick<ResearchEvidenceItem, "unanchored">>): number {
  return items.filter((item) => item.unanchored).length;
}

/** 授權「未見」的寫法（D-70、D-80；比對一律大小寫不敏感、先修剪空白）：空字串、agent 依模板「查不到寫 UNKNOWN」的值、模板的「未見」；`null`／`undefined`（資料庫的 NULL）另判。 */
const LICENSE_UNKNOWN_FORMS: ReadonlySet<string> = new Set(["", "unknown", "未見"]);
/** SPDX 複合表達式的連接詞：以空白或括號與前後分隔的 `OR`／`AND`／`WITH`；`GPL-3.0-or-later` 的 `-or-` 是識別碼的一部分（前後是連字號），不算。 */
const COMPOSITE_LICENSE = /(?:^|[\s()])(?:OR|AND|WITH)(?:[\s()]|$)/i;
/** GPL／AGPL 系（AC-R2P-05-5）：字界 `\b` 使 `LGPL` 不命中（`GPL` 前面是字母）——LGPL 是已知授權。 */
const GPL_FAMILY = /\bA?GPL/i;

/**
 * 授權待查（矩陣頁頂計數與證據列旗標；AC-R2P-05-5；D-80）——與 Bridge 的 `gates/evidence.py is_license_pending` 同一條規則，雙端對拍同一張期望表
 * （`engine-bridge/tests/fixtures/research/license_pending_cases.json`，兩端的測試各自斷言；任何一端改規則必須同時改那張表）：
 *  · 授權為「未見」（`null`、空白、`UNKNOWN`、`未見`；大小寫不敏感、先修剪空白）＝待查——待查的語意是「還不知道授權是什麼」；
 *  · 含 `OR`／`AND`／`WITH` 的複合表達式＝知道授權、要人判，原樣顯示、**不**待查（即使內含 GPL）；
 *  · 其餘依 GPL／AGPL 系判（`\bA?GPL`）；LGPL 等已知授權不待查。
 * 兩端判準若相反，UI 的計數會與 matrix.md 頁頂與資安審查輸入脫鉤（SCG-4 一審 F-02）。
 */
export function isLicensePending(spdx: string | null | undefined): boolean {
  if (spdx === null || spdx === undefined) return true;
  const value = spdx.trim();
  if (LICENSE_UNKNOWN_FORMS.has(value.toLowerCase())) return true;
  if (COMPOSITE_LICENSE.test(value)) return false;
  return GPL_FAMILY.test(value);
}

export function licensePendingCount(items: ReadonlyArray<Pick<ResearchEvidenceItem, "sourceNo">>, sources: ReadonlyArray<Pick<ResearchSource, "sourceNo" | "licenseSpdx">>): number {
  const license = new Map(sources.map((s) => [s.sourceNo, s.licenseSpdx] as const));
  return items.filter((item) => isLicensePending(license.get(item.sourceNo))).length;
}

export type ProsConsEntry = { evidenceNo: string; text: string };
export type ProsConsCandidate = { candidate: string; evidenceNos: string[]; pros: ProsConsEntry[]; cons: ProsConsEntry[] };

const hasContent = (text: string | null | undefined): text is string => typeof text === "string" && text.trim() !== "" && text.trim() !== "未見";

/**
 * 技術優缺點矩陣（唯讀；AC-R2P-06-5）：依候選技術分組，**只列有證據列的候選**（沒有候選名的列不歸任何組、只存在於範圍的候選不憑空出現）。
 * 優點＝該候選各證據列的論點（`claim`）；缺點＝失敗與批評（F3）、限制（F6）與判為削弱或限縮（WEAKEN／LIMIT）的反證說明；每格帶 `evidenceNo`（畫面上的 `[E-NNN]` 連結）。
 * 候選依第一次出現的順序排列。
 */
export function prosConsMatrix(matrix: Pick<ResearchEvidenceMatrix, "items" | "counterEvidence">): ProsConsCandidate[] {
  const groups = new Map<string, ProsConsCandidate>();
  for (const item of matrix.items) {
    const name = (item.candidate ?? "").trim();
    if (name === "") continue;
    const group = groups.get(name) ?? { candidate: name, evidenceNos: [], pros: [], cons: [] };
    groups.set(name, group);
    group.evidenceNos.push(item.evidenceNo);
    if (hasContent(item.claim)) group.pros.push({ evidenceNo: item.evidenceNo, text: item.claim });
    for (const text of [item.f3Critique, item.f6Limits]) if (hasContent(text)) group.cons.push({ evidenceNo: item.evidenceNo, text });
  }
  for (const counter of matrix.counterEvidence) {
    if (counter.conclusion !== "WEAKEN" && counter.conclusion !== "LIMIT") continue;
    const group = [...groups.values()].find((g) => g.evidenceNos.includes(counter.evidenceNo));
    if (group !== undefined && hasContent(counter.note)) group.cons.push({ evidenceNo: counter.evidenceNo, text: counter.note });
  }
  return [...groups.values()];
}

/** 外部網址只有「合法的 https、沒有帳密」才可成為連結（外部來源是資料不是指令：`javascript:`、`data:` 等一律只顯示文字）；回正規化後的網址或 null。 */
export function safeExternalHref(url: string | null | undefined): string | null {
  if (typeof url !== "string" || url === "") return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && parsed.username === "" && parsed.password === "" ? parsed.href : null;
  } catch {
    return null;
  }
}

// ── 議題面板（FR-R2P-04；AT-960-19-7）───────────────────────────────────────────────────

export type ResearchFailure = {
  /** `exit_reason`（取自游標的 `flowDetail`；沒有說明時為空字串） */
  reason: string;
  /** `no_evidence` 沒有任何來源取得成功，沒有 checkpoint 可續，只能重試；`cancelled`（使用者取消）也是重試；其餘（`token_guard_halt`、`step_timeout`…）從 checkpoint 續跑 */
  action: "resume" | "retry";
  text: string;
};

/** 研究被取消時 Bridge 寫進游標 `flow_detail` 的 `exit_reason`（D-77：取消與失敗一樣是 `flow_status=FAILED`，靠這個值分辨）。 */
export const RESEARCH_CANCELLED_REASON = "cancelled";

/**
 * 研究階段失敗（步驟 1 且 `flow_status=FAILED`，初始化失敗不算）的呈現：橫幅「研究未完成：原因」加「續跑」；`no_evidence` 是「研究失敗」加「重試」（沒有任何來源，沒有 checkpoint 可續）；
 * 被取消（`flow_detail=cancelled`）是「研究已取消」加「重試」（取消不是出錯，不帶原因代碼；已入庫的證據保留）。
 * 判準維持只認 `flow_status=FAILED`（D-77：游標不再把失敗寫成 IDLE 加說明，否則看不出是閒置還是失敗）；失敗的研究不得顯示為完成（AC-R2P-04-5）；沒有失敗回 null。
 */
export function researchFailureOf(project: Pick<ResearchProjectSummary, "flowStep" | "flowStatus" | "flowDetail">): ResearchFailure | null {
  if (project.flowStep !== "topic" || project.flowStatus !== "FAILED" || isInitFailed(project)) return null;
  const reason = project.flowDetail.trim();
  if (reason === RESEARCH_CANCELLED_REASON) return { reason, action: "retry", text: "研究已取消：已入庫的證據會保留，可以重試" };
  if (reason === "no_evidence") return { reason, action: "retry", text: `研究失敗：沒有任何來源取得成功（${reason}）` };
  return { reason, action: "resume", text: `研究未完成：${reason === "" ? "後端沒有提供原因" : reason}` };
}

/** 容器模式（Bridge 映像沒有 `claude`）下「啟動深研」停用時顯示的說明（AC-R2P-04-11；逐字）。 */
export const MOCK_ONLY_NOTICE = "容器模式只跑 mock claude 的驗收；真研究限本機模式";

/**
 * 研究環境不允許啟動深研的原因（沒有擋就回 null）：探針失敗、尚未載入、Bridge 沒連上資料庫（研究不降級成純檔案模式）、容器模式、找不到 `claude`。
 * 伺服器端不因 mock-only 拒絕（供 API 直呼驗證），所以這只是 UI 的停用說明。
 */
export function researchEnvironmentBlock(capabilities: Pick<ResearchCapabilities, "mode" | "db" | "claudeCli"> | undefined, probeFailed: boolean): string | null {
  if (probeFailed) return "無法確認研究環境（Bridge 不可用或沒有回應），暫時不能啟動研究";
  if (capabilities === undefined) return "正在檢查研究環境…";
  if (!capabilities.db) return "Bridge 沒有連上資料庫：研究需要資料庫，不會降級成純檔案模式";
  if (capabilities.mode === "mock-only") return MOCK_ONLY_NOTICE;
  if (!capabilities.claudeCli.ok) return "找不到 claude 命令列工具，請先在本機安裝並登入";
  return null;
}

export type ResearchScopeView = {
  layers: Record<"academic" | "industry" | "oss" | "community", boolean>;
  techStack: string;
  inScope: string[];
  outOfScope: string[];
  recencyYears: number | null;
  applicabilityAxes: string[];
};

/**
 * 專案詳情的 `scope`（自由形狀的 JSON）整理成畫面要的唯讀內容；缺欄、型別不對一律當空值，不丟例外。
 * 鍵一律 camelCase（`layers`、`techStack`、`inScope`、`outOfScope`、`recencyYears`、`applicabilityAxes`）：Bridge 寫入的 snake_case 鍵由 console-api 的 DTO 在邊界轉成 camelCase
 * （D-76(2)；schema.d.ts `ResearchProjectDetail.scope`），前端**只認 camelCase**、不兩邊都認——INT-03 就是兩端各自照自己的讀法造成的錯位，邊界統一在防腐層、不在這裡再補一個讀法。
 */
export function readResearchScope(scope: Record<string, unknown>): ResearchScopeView {
  const layers = isRecord(scope.layers) ? scope.layers : {};
  const strings = (value: unknown): string[] => (Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim() !== "") : []);
  return {
    layers: { academic: layers.academic === true, industry: layers.industry === true, oss: layers.oss === true, community: layers.community === true },
    techStack: typeof scope.techStack === "string" ? scope.techStack : "",
    inScope: strings(scope.inScope),
    outOfScope: strings(scope.outOfScope),
    recencyYears: typeof scope.recencyYears === "number" ? scope.recencyYears : null,
    applicabilityAxes: strings(scope.applicabilityAxes),
  };
}

// ── 研究來源設定（FR-R2P-04；AT-960-19-8）──────────────────────────────────────────────

/** 契約 §1.2：小寫 host、無 scheme、埠、路徑與帳密（DB CHECK 同式）。 */
export const ALLOWLIST_HOST_PATTERN = /^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$/;
export const ALLOWLIST_PURPOSE_MAX = 200;
export const ALLOWLIST_INTERVAL_MIN = 1;
export const ALLOWLIST_INTERVAL_MAX = 3600;
export const ALLOWLIST_DEFAULT_INTERVAL = 5;

export const ALLOWLIST_LIST_KIND_LABEL: Readonly<Record<ResearchAllowlistRequest["listKind"], string>> = { WEB: "Web 層（產業網域）", FETCH: "原生抓取" };
export const ALLOWLIST_LAYER_OPTIONS: ReadonlyArray<{ id: ResearchSourceLayer; label: string }> = [
  { id: "INDUSTRY", label: SOURCE_LAYER_LABEL.INDUSTRY },
  { id: "ACADEMIC", label: SOURCE_LAYER_LABEL.ACADEMIC },
  { id: "OSS", label: SOURCE_LAYER_LABEL.OSS },
  { id: "COMMUNITY", label: SOURCE_LAYER_LABEL.COMMUNITY },
];

/** Reddit 網域（`reddit.com`、`*.reddit.com`、`redd.it`）：加入清單須先確認「已自建 Reddit 應用並接受其條款」（D-17；422 `terms_ack_required`）。 */
export function isRedditHost(host: string): boolean {
  const value = host.trim().toLowerCase();
  return value === "reddit.com" || value.endsWith(".reddit.com") || value === "redd.it";
}

export type AllowlistForm = {
  listKind: ResearchAllowlistRequest["listKind"];
  host: string;
  layer: string;
  purpose: string;
  tosNote: string;
  /** 輸入框的字串（驗證後才轉整數） */
  minIntervalSeconds: string;
  tosAcknowledged: boolean;
};
export type AllowlistFormField = "host" | "layer" | "purpose" | "minIntervalSeconds" | "tosAcknowledged";

/** 主機名稱先去頭尾空白並轉小寫再驗（貼進大小寫混用的網域是常見情形，轉換不改變語意）。 */
export function normalizeAllowlistHost(raw: string): string {
  return raw.trim().toLowerCase();
}

/** 研究來源設定的新增表單驗證（前端只為更早給回饋；後端輸入閘與 Bridge 入口各再擋一次）：逐欄回第一則錯誤，沒有錯誤回空物件。 */
export function allowlistFormErrors(form: AllowlistForm): Partial<Record<AllowlistFormField, string>> {
  const errors: Partial<Record<AllowlistFormField, string>> = {};
  const host = normalizeAllowlistHost(form.host);
  if (host === "") errors.host = "請輸入主機名稱";
  else if (/[/:@?#\s]/.test(host)) errors.host = "只輸入主機名稱，不要含 https://、埠號、路徑或帳密";
  else if (!ALLOWLIST_HOST_PATTERN.test(host)) errors.host = "主機名稱只能是英數、點與連字號，且以英數開頭與結尾";
  if (!ALLOWLIST_LAYER_OPTIONS.some((option) => option.id === form.layer)) errors.layer = "請選擇來源層";
  if (Array.from(form.purpose.trim()).length > ALLOWLIST_PURPOSE_MAX) errors.purpose = `用途最多 ${ALLOWLIST_PURPOSE_MAX} 個字`;
  const interval = Number(form.minIntervalSeconds);
  if (form.minIntervalSeconds.trim() === "" || !Number.isInteger(interval) || interval < ALLOWLIST_INTERVAL_MIN || interval > ALLOWLIST_INTERVAL_MAX)
    errors.minIntervalSeconds = `最小間隔須為 ${ALLOWLIST_INTERVAL_MIN} 至 ${ALLOWLIST_INTERVAL_MAX} 的整數（秒）`;
  if (host !== "" && isRedditHost(host) && !form.tosAcknowledged) errors.tosAcknowledged = "Reddit 網域須先勾選「已自建 Reddit 應用並接受其條款」";
  return errors;
}

/** 表單轉請求本文（camelCase）：`tosAcknowledged` 只有 Reddit 網域才可能為真。 */
export function toAllowlistRequest(form: AllowlistForm): ResearchAllowlistRequest {
  const host = normalizeAllowlistHost(form.host);
  return {
    listKind: form.listKind,
    host,
    layer: form.layer,
    purpose: form.purpose.trim(),
    tosNote: form.tosNote.trim(),
    minIntervalSeconds: Number(form.minIntervalSeconds),
    tosAcknowledged: isRedditHost(host) && form.tosAcknowledged,
  };
}

// ══ P1 分流（PKG-FE-D1；TCS-ResearchToPRD-P1-20261107 §5.1；IFACE §4、§8；PRD FR-R2P-11～13）═══════════════════════════════════
// 全是純函式與常數：分流精靈（RouteDrawer）與步驟 3 面板只負責把結果畫出來。常數與契約 §1.2 的 `route.*` 列、Bridge `app/research/route.py` 逐值對拍（AT-961-17-E-2）。

/** 分支名（契約 §1.2；ADR-003 D16）；預設 `feature/issue-<NNNN>`（NNNN＝`rpNo` 數字零填四位）。 */
export const BRANCH_PATTERN = /^feature\/[a-z0-9-]{1,40}$/;
/** 遠端庫名（契約 §1.2：2 至 39 字元；省略時取專案名稱）。 */
export const REPO_NAME_PATTERN = /^[a-z][a-z0-9-]{1,38}$/;
/** 專案名稱＝內環鍵（D-119：同時合 GitHub 庫名與 FSM 鍵文法，2 至 62 字元）。 */
export const PROJECT_NAME_PATTERN = /^[a-z][a-z0-9-]{1,61}$/;
/** GitHub owner（D-106；類推 GitHub 使用者名規則）。 */
export const OWNER_PATTERN = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}$/;
/** 分流軌道與 PRD 目標範圍不同時的理由上限（契約 §1.2）。 */
export const SCOPE_REASON_MAX = 200;
/** SCR 理由、拆解豁免理由、補償理由上限（契約 §1.2；三者在後端是各自獨立的常數，前端同值）。 */
export const REASON_MAX = 500;
export const ROUTE_DEFAULT_BASE_REF = "main";
export const ROUTE_TRACK_LABEL: Readonly<Record<ResearchRouteTrack, string>> = { A: "軌道 A：併入 AISDLC", B: "軌道 B：獨立專案" };

/** 落點目標（D-100：P1 固定四值，每項附一句出處＝落點 SSOT `Root_Layout_and_Module_Placement.md` §2）。 */
export const PLACEMENT_TARGETS: ReadonlyArray<{ id: ResearchPlacementTarget; label: string; source: string }> = [
  { id: "autoclaude", label: "AutoClaude", source: "AutoClaude 的外掛與引擎模組落在 AutoClaude 資料夾，走該專案的新增外掛流程" },
  { id: "agentconsole", label: "AgentConsole", source: "AgentConsole 的介面、後端與橋接模組落在 AgentConsole 資料夾，子專案內的模組不往根層放" },
  { id: "sdd", label: "AISDLC_SDD", source: "AISDLC_SDD 的流程、角色與模板資產只改最新版本目錄，走該框架的目錄規則" },
  { id: "monorepo", label: "整個程式庫根層", source: "只有跨專案治理工具才落根層（tools 與 docs 的編號目錄）" },
];

/** 評估維度表（來源規格 §4：五列、三欄加列頭；P1 唯一一份，元件不內嵌第二份）。 */
export const ROUTE_EVAL_TABLE: ReadonlyArray<{ dimension: string; trackA: string; trackB: string }> = [
  { dimension: "目標場景", trackA: "系統底層共用能力、Agent 工具鏈、工作流擴充", trackB: "獨立商用產品、獨立技術棧、外部終端專案" },
  { dimension: "路徑規劃", trackA: "切入 Monorepo 的 packages 或 services", trackB: "建立全新資料夾或指定獨立工作目錄" },
  { dimension: "Git 流程", trackA: "自動建立 feature/issue-<id> 分支", trackB: "執行 git init，設定 Remote Origin，推送 Initial Commit" },
  { dimension: "CI/CD 與環境", trackA: "繼承既有 AISDLC 測試與 Token 治理管線", trackB: "自動生成 GitHub Actions Workflow、Docker Compose 與環境設定檔" },
  { dimension: "規格掛載", trackA: "自動掛載至全域模組登錄表（Module Registry）", trackB: "將 my-project 完整移至新專案根目錄" },
];

/** 11 個分流步驟的中文名（DDL `research_route_steps.step` CHECK；IFACE §4.1）。 */
export const ROUTE_STEP_LABEL: Readonly<Record<string, string>> = {
  VALIDATE_TARGET: "驗證目標",
  GIT_SWITCH: "建立分支與工作樹",
  SCAFFOLD_FILES: "展開專案骨架",
  GIT_INIT: "初始化 git",
  GIT_COMMIT: "初始提交",
  GH_REPO_CREATE: "建立 GitHub 遠端",
  PUBLISH_DOCS: "發佈 PRD",
  COPY_WORKSPACE: "複製研究工作區",
  REGISTER_STUB: "登記落點提示",
  IMPL_KEY_INIT: "建立內環鍵",
  BASELINE_ADOPT: "採納基線",
};
/** 未登記的步驟名顯示原值、不丟例外。 */
export function routeStepLabel(step: string): string {
  return ROUTE_STEP_LABEL[step] ?? step;
}

const ROUTE_STATUS_LABEL: Readonly<Record<string, string>> = { PENDING: "等待中", RUNNING: "執行中", SUCCEEDED: "已完成", FAILED: "失敗", COMPENSATED: "已補償" };
const ROUTE_STEP_STATUS_LABEL: Readonly<Record<string, string>> = { RUNNING: "執行中", OK: "完成", FAILED: "失敗", SKIPPED: "略過", COMPENSATED: "已補償" };
/** 分流（整體）狀態的中文；未登記的值原樣顯示。 */
export function routeStatusLabel(status: string): string {
  return ROUTE_STATUS_LABEL[status] ?? status;
}
export function routeStepStatusLabel(status: string): string {
  return ROUTE_STEP_STATUS_LABEL[status] ?? status;
}

/** 預演 422 `route_unsupported_in_deployment` 的缺項（`details.missing[].item`；D-122）對映中文；未登記的項目原樣顯示。 */
export const ROUTE_MISSING_ITEM_LABEL: Readonly<Record<string, string>> = {
  git: "git 命令不可用",
  gh: "gh 命令不可用",
  repo_writable: "無法寫入程式庫",
  scaffold_root: "尚未設定專案骨架根目錄",
  scaffold_templates: "沒有可用的專案範本",
  worktree_root: "工作樹根目錄不可用",
  gh_auth: "gh 尚未登入",
};
export function routeMissingLabels(missing: unknown): string[] {
  if (!Array.isArray(missing)) return [];
  return missing
    .map((entry) => {
      const item = typeof entry === "string" ? entry : isRecord(entry) && typeof entry.item === "string" ? entry.item : "";
      return item === "" ? "" : (ROUTE_MISSING_ITEM_LABEL[item] ?? item);
    })
    .filter((label) => label !== "");
}

/** PRD 目標範圍對應的預設軌道；`UNDECIDED` 或未知回 null（兩卡皆不預選）。 */
export function routeTrackForScope(targetScope: string): ResearchRouteTrack | null {
  return targetScope === "AISDLC_MODULE" ? "A" : targetScope === "STANDALONE_PROJECT" ? "B" : null;
}
/** 所選軌道與 PRD 目標範圍不同（目標範圍未決定時不算不同）。 */
export function routeScopeDiffers(targetScope: string, track: ResearchRouteTrack): boolean {
  const preset = routeTrackForScope(targetScope);
  return preset !== null && preset !== track;
}
/** 軌道 A 的預設分支名：`feature/issue-<NNNN>`（`rpNo` 如 `RP-0007` 取數字零填四位）。 */
export function routeDefaultBranch(rpNo: string): string {
  const digits = /(\d+)$/.exec(rpNo)?.[1] ?? "0";
  return `feature/issue-${digits.padStart(4, "0").slice(-4)}`;
}

/** 分流精靈表單（字串與布林；驗證後才轉請求本文）。 */
export type RouteForm = {
  track: ResearchRouteTrack | null;
  targetModule: ResearchPlacementTarget | "";
  branchName: string;
  baseRef: string;
  projectName: string;
  stackTemplate: string;
  owner: string;
  repoName: string;
  visibility: ResearchRouteVisibility;
  confirmRepoName: string;
  createGithub: boolean;
  ci: boolean;
  dockerCompose: boolean;
  scopeDiffersReason: string;
};
export type RouteFormField = "track" | "targetModule" | "branchName" | "baseRef" | "projectName" | "stackTemplate" | "owner" | "repoName" | "confirmRepoName" | "scopeDiffersReason";

/** Public 確認：逐字完全相等（不修剪、不正規化；差一個字元、大小寫、尾端空白、不可見字元都算不符）。 */
export function isRepoNameConfirmed(repoName: string, confirm: string): boolean {
  return repoName !== "" && confirm === repoName;
}

/** 軌道 B 實際使用的庫名：明示輸入優先，省略時取專案名稱（D-119）。 */
export function effectiveRepoName(form: Pick<RouteForm, "repoName" | "projectName">): string {
  return form.repoName === "" ? form.projectName : form.repoName;
}

/** 分流表單的逐欄驗證（前端只為更早給回饋；後端輸入閘與 Bridge 入口各再擋一次）：逐欄回第一則錯誤，沒有錯誤回空物件。 */
export function routeFormErrors(form: RouteForm, differs: boolean): Partial<Record<RouteFormField, string>> {
  const errors: Partial<Record<RouteFormField, string>> = {};
  if (form.track === null) {
    errors.track = "請先選擇分流軌道";
    return errors;
  }
  if (form.track === "A") {
    if (form.targetModule === "") errors.targetModule = "請選擇掛載目標";
    if (!BRANCH_PATTERN.test(form.branchName)) errors.branchName = "分支名須為 feature/ 開頭，後接小寫英數與連字號（1 至 40 字）";
    if (form.baseRef.trim() === "" || /\s/.test(form.baseRef)) errors.baseRef = "請輸入基底 ref（不含空白）";
  } else {
    if (!PROJECT_NAME_PATTERN.test(form.projectName)) errors.projectName = "專案名稱須為小寫英文字母開頭，後接小寫英數與連字號（2 至 62 字）";
    if (form.stackTemplate === "") errors.stackTemplate = "請選擇專案範本";
    const repo = effectiveRepoName(form);
    if (form.repoName !== "" && !REPO_NAME_PATTERN.test(form.repoName)) errors.repoName = "庫名須為小寫英文字母開頭，後接小寫英數與連字號（2 至 39 字）";
    else if (form.createGithub && !REPO_NAME_PATTERN.test(repo)) errors.repoName = "要建立遠端時，庫名（省略時為專案名稱）須為 2 至 39 字的小寫英數與連字號";
    if ((form.owner !== "" || form.createGithub) && !OWNER_PATTERN.test(form.owner)) errors.owner = "owner 須為英數與連字號（1 至 39 字），且以英數開頭";
    if (form.visibility === "PUBLIC" && !isRepoNameConfirmed(repo, form.confirmRepoName)) errors.confirmRepoName = "請重新輸入庫名，必須與庫名完全相同";
  }
  if (differs) {
    const length = Array.from(form.scopeDiffersReason).length;
    if (length < 1) errors.scopeDiffersReason = "分流與 PRD 的目標範圍不同，請寫一句理由";
    else if (length > SCOPE_REASON_MAX) errors.scopeDiffersReason = `理由最多 ${SCOPE_REASON_MAX} 個字`;
  }
  return errors;
}

/** 表單轉請求本文（camelCase；不含 `targetPath`〔D-106 退役〕與 `approver`〔後端取 JWT subject〕）。呼叫前須先通過 {@link routeFormErrors}。 */
export function toRouteRequest(form: RouteForm, differs: boolean): ResearchRouteRequest {
  const reason = differs ? { scopeDiffersReason: form.scopeDiffersReason } : {};
  if (form.track === "A") {
    return { track: "A", targetModule: form.targetModule === "" ? undefined : form.targetModule, branchName: form.branchName, baseRef: form.baseRef, ...reason };
  }
  const repoName = effectiveRepoName(form);
  return {
    track: "B",
    projectName: form.projectName,
    stackTemplate: form.stackTemplate,
    repoName,
    owner: form.owner,
    visibility: form.visibility,
    ...(form.visibility === "PUBLIC" ? { confirmRepoName: form.confirmRepoName } : {}),
    createGithub: form.createGithub,
    ci: form.ci,
    dockerCompose: form.dockerCompose,
    ...reason,
  };
}

/** 預演動作是否觸及外部系統（`touchesExternal`；TCS 夾具的別名 `external` 亦認）。 */
export function isExternalRouteAction(action: Pick<ResearchRouteAction, "touchesExternal" | "external">): boolean {
  return action.touchesExternal === true || action.external === true;
}

/** 遠端 URL 只有符合 `https://github.com/<owner>/<repo>` 形時才可成為連結（外部資料不是指令）；其餘只顯示文字。 */
export function safeRepoHref(url: string | null | undefined): string | null {
  return typeof url === "string" && /^https:\/\/github\.com\/[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9._-]{1,100}$/.test(url) ? url : null;
}

/** capabilities 對分流的停用判定（IFACE §8.3）：回「哪些停用、為什麼」的代碼，文案由說明登記表依代碼給（`ROUTE_DISABLED_TEXT`）。 */
export type RouteBlockCode = "git" | "mock-only" | "repo" | "scaffold" | "gh";
export type RouteBlocks = { all: RouteBlockCode | null; trackA: RouteBlockCode | null; trackB: RouteBlockCode | null; github: RouteBlockCode | null };
export function routeCapabilityBlocks(caps: ResearchCapabilities): RouteBlocks {
  const all: RouteBlockCode | null = !caps.git.ok ? "git" : caps.mode === "mock-only" ? "mock-only" : null;
  return {
    all,
    trackA: caps.repoWritable ? null : "repo",
    trackB: caps.scaffoldRoot === null || caps.scaffoldTemplates.length === 0 ? "scaffold" : null,
    github: caps.ghCli.ok ? null : "gh",
  };
}

/** 確認執行前可否再看到「分流」整體狀態：進行中（RUNNING／PENDING）不可再送；失敗可重試；完成唯讀。 */
export function routeIsActive(status: string | undefined): boolean {
  return status === "RUNNING" || status === "PENDING";
}

/** 掛載目標的預設值：由研究命題與代號比對模組名（不分大小寫）；比不到取清單第一項（只是預選，使用者可改）。 */
export function resolveDefaultModule(project: Pick<ResearchProjectDetail, "topic" | "slug">): ResearchPlacementTarget {
  const text = `${project.topic} ${project.slug}`.toLowerCase();
  const hit = PLACEMENT_TARGETS.find((t) => t.id !== "monorepo" && text.includes(t.id));
  return hit?.id ?? PLACEMENT_TARGETS[0].id;
}

/** 分流精靈的初始表單：軌道取預選（PRD 目標範圍）、分支取 `feature/issue-<NNNN>`、基底 `main`、可見度 Private、CI 與 compose 預設勾選；有已存在的分流列時以它還原軌道與參數（游標取自 API，不取瀏覽器儲存）。 */
export function initialRouteForm(
  project: Pick<ResearchProjectDetail, "rpNo" | "targetScope" | "topic" | "slug">,
  defaultTrack: ResearchRouteTrack | null,
  capabilities: Pick<ResearchCapabilities, "scaffoldTemplates"> | undefined,
  row: ResearchRouteDecision | null = null,
): RouteForm {
  const form: RouteForm = {
    track: defaultTrack,
    targetModule: resolveDefaultModule(project),
    branchName: routeDefaultBranch(project.rpNo),
    baseRef: ROUTE_DEFAULT_BASE_REF,
    projectName: "",
    stackTemplate: capabilities?.scaffoldTemplates[0] ?? "",
    owner: "",
    repoName: "",
    visibility: "PRIVATE",
    confirmRepoName: "",
    createGithub: false,
    ci: true,
    dockerCompose: true,
    scopeDiffersReason: "",
  };
  if (row === null) return form;
  const repo = /^https:\/\/github\.com\/([^/]+)\/([^/]+)$/.exec(row.repoUrl ?? "");
  const known = PLACEMENT_TARGETS.find((t) => t.id === row.targetModule)?.id;
  return {
    ...form,
    track: row.track,
    targetModule: known ?? form.targetModule,
    branchName: row.gitBranch ?? form.branchName,
    baseRef: row.baseRef ?? form.baseRef,
    projectName: row.track === "B" ? (row.implFsmProject ?? "") : "",
    stackTemplate: row.stackTemplate ?? form.stackTemplate,
    owner: repo?.[1] ?? "",
    repoName: repo?.[2] ?? "",
    visibility: row.repoVisibility ?? "PRIVATE",
    createGithub: row.steps.some((s) => s.step === "GH_REPO_CREATE"),
  };
}

/** 重試用的請求本文：由已存在的分流列推回（推不回的欄位用預設；輸入雜湊不符時由後端回 409 `route_conflict`，原因 `inputs_changed`）。 */
export function routeRowToRequest(row: ResearchRouteDecision, project: Pick<ResearchProjectDetail, "rpNo" | "targetScope" | "topic" | "slug">): ResearchRouteConfirmRequest {
  const form = initialRouteForm(project, row.track, undefined, row);
  return { ...toRouteRequest(form, false), retry: true };
}

/**
 * 分流精靈的停用說明（IFACE §8.3；TCS AT-961-16-5）：capabilities 缺項或角色不足時，受影響控件停用並顯示這裡的文字。
 * 這是畫面字樣的單一登記處（元件只取值、不內嵌第二份；git、gh 是指令名）。住在這裡而不是 `lib/help/research-workspace.ts`：說明頁模組恰好匯出一個帶 id 的 `PageHelp`（registry.test.ts 的鎖），且說明頁文字受英文白名單約束。
 * 鍵與 `RouteBlockCode` 對映，另加兩個角色鍵。
 */
export const ROUTE_DISABLED_TEXT = {
  git: "此部署找不到 git，無法分流",
  repo: "此部署無法寫入 monorepo（容器模式）；請改用本機模式",
  gh: "找不到 gh；可先建本地專案，之後自行推送",
  scaffold: "尚未設定 BRIDGE_SCAFFOLD_ROOT 或無可用範本",
  "mock-only": "容器模式只跑 mock claude 的驗收；真分流限本機模式",
  /** 非 ADMIN 的「確認執行」「重試」停用說明（OPERATOR；沿 CenterEntryView 體例，含「權限不足」） */
  adminOnly: "權限不足：僅 ADMIN 可確認執行與重試",
  /** VIEWER 的所有寫入類控件（含預演）停用說明 */
  viewer: "權限不足（唯讀角色）",
} as const;

// ── 步驟 4 前半（FR-R2P-14、19-4；TCS-ResearchToPRD-P1-20261107 AT-961-18-*）：拆解、覆蓋、豁免、簽核、TCS 草擬、執行閘 ──────────────

/** 人工豁免理由字數上限（契約 §1.3：1～500 字；以 code point 計）。 */
export const WAIVER_REASON_MAX = 500;

/** 豁免理由是否有效：去頭尾空白後 1～500 字；無效回欄位錯誤說明，有效回 null。 */
export function waiverReasonError(reason: string): string | null {
  const length = [...reason.trim()].length;
  if (length === 0) return "請填一句豁免理由";
  if (length > WAIVER_REASON_MAX) return `豁免理由最多 ${WAIVER_REASON_MAX} 字`;
  return null;
}

export type DecompositionTaskNode = { id: string; name: string; coversAc: string[] };
export type DecompositionGoalNode = { id: string; name: string; tasks: DecompositionTaskNode[] };

const textOf = (value: unknown): string => (typeof value === "string" ? value : typeof value === "number" ? String(value) : "");
const stringList = (value: unknown): string[] => (Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : []);

/** 拆解樹（`goals[].tasks[]`）的防禦式整形：鍵可能是 snake_case 或 camelCase（PRD §5.1.6 原樣或轉換後），缺欄一律退成空字串與空陣列、不丟例外。 */
export function decompositionTree(goals: ReadonlyArray<Record<string, unknown>> | null | undefined): DecompositionGoalNode[] {
  return (goals ?? []).map((goal, gi) => {
    const tasks = Array.isArray(goal.tasks) ? (goal.tasks as Array<Record<string, unknown>>) : [];
    return {
      id: textOf(goal.goal_id ?? goal.goalId) || `G-${gi + 1}`,
      name: textOf(goal.name),
      tasks: tasks.map((task, ti) => ({
        id: textOf(task.task_id ?? task.taskId) || `T-${gi + 1}-${ti + 1}`,
        name: textOf(task.name),
        coversAc: stringList(task.covers_ac ?? task.coversAc),
      })),
    };
  });
}

/** 樹內 task 總數（與 `tasksCount` 對照用）。 */
export function countTasks(tree: readonly DecompositionGoalNode[]): number {
  return tree.reduce((sum, g) => sum + g.tasks.length, 0);
}

export type CoverageView = {
  total: number;
  covered: number;
  uncovered: string[];
  /** 覆蓋矩陣的列（所有 AC：被涵蓋者取自樹、未覆蓋者取自 `coverage.uncovered`；依字串序） */
  acs: string[];
  /** 未覆蓋且已有有效豁免理由者（輸入優先於已存的豁免） */
  waived: string[];
  /** 未覆蓋且豁免理由尚缺或無效者：非空即簽核停用 */
  pending: string[];
  /** 輸入了但無效的未覆蓋 AC → 欄位錯誤說明 */
  errors: Record<string, string>;
  /** 簽核條件：未覆蓋者清零，或各有有效豁免 */
  complete: boolean;
};

/**
 * 覆蓋視圖（AC-R2P-14-2、14-3）：未覆蓋者逐一列出；簽核在「未覆蓋清零或各有一句有效豁免理由」前停用。
 * `inputs` 是使用者正在輸入的豁免理由（AC → 文字）；沒輸入的 AC 取已存的 `decomposition.waivers`。純函式。
 */
export function coverageView(decomposition: Pick<ResearchDecomposition, "coverage" | "goals" | "waivers">, inputs: Readonly<Record<string, string>> = {}): CoverageView {
  const { total, covered, uncovered } = decomposition.coverage;
  const tree = decompositionTree(decomposition.goals);
  const acSet = new Set<string>(uncovered);
  for (const g of tree) for (const t of g.tasks) for (const ac of t.coversAc) acSet.add(ac);
  const stored = new Map(decomposition.waivers.map((w) => [w.ac, w.reason] as const));
  const waived: string[] = [];
  const pending: string[] = [];
  const errors: Record<string, string> = {};
  for (const ac of uncovered) {
    const reason = inputs[ac] ?? stored.get(ac) ?? "";
    const error = waiverReasonError(reason);
    if (error === null) waived.push(ac);
    else {
      pending.push(ac);
      if (reason !== "") errors[ac] = error;
    }
  }
  return { total, covered, uncovered: [...uncovered], acs: [...acSet].sort(), waived, pending, errors, complete: pending.length === 0 };
}

/** 覆蓋矩陣：欄為 task、列為 AC，`cells[i][j]` 表示第 j 個 task 涵蓋第 i 個 AC（每個 task 一個 Set，200×24 不重複掃描）。 */
export function coverageMatrix(tree: readonly DecompositionGoalNode[], acs: readonly string[]): { tasks: DecompositionTaskNode[]; cells: boolean[][] } {
  const tasks = tree.flatMap((g) => g.tasks);
  const sets = tasks.map((t) => new Set(t.coversAc));
  return { tasks, cells: acs.map((ac) => sets.map((s) => s.has(ac))) };
}

/** 「SCR 進行中」標籤（AC-R2P-19-4 前端文字半）：只在 `SCR_OPEN` 相態出現；發起鈕與橫幅屬 P2。 */
export function scrBadge(phase: string): { visible: boolean; label: string } {
  return phase === "SCR_OPEN" ? { visible: true, label: FLOW_PHASE_LABEL.SCR_OPEN } : { visible: false, label: "" };
}

/** TCS 草擬四態（取自 `flow.effective`；`failed`＝階段失敗）。 */
export type TcsStage = "none" | "drafting" | "pending" | "frozen" | "failed";
/** 內環 TCS 已凍結之後的相態（讀端衍生，D-125；`BUILD_READY` 起都算已凍結）。 */
const TCS_FROZEN_PHASES: readonly string[] = ["BUILD_READY", "BUILDING", "HEALING", "AWAITING_HUMAN", "RELEASE_PENDING", "DELIVERED"];

export function tcsStage(phase: string, status: string): TcsStage {
  if (TCS_FROZEN_PHASES.includes(phase)) return "frozen";
  if (phase === "TCS_DRAFTING") return status === "FAILED" ? "failed" : "drafting";
  if (phase === "TCS_PENDING") return "pending";
  return "none";
}

/** `tcs_invalid` 失敗的缺項說明：`flow_detail` 以 `tcs_invalid` 起頭時回其後文字（純文字顯示），否則 null。 */
export function tcsInvalidText(detail: string): string | null {
  if (!detail.startsWith("tcs_invalid")) return null;
  return detail
    .slice("tcs_invalid".length)
    .replace(/^[:：\s]+/, "")
    .trim();
}

/** `tcs-draft` 啟動前置未成立時 409 `details.unmet[]` 的項名（⚖P1-11）對中文。 */
export const TCS_UNMET_LABEL: Readonly<Record<string, string>> = {
  route_not_succeeded: "分流尚未完成",
  inner_key_not_adopted: "內環鍵尚未採納基線",
  decomposition_missing: "尚未觸發拆解",
  // P2：SCG 登錄與 Tag 的前置（IFACE §2.1、§6.2）
  tasks_incomplete: "仍有任務未完成或未跳過",
  rtm_below_100: "追溯覆蓋率未達 100%",
  rtm_unavailable: "尚無追溯資料（RTM）",
  not_release_ready: "狀態機尚未達 RELEASE_READY",
  scr_open: "規格變更進行中",
};

/** 取 `details.unmet[]`（項為字串，或帶 `item`／`name` 的物件）轉中文；沒有就回空陣列。 */
export function unmetLabels(error: unknown): string[] {
  if (!(error instanceof ApiError)) return [];
  const raw = error.details?.unmet;
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    const key = typeof entry === "string" ? entry : typeof entry === "object" && entry !== null ? textOf((entry as Record<string, unknown>).item ?? (entry as Record<string, unknown>).name) : "";
    return TCS_UNMET_LABEL[key] ?? (key === "" ? "未知前置" : key);
  });
}

/** 拆解狀態中文（`IMPORTED` 於 P1 不使用，D-113，仍登記以免顯示英文原值）。 */
export const DECOMPOSITION_STATUS_LABEL: Readonly<Record<string, string>> = {
  DRAFTED: "草稿（待簽核）",
  SCG_PASSED: "已通過預檢（待簽核）",
  FROZEN: "已凍結",
  IMPORTED: "已匯入",
  SIGNED_OFF: "已簽核",
  REJECTED: "已駁回",
  STALE: "已過期",
};

/** 拆解 422 `details.violations[].rule` 的閘別說明（沿 `decompose.py` 的 `gate` 值，另加簽核的 `uncovered_ac`；IFACE §1.4、§1.8）。 */
export const DECOMPOSITION_RULE_LABEL: Readonly<Record<string, string>> = {
  max_steps: "單次拆解步驟超過上限，系統不截斷也不自動修剪，請按目標分批拆解",
  cycle: "任務之間的依賴有環，無法排出執行順序",
  empty_prompt: "有任務的提示詞是空的",
  brain_failed: "拆解用的模型呼叫失敗，請稍後重試",
  brain_unsupported: "目前的部署不支援這種拆解方式",
  uncovered_ac: "仍有驗收條件沒被任何任務涵蓋，也沒有豁免理由",
};

/**
 * 拆解與簽核錯誤的逐行說明（純文字）：422 結構化錯誤逐筆列「閘別 rule：說明」；其餘退回 `researchErrorText`。
 * 回傳至少一行（不回空陣列，面板才不會顯示空白）。
 */
export function decompositionErrorLines(error: unknown): string[] {
  if (error instanceof ApiError && error.status === 422) {
    const raw = error.details?.violations;
    const lines = Array.isArray(raw)
      ? raw
          .map((v) => (typeof v === "object" && v !== null ? textOf((v as Record<string, unknown>).rule) : ""))
          .filter((rule) => rule !== "")
          .map((rule) => `閘別 ${rule}：${DECOMPOSITION_RULE_LABEL[rule] ?? "未登記的檢查"}`)
      : [];
    if (lines.length > 0) return lines;
  }
  return [researchErrorText(error)];
}

/** 步驟 4 前半面板的停用說明（單一登記處，比照 `ROUTE_DISABLED_TEXT`；三道鎖的文字與後端 409 一致）。 */
export const BUILD_DISABLED_TEXT = {
  viewer: READONLY_TITLE,
  completed: "這一步已完成，唯讀",
  /** `flow_phase=SCR_OPEN`（後端 409 `scr_open`；D-118） */
  scrOpen: "規格變更中：請先完成或撤回規格變更",
  needDecomposition: "需先完成分流並觸發拆解",
  uncovered: "仍有未覆蓋的驗收條件，請補豁免理由",
  /** 草稿未經人工審批（後端 409 `fsm_state_conflict` 的前端文字半） */
  unsigned: "草稿未經人工審批，不能執行",
  tcsUnfrozen: "測試規格尚未凍結，不能執行",
  stale: "PRD 已更新，拆解已過期；請重新拆解並再簽核",
  signed: "拆解已簽核，唯讀",
} as const;

/**
 * 執行連結的閘（AC-R2P-14-3、14-5；PRD FR-15-2 的前端文字半）：回第一個擋住的原因鍵，全通過回 null。
 * 順序固定：規格變更中 → 拆解過期 → 草稿未簽核 → 測試規格未凍結。
 */
export function executionBlock(input: { scrOpen: boolean; decomposition: Pick<ResearchDecomposition, "status" | "stale"> | null; tcsFrozen: boolean }): keyof typeof BUILD_DISABLED_TEXT | null {
  if (input.scrOpen) return "scrOpen";
  const d = input.decomposition;
  if (d === null) return "needDecomposition";
  if (d.stale || d.status === "STALE") return "stale";
  if (d.status !== "SIGNED_OFF") return "unsigned";
  if (!input.tcsFrozen) return "tcsUnfrozen";
  return null;
}

// ── ResearchToPRD P2（看板、自癒、終端、決策彈窗、SCG 登錄、SCR UI；TCS-ResearchToPRD-P2-20261107 AT-962-11～15）─────────────────────────────
// 純函式與常數（FE-P2A 獨占；FE-P2B 只 import）。元件只負責畫；數字邊界與文案一律取這裡。

/** 看板 SSE 去抖與「幀到 DOM」上限的單一常數（IFACE §1.5；AT-962-11-3、11-E-3；KanbanBoard 與測試共讀，不各寫一份）。 */
export const KANBAN_DEBOUNCE_MS = 100;
export const KANBAN_SSE_TO_DOM_MAX_MS = 500;
/** 終端窗格開合（localStorage）與決策彈窗「稍後處理」（sessionStorage；⚖P2-10）的鍵。 */
export const TERMINAL_OPEN_STORAGE_KEY = "research.terminal.open";
export const DECISION_SNOOZE_STORAGE_KEY = "research.decision.snoozed";

export const KANBAN_COLUMN_ORDER = ["decompose", "tcs", "implement", "healing", "regression"] as const;
export type KanbanColumnKey = (typeof KANBAN_COLUMN_ORDER)[number];
export const KANBAN_COLUMN_LABEL: Readonly<Record<KanbanColumnKey, string>> = {
  decompose: "Task 拆解",
  tcs: "測試規格產生",
  implement: "程式碼實作",
  healing: "自癒修復",
  regression: "回歸驗收",
};
/** 完成判定：`unknown`＝內環 FSM 衍生欄量不到（Bridge 不可達），不猜成 false 也不猜成 true（AT-962-11-1、11-E-2）。 */
export type KanbanDone = boolean | "unknown";
export type KanbanColumnView = { key: KanbanColumnKey; label: string; done: KanbanDone };

/**
 * 看板五欄的完成判定（IFACE §1.2；與後端同一判定）：
 * 拆解＝已簽核且未過期；測試規格＝階段 2 已凍結（FSM 欄）；實作＝任務總數大於 0 且完成加跳過等於總數；
 * 自癒＝無重試中步驟且無升級任務；回歸＝RTM 100% 且完全覆蓋且 FSM 在 RELEASE_READY／RELEASE（FSM 欄）。
 */
export function kanbanColumns(dto: ResearchKanban): KanbanColumnView[] {
  const { decompose, tcs, implement, healing, regression } = dto.columns;
  const tasks = implement.tasks;
  const implDone: KanbanDone = implement.unknown === true ? "unknown" : tasks.total > 0 && tasks.completed + tasks.skipped === tasks.total;
  const regDone: KanbanDone =
    regression.unknown === true || regression.fsmState === null
      ? "unknown"
      : regression.rtm !== null && regression.rtm.acPct === 100 && regression.rtm.fullyCovered && (regression.fsmState === "RELEASE_READY" || regression.fsmState === "RELEASE");
  const done: Record<KanbanColumnKey, KanbanDone> = {
    decompose: decompose.status === "SIGNED_OFF" && !decompose.stale,
    tcs: tcs.unknown === true || tcs.stage2Frozen === null ? "unknown" : tcs.stage2Frozen,
    implement: implDone,
    healing: healing.retryingSteps === 0 && healing.escalatedTasks === 0,
    regression: regDone,
  };
  return KANBAN_COLUMN_ORDER.map((key) => ({ key, label: KANBAN_COLUMN_LABEL[key], done: done[key] }));
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
/** 標準 UUID（不分大小寫）；深連結 query 只收它，其餘一律忽略（路徑穿越、腳本、長度不符都不收；D-138 Q-11）。 */
export function isResearchUuid(value: string | null | undefined): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

/** 看板與步驟 4 面板開啟執行中心或監控中心的深連結：帶 `?researchId=<uuid>`（非 UUID 就不帶）。 */
export function consoleCenterHref(consoleProjectId: string, center: "execute" | "monitor", researchId: string | null | undefined): string {
  const base = `/projects/${encodeURIComponent(consoleProjectId)}/${center}`;
  return isResearchUuid(researchId) ? `${base}?researchId=${researchId}` : base;
}

/** Bridge 不可達橫幅文字（AT-962-11-7）。 */
export function kanbanStaleBanner(snapshotAt: string | null): string {
  return `Engine Bridge 無法連線，以下為 ${snapshotAt ?? "未知時間"} 的 DB 快照`;
}

// 決策彈窗（AC-18-2）──
export const DECISION_LABEL: Readonly<Record<string, string>> = { APPROVE: "通過", REJECT: "拒絕", RETRY: "重試", SKIP: "跳過" };
export const DECISION_ORDER = ["APPROVE", "REJECT", "RETRY", "SKIP"] as const;
/** 決定按鈕：只渲染 `allowedDecisions` 內且為已知決定者，順序固定。 */
export function decisionButtons(allowed: readonly string[]): string[] {
  return DECISION_ORDER.filter((d) => allowed.includes(d));
}
/** 決策彈窗的去重鍵：review-request 與待審取 `reviewId`；alert 幀無 reviewId 時用幀 seq（IFACE §5）。 */
export function decisionKey(input: { reviewId?: string | null; alertSeq?: number | string | null }): string | null {
  if (typeof input.reviewId === "string" && input.reviewId !== "") return `review:${input.reviewId}`;
  if (input.alertSeq !== undefined && input.alertSeq !== null && input.alertSeq !== "") return `alert:${String(input.alertSeq)}`;
  return null;
}

/** 彈窗項目：待審清單項與串流幀統一成這個形狀。`reviewId` 為 null＝引擎事件（只顯示，沒有可送出的決定）。 */
export type DecisionItem = {
  key: string;
  reviewId: string | null;
  runId: string | null;
  kind: string;
  taskId: string | null;
  reason: string;
  allowedDecisions: string[];
};
export function decisionKindLabel(kind: string): string {
  return kind === "ESCALATED" ? "自癒重試耗盡（已升級，等待人工決定）" : kind === "ALERT" ? "引擎升級事件" : "Agent 請求審核";
}
/**
 * 步驟 5「交付」畫面字樣的單一出處（FE-P2A 一次宣告；FE-P2B 的 DeliverPanel／TraceabilityTable／ReleaseActions／TagConfirmDialog／PrConfirmDialog 一律 import 這裡，不各寫一份）：
 * 說明登記表（`lib/help/research-workspace.ts`）的欄位名逐字引用這些字樣，出處鎖到本檔找得到它們。
 */
export const DELIVER_LABEL = {
  traceability: "追溯表",
  uncovered: "未覆蓋",
  createTag: "建立 Tag",
  pushRemote: "推送到遠端",
  createPr: "建立 PR",
  openLocal: "開啟本地專案",
  records: "交付紀錄",
} as const;

/**
 * Tag 確認框的欄位邊界與說明（D-157 單一來源；FE-P2B 的 TagConfirmDialog／ReleaseActions／PrConfirmDialog 一律 import 這裡）：
 * `TAG_NAME_PATTERN` 與 Bridge `gitops.valid_semver`、console-api 的 `tagName` 正規式逐字相同（TCS-ResearchToPRD-P2 §5.1；`research.test.ts` 比對 TCS 檔），長度至多 64。
 */
export const TAG_NAME_PATTERN = /^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$/;
export const TAG_NAME_MAX = 64;
export const TAG_MESSAGE_MAX = 200;
export const TAG_RULE_TEXT = "版本號須符合 semver，例如 v1.2.3 或 1.2.3-rc.1（最多 64 字）";
/** 非 ADMIN 的「建立 Tag」「建立 PR」停用說明（OPERATOR；含「權限不足」，沿 `GateRegisterDialog` 的「僅 ADMIN 可登錄 SCG」體例）。 */
export const TAG_ADMIN_ONLY_TEXT = "權限不足：僅 ADMIN 可建立 Tag";
export const PR_ADMIN_ONLY_TEXT = "權限不足：僅 ADMIN 可建立 PR";
// SCG 登錄（AC-15-6）──
export const GATE_REASON_MAX = 500;
export const GATE_REPORT_REF_MAX = 300;
export const GATE_LABEL: Readonly<Record<ResearchGateName, string>> = {
  PR_REVIEW: "SCG-4 程式碼審查（PR_REVIEW）",
  RTM_VERIFY: "SCG-5 追溯驗證（RTM_VERIFY）",
  RELEASE_READY: "發布就緒（RELEASE_READY）",
};
export const GATE_INDEPENDENCE_TEXT = "我確認審查者未參與規格與實作";
export type GateFormInput = { gate: ResearchGateName; result: ResearchGateResult; reason: string; reportRef: string; independent: boolean };
export type GateFormView = {
  resultOptions: ResearchGateResult[];
  reasonRequired: boolean;
  independenceRequired: boolean;
  reasonError: string | null;
  reportRefError: string | null;
  independenceError: string | null;
  canSubmit: boolean;
};

/** SCG 登錄表單判定：RELEASE_READY 只有 FAIL；FAIL 必填理由（1～500）；報告參照 ≤300；PR_REVIEW 必須勾獨立聲明。 */
export function gateRegisterView(input: GateFormInput): GateFormView {
  const resultOptions: ResearchGateResult[] = input.gate === "RELEASE_READY" ? ["FAIL"] : ["PASS", "FAIL"];
  const result = input.gate === "RELEASE_READY" ? "FAIL" : input.result;
  const reasonRequired = result === "FAIL";
  const reasonLen = [...input.reason.trim()].length;
  const reasonError = reasonLen > GATE_REASON_MAX ? `理由最多 ${GATE_REASON_MAX} 字` : reasonRequired && reasonLen === 0 ? "FAIL 必須填理由" : null;
  const reportRefError = [...input.reportRef.trim()].length > GATE_REPORT_REF_MAX ? `報告參照最多 ${GATE_REPORT_REF_MAX} 字` : null;
  const independenceRequired = input.gate === "PR_REVIEW";
  const independenceError = independenceRequired && !input.independent ? "必須先勾選審查者獨立聲明" : null;
  return {
    resultOptions,
    reasonRequired,
    independenceRequired,
    reasonError,
    reportRefError,
    independenceError,
    canSubmit: reasonError === null && reportRefError === null && independenceError === null,
  };
}

export type GateErrorView = { text: string; unmet: string[]; drift: string[]; offerScr: boolean };
/** SCG 登錄失敗的呈現：文案取登記表；409 unmet 逐項中文；422 digest_mismatch 列出每個漂移路徑並可發起 SCR；403 ACCESS_DENIED 用通用權限不足文案。 */
export function gateErrorView(error: unknown): GateErrorView {
  if (error instanceof ApiError && error.status === 403 && error.reason === "ACCESS_DENIED") return { text: "權限不足：僅 ADMIN 可登錄 SCG", unmet: [], drift: [], offerScr: false };
  const drift: string[] = [];
  if (error instanceof ApiError && error.reason === RESEARCH_REASONS.DIGEST_MISMATCH) {
    const raw = error.details?.drift;
    if (Array.isArray(raw)) {
      for (const entry of raw) {
        const path = typeof entry === "string" ? entry : typeof entry === "object" && entry !== null ? textOf((entry as Record<string, unknown>).path) : "";
        if (path !== "") drift.push(path);
      }
    }
  }
  const text = error instanceof ApiError && error.reason === RESEARCH_REASONS.DIGEST_MISMATCH ? "已凍結的規格檔與凍結時的摘要不一致，請檢查下列檔案；要改規格請發起 SCR" : researchErrorText(error);
  return { text, unmet: unmetLabels(error), drift, offerScr: drift.length > 0 || (error instanceof ApiError && error.reason === RESEARCH_REASONS.DIGEST_MISMATCH) };
}

// SCR 表單（AC-19-1、19-5）──
export const SCR_REASON_MAX = 500;
export const SCR_SECTIONS_MAX = 20;
export const SCR_SECTION_ITEM_MAX = 200;
export const SCR_EVIDENCE_MAX = 500;
/**
 * 「受影響章節」可送出的字面（D-168）：章節**編號**（標題行 `## 5`、`### 5.2 …` 的編號）與 AC 編號。
 * 鏡像 Bridge `app/research/scr.py` 的 `_HEADING_NO_RE`／`_AC_RE`（Bridge 只認這兩種字面，其餘一律 422 `affected_unknown`）；
 * 兩邊改一處必同步，跨語言對拍鎖＝共用夾具 `engine-bridge/tests/fixtures/research/scr_section_options_cases.json`。
 * `\w` 在 Python 是 Unicode、在 JS 是 ASCII，故這裡以 `\p{L}\p{N}_` 加 `u` 旗標對齊。
 */
export const SCR_HEADING_NO_RE = /^#{1,6}\s+(\d+(?:\.\d+)*)[.\s、]/u;
export const SCR_AC_RE = /(?<![\p{L}\p{N}_-])(AC-[0-9][0-9A-Za-z-]*)(?![\p{L}\p{N}_-])/gu;
const SCR_OPTION_LABEL_MAX = 60;

export interface ScrSectionOption {
  /** 送出 `affectedSections` 的元素：章節編號或 AC 編號本身。 */
  value: string;
  /** 顯示文字（編號＋標題，截短）；不送出。 */
  label: string;
}

/** 凍結 PRD → 受影響章節選項（依出現順序、去重；章節編號在前、AC 編號在後；至多 200 項、每項值 ≤200 字）。 */
export function scrSectionOptions(content: string | undefined): ScrSectionOption[] {
  if (!content) return [];
  const out = new Map<string, string>();
  for (const line of content.split(/\r?\n/)) {
    const m = SCR_HEADING_NO_RE.exec(line);
    if (m === null || out.has(m[1])) continue;
    const title = line.slice(m[0].length).trim();
    const label = `${m[1]} ${title}`.trim();
    out.set(m[1], [...label].length > SCR_OPTION_LABEL_MAX ? `${[...label].slice(0, SCR_OPTION_LABEL_MAX).join("")}…` : label);
  }
  for (const m of content.matchAll(SCR_AC_RE)) if (!out.has(m[1])) out.set(m[1], m[1]);
  return [...out]
    .filter(([value]) => [...value].length <= SCR_SECTION_ITEM_MAX)
    .slice(0, 200)
    .map(([value, label]) => ({ value, label }));
}

export const SCR_REASON_CLASSES = ["PRD 缺漏證據", "AC 模糊", "需求變更", "技術不可行", "其他"] as const;
export const SCR_KIND_TEXT: Readonly<Record<ResearchScrKind, string>> = {
  MINOR: "小幅變更：在目前研究專案內修訂，舊凍結版保留、新摘要入庫；同一專案有次數上限",
  MAJOR: "大幅變更：另開後繼研究專案（導向新專案），原專案凍結內容不動",
};
export const SCR_SOURCE_LABEL: Readonly<Record<string, string>> = { HUMAN: "人工發起", REVIEW_FINDING: "審查發現", SCG4: "SCG-4 未通過", HEALING_FAILED: "自癒失敗" };
export type ScrFormInput = { kind: ResearchScrKind; sourceKind: string; reason: string; reasonClass: string; affectedSections: string[]; evidenceUrl: string };
export type ScrFormErrors = { reason: string | null; reasonClass: string | null; affectedSections: string | null; evidenceUrl: string | null };

/** 證據連結：只接受 `https://`（含主機）、≤500；空字串＝不填，合法。 */
export function evidenceUrlError(raw: string): string | null {
  const value = raw.trim();
  if (value === "") return null;
  if ([...value].length > SCR_EVIDENCE_MAX) return `證據連結最多 ${SCR_EVIDENCE_MAX} 字`;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname !== "" ? null : "證據連結只接受 https://";
  } catch {
    return "證據連結只接受 https://";
  }
}

export function scrFormView(input: ScrFormInput): { errors: ScrFormErrors; valid: boolean; reasonRemaining: number } {
  const reasonLen = [...input.reason.trim()].length;
  const errors: ScrFormErrors = {
    reason: reasonLen === 0 ? "請填變更理由" : reasonLen > SCR_REASON_MAX ? `理由最多 ${SCR_REASON_MAX} 字` : null,
    reasonClass: (SCR_REASON_CLASSES as readonly string[]).includes(input.reasonClass) ? null : "請選理由分類",
    affectedSections:
      input.affectedSections.length > SCR_SECTIONS_MAX
        ? `受影響章節最多 ${SCR_SECTIONS_MAX} 項`
        : input.affectedSections.some((s) => [...s].length > SCR_SECTION_ITEM_MAX || s.trim() === "")
          ? `每項章節 1～${SCR_SECTION_ITEM_MAX} 字`
          : null,
    evidenceUrl: evidenceUrlError(input.evidenceUrl),
  };
  return { errors, valid: Object.values(errors).every((e) => e === null), reasonRemaining: SCR_REASON_MAX - reasonLen };
}

/** 422 `details.violations[{field, rule}]` 依欄位分組（回顯到欄位下）。 */
export function scrViolationsByField(error: unknown): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  if (!(error instanceof ApiError)) return out;
  const raw = error.details?.violations;
  if (!Array.isArray(raw)) return out;
  for (const v of raw) {
    if (typeof v !== "object" || v === null) continue;
    const field = textOf((v as Record<string, unknown>).field);
    const rule = textOf((v as Record<string, unknown>).rule);
    if (field === "") continue;
    (out[field] ??= []).push(rule === "" ? "未通過檢查" : rule);
  }
  return out;
}

/** ANSI 控制序列（CSI 與孤立 ESC）：終端窗格在餵給共用日誌元件之前剝掉，使可見文字不殘留 `ESC[`（AT-962-13-3；LiveLogCard 本包不改）。 */
const ANSI_PATTERN = new RegExp(String.raw`\u001b\[[0-9;?]*[ -/]*[@-~]|\u001b`, "g");
export function stripAnsi(text: string): string {
  return text.replace(ANSI_PATTERN, "");
}
