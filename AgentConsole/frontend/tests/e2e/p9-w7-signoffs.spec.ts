import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

import { API_URL, RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import { E2E_ROOT, FakeLlm, NEEDS_BRIDGE, bootstrapSettings, brd, call, createFixture, dataOf, ensureQuota, poll, signIn, type Fixture, type Json } from "./realBackend";
import { PG_CONTAINER, psql } from "./w5";
import { MOCK_CLAUDE, startBridge } from "./w7";

/**
 * W7 複驗：契約 v1.4 E2E-16（D-17、D-18、D-19；API-SGN-05、API-AUTH-03、API-NTF-01、US-M-10、UI-KPI-08）。
 *  列 1 探測預設值、列 2 探測打深度探針（503 計為失敗、sdd 無效不拖累探測；另起 Bridge 18085／18083）、
 *  列 3～4 待審批清單與計數同源（四種草案各一＋干擾列）、列 5 儀表板卡與簽核後同步（I-05 的三種漏列草案都造出來）、列 6 通知鈴連結、
 *  列 7～8 refresh 輪替與登出撤銷、列 9 前端登出流程。列 10（Redis 降級）只在 Docker 全棧：p9-w7-docker.stack.ts。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const nm = (base: string) => `${base} ${RUN}`;
const BRIDGES = path.join(E2E_ROOT, "w7-bridges");
const IMPACT_NOTE_C5 = "Bridge 健康探測路徑（Agent 可用率、頂列連線燈）；預設 /health/deep：Bridge 行程可達但引擎自檢未通過（503）也算失敗，改回 /health 只檢查行程是否存活";

type Counts = { projects: number; goals: number; tasks: number; imports: number; total: number };
type Item = { kind: "PROJECT" | "GOAL" | "TASK" | "IMPORT"; id: string; projectId: string | null; projectName: string | null; parentId: string | null; title: string; createdAt: string };
type Pending = { counts: Counts; items: Item[] };
type Summary = { pendingSignoffs: number; pendingReviews: number; unacknowledgedAlerts: number; bridgeConnected: boolean; bridgeCheckedAt?: string };

const pending = async (request: APIRequestContext, query = "", role: "viewer" | "operator" | "admin" = "viewer") => call(request, role, "GET", `/api/v1/signoffs/pending${query}`);
const pendingData = async (request: APIRequestContext, query = ""): Promise<Pending> => {
  const r = await pending(request, query);
  expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(200);
  return dataOf<Pending>(r);
};
const summaryOf = async (request: APIRequestContext): Promise<Summary> => dataOf<Summary>(await call(request, "viewer", "GET", "/api/v1/notifications/summary"));
const availability = async (request: APIRequestContext, projectId: string): Promise<number> =>
  dataOf<{ agentAvailability: { value: number } }>(await call(request, "viewer", "GET", `/api/v1/monitor/projects/${projectId}/metrics`)).agentAvailability.value;
const setSetting = async (request: APIRequestContext, category: string, key: string, value: string | null) => {
  const r = value === null ? await call(request, "admin", "POST", `/api/v1/settings/${category}/${key}/reset`) : await call(request, "admin", "PUT", `/api/v1/settings/${category}/${key}`, { value });
  expect(r.status, `${category}.${key}=${value} → ${JSON.stringify(r.json).slice(0, 300)}`).toBe(200);
};

/** 以 id 簽核任何一種待審批草案（API）。 */
async function signoffById(request: APIRequestContext, it: Item): Promise<void> {
  const base = it.kind === "PROJECT" ? "projects" : it.kind === "GOAL" ? "goals" : it.kind === "TASK" ? "tasks" : "import";
  const r = await call(request, "operator", "POST", `/api/v1/${base}/${it.id}/signoff`, { approver: "w7-qa" });
  expect([200, 409], `${it.kind} ${it.id} signoff → ${JSON.stringify(r.json).slice(0, 200)}`).toContain(r.status);
}

let llm: FakeLlm;

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);
  llm = new FakeLlm(`QA W7 待審批 ${RUN}`);
  await llm.listen();
});

test.afterAll(async ({ request }) => {
  await llm.close();
  await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
  await call(request, "admin", "POST", "/api/v1/settings/model/apiUrl/reset");
  for (const [category, key] of [
    ["autoclaude", "healthCheckPath"],
    ["autoclaude", "engineUrl"],
    ["sdd", "engineUrl"],
  ] as const)
    await call(request, "admin", "POST", `/api/v1/settings/${category}/${key}/reset`);
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 60);
  await ensureQuota(request, "viewer", 70);
});

test.describe("E2E-16 列 1～2：深度探針為探測預設（D-17；US-M-10、UI-KPI-08）", () => {
  test.setTimeout(420_000);

  test("列 1｜探測預設值：admin GET /settings/autoclaude 的 healthCheckPath.value 與 defaultValue 都是 /health/deep；impactNote 逐字等於附錄 C.5", async ({ request }) => {
    const rows = dataOf<Array<{ key: string; value: string; defaultValue: string; impactNote?: string | null }>>(await call(request, "admin", "GET", "/api/v1/settings/autoclaude"));
    const row = rows.find((r) => r.key === "healthCheckPath")!;
    expect(row.defaultValue).toBe("/health/deep");
    expect(row.value, "全新資料庫沒人動過").toBe("/health/deep");
    expect(row.impactNote, "逐字等於附錄 C.5").toBe(IMPACT_NOTE_C5);
    console.log(`[w7-signoffs] 列 1：healthCheckPath value＝${row.value}、defaultValue＝${row.defaultValue}、impactNote 與附錄 C.5 逐字相同`);
  });

  test("列 2｜探測打深度探針：503（git 不在 PATH）計為失敗；改打 /health 同一個 Bridge 變成功；SDD 目錄無效的 Bridge 不拖累探測，只讓 SDD 卡不可用", async ({ request }) => {
    const f = await createFixture(request, { name: nm("QA E2E-16 列2"), kind: "A", level: 4 });
    const noGit = await startBridge({ port: 18085, root: path.join(BRIDGES, "b18085"), instance: "e2e-nogit", emptyPath: true });
    const noSdd = await startBridge({ port: 18083, root: path.join(BRIDGES, "b18083"), instance: "e2e-sdd-none", sddRoot: path.join(E2E_ROOT, "no-such-dir") });
    const connected = (want: boolean, what: string, since = 0) =>
      poll(
        () => summaryOf(request),
        (s) => s.bridgeConnected === want && (!since || Date.parse(s.bridgeCheckedAt ?? "") > since),
        what,
        90_000,
        3_000,
      );
    try {
      // 直連：18085 的淺層 /health 200、深度 /health/deep 503、checks.git.ok＝false、頂層 reason 以 git: 開頭
      expect((await fetch("http://127.0.0.1:18085/health")).status).toBe(200);
      const deepRes = await fetch("http://127.0.0.1:18085/health/deep");
      const deepBody = (await deepRes.json()) as { status: string; reason?: string; checks: { git: { ok: boolean } } };
      expect(deepRes.status).toBe(503);
      expect(deepBody.checks.git.ok).toBe(false);
      expect(deepBody.reason ?? "", "頂層 reason 以 git: 開頭").toMatch(/^git:/);

      // ① 探測環指向 18085（預設路徑 /health/deep）：失敗樣本計入
      const base = await availability(request, f.projectId);
      await setSetting(request, "autoclaude", "engineUrl", "http://127.0.0.1:18085");
      const down = await connected(false, "探測 18085（/health/deep 回 503）→ bridgeConnected＝false");
      const metrics1 = await availability(request, f.projectId);
      expect(metrics1, `agentAvailability 因失敗樣本低於 100（改前 ${base}）`).toBeLessThan(100);
      // ② 對照：路徑暫設 /health，同一個 Bridge 被判成功
      const t2 = Date.now();
      await setSetting(request, "autoclaude", "healthCheckPath", "/health");
      const up = await connected(true, "改打 /health 後同一個 Bridge 被判成功（差別來自探測路徑）", t2);
      // ③ SDD 目錄無效的 18083：探測環（預設路徑還原）判成功、可用率不因它下降；SDD 卡不可用
      await setSetting(request, "autoclaude", "engineUrl", "http://127.0.0.1:18083"); // 先換位址（此時路徑仍是 /health，成功），再把路徑還原成深度探針
      await setSetting(request, "autoclaude", "healthCheckPath", "/health/deep");
      await setSetting(request, "sdd", "engineUrl", "http://127.0.0.1:18083");
      const t3 = Date.now();
      const sddOk = await connected(true, "18083（sdd 無效、其餘健康）以 /health/deep 探測仍被判成功", t3);
      const metrics3 = await availability(request, f.projectId);
      expect(metrics3, "新樣本全是成功：可用率不會比 ① 低（不因 sdd 失敗而下降）").toBeGreaterThanOrEqual(metrics1);
      const sdd = dataOf<{ available: boolean; reason: string | null }>(await call(request, "viewer", "GET", "/api/v1/engines/sdd"));
      expect({ available: sdd.available, reason: sdd.reason }, "SDD 卡不可用，但只影響 SDD 卡").toEqual({ available: false, reason: "sdd_unavailable" });
      const deepNone = (await (await fetch("http://127.0.0.1:18083/health/deep")).json()) as { status: string; checks: { sdd: { ok: boolean } } };
      expect({ status: deepNone.status, sddOk: deepNone.checks.sdd.ok }).toEqual({ status: "ok", sddOk: false });
      console.log(
        `[w7-signoffs] 列 2：①18085（git 不在 PATH）bridgeConnected＝${down.bridgeConnected}、agentAvailability ${base}→${metrics1}；②改 /health 後 bridgeConnected＝${up.bridgeConnected}；③18083（SDD_ROOT 無效）bridgeConnected＝${sddOk.bridgeConnected}、agentAvailability＝${metrics3}、/engines/sdd＝available ${sdd.available}／${sdd.reason}`,
      );
    } finally {
      for (const [category, key] of [
        ["autoclaude", "engineUrl"],
        ["autoclaude", "healthCheckPath"],
        ["sdd", "engineUrl"],
      ] as const)
        await setSetting(request, category, key, null);
      await noGit.stop();
      await noSdd.stop();
    }
    await poll(
      () => summaryOf(request),
      (s) => s.bridgeConnected,
      "三個設定還原後共用 Bridge 回到已連線",
      90_000,
      3_000,
    );
  });
});

test.describe("E2E-16 列 3～6：待審批清單與計數同源、儀表板卡、通知鈴（D-18；API-SGN-05、API-NTF-01）", () => {
  test.setTimeout(420_000);
  const mine: { project?: Item; goal?: Item; task?: Item; importA?: Item; importB?: Item } = {};
  let base: Pending;
  let titles: { project: string; goal: string; task: string; importA: string };

  test("列 3｜四種待簽草案各一＋干擾列：counts 各項相對基線恰 +1、total＝summary.pendingSignoffs、createdAt 升冪、各 kind 欄位逐一正確（IMPORT 的 projectId／projectName／parentId 為 null）；干擾列都不出現", async ({
    request,
  }) => {
    expect(PG_CONTAINER, "需要 E2E_PG_CONTAINER 才能造『專案軟刪、其目標任務未軟刪』的干擾列").toBeTruthy();
    base = await pendingData(request, "?limit=200");
    titles = { project: nm("QA16 草案專案"), goal: nm("QA16 草案目標"), task: nm("QA16 草案任務"), importA: `w7-qa-${RUN}.md` };
    const dir = path.join(E2E_ROOT, "projects", `w7_pending_${RUN}`);
    mkdirSync(dir, { recursive: true });

    // 四種待簽草案
    const pr = await call(request, "operator", "POST", "/api/v1/projects", { name: titles.project, executionPath: dir, passCriteria: "x", description: "", autonomyLevel: 3, draft: true });
    expect(pr.status, JSON.stringify(pr.json)).toBe(201);
    const signed = await createFixture(request, { name: nm("QA16 已簽專案（干擾列）"), kind: "A", level: 4 }); // 已簽專案、其底下全已簽
    const gr = await call(request, "operator", "POST", `/api/v1/projects/${signed.projectId}/goals`, { name: titles.goal, passCriteria: "x", description: "", dependsOn: [], draft: true });
    expect(gr.status, JSON.stringify(gr.json)).toBe(201);
    const tr = await call(request, "operator", "POST", `/api/v1/goals/${signed.goalIds[0]}/tasks`, {
      name: titles.task,
      description: "請輸出 [T9_DONE]",
      passCriteria: "輸出含 [T9_DONE]",
      expectedOutputRegex: "\\[T9_DONE\\]",
      maxRetries: 1,
      draft: true,
    });
    expect(tr.status, JSON.stringify(tr.json)).toBe(201);
    await call(request, "admin", "PUT", "/api/v1/settings/model/apiUrl", { value: llm.endpoint });
    await call(request, "admin", "PUT", "/api/v1/settings/model/apiKey", { value: "e2e-fake-key", confirm: true });
    const parse = async (fileName: string | null): Promise<string> => {
      const t = await call(request, "operator", "POST", "/api/v1/import/text", { content: brd(), ...(fileName ? { sourceFileName: fileName } : {}), sourceType: "MARKDOWN" });
      expect(t.status, JSON.stringify(t.json)).toBe(201);
      const id = dataOf<{ id: string }>(t).id;
      const p = await call(request, "operator", "POST", `/api/v1/import/${id}/parse`, { autonomyLevel: 3, executionPath: dir, additionalPrompt: "" });
      expect(p.status, `parse → ${JSON.stringify(p.json).slice(0, 300)}`).toBe(200);
      return id;
    };
    const importA = await parse(titles.importA);
    const importB = await parse(null); // 貼上文字（沒有檔名）
    // 干擾列：UPLOADED（只上傳、沒解析）、REJECTED（解析後放棄）、軟刪專案（其目標任務未軟刪）
    const up = await call(request, "operator", "POST", "/api/v1/import/text", { content: brd(), sourceFileName: `w7-uploaded-${RUN}.md`, sourceType: "MARKDOWN" });
    expect(up.status).toBe(201);
    const rej = await parse(`w7-rejected-${RUN}.md`);
    expect((await call(request, "operator", "POST", `/api/v1/import/${rej}/reject`)).status).toBe(200);
    const ghost: Fixture = await createFixture(request, { name: nm("QA16 軟刪專案（干擾列）"), kind: "A", level: 4, draft: true });
    await psql(`update console.projects set is_deleted = true, deleted_at = now() where id = '${ghost.projectId}'`); // 真正的軟刪旗標是 is_deleted（deleted_at 只記時間）；目標與任務刻意不動：專案軟刪、其目標任務未軟刪

    const after = await pendingData(request, "?limit=200");
    const delta = {
      projects: after.counts.projects - base.counts.projects,
      goals: after.counts.goals - base.counts.goals,
      tasks: after.counts.tasks - base.counts.tasks,
      imports: after.counts.imports - base.counts.imports,
      total: after.counts.total - base.counts.total,
    };
    expect(delta, "四種各 +1（匯入 +2＝檔名一筆、貼上文字一筆）；已簽專案、軟刪專案的草案目標與任務、UPLOADED、REJECTED 都沒計入").toEqual({ projects: 1, goals: 1, tasks: 1, imports: 2, total: 5 });
    const summary = await summaryOf(request);
    expect(after.counts.total, "counts.total＝summary.pendingSignoffs（同判準、同數字）").toBe(summary.pendingSignoffs);
    expect(after.counts.total).toBe(after.counts.projects + after.counts.goals + after.counts.tasks + after.counts.imports);
    // 排序與長度
    expect(after.items.length, "limit=200").toBe(Math.min(after.counts.total, 200));
    const stamps = after.items.map((i) => Date.parse(i.createdAt));
    expect(stamps, "createdAt 升冪").toEqual([...stamps].sort((a, b) => a - b));
    const def = await pendingData(request);
    expect(def.items.length, "預設 limit 50：items＝min(total, 50)").toBe(Math.min(def.counts.total, 50));
    expect(def.counts, "limit 只截斷 items、不影響 counts").toEqual(after.counts);
    // 逐項欄位
    const byTitle = (title: string) => after.items.find((i) => i.title === title);
    mine.project = byTitle(titles.project);
    mine.goal = byTitle(titles.goal);
    mine.task = byTitle(titles.task);
    mine.importA = byTitle(titles.importA);
    mine.importB = after.items.find((i) => i.kind === "IMPORT" && i.title === "貼上文字" && i.id === importB);
    const projectId = dataOf<{ id: string }>(pr).id;
    expect(mine.project).toMatchObject({ kind: "PROJECT", id: projectId, projectId, projectName: titles.project, parentId: null });
    expect(mine.goal).toMatchObject({ kind: "GOAL", id: dataOf<{ id: string }>(gr).id, projectId: signed.projectId, projectName: signed.name, parentId: signed.projectId });
    expect(mine.task).toMatchObject({ kind: "TASK", id: dataOf<{ id: string }>(tr).id, projectId: signed.projectId, projectName: signed.name, parentId: signed.goalIds[0] });
    expect(mine.importA).toMatchObject({ kind: "IMPORT", id: importA, projectId: null, projectName: null, parentId: null, title: titles.importA });
    expect(mine.importB, "貼上文字的匯入記錄 title＝『貼上文字』").toMatchObject({ kind: "IMPORT", id: importB, projectId: null, projectName: null, parentId: null, title: "貼上文字" });
    for (const decoy of [signed.projectId, ghost.projectId, ghost.goalIds[0], ghost.taskIds[0], dataOf<{ id: string }>(up).id, rej])
      expect(
        after.items.map((i) => i.id),
        `干擾列 ${decoy} 不出現`,
      ).not.toContain(decoy);
    console.log(
      `[w7-signoffs] 列 3：基線 counts＝${JSON.stringify(base.counts)}；造出後 counts＝${JSON.stringify(after.counts)}（delta ${JSON.stringify(delta)}）；summary.pendingSignoffs＝${summary.pendingSignoffs}；6 個干擾列（已簽專案、軟刪專案與其目標及任務、UPLOADED 與 REJECTED 的匯入記錄）皆未出現`,
    );
  });

  test("列 4｜limit 與權限：limit=2 回最早的兩筆且 counts 不變；0、201、abc → 400（errors[0].field＝limit）；未認證 401；viewer 200", async ({ request }) => {
    const all = await pendingData(request, "?limit=200");
    const two = await pendingData(request, "?limit=2");
    expect(two.items.map((i) => i.id)).toEqual(all.items.slice(0, 2).map((i) => i.id));
    expect(two.counts).toEqual(all.counts);
    for (const bad of ["0", "201", "abc"]) {
      const r = await pending(request, `?limit=${bad}`);
      expect(r.status, `limit=${bad}`).toBe(400);
      expect((r.json.errors as Array<{ field: string }>)[0].field).toBe("limit");
    }
    expect((await request.get(`${API_URL}/api/v1/signoffs/pending`, { failOnStatusCode: false })).status()).toBe(401);
    expect((await pending(request, "", "viewer")).status).toBe(200);
  });

  test("列 5｜儀表板「待人工審批」卡：徽章＝KPI「待審批草案數」＝counts.total、項目數＝min(total, 50)、連結依 kind；依序審批 PROJECT／GOAL／TASK／IMPORT 各一筆，卡片、徽章、KPI 同步減 1（不整頁重載）", async ({
    page,
    request,
  }) => {
    const errors = collectConsoleErrors(page);
    // 若基線太多、造出的草案掉到前 50 筆之外（最早的先處理），先把比我的更早的草案由 API 簽掉，讓畫面看得到我的四筆
    let all = await pendingData(request, "?limit=200");
    const mineIds = new Set(Object.values(mine).map((m) => m?.id));
    for (const it of all.items) {
      if (all.counts.total <= 46) break;
      if (mineIds.has(it.id)) continue;
      await signoffById(request, it);
      all = await pendingData(request, "?limit=200");
    }
    await signIn(page, request, "operator");
    await page.goto("/");
    const card = page.getByTestId("pending-signoff-card");
    await expect(card).toBeVisible(FIRST_LOAD);
    const total0 = all.counts.total;
    await expect(page.getByTestId("pending-count")).toHaveText(String(total0), FIRST_LOAD);
    await expect(page.getByTestId("kpi-drafts")).toHaveText(String(total0));
    await expect(page.getByTestId("pending-item")).toHaveCount(Math.min(total0, 50));
    await snap(page, "p9-w7-pending-card.png", { focus: card });
    // 連結落點（契約 §4.5 G-10）
    const link = (it: Item) =>
      page
        .getByTestId("pending-item")
        .filter({ has: page.getByRole("link", { name: it.title, exact: true }) })
        .getByRole("link", { name: it.title, exact: true });
    await expect(link(mine.project!)).toHaveAttribute("href", `/projects/${mine.project!.id}`);
    await expect(link(mine.goal!)).toHaveAttribute("href", `/projects/${mine.goal!.projectId}/goals/${mine.goal!.id}`);
    await expect(link(mine.task!)).toHaveAttribute("href", `/projects/${mine.task!.projectId}/goals/${mine.task!.parentId}/tasks/${mine.task!.id}`);
    await expect(link(mine.importA!)).toHaveAttribute("href", "/import");
    // 依序審批四種（每簽一筆，卡片項目數、徽章、KPI 同步減 1）
    await page.evaluate(() => ((window as unknown as { __w7Marker: string }).__w7Marker = "alive"));
    let n = total0;
    for (const it of [mine.project!, mine.goal!, mine.task!, mine.importA!]) {
      await page.getByRole("button", { name: `審批：${it.title}`, exact: true }).click();
      await page.getByRole("button", { name: "確認 signoff" }).click();
      n -= 1;
      await expect(page.getByTestId("pending-count")).toHaveText(String(n), FIRST_LOAD);
      await expect(page.getByTestId("kpi-drafts")).toHaveText(String(n), FIRST_LOAD);
      await expect(page.getByTestId("pending-item")).toHaveCount(Math.min(n, 50));
      await expect(page.getByRole("button", { name: `審批：${it.title}`, exact: true }), `${it.kind} 已從清單消失`).toHaveCount(0);
    }
    expect(await page.evaluate(() => (window as unknown as { __w7Marker?: string }).__w7Marker), "沒有整頁重載").toBe("alive");
    const after = await pendingData(request, "?limit=200");
    expect(after.counts.total, "後端的 counts.total 同步減 4").toBe(total0 - 4);
    expect(after.items.map((i) => i.id)).not.toContain(mine.project!.id);
    console.log(`[w7-signoffs] 列 5：儀表板徽章＝KPI＝API total＝${total0}；審批 PROJECT、GOAL、TASK、IMPORT 各一筆後 ${total0}→${n}，卡片項目數、徽章、KPI 同步；連結落點符合 G-10`);
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("列 6｜通知鈴連結：「待簽核草案」恆為 /#pending-signoff；「待審核項目」「未確認告警」在專案頁→該專案的 /execute、/monitor，在儀表板→/projects（已知限制 G-G4）", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA E2E-16 列6"), kind: "A", level: 4 });
    await signIn(page, request, "operator");
    await page.goto("/");
    await expect(page.getByTestId("bell-trigger")).toBeVisible(FIRST_LOAD);
    await page.getByTestId("bell-trigger").click();
    await expect(page.getByTestId("notification-panel")).toBeVisible();
    await expect(page.getByTestId("notification-signoffs")).toHaveAttribute("href", "/#pending-signoff");
    await expect(page.getByTestId("notification-reviews")).toHaveAttribute("href", "/projects");
    await expect(page.getByTestId("notification-alerts")).toHaveAttribute("href", "/projects");
    await expect(page.getByTestId("notification-scope-note")).toContainText("全部專案的合計");
    await page.keyboard.press("Escape");
    await page.goto(`/projects/${f.projectId}`);
    await expect(page.getByRole("heading", { name: f.name })).toBeVisible(FIRST_LOAD);
    await page.getByTestId("bell-trigger").click();
    await expect(page.getByTestId("notification-signoffs")).toHaveAttribute("href", "/#pending-signoff");
    await expect(page.getByTestId("notification-reviews")).toHaveAttribute("href", `/projects/${f.projectId}/execute`);
    await expect(page.getByTestId("notification-alerts")).toHaveAttribute("href", `/projects/${f.projectId}/monitor`);
    console.log("[w7-signoffs] 列 6：儀表板 → signoffs＝/#pending-signoff、reviews／alerts＝/projects；專案頁 → reviews＝…/execute、alerts＝…/monitor");
  });
});

test.describe("E2E-16 列 7～9：refresh token 輪替與登出撤銷（D-19；API-AUTH-03）", () => {
  test.setTimeout(240_000);
  type Tokens = { accessToken: string; refreshToken: string };
  const PW = { operator: ["Operator", "Dev2026"].join("#") };
  const login = async (request: APIRequestContext): Promise<Tokens> => {
    const r = await request.post(`${API_URL}/api/v1/auth/login`, { data: { username: "operator", password: PW.operator } });
    expect(r.status()).toBe(200);
    return ((await r.json()) as { data: Tokens }).data;
  };
  const refresh = async (request: APIRequestContext, refreshToken: string) => {
    const r = await request.post(`${API_URL}/api/v1/auth/refresh`, { data: { refreshToken }, failOnStatusCode: false });
    return { status: r.status(), json: (await r.json().catch(() => ({}))) as Json };
  };

  test("列 7｜refresh 輪替：RT1→RT2；再用 RT1 → 401 INVALID_REFRESH_TOKEN；RT2 仍有效換出 RT3；RT1 當 Bearer 仍是 401 TOKEN_INVALID", async ({ request }) => {
    const t1 = await login(request);
    const s2 = await refresh(request, t1.refreshToken);
    expect(s2.status).toBe(200);
    const rt2 = (s2.json.data as Tokens).refreshToken;
    expect(rt2).not.toBe(t1.refreshToken);
    const replay = await refresh(request, t1.refreshToken);
    expect(replay.status).toBe(401);
    expect(replay.json.reason).toBe("INVALID_REFRESH_TOKEN");
    const s4 = await refresh(request, rt2);
    expect(s4.status, "RT2 有效").toBe(200);
    expect((s4.json.data as Tokens).refreshToken).not.toBe(rt2);
    const asBearer = await request.get(`${API_URL}/api/v1/projects?size=1`, { headers: { Authorization: `Bearer ${t1.refreshToken}` }, failOnStatusCode: false });
    expect(asBearer.status()).toBe(401);
    expect(((await asBearer.json()) as Json).reason, "refresh token 本來就不能當 access 用").toBe("TOKEN_INVALID");
    console.log("[w7-signoffs] 列 7：login→refresh(RT1)=200→refresh(RT1)=401 INVALID_REFRESH_TOKEN→refresh(RT2)=200；RT1 當 Bearer=401 TOKEN_INVALID");
  });

  test("列 8｜登出撤銷：logout 204、之後 refresh 401；垃圾字串／已撤銷／access token 皆 204；缺 refreshToken 400；不帶 Authorization 也能呼叫", async ({ request }) => {
    const t = await login(request);
    const out = await request.post(`${API_URL}/api/v1/auth/logout`, { data: { refreshToken: t.refreshToken }, failOnStatusCode: false });
    expect(out.status()).toBe(204);
    const after = await refresh(request, t.refreshToken);
    expect(after.status).toBe(401);
    expect(after.json.reason).toBe("INVALID_REFRESH_TOKEN");
    const post = (body: unknown) => request.post(`${API_URL}/api/v1/auth/logout`, { data: body, failOnStatusCode: false });
    expect((await post({ refreshToken: "垃圾字串-not-a-jwt" })).status(), "垃圾字串").toBe(204);
    expect((await post({ refreshToken: t.refreshToken })).status(), "已撤銷的 RT 再登出一次").toBe(204);
    expect((await post({ refreshToken: t.accessToken })).status(), "access token 當 refreshToken").toBe(204);
    const missing = await post({});
    expect(missing.status(), "缺 refreshToken").toBe(400);
    expect(((await missing.json()) as { errors: Array<{ field: string }> }).errors[0].field).toBe("refreshToken");
    const blank = await post({ refreshToken: "   " });
    expect(blank.status(), "空白 refreshToken").toBe(400);
    console.log("[w7-signoffs] 列 8：logout=204→refresh=401 INVALID_REFRESH_TOKEN；垃圾／已撤銷／access token 皆 204；缺或空白 refreshToken=400（field=refreshToken）；皆未帶 Authorization");
  });

  test("列 9｜前端登出：按「登出」送出一個 POST /api/v1/auth/logout（body 帶 refreshToken）、導向 /login、session 清空；該 refresh token 之後換新 401；logout 請求被弄成失敗仍然登出", async ({
    page,
    request,
  }) => {
    const errors = collectConsoleErrors(page);
    await signIn(page, request, "operator");
    await page.goto("/");
    await expect(page.getByTestId("user-badge")).toBeVisible(FIRST_LOAD);
    const session1 = JSON.parse((await page.evaluate(() => window.sessionStorage.getItem("aisdlc.console.session"))) ?? "{}") as { refreshToken: string };
    expect(session1.refreshToken).toBeTruthy();
    const logoutReqs: Array<{ method: string; body: string | null }> = [];
    page.on("request", (req) => {
      if (req.url().endsWith("/api/v1/auth/logout")) logoutReqs.push({ method: req.method(), body: req.postData() });
    });
    await page.getByRole("button", { name: "登出" }).click();
    await expect(page).toHaveURL(/\/login/, FIRST_LOAD);
    expect(logoutReqs, "恰一個 logout 請求").toHaveLength(1);
    expect(logoutReqs[0].method).toBe("POST");
    expect(JSON.parse(logoutReqs[0].body ?? "{}")).toEqual({ refreshToken: session1.refreshToken });
    expect(await page.evaluate(() => window.sessionStorage.getItem("aisdlc.console.session")), "session 清空").toBeNull();
    expect((await refresh(request, session1.refreshToken)).status, "登出前記下的 refresh token 換新 → 401").toBe(401);
    // 第二次：把 logout 請求以網路攔截弄成失敗——前端不論成敗都導向 /login、清 session
    await signIn(page, request, "operator");
    await page.route("**/api/v1/auth/logout", (route) => route.abort("failed"));
    await page.goto("/");
    await expect(page.getByTestId("user-badge")).toBeVisible(FIRST_LOAD);
    const session2 = JSON.parse((await page.evaluate(() => window.sessionStorage.getItem("aisdlc.console.session"))) ?? "{}") as { refreshToken: string };
    await page.getByRole("button", { name: "登出" }).click();
    await expect(page).toHaveURL(/\/login/, FIRST_LOAD);
    expect(await page.evaluate(() => window.sessionStorage.getItem("aisdlc.console.session")), "logout 失敗也清 session").toBeNull();
    // logout 沒到後端，所以這個 refresh token 仍有效（撤銷只在 logout 抵達時發生）：這是契約「不阻擋本機登出」的代價
    const still = await refresh(request, session2.refreshToken);
    console.log(
      `[w7-signoffs] 列 9：登出送出 1 個 POST /auth/logout（body 只有 refreshToken）→ /login、session 清空、舊 RT 換新 401；logout 被攔截失敗時仍導向 /login 並清 session（該 RT 因 logout 沒到後端，換新 ${still.status}）`,
    );
    void errors;
  });
});
