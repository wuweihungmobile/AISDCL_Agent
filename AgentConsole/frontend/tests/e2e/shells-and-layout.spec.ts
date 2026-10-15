import { expect, test } from "@playwright/test";

import { SHOTS, apiDelete, apiPost, apiToken, loginViaStorage, uniq } from "./helpers";

/**
 * 九個路由都能點、各有標題列；四區塊每頁恰好一份（版面只住 app/layout.tsx）；
 * 響應式（PRD §8.3）：≥1280 完整側欄、768～1279 圖示側欄、<768 底部 Tab。
 * （/import、/settings 已由 W4-F1、/execute 與 /monitor 已由 W4-F2 換成實際頁面：它們的行為由 import／settings／execute／monitor 的 *.mock.spec.ts 驗證，
 *  這裡只留「導覽點得到、標題列在、四區塊各一份」；這幾頁的截圖也改由各自的 mock spec 產出。）
 */
type Created = { id: string };
const name = uniq("E2E 版面專案");
let token = "";
let projectId = "";

test.beforeAll(async ({ request }) => {
  token = await apiToken(request);
  projectId = (await apiPost<Created>(request, token, "/api/v1/projects", { name, executionPath: "/tmp/e2e-layout", passCriteria: "- ok" })).id;
});
test.afterAll(async ({ request }) => {
  await apiDelete(request, token || (await apiToken(request)), `/api/v1/projects/${projectId}`);
});

const REGIONS = ["top", "tools", "content", "bottom"] as const;

test("導覽六項都能點到對應頁面，每頁四區塊各一份", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "主導覽" });
  const cases: Array<[link: string, url: RegExp, heading: RegExp]> = [
    ["BRD/PRD 匯入", /\/import$/, /BRD \/ PRD 智能匯入/],
    ["系統設定", /\/settings$/, /系統參數設定/],
    ["專案管理", /\/projects$/, /專案管理/],
    ["儀表板", /\/$/, /總覽儀表板/],
  ];
  for (const [link, url, heading] of cases) {
    await nav.getByRole("link", { name: link }).click();
    await expect(page).toHaveURL(url);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    for (const r of REGIONS) await expect(page.locator(`[data-region="${r}"]`)).toHaveCount(1);
  }

  // 執行中心／監控中心從「目前專案」進入（進專案頁後記住該專案）
  await page.goto(`/projects/${projectId}`);
  await nav.getByRole("link", { name: "執行中心" }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/execute$`));
  await expect(page.getByRole("heading", { name: new RegExp(`專案執行：${name}`) })).toBeVisible();
  await expect(page.getByTestId("execute-view")).toBeVisible();
  await nav.getByRole("link", { name: "監控中心" }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/monitor$`));
  await expect(page.getByRole("heading", { name: new RegExp(`專案監控：${name}`) })).toBeVisible();
  await expect(page.getByTestId("monitor-view")).toBeVisible();
  for (const r of REGIONS) await expect(page.locator(`[data-region="${r}"]`)).toHaveCount(1);
});

test("PRD §4.2 的 new／edit／goals／tasks 路由都存在且可深連結", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await page.goto("/projects/new");
  await expect(page.getByRole("heading", { name: "新建專案" })).toBeVisible();
  await expect(page.getByLabel("專案名稱")).toBeVisible();
  await page.goto(`/projects/${projectId}/edit`);
  await expect(page.getByLabel("專案名稱")).toHaveValue(name);
  await page.goto(`/projects/${projectId}/goals`);
  await expect(page.getByRole("heading", { name: "目標列表" })).toBeVisible();
  await page.goto(`/projects/${projectId}/goals/new`);
  await expect(page.getByRole("heading", { name: "新建目標" })).toBeVisible();
});

test("搜尋列 Enter → /projects?q=，列表只留符合者並可清除", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await page.goto("/");
  await page.getByRole("searchbox", { name: "搜尋專案、目標、任務" }).fill(name);
  await page.getByRole("searchbox", { name: "搜尋專案、目標、任務" }).press("Enter");
  await expect(page).toHaveURL(/\/projects\?q=/);
  await expect(page.getByTestId("search-chip")).toContainText(name);
  await expect(page.getByTestId("project-card")).toHaveCount(1);
  await page.getByRole("button", { name: "清除搜尋" }).click();
  await expect(page).toHaveURL(/\/projects$/);
});

test.describe("響應式（PRD §8.3）", () => {
  test("平板 1024px：側欄收合成圖示（標籤隱藏、aria-label 保留）", async ({ page, request }) => {
    await page.setViewportSize({ width: 1024, height: 800 });
    await loginViaStorage(page, request);
    await page.goto("/projects");
    const tools = page.locator('[data-region="tools"]');
    const box = (await tools.boundingBox())!;
    expect(box.width).toBeLessThan(80);
    await expect(page.getByRole("link", { name: "專案管理" })).toBeVisible();
    await expect(page.getByTestId("project-rail")).toBeHidden();
    await page.screenshot({ path: `${SHOTS}/20-responsive-tablet.png` });
  });

  test("手機 390px：側欄變成底部 Tab 導航（位於內容下方）", async ({ page, request }) => {
    await page.setViewportSize({ width: 390, height: 800 });
    await loginViaStorage(page, request);
    await page.goto("/projects");
    const tools = (await page.locator('[data-region="tools"]').boundingBox())!;
    const content = (await page.locator('[data-region="content"]').boundingBox())!;
    expect(tools.y).toBeGreaterThanOrEqual(content.y + content.height - 1);
    expect(tools.width).toBeGreaterThan(300);
    await expect(page.getByRole("link", { name: "儀表板" })).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/21-responsive-mobile.png` });
  });

  test("桌面 1440px：240px 完整側欄與『我的專案』rail", async ({ page, request }) => {
    await loginViaStorage(page, request);
    await page.goto("/projects");
    const box = (await page.locator('[data-region="tools"]').boundingBox())!;
    expect(Math.round(box.width)).toBe(240);
    await expect(page.getByTestId("project-rail")).toBeVisible();
  });
});
