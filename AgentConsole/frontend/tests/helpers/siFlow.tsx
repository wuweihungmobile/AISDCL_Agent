/**
 * 「核准流程全程可見」測試的夾具與輔助（TCS-SiFlowVisibility-20261111 §5.1、§5.6）：
 *  - NOW／iso：固定的 `readAt` 與「早於 NOW N 分」的時間字串；
 *  - PATROL／DETAIL／P901：前端實際收到的 camelCase 形態（C-2、C-3）；`DROP` 表示刪鍵；
 *  - camelKeys：規則逐字等同 backend `SiKeyNames.camel`，供根層黃金樣本（snake_case 原樣）轉成前端形態；
 *  - 不被 vitest 收集（tests/ 目錄；沿 tests/helpers/si.tsx 先例）。
 * 所有編號都是測試號（PROP-SI-901 起），不存在於真帳本。
 */
import { readFileSync } from "node:fs";
import path from "node:path";

import { screen } from "@testing-library/react";
import type userEvent from "@testing-library/user-event";

import type { SiProposal } from "@/lib/api/types";
import { GA, clone, renderSi, type RenderSiOptions, type SiFixture, type SiOverride } from "./si";

export const NOW = "2026-11-11T14:00:00+08:00";
export const NOW_MS = Date.parse(NOW);

/** 刪鍵標記（鍵缺席與值為 null 是兩件事）。 */
export const DROP = Symbol("FLOW_DROP");

/** 早於 NOW `minutes` 分鐘的時間字串（帶 +08:00）；負數＝晚於 NOW；`seconds` 另加秒。 */
export function iso(minutes: number, seconds = 0): string {
  const ms = NOW_MS - (minutes * 60 + seconds) * 1000;
  return new Date(ms + 8 * 3600_000).toISOString().replace(/\.\d{3}Z$/, "+08:00");
}

function applyOver(base: Record<string, unknown>, over: Record<string, unknown>): Record<string, unknown> {
  for (const [key, value] of Object.entries(over)) {
    if (value === DROP) delete base[key];
    else base[key] = value;
  }
  return base;
}

export const STEPS = [
  { step: "巡視", result: "看了 3 個提案" },
  { step: "入帳", result: "入帳 0、拒收 0" },
  { step: "到期", result: "沒有到期項目" },
  { step: "運轉", result: "沒有開新運轉" },
  { step: "推進", result: "PROP-SI-901 等你決定" },
];

/** `PATROL(over, top)`：`over` 覆寫 `report`，`top` 覆寫外層（readAt 等）。 */
export function PATROL(
  over: Record<string, unknown> = {},
  top: Record<string, unknown> = {},
): { schemaRev: number; kind: string; readAt: string; report: Record<string, unknown> } & Record<string, unknown> {
  const report = applyOver(
    {
      generatedAt: iso(3),
      off: false,
      heartbeatMinutes: 15,
      ledgerSeq: 130,
      truncated: false,
      steps: clone(STEPS),
      schedule: { enabled: true, current: { code: "SCHED-CELL-RAN", text: "本期已經跑過一次，等下一期" }, lastSkip: null },
      ingest: [],
      props: [{ id: "PROP-SI-901", state: "verified", code: "WAIT-PROMOTE-DECISION", who: "掌舵者", text: "驗證通過，等你決定是否晉升" }],
      runs: { live: [], waiting: [], queued: [] },
      push: { enabled: true, state: "idle", code: "PUSH-NOT-AHEAD", text: "沒有待推送的提交", retry: null, sha: null, ahead: 0, attempts: 0, finishedAt: null, tickAt: null },
    },
    over,
  );
  return applyOver({ schemaRev: 1, kind: "patrol", readAt: NOW, report }, top) as ReturnType<typeof PATROL>;
}

export const patchMixed = readFileSync(path.join(process.cwd(), "tests", "fixtures", "si", "flow", "patch-mixed.diff"), "utf-8");

/** 提案 `PROP-SI-901`（verified、rev 2、lastSeq 120、sources 指向 OBS-SI-050）。 */
export const P901: SiProposal = {
  id: "PROP-SI-901",
  state: "verified",
  route: "auto-loop",
  cls: "A",
  action: "modify",
  run: "RUN-SI-901",
  rev: 2,
  digest: "sha256:0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f9",
  target: ["tools/x.py"],
  touched: ["tools/x.py"],
  touchedCount: 1,
  sources: ["OBS-SI-050"],
  createdSeq: 100,
  lastSeq: 120,
  verdict: "PASS",
  flags: [],
  cooldown: null,
  card: "CARD-LINE-1\nCARD-LINE-2",
};

/** `detail`（C-3 八欄俱全）；`over` 逐鍵覆寫，`DROP` 刪鍵。 */
export function DETAIL(over: Record<string, unknown> = {}): Record<string, unknown> {
  return applyOver(
    {
      patch: { rel: "docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.patch", bytes: Buffer.byteLength(patchMixed), text: patchMixed, truncated: false },
      body: { rel: "docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.md", bytes: 40, text: "# 提案 901\n\n症狀…\n", truncated: false },
      sourceObs: [{ id: "OBS-SI-050", context: "巡邏日誌", symptom: "提案卡了三天沒人處理", severity: "P2", disposition: "proposed" }],
      heldout: { frozen: true, seq: 60, n: 7, min: 5, belowMin: false, frozenBy: "凍結者甲", digest8: "0a1b2c3d", neNote: null },
      sandbox: { seq: 61, id: "APP-SI-901", applied: true, touchedOk: true, rollbackOk: true, failCode: null, failText: null },
      verify: { seq: 62, id: "APP-SI-901", verdict: "PASS", baselineRed: true, patchedGreen: true, mutatedRed: true, probesN: 6, carrierProof: true, reasons: [] },
      next: { code: "WAIT-PROMOTE-DECISION", who: "掌舵者", text: "驗證通過，等你決定是否晉升" },
      timeline: [
        { seq: 12, t: "2026-11-10T09:00:00+08:00", by: "巡邏器", kind: "prop", action: "提出提案" },
        { seq: 21, t: "2026-11-10T10:00:00+08:00", by: "巡邏器", kind: "app", action: "開始驗證" },
        { seq: 30, t: "2026-11-10T11:00:00+08:00", by: "掌舵者", kind: "dec", action: "核准" },
      ],
    },
    over,
  );
}

/** 單筆提案回應（`GET /api/v1/si/proposals/{id}`）：`items[0]`＝提案加 `detail`；`detail` 傳 DROP＝舊根層沒有該鍵。 */
export function proposalResponse(opts: { detail?: Record<string, unknown> | typeof DROP | null; proposal?: Partial<SiProposal>; ne?: Array<Record<string, unknown>> } = {}): Record<string, unknown> {
  const item: Record<string, unknown> = { ...clone(P901), ...(opts.proposal ?? {}) };
  if (opts.detail !== DROP) item.detail = opts.detail === undefined ? DETAIL() : opts.detail;
  return { schemaRev: 1, kind: "proposals", generatedAt: NOW, headSha: null, items: [item], nextSince: null, truncated: false, ne: opts.ne ?? [], problems: [] };
}

/** 提案分頁有三列（P901 加兩個）的夾具：其餘（觀察、事件、運轉、狀態）沿用狀態 A 黃金檔。 */
export function flowFixture(): SiFixture {
  const f = clone(GA);
  const mk = (id: string, state: string, lastSeq: number): SiProposal => ({ ...clone(P901), id, state, lastSeq, sources: [] });
  // 觀察分頁多一列 OBS-SI-050（來源觀察跳轉的目標；編號不存在於真帳本）
  const firstValid = f.observations.items.find((r) => r.valid !== false);
  if (firstValid && "id" in firstValid) f.observations.items.push({ ...clone(firstValid), id: "OBS-SI-050" });
  f.proposals = { ...f.proposals, items: [clone(P901), mk("PROP-SI-902", "proposed", 121), mk("PROP-SI-903", "approved", 122)], truncated: false, nextSince: null, ne: [], problems: [] };
  return f;
}

export type FlowOptions = RenderSiOptions & {
  /** 巡邏端點：給 PATROL()／{status,data}／Response 的函式；預設回新鮮的 PATROL() */
  patrol?: SiOverride;
  /** 單筆提案端點（只對 PROP-SI-901 生效）；預設回完整的 DETAIL() */
  proposal?: SiOverride;
};

/** 渲染整個 SiView（含巡邏卡與詳情對話框），網路為 fetch 替身；觀察分頁的資料含 OBS-SI-050 以外的黃金檔列。 */
export function renderFlow(opts: FlowOptions = {}): ReturnType<typeof renderSi> {
  const { patrol, proposal, ...rest } = opts;
  return renderSi({
    ...rest,
    fixture: rest.fixture ?? flowFixture(),
    overrides: {
      patrol: patrol ?? (() => ({ data: PATROL() })),
      proposal: proposal ?? ((call) => (call.path.endsWith("/PROP-SI-901") ? { data: proposalResponse() } : undefined)),
      ...rest.overrides,
    },
  });
}

type User = ReturnType<typeof userEvent.setup>;

/** 切到提案分頁、按 `P901`（或指定提案）的「詳情」鈕，回傳對話框元素。 */
export async function openDetail(user: User, id = "PROP-SI-901"): Promise<HTMLElement> {
  await user.click(screen.getByRole("tab", { name: /提案/ }));
  await user.click(await screen.findByTestId(`si-detail-open-${id}`));
  return screen.findByRole("dialog");
}

/** 規則逐字等同 backend `SiKeyNames.camel`：鍵符合 `^[a-z][a-z0-9]*(_[a-z0-9]+)+$` 才依 `_` 切段轉駝峰，其餘鍵恆等；遞迴整棵樹。 */
export function camelKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(camelKeys);
  if (typeof value !== "object" || value === null) return value;
  const out: Record<string, unknown> = {};
  for (const [key, v] of Object.entries(value as Record<string, unknown>)) {
    const camel = /^[a-z][a-z0-9]*(_[a-z0-9]+)+$/.test(key)
      ? key
          .split("_")
          .map((seg, i) => (i === 0 ? seg : seg.charAt(0).toUpperCase() + seg.slice(1)))
          .join("")
      : key;
    out[camel] = camelKeys(v);
  }
  return out;
}

/** 遞迴的鍵集合（排序後以點號路徑表示；陣列取第一個元素代表），供「黃金樣本轉換後與基準鍵集合相等」的自檢。 */
export function keyPaths(value: unknown, prefix = ""): string[] {
  if (Array.isArray(value)) return value.length > 0 ? keyPaths(value[0], `${prefix}[]`) : [];
  if (typeof value !== "object" || value === null) return [];
  return Object.entries(value as Record<string, unknown>)
    .flatMap(([k, v]) => [`${prefix}.${k}`, ...keyPaths(v, `${prefix}.${k}`)])
    .sort();
}

/** 根層黃金樣本複本（snake_case 原樣）轉成前端形態：巡邏快照（整個 report）與單筆提案（整個 items[0]，含 detail）。 */
const flowFixturePath = (name: string) => path.join(process.cwd(), "tests", "fixtures", "si", "flow", name);
export function goldenReport(): Record<string, unknown> {
  return camelKeys(JSON.parse(readFileSync(flowFixturePath("patrol.golden.json"), "utf-8"))) as Record<string, unknown>;
}
export function goldenPatrol(readAt = "2026-11-11T12:01:00+08:00"): ReturnType<typeof PATROL> {
  return { schemaRev: 1, kind: "patrol", readAt, report: goldenReport() };
}
export function goldenProposalItem(): Record<string, unknown> {
  return camelKeys(JSON.parse(readFileSync(flowFixturePath("detail.golden.json"), "utf-8"))) as Record<string, unknown>;
}
export function goldenProposalResponse(): Record<string, unknown> {
  return { schemaRev: 1, kind: "proposals", generatedAt: NOW, headSha: null, items: [goldenProposalItem()], nextSince: null, truncated: false, ne: [], problems: [] };
}
