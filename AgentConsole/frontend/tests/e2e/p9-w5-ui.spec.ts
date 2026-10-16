import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { API_URL, RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import { E2E_ROOT, FakeLlm, NEEDS_BRIDGE, bootstrapSettings, brd, call, createFixture, dataOf, ensureQuota, getRun, poll, signIn, waitRun, type Fixture, type Json, type RunView } from "./realBackend";
import { startOfWeekIso } from "./w5";

/**
 * W5 複驗（UI 面）——契約 v1.2 對真後端（e2e profile）＋真 Bridge＋aisdlc-mock-claude 的瀏覽器操作：
 *   C-3 專案列表「已刪除」與「復原」、C-8 執行中刪除的白話原因、C-9 手動重試的 toast、C-10 重開匯入記錄還原黃色提示與解析選項（路徑 C，需假 Brain）、
 *   C-11 執行頁的暫停中晶片、C-1 儀表板（改打 task-totals）的請求量與「本週完成」數字（DEF-AC-009 的複驗）。
 * API 面（task-totals 不變量、restore 錯誤路徑、PDF、跨批次告警…）在 p9-w5-api.spec.ts。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const MOCK_CLAUDE = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");
const FAKE_BRAIN = process.env.E2E_FAKE_BRAIN === "1";
const nm = (base: string) => `${base} ${RUN}`;
const toast = (page: Page, text: string | RegExp) => page.getByRole("status").filter({ hasText: text });

let llm: FakeLlm;

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);
  llm = new FakeLlm(`QA W5 UI ${RUN}`);
  await llm.listen();
});

test.afterAll(async ({ request }) => {
  await llm.close();
  await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
  await call(request, "admin", "POST", "/api/v1/settings/model/apiUrl/reset");
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 60);
  await ensureQuota(request, "viewer", 60);
});

async function startRun(request: Parameters<typeof ensureQuota>[0], f: Fixture, level: number): Promise<string> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: level, tokenBudget: 100000, scope: { mode: "ALL" } });
  expect(r.status, `execute ${f.name} → ${JSON.stringify(r.json).slice(0, 300)}`).toBe(201);
  return dataOf<{ id: string }>(r).id;
}

test.describe("W5 複驗（UI 面）", () => {
  test.setTimeout(300_000);

  test("C-3｜專案列表「已刪除」→「復原」：卡片顯示已刪除標籤與刪除時間、復原 toast 帶目標與任務數、回一般清單看得到；VIEWER 沒有已刪除鈕", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    const f = await createFixture(request, { name: nm("QA W5 UI 復原"), kind: "A", level: 4 }); // 2 個目標、3 個任務
    expect((await call(request, "operator", "DELETE", `/api/v1/projects/${f.projectId}`)).status).toBe(204);
    await signIn(page, request, "operator");
    await page.goto("/projects");
    await expect(page.getByRole("heading", { name: "專案管理" })).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("project-card").filter({ hasText: f.name }), "一般清單看不到已刪除的專案").toHaveCount(0);

    await page.getByTestId("deleted-filter").click();
    await expect(page.getByTestId("deleted-filter")).toHaveAttribute("aria-pressed", "true");
    const card = page.getByTestId("project-card").filter({ hasText: f.name });
    await expect(card).toHaveCount(1, FIRST_LOAD);
    await expect(card.getByTestId("deleted-tag")).toHaveText("已刪除");
    await expect(card.getByTestId("deleted-at")).toContainText("刪除於");
    await expect(card.getByRole("link"), "已刪除專案的詳情頁是 404：名稱不是連結").toHaveCount(0);
    await expect(page.getByTestId("deleted-hint")).toContainText("保留一段時間（預設 30 天）");
    await snap(page, "p9-restore-deleted-list.png");

    await card.getByTestId("project-restore").click();
    await expect(toast(page, `已復原專案「${f.name}」（2 個目標、3 個任務）`)).toBeVisible();
    await expect(card).toHaveCount(0); // 從已刪除清單消失
    await page.getByTestId("deleted-filter").click();
    await expect(page.getByTestId("deleted-filter")).toHaveAttribute("aria-pressed", "false");
    const back = page.getByTestId("project-card").filter({ hasText: f.name });
    await expect(back).toHaveCount(1, FIRST_LOAD);
    await expect(back).toContainText("目標 2");
    await expect(back).toContainText("任務 0 / 3");
    await snap(page, "p9-restore-restored.png");
    const detail = await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`);
    expect(detail.status, "復原後詳情頁可開").toBe(200);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);

    // VIEWER：沒有「已刪除」鈕（後端對 viewer 的 deleted=true 回 403，所以前端不送）
    const viewerPage = await page.context().newPage();
    await signIn(viewerPage, request, "viewer");
    const seenDeletedQuery: string[] = [];
    viewerPage.on("request", (r) => {
      if (r.url().includes("deleted=true")) seenDeletedQuery.push(r.url());
    });
    await viewerPage.goto("/projects");
    await expect(viewerPage.getByRole("heading", { name: "專案管理" })).toBeVisible(FIRST_LOAD);
    await expect(viewerPage.getByTestId("project-list")).toBeVisible(FIRST_LOAD);
    await expect(viewerPage.getByTestId("deleted-filter")).toHaveCount(0);
    expect(seenDeletedQuery).toEqual([]);
    await viewerPage.close();
  });

  test("C-8｜執行中刪除：PAUSED 批次時在目標頁刪除 → 對話框內顯示白話原因且不關閉；取消批次後同一操作成功", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA W5 UI 執行中刪除"), kind: "B", level: 1 });
    const runId = await startRun(request, f, 1);
    await waitRun(request, runId, ["PAUSED"], 90_000);
    await signIn(page, request, "operator");
    await page.goto(`/projects/${f.projectId}/goals/${f.goalIds[1]}`);
    await expect(page.getByTestId("goal-title")).toHaveText("核心", FIRST_LOAD);
    await page.getByRole("button", { name: "刪除目標" }).click();
    const dialog = page.getByRole("dialog", { name: "刪除目標" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "確認刪除" }).click();
    await expect(dialog).toContainText("專案目前有進行中的執行批次");
    await expect(dialog, "失敗時對話框不關閉").toBeVisible();
    await snap(page, "p9-delete-while-executing.png");
    // 取消批次（終態）後同一個對話框再按一次就刪得掉
    expect((await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`)).status).toBe(200);
    await waitRun(request, runId, ["CANCELLED"], 60_000);
    await dialog.getByRole("button", { name: "確認刪除" }).click();
    await expect(toast(page, "已刪除目標「核心」")).toBeVisible();
    await expect(page.getByTestId("project-title")).toHaveText(f.name);
  });

  test("C-9｜手動重試：ESCALATED 任務按「重試」→ toast「手動重試第 N 次（不計入自動重試上限 M）」，後端 retryCount 超過 maxRetries 也不擋", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA W5 UI 手動重試"), kind: "A", level: 4, failTasks: [1] }); // maxRetries=1
    const runId = await startRun(request, f, 4);
    await poll(
      () => getRun(request, runId),
      (r) => r.status === "FAILED" && (r.pendingReviews ?? []).length > 0,
      "批次 FAILED 且審核項已建立",
      90_000,
    );
    const t1 = f.taskIds[0];
    const before = dataOf<{ status: string; retryCount: number }>(await call(request, "viewer", "GET", `/api/v1/tasks/${t1}`));
    expect(before.status).toBe("ESCALATED");
    await signIn(page, request, "operator");
    await page.goto(`/projects/${f.projectId}/goals/${f.goalIds[0]}/tasks/${t1}`);
    await expect(page.getByTestId("task-title")).toHaveText("初始化", FIRST_LOAD);
    const retry = page.getByRole("button", { name: "重試" });
    await expect(retry).toBeEnabled();
    await retry.click();
    const expected = new RegExp(`已重新排入佇列：手動重試第 ${before.retryCount + 1} 次（不計入自動重試上限 1）`);
    await expect(toast(page, expected)).toBeVisible();
    await expect(page.getByTestId("metric-retries")).toHaveText(`${before.retryCount + 1} / 1`); // 已超過 maxRetries，介面如實顯示
    await snap(page, "p9-manual-retry-toast.png");
    expect(dataOf<{ retryCount: number; status: string }>(await call(request, "viewer", "GET", `/api/v1/tasks/${t1}`))).toMatchObject({ retryCount: before.retryCount + 1, status: "QUEUED" });
  });

  test("C-11｜執行頁：暫停中的批次出現「暫停中」晶片（bridgeStatus＝PAUSING，status 仍是 RUNNING）；到步驟邊界後晶片消失、顯示已暫停", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA W5 UI 暫停中晶片"), kind: "B", level: 4 });
    await signIn(page, request, "operator");
    // MutationObserver 記下「晶片曾經出現過」——PAUSING 只持續到下一個步驟邊界（不到 1 秒），輪詢式斷言可能剛好錯過
    await page.addInitScript(() => {
      (window as unknown as { __chipTexts: string[] }).__chipTexts = [];
      const scan = () => {
        for (const el of document.querySelectorAll('[data-testid="bridge-chip"]')) {
          const t = (el.textContent ?? "").trim();
          const seen = (window as unknown as { __chipTexts: string[] }).__chipTexts;
          if (t && !seen.includes(t)) seen.push(t);
        }
      };
      new MutationObserver(scan).observe(document, { subtree: true, childList: true, characterData: true, attributes: true });
    });
    await page.goto(`/projects/${f.projectId}/execute`);
    await expect(page.getByRole("heading", { name: `專案執行：${f.name}` })).toBeVisible(FIRST_LOAD);
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "RUNNING", { timeout: 30_000 });
    await page.getByTestId("control-pause").click();
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    const texts = await page.evaluate(() => (window as unknown as { __chipTexts: string[] }).__chipTexts);
    expect(
      texts.some((t) => t.includes("暫停中")),
      `執行期間出現過的晶片文字：${JSON.stringify(texts)}`,
    ).toBe(true);
    await expect(page.getByTestId("bridge-chip"), "PAUSED 之後沒有過渡態晶片").toHaveCount(0);
    expect((await call(request, "operator", "POST", `/api/v1/executions/${await runIdOf(request, f)}/cancel`)).status).toBe(200);
  });

  test("C-10｜重開匯入記錄（路徑 C）：GET /import/{id} 帶 warnings 與 parseOptions；UI 重開還原黃色提示；被有界閘拒絕的重新解析改寫 parseOptions 但保留 warnings；PUT result 後 warnings 以重算值覆寫", async ({
    page,
    request,
  }) => {
    test.skip(!FAKE_BRAIN, "需要假 Brain 版 Bridge（support/fake_brain_bridge.py）：設 E2E_FAKE_BRAIN=1（見 README〈真 Bridge specs〉）");
    // 路徑 C 只在 model.apiKey 非空時帶 minimax 覆寫（base_url＝model.apiUrl＝假伺服器，白名單內的 loopback）
    expect((await call(request, "admin", "PUT", "/api/v1/settings/model/apiUrl", { value: llm.endpoint })).status).toBe(200);
    expect((await call(request, "admin", "PUT", "/api/v1/settings/model/apiKey", { value: "sk-e2e-dummy", confirm: true })).status).toBe(200);
    const dir = path.join(E2E_ROOT, "projects", `imp-w5-${RUN}`);
    mkdirSync(dir, { recursive: true });
    const newRecord = async (content: string, sourceType: "PLAIN_TEXT" | "MARKDOWN" = "PLAIN_TEXT") =>
      dataOf<{ id: string }>(await call(request, "operator", "POST", "/api/v1/import/text", { content, sourceType, sourceFileName: `w5-${RUN}.txt` })).id;
    type Warn = { code: string; detail?: string; location?: string };
    type Detail = { status: string; warnings: Warn[]; parseOptions: Json | null; lastParseErrors?: unknown[]; parsedResult: { goals: Array<{ tasks: Array<Json> }> } & Json };
    const detailOf = async (id: string) => dataOf<Detail>(await call(request, "viewer", "GET", `/api/v1/import/${id}`));
    try {
      // 從未 parse：warnings 永遠出現（空陣列）、parseOptions 為 null
      const a = await newRecord("把使用者登入功能做完");
      const fresh = await detailOf(a);
      expect([fresh.warnings, fresh.parseOptions]).toEqual([[], null]);

      const opts1 = { executionPath: dir, autonomyLevel: 4, additionalPrompt: "QA 補充說明" };
      const parsed = await call(request, "operator", "POST", `/api/v1/import/${a}/parse`, opts1);
      expect(parsed.status, JSON.stringify(parsed.json).slice(0, 300)).toBe(200);
      const parseWarnings = (parsed.json.data as { warnings: Warn[] }).warnings;
      expect(parseWarnings.filter((w) => w.code === "passcriteria_placeholder")).toHaveLength(2);
      const reopened = await detailOf(a);
      expect(reopened.warnings, "重新 GET：warnings 與 parse 回應相同").toEqual(parseWarnings);
      expect(reopened.parseOptions, "parseOptions 等於 parse 請求").toMatchObject(opts1);
      // 列表不帶這兩者（契約 §1.1.9）
      const row = dataOf<{ content: Array<Json> }>(await call(request, "viewer", "GET", `/api/v1/import?q=${encodeURIComponent(`w5-${RUN}`)}&size=5`)).content.find((x) => x.id === a)!;
      expect(Object.keys(row)).not.toContain("warnings");
      expect(Object.keys(row)).not.toContain("parseOptions");

      // UI：用網址直接重開（沒有任何「本次操作」暫存）→ 黃色解析提示由記錄還原
      await signIn(page, request, "operator");
      await page.goto(`/import?id=${a}`);
      await expect(page.getByTestId("import-step2")).toBeVisible(FIRST_LOAD);
      await expect(page.getByTestId("parse-warning")).toHaveCount(2);
      await expect(page.getByTestId("parse-warning").first()).toContainText("通過標準是佔位字串");
      await snap(page, "p9-import-reopen-warnings.png", { tall: true });

      // 被有界閘拒絕的重新解析：parseOptions 改成這一次的請求、warnings 維持上一次成功的、仍列出閘錯誤。
      // 假 Brain 只看內容文字，所以拒絕情境改用路徑 B（長 Markdown＋假 OpenAI 伺服器）：補充說明帶 GATE_MAX 會讓假模型回 25 個步驟的樹
      const c = await newRecord(brd(), "MARKDOWN");
      const optsB1 = { executionPath: dir, autonomyLevel: 3, additionalPrompt: "QA 補充說明 B" };
      const parsedB = await call(request, "operator", "POST", `/api/v1/import/${c}/parse`, optsB1);
      expect(parsedB.status, JSON.stringify(parsedB.json).slice(0, 300)).toBe(200);
      expect((parsedB.json.data as { path: string }).path).toBe("LLM");
      const warningsB = (parsedB.json.data as { warnings: Warn[] }).warnings;
      const optsB2 = { executionPath: dir, autonomyLevel: 2, additionalPrompt: "GATE_MAX" };
      const rejected = await call(request, "operator", "POST", `/api/v1/import/${c}/parse`, optsB2);
      expect([rejected.status, rejected.json.reason]).toEqual([422, "解析結果未通過有界閘"]);
      const afterGate = await detailOf(c);
      expect(afterGate.parseOptions, "被拒的 parse 也記下該次請求").toMatchObject(optsB2);
      expect(afterGate.warnings, "warnings 不變（仍是上一次成功解析的）").toEqual(warningsB);
      expect((afterGate.lastParseErrors ?? []).length).toBeGreaterThan(0);
      // PUT result：warnings 以重算值覆寫——補齊兩個佔位通過標準後 warnings 清空
      const b = await newRecord("把使用者註冊功能做完");
      expect((await call(request, "operator", "POST", `/api/v1/import/${b}/parse`, opts1)).status).toBe(200);
      const tree = (await detailOf(b)).parsedResult as { goals: Array<{ tasks: Array<{ passCriteria: string }> }> };
      expect((await detailOf(b)).warnings).toHaveLength(2);
      tree.goals.forEach((g) => g.tasks.forEach((t, i) => (t.passCriteria = `輸出含 [S${i + 1}_DONE]`)));
      const edited = await call(request, "operator", "PUT", `/api/v1/import/${b}/result`, { parsedResult: tree });
      expect(edited.status, JSON.stringify(edited.json).slice(0, 300)).toBe(200);
      const afterEdit = await detailOf(b);
      expect(afterEdit.status).toBe("REVIEWING");
      expect(afterEdit.warnings, "補齊通過標準後 warnings 以重算值覆寫（清空）").toEqual([]);
      expect(afterEdit.parseOptions, "PUT result 不動 parseOptions").toMatchObject(opts1);
      for (const id of [a, b, c]) await call(request, "operator", "POST", `/api/v1/import/${id}/reject`);
    } finally {
      await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
    }
  });

  test("C-1／DEF-AC-009｜儀表板（資料庫 ≥31 個專案）：只打 task-totals、沒有任何 task-trend 扇出；穩態每分鐘請求數 ≤10（W4 實測 31）；「本週完成」＝task-totals 的 completed", async ({
    page,
    request,
  }) => {
    test.setTimeout(420_000);
    // 湊滿 31 個專案（W4 的扇出上限是前 30 個）：缺幾個補幾個（admin 建，不吃 operator 的額度）
    const total = async () => dataOf<{ totalElements: number }>(await call(request, "viewer", "GET", "/api/v1/projects?size=1")).totalElements;
    for (let have = await total(), i = 0; have < 31; have += 1, i += 1) {
      const dir = path.join(E2E_ROOT, "projects", `dash-${RUN}-${i}`);
      mkdirSync(dir, { recursive: true });
      const r = await call(request, "admin", "POST", "/api/v1/projects", {
        name: nm(`QA W5 DASH 種子 ${i}`), // 名稱不含導覽列的字樣「儀表板」：後面的 shells-and-layout 用 getByRole("link", { name: "儀表板" }) 做子字串比對，會撞名
        executionPath: dir,
        passCriteria: "種子",
        description: "",
        autonomyLevel: 3,
        draft: false,
      });
      expect(r.status, JSON.stringify(r.json)).toBe(201);
    }
    expect(await total()).toBeGreaterThanOrEqual(31);
    // 讓「本週完成」有非零的值：一個完成的批次
    const f = await createFixture(request, { name: nm("QA W5 DASH 完成"), kind: "A", level: 4 });
    await waitRun(request, await startRun(request, f, 4), ["COMPLETED"], 90_000);
    await ensureQuota(request, "viewer", 95); // 視窗回滿後才開始量，量測期間不會撞 429

    const t0 = Date.now();
    const calls: Array<{ at: number; path: string }> = [];
    page.on("request", (r) => {
      const u = new URL(r.url());
      if (r.url().startsWith(API_URL) && u.pathname.startsWith("/api/v1/")) calls.push({ at: Date.now() - t0, path: u.pathname });
    });
    const errors = collectConsoleErrors(page);
    await signIn(page, request, "viewer");
    await page.goto("/");
    await expect(page.getByTestId("kpi-grid")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("kpi-week-done")).toHaveText(/^\d+$/, FIRST_LOAD);
    const shown = Number(await page.getByTestId("kpi-week-done").innerText());
    const apiWeek = dataOf<{ completed: number; projectsCounted: number }>(await call(request, "viewer", "GET", `/api/v1/monitor/task-totals?from=${encodeURIComponent(startOfWeekIso())}`));
    expect(shown, "畫面的「本週完成」＝同一個視窗的 task-totals.completed").toBe(apiWeek.completed);
    expect(shown).toBeGreaterThanOrEqual(3);
    await snap(page, "p9-dashboard-31-projects.png");
    // 閒置 130 秒（涵蓋兩輪 60 秒輪詢與四輪 30 秒輪詢），什麼都不做
    await page.waitForTimeout(130_000);
    const inLoad = calls.filter((c) => c.at < 10_000);
    const steady = calls.filter((c) => c.at >= 10_000);
    const byPath = (rows: typeof calls) =>
      rows.reduce<Record<string, number>>((m, c) => ({ ...m, [c.path.replace(/[0-9a-f-]{36}/g, ":id")]: (m[c.path.replace(/[0-9a-f-]{36}/g, ":id")] ?? 0) + 1 }), {});
    const perMinute = steady.length / ((130_000 - 10_000) / 60_000);
    console.log(
      `[dashboard] 載入（前 10 秒）${inLoad.length} 次：${JSON.stringify(byPath(inLoad))}；穩態 ${steady.length} 次／120 秒＝每分鐘 ${perMinute.toFixed(1)} 次：${JSON.stringify(byPath(steady))}`,
    );
    expect(
      calls.filter((c) => c.path.includes("task-trend")),
      "不再對每個專案打 task-trend",
    ).toEqual([]);
    expect(inLoad.filter((c) => c.path === "/api/v1/monitor/task-totals").length, "載入時 task-totals 只打一次").toBe(1);
    expect(inLoad.length, `載入時請求數（W4＝31）：${JSON.stringify(byPath(inLoad))}`).toBeLessThanOrEqual(10);
    expect(perMinute, `穩態每分鐘請求數（W4＝約 31）：${JSON.stringify(byPath(steady))}`).toBeLessThanOrEqual(10);
    expect(steady.filter((c) => c.path === "/api/v1/monitor/task-totals").length, "60 秒一輪的 task-totals：120 秒內 1～3 次").toBeGreaterThanOrEqual(1);
    expect(errors, "瀏覽器主控台不應有錯誤（含 429）").toEqual([]);
    await expect(page.getByText("請求過於頻繁")).toHaveCount(0);
  });
});

async function runIdOf(request: Parameters<typeof ensureQuota>[0], f: Fixture): Promise<string> {
  const rows = dataOf<{ content: RunView[] }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}/executions?sort=runNumber,desc&size=1`)).content;
  return rows[0].id;
}
