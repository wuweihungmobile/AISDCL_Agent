import type { ResearchAllowlistEntry, ResearchCapabilities, ResearchEvidenceMatrix, ResearchReconcileResult, ResearchRecordsAudit, ResearchSource } from "@/lib/api/types";
import { sha, T0, T1 } from "./ids";

/** 能力探針（API-RP-01）：本機模式、Web 層預設關（產業網域 allowlist 為空；W-R13）。 */
export const CAPABILITIES_LOCAL: ResearchCapabilities = {
  mode: "local",
  db: true,
  claudeCli: { ok: true, version: "2.1.0" },
  ghCli: { ok: false, authenticated: false },
  git: { ok: true, version: "2.50.0" },
  sddRoot: "<AISDLC_SDD 框架樹>",
  researchRoot: "<研究工作區根>",
  scaffoldRoot: null,
  scaffoldTemplates: [],
  repoWritable: true,
  webLayerEnabled: false,
  fetchHosts: ["export.arxiv.org", "arxiv.org", "api.semanticscholar.org", "api.github.com", "api.stackexchange.com"],
};

/** 容器模式：只跑 mock claude 的驗收，UI 停用「啟動深研」。 */
export const CAPABILITIES_MOCK_ONLY: ResearchCapabilities = { ...CAPABILITIES_LOCAL, mode: "mock-only", claudeCli: { ok: false } };

export const ALLOWLIST: ResearchAllowlistEntry[] = [
  {
    id: "al-1",
    listKind: "FETCH",
    host: "export.arxiv.org",
    layer: "ACADEMIC",
    purpose: "arXiv 論文",
    tosNote: "",
    minIntervalSeconds: 3,
    enabled: true,
    tosAcknowledged: false,
    source: "ENV",
    addedBy: null,
    addedAt: null,
  },
  {
    id: "al-2",
    listKind: "FETCH",
    host: "api.github.com",
    layer: "OSS",
    purpose: "開源 Repo",
    tosNote: "",
    minIntervalSeconds: 1,
    enabled: true,
    tosAcknowledged: false,
    source: "ENV",
    addedBy: null,
    addedAt: null,
  },
  {
    id: "al-3",
    listKind: "WEB",
    host: "docs.example.com",
    layer: "INDUSTRY",
    purpose: "官方文件",
    tosNote: "",
    minIntervalSeconds: 5,
    enabled: true,
    tosAcknowledged: false,
    source: "ADMIN",
    addedBy: "admin",
    addedAt: T0,
  },
];

export const SOURCES: ResearchSource[] = [
  {
    sourceNo: "S-001",
    layer: "ACADEMIC",
    tier: "T1",
    verification: "V2",
    anchorKind: "URL",
    url: "https://arxiv.org/abs/2401.00001",
    doi: null,
    gitCommit: null,
    title: "向量檢索的近似最近鄰綜述",
    authorsOrg: "Example Lab",
    publishedAt: "2024-01-03",
    sourceType: "PAPER",
    licenseSpdx: null,
    licenseNote: "",
    clueOnly: false,
    fetches: [{ fetchNo: "F-0001", method: "GET", observedBy: "BRIDGE", host: "export.arxiv.org", httpStatus: 200, outcome: "OK", rawSha256: sha("d"), rawBytes: 40960, fetchedAt: T0 }],
  },
  {
    sourceNo: "S-002",
    layer: "OSS",
    tier: "T2",
    verification: "V3",
    anchorKind: "COMMIT",
    url: "https://github.com/pgvector/pgvector",
    doi: null,
    gitCommit: "0123456789abcdef0123456789abcdef01234567",
    title: "pgvector",
    authorsOrg: "pgvector",
    publishedAt: null,
    sourceType: "REPO",
    licenseSpdx: "PostgreSQL",
    licenseNote: "",
    clueOnly: false,
    fetches: [{ fetchNo: "F-0002", method: "GET", observedBy: "BRIDGE", host: "api.github.com", httpStatus: 200, outcome: "OK", rawSha256: sha("e"), rawBytes: 2048, fetchedAt: T1 }],
  },
];

export const EVIDENCE: ResearchEvidenceMatrix = {
  matrixVersion: 1,
  scopeRev: 1,
  sha256: sha("f"),
  items: [
    {
      evidenceNo: "E-001",
      sourceNo: "S-001",
      candidate: "HNSW",
      claim: "HNSW 在高維度下召回率較穩定",
      f1Mechanism: "分層近鄰圖",
      f2Evidence: "召回率 0.97（ef=200）",
      f3Critique: "只測過單一資料集",
      f4RiskTags: ["SCOPE"],
      f5Applicability: { 技術可行: { grade: "A", reason: "可由 Python 呼叫" }, 授權相容: { grade: "M", reason: "需再確認" } },
      f6Limits: "記憶體用量高",
      f7Verification: "V2",
      strength: "STRONG",
      unanchored: false,
      matrixVersion: 1,
      scopeRev: 1,
    },
    {
      evidenceNo: "E-002",
      sourceNo: "S-002",
      candidate: "pgvector",
      claim: "pgvector 沒有獨立叢集的運維負擔",
      f1Mechanism: "PostgreSQL 擴充",
      f2Evidence: "官方 README",
      f3Critique: "自述成果",
      f4RiskTags: ["SELF"],
      f5Applicability: { 技術可行: { grade: "A", reason: "沿用既有 PG" } },
      f6Limits: "大規模時效能有上界",
      f7Verification: "V3",
      strength: "MEDIUM",
      unanchored: false,
      matrixVersion: 1,
      scopeRev: 1,
    },
  ],
  counterEvidence: [{ evidenceNo: "E-001", searchId: "Q-001", conclusion: "LIMIT", sourceNo: "S-001", note: "記憶體用量是主要限制" }],
  honestBounds: { notFound: [{ query: "pgvector 對照 HNSW 基準", date: "2026-11-02", result: "沒有獨立重現" }], summaryOnly: [], notReadFully: [] },
  searchLog: [{ searchNo: "Q-001", layer: "ACADEMIC", tool: "WebSearch", query: "HNSW recall limitations", at: T0, resultUrls: ["https://arxiv.org/abs/2401.00001"] }],
};

export const RECORDS_AUDIT: ResearchRecordsAudit = {
  classes: [
    { id: "R1", name: "議題與範圍", count: 1 },
    { id: "R2", name: "研究來源", count: 2 },
    { id: "R7", name: "分流決定", count: 0 },
    { id: "R10", name: "自癒嘗試", count: 0 },
  ],
  missing: ["R7"],
};

/** 對帳全綠。 */
export const RECONCILE_OK: ResearchReconcileResult = {
  consistent: true,
  checks: ["fsm_flow_mapping", "prd_sha256", "review_card", "evidence_matrix", "task_decomposition", "route_decision"].map((name) => ({ name, status: "ok" as const })),
};

/** 對帳有漂移：一個 PRD 檔的 sha256 與資料庫不符、FSM 與游標的對映不合（以資料庫為準，只顯示、不修）。 */
export const RECONCILE_DRIFT: ResearchReconcileResult = {
  consistent: false,
  checks: [
    { name: "fsm_flow_mapping", status: "drift", drift: [{ kind: "fsm_cursor_mismatch", path: "FSM-STATE-research-vector-db.yaml" }] },
    { name: "prd_sha256", status: "drift", drift: [{ kind: "sha256_mismatch", path: "01_specs/PRD-v0.2.0-draft.md", expectedSha256: sha("2"), actualSha256: sha("9") }] },
    { name: "review_card", status: "ok" },
    { name: "evidence_matrix", status: "ok" },
    { name: "task_decomposition", status: "ok" },
    { name: "route_decision", status: "ok" },
  ],
};
