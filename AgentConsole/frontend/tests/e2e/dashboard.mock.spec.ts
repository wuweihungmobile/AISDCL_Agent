import { expect, test } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { compose, fail, installApiMock, paged, signInAs, snap, collectConsoleErrors, type MockHandler } from "./mockApi";

/**
 * 總覽儀表板（設計稿畫面 1；契約 §4.5 G-06～G-08、§1.3.8）與 BottomRegion 的 Engine Bridge 連線點——route mock 版：
 *  - 四張 KPI：活躍專案數（專案 API）、待審批草案數（GET /notifications/summary 的 pendingSignoffs，跨專案）、
 *    本週完成任務數（GET /monitor/task-totals 的 completed：一次請求；from＝本週一 00:00、to 省略＝現在；v1.2，C-1／DEF-AC-009）、
 *    執行中 run 數（各 EXECUTING 專案的最新批次）；
 *  - 「進行中的執行」卡顯示最新批次（Run #n）與其進度，專案名連到執行頁；
 *  - Engine Bridge 連線點取自通知摘要的 bridgeConnected／bridgeCheckedAt：true 綠點、false 紅點、null 灰點「未知」（不假裝已連線）；
 *  - 「待人工審批」卡的清單與徽章取 GET /signoffs/pending（契約 §1.8.1、§4.5 G-10；v1.4，D-18）：專案、目標、任務、匯入草案四種，
 *    徽章＝counts.total＝KPI「待審批草案數」＝頂列徽章（通知摘要 pendingSignoffs）；簽核一筆後三者同步減 1（E2E-16 第 5 列的 mock 版）。
 */
const NOW = new Date().toISOString();
const A = "a0000000-0000-4000-8000-00000000000a";
const B = "b0000000-0000-4000-8000-00000000000b";
const C = "c0000000-0000-4000-8000-00000000000c";
const D = "d0000000-0000-4000-8000-00000000000d";
const RUN_A = "e0000000-0000-4000-8000-00000000000e";

const project = (id: string, name: string, status: string, signedOff: boolean, tasksDone: number, tasksCount: number) => ({
  id,
  name,
  executionPath: `/work/${name}`,
  status,
  autonomyLevel: 4,
  signedOff,
  goalsCount: 3,
  tasksCount,
  tasksDone,
  updatedAt: NOW,
});
const PROJECTS = [
  project(A, "專案甲", "EXECUTING", true, 13, 23),
  project(B, "專案乙", "DRAFT", false, 0, 5),
  project(C, "專案丙", "COMPLETED", true, 4, 4),
  project(D, "專案丁（封存）", "ARCHIVED", true, 4, 4),
];

/** 待簽核草案（契約 §1.8.1 PendingSignoffItem）：IMPORT 沒有專案；GOAL 的 parentId＝專案 id、TASK 的 parentId＝目標 id。 */
type Pending = { kind: "PROJECT" | "GOAL" | "TASK" | "IMPORT"; id: string; projectId: string | null; projectName: string | null; parentId: string | null; title: string; createdAt: string };
const G1 = "f0000000-0000-4000-8000-000000000001";
const G2 = "f0000000-0000-4000-8000-000000000002";
const T1 = "f1000000-0000-4000-8000-000000000001";
const I1 = "f2000000-0000-4000-8000-000000000001";
/** 建立時間升冪（伺服器給的順序）：匯入草案最早，其次專案、兩個目標、任務。 */
const makePending = (): Pending[] => [
  { kind: "IMPORT", id: I1, projectId: null, projectName: null, parentId: null, title: "需求文件.md", createdAt: "2026-10-15T01:00:00Z" },
  { kind: "PROJECT", id: B, projectId: B, projectName: "專案乙", parentId: null, title: "專案乙", createdAt: "2026-10-15T08:00:00Z" },
  { kind: "GOAL", id: G1, projectId: B, projectName: "專案乙", parentId: B, title: "基礎", createdAt: "2026-10-15T08:00:01Z" },
  { kind: "GOAL", id: G2, projectId: B, projectName: "專案乙", parentId: B, title: "核心", createdAt: "2026-10-15T08:00:02Z" },
  { kind: "TASK", id: T1, projectId: B, projectName: "專案乙", parentId: G1, title: "初始化", createdAt: "2026-10-15T08:00:03Z" },
];

/** summary 不含 pendingSignoffs：它與待審批清單同源，一律由 pending 推出（後端以同一組述詞算兩者）；pendingTotal＝總數大於清單（模擬 limit 截斷）。 */
type World = { summary: Record<string, unknown>; totals: "ok" | "fail"; pending: Pending[]; pendingTotal?: number };
const totalOf = (world: World) => world.pendingTotal ?? world.pending.length;

/** 全域任務總計（契約 §1.3.8）：跨專案的步驟列數；completed 是儀表板「本週完成」顯示的值 */
const TOTALS = { from: "2026-10-12T00:00:00Z", to: "2026-10-15T08:40:00Z", started: 8, completed: 7, failed: 1, retried: 0, projectsCounted: 2 };

function backend(world: World): MockHandler {
  return (call) => {
    const signoff = /^\/api\/v1\/(projects|goals|tasks|import)\/([^/]+)\/signoff$/.exec(call.path);
    if (call.method === "POST" && signoff) {
      world.pending = world.pending.filter((p) => p.id !== signoff[2]);
      return { data: { id: signoff[2], status: "REVIEWING", signedOff: true, signedOffBy: "operator", signedOffAt: NOW } };
    }
    if (call.method !== "GET") return undefined;
    if (call.path === "/api/v1/projects") return { data: paged(PROJECTS, 100) };
    if (call.path === "/api/v1/notifications/summary")
      return { data: { pendingSignoffs: totalOf(world), pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null, ...world.summary } };
    if (call.path === "/api/v1/signoffs/pending") {
      const limit = Number(call.query.get("limit") ?? 50);
      const countOf = (kind: Pending["kind"]) => world.pending.filter((p) => p.kind === kind).length;
      return {
        data: { counts: { projects: countOf("PROJECT"), goals: countOf("GOAL"), tasks: countOf("TASK"), imports: countOf("IMPORT"), total: totalOf(world) }, items: world.pending.slice(0, limit) },
      };
    }
    if (call.path === "/api/v1/monitor/task-totals") return world.totals === "fail" ? fail(500, { message: "伺服器錯誤" }) : { data: TOTALS };
    if (call.path === `/api/v1/projects/${A}/executions`) {
      return {
        data: paged(
          [
            {
              id: RUN_A,
              projectId: A,
              runNumber: 3,
              status: "RUNNING",
              autonomyLevel: 4,
              scopeMode: "ALL",
              totalTokensUsed: 5200,
              tokenBudget: 100000,
              startedAt: NOW,
              tasksTotal: 23,
              tasksCompleted: 13,
              tasksFailed: 0,
              successRate: 100,
            },
          ],
          1,
        ),
      };
    }
    return undefined;
  };
}

test.describe("總覽儀表板（route mock）", () => {
  test.setTimeout(120_000);

  test("四張 KPI 取真值；「進行中的執行」顯示最新批次進度並連到執行頁；待審批卡的徽章與清單、KPI、頂列徽章是同一個數字", async ({ page }) => {
    const world: World = { summary: { pendingReviews: 1, unacknowledgedAlerts: 2 }, totals: "ok", pending: makePending() };
    await signInAs(page, "OPERATOR");
    const { calls } = await installApiMock(page, compose(backend(world)));
    const errors = collectConsoleErrors(page);
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "總覽儀表板" })).toBeVisible({ timeout: 60_000 });

    // 活躍專案數：不含 COMPLETED／FAILED／ARCHIVED
    await expect(page.getByTestId("kpi-active")).toHaveText("2");
    await expect(page.getByTestId("kpi-grid")).toContainText("共 4 個專案 · 執行中 1");
    // 待審批草案數＝通知摘要（跨專案、含目標／任務／匯入草案），不是專案列表算出的近似值
    await expect(page.getByTestId("kpi-drafts")).toHaveText("5");
    await expect(page.getByTestId("kpi-grid")).toContainText("需 signoff 才可執行");
    // 本週完成任務數＝GET /monitor/task-totals 的 completed（一次請求；DEF-AC-009 的缺陷版本對每個專案各打一次 task-trend）
    await expect(page.getByTestId("kpi-week-done")).toHaveText("7");
    await expect(page.getByTestId("kpi-grid")).toContainText("本週一起 · 跨 2 個專案");
    await expect(page.getByTestId("kpi-grid")).not.toContainText("近似值");
    expect(
      calls.filter((c) => c.path.includes("/task-trend")),
      "不得再對各專案扇出 task-trend",
    ).toHaveLength(0);
    const totalsCalls = calls.filter((c) => c.path === "/api/v1/monitor/task-totals");
    // 只有一種請求（同一個 from）：dev 模式的 React StrictMode 會讓唯一的觀察者「掛上→卸下→掛上」，第一個請求被取消後重發，
    // 所以最多 2 筆相同網址（production 只有 1 筆）；缺陷版本是對每個專案各一筆不同網址的 task-trend
    expect(new Set(totalsCalls.map((c) => c.query.toString())).size).toBe(1);
    expect(totalsCalls.length).toBeLessThanOrEqual(2);
    const from = totalsCalls[0].query.get("from") as string;
    expect(totalsCalls[0].query.has("to"), "to 省略＝現在（契約 §1.3.8）").toBe(false);
    // from＝本週一 00:00（瀏覽器本機時區）
    expect(await page.evaluate((iso) => ({ day: new Date(iso).getDay(), h: new Date(iso).getHours(), m: new Date(iso).getMinutes(), s: new Date(iso).getSeconds() }), from)).toEqual({
      day: 1,
      h: 0,
      m: 0,
      s: 0,
    });
    // 執行中 run 數：EXECUTING 專案的最新批次仍在跑
    await expect(page.getByTestId("kpi-runs")).toHaveText("1");
    await expect(page.getByTestId("kpi-grid")).toContainText("進行中的執行批次");

    // 「進行中的執行」卡：最新批次的進度（tasksCompleted／tasksTotal），不是專案本身的計數
    const row = page.getByTestId("active-run");
    await expect(row).toHaveCount(1);
    await expect(row.getByTestId("active-run-progress")).toHaveText("Run #3 · 13 / 23 任務完成");
    await expect(row).toContainText("57%");
    await expect(row.getByRole("link", { name: "專案甲" })).toHaveAttribute("href", `/projects/${A}/execute`);
    // 待人工審批卡（v1.4）：清單與徽章取 GET /signoffs/pending（專案、兩個目標、任務、匯入草案各一），
    // 與上面 KPI 的 5、頂列 signoff 徽章同一個數字（舊版卡片只列「草稿專案與其未審批目標」共 3 筆，與 KPI 對不上）
    await expect(page.getByTestId("pending-count")).toHaveText("5");
    await expect(page.getByTestId("pending-item")).toHaveCount(5);
    await expect(page.getByTestId("signoff-badge")).toHaveText("5");
    // 無障礙（DEF-AC-004／005）：色彩對比、頂列 logo 名稱含可見文字等，只有真瀏覽器量得到
    await expectNoA11yViolations(page, "總覽儀表板");
    await snap(page, "01-dashboard-live.png", { tall: true });
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("待人工審批卡（契約 G-10）：專案、目標、任務、匯入草案四種各有副標、連到對應頁；列序照伺服器給的建立時間，請求帶 limit=50", async ({ page }) => {
    const world: World = { summary: {}, totals: "ok", pending: makePending() };
    await signInAs(page, "OPERATOR");
    const { calls } = await installApiMock(page, compose(backend(world)));
    const errors = collectConsoleErrors(page);
    await page.goto("/");
    await expect(page.getByTestId("pending-count")).toHaveText("5", { timeout: 60_000 });

    // 同一份來源：徽章＝KPI＝頂列徽章（通知摘要的 pendingSignoffs 與 counts.total 由同一組述詞算出）
    await expect(page.getByTestId("kpi-drafts")).toHaveText("5");
    await expect(page.getByTestId("signoff-badge")).toHaveText("5");

    // 列序＝伺服器給的（建立時間升冪、最早的先）；前端不重排。連結文字是標題，副標是中文種類（目標與任務帶所屬專案名）
    const rows = page.getByTestId("pending-item");
    await expect(rows).toHaveCount(5);
    const expected = [
      { kind: "IMPORT", title: "需求文件.md", meta: "匯入草案", href: "/import" },
      { kind: "PROJECT", title: "專案乙", meta: "專案草案", href: `/projects/${B}` },
      { kind: "GOAL", title: "基礎", meta: "目標草案・專案乙", href: `/projects/${B}/goals/${G1}` },
      { kind: "GOAL", title: "核心", meta: "目標草案・專案乙", href: `/projects/${B}/goals/${G2}` },
      { kind: "TASK", title: "初始化", meta: "任務草案・專案乙", href: `/projects/${B}/goals/${G1}/tasks/${T1}` },
    ];
    for (const [i, want] of expected.entries()) {
      const row = rows.nth(i);
      await expect(row, `第 ${i + 1} 列的種類`).toHaveAttribute("data-kind", want.kind);
      await expect(row.getByRole("link"), `第 ${i + 1} 列的連結文字`).toHaveText(want.title);
      await expect(row.getByRole("link"), `第 ${i + 1} 列的連結目標`).toHaveAttribute("href", want.href);
      await expect(row, `第 ${i + 1} 列的副標`).toContainText(want.meta);
      await expect(row.getByRole("button", { name: `審批：${want.title}` }), `第 ${i + 1} 列的審批鈕（OPERATOR 可按）`).toBeEnabled();
    }

    // 請求形狀：只打 /signoffs/pending（不再用專案與目標 API 另外組清單），limit＝50；沒有被截斷時不寫說明
    const pendingCalls = calls.filter((c) => c.path === "/api/v1/signoffs/pending");
    expect(pendingCalls.length).toBeGreaterThan(0);
    expect(new Set(pendingCalls.map((c) => c.query.get("limit")))).toEqual(new Set(["50"]));
    expect(
      calls.filter((c) => /^\/api\/v1\/(projects\/[^/]+\/goals|goals\/[^/]+\/tasks)$/.test(c.path)),
      "儀表板不再為了待審批清單逐專案、逐目標展開",
    ).toHaveLength(0);
    await expect(page.getByTestId("pending-truncated")).toHaveCount(0);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("在待審批卡簽核一筆：POST 依種類走對路徑並帶審批者；成功後卡片徽章與清單、KPI、頂列徽章同步減 1（E2E-16 第 5 列）", async ({ page }) => {
    const world: World = { summary: {}, totals: "ok", pending: makePending() };
    await signInAs(page, "OPERATOR", "mock-op");
    const { calls } = await installApiMock(page, compose(backend(world)));
    const errors = collectConsoleErrors(page);
    await page.goto("/");
    await expect(page.getByTestId("pending-count")).toHaveText("5", { timeout: 60_000 });
    await expect(page.getByTestId("kpi-drafts")).toHaveText("5");
    await expect(page.getByTestId("signoff-badge")).toHaveText("5");

    await page.getByRole("button", { name: "審批：初始化" }).click();
    const dialog = page.getByRole("dialog", { name: "審批 signoff：任務" });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("初始化");
    await expect(dialog.getByLabel("審批者")).toHaveValue("mock-op");
    await dialog.getByRole("button", { name: "確認 signoff" }).click();

    // 任務草案→POST /tasks/{id}/signoff，body 只有審批者
    await expect.poll(() => calls.filter((c) => c.method === "POST").map((c) => c.path)).toEqual([`/api/v1/tasks/${T1}/signoff`]);
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ approver: "mock-op" });

    // 三處同源、同一次失效：不必等 30 秒輪詢
    await expect(page.getByTestId("pending-count")).toHaveText("4");
    await expect(page.getByTestId("pending-item")).toHaveCount(4);
    await expect(page.getByRole("button", { name: "審批：初始化" })).toHaveCount(0);
    await expect(page.getByTestId("kpi-drafts")).toHaveText("4");
    await expect(page.getByTestId("signoff-badge")).toHaveText("4");
    await expect(dialog).toBeHidden();

    // 再簽匯入草案（沒有專案的那一種）→ POST /import/{id}/signoff；清單剩 3 筆、IMPORT 那列消失
    await page.getByRole("button", { name: "審批：需求文件.md" }).click();
    const importDialog = page.getByRole("dialog", { name: "審批 signoff：匯入草案" });
    await importDialog.getByRole("button", { name: "確認 signoff" }).click();
    await expect.poll(() => calls.filter((c) => c.method === "POST").map((c) => c.path)).toEqual([`/api/v1/tasks/${T1}/signoff`, `/api/v1/import/${I1}/signoff`]);
    await expect(page.getByTestId("pending-count")).toHaveText("3");
    await expect(page.getByTestId("pending-item")).toHaveCount(3);
    await expect(page.locator('[data-testid="pending-item"][data-kind="IMPORT"]')).toHaveCount(0);
    await expect(page.getByTestId("kpi-drafts")).toHaveText("3");
    await expect(page.getByTestId("signoff-badge")).toHaveText("3");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("待審批超過 limit：徽章、KPI、頂列徽章顯示總數，清單只列最早的 50 筆並寫明「僅列出最早的 N 筆，共 M 筆」", async ({ page }) => {
    // 60 筆目標草案（同一個專案）：伺服器只回最早的 limit 筆，counts.total 仍是 60
    const many: Pending[] = Array.from({ length: 60 }, (_, i) => ({
      kind: "GOAL",
      id: `f3000000-0000-4000-8000-${String(i + 1).padStart(12, "0")}`,
      projectId: B,
      projectName: "專案乙",
      parentId: B,
      title: `目標 ${i + 1}`,
      createdAt: `2026-10-15T09:${String(i).padStart(2, "0")}:00Z`,
    }));
    const world: World = { summary: {}, totals: "ok", pending: many };
    await signInAs(page, "OPERATOR");
    const { calls } = await installApiMock(page, compose(backend(world)));
    await page.goto("/");
    await expect(page.getByTestId("pending-count")).toHaveText("60", { timeout: 60_000 });
    await expect(page.getByTestId("pending-item")).toHaveCount(50);
    await expect(page.getByTestId("pending-truncated")).toHaveText("僅列出最早的 50 筆，共 60 筆");
    await expect(page.getByTestId("kpi-drafts")).toHaveText("60");
    await expect(page.getByTestId("signoff-badge")).toHaveText("60");
    // 列出的是最早的（第 1 筆在、第 51 筆不在）
    await expect(page.getByTestId("pending-item").first()).toContainText("目標 1");
    await expect(page.getByTestId("pending-signoff-card")).not.toContainText("目標 51");
    expect(calls.filter((c) => c.path === "/api/v1/signoffs/pending").every((c) => c.query.get("limit") === "50")).toBe(true);
  });

  test("task-totals 查詢失敗：「本週完成任務數」顯示「—」與錯誤說明（不編數字），其餘 KPI 照常（截圖檔名沿用 partial：只有一張卡缺資料）", async ({ page }) => {
    const world: World = { summary: {}, totals: "fail", pending: [] };
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(backend(world)));
    await page.goto("/");
    await expect(page.getByTestId("kpi-grid")).toContainText("無法載入本週完成任務數", { timeout: 60_000 });
    await expect(page.getByTestId("kpi-week-done")).toHaveText("—");
    await expect(page.getByTestId("kpi-active")).toHaveText("2");
    await expect(page.getByTestId("kpi-drafts")).toHaveText("0");
    await expect(page.getByTestId("kpi-grid")).toContainText("全部已審批");
    // 沒有待審批的草案：徽章 0、清單換成空狀態（不留舊的假項目）
    await expect(page.getByTestId("pending-count")).toHaveText("0");
    await expect(page.getByTestId("pending-signoff-card")).toContainText("沒有待審批的草案");
    await expect(page.getByTestId("pending-item")).toHaveCount(0);
    await snap(page, "01-dashboard-partial.png");
  });

  test("底部 Engine Bridge 連線點：true 綠點已連線、false 紅點未連線、null 灰點「未知」（不假裝已連線）", async ({ page }) => {
    const world: World = { summary: { bridgeConnected: true, bridgeCheckedAt: NOW }, totals: "ok", pending: [] };
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(backend(world)));
    await page.goto("/");
    const bridge = page.locator('[data-region="bottom"]').getByTestId("status-Engine Bridge");
    await expect(page.getByRole("heading", { name: "總覽儀表板" })).toBeVisible({ timeout: 60_000 });

    await expect(bridge).toHaveAttribute("data-state", "online");
    await expect(bridge).toContainText("Engine Bridge · 已連線");
    await expect(bridge).toHaveAttribute("title", /^最近一次探測：\d{2}:\d{2}:\d{2}$/);
    await expect(bridge.locator("span").first()).toHaveClass(/bg-wg-primary/);

    world.summary = { bridgeConnected: false, bridgeCheckedAt: NOW };
    await page.reload();
    await expect(bridge).toHaveAttribute("data-state", "offline");
    await expect(bridge).toContainText("Engine Bridge · 未連線");
    await expect(bridge.locator("span").first()).toHaveClass(/bg-wg-error/);
    await snap(page, "01-dashboard-bridge-offline.png");

    world.summary = { bridgeConnected: null, bridgeCheckedAt: null };
    await page.reload();
    await expect(bridge).toHaveAttribute("data-state", "unknown");
    await expect(bridge).toContainText("Engine Bridge · 未知");
    await expect(bridge).toHaveAttribute("title", /尚未探測過 Engine Bridge/);
    await expect(bridge.locator("span").first()).toHaveClass(/bg-wg-disabled-text/);
    // console-api 自己的點照常：專案列表回得來＝已連線
    await expect(page.locator('[data-region="bottom"]').getByTestId("status-console-api")).toHaveAttribute("data-state", "online");
  });
});

/**
 * 頂列「登出」（契約 §1.9.1，v1.4 D-19；API-AUTH-03 前端半）：先 fire-and-forget 呼叫 POST /auth/logout 撤銷 refresh token，
 * 再清本機 session、導向登入頁；端點失敗不阻擋登出。全棧的撤銷名單行為（登出後舊 refresh token 401、Redis 降級）由 E2E-16 第 7～10 列驗，這裡只驗前端送了什麼、之後做了什麼。
 */
test.describe("頂列登出（route mock）", () => {
  test.setTimeout(120_000);

  for (const [title, reply] of [
    ["按「登出」：先 POST /auth/logout 帶 refresh token（免認證、不帶 Authorization），再清本機 session 並回登入頁", { status: 204 }],
    ["登出端點暫時不可用（503）：不阻擋登出——照樣清本機 session 並回登入頁，不卡在畫面上", fail(503, { message: "後端暫時不可用" })],
  ] as const) {
    test(title, async ({ page }) => {
      const world: World = { summary: {}, totals: "ok", pending: [] };
      await signInAs(page, "OPERATOR", "mock-op");
      const { calls } = await installApiMock(
        page,
        compose((call) => (call.method === "POST" && call.path === "/api/v1/auth/logout" ? reply : undefined), backend(world)),
      );
      const errors = collectConsoleErrors(page);
      await page.goto("/");
      await expect(page.getByTestId("user-badge")).toContainText("mock-op", { timeout: 60_000 });

      await page.getByRole("button", { name: "登出" }).click();
      // 登入頁；網址可帶 ?next=（session 一清，登入守衛也會把「登出前所在的頁」記成 next；既有行為，登入後回到原頁）
      await expect(page).toHaveURL(/\/login(\?next=.*)?$/);
      await expect(page.getByRole("heading", { name: "登入 AISDLC Console" })).toBeVisible();

      // 撤銷的是 refresh token（不是 access token）；登出端點免認證，所以不帶 Authorization，也沒有 401 換新那一套
      const logout = calls.filter((c) => c.path === "/api/v1/auth/logout");
      expect(logout).toHaveLength(1);
      expect(logout[0].method).toBe("POST");
      expect(logout[0].body).toEqual({ refreshToken: "mock-refresh-token" });
      expect(logout[0].headers.authorization).toBeUndefined();
      expect(await page.evaluate(() => window.sessionStorage.getItem("aisdlc.console.session")), "本機 session 已清除").toBeNull();
      expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
    });
  }
});
