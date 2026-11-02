import type { ResearchEvent, ResearchEventPage } from "@/lib/api/types";

/**
 * 事件帳夾具（API-RP-05；事件型別見契約 §3）：十四筆、`seq` 1 起連續。`research.run` 的 `tokensUsed` 是該 stage run 的累計值
 * （頁首的 Token 速率與已用量以它計；TCS AT-960-20-3）。時間以固定的 `2026-11-02` 為基準。
 */
const at = (minute: number): string => `2026-11-02T10:${String(minute).padStart(2, "0")}:00+08:00`;

function event(seq: number, eventType: string, step: ResearchEvent["step"], minute: number, payload: Record<string, unknown>, actor = "bridge"): ResearchEvent {
  return { seq, eventType, step, actor, refKind: null, refId: null, payload, occurredAt: at(minute) };
}

export const EVENTS: ResearchEvent[] = [
  event(1, "research.step", "topic", 0, { flowStep: "topic", flowPhase: "INGESTED", flowStatus: "IDLE", flowDetail: "" }, "operator"),
  event(2, "research.run", "topic", 1, { stage: "RESEARCH", roundNo: 0, attempt: 1, stageRunId: "run-research-1", engineRunId: "eng-1", status: "RUNNING", tokensUsed: 0 }),
  event(3, "research.source", "topic", 2, {
    sourceNo: "S-001",
    layer: "ACADEMIC",
    tier: "T1",
    verification: "V2",
    title: "向量檢索的近似最近鄰綜述",
    url: "https://arxiv.org/abs/2401.00001",
    fetchOutcome: "OK",
  }),
  event(4, "research.source", "topic", 3, { sourceNo: "S-002", layer: "OSS", tier: "T2", verification: "V3", title: "pgvector", url: "https://github.com/pgvector/pgvector", fetchOutcome: "OK" }),
  event(5, "research.evidence", "topic", 4, { matrixVersion: 1, evidenceNo: "E-001", sourceNo: "S-001", claim: "HNSW 在高維度下召回率較穩定", strength: "STRONG" }),
  event(6, "research.run", "topic", 5, { stage: "RESEARCH", roundNo: 0, attempt: 1, stageRunId: "run-research-1", engineRunId: "eng-1", status: "RUNNING", tokensUsed: 2400 }),
  event(7, "research.evidence", "topic", 6, { matrixVersion: 1, evidenceNo: "E-002", sourceNo: "S-002", claim: "pgvector 沒有獨立叢集的運維負擔", strength: "MEDIUM" }),
  event(8, "research.run", "topic", 7, { stage: "RESEARCH", roundNo: 0, attempt: 1, stageRunId: "run-research-1", engineRunId: "eng-1", status: "SUCCEEDED", tokensUsed: 5200 }),
  event(9, "research.step", "topic", 8, { flowStep: "topic", flowPhase: "EVIDENCE_READY", flowStatus: "IDLE", flowDetail: "" }),
  event(10, "research.prd", "studio", 9, { versionNo: 1, semver: "v0.1.0-draft", authorKind: "AGENT", author: "spec-engineer", sha256: "1".repeat(64) }),
  event(11, "research.run", "studio", 10, { stage: "REVIEW", roundNo: 1, attempt: 1, stageRunId: "run-review-1", engineRunId: "eng-2", status: "RUNNING", tokensUsed: 1800 }),
  event(12, "research.review", "studio", 11, { roundNo: 1, weightedScore: 79.9, minDimensionScore: 70, passed: false, verdict: "REVISE", escalated: false }),
  event(13, "research.defect", "studio", 12, { defectNo: "D-1-001", severity: "P2", dimension: "QA", status: "OPEN" }),
  event(14, "research.alert", "topic", 13, { kind: "DENIED_FETCH", detail: "api.example.com 不在允許清單" }),
];

/** 依 `afterSeq`（嚴格大於）與 `limit` 切一頁，回應形狀同 API-RP-05：`truncated` 為真時 `nextSeq` 是本頁最後一筆的 seq。 */
export function eventPage(events: readonly ResearchEvent[], afterSeq = 0, limit = 500): ResearchEventPage {
  const rest = events.filter((e) => e.seq > afterSeq);
  const items = rest.slice(0, limit);
  const truncated = rest.length > items.length;
  return { items, nextSeq: truncated ? items[items.length - 1].seq : null, truncated };
}
