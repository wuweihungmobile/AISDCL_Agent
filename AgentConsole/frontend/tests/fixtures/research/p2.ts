/**
 * ResearchToPRD P2 前端夾具（TCS-ResearchToPRD-P2-20261107 §5.2；IFACE-P2 §1、§3、§6）：看板、自癒、交付概覽、追溯表的黃金資料。
 * **必填欄全給值，不放寬為選填**（D-135）；FSM 衍生欄 null 的情境另以 `kanbanUnreachable` 產生。
 */
import type { ResearchDeliveryOverview, ResearchHealing, ResearchKanban, ResearchPendingReview, ResearchTraceability } from "@/lib/api/types";
import { CONSOLE_PROJECT_ID, R3, T1, T2 } from "./ids";

export const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
export const REVIEW_ESCALATED = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
export const REVIEW_AGENT = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";

export const PENDING_ESCALATED: ResearchPendingReview = {
  reviewId: REVIEW_ESCALATED,
  runId: RUN_ID,
  kind: "ESCALATED",
  taskId: "task-7",
  reason: "自癒重試耗盡：測試仍失敗",
  createdAt: T1,
  allowedDecisions: ["APPROVE", "REJECT", "RETRY", "SKIP"],
};
export const PENDING_AGENT: ResearchPendingReview = {
  reviewId: REVIEW_AGENT,
  runId: RUN_ID,
  kind: "AGENT_REQUEST",
  taskId: null,
  reason: "Agent 請求審核：是否採用方案 B",
  createdAt: T2,
  allowedDecisions: ["APPROVE", "REJECT"],
};

/** 看板黃金資料：拆解已簽核、測試規格已凍結、實作中（3／5）、自癒無事、回歸未達標；Bridge 可達。 */
export const KANBAN: ResearchKanban = {
  researchId: R3,
  consoleProjectId: CONSOLE_PROJECT_ID,
  latestRunId: RUN_ID,
  generatedAt: T2,
  bridgeReachable: true,
  snapshotAt: null,
  stale: false,
  scrOpen: false,
  columns: {
    decompose: { done: true, status: "SIGNED_OFF", tasksCount: 5, stale: false },
    tcs: { done: true, stage2Frozen: true, negotiated: true, fsmState: "IMPLEMENTATION" },
    implement: { done: false, fsmState: "IMPLEMENTATION", tasks: { total: 5, running: 1, completed: 3, skipped: 0, failed: 0, escalated: 0, retrying: 1 } },
    healing: { done: true, retryingSteps: 0, escalatedTasks: 0, maxRetries: 3 },
    regression: {
      done: false,
      fsmState: "IMPLEMENTATION",
      releaseReady: false,
      rtm: { runId: RUN_ID, atPassed: 8, atTotal: 12, acCovered: 6, acTotal: 10, acPct: 60, fullyCovered: false, advisory: true },
      rtmAvailable: true,
    },
  },
  pendingReviews: [],
  gates: [],
};

export const kanbanWith = (patch: Partial<ResearchKanban>): ResearchKanban => ({ ...KANBAN, ...patch });
export const kanbanPending = (...reviews: ResearchPendingReview[]): ResearchKanban => kanbanWith({ pendingReviews: reviews });

/** Bridge 不可達：FSM 衍生欄一律 null 並帶 `unknown`（不猜）；DB 欄位仍在。 */
export const kanbanUnreachable = (): ResearchKanban => ({
  ...KANBAN,
  bridgeReachable: false,
  stale: true,
  snapshotAt: "2026-11-07T09:00:00+08:00",
  columns: {
    ...KANBAN.columns,
    tcs: { done: false, stage2Frozen: null, negotiated: false, fsmState: null, unknown: true as const },
    implement: { ...KANBAN.columns.implement, done: false, fsmState: null, unknown: true as const },
    regression: { done: false, fsmState: null, releaseReady: null, rtm: null, rtmAvailable: false, unknown: true as const },
  },
});

export const HEALING: ResearchHealing = {
  researchId: R3,
  rows: [
    {
      runId: RUN_ID,
      taskId: "task-3",
      stepNumber: 11,
      attempt: 1,
      status: "RETRYING",
      excerpt: "AssertionError: expected 3 got 4",
      occurredAt: T1,
      resolved: false,
      escalated: false,
      specChangeForbidden: false,
      attribution: null,
      patchResult: null,
    },
    {
      runId: RUN_ID,
      taskId: "task-3",
      stepNumber: 12,
      attempt: 2,
      status: "FAILED",
      excerpt: "AssertionError: expected 3 got 5",
      occurredAt: T2,
      resolved: false,
      escalated: false,
      specChangeForbidden: false,
      attribution: null,
      patchResult: null,
    },
    {
      runId: RUN_ID,
      taskId: "task-7",
      stepNumber: 20,
      attempt: 3,
      status: "FAILED",
      excerpt: "timeout after 30s",
      occurredAt: T2,
      resolved: false,
      escalated: true,
      specChangeForbidden: false,
      attribution: null,
      patchResult: null,
    },
  ],
  maxRetries: 3,
  logSyncedThrough: T2,
  retryingSteps: 0,
  escalatedTasks: 0,
  logLag: 0,
  specChange: null,
};

export const TRACEABILITY: ResearchTraceability = {
  rows: [
    {
      ac: "AC-R2P-01-1",
      userStory: "US-01",
      gherkinSummary: { given: "專案", when: "開啟", then: "顯示" },
      unitStatus: "PASS",
      e2eStatus: "NOT_RUN",
      lastRunAt: T2,
      source: ["task:t1", "RTM-COVERAGE-demo.yaml"],
    },
    {
      ac: "AC-R2P-01-2",
      userStory: "US-01",
      gherkinSummary: { given: "無權", when: "送出", then: "拒絕" },
      unitStatus: "FAIL",
      e2eStatus: "NOT_RUN",
      lastRunAt: T1,
      source: ["task:t2", "RTM-COVERAGE-demo.yaml"],
    },
    { ac: "AC-R2P-02-1", userStory: "US-02", gherkinSummary: { given: "x", when: "y", then: "z" }, unitStatus: "NONE", e2eStatus: "NOT_RUN", lastRunAt: null, source: [] },
  ],
  totals: { acTotal: 3, covered: 1, uncovered: 2, frTotal: 2 },
  rtm: { runId: RUN_ID, fullyCovered: false, acPct: 33.3, advisory: true },
  generatedAt: T2,
};

export const DELIVERY_OVERVIEW: ResearchDeliveryOverview = {
  deliveries: [],
  snapshot: null,
  projectRoot: "/work/alpha",
  containerMode: false,
  preconditions: { releaseReady: false, rtmFull: false, scrOpen: false, hasOrigin: true, ghAvailable: true },
};
