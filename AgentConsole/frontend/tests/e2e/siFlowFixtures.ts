import { readFileSync } from "node:fs";
import path from "node:path";

/**
 * 「核准流程全程可見」mock E2E 的夾具（TCS-SiFlowVisibility D6／D7；self-improving-flow.mock.spec.ts 專用，非 spec 檔不被收集）。
 * 形態一律是前端實際收到的 camelCase（C-2、C-3）；推送狀態、原因白話等全部放在夾具的文字欄（`text`），
 * 測試與前端都不自建對照表。時間以「呼叫當下」為基準（瀏覽器的真時鐘），所以新鮮度由 `minutesAgo` 決定。
 * 測試號（PROP-SI-901 起）不存在於真帳本；觀察 OBS-SI-050 取帳本真實存在的編號（si check 的 ref.obs 掃全 repo）。
 */

const FIX = path.join(process.cwd(), "tests", "fixtures", "si");
export type Rec = Record<string, unknown>;
type Page_ = { items: Rec[]; truncated?: boolean; nextSince?: number | null } & Rec;
export type Base = { observations: Page_; events: Page_; proposals: Page_; runs: Page_; status: Page_ };
export const BASE = JSON.parse(readFileSync(path.join(FIX, "A.camel.json"), "utf-8")) as Base;
export const PATCH_MIXED = readFileSync(path.join(FIX, "flow", "patch-mixed.diff"), "utf-8");

export const PROP = "PROP-SI-901";
export const OBS = "OBS-SI-050";
export const REF = (n: number) => `a1000000-0000-4000-8000-${String(n).padStart(12, "0")}`;

export const isoAgo = (minutes: number, now = Date.now()): string => new Date(now - minutes * 60_000).toISOString().replace(/\.\d{3}Z$/, "+00:00");

const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
export const whole = (page: Page_) => ({ ...page, truncated: false, nextSince: null });

/** 巡邏卡「為什麼沒有啟動運轉」與推送八態之一（blocked）的內容；白話文字由夾具給，前端逐字顯示。 */
export function patrolReport(opts: { minutesAgo?: number; rich?: boolean; ingestRef?: string } = {}): Rec {
  const { minutesAgo = 3, rich = false, ingestRef } = opts;
  const report: Rec = {
    generatedAt: isoAgo(minutesAgo),
    off: false,
    heartbeatMinutes: 15,
    ledgerSeq: 130,
    truncated: false,
    steps: [
      { step: "巡視", result: "看了 3 個提案" },
      { step: "入帳", result: "入帳 0、拒收 1" },
      { step: "到期", result: "沒有到期項目" },
      { step: "運轉", result: "沒有開新運轉" },
      { step: "推進", result: `${PROP} 等你決定` },
    ],
    schedule: { enabled: true, current: { code: "SCHED-CELL-RAN", text: "本期已經跑過一次，等下一期" }, lastSkip: null },
    ingest: [],
    props: [{ id: PROP, state: "verified", code: "WAIT-PROMOTE-DECISION", who: "掌舵者", text: "驗證通過，等你決定是否晉升" }],
    runs: { live: [], waiting: [], queued: [] },
    push: { enabled: true, state: "idle", code: "PUSH-NOT-AHEAD", text: "沒有待推送的提交", retry: null, sha: null, ahead: 0, attempts: 0, finishedAt: null, tickAt: null },
  };
  if (rich) {
    report.schedule = {
      enabled: true,
      current: { code: "SCHED-SKIPPED", text: "上一期被略過了，這一期還沒輪到" },
      lastSkip: { seq: 129, t: isoAgo(30), code: "SKIP-QUOTA", text: "額度不夠，這一期先不啟動運轉", auditRef: REF(7) },
    };
    report.runs = {
      live: [{ run: "RUN-SI-902", purpose: "scheduled", startedAt: isoAgo(12), wallDueAt: new Date(Date.now() + 48 * 60_000).toISOString().replace(/\.\d{3}Z$/, "+00:00") }],
      waiting: [{ run: "RUN-SI-903", code: "WAIT-QUOTA", text: "等額度恢復後再繼續" }],
      queued: [],
    };
    report.push = {
      enabled: true,
      state: "blocked",
      code: "PUSH-NOT-RECORDED",
      text: "有一個提交還沒登記在帳本，已停止自動推送，請由人處理",
      retry: null,
      sha: "abc1234",
      ahead: 2,
      attempts: 0,
      finishedAt: null,
      tickAt: null,
    };
  }
  if (ingestRef) {
    report.ingest = [{ auditRef: ingestRef, kind: "run-request", status: "rejected", code: "INGEST-BAD-FORMAT", text: "這個要求的格式不對，主機拒收了", permanent: true }];
  }
  return report;
}

export function patrolBody(over: { minutesAgo?: number; rich?: boolean; ingestRef?: string } = {}): Rec {
  return { schemaRev: 1, kind: "patrol", readAt: isoAgo(0), report: patrolReport(over) };
}

/** 超過 400 行視窗的 patch（需要「展開全部」）；`lines` 行、固定種子（內容只由行號決定）。 */
export function bigPatch(lines: number, wide = false): string {
  const out: string[] = ["diff --git a/big.py b/big.py", "--- a/big.py", "+++ b/big.py", `@@ -1,${lines} +1,${lines} @@`];
  for (let i = 0; i < lines - 4; i++) {
    const body = `value_${i} = compute(${i}) # ${"x".repeat(wide ? 180 : 20)}`;
    out.push(i % 3 === 0 ? `+${body}` : i % 3 === 1 ? `-${body}` : ` ${body}`);
  }
  return out.join("\n") + "\n";
}

export type DetailOpts = { patch?: string; belowMin?: boolean };
export function detailOf(opts: DetailOpts = {}): Rec {
  const patch = opts.patch ?? PATCH_MIXED;
  return {
    patch: { rel: `docs/06_quality/SelfImproving_Proposals/${PROP}/r2.patch`, bytes: Buffer.byteLength(patch), text: patch, truncated: false },
    body: { rel: `docs/06_quality/SelfImproving_Proposals/${PROP}/r2.md`, bytes: 40, text: "# 提案 901\n\n症狀…\n", truncated: false },
    sourceObs: [{ id: OBS, context: "巡邏日誌", symptom: "提案卡了三天沒人處理", severity: "P2", disposition: "proposed" }],
    heldout: {
      frozen: true,
      seq: 60,
      n: opts.belowMin ? 3 : 7,
      min: 5,
      belowMin: opts.belowMin === true,
      frozenBy: "凍結者甲",
      digest8: "0a1b2c3d",
      neNote: opts.belowMin ? "案例只有 3 個、低於下限 5 個，驗證結果只能是無法評估" : null,
    },
    sandbox: { seq: 61, id: "APP-SI-901", applied: true, touchedOk: true, rollbackOk: true, failCode: null, failText: null },
    verify: { seq: 62, id: "APP-SI-901", verdict: opts.belowMin ? "NE" : "PASS", baselineRed: true, patchedGreen: true, mutatedRed: true, probesN: 6, carrierProof: true, reasons: [] },
    next: { code: "WAIT-PROMOTE-DECISION", who: "掌舵者", text: "驗證通過，等你決定是否晉升" },
    timeline: [
      { seq: 12, t: "2026-11-10T09:00:00+08:00", by: "巡邏器", kind: "prop", action: "提出提案" },
      { seq: 21, t: "2026-11-10T10:00:00+08:00", by: "巡邏器", kind: "app", action: "開始驗證" },
      { seq: 30, t: "2026-11-10T11:00:00+08:00", by: "掌舵者", kind: "dec", action: "核准" },
    ],
  };
}

const proposalRow = (id: string, state: string, lastSeq: number): Rec => ({
  id,
  state,
  route: "auto-loop",
  cls: "A",
  action: "modify",
  run: "RUN-SI-901",
  rev: 2,
  digest: "sha256:0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f9",
  target: ["tools/x.py"],
  touched: ["tools/x.py"],
  touchedCount: 1,
  sources: [OBS],
  createdSeq: 100,
  lastSeq,
  verdict: "PASS",
  flags: [],
  cooldown: null,
  card: "CARD-LINE-1\nCARD-LINE-2",
});

/** 提案分頁三列與含 OBS-SI-050 的觀察分頁（來源觀察跳轉的目標）。 */
export function listFixture(): { proposals: Page_; observations: Page_ } {
  const observations = clone(BASE.observations);
  const firstValid = observations.items.find((r) => r.valid !== false);
  if (firstValid && "id" in firstValid) observations.items.push({ ...clone(firstValid), id: OBS });
  const proposals: Page_ = { ...clone(BASE.proposals), items: [proposalRow(PROP, "verified", 120), proposalRow("PROP-SI-902", "proposed", 121), proposalRow("PROP-SI-903", "approved", 122)] };
  return { proposals, observations };
}

/** 單筆提案回應：`items[0]`＝提案加 `detail`。 */
export function proposalResponse(detail: Rec): Rec {
  return {
    schemaRev: 1,
    kind: "proposals",
    generatedAt: isoAgo(0),
    headSha: null,
    items: [{ ...proposalRow(PROP, "verified", 120), detail }],
    nextSince: null,
    truncated: false,
    ne: [],
    problems: [],
  };
}
