import { expect, test, type Locator } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { ensureQuota, signIn } from "./realBackend";

/**
 * 自我進化頁（Docker 全棧，經 nginx 同源；OBS-SI-321——`/self-improving` 此前沒有任何瀏覽器層測試）——**實機冒煙，不是每個 commit 的閘**（沿 issues-docker／sysadmin-backup-docker 兩支的形態）：
 * `docker compose --profile db --profile app --profile full up -d` 之後，以
 * `$env:E2E_API_URL = "http://localhost"; npx playwright test -c tests/e2e/docker.config.ts -g "OBS_SI_321" --output <各自的暫存目錄>` 執行。
 * 與 *.mock.spec.ts 的差別：這裡不用 route mock，資料來自真 console-api → 真 Bridge → 真根層 `si export`，所以只驗**與帳本內容無關**的事（現有幾筆提案、待入帳是否為空都不影響斷言）。
 * 分兩支，各自回答一個問題（序列執行；兩支都不下決定、不送任何表單）：
 *  · `OBS_SI_321_UI`＝瀏覽器層：從導覽進頁、狀態橫幅／對帳面板／提案分頁各自走到終態，終態若是錯誤態就必須是頁面設計的「誠實錯誤態」（摘要、重試鈕，且**不得**同時宣稱空表或「無待入帳」）、
 *    進頁過程沒有對 `/api/v1/si/` 的非 GET 請求、axe 無障礙違規 0。後端慢或掛了，這支仍綠——它量的是畫面，不是後端。
 *  · `OBS_SI_321_OK`＝鏡像可用：狀態橫幅 ok（head 欄在）、提案表（`si-prop-table`）或其空狀態（`si-empty`）可見。這支量的是整條資料鏈（Bridge 子行程 `si export` 須在其逾時內回來）：
 *    它紅＝全棧的 SI 匯出不可用或太慢，不是畫面壞了；缺陷登記後可比照 realBackend 的 `DEFECTS_OPEN` 用 `test.fail` 釘住。
 */
test.describe.configure({ mode: "serial" });

const WRITES_TERMINALS = ["si-writes-empty", "si-pending-list", "si-write-alerts", "si-reconcile-ne"];
const PROPOSAL_TERMINALS = ["si-prop-table", "si-empty"];

const anyOf = (scope: Locator, testIds: string[]): Locator => scope.locator(testIds.map((id) => `[data-testid="${id}"]`).join(", "));

/** 區塊離開載入態後的終態：回傳命中的 data-testid（錯誤態一律回 `si-error`）；錯誤態同時驗頁面契約——有摘要與重試鈕，且沒有任何「空」的宣稱。 */
async function settledState(scope: Locator, okTestIds: string[], what: string): Promise<string> {
  await expect(scope.getByTestId("si-loading"), `${what}一直停在載入態`).toHaveCount(0, { timeout: 90_000 });
  if ((await scope.getByTestId("si-error").count()) > 0) {
    await expect(scope.getByTestId("si-error-summary"), `${what}：錯誤態必須有摘要文字`).not.toHaveText("");
    await expect(scope.getByTestId("si-retry"), `${what}：錯誤態必須有重試鈕`).toBeEnabled();
    await expect(anyOf(scope, [...okTestIds, "si-prop-table", "si-empty", "si-writes-empty"]), `${what}：錯誤態不得同時宣稱表格、空狀態或「無待入帳」`).toHaveCount(0);
    return "si-error";
  }
  const hit = anyOf(scope, okTestIds).first();
  await expect(hit, `${what}：既不是錯誤態也沒有任何終態元素`).toBeVisible();
  return (await hit.getAttribute("data-testid")) ?? "";
}

test.describe("Docker 全棧：自我進化頁（瀏覽器層冒煙）", () => {
  test.setTimeout(300_000);

  test("OBS_SI_321_UI ADMIN 從導覽進自我進化：橫幅、對帳面板、提案分頁各自走到終態（錯誤態必須誠實），無寫入請求、無障礙違規 0", async ({ page, request }) => {
    await ensureQuota(request, "admin", 40);
    await signIn(page, request, "admin");

    // 進頁期間的寫入請求：唯讀鏡像不該有（`console-writes` 與其餘 si 端點都是 GET）
    const siWrites: string[] = [];
    page.on("request", (req) => {
      if (req.url().includes("/api/v1/si/") && !["GET", "HEAD", "OPTIONS"].includes(req.method())) siWrites.push(`${req.method()} ${req.url()}`);
    });

    // 導覽入口：登記表第七項「自我進化」點得到、網址對、該項為 aria-current
    await page.goto("/projects");
    const nav = page.getByRole("navigation", { name: "主導覽" });
    await nav.getByRole("link", { name: "自我進化" }).click();
    await expect(page).toHaveURL(/\/self-improving$/);
    await expect(page.getByRole("heading", { level: 1, name: "自我進化" })).toBeVisible({ timeout: 60_000 });
    await expect(nav.getByRole("link", { name: "自我進化" })).toHaveAttribute("aria-current", "page");
    await expect(page.getByTestId("si-view")).toBeVisible();

    // 狀態橫幅：元素存在；終態是 ok（head 欄）或誠實錯誤態
    const banner = page.getByTestId("si-status-banner");
    await expect(banner).toBeVisible();
    const bannerState = await settledState(banner, ["si-head-sha"], "狀態橫幅");

    // 對帳面板（只對 ADMIN 渲染）
    const writes = page.getByTestId("si-writes-panel");
    await expect(writes).toBeVisible();
    const writesState = await settledState(writes, WRITES_TERMINALS, "對帳面板");

    // 「提案」分頁
    await page.getByRole("tab", { name: /^提案/ }).click();
    const panel = page.getByTestId("si-panel-proposals");
    await expect(panel).toBeVisible();
    const proposalsState = await settledState(panel, PROPOSAL_TERMINALS, "提案面板");

    expect(siWrites, "進頁與看提案分頁的過程不得有任何對 /api/v1/si/ 的非 GET 請求").toEqual([]);
    await expectNoA11yViolations(page, "自我進化頁（全棧真實資料：提案分頁）");
    console.log(`[self-improving-docker] OBS-SI-321 UI：橫幅＝${bannerState}；對帳面板＝${writesState}；提案分頁＝${proposalsState}；非 GET 的 si 請求 ${siWrites.length} 件`);
  });

  test("OBS_SI_321_OK 鏡像可用：狀態橫幅 ok、提案表或其空狀態可見（整條資料鏈：Bridge 子行程 si export 在逾時內回來）", async ({ page, request }) => {
    await ensureQuota(request, "admin", 40);
    await signIn(page, request, "admin");
    await page.goto("/self-improving");
    await expect(page.getByRole("heading", { level: 1, name: "自我進化" })).toBeVisible({ timeout: 60_000 });

    const banner = page.getByTestId("si-status-banner");
    await expect(banner.getByTestId("si-loading")).toHaveCount(0, { timeout: 90_000 });
    await expect(banner.getByTestId("si-error"), "狀態橫幅是錯誤態：全棧的 SI 匯出（Bridge 子行程 si export）不可用或逾時").toHaveCount(0);
    await expect(banner.getByTestId("si-head-sha")).toBeVisible();

    await page.getByRole("tab", { name: /^提案/ }).click();
    const panel = page.getByTestId("si-panel-proposals");
    await expect(panel.getByTestId("si-loading")).toHaveCount(0, { timeout: 90_000 });
    await expect(panel.getByTestId("si-error"), "提案面板是錯誤態：全棧的 SI 匯出不可用或逾時").toHaveCount(0);
    const tableOrEmpty = anyOf(panel, PROPOSAL_TERMINALS);
    await expect(tableOrEmpty).toHaveCount(1);
    await expect(tableOrEmpty).toBeVisible();
    console.log(`[self-improving-docker] OBS-SI-321 OK：狀態橫幅 ok；提案分頁＝${(await tableOrEmpty.getAttribute("data-testid")) ?? ""}`);
  });
});
