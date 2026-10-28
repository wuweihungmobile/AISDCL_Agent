import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

import { HELP_PAGES, HELP_ROUTES } from "../../lib/help/registry";
import { expectNoA11yViolations } from "./a11y";
import { collectConsoleErrors, compose, installApiMock, shellHandler, signInAs, type MockCall, type MockHandler } from "./mockApi";

/**
 * 每頁說明（TCS-PageHelp-20261027 §5.6；R-PH-22、R-PH-26～R-PH-28；載具 E2〔Playwright route mock〕，輪 1b 建）：真瀏覽器才量得到的東西——
 *  - AT-PH-06-3-1、06-3-2、06-3-E-1：請求計數（每條路由各點一次「本頁說明」：議題中心恰一個唯讀 `GET /api/v1/issues?limit=1`，其餘路由零個；VIEWER 三次開啟各一個；新增請求全程無寫入、無 /si/ 路徑）；
 *  - AT-PH-07-1-2：鍵盤（Tab 到鈕、Enter 與空白鍵開、Esc 與關閉鈕關，焦點都回到該鈕）；
 *  - AT-PH-07-3-1、07-3-2、07-3-E-1：窄螢幕（390×844 對話框不超出視窗、頂列不橫向捲動、< 768 文字隱藏、兩張表逐列堆疊）；
 *  - AT-PH-07-4-1、07-4-2、07-4-3：axe（關閉態、開啟態、展開「全站共通」後；1440×900 與 390×844；WCAG 2.0／2.1 A／AA 零違規）。
 * 後端以本檔自帶的 `GET /api/v1/issues` 處理器代替（不改 mockApi.ts、不改既有 spec）：回黃金檔的 legend（真 CLI 輸出）；頂列的兩個輪詢端點由 `shellHandler` 供給，其餘 `/api/v1/**` 由 `installApiMock` 回 404。
 * 請求計數用**新穎性規則**（D-PH-13）：「新增請求」＝點擊之後出現、且鍵在點擊之前沒出現過的請求；鍵＝（方法, 路徑），唯一例外是 `/api/v1/issues`，其鍵再含排序後的查詢串
 * （否則議題中心頁自己的清單請求會把詞表請求「吃掉」）；頁面自己的輪詢與頂列輪詢因路徑在點擊前已出現過而自然排除。點擊前的基線＝頁面載入、鈕可見後固定再等 1,000 毫秒（不用 networkidle：多數路由到不了），
 * 點擊後的觀察窗＝對話框出現後再等 500 毫秒。
 * 詞表請求另按**路由獨立**計（SCG-4 一審 F-05）：從進路由前的 `calls.length` 起算、涵蓋頁面載入到對話框關閉的全程；議題中心恰一個、其餘路由零個。新穎性規則的鍵跨路由累積（為了把頂列輪詢排除），
 * 單靠它，某路由「載入時預取詞表」會被點擊前的基線吃掉、只在排最後的 /issues 路由間接現形；逐路由計才讓每條路由自己守住自己。
 * 本機重跑：`$env:E2E_MODE="standalone"; npm run build; npx playwright test tests/e2e/page-help.mock.spec.ts --output <各自目錄>`（CI 以 standalone 產物跑：`playwright test mock.spec`）。
 */

const LEGEND = (JSON.parse(readFileSync(path.join(process.cwd(), "tests", "fixtures", "si", "A.camel.json"), "utf-8")) as { issues: { legend: unknown } }).issues.legend;

/** `GET /api/v1/issues`（任何查詢串）回黃金檔議題頁的形狀：空清單、整本帳的計數全 0、legend 取自黃金檔。 */
const issuesLegend: MockHandler = (call) => {
  if (call.method !== "GET" || call.path !== "/api/v1/issues") return undefined;
  return {
    data: {
      schemaRev: 1,
      kind: "issues",
      generatedAt: "2026-10-27T10:00:00+08:00",
      headSha: "0".repeat(40),
      items: [],
      nextSince: null,
      truncated: false,
      ne: [],
      problems: [],
      legend: LEGEND,
      summary: { total: 0, byStatus: {}, byTab: { 待處理: 0, 待您決定: 0, 已完成: 0 }, unmapped: 0 },
    },
  };
};

const BACKEND = compose(shellHandler(), issuesLegend);
const concretePath = (template: string): string => template.replace("[projectId]", "p1").replace("[goalId]", "g1").replace("[taskId]", "t1");
const titleOf = (id: keyof typeof HELP_PAGES): string => `${HELP_PAGES[id]?.title}・本頁說明`;

/** 新穎性規則的鍵：（方法, 路徑）；`/api/v1/issues` 另含排序後的查詢串。 */
function noveltyKey(call: MockCall): string {
  if (call.path !== "/api/v1/issues") return `${call.method} ${call.path}`;
  const query = [...call.query.entries()].map(([key, value]) => `${key}=${value}`).sort();
  return `${call.method} ${call.path}?${query.join("&")}`;
}

/** 詞表請求：`GET /api/v1/issues`，查詢串恰 `limit=1`（頁面自己的清單請求帶 limit=100）。 */
const isLegendCall = (call: MockCall): boolean => call.method === "GET" && call.path === "/api/v1/issues" && call.query.toString() === "limit=1";
const describeCall = (call: MockCall): string => `${call.method} ${call.path}${call.query.toString() ? `?${call.query.toString()}` : ""}`;

/** 這條路由自己的詞表請求：從 `since`（進路由前的 calls.length）起算、含頁面載入的全程，不與別的路由累積。議題中心恰一個，其餘路由零個。 */
const legendCallsSince = (calls: MockCall[], since: number): string[] => calls.slice(since).filter(isLegendCall).map(describeCall);
const expectedLegendCalls = (id: keyof typeof HELP_PAGES): string[] => (id === "issues" ? ["GET /api/v1/issues?limit=1"] : []);

/** 一路按 Tab 直到焦點落在符合選擇器的元素上（最多 80 次；找不到就失敗，不空轉；沿 issues.mock.spec.ts）。 */
async function tabUntil(page: Page, selector: string): Promise<void> {
  for (let i = 0; i < 80; i += 1) {
    await page.keyboard.press("Tab");
    if (await page.evaluate((sel) => document.activeElement?.matches(sel) ?? false, selector)) return;
  }
  throw new Error(`按 Tab 80 次仍沒有把焦點帶到 ${selector}`);
}

/** 登入、掛假後端、設視窗（須在 goto 之前）、前往路徑，等頂列出現。 */
async function visit(page: Page, route: string, options: { role?: "ADMIN" | "OPERATOR" | "VIEWER"; width?: number; height?: number } = {}): Promise<{ calls: MockCall[] }> {
  if (options.width !== undefined) await page.setViewportSize({ width: options.width, height: options.height ?? 900 });
  await signInAs(page, options.role ?? "OPERATOR");
  const mock = await installApiMock(page, BACKEND);
  await page.goto(route);
  await expect(page.locator('[data-region="top"]')).toBeVisible({ timeout: 60_000 });
  return mock;
}

const helpButton = (page: Page): Locator => page.getByTestId("page-help-open");
const helpDialog = (page: Page): Locator => page.getByTestId("page-help-dialog");

/** 對話框開啟後等內容就緒：議題中心頁等四群詞表出現。 */
async function openHelp(page: Page, id: keyof typeof HELP_PAGES): Promise<Locator> {
  await helpButton(page).click();
  const dialog = page.getByRole("dialog", { name: titleOf(id) });
  await expect(dialog).toBeVisible();
  if (id === "issues") for (const group of ["statuses", "results", "sources", "severities"]) await expect(dialog.getByTestId(`page-help-legend-${group}`)).toBeVisible();
  return dialog;
}

/**
 * 在已載入的頁面上點「本頁說明」並觀察新增請求（D-PH-13）：先固定等 1,000 毫秒取基線，點擊、等對話框出現，再等 500 毫秒；
 * 回傳新增請求與點擊之後的瀏覽器錯誤（頁面自己載入時的雜訊不算）。
 */
async function clickAndObserve(page: Page, calls: MockCall[], errors: string[], id: keyof typeof HELP_PAGES): Promise<{ added: MockCall[]; fresh: string[] }> {
  await page.waitForTimeout(1000);
  const before = new Set(calls.map(noveltyKey));
  const mark = calls.length;
  const errorMark = errors.length;
  await openHelp(page, id);
  await page.waitForTimeout(500);
  return { added: calls.slice(mark).filter((call) => !before.has(noveltyKey(call))), fresh: errors.slice(errorMark) };
}

/** 本檔登記為「已寫」的路由樣板（說明 id 在 HELP_PAGES 內者）。 */
const writtenRoutes = (): Array<[template: string, id: keyof typeof HELP_PAGES]> =>
  Object.entries(HELP_ROUTES)
    .filter(([, id]) => HELP_PAGES[id] !== undefined)
    .map(([template, id]): [string, keyof typeof HELP_PAGES] => [template, id]);

test.describe("每頁說明（route mock）", () => {
  test.setTimeout(180_000);

  test("AT_PH_06_3_1 每條路由各點一次：待寫頁的路由無鈕；已寫頁的路由議題中心恰一個新增請求 GET /api/v1/issues?limit=1、其餘零個；每條路由自己的詞表請求（含頁面載入的全程）也是議題中心恰一個、其餘零個；對話框名稱＝<頁名>・本頁說明；點擊到對話框出現期間無 pageerror", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    const { calls } = await installApiMock(page, BACKEND);
    let clicked = 0;
    let pendingRoutes = 0;
    for (const [template, id] of Object.entries(HELP_ROUTES)) {
      const routeStart = calls.length;
      await page.goto(concretePath(template));
      await expect(page.locator('[data-region="top"]'), `${template} 載入`).toBeVisible({ timeout: 60_000 });
      if (HELP_PAGES[id] === undefined) {
        await page.waitForTimeout(1000);
        await expect(helpButton(page), `${template}（${id}）是待寫頁：不渲染鈕`).toHaveCount(0);
        pendingRoutes += 1;
        continue;
      }
      await expect(helpButton(page), `${template}（${id}）已寫：渲染鈕`).toBeVisible({ timeout: 60_000 });
      const { added, fresh } = await clickAndObserve(page, calls, errors, id);
      expect(added.map(describeCall), `${template} 的新增請求`).toEqual(expectedLegendCalls(id));
      expect(
        fresh.filter((message) => message.startsWith("pageerror")),
        `${template} 點擊期間的 pageerror`,
      ).toEqual([]);
      await page.keyboard.press("Escape");
      await expect(helpDialog(page)).toHaveCount(0);
      expect(legendCallsSince(calls, routeStart), `${template} 全程（含頁面載入）的詞表請求：不得在非議題中心路由預取`).toEqual(expectedLegendCalls(id));
      clicked += 1;
    }
    expect(clicked + pendingRoutes, "防反空轉：HELP_ROUTES 的每條路由都走過（已寫頁點過、待寫頁驗證無鈕）").toBe(Object.keys(HELP_ROUTES).length);
    expect(clicked, "防反空轉：每一條已寫頁的路由都真的點過").toBe(writtenRoutes().length);
  });

  test("AT_PH_06_3_2 VIEWER 在 /issues：開啟→Esc 關閉→開啟→關閉→開啟（三次開啟）：詞表請求共 3 個、查詢串皆恰 limit=1；VIEWER 的請求不被前端擋；每次開啟後四群詞表皆出現", async ({ page }) => {
    const { calls } = await visit(page, "/issues", { role: "VIEWER" });
    await expect(helpButton(page)).toBeVisible({ timeout: 60_000 });
    await page.waitForTimeout(1000);
    for (let round = 1; round <= 3; round += 1) {
      const dialog = await openHelp(page, "issues");
      await page.waitForTimeout(300);
      expect(calls.filter(isLegendCall), `第 ${round} 次開啟後累計的詞表請求`).toHaveLength(round);
      if (round === 1) await page.keyboard.press("Escape");
      else await dialog.getByRole("button", { name: "關閉" }).click();
      await expect(helpDialog(page)).toHaveCount(0);
    }
    expect(calls.filter(isLegendCall).map(describeCall)).toEqual(Array(3).fill("GET /api/v1/issues?limit=1"));
  });

  test("AT_PH_06_3_E_1 新增請求（點擊後才出現的新鍵，不含頁面載入時自己發的請求）全程：沒有非 GET、沒有 /si/ 路徑、除議題詞表請求外沒有其他新增請求；每條路由自己的詞表請求（含頁面載入的全程）議題中心恰一個、其餘零個，VIEWER 每次開啟各恰一個", async ({
    page,
  }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    const { calls } = await installApiMock(page, BACKEND);
    const novel: MockCall[] = [];
    let visited = 0;
    for (const [template, id] of writtenRoutes()) {
      const routeStart = calls.length;
      await page.goto(concretePath(template));
      await expect(helpButton(page), `${template} 有鈕`).toBeVisible({ timeout: 60_000 });
      const { added } = await clickAndObserve(page, calls, errors, id);
      novel.push(...added);
      await page.keyboard.press("Escape");
      await expect(helpDialog(page)).toHaveCount(0);
      expect(legendCallsSince(calls, routeStart), `${template} 全程（含頁面載入）的詞表請求：不得在非議題中心路由預取`).toEqual(expectedLegendCalls(id));
      visited += 1;
    }
    expect(visited, "防反空轉：每一條已寫頁的路由都走過").toBe(writtenRoutes().length);
    // VIEWER 三次開啟（這一輪的新增請求另累計）
    const viewer = await page.context().newPage();
    const viewerErrors = collectConsoleErrors(viewer);
    await signInAs(viewer, "VIEWER");
    const viewerMock = await installApiMock(viewer, BACKEND);
    await viewer.goto("/issues");
    await expect(helpButton(viewer)).toBeVisible({ timeout: 60_000 });
    for (let round = 1; round <= 3; round += 1) {
      const roundStart = viewerMock.calls.length;
      const { added } = await clickAndObserve(viewer, viewerMock.calls, viewerErrors, "issues");
      novel.push(...added);
      await viewer.keyboard.press("Escape");
      await expect(helpDialog(viewer)).toHaveCount(0);
      expect(legendCallsSince(viewerMock.calls, roundStart), `VIEWER 第 ${round} 次開啟的詞表請求（每次開啟各自重取，不被前一次的鍵吃掉）`).toEqual(["GET /api/v1/issues?limit=1"]);
    }
    expect(novel.length, "防反空轉：確實觀察到新增請求（議題中心的詞表請求）").toBeGreaterThanOrEqual(1);
    expect(novel.filter((call) => call.method !== "GET").map(describeCall), "沒有任何非 GET").toEqual([]);
    expect(novel.filter((call) => call.path.includes("/si/")).map(describeCall), "沒有 /si/ 路徑").toEqual([]);
    expect(novel.filter((call) => !isLegendCall(call)).map(describeCall), "除議題詞表請求外沒有其他新增請求").toEqual([]);
  });

  test("AT_PH_07_1_2 真瀏覽器鍵盤：Tab 到說明鈕（焦點環可見）、Enter 開啟且焦點進入對話框、Esc 關閉且焦點回到該鈕；再以空白鍵開、右上「關閉」鈕關，焦點同樣回到該鈕", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await visit(page, "/projects");
    const button = helpButton(page);
    await expect(button).toBeVisible({ timeout: 60_000 });
    await tabUntil(page, '[data-testid="page-help-open"]');
    await expect(button).toBeFocused();
    expect(await button.evaluate((el) => getComputedStyle(el).outlineStyle), ":focus-visible 焦點環可見").not.toBe("none");

    await page.keyboard.press("Enter");
    const dialog = helpDialog(page);
    await expect(dialog).toBeVisible();
    expect(await page.evaluate(() => document.querySelector('[data-testid="page-help-dialog"]')?.contains(document.activeElement) ?? false), "焦點進入對話框").toBe(true);
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(button, "Esc 關閉後焦點回到鈕").toBeFocused();

    await page.keyboard.press("Space");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "關閉" }).click();
    await expect(dialog).toHaveCount(0);
    await expect(button, "關閉鈕關閉後焦點回到鈕").toBeFocused();
    expect(errors, "瀏覽器主控台沒有 React 警告（含 hydration 不一致，鈕以 next/dynamic 載入）、被擋的請求或未捕捉例外").toEqual([]);
  });

  test("AT_PH_07_3_1 視窗 390×844 的 /issues、/projects、/settings：鈕可見可點；對話框完全在視窗內；對話框與 documentElement 都沒有橫向捲動；展開「全站共通」後仍成立", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await signInAs(page, "OPERATOR");
    await installApiMock(page, BACKEND);
    for (const [route, id] of [
      ["/issues", "issues"],
      ["/projects", "projects"],
      ["/settings", "settings"],
    ] as const) {
      await page.goto(route);
      await expect(helpButton(page), `${route} 的鈕`).toBeVisible({ timeout: 60_000 });
      const dialog = await openHelp(page, id);
      const check = async (stage: string) => {
        const box = await dialog.boundingBox();
        expect(box, `${route} ${stage}：對話框有版面`).not.toBeNull();
        if (box === null) return;
        expect(box.x, `${route} ${stage} x`).toBeGreaterThanOrEqual(0);
        expect(box.x + box.width, `${route} ${stage} 右緣`).toBeLessThanOrEqual(390);
        expect(box.y, `${route} ${stage} y`).toBeGreaterThanOrEqual(0);
        expect(box.y + box.height, `${route} ${stage} 下緣`).toBeLessThanOrEqual(844);
        const overflow = await dialog.evaluate((el) => ({ dialog: el.scrollWidth - el.clientWidth, document: document.documentElement.scrollWidth - document.documentElement.clientWidth }));
        expect(overflow.dialog, `${route} ${stage}：對話框 scrollWidth ≤ clientWidth`).toBeLessThanOrEqual(0);
        expect(overflow.document, `${route} ${stage}：documentElement scrollWidth ≤ clientWidth`).toBeLessThanOrEqual(0);
      };
      await check("開啟");
      await dialog.getByText("全站共通", { exact: true }).click();
      await expect(page.getByTestId("page-help-common")).toHaveJSProperty("open", true);
      await check("展開全站共通");
      await page.keyboard.press("Escape");
      await expect(helpDialog(page)).toHaveCount(0);
    }
  });

  test("AT_PH_07_3_2 視窗 390×844、767×900、768×900：390 時頂列與 documentElement 沒有橫向捲動；767 時鈕可見但文字節點被剪裁；768 時文字節點可見；兩種寬度都找得到名稱「本頁說明」的鈕", async ({
    page,
  }) => {
    await signInAs(page, "OPERATOR");
    await installApiMock(page, BACKEND);
    const textNode = () => helpButton(page).getByText("本頁說明", { exact: true });
    const sizeOf = async () => (await textNode().boundingBox()) ?? { width: 0, height: 0 };

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/projects");
    await expect(helpButton(page)).toBeVisible({ timeout: 60_000 });
    expect(
      await page.evaluate(() => {
        const top = document.querySelector('[data-region="top"]') as HTMLElement;
        return { top: top.scrollWidth - top.clientWidth, document: document.documentElement.scrollWidth - document.documentElement.clientWidth };
      }),
      "390：頂列與 documentElement 沒有橫向捲動",
    ).toEqual({ top: 0, document: 0 });

    await page.setViewportSize({ width: 767, height: 900 });
    await expect(page.getByRole("button", { name: "本頁說明" })).toBeVisible();
    const narrow = await sizeOf();
    expect(narrow.width, "767：文字節點被剪裁（sr-only）").toBeLessThanOrEqual(1);
    expect(narrow.height).toBeLessThanOrEqual(1);

    await page.setViewportSize({ width: 768, height: 900 });
    await expect(page.getByRole("button", { name: "本頁說明" })).toBeVisible();
    expect((await sizeOf()).width, "768：文字節點可見").toBeGreaterThan(1);
  });

  test("AT_PH_07_3_E_1 /projects：欄位表與第一張狀態表各取第一個資料列的三格：1440 並排（y 差 < 2）；390 逐列堆疊（y 嚴格遞增、x 相同）且每格有 data-label 小標", async ({ page }) => {
    const rowsOf = (dialog: Locator) => [
      dialog.getByTestId("page-help-fields").locator("tbody tr").first().locator("td"),
      dialog.getByTestId("page-help-states-projectStatus").locator("tbody tr").first().locator("td"),
    ];
    await signInAs(page, "OPERATOR");
    await installApiMock(page, BACKEND);
    for (const width of [1440, 390] as const) {
      await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
      await page.goto("/projects");
      await expect(helpButton(page)).toBeVisible({ timeout: 60_000 });
      const dialog = await openHelp(page, "projects");
      const heads = [
        ["欄位", "意思", "資料來源"],
        ["狀態", "意思", "通常的下一步"],
      ];
      for (const [tableIndex, cells] of rowsOf(dialog).entries()) {
        await expect(cells, `${width}：第 ${tableIndex + 1} 張表的第一列有三格`).toHaveCount(3);
        const boxes = [];
        for (let i = 0; i < 3; i += 1) {
          const cell = cells.nth(i);
          const box = await cell.boundingBox();
          expect(box, `${width}：表 ${tableIndex + 1} 第 ${i + 1} 格有版面`).not.toBeNull();
          boxes.push(box as { x: number; y: number; width: number; height: number });
          await expect(cell).toHaveAttribute("data-label", heads[tableIndex][i]);
          if (width === 390) {
            const before = await cell.evaluate((el) => getComputedStyle(el, "::before").content);
            expect(before, `${width}：表 ${tableIndex + 1} 第 ${i + 1} 格以 ::before 呈現欄名`).toContain(heads[tableIndex][i]);
          }
        }
        if (width === 1440) {
          expect(Math.abs(boxes[0].y - boxes[1].y), "1440：第 1、2 格並排").toBeLessThan(2);
          expect(Math.abs(boxes[1].y - boxes[2].y), "1440：第 2、3 格並排").toBeLessThan(2);
        } else {
          expect(boxes[1].y, "390：第 2 格在第 1 格下方").toBeGreaterThan(boxes[0].y);
          expect(boxes[2].y, "390：第 3 格在第 2 格下方").toBeGreaterThan(boxes[1].y);
          expect(Math.abs(boxes[0].x - boxes[1].x), "390：同左緣").toBeLessThan(1);
          expect(Math.abs(boxes[1].x - boxes[2].x), "390：同左緣").toBeLessThan(1);
        }
      }
      await page.keyboard.press("Escape");
    }
  });

  // axe：六種組合（/issues、/projects/p1、/settings × 1440×900、390×844）；待寫頁的路由跳過並斷言其無鈕
  const AXE_ROUTES = ["/issues", "/projects/p1", "/settings"] as const;
  const AXE_VIEWPORTS = [
    { width: 1440, height: 900 },
    { width: 390, height: 844 },
  ] as const;

  async function axeSweep(page: Page, stage: "closed" | "open" | "expanded", label: string): Promise<void> {
    let scanned = 0;
    await signInAs(page, "OPERATOR");
    await installApiMock(page, BACKEND);
    for (const route of AXE_ROUTES) {
      for (const viewport of AXE_VIEWPORTS) {
        await page.setViewportSize(viewport);
        await page.goto(route);
        await expect(page.locator('[data-region="top"]')).toBeVisible({ timeout: 60_000 });
        const id = HELP_ROUTES[route === "/projects/p1" ? "/projects/[projectId]" : route];
        const name = `${label}：${route} ${viewport.width}×${viewport.height}`;
        if (HELP_PAGES[id] === undefined) {
          await page.waitForTimeout(1000);
          await expect(helpButton(page), `${name}：待寫頁沒有鈕`).toHaveCount(0);
          continue;
        }
        await expect(helpButton(page)).toBeVisible({ timeout: 60_000 });
        if (stage !== "closed") {
          const dialog = await openHelp(page, id);
          if (stage === "expanded") {
            await dialog.getByText("全站共通", { exact: true }).click();
            await expect(page.getByTestId("page-help-common")).toHaveJSProperty("open", true);
          }
        }
        await expectNoA11yViolations(page, name);
        scanned += 1;
      }
    }
    expect(scanned, "防反空轉：至少掃了 /issues 與 /settings 兩頁的兩種視窗").toBeGreaterThanOrEqual(4);
  }

  test("AT_PH_07_4_1 axe 關閉態（鈕在頂列）：三條路由 × 兩種視窗零違規", async ({ page }) => {
    await axeSweep(page, "closed", "關閉態");
  });

  test("AT_PH_07_4_2 axe 開啟態（對話框顯示、全站共通收合）：三條路由 × 兩種視窗零違規", async ({ page }) => {
    await axeSweep(page, "open", "開啟態");
  });

  test("AT_PH_07_4_3 axe 展開「全站共通」後：三條路由 × 兩種視窗零違規（收合的內容在展開前不會被掃到，所以另掃一次）", async ({ page }) => {
    await axeSweep(page, "expanded", "展開全站共通");
  });
});
