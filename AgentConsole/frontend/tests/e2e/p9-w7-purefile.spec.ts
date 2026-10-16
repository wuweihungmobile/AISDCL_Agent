import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

import { RUN } from "./helpers";
import { E2E_ROOT, NEEDS_BRIDGE, bootstrapSettings, call, createFixture, dataOf, ensureQuota, poll, type Fixture } from "./realBackend";
import { MOCK_CLAUDE, startBridge, type VariantBridge } from "./w7";

/**
 * W7 複驗：完整性審查 I-07／Architecture §12.1 L-12 的「待驗」——Bridge 以純檔案模式啟動（沒設 `BRIDGE_DB_DSN`）時，
 * Console 的斷點清單（`GET /executions/{runId}/checkpoints`）與步驟時間軸（`GET /executions/{runId}/steps`）實際長什麼樣。
 * 做法：同一份夾具（PRJ-A：兩個目標、三個任務）各跑一次到終態——對照組走共用的 DB 模式 Bridge（18081），實驗組走另起的純檔案模式 Bridge（18086，
 * 把 console-api 的 `autoclaude.engineUrl` 指過去）；比對兩邊的批次詳情、步驟與斷點。結束後把 `engineUrl` 還原。
 * 這支只量不裁決：結果寫進 QA 報告，登記與否由主控決定。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const nm = (base: string) => `${base} ${RUN}`;
const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED"];
const PORT = 18086;

type Detail = {
  id: string;
  status: string;
  completedSteps?: number;
  totalSteps?: number;
  totalTokensUsed?: number;
  bridge?: { connected: boolean; instance?: string; status?: string; runKnown?: boolean };
};
type StepRow = { stepId: string; status: string };
type Observed = {
  status: string;
  completedSteps: number | undefined;
  totalSteps: number | undefined;
  steps: StepRow[];
  stepsTotal: number;
  checkpoints: Array<{ name: string }>;
  instance: string | undefined;
};

let bridge: VariantBridge | undefined;

async function observe(request: APIRequestContext, f: Fixture): Promise<Observed> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
  expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(201);
  const id = dataOf<{ id: string }>(r).id;
  const fin = await poll(
    async () => dataOf<Detail>(await call(request, "viewer", "GET", `/api/v1/executions/${id}`)),
    (d) => TERMINAL.includes(d.status),
    `批次 ${id} 進入終態`,
    150_000,
    2_000,
  );
  const steps = dataOf<{ content: StepRow[]; totalElements: number }>(await call(request, "viewer", "GET", `/api/v1/executions/${id}/steps?size=200`));
  const cps = await call(request, "viewer", "GET", `/api/v1/executions/${id}/checkpoints`);
  expect(cps.status, `checkpoints → ${JSON.stringify(cps.json).slice(0, 200)}`).toBe(200);
  return {
    status: fin.status,
    completedSteps: fin.completedSteps,
    totalSteps: fin.totalSteps,
    steps: steps.content,
    stepsTotal: steps.totalElements,
    checkpoints: dataOf<Array<{ name: string }>>(cps),
    instance: fin.bridge?.instance,
  };
}

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200); // 執行類情境要求 apiKey 為空
});

test.afterAll(async ({ request }) => {
  await call(request, "admin", "POST", "/api/v1/settings/autoclaude/engineUrl/reset");
  await bridge?.stop();
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 60);
  await ensureQuota(request, "viewer", 60);
});

test("I-07｜Bridge 純檔案模式：Console 的步驟時間軸與斷點清單對照 DB 模式", async ({ request }) => {
  test.setTimeout(420_000);
  // 對照組：共用的 DB 模式 Bridge
  const dbMode = await observe(request, await createFixture(request, { name: nm("QA W7 I-07 DB 模式"), kind: "A", level: 4 }));
  expect(dbMode.status).toBe("COMPLETED");

  // 實驗組：純檔案模式（變體 Bridge 沒有 BRIDGE_DB_DSN）；允許路徑要涵蓋夾具專案目錄（<E2E_ROOT>/projects）
  const root = path.join(E2E_ROOT, "w7-bridges", "purefile");
  mkdirSync(root, { recursive: true });
  bridge = await startBridge({ port: PORT, root, instance: "w7-purefile", extraEnv: { BRIDGE_ALLOWED_PATH_ROOTS: [root, path.join(E2E_ROOT, "projects")].join(path.delimiter) } });
  expect((await call(request, "admin", "PUT", "/api/v1/settings/autoclaude/engineUrl", { value: bridge.url })).status).toBe(200);
  const fileMode = await observe(request, await createFixture(request, { name: nm("QA W7 I-07 純檔案模式"), kind: "A", level: 4 }));

  const pick = (o: Observed) => ({
    status: o.status,
    instance: o.instance,
    completedSteps: o.completedSteps,
    totalSteps: o.totalSteps,
    stepsTotal: o.stepsTotal,
    stepStatuses: o.steps.map((s) => s.status).join(","),
    checkpoints: o.checkpoints.length,
  });
  console.log(`[w7-purefile] DB 模式：${JSON.stringify(pick(dbMode))}`);
  console.log(`[w7-purefile] 純檔案模式：${JSON.stringify(pick(fileMode))}`);
  // 對照組應有步驟與斷點（既有證據：QA_P3-6 §15.2）；實驗組只量不判：批次本身仍要能跑完，否則這個比較沒有意義
  expect(dbMode.steps.length, "DB 模式的步驟時間軸不為空").toBeGreaterThan(0);
  expect(dbMode.checkpoints.length, "DB 模式的斷點清單不為空").toBeGreaterThan(0);
  expect(fileMode.status, "純檔案模式的批次也能跑到終態").toBe("COMPLETED");
  expect(fileMode.instance, "批次確實是由變體 Bridge 跑的").toBe("w7-purefile");
});
