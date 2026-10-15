/**
 * 執行頁與監控頁的測試夾具（vitest 用）：契約 §1.2、§1.3 的 ProjectDetail／ExecutionRunDetail／Dag／Checkpoint／審核項／告警／指標。
 * 形狀取自 schema-p3-6.d.ts；id 用短字串（測試只比對相等，不驗 UUID 格式）。
 */
import type {
  Alert,
  Checkpoint,
  Dag,
  ExecutionRunDetail,
  ExecutionRunSummary,
  ProjectDetail,
  ProjectMetrics,
  ReviewItem,
} from "@/lib/api/types";

export const TS = "2026-10-15T08:30:12Z";

export function projectDetail(patch: Partial<ProjectDetail> = {}): ProjectDetail {
  return {
    id: "p1",
    name: "AISDLC Core Platform",
    executionPath: "/work/core",
    passCriteria: "- ok",
    status: "READY",
    autonomyLevel: 3,
    signedOff: true,
    goalsCount: 2,
    tasksCount: 3,
    tasksDone: 0,
    createdAt: TS,
    updatedAt: TS,
    goals: [
      { id: "g1", name: "基礎", status: "PENDING", sortOrder: 0, signedOff: true, taskCount: 2, completedTaskCount: 0 },
      { id: "g2", name: "核心", status: "PENDING", sortOrder: 1, signedOff: true, taskCount: 1, completedTaskCount: 0 },
    ],
    ...patch,
  };
}

export function taskSummary(id: string, goalId: string, name: string, patch: Record<string, unknown> = {}) {
  return { id, goalId, name, sortOrder: 0, status: "PENDING", retryCount: 0, maxRetries: 1, signedOff: true, updatedAt: TS, ...patch };
}

export function runSummary(patch: Partial<ExecutionRunSummary> = {}): ExecutionRunSummary {
  return {
    id: "r1",
    projectId: "p1",
    runNumber: 1,
    status: "RUNNING",
    autonomyLevel: 4,
    scopeMode: "ALL",
    totalTokensUsed: 1240,
    tokenBudget: 100000,
    startedAt: TS,
    durationSec: 12,
    tasksTotal: 3,
    tasksCompleted: 1,
    tasksFailed: 0,
    successRate: 100,
    ...patch,
  };
}

export function runDetail(patch: Partial<ExecutionRunDetail> = {}): ExecutionRunDetail {
  return {
    id: "r1",
    projectId: "p1",
    runNumber: 1,
    status: "RUNNING",
    bridgeStatus: "RUNNING",
    autonomyLevel: 4,
    scope: { mode: "ALL", goalIds: [], taskIds: [] },
    totalTokensUsed: 1240,
    tokenBudget: 100000,
    startedAt: TS,
    completedSteps: 1,
    totalSteps: 3,
    lastEventSeq: 20,
    elapsedSec: 12,
    pendingReviews: [],
    bridge: { connected: true, instance: "e2e-bridge", status: "RUNNING", runKnown: true, checkedAt: TS },
    ...patch,
  };
}

export function reviewItem(patch: Partial<ReviewItem> = {}): ReviewItem {
  return {
    id: "rv1",
    runId: "r1",
    kind: "TASK_CONFIRM",
    status: "PENDING",
    taskId: "t2",
    goalId: "g1",
    taskName: "設定",
    goalName: "基礎",
    reason: "Level 1：請確認是否繼續執行任務「設定」",
    requestedAt: TS,
    allowedDecisions: ["APPROVE", "REJECT"],
    ...patch,
  };
}

export function dag(): Dag {
  return {
    runId: "r1",
    statusAsOf: TS,
    nodes: [
      { id: "g1", kind: "GOAL", label: "基礎", status: "IN_PROGRESS", sequence: 1 },
      { id: "g2", kind: "GOAL", label: "核心", status: "PENDING", sequence: 2 },
      { id: "t1", kind: "TASK", label: "初始化", status: "COMPLETED", goalId: "g1", stepId: "G1-T1", sequence: 1 },
      { id: "t2", kind: "TASK", label: "設定", status: "RUNNING", goalId: "g1", stepId: "G1-T2", sequence: 2 },
      { id: "t3", kind: "TASK", label: "實作", status: "PENDING", goalId: "g2", stepId: "G2-T1", sequence: 3 },
    ],
    edges: [
      { from: "g1", to: "g2", kind: "DEPENDENCY" },
      { from: "g1", to: "t1", kind: "CONTAINS" },
      { from: "g1", to: "t2", kind: "CONTAINS" },
      { from: "g2", to: "t3", kind: "CONTAINS" },
    ],
  };
}

export function checkpoints(): Checkpoint[] {
  return [
    { id: "c1", runId: "r1", name: "after-G1-T1", createdAt: TS, isAutomatic: true, stepIdx: 1, stepId: "G1-T2", completedSteps: 1 },
    { id: "c2", runId: "r1", name: "after-G1-T2", createdAt: "2026-10-15T08:31:12Z", isAutomatic: true, stepIdx: 2, stepId: "G2-T1", completedSteps: 2 },
  ];
}

const mv = (value: number | null, previousValue: number | null = null, delta: number | null = null) => ({ value, previousValue, delta });

export function metrics(patch: Partial<ProjectMetrics> = {}): ProjectMetrics {
  return {
    projectId: "p1",
    runId: "r1",
    from: "2026-10-14T08:40:00Z",
    to: "2026-10-15T08:40:00Z",
    generatedAt: "2026-10-15T08:40:00Z",
    taskCompletionRate: mv(34.8, 22.5, 12.3),
    taskSuccessRate: mv(92.3, 94.4, -2.1),
    retryRate: mv(7.7, 6.2, 1.5),
    totalTokens: mv(45230, 36800, 8430),
    tokenBudgetUsageRate: mv(45.2),
    averageRetryCount: mv(0.5),
    projectCompletionRate: mv(13),
    goalAchievementRate: mv(50),
    averageTaskDurationSec: mv(48.2),
    agentAvailability: mv(100),
    tokenBudget: 100000,
    taskStatusDistribution: { PENDING: 7, QUEUED: 0, BLOCKED: 0, RUNNING: 2, VALIDATING: 0, COMPLETED: 13, FAILED: 1, ESCALATED: 0, PAUSED: 0, SKIPPED: 0, CANCELLED: 0 },
    taskDurations: [
      { taskId: "t1", taskName: "T1", goalName: "基礎", durationSec: 45 },
      { taskId: "t2", taskName: "T2", goalName: "基礎", durationSec: 32 },
      { taskId: "t3", taskName: "T3", goalName: "核心", durationSec: 68 },
      { taskId: "t4", taskName: "T4", goalName: "核心", durationSec: 18 },
    ],
    retryDistribution: [0, 1, 2, 3, 4, 5].map((retries) => ({ retries, tasks: retries === 0 ? 20 : retries === 1 ? 3 : 0 })),
    ...patch,
  };
}

export function alert(patch: Partial<Alert> = {}): Alert {
  return {
    id: "a1",
    projectId: "p1",
    runId: "r1",
    rule: "TOKEN_BUDGET_WARNING",
    severity: "WARNING",
    subject: "run:r1",
    message: "Token 使用量已達預算的 83%（1240 / 1500）",
    createdAt: "2026-10-15T08:30:20Z",
    acknowledged: false,
    ...patch,
  };
}
