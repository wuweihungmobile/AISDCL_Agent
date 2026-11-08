import { expect, test, type Locator, type Page } from "@playwright/test";

import { ALLOWLIST, CAPABILITIES_LOCAL } from "../fixtures/research/misc";
import { collectConsoleErrors, compose, installApiMock, shellHandler, signInAs, type MockHandler } from "./mockApi";
import { backupBackend, BACKUP_LABELS_DEFAULT, issuesBackend, PROJECT_NAMES_BY_CREATION, projectsBackend, RESEARCH_LIST, RESEARCH_RPNOS_BY_RP, RESEARCH_RPNOS_BY_TITLE } from "./sortFixtures";

/**
 * Console UX 增量（TCS-ConsoleUxSortHelp-20261108 AC-963-8；AT-963-8-2～8-5）——route mock 版：真瀏覽器看排序控制列與表頭排序。
 * 後端以 sortFixtures.ts 的處理器代替（不改 mockApi.ts）；專案 mock 依請求 `sort` 真的排序。
 * 判定指令：npx playwright test tests/e2e/console-sort.mock.spec.ts --output=<各自目錄>（cwd＝AgentConsole/frontend）
 */
const researchBackend: MockHandler = (call) => {
  if (call.method !== "GET") return undefined;
  if (call.path === "/api/v1/research/capabilities") return { data: CAPABILITIES_LOCAL };
  if (call.path === "/api/v1/research/allowlist") return { data: ALLOWLIST };
  if (call.path === "/api/v1/research/projects") return { data: RESEARCH_LIST };
  return undefined;
};

/** 依 `names` 在文字中出現者，回傳各列對應到的名稱（順序＝畫面順序）。 */
async function orderOf(rows: Locator, names: readonly string[]): Promise<string[]> {
  const texts = await rows.allTextContents();
  return texts.map((t) => names.find((n) => t.includes(n)) ?? `?${t.slice(0, 20)}`);
}

async function open(page: Page, role: "ADMIN" | "OPERATOR", backend: MockHandler, route: string, ready: Locator | ((p: Page) => Locator)) {
  const errors = collectConsoleErrors(page);
  await signInAs(page, role);
  const { calls } = await installApiMock(page, compose(backend, shellHandler()));
  await page.goto(route);
  await expect(typeof ready === "function" ? ready(page) : ready).toBeVisible({ timeout: 60_000 });
  return { calls, errors };
}

test.describe("Console 排序（route mock）", () => {
  test.setTimeout(120_000);

  test("AT_963_8_2 專案管理：預設建立順序、選「名稱」與方向鈕改變卡片順序且請求帶對應 sort、沒有「任務數」選項", async ({ page }) => {
    const { calls, errors } = await open(page, "OPERATOR", projectsBackend, "/projects", (p) => p.getByTestId("project-card").first());
    const cards = page.getByTestId("project-card");
    const names = PROJECT_NAMES_BY_CREATION;
    await expect(cards).toHaveCount(3);
    expect(await orderOf(cards, names), "預設＝建立順序").toEqual(["Charlie", "Alpha", "Bravo"]);
    expect(calls.filter((c) => c.path === "/api/v1/projects" && c.query.get("sort") === "createdAt,asc").length, "預設請求 sort=createdAt,asc").toBeGreaterThan(0);

    const bar = page.getByRole("group", { name: "專案排序" });
    const select = bar.getByRole("combobox", { name: "排序" });
    const options = await select.locator("option").allTextContents();
    expect(options, "選項集合；沒有任務數與目標數").toEqual(["建立順序", "名稱", "狀態", "最近更新", "自治等級"]);
    expect(options.some((o) => o.includes("任務數"))).toBe(false);

    await select.selectOption({ label: "名稱" });
    await expect.poll(() => orderOf(cards, names), { message: "名稱升冪" }).toEqual(["Alpha", "Bravo", "Charlie"]);
    expect(calls.some((c) => c.path === "/api/v1/projects" && c.query.get("sort") === "name,asc")).toBe(true);

    await bar.getByRole("button", { name: "目前由小到大，按一下改由大到小" }).click();
    await expect.poll(() => orderOf(cards, names), { message: "名稱降冪" }).toEqual(["Charlie", "Bravo", "Alpha"]);
    expect(calls.some((c) => c.path === "/api/v1/projects" && c.query.get("sort") === "name,desc")).toBe(true);
    await expect(bar.getByRole("button", { name: "目前由大到小，按一下改由小到大" })).toBeVisible();
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("AT_963_8_3 議題中心：待處理佇列序不變；全部分頁點「編號」表頭 aria-sort 反向、列序反轉、置頂列仍在頂端；鍵盤 Tab 到表頭按鈕按 Enter 同樣有效", async ({ page }) => {
    const { errors } = await open(page, "ADMIN", issuesBackend, "/issues", (p) => p.getByTestId("issues-table"));
    const rowIds = () => page.locator('[data-testid^="issue-row-"]').evaluateAll((els) => els.map((el) => (el.getAttribute("data-testid") ?? "").replace("issue-row-", "")));

    // 待處理佇列序不變（R-IC-33 第一條：嚴重度→…；OBS-SI-006 緊急在前、007 高在後）
    expect(await rowIds(), "待處理佇列序").toEqual(["OBS-SI-006", "OBS-SI-007"]);
    await expect(page.getByTestId("sort-reset")).toHaveCount(0);

    await page.getByRole("tab", { name: "全部" }).click();
    await expect(page.getByTestId("issue-row-OBS-SI-001")).toBeVisible();
    const before = await rowIds();
    expect(before.slice(0, 2).sort(), "全部分頁預設：兩個置頂列在最上").toEqual(["OBS-SI-005", "PROP-SI-004"]);
    await expect(page.getByTestId("issue-top-pinned")).toHaveCount(2);

    const header = page.getByRole("columnheader", { name: "編號" });
    await expect(header).toHaveAttribute("aria-sort", "none");
    await header.getByRole("button").click();
    await expect(header).toHaveAttribute("aria-sort", "ascending");
    const asc = await rowIds();
    expect(asc.slice(0, 2).sort(), "排序後置頂列仍在頂端").toEqual(["OBS-SI-005", "PROP-SI-004"]);
    expect(asc.slice(2), "其下依編號升冪").toEqual(["OBS-SI-001", "OBS-SI-006", "OBS-SI-007"]);
    expect(await page.getByTestId("issue-top-pinned").evaluateAll((els) => els.map((el) => el.closest("tr")?.getAttribute("data-testid"))), "置頂標記仍在置頂列").toEqual(
      asc.slice(0, 2).map((id) => `issue-row-${id}`),
    );
    await expect(page.getByTestId("sort-reset")).toBeVisible();

    await header.getByRole("button").click();
    await expect(header).toHaveAttribute("aria-sort", "descending");
    const desc = await rowIds();
    expect(desc.slice(0, 2).sort(), "反向後置頂列仍在頂端").toEqual(["OBS-SI-005", "PROP-SI-004"]);
    expect(desc.slice(2), "其下列序反轉").toEqual(["OBS-SI-007", "OBS-SI-006", "OBS-SI-001"]);

    // 鍵盤：Tab 到「來源」表頭按鈕（data-sort-key=source），Enter 啟動排序
    const sourceBtn = page.locator('th button[data-sort-key="source"]');
    let reached = false;
    await sourceBtn.focus(); // 先落在鄰近元素，再用 Tab 走到下一顆（標題）確認 Tab 序可走過表頭按鈕
    await page.keyboard.press("Shift+Tab");
    for (let i = 0; i < 20 && !reached; i += 1) {
      await page.keyboard.press("Tab");
      reached = await page.evaluate(() => document.activeElement?.matches('th button[data-sort-key="source"]') ?? false);
    }
    expect(reached, "Tab 能走到來源表頭按鈕").toBe(true);
    await page.keyboard.press("Enter");
    await expect(page.getByRole("columnheader", { name: "來源" })).toHaveAttribute("aria-sort", "ascending");
    await expect(header).toHaveAttribute("aria-sort", "none");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("AT_963_8_4 研發工作流清單：預設編號升冪；選「標題」列序改變；「本頁說明」步驟 ≥ 5 且不含「目前開放前兩步」", async ({ page }) => {
    const { errors } = await open(page, "OPERATOR", researchBackend, "/research", (p) => p.getByTestId("research-list"));
    const rows = page.getByTestId("research-row");
    await expect(rows).toHaveCount(3);
    expect(await orderOf(rows, RESEARCH_RPNOS_BY_RP), "預設編號升冪").toEqual([...RESEARCH_RPNOS_BY_RP]);

    const select = page.getByRole("group", { name: "研究專案排序" }).getByRole("combobox", { name: "排序" });
    await select.selectOption({ label: "標題" });
    await expect.poll(() => orderOf(rows, RESEARCH_RPNOS_BY_TITLE), { message: "標題升冪" }).toEqual([...RESEARCH_RPNOS_BY_TITLE]);

    await page.getByTestId("page-help-open").click();
    const dialog = page.getByTestId("page-help-dialog");
    await expect(dialog).toBeVisible();
    const steps = dialog.getByTestId("page-help-steps").locator("ol > li");
    expect(await steps.count(), "步驟 ≥ 5").toBeGreaterThanOrEqual(5);
    await expect(dialog).not.toContainText("目前開放前兩步");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("AT_963_8_5 備份：預設新到舊；點「標籤」表頭列序改變且出現「還原預設排序」；按它回新到舊", async ({ page }) => {
    const { errors } = await open(page, "ADMIN", backupBackend, "/sysadmin/backup", (p) => p.getByTestId("bk-table"));
    const rows = page.locator('[data-testid^="bk-row-"]');
    const labels = [...BACKUP_LABELS_DEFAULT];
    await expect(rows).toHaveCount(3);
    const order = () => rows.evaluateAll((els) => els.map((el) => (el.getAttribute("data-testid") ?? "").replace("bk-row-", "")));
    expect(await order(), "預設新到舊").toEqual(labels);
    await expect(page.getByTestId("sort-reset")).toHaveCount(0);

    await page.getByRole("columnheader", { name: "標籤" }).getByRole("button").click();
    await expect(page.getByTestId("sort-reset")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "標籤" })).toHaveAttribute("aria-sort", "ascending");
    const sorted = await order();
    expect(sorted, "標籤升冪後列序改變").not.toEqual(labels);
    expect(sorted, "標籤自然序升冪：數字開頭在前、字母開頭在後").toEqual(["20261026-020000F", "20261026-020000F_20261027-020000D", "aisdlc-20261025-183000.dump"]);

    await page.getByTestId("sort-reset").click();
    await expect.poll(order, { message: "還原預設排序後回新到舊" }).toEqual(labels);
    await expect(page.getByTestId("sort-reset")).toHaveCount(0);
    await expect(page.getByRole("columnheader", { name: "結束" })).toHaveAttribute("aria-sort", "descending");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});
