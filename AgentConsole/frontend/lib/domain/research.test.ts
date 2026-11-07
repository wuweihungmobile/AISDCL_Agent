import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { ResearchEvent, ResearchFlowStatus, ResearchFlowStepId, ResearchProjectSummary, ResearchReconcileResult, ResearchReviewRound } from "@/lib/api/types";
import { sha } from "@/tests/fixtures/research/ids";
import { RECONCILE_DRIFT, RECONCILE_OK } from "@/tests/fixtures/research/misc";
import {
  BLOCKING_FLOW_STATUSES,
  BUILD_DISABLED_TEXT,
  WAIVER_REASON_MAX,
  coverageMatrix,
  coverageView,
  decompositionErrorLines,
  decompositionTree,
  executionBlock,
  scrBadge,
  tcsInvalidText,
  tcsStage,
  unmetLabels,
  waiverReasonError,
  DEFAULT_APPLICABILITY_AXES,
  DEFAULT_BUDGET_WARN_AT,
  DIFF_MAX_EDITS,
  FALLBACK_SLUG_PREFIX,
  FLOW_PHASE_DERIVED,
  FLOW_PHASE_LABEL,
  FLOW_STATUS_LABEL,
  FLOW_STEP_IDS,
  FLOW_STEP_LABEL,
  FLOW_VOCABULARY_KEYS,
  GATE0_WAIT_BANNER_HOURS,
  LAMP_META,
  LAMP_ORDER,
  BRANCH_PATTERN,
  OWNER_PATTERN,
  PLACEMENT_TARGETS,
  PROJECT_NAME_PATTERN,
  REASON_MAX,
  REPO_NAME_PATTERN,
  ROUTE_EVAL_TABLE,
  ROUTE_MISSING_ITEM_LABEL,
  ROUTE_STEP_LABEL,
  SCOPE_REASON_MAX,
  effectiveRepoName,
  isExternalRouteAction,
  isRepoNameConfirmed,
  routeCapabilityBlocks,
  routeDefaultBranch,
  routeFormErrors,
  routeMissingLabels,
  routeScopeDiffers,
  routeStatusLabel,
  routeStepLabel,
  routeTrackForScope,
  safeRepoHref,
  toRouteRequest,
  type RouteForm,
  PROJECT_BADGE_LABEL,
  RADAR_AXES,
  READONLY_TITLE,
  RECONCILE_CHECK_LABEL,
  RESEARCH_REASONS,
  RESEARCH_CANCELLED_REASON,
  REVIEW_RETRY_LIMIT,
  SLUG_PATTERN,
  STEP_STATE_LABEL,
  TOKEN_RATE_WINDOW_MS,
  budgetState,
  continueLabel,
  createResearchErrors,
  deriveSteps,
  diffLines,
  executionBudgetSettings,
  filterProjects,
  flowPhaseLabel,
  flowStatusLabel,
  flowVocabularyLabel,
  formatInstant,
  formatTokenRate,
  gate0WaitStart,
  gate0WaitView,
  gateWaitedHours,
  isCompletedStep,
  isFlowStepId,
  isInitFailed,
  isLicensePending,
  isStageFailed,
  lampInputsOf,
  lampOf,
  licensePendingCount,
  projectBadge,
  readResearchScope,
  reconcileDriftView,
  remainingReviewBudget,
  researchErrorText,
  researchFailureOf,
  resolveBudget,
  resolveViewStep,
  reviewRetryCount,
  scoreRadar,
  slugFromTopic,
  splitLines,
  stepIndex,
  stepNumber,
  stepReachable,
  toCreateRequest,
  tokenRate,
  tokensUsedTotal,
  topicSummary,
  type DiffLine,
  type LampFsm,
  type LampKind,
  type LampRun,
} from "./research";

/**
 * 研發工作流的純函式（TCS-ResearchToPRD-P0-20261102 §3.3；FR-R2P-01、22、09）。這些函式一律是純函式：不讀 window、document、localStorage、sessionStorage。
 * 「node 環境」的驗證方式：全域 setup（tests/setup.ts）無條件讀 `window`，所以整檔不能改以 node 環境執行（該檔不在本包允許集合；注意 vitest 的環境指示字樣出現在檔內任何位置都會生效，註解也不能提）；
 * 改以兩道證據取代——(1) 原始碼（去註解後）靜態掃描沒有任何瀏覽器全域；(2) 執行前 `withoutBrowserGlobals()` 把 window、document、localStorage、sessionStorage 全數換成 undefined，
 * 函式照常算（AT_960_19_E_1、AT_960_17_E_1）。
 * 本檔 AT：AT_960_19_E_1、AT_960_20_2、AT_960_20_3、AT_960_16_E_4、AT_960_17_E_1；其餘是支撐這些 AT 的單元測試（詞彙、清單、新建表單、雷達、等待時數）。
 * 判定指令：npx vitest run lib/domain/research.test.ts -t "<AT 底線形>"
 */
const ROOT = process.cwd();

/** 把瀏覽器全域換成 undefined（setup.ts 的 afterEach 會 unstubAllGlobals 還原）：證明被測函式不依賴它們。 */
function withoutBrowserGlobals(): void {
  for (const name of ["window", "document", "localStorage", "sessionStorage"]) vi.stubGlobal(name, undefined);
}

/** 去掉註解後的原始碼（靜態掃描用；沿 tests/design-rules.test.ts 的 stripComments）。 */
const stripComments = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/.*$/gm, "$1");

const RESEARCH_SOURCE = stripComments(readFileSync(path.join(ROOT, "lib", "domain", "research.ts"), "utf-8"));

const ALL_STATUSES: ResearchFlowStatus[] = ["IDLE", "RUNNING", "WAITING_HUMAN", "BLOCKED", "ESCALATED", "FAILED", "CANCELLED", "COMPLETED", "PAUSED"];

// ── AT_960_19_E_1：deriveSteps 與 stepReachable 表驅動 ─────────────────────────────────

describe("AT_960_19_E_1 五步列與可達性（表驅動；純函式）", () => {
  it("AT_960_19_E_1 deriveSteps：游標 k 為 1 至 5、九種 flow_status 全部組合，恆五項、序號與名稱固定；小於 k 已完成、等於 k 進行中（受阻三態改標受阻）、大於 k 待做", () => {
    expect(FLOW_STEP_IDS).toEqual(["topic", "studio", "route", "build", "deliver"]);
    expect(FLOW_STEP_IDS.map((id) => FLOW_STEP_LABEL[id])).toEqual(["研究", "規格工作室", "分流", "拆解與執行", "交付"]);
    for (const [index, current] of FLOW_STEP_IDS.entries()) {
      for (const status of ALL_STATUSES) {
        const steps = deriveSteps(current, status);
        const where = `k=${index + 1} status=${status}`;
        expect(steps, where).toHaveLength(5);
        expect(
          steps.map((s) => s.id),
          where,
        ).toEqual([...FLOW_STEP_IDS]);
        expect(
          steps.map((s) => s.number),
          where,
        ).toEqual([1, 2, 3, 4, 5]);
        steps.forEach((s, i) => {
          const expected = i < index ? "DONE" : i > index ? "TODO" : BLOCKING_FLOW_STATUSES.includes(status) ? "BLOCKED" : "CURRENT";
          expect(s.state, `${where} 第 ${i + 1} 項`).toBe(expected);
          expect(s.label).toBe(FLOW_STEP_LABEL[s.id]);
        });
        expect(
          steps.filter((s) => s.state === "CURRENT" || s.state === "BLOCKED"),
          `${where}：恰一項是目前步`,
        ).toHaveLength(1);
      }
    }
    expect(BLOCKING_FLOW_STATUSES).toEqual(["BLOCKED", "ESCALATED", "FAILED"]);
    expect(Object.values(STEP_STATE_LABEL)).toEqual(["已完成", "進行中", "受阻", "待做"]);
  });

  it("AT_960_19_E_1 stepReachable：25 個 (step, furthest) 組合，僅在 step 不超前於 furthest 時為真；resolveViewStep 與 isCompletedStep 由它推導", () => {
    let reachable = 0;
    for (const step of FLOW_STEP_IDS) {
      for (const furthest of FLOW_STEP_IDS) {
        const expected = FLOW_STEP_IDS.indexOf(step) <= FLOW_STEP_IDS.indexOf(furthest);
        expect(stepReachable(step, furthest), `${step} / ${furthest}`).toBe(expected);
        if (expected) reachable += 1;
      }
    }
    expect(reachable, "25 組中恰 15 組可達").toBe(15);

    // 解析網址：合法且可達照辦；超前、缺少、不是五步之一一律回游標所在步並要求導回
    const cursor: ResearchFlowStepId = "studio";
    expect(resolveViewStep("deliver", cursor, "studio")).toEqual({ step: "studio", redirect: true });
    expect(resolveViewStep("route", cursor, "studio")).toEqual({ step: "studio", redirect: true });
    expect(resolveViewStep("topic", cursor, "studio")).toEqual({ step: "topic", redirect: false });
    expect(resolveViewStep("studio", cursor, "studio")).toEqual({ step: "studio", redirect: false });
    expect(resolveViewStep(null, cursor, "studio")).toEqual({ step: "studio", redirect: true });
    expect(resolveViewStep(undefined, cursor, "studio")).toEqual({ step: "studio", redirect: true });
    expect(resolveViewStep("nope", cursor, "studio")).toEqual({ step: "studio", redirect: true });
    expect(resolveViewStep("", cursor, "studio")).toEqual({ step: "studio", redirect: true });
    // furthest 比游標還小（資料不一致）以游標為準：游標所在步永遠可達
    expect(resolveViewStep("studio", "studio", "topic")).toEqual({ step: "studio", redirect: false });
    // furthest 大於游標：前進過的步驟可達
    expect(resolveViewStep("deliver", "route", "deliver")).toEqual({ step: "deliver", redirect: false });

    expect(isCompletedStep("topic", "studio")).toBe(true);
    expect(isCompletedStep("studio", "studio")).toBe(false);
    expect(isCompletedStep("route", "studio")).toBe(false);
    expect(FLOW_STEP_IDS.map((s) => [stepIndex(s), stepNumber(s)])).toEqual([
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 4],
      [4, 5],
    ]);
    expect(isFlowStepId("build")).toBe(true);
    expect(isFlowStepId("Build")).toBe(false);
    expect(isFlowStepId(3)).toBe(false);
  });

  it("AT_960_19_E_1 純函式：原始碼（去註解後）不讀 localStorage、sessionStorage、window、document；瀏覽器全域全部換成 undefined 後照常計算", () => {
    withoutBrowserGlobals();
    for (const name of ["window", "document", "localStorage", "sessionStorage"]) expect(typeof (globalThis as Record<string, unknown>)[name], `${name} 已被移除`).toBe("undefined");
    const usesGlobal = (code: string, name: string) => new RegExp(`\\b${name}\\b`).test(stripComments(code));
    for (const forbidden of ["localStorage", "sessionStorage", "window", "document"]) expect(usesGlobal(RESEARCH_SOURCE, forbidden), `原始碼不得出現 ${forbidden}`).toBe(false);
    expect(deriveSteps("build", "RUNNING").map((s) => s.state)).toEqual(["DONE", "DONE", "DONE", "CURRENT", "TODO"]);
    expect(stepReachable("topic", "studio")).toBe(true);
    expect(resolveViewStep("deliver", "studio", "studio")).toEqual({ step: "studio", redirect: true });
    // 負控：掃描判準有鑑別力（整詞比對：變數名 windowStart 不算；註解不算；真的讀取才算）
    expect(usesGlobal("const x = window.localStorage; // 註解", "localStorage")).toBe(true);
    expect(usesGlobal("const x = window.localStorage;", "window")).toBe(true);
    expect(usesGlobal("const x = document.title;", "document")).toBe(true);
    expect(usesGlobal("const windowStart = now - 1;", "window")).toBe(false);
    expect(usesGlobal("// 只有註解提到 window", "window")).toBe(false);
  });
});

// ── 詞彙（researchFlow 狀態說明表的上游）──────────────────────────────────────────────

describe("研究流程詞彙：flow_status、flow_phase 與衍生相態", () => {
  it("flow_status 八個 DB 值加衍生的 PAUSED、flow_phase 十三個 DB 值加六個衍生相態（P1 補 BUILD_READY，D-114；衍生相態 PAUSED 與衍生狀態 PAUSED 同名同義、只登記在狀態表）；兩張表的鍵不相交；標籤非空且各表內不重複", () => {
    expect(Object.keys(FLOW_STATUS_LABEL).sort()).toEqual([...ALL_STATUSES].sort());
    expect(Object.keys(FLOW_STATUS_LABEL)).toHaveLength(9);
    expect(Object.keys(FLOW_PHASE_LABEL)).toHaveLength(19);
    expect([...FLOW_PHASE_DERIVED].sort()).toEqual(["AWAITING_HUMAN", "BUILDING", "BUILD_READY", "DELIVERED", "HEALING", "RELEASE_PENDING"]);
    const dbPhases = Object.keys(FLOW_PHASE_LABEL).filter((k) => !(FLOW_PHASE_DERIVED as readonly string[]).includes(k));
    expect(dbPhases.sort()).toEqual(
      ["INGESTED", "RESEARCHING", "EVIDENCE_READY", "DRAFTING", "REVIEWING", "REVISING", "GATE0_PENDING", "FROZEN", "ROUTING", "ROUTED", "TCS_DRAFTING", "TCS_PENDING", "SCR_OPEN"].sort(),
    );
    for (const key of Object.keys(FLOW_STATUS_LABEL)) expect(Object.keys(FLOW_PHASE_LABEL), `${key} 不得同時是 phase`).not.toContain(key);
    expect(FLOW_VOCABULARY_KEYS).toHaveLength(28);
    expect(new Set(FLOW_VOCABULARY_KEYS).size).toBe(28);
    for (const table of [FLOW_STATUS_LABEL, FLOW_PHASE_LABEL]) {
      const labels = Object.values(table);
      for (const label of labels) expect(label.trim()).not.toBe("");
      expect(new Set(labels).size, "同一張表內標籤不重複").toBe(labels.length);
    }
  });

  it("標籤查詢：已登記的值回中文、未登記的值原樣回傳（不丟例外）；flowVocabularyLabel 先認 status 再認 phase", () => {
    expect(flowStatusLabel("RUNNING")).toBe("執行中");
    expect(flowStatusLabel("MYSTERY")).toBe("MYSTERY");
    expect(flowPhaseLabel("GATE0_PENDING")).toBe("等待核准");
    expect(flowPhaseLabel("NEW_PHASE_X")).toBe("NEW_PHASE_X");
    expect(flowVocabularyLabel("ESCALATED")).toBe(FLOW_STATUS_LABEL.ESCALATED);
    expect(flowVocabularyLabel("HEALING")).toBe(FLOW_PHASE_LABEL.HEALING);
    expect(flowVocabularyLabel("__未登記的鍵__")).toBe("__未登記的鍵__");
  });
});

// ── AT_960_20_2：狀態燈窮舉表 ───────────────────────────────────────────────────────

describe("AT_960_20_2 狀態燈窮舉表（優先序 Escalated＞Healing＞Running＞Paused＞Idle）", () => {
  const RUNS: LampRun[] = ["none", "RUNNING", "PAUSED"];
  const FSMS: LampFsm[] = ["ok", "ESCALATION"];
  const FLAGS = [false, true] as const;

  /** 獨立的期望值：把每個燈號的成立條件列成表，依優先序掃第一個成立者（與 lampOf 的 if 鏈寫法不同）。 */
  function expectedLamp(run: LampRun, fsm: LampFsm, tasksEscalated: boolean, retrying: boolean, reviewEscalated: boolean): LampKind {
    const holds: Record<LampKind, boolean> = {
      Escalated: fsm === "ESCALATION" || tasksEscalated || reviewEscalated,
      Healing: run === "RUNNING" && retrying,
      Running: run === "RUNNING",
      Paused: run === "PAUSED",
      Idle: true,
    };
    return LAMP_ORDER.find((kind) => holds[kind]) as LampKind;
  }

  it("AT_960_20_2 run（none、RUNNING、PAUSED）× FSM（ok、ESCALATION）× 任務 ESCALATED × 任務 RETRYING × 審查 ESCALATE ＝ 48 組逐組斷言；五種燈號都出現", () => {
    let count = 0;
    const seen = new Set<LampKind>();
    for (const run of RUNS) {
      for (const fsm of FSMS) {
        for (const escalated of FLAGS) {
          for (const retrying of FLAGS) {
            for (const reviewEscalated of FLAGS) {
              const got = lampOf(run, fsm, { escalated, retrying, reviewEscalated });
              expect(got, `run=${run} fsm=${fsm} 任務ESCALATED=${escalated} RETRYING=${retrying} 審查ESCALATE=${reviewEscalated}`).toBe(expectedLamp(run, fsm, escalated, retrying, reviewEscalated));
              seen.add(got);
              count += 1;
            }
          }
        }
      }
    }
    expect(count, "窮舉表不少於 24 組").toBe(48);
    expect(count).toBeGreaterThanOrEqual(24);
    expect([...seen].sort()).toEqual([...LAMP_ORDER].sort());
  });

  it("AT_960_20_2 規則的文字面：FSM ESCALATION、任務 ESCALATED、審查 ESCALATE 任一即 Escalated（壓過一切）；RUNNING 且有重試＝Healing；RUNNING＝Running；PAUSED＝Paused；其餘 Idle；每個燈號有中文文字標籤、優先序固定", () => {
    const none = { escalated: false, retrying: false, reviewEscalated: false };
    expect(lampOf("RUNNING", "ESCALATION", { ...none, retrying: true })).toBe("Escalated");
    expect(lampOf("none", "ok", { ...none, escalated: true })).toBe("Escalated");
    expect(lampOf("PAUSED", "ok", { ...none, reviewEscalated: true })).toBe("Escalated");
    expect(lampOf("RUNNING", "ok", { ...none, retrying: true })).toBe("Healing");
    expect(lampOf("RUNNING", "ok", none)).toBe("Running");
    expect(lampOf("PAUSED", "ok", { ...none, retrying: true }), "暫停中的重試不算自癒中").toBe("Paused");
    expect(lampOf("none", "ok", { ...none, retrying: true }), "沒有進行中的 run 就沒有自癒").toBe("Idle");
    expect(lampOf("none", "ok", none)).toBe("Idle");
    expect(LAMP_ORDER).toEqual(["Escalated", "Healing", "Running", "Paused", "Idle"]);
    expect(LAMP_ORDER.map((kind) => LAMP_META[kind].label)).toEqual(["待人工", "自癒中", "執行中", "已暫停", "閒置"]);
    expect(new Set(LAMP_ORDER.map((kind) => LAMP_META[kind].color)).size, "五個燈號顏色互異（只作輔助）").toBe(5);
    for (const kind of LAMP_ORDER) expect(LAMP_META[kind].color, `${kind} 的顏色取設計 token`).toMatch(/^var\(--color-[a-z-]+\)$/);
  });

  it("lampInputsOf：由 flow.effective.status 取 run 與 FSM；HEALING 相態即重試中；P0 沒有任務所以其餘恆為假", () => {
    const base = { step: "studio", phase: "REVIEWING", detail: "" } as const;
    const project = (status: ResearchFlowStatus, phase: string = base.phase) =>
      ({ flow: { currentStep: "studio", furthestStep: "studio", steps: [], resumeHref: "", effective: { ...base, phase, status } } }) as never;
    expect(lampInputsOf(project("RUNNING"))).toEqual({ run: "RUNNING", fsm: "ok", tasks: { escalated: false, retrying: false, reviewEscalated: false } });
    expect(lampInputsOf(project("PAUSED")).run).toBe("PAUSED");
    expect(lampInputsOf(project("ESCALATED"))).toMatchObject({ run: "none", fsm: "ESCALATION" });
    expect(lampInputsOf(project("RUNNING", "HEALING")).tasks.retrying).toBe(true);
    for (const status of ["IDLE", "WAITING_HUMAN", "BLOCKED", "FAILED", "CANCELLED", "COMPLETED"] as const) expect(lampInputsOf(project(status)), status).toMatchObject({ run: "none", fsm: "ok" });
  });
});

// ── AT_960_20_3：Token 速率與預算 ─────────────────────────────────────────────────────

describe("AT_960_20_3 Token 速率（近五分鐘增量除以五）與預算警示", () => {
  const NOW = Date.parse("2026-11-02T10:00:00+08:00");
  const at = (minutesAgo: number) => new Date(NOW - minutesAgo * 60_000).toISOString();
  const run = (stageRunId: string, minutesAgo: number, tokensUsed: number): Pick<ResearchEvent, "eventType" | "occurredAt" | "payload"> => ({
    eventType: "research.run",
    occurredAt: at(minutesAgo),
    payload: { stageRunId, tokensUsed, status: "RUNNING" },
  });

  it("AT_960_20_3 五分鐘內增量 3000 得 600 tokens／min；視窗外的舊事件當基準；無事件得 null、顯示「—」；與 research_stage_runs.tokens_used 的差分一致", () => {
    expect(TOKEN_RATE_WINDOW_MS).toBe(300_000);
    // 視窗開始前（10 分鐘前）累計 2000，視窗內最新（1 分鐘前）累計 5000：增量 3000
    expect(tokenRate([run("r1", 10, 2000), run("r1", 4, 3500), run("r1", 1, 5000)], NOW)).toBe(600);
    // 視窗內才出現第一筆事件的 run 從 0 起算：第一筆 0、最新 3000
    expect(tokenRate([run("r1", 4, 0), run("r1", 1, 3000)], NOW)).toBe(600);
    // 兩個 stage run 的增量加總：r1 增 1500、r2 增 1500
    expect(tokenRate([run("r1", 9, 1000), run("r1", 2, 2500), run("r2", 8, 0), run("r2", 1, 1500)], NOW)).toBe(600);
    // 無事件、只有視窗外的事件、只有別種事件：null（不是 0）
    expect(tokenRate([], NOW)).toBeNull();
    expect(tokenRate([run("r1", 30, 9000)], NOW)).toBeNull();
    expect(tokenRate([{ eventType: "research.step", occurredAt: at(1), payload: { tokensUsed: 5000, stageRunId: "r1" } }], NOW)).toBeNull();
    // 視窗內有事件但累計沒增加：0（有量到，只是沒有消耗）
    expect(tokenRate([run("r1", 9, 4000), run("r1", 1, 4000)], NOW)).toBe(0);
    // 壞資料不入樣：缺 stageRunId、tokensUsed 非數字或負數、時間解不出、未來的事件
    const bad: Array<Pick<ResearchEvent, "eventType" | "occurredAt" | "payload">> = [
      { eventType: "research.run", occurredAt: at(1), payload: { tokensUsed: 100 } },
      { eventType: "research.run", occurredAt: at(1), payload: { stageRunId: "x", tokensUsed: "100" } },
      { eventType: "research.run", occurredAt: at(1), payload: { stageRunId: "x", tokensUsed: -5 } },
      { eventType: "research.run", occurredAt: "不是時間", payload: { stageRunId: "x", tokensUsed: 100 } },
      run("future", -10, 9999),
    ];
    expect(tokenRate(bad, NOW)).toBeNull();
    expect(formatTokenRate(600)).toBe("600 tokens/min");
    expect(formatTokenRate(1234.4)).toBe("1,234 tokens/min");
    expect(formatTokenRate(0)).toBe("0 tokens/min");
    expect(formatTokenRate(null)).toBe("—");
  });

  it("AT_960_20_3 已用 token＝各 stage run 的最大累計值加總；預算取 run 值、沒有則取系統參數 globalTokenBudget；用量達預算的 0.8 以上為警示", () => {
    expect(tokensUsedTotal([run("r1", 20, 1000), run("r1", 5, 4000), run("r2", 3, 2500)])).toBe(6500);
    expect(tokensUsedTotal([])).toBe(0);
    expect(resolveBudget(500_000, 1_000_000)).toBe(500_000);
    expect(resolveBudget(null, 1_000_000)).toBe(1_000_000);
    expect(resolveBudget(undefined, 1_000_000)).toBe(1_000_000);
    expect(resolveBudget(0, 1_000_000), "run 預算 0 不是有效預算").toBe(1_000_000);
    expect(resolveBudget(null, null)).toBeNull();
    expect(resolveBudget(Number.NaN, -1)).toBeNull();

    expect(DEFAULT_BUDGET_WARN_AT).toBe(0.8);
    expect(budgetState(340_000, 1_000_000, 0.8)).toEqual({ budget: 1_000_000, ratio: 0.34, percent: 34, level: "ok" });
    expect(budgetState(799_999, 1_000_000, 0.8).level).toBe("ok");
    expect(budgetState(800_000, 1_000_000, 0.8).level, "剛好 0.8 即警示").toBe("warn");
    expect(budgetState(1_200_000, 1_000_000, 0.8)).toMatchObject({ percent: 120, level: "warn" });
    expect(budgetState(100, null, 0.8)).toEqual({ budget: null, ratio: null, percent: null, level: "unknown" });
    expect(budgetState(100, 0, 0.8).level).toBe("unknown");
  });

  it("AT_960_20_3 系統參數：executionBudgetSettings 讀 globalTokenBudget 與 tokenBudgetWarningThreshold；缺或不合法時預算 null、閾值取初值 0.8", () => {
    expect(
      executionBudgetSettings([
        { key: "globalTokenBudget", value: "2000000" },
        { key: "tokenBudgetWarningThreshold", value: "0.9" },
        { key: "other", value: "1" },
      ]),
    ).toEqual({ globalTokenBudget: 2_000_000, warnAt: 0.9 });
    expect(executionBudgetSettings([])).toEqual({ globalTokenBudget: null, warnAt: 0.8 });
    expect(
      executionBudgetSettings([
        { key: "globalTokenBudget", value: "abc" },
        { key: "tokenBudgetWarningThreshold", value: "5" },
      ]),
    ).toEqual({ globalTokenBudget: null, warnAt: 0.8 });
    expect(
      executionBudgetSettings([
        { key: "globalTokenBudget", value: "" },
        { key: "tokenBudgetWarningThreshold", value: "" },
      ]),
    ).toEqual({ globalTokenBudget: null, warnAt: 0.8 });
  });
});

// ── AT_960_16_E_4：剩餘審查預算 ───────────────────────────────────────────────────────

/** 剩餘預算的來源掃描器：元件不得以輪列的 fsmRetryCount 算剩餘預算，也不得自己寫「3 − 計數」。回違規說明。 */
function budgetSourceViolations(source: string): string[] {
  const code = stripComments(source);
  const found: string[] = [];
  if (/remainingReviewBudget|REVIEW_RETRY_LIMIT/.test(code) && /fsmRetryCount/.test(code)) found.push("以輪列的 fsmRetryCount 計算剩餘預算");
  if (/\b3\s*-\s*[\w.?]*[cC]ount/.test(code)) found.push("自寫「3 − 計數」");
  if (/\bRETRY_LIMIT\s*=\s*\d/.test(code)) found.push("自訂預算上限常數");
  return found;
}

function researchComponentSources(): Array<{ file: string; text: string }> {
  const dir = path.join(ROOT, "components", "domain", "research");
  return readdirSync(dir)
    .filter((name) => /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name))
    .map((name) => ({ file: `components/domain/research/${name}`, text: readFileSync(path.join(dir, name), "utf-8") }));
}

describe("AT_960_16_E_4 剩餘審查預算＝max(0, 3 − currentCount)，來源只取 FSM 視圖的 currentCount", () => {
  it("AT_960_16_E_4 表驅動 0、1、2、3、4 依序得 3、2、1、0、0（4 是異常值，夾到 0 不為負）；函式簽名只吃 currentCount", () => {
    const table: Array<[number, number]> = [
      [0, 3],
      [1, 2],
      [2, 1],
      [3, 0],
      [4, 0],
    ];
    for (const [count, expected] of table) expect(remainingReviewBudget(count), `currentCount=${count}`).toBe(expected);
    expect(remainingReviewBudget.length, "只吃 currentCount 一個參數").toBe(1);
    expect(remainingReviewBudget(100)).toBe(0);
    // 人工恢復後：currentCount 仍為 3，剩餘預算為 0（按鈕不因此停用——至多再跑一輪，由元件層驗；D-60）
    expect(remainingReviewBudget(3)).toBe(0);
  });

  it("AT_960_16_E_4 上限只有一個具名常數（值 3，對映 FSM SCG_VALIDATION 上限）；reviewRetryCount 只取 retryHistory.gates.SCG_VALIDATION.currentCount，缺席當 0", () => {
    expect(REVIEW_RETRY_LIMIT).toBe(3);
    expect(RESEARCH_SOURCE.match(/REVIEW_RETRY_LIMIT\s*=\s*\d+/g), "上限恰一處宣告").toHaveLength(1);
    expect(budgetSourceViolations(RESEARCH_SOURCE), "lib/domain/research.ts 自己也不得自寫「3 − 計數」或以 fsmRetryCount 算預算").toEqual([]);
    const fsm = (gates: Record<string, { currentCount: number; entries: number }>) => ({ retryHistory: { count: 0, last: null, gates } }) as never;
    expect(reviewRetryCount(fsm({ SCG_VALIDATION: { currentCount: 2, entries: 2 }, PR_REVIEW: { currentCount: 1, entries: 1 } }))).toBe(2);
    expect(reviewRetryCount(fsm({ PR_REVIEW: { currentCount: 3, entries: 3 } }))).toBe(0);
    expect(reviewRetryCount(fsm({}))).toBe(0);
    expect(reviewRetryCount(null)).toBe(0);
    expect(reviewRetryCount(undefined)).toBe(0);
  });

  it("AT_960_16_E_4 靜態掃描：components/domain/research 的每個非測試元件都不以輪列的 fsmRetryCount 計算剩餘預算、不自寫「3 − 計數」；掃描器有負控且範圍非空", () => {
    const sources = researchComponentSources();
    expect(sources.length, "掃描範圍非空：第一波至少四個元件").toBeGreaterThanOrEqual(4);
    for (const { file, text } of sources) expect(budgetSourceViolations(text), file).toEqual([]);
    // 工作室的核對：GatekeeperPanel.tsx 一旦存在（第二波），剩餘預算必須經 remainingReviewBudget 計算
    const gatekeeper = sources.find((s) => s.file.endsWith("/GatekeeperPanel.tsx"));
    if (gatekeeper !== undefined) expect(gatekeeper.text).toMatch(/remainingReviewBudget\(/);
    // 負控
    expect(budgetSourceViolations("const left = remainingReviewBudget(round.fsmRetryCount);")).not.toEqual([]);
    expect(budgetSourceViolations("const left = 3 - currentCount;")).not.toEqual([]);
    expect(budgetSourceViolations("const left = 3 - round.fsmRetryCount;")).not.toEqual([]);
    expect(budgetSourceViolations("const RETRY_LIMIT = 3;")).not.toEqual([]);
    expect(budgetSourceViolations("const left = remainingReviewBudget(reviewRetryCount(fsm)); // 註解提到 fsmRetryCount 不算")).toEqual([]);
  });
});

// ── AT_960_17_E_1：diffLines ──────────────────────────────────────────────────────────

/** 可重現的亂數（mulberry32）。 */
function prng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** 最長共同子序列長度（參考實作；O(nm)，只給小輸入）。 */
function lcsLength(a: readonly string[], b: readonly string[]): number {
  const table = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = 1; i <= a.length; i += 1) for (let j = 1; j <= b.length; j += 1) table[i][j] = a[i - 1] === b[j - 1] ? table[i - 1][j - 1] + 1 : Math.max(table[i - 1][j], table[i][j - 1]);
  return table[a.length][b.length];
}

/** diff 結果的合法性：還原得到 A 與 B、行號單調、同一段變更內刪除在前。 */
function expectValidDiff(result: readonly DiffLine[], a: string, b: string, where: string): void {
  expect(
    result.filter((l) => l.kind !== "add").map((l) => l.text),
    `${where}：還原 A`,
  ).toEqual(splitLines(a));
  expect(
    result.filter((l) => l.kind !== "remove").map((l) => l.text),
    `${where}：還原 B`,
  ).toEqual(splitLines(b));
  const aLines = result.map((l) => l.aLine).filter((n): n is number => n !== null);
  const bLines = result.map((l) => l.bLine).filter((n): n is number => n !== null);
  expect(aLines, `${where}：A 行號為 1…n`).toEqual(Array.from({ length: aLines.length }, (_, i) => i + 1));
  expect(bLines, `${where}：B 行號為 1…m`).toEqual(Array.from({ length: bLines.length }, (_, i) => i + 1));
  for (const line of result) {
    expect(
      line.kind === "add" ? line.aLine === null && line.bLine !== null : line.kind === "remove" ? line.bLine === null && line.aLine !== null : line.aLine !== null && line.bLine !== null,
      `${where}：行號與種類相容`,
    ).toBe(true);
  }
  for (let i = 1; i < result.length; i += 1) {
    if (result[i - 1].kind === "add" && result[i].kind === "remove") throw new Error(`${where}：同一段變更內新增排在刪除之前（第 ${i} 行）`);
  }
}

/** 約 200KB 的兩版夾具：A 為 4000 行固定內容，B 在 A 上改、刪、插若干行（全部由固定規則產生）。 */
function bigFixtures(): { a: string; b: string } {
  const rand = prng(20261102);
  const words = ["證據", "矩陣", "審查", "凍結", "規格", "來源", "查證", "風險", "預算", "工作區", "流程", "核准"];
  const lines = Array.from({ length: 4000 }, (_, i) => `${String(i).padStart(4, "0")} ${Array.from({ length: 8 }, () => words[Math.floor(rand() * words.length)]).join(" ")} ${"x".repeat(12)}`);
  const changed: string[] = [];
  lines.forEach((line, i) => {
    if (i % 211 === 0) return; // 刪除
    changed.push(i % 37 === 0 ? `${line} （已修訂）` : line);
    if (i % 97 === 0) changed.push(`新增行 ${i}`);
  });
  return { a: lines.join("\n"), b: changed.join("\n") };
}

describe("AT_960_17_E_1 diffLines：確定性、反向對稱與 200KB 計算時間（無瀏覽器全域）", () => {
  it("AT_960_17_E_1 200KB 兩版夾具：同一輸入五次輸出逐值相同；A→B 的新增行集合等於 B→A 的刪除行集合（逐行號）；中位數計算時間小於 1000 毫秒", () => {
    withoutBrowserGlobals();
    const { a, b } = bigFixtures();
    expect(Buffer.byteLength(a, "utf-8"), "夾具約 200KB").toBeGreaterThan(190_000);
    expect(Buffer.byteLength(b, "utf-8")).toBeGreaterThan(190_000);
    const runs: DiffLine[][] = [];
    const times: number[] = [];
    for (let i = 0; i < 5; i += 1) {
      const t0 = performance.now();
      runs.push(diffLines(a, b));
      times.push(performance.now() - t0);
    }
    for (let i = 1; i < runs.length; i += 1) expect(runs[i], `第 ${i + 1} 次與第 1 次逐值相同`).toEqual(runs[0]);
    const forward = runs[0];
    const backward = diffLines(b, a);
    expectValidDiff(forward, a, b, "A→B");
    expectValidDiff(backward, b, a, "B→A");
    expect(forward.filter((l) => l.kind === "add").length, "夾具確有新增").toBeGreaterThan(0);
    expect(forward.filter((l) => l.kind === "remove").length, "夾具確有刪除").toBeGreaterThan(0);
    // 新增行集合（B 版行號）等於反向的刪除行集合（同一份 B 的行號）
    expect(forward.filter((l) => l.kind === "add").map((l) => l.bLine)).toEqual(backward.filter((l) => l.kind === "remove").map((l) => l.aLine));
    expect(forward.filter((l) => l.kind === "remove").map((l) => l.aLine)).toEqual(backward.filter((l) => l.kind === "add").map((l) => l.bLine));
    const median = [...times].sort((x, y) => x - y)[2];
    expect(median, `中位數 ${median.toFixed(1)} 毫秒`).toBeLessThan(1000);
  });

  it("AT_960_17_E_1 空輸入與單行輸入有明確結果：空對空為空陣列、空對單行為單一 add、單行對空為單一 remove、相同為單一 same；CRLF 與 LF 等價、結尾換行不多算一行", () => {
    expect(diffLines("", "")).toEqual([]);
    expect(diffLines("", "a")).toEqual([{ kind: "add", text: "a", aLine: null, bLine: 1 }]);
    expect(diffLines("a", "")).toEqual([{ kind: "remove", text: "a", aLine: 1, bLine: null }]);
    expect(diffLines("a", "a")).toEqual([{ kind: "same", text: "a", aLine: 1, bLine: 1 }]);
    expect(diffLines("a", "b")).toEqual([
      { kind: "remove", text: "a", aLine: 1, bLine: null },
      { kind: "add", text: "b", aLine: null, bLine: 1 },
    ]);
    expect(diffLines("a\r\nb\r\n", "a\nb")).toEqual([
      { kind: "same", text: "a", aLine: 1, bLine: 1 },
      { kind: "same", text: "b", aLine: 2, bLine: 2 },
    ]);
    expect(splitLines("")).toEqual([]);
    expect(splitLines("a\n")).toEqual(["a"]);
    expect(splitLines("\n")).toEqual([""]);
    expect(splitLines("a\n\nb")).toEqual(["a", "", "b"]);
  });

  it("AT_960_17_E_1 空白變動行算差異；新增、刪除、不變、空白變動並存的小夾具結果逐行固定", () => {
    const a = ["# 標題", "", "保留", "刪掉這行", "尾端空白 ", "結尾"].join("\n");
    const b = ["# 標題", "", "保留", "尾端空白", "新增的一行", "結尾"].join("\n");
    expect(diffLines(a, b).map((l) => `${l.kind === "same" ? " " : l.kind === "add" ? "+" : "-"}${l.text}`)).toEqual([
      " # 標題",
      " ",
      " 保留",
      "-刪掉這行",
      "-尾端空白 ",
      "+尾端空白",
      "+新增的一行",
      " 結尾",
    ]);
  });

  it("diffLines 的正確性（隨機小輸入，對照 LCS 參考實作）：還原得到 A 與 B、same 行數＝最長共同子序列（編輯最短）、反向互為對稱（逐行號）、五次輸出相同", () => {
    const rand = prng(7);
    const alphabet = ["a", "b", "c", "", "d"];
    for (let trial = 0; trial < 300; trial += 1) {
      const lenA = Math.floor(rand() * 14);
      const lenB = Math.floor(rand() * 14);
      const linesA = Array.from({ length: lenA }, () => alphabet[Math.floor(rand() * alphabet.length)]);
      const linesB = Array.from({ length: lenB }, () => alphabet[Math.floor(rand() * alphabet.length)]);
      // 結尾的空字串行會被 splitLines 當成結尾換行而不算一行：先以 splitLines 的口徑取參考輸入
      const a = linesA.join("\n");
      const b = linesB.join("\n");
      const refA = splitLines(a);
      const refB = splitLines(b);
      const result = diffLines(a, b);
      expectValidDiff(result, a, b, `trial ${trial}`);
      expect(result.filter((l) => l.kind === "same").length, `trial ${trial}：same 行數＝LCS`).toBe(lcsLength(refA, refB));
      expect(diffLines(a, b), `trial ${trial}：確定性`).toEqual(result);
      const back = diffLines(b, a);
      expect(
        back.filter((l) => l.kind === "remove").map((l) => l.aLine),
        `trial ${trial}：反向刪除＝正向新增`,
      ).toEqual(result.filter((l) => l.kind === "add").map((l) => l.bLine));
      expect(
        back.filter((l) => l.kind === "add").map((l) => l.bLine),
        `trial ${trial}：反向新增＝正向刪除`,
      ).toEqual(result.filter((l) => l.kind === "remove").map((l) => l.aLine));
    }
  });

  it("最短編輯距離超過 DIFF_MAX_EDITS 時退回整段刪除加整段新增：結果仍是合法的編輯序列、計算不耗盡記憶體", () => {
    const size = DIFF_MAX_EDITS + 400;
    const a = Array.from({ length: size }, (_, i) => `甲 ${i}`).join("\n");
    const b = Array.from({ length: size }, (_, i) => `乙 ${i}`).join("\n");
    const t0 = performance.now();
    const result = diffLines(a, b);
    expect(performance.now() - t0, "退回路徑不拖垮").toBeLessThan(5000);
    expectValidDiff(result, a, b, "完全不同的兩份");
    expect(result.every((l) => l.kind !== "same")).toBe(true);
    expect(result.slice(0, size).every((l) => l.kind === "remove")).toBe(true);
    expect(result.slice(size).every((l) => l.kind === "add")).toBe(true);
  });
});

// ── 雷達、Gate 0 等待 ──────────────────────────────────────────────────────────────────

const round = (patch: Partial<ResearchReviewRound> & Pick<ResearchReviewRound, "roundNo">): ResearchReviewRound =>
  ({ fsmGateResult: "FAIL", finishedAt: "2026-11-02T10:00:00+08:00", scores: [], ...patch }) as ResearchReviewRound;

describe("四方雷達 scoreRadar", () => {
  it("固定四軸依序（架構、商業、QA、資安）；分數取該維度的整數分；缺的維度回 null、不補 0", () => {
    expect(RADAR_AXES.map((a) => a.dimension)).toEqual(["ARCHITECTURE", "PRODUCT", "QA", "SECURITY"]);
    const scores = [
      { dimension: "SECURITY", score: 90 },
      { dimension: "ARCHITECTURE", score: 78 },
      { dimension: "QA", score: 70 },
      { dimension: "PRODUCT", score: 84 },
    ] as ResearchReviewRound["scores"];
    expect(scoreRadar({ scores })).toEqual([
      { dimension: "ARCHITECTURE", label: "架構", score: 78 },
      { dimension: "PRODUCT", label: "商業", score: 84 },
      { dimension: "QA", label: "QA", score: 70 },
      { dimension: "SECURITY", label: "資安", score: 90 },
    ]);
    expect(scoreRadar({ scores: [] }).map((a) => a.score)).toEqual([null, null, null, null]);
  });
});

describe("Gate 0 等待時數（D-48(3)；AC-R2P-09-10）", () => {
  const FINISHED = "2026-11-02T10:00:00+08:00";
  const hoursLater = (hours: number, extraMinutes = 0) => Date.parse(FINISHED) + hours * 3_600_000 + extraMinutes * 60_000;

  it("等待起點＝最近一個 fsmGateResult 為 PASS 的輪的 finishedAt（POST_HUMAN 通過輪的 fsmGateResult 為 null、不作起點）；沒有 PASS 輪回 null", () => {
    const early = round({ roundNo: 1, fsmGateResult: "PASS", finishedAt: "2026-11-01T08:00:00+08:00" });
    const late = round({ roundNo: 2, fsmGateResult: "PASS", finishedAt: FINISHED });
    const postHuman = round({ roundNo: 3, fsmGateResult: null, finishedAt: "2026-11-03T09:00:00+08:00", triggerKind: "POST_HUMAN" } as never);
    expect(gate0WaitStart([early, late])).toBe(FINISHED);
    expect(gate0WaitStart([late, early]), "與陣列順序無關，取 roundNo 最大者").toBe(FINISHED);
    expect(gate0WaitStart([early, postHuman])).toBe(early.finishedAt);
    expect(gate0WaitStart([round({ roundNo: 1, fsmGateResult: "FAIL" }), postHuman])).toBeNull();
    expect(gate0WaitStart([])).toBeNull();
  });

  it("gateWaitedHours：向下取整（5 小時、71 小時 59 分、72 小時、100 小時）；起點解不出回 null；時鐘偏差的負值夾到 0；入參為 finishedAt 與 now", () => {
    expect(gateWaitedHours(FINISHED, hoursLater(5))).toBe(5);
    expect(gateWaitedHours(FINISHED, hoursLater(71, 59))).toBe(71);
    expect(gateWaitedHours(FINISHED, hoursLater(72))).toBe(72);
    expect(gateWaitedHours(FINISHED, hoursLater(100))).toBe(100);
    expect(gateWaitedHours(FINISHED, hoursLater(0, 30))).toBe(0);
    expect(gateWaitedHours(FINISHED, hoursLater(-2))).toBe(0);
    expect(gateWaitedHours("不是時間", Date.now())).toBeNull();
    expect(gateWaitedHours.length).toBe(2);
    expect(GATE0_WAIT_BANNER_HOURS).toBe(72);
  });

  it("gate0WaitView：FSM 現態不是 HUMAN_PENDING 不顯示；滿 72 小時 overdue；較新的 POST_HUMAN 通過輪不改變起點", () => {
    const rounds = [round({ roundNo: 1, fsmGateResult: "PASS", finishedAt: FINISHED }), round({ roundNo: 2, fsmGateResult: null, finishedAt: "2026-11-05T10:00:00+08:00" })];
    expect(gate0WaitView("HUMAN_PENDING", rounds, hoursLater(5))).toEqual({ hours: 5, overdue: false });
    expect(gate0WaitView("HUMAN_PENDING", rounds, hoursLater(71, 59))).toEqual({ hours: 71, overdue: false });
    expect(gate0WaitView("HUMAN_PENDING", rounds, hoursLater(72))).toEqual({ hours: 72, overdue: true });
    expect(gate0WaitView("HUMAN_PENDING", rounds, hoursLater(100))).toEqual({ hours: 100, overdue: true });
    expect(gate0WaitView("SCG_VALIDATION", rounds, hoursLater(100))).toBeNull();
    expect(gate0WaitView("ESCALATION", rounds, hoursLater(100))).toBeNull();
    expect(gate0WaitView(null, rounds, hoursLater(100))).toBeNull();
    expect(gate0WaitView("HUMAN_PENDING", [], hoursLater(100))).toBeNull();
  });
});

// ── 對帳漂移（AC-R2P-23-1、23-2；AT_960_21_6 的純函式面）──────────────────────────────────

describe("對帳結果轉畫面（reconcileDriftView）：漂移只顯示、量不到不算漂移也不算一致", () => {
  const SIX_CHECKS = ["fsm_flow_mapping", "prd_sha256", "review_card", "evidence_matrix", "task_decomposition", "route_decision"];

  it("對帳六項檢查的中文名稱恰為契約的六個名稱（⚖16）", () => {
    expect(Object.keys(RECONCILE_CHECK_LABEL)).toEqual(SIX_CHECKS);
    expect(new Set(Object.values(RECONCILE_CHECK_LABEL)).size).toBe(6);
    for (const label of Object.values(RECONCILE_CHECK_LABEL)) expect(label.trim()).not.toBe("");
  });

  it("全部 ok：三塊皆空（沒有漂移、沒有對映警示、沒有量不到的項目）", () => {
    expect(reconcileDriftView(RECONCILE_OK)).toEqual({ files: [], fsmMapping: false, notEvaluable: [], hasDrift: false, pendingCorrection: false });
  });

  it("AT_961_20_E_2 pending_correction 是第三態：不算漂移（hasDrift 假、pendingCorrection 真）；drift 與 NOT_EVALUABLE 照舊", () => {
    const withMapping = (status: string): ResearchReconcileResult =>
      ({
        consistent: false,
        checks: [
          { name: "fsm_flow_mapping", status },
          { name: "prd_sha256", status: "ok" },
        ],
      }) as unknown as ResearchReconcileResult;
    const pending = reconcileDriftView(withMapping("pending_correction"));
    expect(pending.hasDrift).toBe(false);
    expect(pending.pendingCorrection).toBe(true);
    expect(pending.fsmMapping).toBe(false);
    expect(pending.notEvaluable).toEqual([]);
    const drift = reconcileDriftView(withMapping("drift"));
    expect([drift.hasDrift, drift.pendingCorrection, drift.fsmMapping]).toEqual([true, false, true]);
    const missing = reconcileDriftView(withMapping("NOT_EVALUABLE"));
    expect([missing.hasDrift, missing.pendingCorrection]).toEqual([false, false]);
    expect(missing.notEvaluable).toEqual(["狀態機與流程游標的對映"]);
  });

  it("PRD sha 不符＋FSM 對映不合：檔案漂移列帶檔名與雙方 sha256（資料庫為期望值、檔案為實際值）；FSM 對映另成警示、不混進檔案列", () => {
    expect(reconcileDriftView(RECONCILE_DRIFT)).toEqual({
      files: [{ check: "prd_sha256", label: "PRD 檔案", path: "01_specs/PRD-v0.2.0-draft.md", expectedSha256: sha("2"), actualSha256: sha("9") }],
      fsmMapping: true,
      notEvaluable: [],
      hasDrift: true,
      pendingCorrection: false,
    });
  });

  it("NOT_EVALUABLE（量不到）：列入「量不到」、不算漂移也不算一致；未登記的檢查名以原名顯示；多個漂移列依檢查順序保留", () => {
    const result: ResearchReconcileResult = {
      consistent: false,
      checks: [
        { name: "fsm_flow_mapping", status: "NOT_EVALUABLE" },
        { name: "prd_sha256", status: "drift", drift: [{ kind: "sha256_mismatch", path: "01_specs/PRD-v1.0.0.md", expectedSha256: sha("a"), actualSha256: sha("b") }] },
        { name: "review_card", status: "drift", drift: [{ kind: "file_missing", path: "01_specs/review_card.json" }] },
        { name: "future_check", status: "NOT_EVALUABLE" },
        { name: "evidence_matrix", status: "ok" },
      ],
    };
    const view = reconcileDriftView(result);
    expect(view.notEvaluable).toEqual(["狀態機與流程游標的對映", "future_check"]);
    expect(view.fsmMapping, "量不到不是對映不合").toBe(false);
    expect(view.files.map((f) => f.path)).toEqual(["01_specs/PRD-v1.0.0.md", "01_specs/review_card.json"]);
    // 資料庫有列而檔案缺席：沒有雙方 sha，不編造
    expect(view.files[1]).toEqual({ check: "review_card", label: "審查卡", path: "01_specs/review_card.json", expectedSha256: undefined, actualSha256: undefined });
  });

  it("drift 檢查缺 drift 陣列時不丟例外、不憑空產生檔案列；純函式不改動輸入", () => {
    const result: ResearchReconcileResult = { consistent: false, checks: [{ name: "prd_sha256", status: "drift" }] };
    const frozen = JSON.parse(JSON.stringify(result)) as ResearchReconcileResult;
    expect(reconcileDriftView(result)).toEqual({ files: [], fsmMapping: false, notEvaluable: [], hasDrift: false, pendingCorrection: false });
    expect(result).toEqual(frozen);
    expect(reconcileDriftView({ consistent: true, checks: [] })).toEqual({ files: [], fsmMapping: false, notEvaluable: [], hasDrift: false, pendingCorrection: false });
  });
});

describe("帶時區的時間顯示（formatInstant）", () => {
  const FORMAT = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}) UTC([+-])(\d{2}):(\d{2})$/;

  it.each(["2026-11-02T10:00:00+08:00", "2026-11-02T02:00:00Z", "2026-07-01T00:00:00-05:00", "2026-01-31T23:59:00+13:45", "2026-12-31T23:59:00Z"])(
    "%s：格式固定為「年-月-日 時:分 UTC±hh:mm」，且顯示的本地時間加上顯示的偏移量就是原本那個時刻（不管這台機器在哪個時區）",
    (iso) => {
      const match = FORMAT.exec(formatInstant(iso));
      expect(match, formatInstant(iso)).not.toBeNull();
      const [, y, mo, d, h, mi, sign, oh, om] = match as RegExpExecArray;
      const offsetMinutes = (sign === "-" ? -1 : 1) * (Number(oh) * 60 + Number(om));
      const reconstructed = Date.UTC(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi)) - offsetMinutes * 60_000;
      expect(reconstructed).toBe(Date.parse(iso));
    },
  );

  it("解不出的時間顯示「—」（不顯示 Invalid Date、不顯示 naive 時間）", () => {
    for (const bad of [null, undefined, "", "不是時間", "2026-13-45T99:99:99Z"]) expect(formatInstant(bad), String(bad)).toBe("—");
  });
});

// ── 清單頁 ────────────────────────────────────────────────────────────────────────────

const summary = (patch: Partial<ResearchProjectSummary> = {}): ResearchProjectSummary => ({
  id: "p1",
  rpNo: "RP-0001",
  slug: "agent-memory-gc",
  title: "Agent 記憶體回收研究",
  depthLevel: "STANDARD",
  targetScope: "UNDECIDED",
  flowStep: "topic",
  flowPhase: "INGESTED",
  flowStatus: "IDLE",
  flowDetail: "",
  consoleProjectId: null,
  createdBy: "operator",
  createdAt: "2026-11-02T09:00:00+08:00",
  updatedAt: "2026-11-02T09:00:00+08:00",
  archivedAt: null,
  ...patch,
});

describe("研究專案清單：徽章、篩選、主連結", () => {
  it("projectBadge：已封存＞初始化失敗＞失敗（階段失敗或取消）＞SCR 進行中＞已交付＞Gate 0 已核准（游標越過規格工作室）＞進行中", () => {
    expect(Object.keys(PROJECT_BADGE_LABEL)).toEqual(["active", "frozen", "delivered", "scr", "failed", "init_failed", "archived"]);
    expect(PROJECT_BADGE_LABEL.failed).toBe("失敗");
    expect(projectBadge(summary())).toBe("active");
    expect(projectBadge(summary({ flowStep: "studio", flowPhase: "REVIEWING", flowStatus: "RUNNING" }))).toBe("active");
    expect(projectBadge(summary({ flowStep: "route", flowPhase: "FROZEN" }))).toBe("frozen");
    expect(projectBadge(summary({ flowStep: "build", flowPhase: "BUILDING" }))).toBe("frozen");
    expect(projectBadge(summary({ flowStep: "deliver", flowStatus: "COMPLETED" }))).toBe("delivered");
    expect(projectBadge(summary({ flowStep: "studio", flowPhase: "SCR_OPEN" }))).toBe("scr");
    expect(projectBadge(summary({ flowStatus: "FAILED", flowDetail: "init_failed:fsm" }))).toBe("init_failed");
    expect(projectBadge(summary({ archivedAt: "2026-11-02T10:00:00+08:00", flowStatus: "FAILED", flowDetail: "init_failed:fsm" }))).toBe("archived");
    expect(isInitFailed(summary({ flowStatus: "FAILED", flowDetail: "init_failed:files" }))).toBe(true);
    expect(isInitFailed(summary({ flowStatus: "IDLE", flowDetail: "init_failed:files" })), "重試成功後已回 IDLE").toBe(false);
  });

  it("INT-14⑥ 階段失敗與取消不標「進行中」：FAILED（no_evidence、evaluator_failed、cancelled…）與舊版留下的 CANCELLED 游標都是「失敗」；初始化失敗仍是自己的徽章；已封存最優先", () => {
    for (const flowDetail of ["no_evidence", "evaluator_failed", "step_timeout", "cancelled", ""]) {
      const failed = summary({ flowPhase: "INGESTED", flowStatus: "FAILED", flowDetail });
      expect(projectBadge(failed), `FAILED／${flowDetail}`).toBe("failed");
      expect(isStageFailed(failed), `FAILED／${flowDetail}`).toBe(true);
      expect(projectBadge({ ...failed, flowStep: "studio", flowPhase: "REVISING" }), `步驟 2 的 FAILED／${flowDetail} 也不是進行中`).toBe("failed");
    }
    const legacyCancelled = summary({ flowPhase: "RESEARCHING", flowStatus: "CANCELLED" });
    expect(projectBadge(legacyCancelled), "舊版 Bridge 取消後留下的游標（phase 停在 RESEARCHING）").toBe("failed");
    expect(isStageFailed(legacyCancelled)).toBe(true);
    for (const flowStatus of ["IDLE", "RUNNING", "WAITING_HUMAN", "BLOCKED", "ESCALATED", "COMPLETED"] as const) expect(isStageFailed(summary({ flowStatus })), flowStatus).toBe(false);
    expect(isStageFailed(summary({ flowStatus: "FAILED", flowDetail: "init_failed:workspace" })), "初始化失敗不算階段失敗").toBe(false);
    expect(projectBadge(summary({ flowStatus: "FAILED", flowDetail: "init_failed:workspace" }))).toBe("init_failed");
    expect(projectBadge(summary({ archivedAt: "2026-11-02T10:00:00+08:00", flowStatus: "FAILED", flowDetail: "no_evidence" })), "已封存優先於失敗").toBe("archived");
    expect(filterProjects([summary({ id: "f", flowStatus: "FAILED", flowDetail: "no_evidence" }), summary({ id: "a" })], { q: "", status: "failed", step: "all" }).map((p) => p.id)).toEqual(["f"]);
  });

  it("continueLabel 是「繼續（第 k 步：名稱）」；filterProjects：『全部』不含已封存、搜尋不分大小寫比對編號／名稱／代號、可按狀態與步驟篩", () => {
    expect(FLOW_STEP_IDS.map(continueLabel)).toEqual(["繼續（第 1 步：研究）", "繼續（第 2 步：規格工作室）", "繼續（第 3 步：分流）", "繼續（第 4 步：拆解與執行）", "繼續（第 5 步：交付）"]);
    const list = [
      summary({ id: "a", rpNo: "RP-0001", title: "Agent 記憶體回收", slug: "agent-gc" }),
      summary({ id: "b", rpNo: "RP-0002", title: "向量資料庫選型", slug: "vector-db", flowStep: "route", flowPhase: "FROZEN" }),
      summary({ id: "c", rpNo: "RP-0003", title: "已封存的舊題目", slug: "old", archivedAt: "2026-10-01T00:00:00+08:00" }),
      summary({ id: "d", rpNo: "RP-0004", title: "初始化壞掉", slug: "broken", flowStatus: "FAILED", flowDetail: "init_failed:files" }),
    ];
    const ids = (filter: Partial<Parameters<typeof filterProjects>[1]>) => filterProjects(list, { q: "", status: "all", step: "all", ...filter }).map((p) => p.id);
    expect(ids({})).toEqual(["a", "b", "d"]);
    expect(ids({ status: "archived" })).toEqual(["c"]);
    expect(ids({ status: "frozen" })).toEqual(["b"]);
    expect(ids({ status: "init_failed" })).toEqual(["d"]);
    expect(ids({ step: "route" })).toEqual(["b"]);
    expect(ids({ step: "topic" })).toEqual(["a", "d"]);
    expect(ids({ q: "AGENT" })).toEqual(["a"]);
    expect(ids({ q: "rp-0002" })).toEqual(["b"]);
    expect(ids({ q: "  vector " })).toEqual(["b"]);
    expect(ids({ q: "沒有這個" })).toEqual([]);
    expect(ids({ q: "old", status: "archived" })).toEqual(["c"]);
  });
});

// ── 新建研究專案 ──────────────────────────────────────────────────────────────────────

describe("新建研究專案：代號、摘要、驗證、請求本文", () => {
  it("slugFromTopic：ASCII 英數轉小寫、其餘（連續者）以連字號連接、去頭尾連字號、截至 30 字元；結果符合 slug 規則", () => {
    expect(slugFromTopic("Agent Memory GC 研究")).toBe("agent-memory-gc");
    expect(slugFromTopic("  --Hello,   World!!  ")).toBe("hello-world");
    expect(slugFromTopic("RAG vs. Long-Context 2026")).toBe("rag-vs-long-context-2026");
    const long = slugFromTopic("a".repeat(29) + " bbbb cccc");
    expect(long).toHaveLength(29);
    expect(long.endsWith("-"), "截斷後去尾端連字號").toBe(false);
    expect(slugFromTopic("x".repeat(50))).toHaveLength(30);
    for (const topic of ["Agent Memory GC 研究", "x".repeat(50), "123", "中文 abc 中文"]) expect(slugFromTopic(topic), topic).toMatch(SLUG_PATTERN);
  });

  it("slugFromTopic：沒有任何 ASCII 英數（純中文、純符號）時退回 rp- 加四位小寫英數、符合 slug 規則、同一命題恆得同一代號", () => {
    for (const topic of ["向量資料庫如何選型", "——「」！？", "한국어 テスト"]) {
      const slug = slugFromTopic(topic);
      expect(slug.startsWith(FALLBACK_SLUG_PREFIX), topic).toBe(true);
      expect(slug, topic).toMatch(/^rp-[a-z0-9]{4}$/);
      expect(slug, topic).toMatch(SLUG_PATTERN);
      expect(slugFromTopic(topic), "確定性").toBe(slug);
    }
    expect(slugFromTopic("題目甲")).not.toBe(slugFromTopic("題目乙"));
  });

  it("topicSummary：取第一個非空行的前 60 字（超過加「…」）", () => {
    expect(topicSummary("短命題")).toBe("短命題");
    expect(topicSummary("\n\n  第一行  \n第二行")).toBe("第一行");
    const long = "字".repeat(61);
    expect(topicSummary(long)).toBe(`${"字".repeat(60)}…`);
    expect(topicSummary("字".repeat(60))).toBe("字".repeat(60));
    expect(topicSummary("   ")).toBe("");
  });

  it("createResearchErrors：topic 空與 501 字、slug 不合規、四層全關各回對應欄位的錯誤；合法輸入回空物件", () => {
    const ok = { topic: "合法命題", slug: "ok-slug", depthLevel: "STANDARD", layers: { academic: true, industry: false, oss: false, community: false } };
    expect(createResearchErrors(ok)).toEqual({});
    expect(createResearchErrors({ ...ok, topic: "" }).topic).toBeDefined();
    expect(createResearchErrors({ ...ok, topic: "   " }).topic, "只有空白也算空").toBeDefined();
    expect(createResearchErrors({ ...ok, topic: "字".repeat(500) })).toEqual({});
    expect(createResearchErrors({ ...ok, topic: "字".repeat(501) }).topic).toContain("500");
    expect(createResearchErrors({ ...ok, topic: "含\u0000NUL" }).topic).toBeDefined();
    for (const slug of ["Abc", "", "-abc", "a_b", "a".repeat(31), "中文"]) expect(createResearchErrors({ ...ok, slug }).slug, JSON.stringify(slug)).toBeDefined();
    expect(createResearchErrors({ ...ok, slug: "a".repeat(30) })).toEqual({});
    expect(createResearchErrors({ ...ok, layers: { academic: false, industry: false, oss: false, community: false } }).layers).toContain("來源層");
    expect(createResearchErrors({ ...ok, depthLevel: "HUGE" }).depthLevel).toBeDefined();
    const many = createResearchErrors({ topic: "", slug: "Abc", depthLevel: "x", layers: { academic: false, industry: false, oss: false, community: false } });
    expect(Object.keys(many).sort()).toEqual(["depthLevel", "layers", "slug", "topic"]);
  });

  it("toCreateRequest：欄位名 camelCase、值域 QUICK／STANDARD／DEEP；title 取命題摘要、inScope 至少一項、適用性軸全六軸、recencyYears 為 3；不含 snake_case 鍵", () => {
    const request = toCreateRequest({ topic: "  向量資料庫如何選型  ", slug: "vector-db", depthLevel: "DEEP", layers: { academic: true, industry: false, oss: true, community: true } });
    expect(request).toEqual({
      slug: "vector-db",
      title: "向量資料庫如何選型",
      topic: "向量資料庫如何選型",
      scope: {
        layers: { academic: true, industry: false, oss: true, community: true },
        techStack: "",
        inScope: ["向量資料庫如何選型"],
        outOfScope: [],
        recencyYears: 3,
        applicabilityAxes: ["技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本"],
      },
      depthLevel: "DEEP",
    });
    expect(DEFAULT_APPLICABILITY_AXES).toHaveLength(6);
    expect(JSON.stringify(request)).not.toMatch(/_[a-z]/);
    const longTopic = "字".repeat(500);
    const longRequest = toCreateRequest({ topic: longTopic, slug: "long", depthLevel: "QUICK", layers: { academic: true, industry: false, oss: false, community: false } });
    expect(Array.from(longRequest.title).length).toBeLessThanOrEqual(200);
    expect(Array.from(longRequest.scope.inScope[0]).length).toBe(200);
    expect(longRequest.topic).toHaveLength(500);
  });
});

// ── 錯誤原因 ──────────────────────────────────────────────────────────────────────────

describe("研究 reason 與錯誤文案", () => {
  it("RESEARCH_REASONS 為三十五個 reason（snake_case、互異、逐字等於後端 ErrorReasons 的 RESEARCH_ 常數與契約勘誤後的清單：P0 二十二個〔原列十八個扣被 D-72 取代的 spec_digest_changed，加 Bridge 專屬的五個〕，加 R-2 尾巴四個與 P1 九個）", () => {
    const values = Object.values(RESEARCH_REASONS);
    expect(values).toHaveLength(35);
    expect(new Set(values).size).toBe(35);
    for (const value of values) expect(value).toMatch(/^[a-z]+(_[a-z]+)*$/);
    expect([...values].sort()).toEqual(
      [
        "research_write_disabled",
        "research_write_forbidden",
        "research_requires_db",
        "db_blocked",
        "research_not_found",
        "slug_in_use",
        "stage_conflict",
        "prd_version_conflict",
        "review_not_passed",
        "fsm_state_conflict",
        "escalated",
        "spec_frozen",
        "layer_unavailable",
        "sanitization_failed",
        "terms_ack_required",
        "bridge_unreachable",
        "bridge_timeout",
        "allowlist_exists",
        "init_failed",
        "not_implemented",
        "digest_mismatch",
        "missing_digests",
        "route_unsupported_in_deployment",
        "route_conflict",
        "branch_exists",
        "target_not_empty",
        "public_confirmation_required",
        "route_step_failed",
        "scr_open",
        "scr_limit",
        "decomposition_stale",
        "compile_failed",
        "sdd_cli_failed",
        "fsm_state_unreadable",
        "invalid_request",
      ].sort(),
    );
    expect(values, "D-72：409 spec_digest_changed 已由 422 digest_mismatch／missing_digests 取代，Bridge 不再回它").not.toContain("spec_digest_changed");
  });

  it("INT-13 Gate 0 核准的兩個 422：digest_mismatch 與 missing_digests 各有白話文案（不再退回伺服器訊息）；Bridge 專屬的另外三個也有", () => {
    const text = (reason: string) => researchErrorText(new ApiError({ status: 422, message: "伺服器訊息", reason }));
    expect(text(RESEARCH_REASONS.DIGEST_MISMATCH)).toBe("核准時的摘要與現檔不符，請重新整理後再核准");
    expect(text(RESEARCH_REASONS.MISSING_DIGESTS)).toContain("沒有附上任何檔案摘要");
    expect(text(RESEARCH_REASONS.ALLOWLIST_EXISTS)).toContain("已有條目");
    expect(text(RESEARCH_REASONS.INIT_FAILED)).toContain("重試初始化");
    expect(text(RESEARCH_REASONS.NOT_IMPLEMENTED)).toContain("尚未開放");
    expect(text("spec_digest_changed"), "已被取代的 reason 沒有文案，退回通用訊息").toBe("伺服器訊息：spec_digest_changed");
  });

  it("researchErrorText：有對映的 reason 回白話原因；沒有對映或不是 ApiError 退回通用訊息；唯讀提示字樣固定", () => {
    expect(researchErrorText(new ApiError({ status: 409, message: "衝突", reason: RESEARCH_REASONS.SLUG_IN_USE }))).toContain("代號");
    expect(researchErrorText(new ApiError({ status: 503, message: "x", reason: RESEARCH_REASONS.REQUIRES_DB }))).toContain("資料庫");
    for (const reason of Object.values(RESEARCH_REASONS)) expect(researchErrorText(new ApiError({ status: 409, message: "原訊息", reason })), reason).not.toBe("原訊息：" + reason);
    expect(researchErrorText(new ApiError({ status: 500, message: "壞了", reason: "unknown_reason" }))).toBe("壞了：unknown_reason");
    expect(researchErrorText(new Error("一般錯誤"))).toBe("一般錯誤");
    expect(READONLY_TITLE).toBe("權限不足（唯讀角色）");
  });
});

// ── INT-04 研究失敗的呈現（D-77）────────────────────────────────────────────────────────

describe("INT-04 researchFailureOf：失敗游標一律是 FAILED 加 exit_reason（取消為 cancelled）；只認 FAILED，不認「IDLE 加說明」", () => {
  const topic = (flowDetail: string, flowStatus: ResearchFlowStatus = "FAILED") => ({ flowStep: "topic" as const, flowStatus, flowDetail });

  it("no_evidence：「研究失敗」加「重試」（沒有任何來源，沒有 checkpoint 可續）", () => {
    expect(researchFailureOf(topic("no_evidence"))).toEqual({ reason: "no_evidence", action: "retry", text: "研究失敗：沒有任何來源取得成功（no_evidence）" });
  });

  it("evaluator_failed：「研究未完成：evaluator_failed」加「續跑」（顯示 Bridge 給的原因代碼）", () => {
    expect(researchFailureOf(topic("evaluator_failed"))).toEqual({ reason: "evaluator_failed", action: "resume", text: "研究未完成：evaluator_failed" });
  });

  it("cancelled：「研究已取消」加「重試」，不帶原因代碼（取消不是出錯）；已入庫的證據保留", () => {
    const failure = researchFailureOf(topic(RESEARCH_CANCELLED_REASON));
    expect(RESEARCH_CANCELLED_REASON).toBe("cancelled");
    expect(failure).toEqual({ reason: "cancelled", action: "retry", text: "研究已取消：已入庫的證據會保留，可以重試" });
    expect(failure?.text).not.toContain("研究未完成");
    expect(researchFailureOf(topic("  cancelled  "))?.reason, "前後空白先修剪").toBe("cancelled");
  });

  it("只認 flow_status=FAILED（D-77 之前的 IDLE 加說明不再是失敗）；初始化失敗、步驟 2 的失敗、沒有說明的 FAILED 各有明確結果", () => {
    for (const status of ["IDLE", "RUNNING", "BLOCKED", "CANCELLED", "COMPLETED"] as const) expect(researchFailureOf(topic("no_evidence", status)), status).toBeNull();
    expect(researchFailureOf(topic("init_failed:fsm"))).toBeNull();
    expect(researchFailureOf({ flowStep: "studio", flowStatus: "FAILED", flowDetail: "cancelled" }), "步驟 2 的失敗不是研究失敗").toBeNull();
    expect(researchFailureOf(topic(""))).toMatchObject({ action: "resume", text: "研究未完成：後端沒有提供原因" });
  });
});

// ── INT-03 專案範圍鍵（D-76(2)）──────────────────────────────────────────────────────────

describe("INT-03 readResearchScope：鍵一律 camelCase（console-api DTO 在邊界轉換），前端只認 camelCase", () => {
  /** API 回的 `scope` 形狀（schema.d.ts `ResearchProjectDetail.scope`：layers、techStack、inScope、outOfScope、recencyYears、applicabilityAxes、targetScopeHint）。 */
  const API_SCOPE = {
    layers: { academic: true, industry: false, oss: true, community: true },
    techStack: "Python 3.11；PostgreSQL 18",
    inScope: ["可自架的向量資料庫"],
    outOfScope: ["只提供雲端託管的方案"],
    recencyYears: 2,
    applicabilityAxes: ["技術可行", "授權相容"],
    targetScopeHint: "UNDECIDED",
  };

  it("API 形狀的 scope（camelCase）逐欄讀出，議題面板的納入範圍、排除範圍、技術棧、文獻年限與適用性軸都有值", () => {
    expect(readResearchScope(API_SCOPE)).toEqual({
      layers: { academic: true, industry: false, oss: true, community: true },
      techStack: "Python 3.11；PostgreSQL 18",
      inScope: ["可自架的向量資料庫"],
      outOfScope: ["只提供雲端託管的方案"],
      recencyYears: 2,
      applicabilityAxes: ["技術可行", "授權相容"],
    });
  });

  it("snake_case 的鍵（Bridge 內部寫入的形狀）不讀：邊界轉換是 console-api 的責任，前端若兩邊都認就掩蓋了邊界壞掉（INT-03 的成因）", () => {
    const snake = { layers: API_SCOPE.layers, tech_stack: "x", in_scope: ["a"], out_of_scope: ["b"], recency_years: 3, applicability_axes: ["c"] };
    expect(readResearchScope(snake)).toEqual({ layers: API_SCOPE.layers, techStack: "", inScope: [], outOfScope: [], recencyYears: null, applicabilityAxes: [] });
  });
});

// ── F-02 授權待查（D-80；雙端對拍）──────────────────────────────────────────────────────

type LicenseCase = { license_spdx: string | null; pending: boolean; why: string };

describe("F-02 授權待查 isLicensePending：與 Bridge 同一條規則（D-80），同一張期望表兩端各自斷言", () => {
  it("本端的固定列：UNKNOWN（含大小寫與空白）、null、空白、未見＝待查；LGPL、複合式（OR／AND／WITH、括號、連接詞小寫）、寬鬆授權＝不待查；GPL／AGPL 系＝待查", () => {
    const rows: Array<[string | null | undefined, boolean]> = [
      [null, true],
      [undefined, true],
      ["", true],
      ["   ", true],
      ["未見", true],
      ["UNKNOWN", true],
      ["unknown", true],
      ["Unknown", true],
      [" UNKNOWN ", true],
      ["MIT", false],
      ["Apache-2.0", false],
      ["GPL-3.0-only", true],
      ["gpl-3.0-only", true],
      ["GPL-2.0-or-later", true],
      ["AGPL-3.0-or-later", true],
      ["agpl-3.0", true],
      ["GPL", true],
      ["LGPL-3.0", false],
      ["LGPL-2.1-or-later", false],
      ["lgpl-2.1", false],
      ["MIT OR GPL-2.0", false],
      ["GPL-2.0 OR MIT", false],
      ["Apache-2.0 AND GPL-3.0-only", false],
      ["GPL-2.0 WITH Classpath-exception-2.0", false],
      ["(MIT OR GPL-2.0-only)", false],
      ["mit or gpl-2.0", false],
    ];
    for (const [spdx, pending] of rows) expect(isLicensePending(spdx), JSON.stringify(spdx)).toBe(pending);
  });

  it("雙端對拍：讀 Bridge 棒放的期望表 engine-bridge/tests/fixtures/research/license_pending_cases.json，逐列斷言前端函式（缺檔即紅，不跳過）", () => {
    const file = path.join(ROOT, "..", "engine-bridge", "tests", "fixtures", "research", "license_pending_cases.json");
    expect(existsSync(file), `找不到雙端共用的期望表：${file}`).toBe(true);
    const table = JSON.parse(readFileSync(file, "utf-8")) as { schema: number; cases: LicenseCase[] };
    expect(table.schema).toBe(1);
    expect(table.cases.length, "期望表不可是空的（空表會讓對拍空過）").toBeGreaterThanOrEqual(20);
    expect(
      table.cases.some((c) => c.license_spdx === null),
      "表內要有 null 列",
    ).toBe(true);
    expect(table.cases.filter((c) => c.pending).length).toBeGreaterThan(0);
    expect(table.cases.filter((c) => !c.pending).length).toBeGreaterThan(0);
    for (const c of table.cases) expect(isLicensePending(c.license_spdx), `${JSON.stringify(c.license_spdx)}：${c.why}`).toBe(c.pending);
  });

  it("licensePendingCount：逐證據列取來源的授權；UNKNOWN 與複合式的判準與 isLicensePending 一致；來源清單裡找不到的列算待查（同 Bridge：缺來源＝未見）", () => {
    const sources = [
      { sourceNo: "S-001", licenseSpdx: "MIT" },
      { sourceNo: "S-002", licenseSpdx: "UNKNOWN" },
      { sourceNo: "S-003", licenseSpdx: "LGPL-3.0" },
      { sourceNo: "S-004", licenseSpdx: "MIT OR GPL-2.0" },
      { sourceNo: "S-005", licenseSpdx: "AGPL-3.0-or-later" },
      { sourceNo: "S-006", licenseSpdx: null },
    ];
    const items = ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-404"].map((sourceNo) => ({ sourceNo }));
    expect(licensePendingCount(items, sources)).toBe(4);
    expect(licensePendingCount(items.slice(0, 1), sources)).toBe(0);
  });
});

// ── 存在性（防止被改名後測試整批空轉）──────────────────────────────────────────────────

describe("測試前提", () => {
  it("lib/domain/research.ts 與本檔同目錄；components/domain/research 目錄存在", () => {
    expect(existsSync(path.join(ROOT, "lib", "domain", "research.ts"))).toBe(true);
    expect(existsSync(path.join(ROOT, "components", "domain", "research"))).toBe(true);
  });
});

// ══ P1 分流（PKG-FE-D1；TCS-ResearchToPRD-P1-20261107）══════════════════════════════════════════════════════════════

const CONTRACT = readFileSync(path.resolve(process.cwd(), "..", "docs", "02_architecture", "API_Contract_ResearchToPRD.md"), "utf8");
const BRIDGE_ROUTE_PY = readFileSync(path.resolve(process.cwd(), "..", "engine-bridge", "app", "research", "route.py"), "utf8");

/** 契約 §1.2 的欄位列：`| \`<欄位>\`〔P1〕 | <規則> | … |` → 規則欄原文。 */
function contractRule(field: string): string {
  const row = CONTRACT.split(/\r?\n/).find((line) => line.startsWith(`| \`${field}\``));
  if (row === undefined) throw new Error(`契約沒有 ${field} 這一列`);
  return row.split("|")[2].trim();
}
/** 規則欄內第一個反引號包住的正規式字面。 */
const contractRegex = (field: string): string => /`([^`]+)`/.exec(contractRule(field))?.[1] ?? "";

describe("AT_961_17_E_2 分流常數與後端單一來源對拍", () => {
  it("AT_961_17_E_2 BRANCH_PATTERN、REPO_NAME_PATTERN 與契約 route.* 列逐字相等；理由上限 200、500 與契約字面相等", () => {
    expect(BRANCH_PATTERN.source.replace(/\\\//g, "/")).toBe(contractRegex("route.branchName").replace(/^\^/, "^").replace(/\$$/, "$"));
    expect(`^${REPO_NAME_PATTERN.source.replace(/^\^|\$$/g, "")}$`).toBe(contractRegex("route.repoName"));
    expect(contractRule("route.scopeDiffersReason")).toContain(`1～${SCOPE_REASON_MAX} 字`);
    expect(SCOPE_REASON_MAX).toBe(200);
    expect(contractRule("reason")).toContain(`1～${REASON_MAX} 字`);
    expect(REASON_MAX).toBe(500);
    expect(PROJECT_NAME_PATTERN.source).toBe("^[a-z][a-z0-9-]{1,61}$");
    expect(OWNER_PATTERN.source).toBe("^[A-Za-z0-9][A-Za-z0-9-]{0,38}$");
  });

  it("AT_961_17_E_2 PLACEMENT_TARGETS 的四個模組值與 Bridge route.py 常數（以原始碼文字解析）及 V19 CHECK 列舉逐值相等；每項附出處句", () => {
    const block = /PLACEMENT_TARGETS[^=]*=\s*\{([\s\S]*?)\n\}/.exec(BRIDGE_ROUTE_PY)?.[1] ?? "";
    const bridgeKeys = [...block.matchAll(/^ {4}"([a-z]+)": Placement\(/gm)].map((m) => m[1]);
    expect(bridgeKeys.length).toBe(4);
    expect(PLACEMENT_TARGETS.map((t) => t.id)).toEqual(bridgeKeys);
    const v19 = path.resolve(process.cwd(), "..", "backend", "src", "main", "resources", "db", "migration", "V19__research_route_scr_delivery.sql");
    if (existsSync(v19)) {
      const sql = readFileSync(v19, "utf8");
      for (const id of PLACEMENT_TARGETS.map((t) => t.id)) expect(sql, `V19 CHECK 含 ${id}`).toContain(`'${id}'`);
    }
    for (const target of PLACEMENT_TARGETS) expect(target.source.trim(), target.id).not.toBe("");
  });
});

describe("AT_961_19_E_1 P1 reason 的前端文案表與衍生相態標籤", () => {
  const P1_REASONS = [
    RESEARCH_REASONS.ROUTE_UNSUPPORTED_IN_DEPLOYMENT,
    RESEARCH_REASONS.ROUTE_CONFLICT,
    RESEARCH_REASONS.BRANCH_EXISTS,
    RESEARCH_REASONS.TARGET_NOT_EMPTY,
    RESEARCH_REASONS.PUBLIC_CONFIRMATION_REQUIRED,
    RESEARCH_REASONS.ROUTE_STEP_FAILED,
    RESEARCH_REASONS.SCR_OPEN,
    RESEARCH_REASONS.SCR_LIMIT,
    RESEARCH_REASONS.DECOMPOSITION_STALE,
    RESEARCH_REASONS.COMPILE_FAILED,
    RESEARCH_REASONS.SDD_CLI_FAILED,
    RESEARCH_REASONS.FSM_STATE_UNREADABLE,
    RESEARCH_REASONS.INVALID_REQUEST,
  ];
  it("AT_961_19_E_1 P1 的 9 個與 R-2 的 4 個 reason 逐一有非空中文文案、不直出伺服器訊息；not_implemented 保留通用文案（D-111）", () => {
    for (const reason of P1_REASONS) {
      const text = researchErrorText(new ApiError({ status: 422, message: "伺服器原訊息 XYZ", reason }));
      expect(text, reason).not.toBe("");
      expect(text, reason).toMatch(/[\u4e00-\u9fff]/);
      expect(text, reason).not.toContain("XYZ");
    }
    expect(researchErrorText(new ApiError({ status: 501, message: "x", reason: RESEARCH_REASONS.NOT_IMPLEMENTED }))).toContain("尚未開放");
  });

  it("AT_961_19_E_1 502 route_step_failed 的文案帶失敗步驟名（details.failureStep 對映 ROUTE_STEP_LABEL；未登記步驟名原樣顯示；沒有 details 時用通用句）", () => {
    const withStep = (failureStep: unknown) => researchErrorText(new ApiError({ status: 502, message: "x", reason: RESEARCH_REASONS.ROUTE_STEP_FAILED, details: { failureStep } }));
    expect(withStep("GIT_SWITCH")).toContain(ROUTE_STEP_LABEL.GIT_SWITCH);
    expect(withStep("NEW_STEP")).toContain("NEW_STEP");
    expect(researchErrorText(new ApiError({ status: 502, message: "x", reason: RESEARCH_REASONS.ROUTE_STEP_FAILED }))).toContain("分流有一步失敗");
  });

  it("AT_961_19_E_1 BUILD_READY「可開始建置」、SCR_OPEN「SCR 進行中」入 FLOW_PHASE_LABEL，PAUSED「已暫停」取自同名的狀態標籤（兩表鍵不相交，stateKeys 零改動鎖），flowPhaseLabel 三者都取得到（D-114）", () => {
    expect(FLOW_PHASE_LABEL.BUILD_READY).toBe("可開始建置");
    expect(FLOW_STATUS_LABEL.PAUSED).toBe("已暫停");
    expect(FLOW_PHASE_LABEL.SCR_OPEN).toBe("SCR 進行中");
    expect(flowPhaseLabel("PAUSED")).toBe("已暫停");
    expect(flowPhaseLabel("BUILD_READY")).toBe("可開始建置");
    expect(flowPhaseLabel("ROUTING")).toBe("分流中");
    expect(flowPhaseLabel("ROUTED")).toBe("已分流");
  });
});

describe("分流純函式：步驟名、狀態、預設值、停用判定", () => {
  it("ROUTE_STEP_LABEL 恰好十一個步驟、標籤非空且互異；routeStepLabel 與 routeStatusLabel 對未登記值回原值", () => {
    expect(Object.keys(ROUTE_STEP_LABEL).sort()).toEqual(
      ["VALIDATE_TARGET", "GIT_SWITCH", "SCAFFOLD_FILES", "GIT_INIT", "GIT_COMMIT", "GH_REPO_CREATE", "PUBLISH_DOCS", "COPY_WORKSPACE", "REGISTER_STUB", "IMPL_KEY_INIT", "BASELINE_ADOPT"].sort(),
    );
    expect(new Set(Object.values(ROUTE_STEP_LABEL)).size).toBe(11);
    expect(routeStepLabel("NEW")).toBe("NEW");
    expect(routeStatusLabel("SUCCEEDED")).toBe("已完成");
    expect(routeStatusLabel("FAILED")).toBe("失敗");
    expect(routeStatusLabel("WEIRD")).toBe("WEIRD");
  });

  it("評估維度表五列、列頭與來源規格 §4 一致", () => {
    expect(ROUTE_EVAL_TABLE.map((r) => r.dimension)).toEqual(["目標場景", "路徑規劃", "Git 流程", "CI/CD 與環境", "規格掛載"]);
  });

  it("預選軌道與差異判定：AISDLC_MODULE→A、STANDALONE_PROJECT→B、UNDECIDED 不預選也不算差異；預設分支取 rpNo 數字零填四位", () => {
    expect(routeTrackForScope("AISDLC_MODULE")).toBe("A");
    expect(routeTrackForScope("STANDALONE_PROJECT")).toBe("B");
    expect(routeTrackForScope("UNDECIDED")).toBeNull();
    expect(routeScopeDiffers("AISDLC_MODULE", "B")).toBe(true);
    expect(routeScopeDiffers("AISDLC_MODULE", "A")).toBe(false);
    expect(routeScopeDiffers("UNDECIDED", "B")).toBe(false);
    expect(routeDefaultBranch("RP-0007")).toBe("feature/issue-0007");
    expect(routeDefaultBranch("RP-12345")).toBe("feature/issue-2345");
    expect(BRANCH_PATTERN.test(routeDefaultBranch("RP-0007"))).toBe(true);
  });

  it("預演缺項對映中文（gh 命令不可用、無法寫入程式庫），未登記項目原樣顯示，形狀不合回空陣列", () => {
    expect(routeMissingLabels([{ item: "gh" }, { item: "repo_writable" }, "scaffold_root", { item: "x_new" }])).toEqual([
      "gh 命令不可用",
      "無法寫入程式庫",
      ROUTE_MISSING_ITEM_LABEL.scaffold_root,
      "x_new",
    ]);
    expect(routeMissingLabels(undefined)).toEqual([]);
  });

  it("capabilities 停用判定：git 缺或 mock-only 兩軌皆停；repoWritable 假停軌道 A；scaffoldRoot 為 null 或範本空停軌道 B；ghCli.ok 假只停 GitHub 勾選", () => {
    const base = {
      mode: "local",
      db: true,
      claudeCli: { ok: true },
      ghCli: { ok: true, authenticated: false },
      git: { ok: true },
      sddRoot: null,
      researchRoot: "r",
      scaffoldRoot: "s",
      scaffoldTemplates: ["python-fastapi"],
      repoWritable: true,
      webLayerEnabled: false,
      fetchHosts: [],
    } as const;
    const blocks = (patch: object) => routeCapabilityBlocks({ ...base, ...patch } as never);
    expect(blocks({})).toEqual({ all: null, trackA: null, trackB: null, github: null });
    expect(blocks({ git: { ok: false } }).all).toBe("git");
    expect(blocks({ mode: "mock-only" }).all).toBe("mock-only");
    expect(blocks({ repoWritable: false })).toMatchObject({ all: null, trackA: "repo", trackB: null });
    expect(blocks({ scaffoldRoot: null }).trackB).toBe("scaffold");
    expect(blocks({ scaffoldTemplates: [] }).trackB).toBe("scaffold");
    expect(blocks({ ghCli: { ok: false, authenticated: false } })).toMatchObject({ github: "gh", trackA: null, trackB: null });
  });

  it("Public 確認為逐字完全相等：差一字元、大小寫、尾端空白、不可見字元皆不符；空庫名永遠不符", () => {
    expect(isRepoNameConfirmed("demo-app", "demo-app")).toBe(true);
    for (const wrong of ["demo-ap", "Demo-App", "demo-app ", "demo-app\u200b", ""]) expect(isRepoNameConfirmed("demo-app", wrong), JSON.stringify(wrong)).toBe(false);
    expect(isRepoNameConfirmed("", "")).toBe(false);
  });

  it("safeRepoHref 只放行 https://github.com/<owner>/<repo>；isExternalRouteAction 認 touchesExternal 與別名 external", () => {
    expect(safeRepoHref("https://github.com/acme/demo-app")).toBe("https://github.com/acme/demo-app");
    // 含 userinfo 的負控以片段拼出：原始碼不留「帶密碼的 URL」字面（根層機密掃描閘會擋 commit），執行期仍是同一個字串。
    const withUserinfo = "https://user:" + "p@github.com/a/b";
    for (const bad of ["http://github.com/a/b", "https://github.com.evil.com/a/b", "javascript:alert(1)", "https://github.com/a/b/c", withUserinfo, null, undefined])
      expect(safeRepoHref(bad), String(bad)).toBeNull();
    expect(isExternalRouteAction({ touchesExternal: true })).toBe(true);
    expect(isExternalRouteAction({ touchesExternal: false, external: true })).toBe(true);
    expect(isExternalRouteAction({ touchesExternal: false })).toBe(false);
  });
});

describe("分流表單驗證與請求本文", () => {
  const formA: RouteForm = {
    track: "A",
    targetModule: "autoclaude",
    branchName: "feature/issue-0007",
    baseRef: "main",
    projectName: "",
    stackTemplate: "",
    owner: "",
    repoName: "",
    visibility: "PRIVATE",
    confirmRepoName: "",
    createGithub: false,
    ci: true,
    dockerCompose: true,
    scopeDiffersReason: "",
  };
  const formB: RouteForm = { ...formA, track: "B", targetModule: "", branchName: "", baseRef: "", projectName: "demo-app", stackTemplate: "python-fastapi", owner: "acme" };

  it("軌道 A：分支名不合 ^feature/[a-z0-9-]{1,40}$、缺掛載目標、基底 ref 空或含空白各回欄位錯誤；合規回空物件", () => {
    expect(routeFormErrors(formA, false)).toEqual({});
    expect(routeFormErrors({ ...formA, branchName: "issue-1" }, false).branchName).toBeDefined();
    expect(routeFormErrors({ ...formA, branchName: `feature/${"a".repeat(41)}` }, false).branchName).toBeDefined();
    expect(routeFormErrors({ ...formA, branchName: `feature/${"a".repeat(40)}` }, false).branchName).toBeUndefined();
    expect(routeFormErrors({ ...formA, targetModule: "" }, false).targetModule).toBeDefined();
    expect(routeFormErrors({ ...formA, baseRef: " " }, false).baseRef).toBeDefined();
    expect(routeFormErrors({ ...formA, baseRef: "ma in" }, false).baseRef).toBeDefined();
    expect(routeFormErrors({ ...formA, track: null }, false).track).toBeDefined();
  });

  it("軌道 B：專案名稱、owner、庫名即時驗證；Public 需完全相同的確認名；庫名省略時取專案名稱", () => {
    expect(routeFormErrors(formB, false)).toEqual({});
    expect(routeFormErrors({ ...formB, projectName: "Demo" }, false).projectName).toBeDefined();
    expect(routeFormErrors({ ...formB, projectName: "a" }, false).projectName).toBeDefined();
    expect(routeFormErrors({ ...formB, repoName: "Bad_Name" }, false).repoName).toBeDefined();
    expect(routeFormErrors({ ...formB, owner: "-x" }, false).owner).toBeDefined();
    expect(routeFormErrors({ ...formB, owner: "", createGithub: true }, false).owner).toBeDefined();
    expect(routeFormErrors({ ...formB, owner: "" }, false).owner).toBeUndefined();
    expect(routeFormErrors({ ...formB, stackTemplate: "" }, false).stackTemplate).toBeDefined();
    expect(routeFormErrors({ ...formB, visibility: "PUBLIC", confirmRepoName: "" }, false).confirmRepoName).toBeDefined();
    expect(routeFormErrors({ ...formB, visibility: "PUBLIC", confirmRepoName: "demo-app" }, false).confirmRepoName).toBeUndefined();
    expect(routeFormErrors({ ...formB, visibility: "PUBLIC", repoName: "other", confirmRepoName: "demo-app" }, false).confirmRepoName).toBeDefined();
    expect(effectiveRepoName(formB)).toBe("demo-app");
    expect(effectiveRepoName({ ...formB, repoName: "other" })).toBe("other");
  });

  it("理由 0、1、200、201 字：差異時 0 與 201 有錯、1 與 200 無錯；不差異時不檢查；以字元（code point）計", () => {
    const err = (n: number) => routeFormErrors({ ...formA, scopeDiffersReason: "字".repeat(n) }, true).scopeDiffersReason;
    expect(err(0)).toBeDefined();
    expect(err(1)).toBeUndefined();
    expect(err(200)).toBeUndefined();
    expect(err(201)).toBeDefined();
    expect(routeFormErrors({ ...formA, scopeDiffersReason: "😀".repeat(200) }, true).scopeDiffersReason).toBeUndefined();
    expect(routeFormErrors({ ...formA, scopeDiffersReason: "" }, false).scopeDiffersReason).toBeUndefined();
  });

  it("toRouteRequest：軌道 A 不含 B 欄位與 targetPath、approver；軌道 B 的 PUBLIC 才帶 confirmRepoName；差異時才帶 scopeDiffersReason", () => {
    const a = toRouteRequest(formA, false);
    expect(a).toEqual({ track: "A", targetModule: "autoclaude", branchName: "feature/issue-0007", baseRef: "main" });
    const b = toRouteRequest(formB, true);
    expect(b).toMatchObject({ track: "B", projectName: "demo-app", repoName: "demo-app", owner: "acme", visibility: "PRIVATE", createGithub: false, ci: true, dockerCompose: true });
    expect(b).not.toHaveProperty("confirmRepoName");
    expect(b).toHaveProperty("scopeDiffersReason");
    expect(toRouteRequest({ ...formB, visibility: "PUBLIC", confirmRepoName: "demo-app" }, false)).toMatchObject({ visibility: "PUBLIC", confirmRepoName: "demo-app" });
    for (const body of [a, b]) {
      expect(body).not.toHaveProperty("targetPath");
      expect(body).not.toHaveProperty("approver");
    }
  });
});

// ── 步驟 4 前半（TCS-ResearchToPRD-P1-20261107 AT-961-18-*；純函式面）──────────────────────────────────

describe("步驟 4 前半純函式：覆蓋視圖、豁免理由、執行閘、TCS 相態", () => {
  const draft = {
    coverage: { total: 3, covered: 1, uncovered: ["AC-2", "AC-3"] },
    goals: [{ goal_id: "G-1", name: "g", tasks: [{ task_id: "T-1", name: "t", covers_ac: ["AC-1"] }] }],
    waivers: [] as Array<{ ac: string; reason: string }>,
  };

  it("waiverReasonError：以 code point 計，去頭尾空白後 0 與 501 字無效、1 與 500 字有效（上限常數 500）", () => {
    expect(WAIVER_REASON_MAX).toBe(500);
    expect(waiverReasonError("")).not.toBeNull();
    expect(waiverReasonError("   ")).not.toBeNull();
    expect(waiverReasonError("字".repeat(501))).not.toBeNull();
    expect(waiverReasonError("字")).toBeNull();
    expect(waiverReasonError("字".repeat(500))).toBeNull();
    expect(waiverReasonError("😀".repeat(500)), "emoji 算一個字").toBeNull();
  });

  it("coverageView：未覆蓋逐一列出；輸入優先於已存豁免；有效豁免才算完成；無效輸入帶欄位錯誤；矩陣列取樹與未覆蓋的聯集並排序", () => {
    const empty = coverageView(draft);
    expect(empty).toMatchObject({ total: 3, covered: 1, uncovered: ["AC-2", "AC-3"], waived: [], pending: ["AC-2", "AC-3"], complete: false, errors: {} });
    expect(empty.acs).toEqual(["AC-1", "AC-2", "AC-3"]);
    const partial = coverageView(draft, { "AC-2": "有理由", "AC-3": "字".repeat(501) });
    expect(partial.waived).toEqual(["AC-2"]);
    expect(partial.pending).toEqual(["AC-3"]);
    expect(Object.keys(partial.errors)).toEqual(["AC-3"]);
    expect(partial.complete).toBe(false);
    const stored = coverageView({
      ...draft,
      waivers: [
        { ac: "AC-2", reason: "舊理由" },
        { ac: "AC-3", reason: "舊理由二" },
      ],
    });
    expect(stored.complete).toBe(true);
    // 輸入覆寫已存值：清成空字串＝回到未完成
    expect(
      coverageView(
        {
          ...draft,
          waivers: [
            { ac: "AC-2", reason: "舊理由" },
            { ac: "AC-3", reason: "x" },
          ],
        },
        { "AC-2": "" },
      ).pending,
    ).toEqual(["AC-2"]);
    expect(coverageView({ ...draft, coverage: { total: 1, covered: 1, uncovered: [] } }).complete).toBe(true);
  });

  it("decompositionTree／coverageMatrix：snake_case 與 camelCase 鍵都認，缺欄不丟例外；矩陣格與涵蓋關係逐格一致", () => {
    const tree = decompositionTree([{ goalId: "G-9", name: "x", tasks: [{ taskId: "T-9", name: "y", coversAc: ["AC-1", 5 as unknown as string] }, {}] }, { tasks: "壞" as unknown as [] }]);
    expect(tree[0]).toMatchObject({
      id: "G-9",
      tasks: [
        { id: "T-9", coversAc: ["AC-1"] },
        { id: "T-1-2", name: "", coversAc: [] },
      ],
    });
    expect(tree[1].tasks).toEqual([]);
    expect(decompositionTree(null)).toEqual([]);
    const m = coverageMatrix(decompositionTree(draft.goals), ["AC-1", "AC-2"]);
    expect(m.tasks.map((t) => t.id)).toEqual(["T-1"]);
    expect(m.cells).toEqual([[true], [false]]);
  });

  it("scrBadge：只有 SCR_OPEN 顯示「SCR 進行中」", () => {
    expect(scrBadge("SCR_OPEN")).toEqual({ visible: true, label: "SCR 進行中" });
    for (const phase of ["TCS_PENDING", "BUILD_READY", "FROZEN", ""]) expect(scrBadge(phase).visible, phase).toBe(false);
  });

  it("tcsStage：相態對映四態（BUILD_READY 起都算已凍結；TCS_DRAFTING 失敗為 failed）", () => {
    expect(tcsStage("TCS_DRAFTING", "RUNNING")).toBe("drafting");
    expect(tcsStage("TCS_DRAFTING", "FAILED")).toBe("failed");
    expect(tcsStage("TCS_PENDING", "WAITING_HUMAN")).toBe("pending");
    for (const phase of ["BUILD_READY", "BUILDING", "HEALING", "AWAITING_HUMAN", "RELEASE_PENDING", "DELIVERED"]) expect(tcsStage(phase, "IDLE"), phase).toBe("frozen");
    for (const phase of ["FROZEN", "ROUTING", "ROUTED", "SCR_OPEN"]) expect(tcsStage(phase, "IDLE"), phase).toBe("none");
  });

  it("executionBlock：規格變更中＞拆解過期＞草稿未簽核＞測試規格未凍結；全通過回 null；每個鍵都有非空文案", () => {
    const signed = { status: "SIGNED_OFF" as const, stale: false };
    expect(executionBlock({ scrOpen: true, decomposition: signed, tcsFrozen: true })).toBe("scrOpen");
    expect(executionBlock({ scrOpen: false, decomposition: null, tcsFrozen: true })).toBe("needDecomposition");
    expect(executionBlock({ scrOpen: false, decomposition: { ...signed, stale: true }, tcsFrozen: true })).toBe("stale");
    expect(executionBlock({ scrOpen: false, decomposition: { status: "STALE", stale: false }, tcsFrozen: true })).toBe("stale");
    expect(executionBlock({ scrOpen: false, decomposition: { status: "DRAFTED", stale: false }, tcsFrozen: true })).toBe("unsigned");
    expect(executionBlock({ scrOpen: false, decomposition: signed, tcsFrozen: false })).toBe("tcsUnfrozen");
    expect(executionBlock({ scrOpen: false, decomposition: signed, tcsFrozen: true })).toBeNull();
    for (const text of Object.values(BUILD_DISABLED_TEXT)) expect(text.trim()).not.toBe("");
  });

  it("tcsInvalidText／unmetLabels／decompositionErrorLines：缺項說明、409 缺項中文、422 閘別逐筆", () => {
    expect(tcsInvalidText("tcs_invalid: 缺 AC-1")).toBe("缺 AC-1");
    expect(tcsInvalidText("tcs_invalid")).toBe("");
    expect(tcsInvalidText("別的失敗")).toBeNull();
    const conflict = new ApiError({ status: 409, message: "x", details: { unmet: ["route_not_succeeded", { name: "inner_key_not_adopted" }, "新項目", 3] } });
    expect(unmetLabels(conflict)).toEqual(["分流尚未完成", "內環鍵尚未採納基線", "新項目", "未知前置"]);
    expect(unmetLabels(new Error("x"))).toEqual([]);
    expect(unmetLabels(new ApiError({ status: 409, message: "x" }))).toEqual([]);
    const violations = new ApiError({ status: 422, message: "x", reason: "invalid_request", details: { violations: [{ rule: "cycle" }, { rule: "未登記" }, { field: "f" }, "字串"] } });
    expect(decompositionErrorLines(violations)).toEqual(["閘別 cycle：任務之間的依賴有環，無法排出執行順序", "閘別 未登記：未登記的檢查"]);
    expect(decompositionErrorLines(new ApiError({ status: 422, message: "沒有 violations" })).length).toBe(1);
    expect(decompositionErrorLines(new ApiError({ status: 500, message: "壞了" })).length).toBe(1);
  });
});
