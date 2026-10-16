import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import { DEFECTS_OPEN, E2E_ROOT, NEEDS_BRIDGE, bootstrapSettings, call, createFixture, dataOf, ensureQuota, getRun, poll, signIn, waitRun, type Fixture } from "./realBackend";

/**
 * W5 複驗：無障礙（UI-A11Y-01／02／03；DEF-AC-004／005 的複驗）——真瀏覽器對真後端（e2e profile）＋真 Bridge＋aisdlc-mock-claude。
 *  A. axe-core 4.x（WCAG 2.0／2.1 A／AA）掃 W4 報告 §15.3 的 11 頁（登入、總覽、專案列表、新建專案表單、專案詳情、目標詳情、任務詳情、
 *     執行頁、監控頁、設定頁、匯入頁），另加三個資料豐富的狀態（已刪除清單、執行頁暫停中的審核卡、執行頁完成後的日誌與 DAG）。
 *     W4 的結果：310 個違規節點（color-contrast 257、label-content-name-mismatch 31、svg-img-alt 18、list 1、listitem 3）；這裡要求 0。
 *  B. 鍵盤走查（UI-A11Y-02：Tab／Enter／Esc、拖曳的鍵盤替代）：不碰滑鼠完成登入、跳到主要內容、開關對話框並歸還焦點、
 *     目標排序（dnd-kit 鍵盤感測器）、分頁籤方向鍵、執行頁審核（Enter 開對話框、Esc 取消不送出、Enter 確認）、通知鈴的 Popover。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const MOCK_CLAUDE = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");
const nm = (base: string) => `${base} ${RUN}`;

let done: Fixture; // 已完成的夾具（專案／目標／任務詳情、執行頁、監控頁）
let paused: Fixture; // 等級 1：暫停中、有待決審核卡
let pausedRun = "";

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  test.setTimeout(300_000);
  await bootstrapSettings(request, MOCK_CLAUDE);
  expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);
  await ensureQuota(request, "operator", 60);
  done = await createFixture(request, { name: nm("QA W5 無障礙 完成"), kind: "A", level: 4 });
  const r = await call(request, "operator", "POST", `/api/v1/projects/${done.projectId}/execute`, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
  expect(r.status).toBe(201);
  await waitRun(request, dataOf<{ id: string }>(r).id, ["COMPLETED"], 90_000);
  paused = await createFixture(request, { name: nm("QA W5 無障礙 暫停"), kind: "B", level: 1 });
  const p = await call(request, "operator", "POST", `/api/v1/projects/${paused.projectId}/execute`, { autonomyLevel: 1, tokenBudget: 100000, scope: { mode: "ALL" } });
  expect(p.status).toBe(201);
  pausedRun = dataOf<{ id: string }>(p).id;
  await poll(
    () => getRun(request, pausedRun),
    (x) => x.status === "PAUSED" && (x.pendingReviews ?? []).length > 0,
    "批次 PAUSED 且審核項已建立",
    90_000,
  );
});

test.afterAll(async ({ request }) => {
  if (pausedRun) await call(request, "operator", "POST", `/api/v1/executions/${pausedRun}/cancel`);
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 45);
});

const clickAndScan = async (page: Page, label: string) => expectNoA11yViolations(page, label);

test.describe("無障礙（真後端）：axe 掃 11 頁＋資料豐富狀態", () => {
  test.setTimeout(240_000);

  test("登入頁、總覽、專案列表、新建專案表單：零違規", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "登入 AISDLC Console" })).toBeVisible(FIRST_LOAD);
    await clickAndScan(page, "1. 登入頁");
    await signIn(page, request, "operator");
    await page.goto("/");
    await expect(page.getByTestId("kpi-grid")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("kpi-week-done")).toHaveText(/^\d+$/, FIRST_LOAD);
    await clickAndScan(page, "2. 總覽頁（真資料）");
    await page.goto("/projects");
    await expect(page.getByTestId("project-list")).toBeVisible(FIRST_LOAD);
    await clickAndScan(page, "3. 專案列表");
    await page.getByRole("button", { name: "新建專案" }).click();
    await expect(page.getByRole("dialog", { name: "新建專案" })).toBeVisible();
    await expect(page.locator(".w-md-editor").first()).toBeVisible();
    await clickAndScan(page, "4. 新建專案表單（Dialog，含 Markdown 編輯器）");
    await page.keyboard.press("Escape");
    await page.getByTestId("deleted-filter").click();
    await expect(page.getByTestId("deleted-hint")).toBeVisible(FIRST_LOAD);
    await clickAndScan(page, "5. 專案列表（已刪除檢視）");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("專案詳情、目標詳情、任務詳情（含執行歷史與日誌）、執行頁（完成後的日誌與 DAG）、監控頁（圖表、告警、日誌）：零違規", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    await signIn(page, request, "operator");
    await page.goto(`/projects/${done.projectId}`);
    await expect(page.getByTestId("project-title")).toHaveText(done.name, FIRST_LOAD);
    await expect(page.getByTestId("goal-row")).toHaveCount(2);
    await clickAndScan(page, "6. 專案詳情");
    await page.goto(`/projects/${done.projectId}/goals/${done.goalIds[0]}`);
    await expect(page.getByTestId("goal-title")).toHaveText("基礎", FIRST_LOAD);
    await expect(page.getByTestId("task-row")).toHaveCount(2);
    await clickAndScan(page, "7. 目標詳情");
    await page.goto(`/projects/${done.projectId}/goals/${done.goalIds[0]}/tasks/${done.taskIds[0]}`);
    await expect(page.getByTestId("task-title")).toHaveText("初始化", FIRST_LOAD);
    await clickAndScan(page, "8. 任務詳情（執行歷史與日誌）");
    await page.goto(`/projects/${done.projectId}/execute`);
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", FIRST_LOAD);
    await expect(page.getByTestId("log-line").first()).toBeVisible();
    await clickAndScan(page, "9. 執行頁（完成：日誌與 DAG）");
    await page.goto(`/projects/${done.projectId}/monitor`);
    await expect(page.getByRole("heading", { name: `專案監控：${done.name}` })).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("token-trend-chart")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("task-trend-chart")).toBeVisible();
    await clickAndScan(page, "10. 監控頁（圖表、告警、日誌）");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("執行頁（暫停中、待決審核卡）、設定頁（admin，50 鍵）、匯入頁（三個分頁）：零違規", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    await signIn(page, request, "operator");
    await page.goto(`/projects/${paused.projectId}/execute`);
    await expect(page.getByTestId("review-row")).toHaveCount(1, FIRST_LOAD);
    await expect(page.getByTestId("run-status")).toContainText("已暫停");
    await clickAndScan(page, "11. 執行頁（暫停中、審核卡）");
    await signIn(page, request, "admin");
    await page.goto("/settings");
    await expect(page.getByTestId("settings-panel")).toBeVisible(FIRST_LOAD);
    await clickAndScan(page, "12. 設定頁（模型分頁）");
    await page.getByRole("tab", { name: "執行", exact: true }).click();
    await expect(page.getByRole("heading", { name: "執行設定" })).toBeVisible();
    await clickAndScan(page, "13. 設定頁（執行分頁）");
    await signIn(page, request, "operator");
    await page.goto("/import");
    await expect(page.getByTestId("import-step1")).toBeVisible(FIRST_LOAD);
    await clickAndScan(page, "14. 匯入頁（上傳檔案分頁）");
    await page.getByRole("tab", { name: "貼上文字" }).click();
    await expect(page.getByLabel("需求文字")).toBeVisible();
    await clickAndScan(page, "15. 匯入頁（貼上文字分頁）");
    await page.getByRole("tab", { name: "歷史記錄" }).click();
    await expect(page.getByTestId("import-history-panel")).toBeVisible();
    await clickAndScan(page, "16. 匯入頁（歷史記錄分頁）");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});

test.describe("鍵盤走查（UI-A11Y-02）：不碰滑鼠完成 Tab／Enter／Esc 與拖曳的鍵盤替代", () => {
  test.setTimeout(240_000);

  test("登入：Tab 依序到使用者名稱→密碼→登入鈕，Enter 送出", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "登入 AISDLC Console" })).toBeVisible(FIRST_LOAD);
    await page.getByLabel("使用者名稱").focus();
    await page.keyboard.type("operator");
    await page.keyboard.press("Tab");
    await expect(page.getByLabel("密碼")).toBeFocused();
    await page.keyboard.type(["Operator", "Dev2026"].join("#"));
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "登入" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("user-badge")).toContainText("operator", FIRST_LOAD);
  });

  test("跳到主要內容：第一個 Tab 停在連結，Enter 後下一個 Tab 進入內容區（不是又繞過整個頂列與側欄）；對話框：Tab 不離開、Esc 關閉並把焦點還給觸發鈕", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto("/projects");
    await expect(page.getByTestId("project-list")).toBeVisible(FIRST_LOAD);
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "跳到主要內容" });
    await expect(skip).toBeFocused();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Tab");
    const inContent = await page.evaluate(() => !!document.activeElement?.closest("#main-content"));
    expect(inContent, `Enter 之後的 Tab 應落在內容區；實際焦點＝${await page.evaluate(() => document.activeElement?.outerHTML.slice(0, 80))}`).toBe(true);

    // 對話框：以鍵盤開、Tab 12 次焦點不離開對話框（焦點陷阱）、Esc 關閉、焦點回到「新建專案」
    const trigger = page.getByRole("button", { name: "新建專案" });
    await trigger.focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog", { name: "新建專案" });
    await expect(dialog).toBeVisible();
    for (let i = 0; i < 12; i += 1) {
      await page.keyboard.press("Tab");
      expect(await page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]')), `第 ${i + 1} 次 Tab 後焦點仍在對話框內`).toBe(true);
    }
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0); // 焦點是否回到觸發鈕：見下一支（DEF-AC-011）
  });

  test("對話框關閉後焦點回到觸發的按鈕（WCAG 2.4.3 焦點順序；DEF-AC-011，P3，test.fail 釘住）：新建專案、新增目標、刪除專案確認、審核確認四個對話框 Esc 關閉後的焦點落點", async ({
    page,
    request,
  }) => {
    test.fail(DEFECTS_OPEN, "DEF-AC-011（P3）：以程式控制開啟的對話框關閉後焦點回到 <body>，鍵盤使用者要從頁首重新 Tab");
    const f = await createFixture(request, { name: nm("QA W5 焦點歸還"), kind: "A", level: 4 });
    await signIn(page, request, "operator");
    const where = () =>
      page.evaluate(() => {
        const a = document.activeElement;
        return a
          ? `${a.tagName.toLowerCase()}${a.getAttribute("aria-label") ? `[${a.getAttribute("aria-label")}]` : ""}${a === document.body ? "（body）" : `「${(a.textContent ?? "").trim().slice(0, 12)}」`}`
          : "(none)";
      });
    const results: Array<{ dialog: string; trigger: string; focusedAfterEsc: string; ok: boolean }> = [];
    const probe = async (dialogName: string, trigger: ReturnType<Page["locator"]>, dialogLocator: ReturnType<Page["locator"]>) => {
      await trigger.focus();
      const triggerAt = await where();
      await page.keyboard.press("Enter");
      await expect(dialogLocator).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(dialogLocator).toHaveCount(0);
      await page.waitForTimeout(250); // 讓 Radix 的 onCloseAutoFocus 跑完
      const isBack = await trigger.evaluate((el) => el === document.activeElement);
      results.push({ dialog: dialogName, trigger: triggerAt, focusedAfterEsc: await where(), ok: isBack });
    };
    await page.goto("/projects");
    await expect(page.getByTestId("project-list")).toBeVisible(FIRST_LOAD);
    await probe("新建專案", page.getByRole("button", { name: "新建專案" }), page.getByRole("dialog", { name: "新建專案" }));
    await page.goto(`/projects/${f.projectId}`);
    await expect(page.getByTestId("goal-row")).toHaveCount(2, FIRST_LOAD);
    await probe("新增目標", page.getByRole("button", { name: "新增目標" }), page.getByRole("dialog", { name: "新建目標" }));
    await probe("刪除專案確認", page.getByRole("button", { name: "刪除專案" }), page.getByRole("dialog", { name: "刪除專案" }));
    await page.goto(`/projects/${paused.projectId}/execute`);
    await expect(page.getByTestId("review-row")).toHaveCount(1, FIRST_LOAD);
    await probe("審核確認", page.getByTestId("review-approve"), page.getByTestId("review-dialog"));
    console.log(`[a11y] 對話框 Esc 關閉後的焦點：${results.map((r) => `${r.dialog}：觸發鈕 ${r.trigger} → 焦點 ${r.focusedAfterEsc}（${r.ok ? "已歸還" : "未歸還"}）`).join("；")}`);
    expect(
      results.filter((r) => !r.ok),
      "Esc 關閉後焦點沒有回到觸發鈕的對話框",
    ).toEqual([]);
  });

  test("目標排序的鍵盤替代：拖曳把手 Space 拾起、方向鍵移動、Space 放下 → PUT reorder、順序保持（後端 sortOrder 為準）", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA W5 鍵盤排序"), kind: "A", level: 4 }); // 目標：基礎、核心
    await signIn(page, request, "operator");
    await page.goto(`/projects/${f.projectId}`);
    await expect(page.getByTestId("goal-row")).toHaveCount(2, FIRST_LOAD);
    const rows = page.getByTestId("goal-row");
    await expect(rows.nth(0)).toContainText("基礎");
    const handle = page.getByRole("button", { name: "拖曳排序：核心" });
    await handle.focus();
    // dnd-kit 的鍵盤感測器在起始鍵之後的下一個 tick 才掛上 keydown 監聽，按鍵之間要留一點時間（人按鍵本來就慢）
    await page.keyboard.press("Space");
    await page.waitForTimeout(250);
    await page.keyboard.press("ArrowUp");
    await page.waitForTimeout(250);
    await page.keyboard.press("Space");
    await expect(page.getByRole("status").filter({ hasText: "已更新目標順序" })).toBeVisible();
    await expect(rows.nth(0)).toContainText("核心");
    await page.reload();
    await expect(page.getByTestId("goal-row").nth(0)).toContainText("核心", FIRST_LOAD);
    const order = dataOf<{ goals: Array<{ name: string }> }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`)).goals.map((g) => g.name);
    expect(order, "後端的目標順序").toEqual(["核心", "基礎"]);
    // Esc 取消：拾起後按 Esc 不改順序
    await page.getByRole("button", { name: "拖曳排序：基礎" }).focus();
    await page.keyboard.press("Space");
    await page.waitForTimeout(250);
    await page.keyboard.press("ArrowUp");
    await page.waitForTimeout(250);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(250);
    await expect(page.getByTestId("goal-row").nth(0)).toContainText("核心");
    await snap(page, "p9-keyboard-reorder.png");
  });

  test("分頁籤：方向鍵／Home／End 切換並移動焦點（設定頁六個分頁、匯入頁三個分頁）", async ({ page, request }) => {
    await signIn(page, request, "admin");
    await page.goto("/settings");
    await expect(page.getByTestId("settings-panel")).toBeVisible(FIRST_LOAD);
    const tabs = page.getByRole("tab");
    await expect(tabs).toHaveCount(6);
    await tabs.first().focus();
    await expect(tabs.first()).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("ArrowRight");
    await expect(tabs.nth(1)).toBeFocused();
    await expect(tabs.nth(1)).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("heading", { name: "Agent設定" })).toBeVisible();
    await page.keyboard.press("End");
    await expect(tabs.nth(5)).toBeFocused();
    await expect(page.getByRole("heading", { name: "SDD設定" })).toBeVisible();
    await page.keyboard.press("Home");
    await expect(tabs.first()).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("Tab"); // 離開 tablist：進入分頁內容（第一個可聚焦的控制項）
    expect(await page.evaluate(() => !!document.activeElement?.closest('[role="tabpanel"]'))).toBe(true);

    await signIn(page, request, "operator");
    await page.goto("/import");
    await expect(page.getByTestId("import-step1")).toBeVisible(FIRST_LOAD);
    const importTabs = page.getByRole("tab");
    await importTabs.first().focus();
    await page.keyboard.press("ArrowRight");
    await expect(importTabs.nth(1)).toHaveAttribute("aria-selected", "true");
    await expect(page.getByLabel("需求文字")).toBeVisible();
    await page.keyboard.press("End");
    await expect(page.getByTestId("import-history-panel")).toBeVisible();
  });

  test("執行頁審核卡：鍵盤 Enter 開確認對話框、Esc 取消（不送出決定）、再 Enter 確認；通知鈴 Enter 開 Popover、Esc 關閉並歸還焦點", async ({ page, request }) => {
    await signIn(page, request, "operator");
    await page.goto(`/projects/${paused.projectId}/execute`);
    await expect(page.getByTestId("review-row")).toHaveCount(1, FIRST_LOAD);
    const approve = page.getByTestId("review-approve");
    await approve.focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByTestId("review-dialog");
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    expect((await getRun(request, pausedRun)).pendingReviews ?? [], "Esc 沒有送出任何決定").toHaveLength(1);
    await approve.focus(); // Esc 之後焦點是否還在決定鈕上屬 DEF-AC-011，本情境不依賴它
    await page.keyboard.press("Enter");
    await expect(dialog).toBeVisible();
    await page.getByTestId("review-confirm").focus();
    await page.keyboard.press("Enter");
    await expect(dialog).toHaveCount(0);
    await poll(
      () => getRun(request, pausedRun),
      (r) => (r.completedSteps ?? 0) >= 2 && ((r.pendingReviews ?? []).length > 0 || r.status !== "PAUSED"),
      "通過後續跑第二個任務並在下一個審核點暫停",
      90_000,
    );

    // 通知鈴：Enter 開、Esc 關、焦點回到鈴
    const bell = page.getByTestId("bell-trigger");
    await bell.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("notification-panel")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("notification-panel")).toHaveCount(0);
    await expect(bell).toBeFocused();
  });
});
