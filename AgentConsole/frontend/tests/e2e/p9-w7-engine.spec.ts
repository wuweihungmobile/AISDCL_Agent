import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

import { RUN } from "./helpers";
import { E2E_ROOT, NEEDS_BRIDGE, bootstrapSettings, call, createFixture, dataOf, ensureQuota, getRun, poll, type Fixture, type RunView } from "./realBackend";
import { BRIDGE_LOG, PG_CONTAINER, psql } from "./w5";
import { FakeModelServer, MOCK_CLAUDE, filesContaining, walkFiles, yamlLoad } from "./w7";

/**
 * W7 複驗：契約 v1.3 E2E-14 第 1～7 列（D-11、API-AUT-06、API-SET-10）＋審查 V-12（附錄 C 標 ENGINE 的其餘鍵）。
 * 對真後端（e2e profile）＋真 Bridge＋aisdlc-mock-claude；磁碟斷言讀 `<ENGINE_WORKSPACE>/<runId>/config.yaml`（用 YAML 解析器，不比對文字）；
 * 假伺服器（`w7.ts` 的 FakeModelServer）依請求 JSON 的 messages[0].content 分類（correction_prompt／evolution_type／is_achieved），立即回應。
 * 假金鑰 `e2e-fake-key` 不以 `sk-` 開頭（機密掃描）；情境結束一律清空金鑰並把本檔改過的旗標與參數還原（E2E-02～E2E-08 的前提，契約 §5.0.2）。
 * 資源使用（E2E-14 第 8～9 列）在 p9-w7-resources.spec.ts。輪詢一律用 viewer、寫入用 operator／admin（限流以 JWT subject 計）。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const KEY = "e2e-fake-key";
const nm = (base: string) => `${base} ${RUN}`;
const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED"];
const execBody = (level: number) => ({ autonomyLevel: level, tokenBudget: 100000, scope: { mode: "ALL" } });
const WORKSPACE = path.join(E2E_ROOT, "workspace");
const runDir = (runId: string) => path.join(WORKSPACE, runId);

type Caps = { autoMutation: string; selfEvolution: string };
type EngineCfg = {
  claude?: { command?: string; extra_args?: string[]; continue_flag?: string; encoding?: string };
  minimax?: { base_url?: string; model?: string; timeout_seconds?: number; enable_kernel_brain?: boolean; api_key?: unknown };
  playbook?: Record<string, unknown>;
  token_guard?: { compact_threshold_pct?: number; halt_threshold_pct?: number; auto_resume?: boolean; max_auto_resumes?: number };
  storage?: unknown;
};
type StepRow = { stepId: string; status: string; attempt?: number };

const model = new FakeModelServer();

const diskConfig = (runId: string): Promise<EngineCfg> => yamlLoad<EngineCfg>(path.join(runDir(runId), "config.yaml"));

async function put(request: APIRequestContext, category: string, key: string, value: string): Promise<void> {
  const r = await call(request, "admin", "PUT", `/api/v1/settings/${category}/${key}`, { value });
  expect(r.status, `PUT ${category}.${key}=${value} → ${JSON.stringify(r.json).slice(0, 300)}`).toBe(200);
}
async function reset(request: APIRequestContext, category: string, key: string): Promise<void> {
  const r = await call(request, "admin", "POST", `/api/v1/settings/${category}/${key}/reset`);
  expect(r.status, `reset ${category}.${key} → ${JSON.stringify(r.json).slice(0, 300)}`).toBe(200);
}
const setKey = async (request: APIRequestContext): Promise<void> => {
  const r = await call(request, "admin", "PUT", "/api/v1/settings/model/apiKey", { value: KEY, confirm: true });
  expect(r.status, `PUT model.apiKey → ${JSON.stringify(r.json).slice(0, 300)}`).toBe(200);
};
const clearKey = async (request: APIRequestContext): Promise<void> => {
  expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);
};
/** 情境結束／開始時的共通還原：金鑰清空、三個旗標回 false、假伺服器回到 200 並清空紀錄。 */
async function baseline(request: APIRequestContext): Promise<void> {
  await clearKey(request);
  for (const [category, key] of [
    ["agent", "enableAutoMutation"],
    ["agent", "enableSelfEvolution"],
    ["model", "enableKernelBrain"],
  ] as const)
    await put(request, category, key, "false");
  model.status = 200;
  model.reset();
}

async function start(request: APIRequestContext, f: Fixture, level: number): Promise<{ id: string; caps: Caps | undefined; body: string }> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, execBody(level));
  expect(r.status, `execute ${f.name} → ${JSON.stringify(r.json).slice(0, 400)}`).toBe(201);
  const d = dataOf<{ id: string; engineCapabilities?: Caps }>(r);
  return { id: d.id, caps: d.engineCapabilities, body: JSON.stringify(r.json) };
}

/** 等批次進終態；FAILED 時再等審核項建立（Bridge 直寫 DB 的終態比 Console 消費事件建審核項早一步）。 */
const finish = (request: APIRequestContext, runId: string, timeoutMs = 150_000): Promise<RunView> =>
  poll(
    () => getRun(request, runId),
    (r) => TERMINAL.includes(r.status) && (r.status !== "FAILED" || (r.pendingReviews ?? []).length > 0),
    `批次 ${runId} 進入終態`,
    timeoutMs,
  );

/** 自治等級 3 在目標邊界會暫停等審核：到終態前把出現的審核項一律通過。 */
async function finishApproving(request: APIRequestContext, runId: string, timeoutMs = 150_000): Promise<RunView> {
  const t0 = Date.now();
  for (;;) {
    const r = await getRun(request, runId);
    if (TERMINAL.includes(r.status) && (r.status !== "FAILED" || (r.pendingReviews ?? []).length > 0)) return r;
    for (const p of r.pendingReviews ?? []) {
      const ok = await call(request, "operator", "POST", `/api/v1/executions/${runId}/review/${p.id}`, { decision: "APPROVE", comment: "w7 qa" });
      expect([200, 204, 409], `審核 ${p.id} → ${JSON.stringify(ok.json).slice(0, 200)}`).toContain(ok.status);
    }
    if (Date.now() - t0 > timeoutMs) throw new Error(`批次 ${runId} 在 ${timeoutMs}ms 內沒有進入終態：${JSON.stringify(r).slice(0, 400)}`);
    await new Promise((res) => setTimeout(res, 2000));
  }
}

async function steps(request: APIRequestContext, runId: string): Promise<StepRow[]> {
  return dataOf<{ content: StepRow[] }>(await call(request, "viewer", "GET", `/api/v1/executions/${runId}/steps?size=200`)).content;
}

async function cancelAndWait(request: APIRequestContext, runId: string): Promise<void> {
  await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`);
  await poll(
    () => getRun(request, runId),
    (r) => TERMINAL.includes(r.status),
    `批次 ${runId} 取消後進入終態`,
    60_000,
    1500,
  );
}

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  await model.listen();
  await put(request, "model", "apiUrl", model.endpoint);
  await baseline(request);
});

test.afterAll(async ({ request }) => {
  await baseline(request);
  await call(request, "admin", "POST", "/api/v1/settings/model/apiUrl/reset");
  await model.close();
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 50);
  await ensureQuota(request, "viewer", 70);
});

test.describe("E2E-14：D-11 引擎旋鈕（磁碟上的引擎設定檔、假模型伺服器的請求分類）", () => {
  test.setTimeout(300_000);
  let firstRunId = "";

  test("列 1｜等級 7＋金鑰、全部步驟成功：{ENABLED, ENABLED}；磁碟 minimax.enable_kernel_brain＝true、無惰性鍵、無金鑰明文；Brain 零校正請求", async ({ request }) => {
    await baseline(request);
    await setKey(request);
    const f = await createFixture(request, { name: nm("QA E2E-14 列1"), kind: "A", level: 4 });
    const run = await start(request, f, 7);
    firstRunId = run.id;
    expect(run.caps, "201 回應").toEqual({ autoMutation: "ENABLED", selfEvolution: "ENABLED" });
    const done = await finish(request, run.id);
    expect(done.status, JSON.stringify(done).slice(0, 300)).toBe("COMPLETED");
    const detail = dataOf<{ engineCapabilities?: Caps }>(await call(request, "viewer", "GET", `/api/v1/executions/${run.id}`));
    expect(detail.engineCapabilities, "詳情與 201 同值").toEqual({ autoMutation: "ENABLED", selfEvolution: "ENABLED" });

    const cfg = await diskConfig(run.id);
    expect(cfg.minimax?.enable_kernel_brain, "磁碟 config：布林 true").toBe(true);
    expect(cfg.minimax?.base_url, "minimax.base_url 等於 model.apiUrl（原樣）").toBe(model.endpoint);
    expect(cfg.minimax?.model).toBe("e2e-model");
    expect(typeof cfg.minimax?.timeout_seconds).toBe("number");
    expect(cfg.playbook?.step_timeout_seconds, "playbook.step_timeout_seconds 存在").toBeDefined();
    expect(Object.keys(cfg.playbook ?? {}), "否定斷言：Console 不送惰性鍵").not.toContain("max_evolutions");
    expect(Object.keys(cfg.playbook ?? {})).not.toContain("require_evolution_signoff");
    expect(Object.keys(cfg.minimax ?? {}), "minimax 區段沒有 api_key").not.toContain("api_key");

    const record = JSON.parse(readFileSync(path.join(runDir(run.id), "run.json"), "utf-8")) as { env_keys: string[] };
    expect(record.env_keys, "run.json 只記環境變數『名稱』").toContain("MINIMAX_API_KEY");
    expect(filesContaining(runDir(run.id), KEY), `整個 run 目錄（${walkFiles(runDir(run.id)).length} 個檔）都搜不到金鑰的值（A5）`).toEqual([]);
    expect(run.body, "201 回應不含金鑰").not.toContain(KEY);
    if (BRIDGE_LOG) expect(readFileSync(BRIDGE_LOG, "utf-8"), "Bridge 日誌不含金鑰").not.toContain(KEY);

    expect(model.count("correction"), "沒有失敗步驟，Brain 沒被諮詢").toBe(0);
    const authed = model.requests.filter((r) => r.auth !== null);
    for (const r of authed) expect(r.auth, "金鑰經 env 到達引擎，外呼帶它").toBe(`Bearer ${KEY}`);
    console.log(`[w7-engine] 列 1：caps=${JSON.stringify(run.caps)}、假伺服器請求 ${model.requests.map((r) => r.kind).join("、") || "（無）"}；run 目錄 ${walkFiles(runDir(run.id)).length} 個檔`);
  });

  test("列 7｜凍結與缺席：清掉金鑰後詳情仍是列 1 的值；批次列表項沒有該欄位；DB 設為 NULL 後詳情缺席或 null", async ({ request }) => {
    test.skip(!firstRunId, "需要列 1 的批次");
    expect(PG_CONTAINER, "需要 E2E_PG_CONTAINER 才能直接改 DB").toBeTruthy();
    await clearKey(request);
    const frozen = dataOf<{ engineCapabilities?: Caps; projectId: string }>(await call(request, "viewer", "GET", `/api/v1/executions/${firstRunId}`));
    expect(frozen.engineCapabilities, "建立時凍結，不隨設定變").toEqual({ autoMutation: "ENABLED", selfEvolution: "ENABLED" });
    const list = dataOf<{ content: Array<Record<string, unknown>> }>(await call(request, "viewer", "GET", `/api/v1/projects/${frozen.projectId}/executions`)).content;
    expect(list.length).toBeGreaterThanOrEqual(1);
    for (const item of list) expect(Object.keys(item), "批次列表項不帶 engineCapabilities").not.toContain("engineCapabilities");
    const before = await psql(`select engine_capabilities from console.execution_runs where id='${firstRunId}'`);
    expect(before, "DB 欄位有值（jsonb）").toContain("ENABLED");
    await psql(`update console.execution_runs set engine_capabilities = null where id='${firstRunId}'`);
    const after = dataOf<{ engineCapabilities?: Caps | null }>(await call(request, "viewer", "GET", `/api/v1/executions/${firstRunId}`));
    expect(after.engineCapabilities ?? null, "V10 之前的批次：缺席或 null").toBeNull();
    console.log(`[w7-engine] 列 7：DB 欄位原值 ${before}；設為 NULL 後詳情的 engineCapabilities＝${JSON.stringify(after.engineCapabilities ?? null)}`);
  });

  test("列 2｜等級 7＋金鑰＋失敗步驟（假伺服器全回 500）：Brain 真的被呼叫、T1 只有 1 個 attempt、直接升級；沒有 evolved_*.yaml、T2／T3 未執行", async ({ request }) => {
    await baseline(request);
    await setKey(request);
    model.status = 500;
    const f = await createFixture(request, { name: nm("QA E2E-14 列2"), kind: "A", level: 4, failTasks: [1] });
    const run = await start(request, f, 7);
    expect(run.caps).toEqual({ autoMutation: "ENABLED", selfEvolution: "ENABLED" });
    const done = await finish(request, run.id, 200_000);
    expect(done.status, JSON.stringify(done).slice(0, 300)).toBe("FAILED");
    expect(done.reason ?? "", "reason 以「引擎升級（ESCALATION）」開頭").toMatch(/^引擎升級（ESCALATION）/);
    expect(model.count("correction"), "Brain 在第一次失敗後立刻被諮詢（≥1 個校正請求）").toBeGreaterThanOrEqual(1);
    const rows = await steps(request, run.id);
    const seq = rows.map((s) => `${s.stepId}:${s.status}`);
    expect(seq, "T1 只有 1 個 attempt（沒有 RETRYING）；T2、T3 未執行").toEqual(["G1-T1:STARTED", "G1-T1:FAILED"]);
    expect(done.totalTokensUsed, "Brain 呼叫失敗讓該步驟直接升級：1 個 attempt＝1,240").toBe(1240);
    expect(
      walkFiles(runDir(run.id)).filter((p) => /(^|\/)evolved_[^/]*\.ya?ml$/.test(p)),
      "run 工作區沒有 evolved_*.yaml",
    ).toEqual([]);
    expect(
      walkFiles(f.dir).filter((p) => /(^|\/)evolved_[^/]*\.ya?ml$/.test(p)),
      "專案目錄沒有 evolved_*.yaml",
    ).toEqual([]);
    console.log(`[w7-engine] 列 2：reason＝${done.reason}；steps＝${seq.join("、")}；tokens＝${done.totalTokensUsed}；假伺服器請求＝${model.requests.map((r) => r.kind).join("、")}`);
  });

  test("列 3｜對照：等級 3＋金鑰（Brain 關）、同一個失敗夾具：{OFF, ENABLED}；enable_kernel_brain＝false；T1 有 2 個 attempt；零校正、演化提案 ≥1；沒有 evolved_*.yaml", async ({ request }) => {
    await baseline(request);
    await setKey(request);
    model.status = 500;
    const f = await createFixture(request, { name: nm("QA E2E-14 列3"), kind: "A", level: 4, failTasks: [1] });
    const run = await start(request, f, 3);
    expect(run.caps).toEqual({ autoMutation: "OFF", selfEvolution: "ENABLED" });
    const done = await finish(request, run.id, 200_000);
    expect(done.status, JSON.stringify(done).slice(0, 300)).toBe("FAILED");
    expect((await diskConfig(run.id)).minimax?.enable_kernel_brain, "磁碟 config：布林 false（顯式送）").toBe(false);
    const seq = (await steps(request, run.id)).map((s) => `${s.stepId}:${s.status}`);
    expect(seq, "T1 有 2 個 attempt：STARTED→RETRYING→FAILED").toEqual(["G1-T1:STARTED", "G1-T1:RETRYING", "G1-T1:FAILED"]);
    expect(done.totalTokensUsed, "2 個 attempt＝2,480").toBe(2480);
    expect(model.count("correction"), "整個批次期間校正請求恆為 0（Brain 關）").toBe(0);
    expect(model.count("evolution"), "有金鑰＝selfEvolution ENABLED：失敗型 ESCALATION 後演化提案 ≥1").toBeGreaterThanOrEqual(1);
    expect(walkFiles(runDir(run.id)).filter((p) => /(^|\/)evolved_[^/]*\.ya?ml$/.test(p))).toEqual([]);
    expect(walkFiles(f.dir).filter((p) => /(^|\/)evolved_[^/]*\.ya?ml$/.test(p))).toEqual([]);
    console.log(`[w7-engine] 列 3：steps＝${seq.join("、")}；tokens＝${done.totalTokensUsed}；假伺服器請求＝${model.requests.map((r) => r.kind).join("、")}`);
  });

  test("列 4｜沒有金鑰、等級 7：{UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY}；磁碟 config 沒有 minimax 區段；run COMPLETED（沒有因 enable_kernel_brain 缺金鑰而離開碼 1）；假伺服器零請求", async ({
    request,
  }) => {
    await baseline(request);
    const f = await createFixture(request, { name: nm("QA E2E-14 列4"), kind: "A", level: 4 });
    const run = await start(request, f, 7);
    expect(run.caps).toEqual({ autoMutation: "UNAVAILABLE_NO_API_KEY", selfEvolution: "UNAVAILABLE_NO_API_KEY" });
    const done = await finish(request, run.id);
    expect(done.status, JSON.stringify(done).slice(0, 300)).toBe("COMPLETED");
    const cfg = await diskConfig(run.id);
    expect(Object.keys(cfg), "沒有 minimax 區段").not.toContain("minimax");
    const record = JSON.parse(readFileSync(path.join(runDir(run.id), "run.json"), "utf-8")) as { env_keys: string[] };
    expect(record.env_keys, "沒有金鑰就不帶 MINIMAX_API_KEY").not.toContain("MINIMAX_API_KEY");
    expect(model.count(), "假伺服器零請求").toBe(0);
  });

  test("列 5｜等級 3、沒有金鑰、旗標全 false：{OFF, OFF}；磁碟 config 沒有 minimax 區段；COMPLETED（目標邊界的審核一律通過）", async ({ request }) => {
    await baseline(request);
    const f = await createFixture(request, { name: nm("QA E2E-14 列5"), kind: "A", level: 4 });
    const run = await start(request, f, 3);
    expect(run.caps).toEqual({ autoMutation: "OFF", selfEvolution: "OFF" });
    const done = await finishApproving(request, run.id);
    expect(done.status, JSON.stringify(done).slice(0, 300)).toBe("COMPLETED");
    expect(Object.keys(await diskConfig(run.id)), "沒有 minimax 區段").not.toContain("minimax");
    expect(model.count(), "假伺服器零請求").toBe(0);
  });

  test("列 6｜旗標單獨生效（等級 3）：①金鑰＋enableAutoMutation ②金鑰＋model.enableKernelBrain 皆 {ENABLED, ENABLED}；③無金鑰＋enableSelfEvolution {OFF, UNAVAILABLE_NO_API_KEY}；④金鑰＋enableSelfEvolution {OFF, ENABLED}（enable_kernel_brain false）", async ({
    request,
  }) => {
    const cases: Array<{ label: string; key: boolean; flag: [string, string]; caps: Caps; brain: boolean | undefined }> = [
      { label: "①", key: true, flag: ["agent", "enableAutoMutation"], caps: { autoMutation: "ENABLED", selfEvolution: "ENABLED" }, brain: true },
      { label: "②", key: true, flag: ["model", "enableKernelBrain"], caps: { autoMutation: "ENABLED", selfEvolution: "ENABLED" }, brain: true },
      { label: "③", key: false, flag: ["agent", "enableSelfEvolution"], caps: { autoMutation: "OFF", selfEvolution: "UNAVAILABLE_NO_API_KEY" }, brain: undefined },
      { label: "④", key: true, flag: ["agent", "enableSelfEvolution"], caps: { autoMutation: "OFF", selfEvolution: "ENABLED" }, brain: false },
    ];
    for (const c of cases) {
      await baseline(request); // 每次只改一個旗標，跑完還原
      if (c.key) await setKey(request);
      await put(request, c.flag[0], c.flag[1], "true");
      const f = await createFixture(request, { name: nm(`QA E2E-14 列6${c.label}`), kind: "A", level: 4 });
      const run = await start(request, f, 3);
      expect(run.caps, `${c.label} ${c.flag.join(".")}（金鑰 ${c.key ? "有" : "無"}）`).toEqual(c.caps);
      const cfg = await diskConfig(run.id);
      if (c.brain === undefined) expect(Object.keys(cfg), `${c.label} 無金鑰：沒有 minimax 區段`).not.toContain("minimax");
      else expect(cfg.minimax?.enable_kernel_brain, `${c.label} 磁碟 enable_kernel_brain`).toBe(c.brain);
      await cancelAndWait(request, run.id);
      console.log(
        `[w7-engine] 列 6${c.label}：${c.flag.join(".")}＝true、金鑰${c.key ? "有" : "無"} → ${JSON.stringify(run.caps)}、磁碟 enable_kernel_brain＝${c.brain === undefined ? "（無 minimax 區段）" : c.brain}`,
      );
    }
    await baseline(request);
  });
});

test.describe("V-12：附錄 C 標 ENGINE 的其餘鍵——磁碟上的 config.yaml 與 playbook.yaml 逐鍵斷言（只讀設定檔，不新增引擎行為）", () => {
  test.setTimeout(300_000);

  test("ENGINE 鍵目錄＝十六把；其中十五把各設一個非預設值，起一個批次，磁碟上的引擎設定逐鍵吻合（第十六把 agent.enableAutoMutation 在列 6①）；結束後全部還原", async ({ request }) => {
    // 目錄面：GET /settings 的 effect 標籤（附錄 C）——ENGINE 恰為這十六把，UNVERIFIED 恰為 sdd 的三把，五十鍵全數有標籤（L-02 的可追溯面）
    const all = dataOf<Record<string, Array<{ key: string; effect: string }>>>(await call(request, "viewer", "GET", "/api/v1/settings"));
    const byEffect: Record<string, string[]> = {};
    for (const [category, rows] of Object.entries(all)) for (const r of rows) (byEffect[r.effect] ??= []).push(`${category}.${r.key}`);
    const SIXTEEN = [
      "model.apiUrl",
      "model.apiKey",
      "model.name",
      "model.timeout",
      "model.enableKernelBrain",
      "agent.taskTimeout",
      "agent.maxRetries",
      "agent.enableAutoMutation",
      "execution.compactThresholdPct",
      "execution.haltThresholdPct",
      "execution.autoResume",
      "execution.maxAutoResumes",
      "autoclaude.claudeCommand",
      "autoclaude.claudeExtraArgs",
      "autoclaude.claudeContinueFlag",
      "autoclaude.claudeEncoding",
    ];
    expect([...(byEffect.ENGINE ?? [])].sort(), "effect＝ENGINE 的鍵恰為附錄 C 的十六把").toEqual([...SIXTEEN].sort());
    expect([...(byEffect.UNVERIFIED ?? [])].sort(), "effect＝UNVERIFIED 恰為 sdd 的三把").toEqual(["sdd.specFormat", "sdd.validationLevel", "sdd.workflowEngine"]);
    expect(
      Object.values(byEffect).reduce((n, v) => n + v.length, 0),
      "五十鍵皆有標籤",
    ).toBe(50);
    console.log(
      `[w7-engine] 設定鍵目錄（GET /settings 的 effect）：${Object.entries(byEffect)
        .map(([k, v]) => `${k} ${v.length}`)
        .join("、")}；STORED_ONLY＝${(byEffect.STORED_ONLY ?? []).join("、")}`,
    );
    await baseline(request);
    await setKey(request);
    const extraArgs = "--e2e-extra=1 --e2e-flag";
    try {
      await put(request, "model", "name", "e2e-model-v12");
      await put(request, "model", "timeout", "45");
      await put(request, "model", "enableKernelBrain", "true");
      await put(request, "agent", "taskTimeout", "777");
      await put(request, "agent", "maxRetries", "2");
      await put(request, "execution", "haltThresholdPct", "93"); // 跨鍵校驗：先抬 halt、再降 compact
      await put(request, "execution", "compactThresholdPct", "71");
      await put(request, "execution", "autoResume", "true");
      await put(request, "execution", "maxAutoResumes", "7");
      await put(request, "autoclaude", "claudeExtraArgs", extraArgs);
      await put(request, "autoclaude", "claudeContinueFlag", "--continue-e2e");
      await put(request, "autoclaude", "claudeEncoding", "utf-8-sig");

      const f = await createFixture(request, { name: nm("QA W7 V-12"), kind: "A", level: 4 });
      const run = await start(request, f, 4);
      expect(run.caps, "model.enableKernelBrain＝true 且有金鑰：autoMutation ENABLED").toEqual({ autoMutation: "ENABLED", selfEvolution: "ENABLED" });
      const cfg = await diskConfig(run.id);
      const table: Array<[string, unknown, unknown]> = [
        ["autoclaude.claudeCommand → claude.command", cfg.claude?.command, MOCK_CLAUDE],
        ["autoclaude.claudeExtraArgs → claude.extra_args", cfg.claude?.extra_args, ["--e2e-extra=1", "--e2e-flag"]],
        ["autoclaude.claudeContinueFlag → claude.continue_flag", cfg.claude?.continue_flag, "--continue-e2e"],
        ["autoclaude.claudeEncoding → claude.encoding", cfg.claude?.encoding, "utf-8-sig"],
        ["agent.taskTimeout → playbook.step_timeout_seconds", cfg.playbook?.step_timeout_seconds, 777],
        ["execution.compactThresholdPct → token_guard.compact_threshold_pct", cfg.token_guard?.compact_threshold_pct, 71],
        ["execution.haltThresholdPct → token_guard.halt_threshold_pct", cfg.token_guard?.halt_threshold_pct, 93],
        ["execution.autoResume → token_guard.auto_resume", cfg.token_guard?.auto_resume, true],
        ["execution.maxAutoResumes → token_guard.max_auto_resumes", cfg.token_guard?.max_auto_resumes, 7],
        ["model.apiUrl → minimax.base_url", cfg.minimax?.base_url, model.endpoint],
        ["model.name → minimax.model", cfg.minimax?.model, "e2e-model-v12"],
        ["model.timeout → minimax.timeout_seconds", cfg.minimax?.timeout_seconds, 45],
        ["model.enableKernelBrain → minimax.enable_kernel_brain", cfg.minimax?.enable_kernel_brain, true],
      ];
      for (const [what, actual, expected] of table) {
        if (what.startsWith("autoclaude.claudeCommand")) expect(path.normalize(String(actual)).toLowerCase(), what).toBe(path.normalize(String(expected)).toLowerCase());
        else expect(actual, what).toEqual(expected);
      }
      // agent.maxRetries → playbook.yaml 的 global_invariants.max_retries_per_step（每個任務自己的 max_retries 優先，夾具任務各為 1）
      const pb = await yamlLoad<{ global_invariants?: { max_retries_per_step?: number }; tasks?: Array<{ max_retries?: number }> }>(path.join(runDir(run.id), "playbook.yaml"));
      expect(pb.global_invariants?.max_retries_per_step, "agent.maxRetries → global_invariants.max_retries_per_step").toBe(2);
      expect(
        (pb.tasks ?? []).map((t) => t.max_retries),
        "任務自己的 maxRetries 優先",
      ).toEqual([1, 1, 1]);
      // model.apiKey 走 env，不進磁碟
      const record = JSON.parse(readFileSync(path.join(runDir(run.id), "run.json"), "utf-8")) as { env_keys: string[] };
      expect(record.env_keys).toContain("MINIMAX_API_KEY");
      expect(filesContaining(runDir(run.id), KEY), "model.apiKey：只經 env，run 目錄搜不到明文").toEqual([]);
      console.log(
        `[w7-engine] V-12：${table.length + 1} 把鍵（另 model.apiKey 走 env）逐鍵吻合；磁碟 claude＝${JSON.stringify(cfg.claude)}、token_guard＝${JSON.stringify(cfg.token_guard)}、minimax＝${JSON.stringify(cfg.minimax)}`,
      );
      await cancelAndWait(request, run.id);
    } finally {
      // 還原：先降 halt 的跨鍵順序（compact 先回 80、halt 再回 90），其餘 reset 回預設，再把 bootstrap 值補回
      for (const [category, key] of [
        ["execution", "compactThresholdPct"],
        ["execution", "haltThresholdPct"],
        ["execution", "maxAutoResumes"],
        ["agent", "taskTimeout"],
        ["autoclaude", "claudeExtraArgs"],
        ["autoclaude", "claudeContinueFlag"],
        ["autoclaude", "claudeEncoding"],
      ] as const)
        await reset(request, category, key);
      await bootstrapSettings(request, MOCK_CLAUDE); // autoclaude.claudeCommand、execution.autoResume=false、agent.maxRetries=1、model.name、model.timeout
      await baseline(request);
    }
  });
});
