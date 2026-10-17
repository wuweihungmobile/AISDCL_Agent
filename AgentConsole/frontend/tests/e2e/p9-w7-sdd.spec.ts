import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { API_URL, RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import { E2E_ROOT, NEEDS_BRIDGE, bootstrapSettings, call, createFixture, dataOf, ensureQuota, signIn, type Fixture } from "./realBackend";
import { MOCK_CLAUDE, REAL_FSM, dirSnapshot, startBridge, writeText, yamlDump, yamlLoad, type VariantBridge } from "./w7";

/**
 * W7 複驗：契約 v1.4 E2E-15（D-16：AISDLC_SDD 接入；API-ENG-01、NFR-OBS-01、BR-13、BR-14）。
 * 主體用**夾具**（`<E2E_ROOT>/sdd-fixture/AISDLC_SDD_v9.99`，QA 以 YAML 序列化器產生），不依賴 repo 內被 git 忽略的真實 FSM 檔（主控裁決 Q7）；
 * 真實檔只在第 12 列選跑（檔在才跑、不在就在報告寫明未跑）。第二個 Bridge 起在 18082（純檔案模式、只用它的 /sdd/*）；
 * 18083（SDD_ROOT 指向不存在的目錄）與 18084（乾淨 clone 等價：只有入口文件）各自驗一種「引擎不可用／空」。
 * 檔案 ↔ API ↔ 畫面（NFR-OBS-01 補強）：夾具檔由測試自己的 YAML 解析器（PyYAML）讀，不經 Bridge。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const nm = (base: string) => `${base} ${RUN}`;
const FIXTURE_ROOT = path.join(E2E_ROOT, "sdd-fixture");
const VERSION_DIR = path.join(FIXTURE_ROOT, "AISDLC_SDD_v9.99");
const FSM_DIR = path.join(VERSION_DIR, "build", "reports", "fsm");
const FRESH_ROOT = path.join(E2E_ROOT, "sdd-fresh");
const NONE_ROOT = path.join(E2E_ROOT, "no-such-dir");
const BRIDGES = path.join(E2E_ROOT, "w7-bridges");
const [P_SDD, P_NONE, P_FRESH] = [18082, 18083, 18084];
const ALPHA = path.join(FSM_DIR, "FSM-STATE-e2e-alpha.yaml");

type Json = Record<string, unknown>;
type SddProject = { project: string; source: string; currentState: string | null; updatedAt: string | null };
type Fsm = {
  project: string;
  currentState: string | null;
  currentSprint: number | null;
  sessionId: string | null;
  updatedAt: string | null;
  frozenStages: Json[];
  decisionTrace: Json[];
  source: string;
  humanPending: { count: number; items: Json[] };
  retryHistory: { count: number; last: Json | null };
  rtmCoverage: unknown;
};
type SddStatus = { available: boolean; reason: string | null; version: { latest: string; root: string } | null; projects: SddProject[]; fsm: Fsm | null; checkedAt: string };
type FsmDoc = { fsm_state: Json & { decision_trace: Json[]; retry_history: Record<string, { history: Json[] }>; human_pending_tracking: Json } };

const pad = (n: number) => String(n).padStart(2, "0");
/** 契約 M-20 的時間顯示：本機時區的 `YYYY-MM-DD HH:MM:SS`（與前端 sddTime 同一規則，測試端獨立實作）。 */
const localTime = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

const trace = (n: number): Json => ({
  ts: `2026-10-15T0${n}:00:00+00:00`,
  from: `STATE_${n - 1}`,
  to: `STATE_${n}`,
  reason: `r${n}`,
  spec_refs: [`FRD-00${n}`, "SRD-001"],
  agents_consulted: ["sa-analyst", "qa-tester"],
  trigger: n % 2 === 1 ? "auto" : "human",
});
const gate = (limit: number, current: number, history: Json[]): { current_count: number; max_limit: number; history: Json[] } => ({ current_count: current, max_limit: limit, history });

const alphaDoc = (): FsmDoc => ({
  fsm_state: {
    project: "e2e-alpha",
    session_id: "sid-alpha",
    created_at: "2026-10-15T00:00:00+00:00",
    updated_at: "2026-10-16T01:02:03+00:00",
    current_state: "IMPLEMENTATION",
    current_sprint: 2,
    retry_history: {
      SCG_VALIDATION: gate(3, 2, [
        { attempt: 1, date: "2026-10-15T09:00:00+00:00", failure_reason: "f1", scg_gate: "SCG-0" },
        { attempt: 2, date: "2026-10-15T10:00:00+00:00", failure_reason: "f2", scg_gate: "SCG-0" },
      ]),
      PR_REVIEW: gate(5, 1, [{ attempt: 1, date: "2026-10-15T11:00:00+00:00", failure_reason: "f3", scg_gate: "PR-1" }]),
      RTM_VERIFY: gate(2, 0, []),
    },
    human_pending_tracking: { entered_at: null, reminder_sent_at: null, reminder_hours: 72, escalation_hours: 168 },
    decision_trace: [1, 2, 3, 4, 5, 6, 7].map(trace),
    frozen_stages: [{ stage: "SCG-0" }],
  },
});
const bravoDoc = (): FsmDoc => ({
  fsm_state: {
    project: "e2e-bravo",
    session_id: "sid-bravo",
    created_at: "2026-10-15T00:00:00+00:00",
    updated_at: "2026-10-15T08:00:00+00:00",
    current_state: "HUMAN_PENDING",
    current_sprint: 1,
    retry_history: { SCG_VALIDATION: gate(3, 0, []), PR_REVIEW: gate(5, 0, []), RTM_VERIFY: gate(2, 0, []) },
    human_pending_tracking: { entered_at: "2026-10-15T08:00:00+00:00", reminder_sent_at: null, reminder_hours: 72, escalation_hours: 168 },
    decision_trace: [],
    frozen_stages: [],
  },
});

const sdd = async (request: APIRequestContext, query = "", role: "viewer" | "operator" | "admin" = "viewer") => call(request, role, "GET", `/api/v1/engines/sdd${query}`);
const status = async (request: APIRequestContext, query = ""): Promise<SddStatus> => {
  const r = await sdd(request, query);
  expect(r.status, JSON.stringify(r.json).slice(0, 400)).toBe(200);
  return dataOf<SddStatus>(r);
};
const setSddUrl = async (request: APIRequestContext, port: number | null) => {
  const r =
    port === null
      ? await call(request, "admin", "POST", "/api/v1/settings/sdd/engineUrl/reset")
      : await call(request, "admin", "PUT", "/api/v1/settings/sdd/engineUrl", { value: `http://127.0.0.1:${port}` });
  expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(200);
};
const deep = async (port: number) => {
  const res = await fetch(`http://127.0.0.1:${port}/health/deep`);
  return { status: res.status, body: (await res.json()) as { status: string; reason?: string; checks: Record<string, Json> } };
};

async function openCard(page: Page, request: APIRequestContext, f: Fixture): Promise<void> {
  await signIn(page, request, "viewer");
  await page.goto(`/projects/${f.projectId}/monitor`);
  await expect(page.getByRole("heading", { name: `專案監控：${f.name}` })).toBeVisible(FIRST_LOAD);
  await expect(page.getByTestId("sdd-card")).toBeVisible(FIRST_LOAD);
}

let bridge: VariantBridge | null = null;
let project: Fixture;
let alpha0: FsmDoc;
let bravo0: FsmDoc;

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  rmSync(FIXTURE_ROOT, { recursive: true, force: true });
  rmSync(FRESH_ROOT, { recursive: true, force: true });
  mkdirSync(path.join(VERSION_DIR, "build", "reports", "fsm"), { recursive: true });
  writeText(path.join(VERSION_DIR, "AISDLC_SDD_INIT.md"), "# AISDLC_SDD（E2E-15 夾具）\n");
  alpha0 = alphaDoc();
  bravo0 = bravoDoc();
  await yamlDump(path.join(FSM_DIR, "FSM-STATE-e2e-alpha.yaml"), alpha0);
  await yamlDump(path.join(FSM_DIR, "FSM-STATE-e2e-bravo.yaml"), bravo0);
  writeText(path.join(FSM_DIR, "FSM-STATE-e2e-broken.yaml"), "fsm_state: [unclosed\n  project: : :\n");
  writeText(path.join(FSM_DIR, "FSM-STATE-bad name.yaml"), "fsm_state:\n  project: bad\n");
  writeText(path.join(FSM_DIR, "FSM-STATE-e2e-ignored.yml"), "fsm_state:\n  project: ignored\n");
  mkdirSync(path.join(FRESH_ROOT, "AISDLC_SDD_v9.98"), { recursive: true });
  writeText(path.join(FRESH_ROOT, "AISDLC_SDD_v9.98", "AISDLC_SDD_INIT.md"), "# AISDLC_SDD（乾淨 clone 等價）\n");
  bridge = await startBridge({ port: P_SDD, root: path.join(BRIDGES, "b18082"), instance: "e2e-sdd", sddRoot: FIXTURE_ROOT });
  await setSddUrl(request, P_SDD);
  project = await createFixture(request, { name: nm("QA E2E-15 專案"), kind: "A", level: 4 });
});

test.afterAll(async ({ request }) => {
  await setSddUrl(request, null).catch(() => undefined);
  await bridge?.stop();
  rmSync(FIXTURE_ROOT, { recursive: true, force: true });
  rmSync(FRESH_ROOT, { recursive: true, force: true });
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "viewer", 60);
});

test.describe("E2E-15：AISDLC_SDD 接入（夾具；NFR-OBS-01 檔案 ↔ API ↔ 畫面）", () => {
  test.setTimeout(300_000);
  let before: Record<string, string> = {};

  test("列 1｜清單：三筆（含空白的 bad name 自 v1.5 起屬淨化輸出域而列入，另有 alpha、bravo），broken 與 .yml 不在其中；version.latest＝AISDLC_SDD_v9.99；fsm＝null 且沒有 reason", async ({
    request,
  }) => {
    before = dirSnapshot(VERSION_DIR); // 列 11 的唯讀快照：第 1～5 列都不得改動夾具目錄
    const s = await status(request);
    expect(s.available).toBe(true);
    expect(s.reason ?? null).toBeNull();
    expect(s.version?.latest).toBe("AISDLC_SDD_v9.99");
    expect(s.version?.root ?? "", "root 是 Bridge 看到的目錄").toContain("AISDLC_SDD_v9.99");
    expect(
      s.projects.map((p) => p.project),
      "順序＝專案名不分大小寫升冪：bad name、alpha、bravo（契約 §1.7.1／§1.10.4：含空白的名稱屬 sanitize_component 輸出域，v1.5 起列入）；壞檔與 .yml 不列",
    ).toEqual(["bad name", "e2e-alpha", "e2e-bravo"]);
    expect(s.projects[0]).toEqual({ project: "bad name", source: "FSM-STATE-bad name.yaml", currentState: null, updatedAt: null });
    expect(s.projects[1]).toEqual({ project: "e2e-alpha", source: "FSM-STATE-e2e-alpha.yaml", currentState: "IMPLEMENTATION", updatedAt: "2026-10-16T01:02:03+00:00" });
    expect(s.projects[2]).toEqual({ project: "e2e-bravo", source: "FSM-STATE-e2e-bravo.yaml", currentState: "HUMAN_PENDING", updatedAt: "2026-10-15T08:00:00+00:00" });
    expect(s.fsm).toBeNull();
    expect(s.checkedAt, "UTC，…Z").toMatch(/Z$/);
    console.log(`[w7-sdd] 列 1（v1.5 對齊）：${JSON.stringify({ available: s.available, version: s.version?.latest, projects: s.projects.map((p) => `${p.project}:${p.currentState}`) })}`);
  });

  test("列 2｜單一專案 alpha：欄位與檔案「原樣」（decisionTrace 是檔內 7 筆的最後 5 筆，snake_case 鍵保留；frozenStages；retryHistory.last；rtmCoverage＝null）", async ({ request }) => {
    const file = await yamlLoad<FsmDoc>(ALPHA);
    const fs = file.fsm_state;
    const s = await status(request, "?project=e2e-alpha");
    const f = s.fsm!;
    expect(f).toBeTruthy();
    expect(f.currentState).toBe(fs.current_state);
    expect(f.currentSprint).toBe(fs.current_sprint);
    expect(f.sessionId).toBe(fs.session_id);
    expect(f.updatedAt).toBe(fs.updated_at);
    expect(f.decisionTrace, "長度 5，等於檔內 7 筆的最後 5 筆（舊→新），逐值相等").toHaveLength(5);
    expect(f.decisionTrace).toEqual(fs.decision_trace.slice(-5));
    expect(Object.keys(f.decisionTrace[0]).sort(), "保留 snake_case 鍵").toEqual(["agents_consulted", "from", "reason", "spec_refs", "to", "trigger", "ts"]);
    expect(f.frozenStages).toEqual(fs.frozen_stages);
    expect(f.humanPending).toEqual({ count: 0, items: [] });
    expect(f.retryHistory.count, "三閘 history 筆數總和＝2＋1＋0").toBe(3);
    expect(f.retryHistory.last, "date 最晚那筆（PR_REVIEW）加 gate 欄").toEqual({ attempt: 1, date: "2026-10-15T11:00:00+00:00", failure_reason: "f3", scg_gate: "PR-1", gate: "PR_REVIEW" });
    expect(f.rtmCoverage ?? null).toBeNull();
    expect(f.source).toBe("FSM-STATE-e2e-alpha.yaml");
    expect(f.project).toBe("e2e-alpha");
    expect(
      s.projects.map((p) => p.project),
      "清單照常（v1.5：三筆）",
    ).toEqual(["bad name", "e2e-alpha", "e2e-bravo"]);
  });

  test("列 3｜待人工：bravo 的 humanPending.count＝1 且 items[0].entered_at 原樣；retryHistory＝{0, null}", async ({ request }) => {
    const f = (await status(request, "?project=e2e-bravo")).fsm!;
    expect(f.currentState).toBe("HUMAN_PENDING");
    expect(f.humanPending.count).toBe(1);
    expect(f.humanPending.items[0].entered_at).toBe("2026-10-15T08:00:00+00:00");
    expect(f.retryHistory).toEqual({ count: 0, last: null });
    expect(f.decisionTrace).toEqual([]);
  });

  test("列 4｜找不到、壞檔、非法名：nope→fsm_not_found（200）；e2e-broken→fsm_state_unreadable（200）；a%20b、..%2Fx 自 v1.5 起是合法請求值（交 Bridge 淨化鏡像處理）→200＋fsm_not_found；201 字元與含 NUL 才回 400（errors[0].field＝project）", async ({
    request,
  }) => {
    const nope = await status(request, "?project=nope");
    expect({ available: nope.available, reason: nope.reason, fsm: nope.fsm }).toEqual({ available: true, reason: "fsm_not_found", fsm: null });
    expect(nope.projects, "projects 照常（v1.5：三筆）").toHaveLength(3);
    const broken = await status(request, "?project=e2e-broken");
    expect({ available: broken.available, reason: broken.reason, fsm: broken.fsm }).toEqual({ available: true, reason: "fsm_state_unreadable", fsm: null });
    // 契約 §1.7.1（v1.5 加註③）／§1.10.4：`project` 改為 1～200 字元、不含控制字元；Console 不淨化、不檢查 Windows 禁用字元，值原樣交給 Bridge。
    // `a b`（含空白）是淨化輸出域內的名稱：找不到狀態檔 → fsm_not_found；`../x` 的 URL 解碼後路由不匹配，Bridge 回沒有 reason 的 404，Console 暫轉成 fsm_not_found（§3.1.7 第 11 點）。
    for (const odd of ["a%20b", "..%2Fx"]) {
      const d = await status(request, `?project=${odd}`);
      expect({ available: d.available, reason: d.reason, fsm: d.fsm }, odd).toEqual({ available: true, reason: "fsm_not_found", fsm: null });
    }
    for (const bad of [encodeURIComponent("x".repeat(201)), "a%00b"]) {
      const r = await sdd(request, `?project=${bad}`);
      expect(r.status, bad.slice(0, 12)).toBe(400);
      expect((r.json.errors as Array<{ field: string }>)[0].field, bad.slice(0, 12)).toBe("project");
    }
  });

  test("列 5｜檔案 ↔ API ↔ 畫面（NFR-OBS-01 補強）：卡片的狀態、Sprint、更新時間、待人工、最近 5 筆決策（倒序）與夾具檔逐值一致，也與列 2 的 API 一致；改選 bravo → 等待人工確認", async ({
    page,
    request,
  }) => {
    const errors = collectConsoleErrors(page);
    const file = await yamlLoad<FsmDoc>(ALPHA);
    const fs = file.fsm_state;
    const api = (await status(request, "?project=e2e-alpha")).fsm!;
    await openCard(page, request, project);
    await page.getByTestId("sdd-project-select").selectOption("e2e-alpha");
    await expect(page.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    await expect(page.getByTestId("sdd-version")).toHaveText("AISDLC_SDD_v9.99");
    const card = page.getByTestId("sdd-fsm");
    await expect(card).toHaveAttribute("data-project", "e2e-alpha", FIRST_LOAD);
    // 檔 ↔ DOM
    await expect(page.getByTestId("sdd-state")).toHaveText(String(fs.current_state));
    await expect(page.getByTestId("sdd-sprint")).toHaveText(`Sprint ${fs.current_sprint}`);
    await expect(page.getByTestId("sdd-updated")).toHaveText(localTime(String(fs.updated_at)));
    await expect(page.getByTestId("sdd-human-pending")).toHaveText("無");
    const expected = fs.decision_trace.slice(-5).reverse();
    const rows = page.getByTestId("sdd-decision");
    await expect(rows).toHaveCount(5);
    for (let i = 0; i < 5; i += 1) {
      const d = expected[i] as { ts: string; from: string; to: string; reason: string };
      await expect(rows.nth(i).getByTestId("sdd-decision-ts")).toHaveText(localTime(d.ts));
      await expect(rows.nth(i).getByTestId("sdd-decision-transition")).toHaveText(`${d.from} → ${d.to}`);
      await expect(rows.nth(i).getByTestId("sdd-decision-reason")).toHaveText(d.reason);
    }
    // API ↔ DOM（列 2 的 API 值與同一個畫面）
    expect(api.currentState).toBe(await page.getByTestId("sdd-state").innerText());
    expect(`Sprint ${api.currentSprint}`).toBe(await page.getByTestId("sdd-sprint").innerText());
    expect(
      api.decisionTrace
        .slice()
        .reverse()
        .map((d) => d.reason),
    ).toEqual(await rows.getByTestId("sdd-decision-reason").allInnerTexts());
    await snap(page, "p9-w7-sdd-card.png", { focus: page.getByTestId("sdd-card") });
    // 改選 bravo
    await page.getByTestId("sdd-project-select").selectOption("e2e-bravo");
    await expect(page.getByTestId("sdd-fsm")).toHaveAttribute("data-project", "e2e-bravo", FIRST_LOAD);
    await expect(page.getByTestId("sdd-state")).toHaveText("HUMAN_PENDING");
    await expect(page.getByTestId("sdd-human-pending")).toHaveText("等待人工確認");
    await page.getByTestId("sdd-human-pending").click();
    await expect(page.getByTestId("sdd-human-pending-items")).toContainText(`進入時間：${localTime("2026-10-15T08:00:00+00:00")}`);
    await expect(page.getByTestId("sdd-decisions-empty")).toHaveText("尚無決策紀錄");
    console.log(
      `[w7-sdd] 列 5：alpha 畫面＝IMPLEMENTATION／Sprint 2／${localTime(String(fs.updated_at))}，5 筆決策倒序 ${expected.map((d) => (d as { reason: string }).reason).join("→")}；bravo＝等待人工確認`,
    );
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("列 10｜權限：未認證 401；viewer／operator／admin 皆 200", async ({ request }) => {
    const anon = await request.get(`${API_URL}/api/v1/engines/sdd`, { failOnStatusCode: false });
    expect(anon.status()).toBe(401);
    for (const role of ["viewer", "operator", "admin"] as const) expect((await sdd(request, "", role)).status, role).toBe(200);
  });

  test("列 11（前半）｜只讀：第 1～5、10 列前後夾具目錄（遞迴）mtime 與大小快照完全相同", async () => {
    expect(Object.keys(before).length, "快照有東西").toBeGreaterThan(5);
    expect(dirSnapshot(VERSION_DIR), "Bridge 與 console-api 都不新增、不改動任何檔案").toEqual(before);
  });

  test("列 6｜檔案變動後下一輪輪詢跟上（不整頁重載）；讀到壞檔時顯示「FSM 狀態檔無法讀取」、下一輪恢復", async ({ page, request }) => {
    test.setTimeout(420_000);
    const errors = collectConsoleErrors(page);
    await openCard(page, request, project);
    await page.getByTestId("sdd-project-select").selectOption("e2e-alpha");
    await expect(page.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION", FIRST_LOAD);
    await page.evaluate(() => ((window as unknown as { __w7Marker: string }).__w7Marker = "alive"));
    // 改寫：current_state 換值、updated_at 更新、decision_trace 加一筆
    const changed = alphaDoc();
    changed.fsm_state.current_state = "PR_REVIEW";
    changed.fsm_state.updated_at = "2026-10-16T02:03:04+00:00";
    changed.fsm_state.decision_trace.push(trace(8));
    await yamlDump(ALPHA, changed);
    const t0 = Date.now();
    await expect(page.getByTestId("sdd-state")).toHaveText("PR_REVIEW", { timeout: 50_000 });
    const lag = Date.now() - t0;
    await expect(page.getByTestId("sdd-updated")).toHaveText(localTime("2026-10-16T02:03:04+00:00"));
    await expect(page.getByTestId("sdd-decision").first().getByTestId("sdd-decision-reason")).toHaveText("r8");
    expect(await page.evaluate(() => (window as unknown as { __w7Marker?: string }).__w7Marker), "沒有整頁重載").toBe("alive");
    // 壞檔（寫到一半的檔）：卡片不崩潰，顯示無法讀取
    writeFileSync(ALPHA, "fsm_state: [unclosed\n  project: : :\n", "utf-8");
    await expect(page.getByTestId("sdd-message")).toHaveText("FSM 狀態檔無法讀取", { timeout: 50_000 });
    await expect(page.getByTestId("sdd-message")).toHaveAttribute("data-reason", "fsm_state_unreadable");
    // 恢復成可讀：下一輪回來
    await yamlDump(ALPHA, changed);
    await expect(page.getByTestId("sdd-state")).toHaveText("PR_REVIEW", { timeout: 50_000 });
    expect(await page.evaluate(() => (window as unknown as { __w7Marker?: string }).__w7Marker), "全程沒有整頁重載").toBe("alive");
    console.log(`[w7-sdd] 列 6：改檔後卡片 ${lag}ms 內更新為 PR_REVIEW／r8；壞檔顯示「FSM 狀態檔無法讀取」；恢復後下一輪回來；全程未重載`);
    expect(
      errors.filter((e) => !/fsm_state_unreadable|422/.test(e)),
      "整段流程不應有主控台錯誤",
    ).toEqual([]);
    await yamlDump(ALPHA, alphaDoc()); // 還原夾具
  });

  test("列 7｜引擎不可用（Bridge 不可達）：200、available＝false、reason＝bridge_unreachable、version＝null、projects＝[]；卡片「Engine Bridge 無法連線」；重啟後下一輪復原", async ({
    page,
    request,
  }) => {
    test.setTimeout(420_000);
    const errors = collectConsoleErrors(page);
    await openCard(page, request, project);
    await expect(page.getByTestId("sdd-status")).toHaveAttribute("data-available", "true", FIRST_LOAD);
    await bridge!.stop();
    const s = await sdd(request);
    expect(s.status, "不是 502").toBe(200);
    const d = dataOf<SddStatus>(s);
    expect({ available: d.available, reason: d.reason, version: d.version, projects: d.projects, fsm: d.fsm }).toEqual({
      available: false,
      reason: "bridge_unreachable",
      version: null,
      projects: [],
      fsm: null,
    });
    await expect(page.getByTestId("sdd-message")).toHaveText("Engine Bridge 無法連線", { timeout: 60_000 });
    await expect(page.getByTestId("sdd-status")).toHaveAttribute("data-available", "false");
    bridge = await startBridge({ port: P_SDD, root: path.join(BRIDGES, "b18082"), instance: "e2e-sdd", sddRoot: FIXTURE_ROOT });
    await expect(page.getByTestId("sdd-status")).toHaveAttribute("data-available", "true", { timeout: 60_000 });
    await expect(page.getByTestId("sdd-version")).toHaveText("AISDLC_SDD_v9.99");
    console.log("[w7-sdd] 列 7：Bridge 18082 結束 → 200／bridge_unreachable／卡片「Engine Bridge 無法連線」；重啟後下一輪復原為可用");
    expect(errors.filter((e) => !/Failed to load|ERR_/.test(e))).toEqual([]);
  });

  test("列 8｜SDD 目錄無效（SDD_ROOT 指向不存在的目錄）：/engines/sdd 為 sdd_unavailable；Bridge 的 /health/deep 仍 200、checks.sdd＝{ok:false}、頂層沒有 reason；/health 200；卡片顯示找不到目錄", async ({
    page,
    request,
  }) => {
    test.setTimeout(300_000);
    const none = await startBridge({ port: P_NONE, root: path.join(BRIDGES, "b18083"), instance: "e2e-sdd-none", sddRoot: NONE_ROOT });
    try {
      await setSddUrl(request, P_NONE);
      const d = await status(request);
      expect({ available: d.available, reason: d.reason, version: d.version, projects: d.projects, fsm: d.fsm }).toEqual({
        available: false,
        reason: "sdd_unavailable",
        version: null,
        projects: [],
        fsm: null,
      });
      const h = await deep(P_NONE);
      expect(h.status, "sdd 無效只當資訊：整體仍 200").toBe(200);
      expect(h.body.status).toBe("ok");
      expect(h.body.checks.sdd).toMatchObject({ ok: false, latest: null });
      expect(String(h.body.checks.sdd.reason), "reason 說明目錄無效").toContain("SDD_ROOT 不是目錄");
      expect(h.body.reason, "頂層沒有 reason").toBeUndefined();
      expect((await fetch(`http://127.0.0.1:${P_NONE}/health`)).status).toBe(200);
      await openCard(page, request, project);
      await expect(page.getByTestId("sdd-message")).toHaveText("找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）", FIRST_LOAD);
      console.log(
        `[w7-sdd] 列 8：/engines/sdd＝${JSON.stringify({ available: d.available, reason: d.reason })}；${P_NONE} 的 /health/deep＝${h.status} checks.sdd＝${JSON.stringify(h.body.checks.sdd)}`,
      );
    } finally {
      await setSddUrl(request, P_SDD);
      await none.stop();
    }
  });

  test("列 9｜乾淨 clone 等價（只有入口文件、沒有 build/reports/fsm）：available＝true、projects＝[]、fsm＝null、reason＝null；卡片「尚無 FSM 狀態檔」；/health/deep 200、checks.sdd＝{ok:true, latest:AISDLC_SDD_v9.98}", async ({
    page,
    request,
  }) => {
    test.setTimeout(300_000);
    const fresh = await startBridge({ port: P_FRESH, root: path.join(BRIDGES, "b18084"), instance: "e2e-sdd-fresh", sddRoot: FRESH_ROOT });
    try {
      await setSddUrl(request, P_FRESH);
      const d = await status(request);
      expect({ available: d.available, reason: d.reason ?? null, projects: d.projects, fsm: d.fsm }).toEqual({ available: true, reason: null, projects: [], fsm: null });
      expect(d.version?.latest).toBe("AISDLC_SDD_v9.98");
      const h = await deep(P_FRESH);
      expect(h.status).toBe(200);
      expect(h.body.checks.sdd).toMatchObject({ ok: true, latest: "AISDLC_SDD_v9.98" });
      await openCard(page, request, project);
      await expect(page.getByTestId("sdd-empty")).toHaveText("尚無 FSM 狀態檔（SDD runtime 執行後才會產生）", FIRST_LOAD);
      console.log(
        `[w7-sdd] 列 9：18084 的 /engines/sdd＝available ${d.available}、projects ${d.projects.length}；/health/deep checks.sdd＝${JSON.stringify(h.body.checks.sdd)}；卡片「尚無 FSM 狀態檔」（Docker 全棧的另一半見 QA 報告）`,
      );
    } finally {
      await setSddUrl(request, P_SDD);
      await fresh.stop();
    }
  });

  test("列 11（後半）｜只讀：第 6～9 列之後夾具目錄與乾淨 clone 目錄沒有被 Bridge 或 console-api 動過（相對第 6 列由測試自己改完檔之後的快照）", async () => {
    // 第 6 列的最後一步把 alpha 還原成 alphaDoc()；其餘檔案內容從未被測試以外的任何東西寫過。以檔案內容逐一比對初值。
    expect(await yamlLoad<FsmDoc>(ALPHA)).toEqual(alpha0);
    expect(await yamlLoad<FsmDoc>(path.join(FSM_DIR, "FSM-STATE-e2e-bravo.yaml"))).toEqual(bravo0);
    expect(existsSync(path.join(FRESH_ROOT, "AISDLC_SDD_v9.98", "build")), "乾淨 clone 目錄沒有被建出 build/").toBe(false);
    expect(existsSync(NONE_ROOT), "不存在的目錄沒有被建出來").toBe(false);
    const snap1 = dirSnapshot(VERSION_DIR);
    await new Promise((r) => setTimeout(r, 1500));
    expect(dirSnapshot(VERSION_DIR), "靜止時快照穩定").toEqual(snap1);
  });

  test("列 12｜真實 repo 根（選跑：AISDLC_SDD/<LATEST>/build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml 存在才跑）：projects 含 AISDLC_SDD；fsm 與該檔逐欄一致；畫面一致", async ({ page, request }) => {
    test.skip(!existsSync(REAL_FSM), `未跑：檔不存在（${REAL_FSM}）；該檔被 git 忽略，乾淨 clone 與 CI 沒有`);
    await setSddUrl(request, null); // 還原預設：Bridge 預設指向 repo 的 AISDLC_SDD（共用的 18081）
    const list = await status(request);
    expect(list.available, JSON.stringify(list).slice(0, 300)).toBe(true);
    expect(
      list.projects.map((p) => p.project),
      "只斷言包含（同目錄可能有 test-<數字> 殘留檔）",
    ).toContain("AISDLC_SDD");
    const real = (await yamlLoad<FsmDoc>(REAL_FSM)).fsm_state as Json & { retry_history: Record<string, { history: Json[] }> };
    const f = (await status(request, "?project=AISDLC_SDD")).fsm!;
    const hpEntered = (real.human_pending_tracking as Json | undefined)?.entered_at ?? null;
    const historyCount = Object.values(real.retry_history).reduce((n, g) => n + (Array.isArray(g.history) ? g.history.length : 0), 0);
    expect({
      currentState: f.currentState,
      currentSprint: f.currentSprint,
      updatedAt: f.updatedAt,
      sessionId: f.sessionId,
      humanPendingCount: f.humanPending.count,
      retryCount: f.retryHistory.count,
      decisionTrace: f.decisionTrace,
    }).toEqual({
      currentState: real.current_state,
      currentSprint: real.current_sprint,
      updatedAt: real.updated_at,
      sessionId: real.session_id,
      humanPendingCount: hpEntered ? 1 : 0,
      retryCount: historyCount,
      decisionTrace: (real.decision_trace as Json[]).slice(-5),
    });
    await openCard(page, request, project);
    await page.getByTestId("sdd-project-select").selectOption("AISDLC_SDD");
    await expect(page.getByTestId("sdd-state")).toHaveText(String(real.current_state), FIRST_LOAD);
    await expect(page.getByTestId("sdd-sprint")).toHaveText(`Sprint ${real.current_sprint}`);
    await expect(page.getByTestId("sdd-updated")).toHaveText(localTime(String(real.updated_at)));
    console.log(
      `[w7-sdd] 列 12：真實檔 FSM-STATE-AISDLC_SDD.yaml ↔ API ↔ 畫面一致：${f.currentState}／Sprint ${f.currentSprint}／${f.updatedAt}／待人工 ${f.humanPending.count}／重試 ${f.retryHistory.count}／清單含 AISDLC_SDD 與另 ${list.projects.length - 1} 個專案`,
    );
    await setSddUrl(request, P_SDD);
  });
});
