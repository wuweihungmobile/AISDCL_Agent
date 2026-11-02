import type { ResearchDefect, ResearchPrdVersion, ResearchReviewDimension, ResearchReviewRound, ResearchReviewScore } from "@/lib/api/types";
import { sha, T0, T1, T2 } from "./ids";

/**
 * 審查輪與 PRD 版本夾具（API-RP-08、API-RP-10；TCS §5.1「審查權重」與 §5.2 研究劇本的分數）：
 * 四維權重 ARCHITECTURE 0.30、PRODUCT 0.25、QA 0.25、SECURITY 0.20；整數 W100＝30A＋25P＋25Q＋20S，`weightedScore`＝W100 除以 100（不四捨五入）；
 * 通過＝預檢通過且 W100 不低於 8500 且最低維度不低於 60 且無未結 P1（比較一律用整數）。
 * fail3：三輪 79.90、82.75、84.60（各輪維度分數見 `FAIL3_SCORES`）；pass：第 1 輪同 fail3、第 2 輪 90.30。
 */
export const WEIGHTS: Readonly<Record<ResearchReviewDimension, number>> = { ARCHITECTURE: 0.3, PRODUCT: 0.25, QA: 0.25, SECURITY: 0.2 };

const AGENTS: Readonly<Record<ResearchReviewDimension, string>> = { ARCHITECTURE: "sd-architect", PRODUCT: "pm-po", QA: "qa-engineer", SECURITY: "security-auditor" };

/** 四維分數 [ARCHITECTURE, PRODUCT, QA, SECURITY]。 */
export type Scores = readonly [number, number, number, number];
export const FAIL3_SCORES: readonly Scores[] = [
  [78, 84, 70, 90],
  [80, 85, 78, 90],
  [82, 86, 82, 90],
];
export const PASS_SCORES: readonly Scores[] = [
  [78, 84, 70, 90],
  [92, 90, 88, 91],
];

export function scoreRows(scores: Scores): ResearchReviewScore[] {
  const dims: ResearchReviewDimension[] = ["ARCHITECTURE", "PRODUCT", "QA", "SECURITY"];
  return dims.map((dimension, i) => ({
    dimension,
    weight: WEIGHTS[dimension],
    score: scores[i],
    agentId: AGENTS[dimension],
    assistAgentId: dimension === "SECURITY" ? "compliance-officer" : null,
    assistAgentYamlSha256: dimension === "SECURITY" ? sha("c") : null,
    agentYamlSha256: sha("a"),
    personaSha256: sha("b"),
    summary: `${dimension} 維度的審查摘要`,
  }));
}

export function defect(round: number, seq: number, patch: Partial<ResearchDefect> = {}): ResearchDefect {
  return {
    defectNo: `D-${round}-${String(seq).padStart(3, "0")}`,
    dimension: "QA",
    severity: "P2",
    code: "AC_NOT_TESTABLE",
    prdAnchor: "§4.2",
    description: "驗收條件沒有可量測的判準",
    suggestion: "補上可量測的門檻與觀察方式",
    evidenceRefs: ["E-001"],
    status: "OPEN",
    fixedInVersionNo: null,
    resolvedIn: null,
    waiver: null,
    ...patch,
  };
}

type RoundOpts = {
  fsmGateResult?: ResearchReviewRound["fsmGateResult"];
  fsmRetryCount?: number | null;
  triggerKind?: ResearchReviewRound["triggerKind"];
  fsmGeneration?: number;
  defects?: ResearchDefect[];
  startedAt?: string;
  finishedAt?: string;
  /** 缺省依分數判定；FSM 第 3 次 FAIL 的輪傳 true */
  escalated?: boolean;
};

/** 一輪的審查結果（只有「有結果」的輪才有列，D-57）：分數、條件與判定都由四維分數算出。 */
export function makeRound(roundNo: number, scores: Scores, prdVersionNo: number, opts: RoundOpts = {}): ResearchReviewRound {
  const [a, p, q, s] = scores;
  const w100 = 30 * a + 25 * p + 25 * q + 20 * s;
  const min = Math.min(...scores);
  const defects = opts.defects ?? [defect(roundNo, 1)];
  const openP1 = defects.filter((d) => d.severity === "P1" && d.status === "OPEN").length;
  const passed = w100 >= 8500 && min >= 60 && openP1 === 0;
  const escalated = opts.escalated ?? false;
  return {
    roundNo,
    fsmGeneration: opts.fsmGeneration ?? 1,
    prdVersionNo,
    prdVersion: `v0.${prdVersionNo}.0-draft`,
    triggerKind: opts.triggerKind ?? "AUTO",
    precheck: {
      passed: true,
      checks: [
        { id: "SLV-001", passed: true, detail: "章節完整" },
        { id: "SLV-002", passed: true, detail: "引用都存在" },
        { id: "SLV-003", passed: true, detail: "每個 Feature 都有驗收條件" },
        { id: "AMBIGUITY", passed: true, detail: "沒有含糊用語" },
      ],
    },
    weightedScore: w100 / 100,
    threshold: 85,
    floorScore: 60,
    minDimensionScore: min,
    conditions: { precheckPassed: true, weightedGeThreshold: w100 >= 8500, allDimensionsGeFloor: min >= 60, noOpenP1: openP1 === 0 },
    openP1Count: openP1,
    passed,
    verdict: passed ? "PASS" : escalated ? "ESCALATE" : "REVISE",
    fsmGateResult: opts.fsmGateResult === undefined ? (passed ? "PASS" : "FAIL") : opts.fsmGateResult,
    fsmRetryCount: opts.fsmRetryCount === undefined ? (passed ? 0 : roundNo) : opts.fsmRetryCount,
    escalated,
    scores: scoreRows(scores),
    defects,
    startedAt: opts.startedAt ?? T0,
    finishedAt: opts.finishedAt ?? T1,
  };
}

/** 劇本 fail3：三輪都沒過，第 3 次 gate FAIL 使 FSM 進入 ESCALATION（第 3 輪 verdict 為 ESCALATE）。 */
export const FAIL3_ROUNDS: ResearchReviewRound[] = [
  makeRound(1, FAIL3_SCORES[0], 1, { defects: [defect(1, 1), defect(1, 2, { severity: "P3", dimension: "PRODUCT" })] }),
  makeRound(2, FAIL3_SCORES[1], 2, { defects: [defect(2, 1, { severity: "P3" })] }),
  makeRound(3, FAIL3_SCORES[2], 3, { defects: [defect(3, 1, { severity: "P3" })], escalated: true }),
];

/** 劇本 pass：第 1 輪未過、第 2 輪通過（90.30）。 */
export const PASS_ROUNDS: ResearchReviewRound[] = [
  makeRound(1, PASS_SCORES[0], 1, { defects: [defect(1, 1), defect(1, 2, { severity: "P1", dimension: "ARCHITECTURE" })] }),
  makeRound(2, PASS_SCORES[1], 2, { defects: [defect(2, 1, { severity: "P3", status: "OPEN" })], finishedAt: T2 }),
];

/** PRD 版本清單（API-RP-08；單筆端點另帶 `content`）。 */
export const PRD_VERSIONS: ResearchPrdVersion[] = [
  {
    versionNo: 1,
    semver: "v0.1.0-draft",
    kind: "DRAFT",
    authorKind: "AGENT",
    author: "spec-engineer",
    parentVersionNo: null,
    sha256: sha("1"),
    bytes: 4096,
    evidenceRefs: ["E-001", "E-002"],
    changeSummary: "初稿",
    createdAt: T0,
  },
  {
    versionNo: 2,
    semver: "v0.2.0-draft",
    kind: "DRAFT",
    authorKind: "AGENT",
    author: "spec-engineer",
    parentVersionNo: 1,
    sha256: sha("2"),
    bytes: 4400,
    evidenceRefs: ["E-001", "E-002", "E-003"],
    changeSummary: "依第 1 輪缺陷修訂",
    createdAt: T1,
  },
];

export const PRD_CONTENT = ["# PRD 向量資料庫選型", "", "## 1 背景", "為何需要向量資料庫 [E-001]", "", "## 2 問題", "自架與雲端的取捨 [E-002]", ""].join("\n");
