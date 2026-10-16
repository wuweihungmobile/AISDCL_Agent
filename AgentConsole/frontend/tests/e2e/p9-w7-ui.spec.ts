import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import { E2E_ROOT, FakeLlm, NEEDS_BRIDGE, bootstrapSettings, brd, call, createFixture, dataOf, ensureQuota, poll, signIn, type Fixture } from "./realBackend";
import { MOCK_CLAUDE, createLongFixture } from "./w7";

/**
 * W7 複驗（UI 面）：
 *  ① DAG 全螢幕（契約 §4.2 E-22；US-E-09；審查 D-01）：點「全螢幕」→覆蓋層尺寸等於視窗、Esc 與「結束全螢幕」都能關、關閉後焦點回到「全螢幕」鈕、展開／收合狀態進出都保留、全螢幕內 axe 零違規。
 *  ② US-P-04（審查 V-04）：專案 EXECUTING 時編輯頁的鎖定橫幅與欄位停用（真後端、真執行中的批次）。
 *  ③ V-08：九個畫面對設計稿（docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md 與 screenshots/*.png）逐一做 DOM 結構斷言，並各存一張截圖
 *     （p9-w7-screen-0N-*.png）供人眼對照設計稿 PNG；已登記的差異（ADR-001 §4／ADR-002 §4／契約 §4.6）以「登記的差異」另列斷言，不計為缺口。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const nm = (base: string) => `${base} ${RUN}`;
const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED"];

type Run = { id: string; status: string };
let llm: FakeLlm;
let done: Fixture; // 跑完的專案（有執行、監控資料）
let draft: Fixture; // 草案專案（簽核橫幅、列表的「未審批」標籤）

async function startAndFinish(request: Parameters<typeof ensureQuota>[0], f: Fixture): Promise<string> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
  expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(201);
  const id = dataOf<Run>(r).id;
  await poll(
    async () => dataOf<Run>(await call(request, "viewer", "GET", `/api/v1/executions/${id}`)),
    (d) => TERMINAL.includes(d.status),
    `批次 ${id} 進入終態`,
    120_000,
    2_000,
  );
  return id;
}

/** 一組「設計稿元素」：名稱＋定位器；全部用 expect.soft 逐一斷言，失敗清單一次列完（不是遇到第一個就停）。 */
async function expectAnchors(page: Page, screen: string, anchors: Array<[string, Locator]>): Promise<void> {
  for (const [what, loc] of anchors) await expect.soft(loc.first(), `${screen}｜${what}`).toBeVisible({ timeout: 5_000 });
}

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);
  llm = new FakeLlm(`QA W7 畫面 ${RUN}`);
  await llm.listen();
  done = await createFixture(request, { name: nm("QA W7 畫面 完成"), kind: "A", level: 4 });
  await startAndFinish(request, done);
  draft = await createFixture(request, { name: nm("QA W7 畫面 草案"), kind: "A", level: 4, draft: true });
  // 設計稿畫面 3 的「通過標準」是逐項清單、畫面 4 與 5 是核取清單；通過標準欄位本來就以 Markdown 渲染（MarkdownView variant="criteria"），
  // 夾具預設只有單句，所以把畫面用到的三筆改成設計稿同樣的內容才比得到（只改夾具資料，不是改產品行為）。
  const bullets = "- 所有單元測試通過率 ≥ 95%\n- 整合測試全數通過\n- 程式碼覆蓋率 ≥ 80%";
  expect((await call(request, "operator", "PUT", `/api/v1/projects/${draft.projectId}`, { passCriteria: bullets })).status).toBe(200);
  expect((await call(request, "operator", "PUT", `/api/v1/goals/${draft.goalIds[0]}`, { passCriteria: "- [ ] 所有核心模組通過單元測試\n- [ ] API 架構層通過整合測試" })).status).toBe(200);
  expect((await call(request, "operator", "PUT", `/api/v1/tasks/${done.taskIds[0]}`, { passCriteria: "- [x] 端點回傳通用回應格式\n- [ ] 整合 SpringDoc OpenAPI" })).status).toBe(200);
});

test.afterAll(async ({ request }) => {
  await llm.close();
  await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
  await call(request, "admin", "POST", "/api/v1/settings/model/apiUrl/reset");
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 60);
  await ensureQuota(request, "viewer", 50);
});

test.describe("DAG 全螢幕（E-22）", () => {
  test.setTimeout(240_000);

  test("點「全螢幕」→覆蓋層鋪滿視窗；展開／收合狀態進出都保留；Esc 與「結束全螢幕」都能關；關閉後焦點回到「全螢幕」鈕；全螢幕內 axe 零違規", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    await signIn(page, request, "operator");
    await page.goto(`/projects/${done.projectId}/execute`);
    await expect(page.getByTestId("dag-card")).toBeVisible(FIRST_LOAD);
    const taskNodes = () => page.locator('[data-testid^="dag-task-"]');
    await expect(taskNodes(), "預設展開任務：夾具 A 有 3 個任務").toHaveCount(3, FIRST_LOAD);
    await page.getByTestId("dag-toggle").click(); // 先收合
    await expect(taskNodes()).toHaveCount(0);
    await expect(page.getByTestId("dag-toggle")).toHaveText("展開任務");

    const open = page.getByTestId("dag-fullscreen-open");
    await expect(open).toHaveAttribute("aria-pressed", "false");
    await open.click();
    const fs = page.getByTestId("dag-fullscreen");
    await expect(fs).toBeVisible();
    await expect(open, "進入後按鈕 aria-pressed 同步").toHaveAttribute("aria-pressed", "true");
    const vp = page.viewportSize()!;
    // 開啟過場（淡入、微位移）結束後再量：過場中 y 會差幾個像素
    const measure = async () => {
      const b = (await fs.boundingBox())!;
      return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) };
    };
    await expect.poll(measure, { message: "DAG 容器尺寸等於視窗", timeout: 5_000 }).toEqual({ x: 0, y: 0, w: vp.width, h: vp.height });
    const box = await measure();
    await expect(page.getByTestId("dag-fullscreen-exit")).toHaveText("結束全螢幕");
    await expect(page.getByTestId("dag-fullscreen-exit")).toHaveAttribute("aria-pressed", "true");
    expect(await taskNodes().count(), "收合狀態進全螢幕時保留（沒有任務節點）").toBe(0);
    await page.getByTestId("dag-fs-toggle").click();
    await expect(taskNodes(), "全螢幕內展開：3 個任務節點，且只掛一份（testid 唯一）").toHaveCount(3);
    await expect(page.locator('[data-testid^="dag-goal-"]')).toHaveCount(2);
    await snap(page, "p9-w7-dag-fullscreen.png", { focus: fs });
    await expectNoA11yViolations(page, "DAG 全螢幕");

    await page.keyboard.press("Escape");
    await expect(fs, "Esc 關閉").toBeHidden();
    await expect(open).toBeFocused();
    expect(await page.evaluate(() => document.activeElement?.getAttribute("data-testid")), "焦點歸還「全螢幕」鈕").toBe("dag-fullscreen-open");
    await expect(taskNodes(), "全螢幕內展開的狀態帶回卡片（進出都保留）").toHaveCount(3);
    await expect(page.getByTestId("dag-toggle")).toHaveText("收合任務");
    await expect(open).toHaveAttribute("aria-pressed", "false");

    // 第二種關法：「結束全螢幕」鈕
    await open.click();
    await expect(fs).toBeVisible();
    await page.getByTestId("dag-fullscreen-exit").click();
    await expect(fs).toBeHidden();
    await expect(open).toBeFocused();
    console.log(`[w7-ui] E-22：全螢幕尺寸 ${box.w}x${box.h}＝視窗 ${vp.width}x${vp.height}；Esc 與「結束全螢幕」都關閉並把焦點還給「全螢幕」鈕；收合／展開狀態進出保留；全螢幕內 axe 零違規`);
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
  });
});

test.describe("US-P-04（審查 V-04）：專案執行中的編輯鎖定", () => {
  test.setTimeout(300_000);

  test("專案 EXECUTING 時開編輯頁：橫幅「專案執行中：只能修改名稱與說明」、執行路徑與自治等級停用、名稱可編輯；批次終態後解鎖", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    const f = await createLongFixture(request, nm("QA W7 鎖定"), 25);
    const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
    expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(201);
    const runId = dataOf<Run>(r).id;
    try {
      const p = dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`));
      expect(p.status, "專案進入 EXECUTING").toBe("EXECUTING");
      await signIn(page, request, "operator");
      await page.goto(`/projects/${f.projectId}/edit`);
      await expect(page.getByText("專案執行中：只能修改名稱與說明，其他欄位已鎖定。")).toBeVisible(FIRST_LOAD);
      await expect(page.getByLabel("執行路徑")).toBeDisabled();
      await expect(page.getByLabel("自治等級")).toBeDisabled();
      await expect(page.getByLabel("專案名稱", { exact: true })).toBeEnabled();
      await snap(page, "p9-w7-project-edit-locked.png");
      console.log("[w7-ui] US-P-04：EXECUTING 專案的編輯頁顯示鎖定橫幅；執行路徑、自治等級停用；名稱可編輯");
    } finally {
      await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`);
    }
    await poll(
      async () => dataOf<Run>(await call(request, "viewer", "GET", `/api/v1/executions/${runId}`)),
      (d) => TERMINAL.includes(d.status),
      `批次 ${runId} 取消後進入終態`,
      90_000,
      2_000,
    );
    await poll(
      async () => dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`)),
      (d) => d.status !== "EXECUTING",
      "專案離開 EXECUTING",
      60_000,
      2_000,
    );
    await page.reload();
    await expect(page.getByLabel("執行路徑")).toBeEnabled(FIRST_LOAD);
    await expect(page.getByText("專案執行中：只能修改名稱與說明，其他欄位已鎖定。")).toHaveCount(0);
    console.log("[w7-ui] US-P-04：批次取消、專案離開 EXECUTING 後重新整理，欄位解鎖、橫幅消失");
    expect(errors.filter((e) => !/Failed to load|ERR_/.test(e))).toEqual([]);
  });
});

test.describe("V-08：九個畫面對設計稿（DOM 結構斷言＋截圖供人眼對照）", () => {
  test.setTimeout(240_000);

  test("全域版面（四區塊）：公告列、主導覽列（Logo、搜尋、鈴、待審批佇列）、側欄六項與我的專案", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "總覽儀表板" })).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "全域", [
      ["公告列：說明文件", page.getByText("說明文件", { exact: true })],
      ["公告列：下載 CLI", page.getByText("下載 CLI", { exact: true })],
      ["公告列：GitHub", page.getByText("GitHub", { exact: true })],
      ["公告列：Engine Bridge · 已連線", page.getByText(/Engine Bridge · 已連線/)],
      ["公告列：通知總覽", page.getByText("通知總覽", { exact: true })],
      ["公告列：幫助中心", page.getByText("幫助中心", { exact: true })],
      ["公告列：繁體中文", page.getByText("繁體中文", { exact: true })],
      ["公告列：使用者徽章", page.getByTestId("user-badge")],
      ["Logo：AISDLC Console", page.getByText("AISDLC Console", { exact: true })],
      ["Logo：AGENT CONTROL PANEL", page.getByText("AGENT CONTROL PANEL", { exact: true })],
      ["搜尋列（placeholder 搜尋專案、目標、任務…）", page.getByPlaceholder("搜尋專案、目標、任務…")],
      ["通知鈴", page.getByTestId("bell-trigger")],
      ["待審批佇列鈕", page.getByRole("link", { name: /待審批佇列 \d+ 筆/ })],
      ["側欄標題：導航", page.getByText("導航", { exact: true })],
      ["導航：儀表板", page.getByRole("link", { name: "儀表板", exact: true })],
      ["導航：專案管理", page.getByRole("link", { name: "專案管理", exact: true })],
      ["導航：BRD/PRD 匯入", page.getByRole("link", { name: "BRD/PRD 匯入", exact: true })],
      ["導航：執行中心", page.getByRole("link", { name: "執行中心", exact: true })],
      ["導航：監控中心", page.getByRole("link", { name: "監控中心", exact: true })],
      ["導航：系統設定", page.getByRole("link", { name: "系統設定", exact: true })],
      ["我的專案 rail", page.getByText("我的專案", { exact: true })],
    ]);
  });

  test("畫面 1 總覽儀表板：標題與副標、匯入按鈕、四張 KPI 卡、進行中的執行、待人工審批", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "總覽儀表板" })).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("pending-signoff-card")).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "畫面 1", [
      ["副標", page.getByText("AISDLC 自治開發 Agent · 全局健康度與待辦")],
      ["主色按鈕：匯入 BRD / PRD", page.getByRole("link", { name: "匯入 BRD / PRD" })],
      ["KPI 卡 ×4 的容器", page.getByTestId("kpi-grid")],
      ["進行中的執行（標題）", page.getByText("進行中的執行", { exact: true })],
      ["連結：查看全部專案 →", page.getByRole("link", { name: "查看全部專案 →" })],
      ["待人工審批（標題）", page.getByText("待人工審批", { exact: true })],
      ["說明：AI 草案 signoff 硬閘 — 未審批禁止執行", page.getByText("AI 草案 signoff 硬閘 — 未審批禁止執行")],
      ["待人工審批的計數 badge", page.getByTestId("pending-count")],
    ]);
    await expect(page.getByTestId("kpi-grid").locator("> *"), "KPI 卡四張").toHaveCount(4);
    // 登記的差異（ADR-002 §4 第 2 項）：KPI 為 活躍專案數／待審批草案數／本週完成任務數／執行中 run 數（設計稿為 專案完成率／任務成功率／Token 總消耗／待人工審批）
    for (const label of ["活躍專案數", "待審批草案數", "本週完成任務數", "執行中 run 數"])
      await expect.soft(page.getByTestId("kpi-grid").getByText(label, { exact: true }), `登記的差異：KPI「${label}」`).toBeVisible();
    await snap(page, "p9-w7-screen-01-dashboard.png");
  });

  test("畫面 2 專案管理：標題與副標、匯入／新建專案、篩選工具列（狀態 tab、排序、分頁）、專案卡（圖示、狀態、未審批標籤、meta、四個動作）", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto("/projects");
    await expect(page.getByRole("heading", { name: "專案管理" })).toBeVisible(FIRST_LOAD);
    const card = page.getByTestId("project-card").filter({ hasText: draft.name });
    await expect(card).toHaveCount(1, FIRST_LOAD);
    await expectAnchors(page, "畫面 2", [
      ["副標：Project → Goal → Task 三層管理 · 共 N 筆", page.getByText(/Project → Goal → Task 三層管理 · 共 \d+ 筆/)],
      ["右側：匯入", page.getByRole("link", { name: "匯入", exact: true })],
      ["右側：新建專案", page.getByRole("button", { name: "新建專案" })],
      ["工具列：篩選標籤", page.getByText("篩選", { exact: true })],
      ["狀態 tab：全部", page.getByRole("button", { name: "全部", exact: true })],
      ["狀態 tab：草稿", page.getByRole("button", { name: "草稿", exact: true })],
      ["狀態 tab：就緒", page.getByRole("button", { name: "就緒", exact: true })],
      ["狀態 tab：執行中", page.getByRole("button", { name: "執行中", exact: true })],
      ["狀態 tab：完成", page.getByRole("button", { name: "完成", exact: true })],
      ["狀態 tab：失敗", page.getByRole("button", { name: "失敗", exact: true })],
      ["排序下拉", page.getByRole("combobox").first()],
      ["專案卡：名稱連結", card.getByRole("link", { name: draft.name })],
      ["專案卡：未審批紅標籤", card.getByText("未審批", { exact: true })],
      ["專案卡 meta：Lv.N 自治", card.getByText(/Lv\.\d+ 自治/)],
      ["專案卡 meta：目標 N", card.getByText(/目標 \d+/)],
      ["專案卡 meta：任務 done / total", card.getByText(/任務 \d+ \/ \d+/)],
      ["專案卡 meta：更新 日期", card.getByText(/更新 \d{4}-\d{2}-\d{2}/)],
      ["專案卡：查看", card.getByRole("link", { name: /查看/ })],
      ["專案卡：編輯（按鈕）", card.getByRole("button", { name: /編輯/ })],
      ["專案卡：執行", card.getByRole("link", { name: /執行/ })],
      ["專案卡：監控", card.getByRole("link", { name: /監控/ })],
    ]);
    await snap(page, "p9-w7-screen-02-projects.png");
  });

  test("畫面 3 專案詳情：返回連結、標題與 meta、signoff 警示橫幅、基本資訊／專案說明兩欄、目標清單、底部行動", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto(`/projects/${draft.projectId}`);
    await expect(page.getByRole("heading", { name: draft.name })).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "畫面 3", [
      ["返回專案列表", page.getByRole("link", { name: /返回專案列表/ })],
      ["meta：自治等級", page.getByText(/自治等級/)],
      ["signoff 警示橫幅", page.getByText(/AI 草案/)],
      ["橫幅按鈕：審批 signoff", page.getByRole("button", { name: /審批/ })],
      ["左卡：基本資訊", page.getByText("基本資訊", { exact: true })],
      ["基本資訊：執行路徑", page.getByText("執行路徑", { exact: true })],
      ["基本資訊：通過標準", page.getByText("通過標準", { exact: true })],
      ["右卡：專案說明", page.getByText("專案說明", { exact: true })],
      ["目標清單 (N)", page.getByText(/目標清單 \(\d+\)/)],
      ["新增目標", page.getByRole("button", { name: /新增目標/ })],
      ["底部：執行專案", page.getByRole("link", { name: /執行專案/ })],
      ["底部：查看監控", page.getByRole("link", { name: /查看監控/ })],
      ["底部：編輯專案（按鈕）", page.getByRole("button", { name: /編輯專案/ })],
    ]);
    // 設計稿：基本資訊的「通過標準」是三個項目的清單
    await expect.soft(page.locator(".md-criteria li"), "通過標準渲染成逐項清單（設計稿三項）").toHaveCount(3);
    // 登記的差異（ADR-002 §4 第 4、10 項）：底部多「刪除專案」、沒有 PRD wireframe 的「匯出」
    await expect.soft(page.getByRole("button", { name: /刪除專案/ }), "登記的差異：多一個刪除專案").toBeVisible();
    await expect.soft(page.getByRole("button", { name: "匯出" }), "登記的差異：不提供匯出").toHaveCount(0);
    await snap(page, "p9-w7-screen-03-project-detail.png");
  });

  test("畫面 4 目標詳情：返回專案、標題與 meta、草案警示橫幅、目標說明／通過標準、任務清單、編輯目標", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto(`/projects/${draft.projectId}/goals/${draft.goalIds[0]}`);
    await expect(page.getByRole("heading", { name: "基礎" })).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "畫面 4", [
      ["返回專案", page.getByRole("link", { name: /返回專案/ })],
      ["草案警示橫幅（精簡版）", page.getByText(/草案未審批/)],
      ["卡：目標說明", page.getByText("目標說明", { exact: true })],
      ["卡：通過標準", page.getByText("通過標準", { exact: true })],
      ["任務清單 (N)", page.getByText(/任務清單 \(\d+\)/)],
      ["新增任務", page.getByRole("button", { name: /新增任務/ })],
      ["底部：編輯目標（按鈕）", page.getByRole("button", { name: /編輯目標/ })],
    ]);
    // 設計稿：通過標準是兩個項目的核取清單（都未勾）
    await expect.soft(page.locator(".md-criteria [role=checkbox]"), "通過標準渲染成核取清單（設計稿兩項）").toHaveCount(2);
    await expect.soft(page.locator(".md-criteria [role=checkbox][aria-checked=false]"), "兩項都未勾").toHaveCount(2);
    await snap(page, "p9-w7-screen-04-goal-detail.png");
  });

  test("畫面 5 任務詳情：返回目標、標題與 meta、三張指標卡（開始時間／Token 消耗／重試次數）、任務說明／通過標準、深色執行日誌、重試／編輯", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto(`/projects/${done.projectId}/goals/${done.goalIds[0]}/tasks/${done.taskIds[0]}`);
    await expect(page.getByRole("heading", { name: "初始化" })).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "畫面 5", [
      ["返回目標", page.getByRole("link", { name: /返回目標/ })],
      ["指標卡：開始時間", page.getByText("開始時間", { exact: true })],
      ["指標卡：Token 消耗", page.getByText("Token 消耗", { exact: true })],
      ["指標卡：重試次數", page.getByText("重試次數", { exact: true })],
      ["卡：任務說明", page.getByText("任務說明", { exact: true })],
      ["卡：通過標準", page.getByText("通過標準", { exact: true })],
      ["執行日誌卡", page.getByText("執行日誌", { exact: true })],
      ["底部：編輯（按鈕）", page.getByRole("button", { name: /編輯/ })],
    ]);
    // 設計稿：通過標準是兩個項目的核取清單（一勾一未勾）
    await expect.soft(page.locator(".md-criteria [role=checkbox]"), "通過標準渲染成核取清單（設計稿兩項）").toHaveCount(2);
    await expect.soft(page.locator(".md-criteria [role=checkbox][aria-checked=true]"), "其中一項已勾").toHaveCount(1);
    // 登記的差異（ADR-002 §4 第 4、11 項）：沒有 PRD wireframe 的暫停／取消；第三張指標卡取設計稿的「重試次數」而非「執行時長」
    await expect.soft(page.getByRole("button", { name: /暫停|取消/ }), "登記的差異：任務詳情沒有暫停／取消").toHaveCount(0);
    await expect.soft(page.getByText("執行時長", { exact: true }), "登記的差異：沒有『執行時長』指標卡").toHaveCount(0);
    await snap(page, "p9-w7-screen-05-task-detail.png");
  });

  test("畫面 6 匯入：標題、步驟 1「輸入來源」（來源 tab、拖放區、自治等級、執行路徑、補充說明、開始解析）；解析後步驟 2「結構預覽與編輯」（樹、signoff 警示、放棄／確認匯入）", async ({
    page,
    request,
  }) => {
    const dir = path.join(E2E_ROOT, "projects", `w7-screen-${RUN}`);
    mkdirSync(dir, { recursive: true });
    await call(request, "admin", "PUT", "/api/v1/settings/model/apiUrl", { value: llm.endpoint });
    await call(request, "admin", "PUT", "/api/v1/settings/model/apiKey", { value: "e2e-fake-key", confirm: true });
    await signIn(page, request, "operator");
    await page.goto("/import");
    await expect(page.getByRole("heading", { name: "BRD / PRD 智能匯入" })).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "畫面 6 步驟 1", [
      ["步驟 1 卡：輸入來源", page.getByText("輸入來源", { exact: true })],
      ["來源 tab：上傳檔案（設計稿稱「檔案上傳」）", page.getByRole("tab", { name: /上傳檔案/ })],
      ["來源 tab：貼上文字", page.getByRole("tab", { name: /貼上文字/ })],
      ["拖放區文字：拖曳檔案至此，或點擊選擇", page.getByText(/拖曳檔案至此，或點擊選擇/)],
      ["格式說明（10MB）", page.getByText(/10 ?MB/).first()],
      ["自治等級", page.getByLabel("自治等級")],
      ["執行路徑", page.getByLabel("執行路徑")],
      ["補充說明", page.getByLabel("補充說明")],
      ["開始解析", page.getByRole("button", { name: "開始解析" })],
    ]);
    await snap(page, "p9-w7-screen-06-import-step1.png");
    await page.getByRole("tab", { name: "貼上文字" }).click();
    await page.getByLabel("需求文字").fill(brd());
    await page.getByLabel("來源名稱").fill(`w7-screen-${RUN}.md`);
    await page.getByLabel("格式").selectOption("MARKDOWN");
    await page.getByLabel("執行路徑").fill(dir);
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "畫面 6 步驟 2", [
      ["步驟 2 卡：結構預覽與編輯", page.getByText("結構預覽與編輯", { exact: true })],
      ["樹狀預覽：專案", page.getByTestId("import-step2").getByText(/QA W7 畫面/)],
      ["signoff 警示（signed_off=false）", page.getByText(/signed_off=false|未 signoff|待人工 signoff/).first()],
      ["按鈕：signoff 審批", page.getByRole("button", { name: /signoff/ }).first()],
      ["按鈕：放棄", page.getByRole("button", { name: "放棄" })],
      ["按鈕：確認匯入", page.getByRole("button", { name: "確認匯入" })],
    ]);
    await snap(page, "p9-w7-screen-06-import-step2.png", { tall: true });
    const id = new URL(page.url()).searchParams.get("id");
    if (id) await call(request, "operator", "POST", `/api/v1/import/${id}/reject`);
  });

  test("畫面 7 專案執行：標題與副標、執行控制、執行進度、DAG 依賴視覺化、即時日誌（SSE 串流）、待審核項目", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto(`/projects/${done.projectId}/execute`);
    await expect(page.getByRole("heading", { name: `專案執行：${done.name}` })).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "畫面 7", [
      ["副標：漸進式自治 · DAG 排程 · 斷點續行", page.getByText("漸進式自治 · DAG 排程 · 斷點續行")],
      ["卡：執行控制", page.getByText("執行控制", { exact: true })],
      ["執行控制：自治等級", page.getByLabel("自治等級")],
      ["執行控制：Token 預算", page.getByText(/Token 預算/)],
      ["執行控制：執行範圍", page.getByText("執行範圍", { exact: true })],
      ["按鈕：啟動執行", page.getByRole("button", { name: /啟動執行/ })],
      ["卡：執行進度", page.getByText("執行進度", { exact: true })],
      ["卡：DAG 依賴視覺化", page.getByText("DAG 依賴視覺化", { exact: true })],
      ["卡：即時日誌", page.getByText("即時日誌", { exact: true })],
      ["日誌標頭：SSE 串流", page.getByText(/SSE 串流/)],
      ["卡：待審核項目", page.getByText("待審核項目", { exact: true })],
    ]);
    await snap(page, "p9-w7-screen-07-execute.png", { tall: true });
  });

  test("畫面 8 專案監控：標題與時間範圍、四張指標卡、Token 使用趨勢、任務狀態分佈、執行時間分佈、執行日誌查詢、告警", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto(`/projects/${done.projectId}/monitor`);
    await expect(page.getByRole("heading", { name: `專案監控：${done.name}` })).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "畫面 8", [
      ["返回專案", page.getByRole("link", { name: /返回專案/ })],
      ["時間範圍下拉", page.getByLabel(/時間範圍/)],
      ["指標卡：完成率", page.getByText("完成率", { exact: true })],
      ["指標卡：任務成功率", page.getByText("任務成功率", { exact: true })],
      ["指標卡：重試率", page.getByText("重試率", { exact: true })],
      ["指標卡：Token 消耗", page.getByText("Token 消耗", { exact: true })],
      ["卡：Token 使用趨勢", page.getByText("Token 使用趨勢", { exact: true })],
      ["圖：token-trend-chart", page.getByTestId("token-trend-chart")],
      ["卡：任務狀態分佈", page.getByText("任務狀態分佈", { exact: true })],
      ["卡：執行時間分佈", page.getByText("執行時間分佈", { exact: true })],
      ["卡：執行日誌查詢", page.getByText("執行日誌查詢", { exact: true })],
      ["日誌等級下拉", page.getByLabel(/等級/).first()],
      ["卡：告警", page.getByText("告警", { exact: true })],
    ]);
    // 登記的差異（契約 §4.6 G-M1～G-M3）：多了 Agent 即時狀態卡、批次下拉；W7 另加「AISDLC_SDD 引擎」卡
    await expect.soft(page.getByTestId("agent-card"), "登記的增補：Agent 即時狀態卡").toBeVisible();
    await expect.soft(page.getByTestId("sdd-card"), "W7 增補：AISDLC_SDD 引擎卡").toBeVisible();
    await snap(page, "p9-w7-screen-08-monitor.png", { tall: true });
  });

  test("畫面 9 系統參數設定：標題、匯出／匯入設定、六個分類 tab、參數卡（控制項、重置）、測試連線、修改歷史、全部重置", async ({ page, request }) => {
    await signIn(page, request, "admin");
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "系統參數設定" })).toBeVisible(FIRST_LOAD);
    await expectAnchors(page, "畫面 9", [
      ["右側：匯出設定", page.getByRole("button", { name: /匯出設定/ })],
      ["右側：匯入設定", page.getByRole("button", { name: /匯入設定/ })],
      ["tab：模型", page.getByRole("tab", { name: /模型/ })],
      ["tab：Agent", page.getByRole("tab", { name: /Agent/ })],
      ["tab：執行", page.getByRole("tab", { name: /執行/ })],
      ["tab：監控", page.getByRole("tab", { name: /監控/ })],
      ["tab：AutoClaude", page.getByRole("tab", { name: /AutoClaude/ })],
      ["tab：SDD", page.getByRole("tab", { name: /SDD/ })],
      ["模型 tab：測試連線", page.getByRole("button", { name: /測試連線/ })],
      ["每列尾端的重置鈕", page.getByRole("button", { name: /重置/ })],
      ["卡：修改歷史", page.getByText("修改歷史", { exact: true })],
      ["底部：全部重置為預設值", page.getByRole("button", { name: /全部重置為預設值/ })],
    ]);
    await snap(page, "p9-w7-screen-09-settings.png", { tall: true });
  });
});
