import type { ResearchFlow, ResearchFlowStatus, ResearchFlowStepId, ResearchProjectDetail, ResearchProjectSummary } from "@/lib/api/types";
import { deriveSteps } from "@/lib/domain/research";
import { CONSOLE_PROJECT_ID, R1, R2, R3, T0, T1, T2 } from "./ids";

/** 流程脊（API-RP-04 的 `flow`）：五步狀態由 deriveSteps 的同一規則算出，`effective` 取 DB 游標（步驟 1～3 直接用游標；後端衍生的相態只在步驟 4 之後）。 */
export function flowOf(id: string, current: ResearchFlowStepId, phase: string, status: ResearchFlowStatus, opts: { furthest?: ResearchFlowStepId; detail?: string } = {}): ResearchFlow {
  return {
    currentStep: current,
    furthestStep: opts.furthest ?? current,
    steps: deriveSteps(current, status).map(({ id: stepId, label, state }) => ({ id: stepId, label, state })),
    effective: { step: current, phase, status, detail: opts.detail ?? "" },
    resumeHref: `/research/${id}?step=${current}`,
  };
}

const SCOPE = {
  layers: { academic: true, industry: false, oss: true, community: true },
  techStack: "Python 3.11；PostgreSQL 18",
  inScope: ["可自架的向量資料庫"],
  outOfScope: ["只提供雲端託管的方案"],
  recencyYears: 3,
  applicabilityAxes: ["技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本"],
};

type Seed = Pick<ResearchProjectSummary, "id" | "rpNo" | "slug" | "title" | "flowStep" | "flowPhase" | "flowStatus"> & Partial<ResearchProjectSummary>;

function summaryOf(seed: Seed): ResearchProjectSummary {
  return {
    depthLevel: "STANDARD",
    targetScope: "UNDECIDED",
    flowDetail: "",
    consoleProjectId: null,
    createdBy: "operator",
    createdAt: T0,
    updatedAt: T2,
    archivedAt: null,
    ...seed,
  };
}

export const SUMMARY_R1 = summaryOf({ id: R1, rpNo: "RP-0001", slug: "agent-memory-gc", title: "Agent 記憶體回收策略研究", flowStep: "topic", flowPhase: "RESEARCHING", flowStatus: "RUNNING" });
export const SUMMARY_R2 = summaryOf({ id: R2, rpNo: "RP-0002", slug: "vector-db", title: "向量資料庫選型", flowStep: "studio", flowPhase: "GATE0_PENDING", flowStatus: "WAITING_HUMAN" });
export const SUMMARY_R3 = summaryOf({
  id: R3,
  rpNo: "RP-0003",
  slug: "rag-eval",
  title: "RAG 評測基準",
  flowStep: "route",
  flowPhase: "FROZEN",
  flowStatus: "IDLE",
  consoleProjectId: CONSOLE_PROJECT_ID,
  updatedAt: T1,
});

/** 清單（API-RP-02）：三個專案，其中 R3 有關聯的 Console 專案。 */
export const PROJECT_LIST: ResearchProjectSummary[] = [SUMMARY_R1, SUMMARY_R2, SUMMARY_R3];

export type DetailVariant = "topicRunning" | "topicReady" | "studio" | "reviewing" | "gate0" | "escalated" | "frozen" | "blocked" | "initFailed";

type DetailSeed = {
  summary: ResearchProjectSummary;
  phase: string;
  status: ResearchFlowStatus;
  furthest?: ResearchFlowStepId;
  detail?: string;
  counts: ResearchProjectDetail["counts"];
  headPrdVersion: number | null;
  lastReview: ResearchProjectDetail["lastReview"];
};

function detailOf(seed: DetailSeed): ResearchProjectDetail {
  const { summary } = seed;
  return {
    ...summary,
    flowPhase: seed.phase,
    flowStatus: seed.status,
    flowDetail: seed.detail ?? "",
    topic: `${summary.title}：比較可自架的方案，評估授權、維護風險與效能邊界`,
    scope: SCOPE,
    scopeRev: 1,
    fsmProject: `research-${summary.slug}`,
    fsmGeneration: 1,
    flow: flowOf(summary.id, summary.flowStep, seed.phase, seed.status, { furthest: seed.furthest, detail: seed.detail }),
    counts: seed.counts,
    headPrdVersion: seed.headPrdVersion,
    lastReview: seed.lastReview,
    parentResearchId: null,
  };
}

const ZERO = { sources: 0, evidenceItems: 0, prdVersions: 0, reviewRounds: 0, openDefects: 0 };

/** 專案詳情的各種情境（API-RP-04）；`detailVariant(name, patch)` 取副本並套用修改。 */
const DETAIL_SEEDS: Record<DetailVariant, DetailSeed> = {
  topicRunning: { summary: { ...SUMMARY_R1 }, phase: "RESEARCHING", status: "RUNNING", counts: { ...ZERO, sources: 3, evidenceItems: 2 }, headPrdVersion: null, lastReview: null },
  topicReady: {
    summary: { ...SUMMARY_R1, flowPhase: "EVIDENCE_READY", flowStatus: "IDLE" },
    phase: "EVIDENCE_READY",
    status: "IDLE",
    counts: { ...ZERO, sources: 6, evidenceItems: 8 },
    headPrdVersion: null,
    lastReview: null,
  },
  studio: {
    summary: { ...SUMMARY_R2, flowPhase: "DRAFTING", flowStatus: "IDLE" },
    phase: "DRAFTING",
    status: "IDLE",
    counts: { sources: 6, evidenceItems: 8, prdVersions: 2, reviewRounds: 1, openDefects: 3 },
    headPrdVersion: 2,
    lastReview: { round: 1, weightedScore: 79.9, minDimensionScore: 70, passed: false, escalated: false },
  },
  reviewing: {
    summary: { ...SUMMARY_R2, flowPhase: "REVIEWING", flowStatus: "RUNNING" },
    phase: "REVIEWING",
    status: "RUNNING",
    counts: { sources: 6, evidenceItems: 8, prdVersions: 2, reviewRounds: 1, openDefects: 3 },
    headPrdVersion: 2,
    lastReview: { round: 1, weightedScore: 79.9, minDimensionScore: 70, passed: false, escalated: false },
  },
  gate0: {
    summary: { ...SUMMARY_R2 },
    phase: "GATE0_PENDING",
    status: "WAITING_HUMAN",
    counts: { sources: 6, evidenceItems: 8, prdVersions: 3, reviewRounds: 2, openDefects: 1 },
    headPrdVersion: 3,
    lastReview: { round: 2, weightedScore: 90.3, minDimensionScore: 88, passed: true, escalated: false },
  },
  escalated: {
    summary: { ...SUMMARY_R2, flowPhase: "REVISING", flowStatus: "ESCALATED" },
    phase: "REVISING",
    status: "ESCALATED",
    counts: { sources: 6, evidenceItems: 8, prdVersions: 4, reviewRounds: 3, openDefects: 4 },
    headPrdVersion: 4,
    lastReview: { round: 3, weightedScore: 84.6, minDimensionScore: 82, passed: false, escalated: true },
  },
  frozen: {
    summary: { ...SUMMARY_R3 },
    phase: "FROZEN",
    status: "IDLE",
    counts: { sources: 6, evidenceItems: 8, prdVersions: 4, reviewRounds: 2, openDefects: 0 },
    headPrdVersion: 4,
    lastReview: { round: 2, weightedScore: 90.3, minDimensionScore: 88, passed: true, escalated: false },
  },
  blocked: {
    summary: { ...SUMMARY_R2, flowPhase: "REVIEWING", flowStatus: "BLOCKED", flowDetail: "BLOCKED_DB" },
    phase: "REVIEWING",
    status: "BLOCKED",
    detail: "BLOCKED_DB",
    counts: { sources: 6, evidenceItems: 8, prdVersions: 2, reviewRounds: 1, openDefects: 3 },
    headPrdVersion: 2,
    lastReview: { round: 1, weightedScore: 79.9, minDimensionScore: 70, passed: false, escalated: false },
  },
  initFailed: {
    summary: { ...SUMMARY_R1, flowPhase: "INGESTED", flowStatus: "FAILED", flowDetail: "init_failed:fsm" },
    phase: "INGESTED",
    status: "FAILED",
    detail: "init_failed:fsm",
    counts: ZERO,
    headPrdVersion: null,
    lastReview: null,
  },
};

export function detailVariant(name: DetailVariant, patch: Partial<ResearchProjectDetail> = {}): ResearchProjectDetail {
  const base = detailOf(DETAIL_SEEDS[name]);
  return { ...base, ...patch };
}

/** 各變體的名稱清單（測試逐一跑）。 */
export const DETAIL_VARIANTS = Object.keys(DETAIL_SEEDS) as DetailVariant[];
