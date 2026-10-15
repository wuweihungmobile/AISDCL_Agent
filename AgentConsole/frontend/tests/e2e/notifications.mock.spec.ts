import { expect, test } from "@playwright/test";

import { compose, installApiMock, paged, signInAs, snap, type MockHandler } from "./mockApi";

/**
 * 通知徽章（契約 §1.4、§4.5 G-01／G-02／G-06）——route mock 版：
 * 頂列「通知鈴」徽章＝待審核項目＋未確認告警；「signoff 佇列」徽章＝待簽核草案；兩者與 Dashboard「待審批草案數」KPI
 * 都來自 GET /notifications/summary（每 30 秒輪詢，輪詢節奏由 lib/api/queries.polling.test.tsx 驗證）。
 */
const P1 = "0c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f";
const NOW = "2026-10-15T08:30:12Z";

const project = { id: P1, name: "通知測試專案", executionPath: "/e2e/notify", status: "DRAFT", autonomyLevel: 3, signedOff: false, goalsCount: 0, tasksCount: 0, tasksDone: 0, updatedAt: NOW };

function backend(summary: () => Record<string, unknown>): MockHandler {
  return (call) => {
    if (call.method !== "GET") return undefined;
    if (call.path === "/api/v1/notifications/summary") return { data: { bridgeConnected: null, bridgeCheckedAt: null, ...summary() } };
    if (call.path === "/api/v1/projects") return { data: paged([project], 100) };
    if (call.path === `/api/v1/projects/${P1}/goals`) return { data: [] };
    return undefined;
  };
}

test.describe("通知徽章（route mock）", () => {
  test.setTimeout(120_000);

  test("通知鈴徽章＝待審核＋未確認告警；signoff 佇列鈕徽章＝待簽核；點鈴鐺開小面板列三個數字與連結", async ({ page }) => {
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(backend(() => ({ pendingSignoffs: 2, pendingReviews: 1, unacknowledgedAlerts: 3 }))));
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "總覽儀表板" })).toBeVisible({ timeout: 60_000 });

    await expect(page.getByTestId("bell-badge")).toHaveText("4");
    await expect(page.getByTestId("signoff-badge")).toHaveText("2");
    await expect(page.getByRole("button", { name: "通知（4 筆待處理）" })).toBeVisible();

    await page.getByTestId("bell-trigger").click();
    const panel = page.getByTestId("notification-panel");
    await expect(panel).toBeVisible();
    await expect(panel.getByTestId("notification-signoffs-count")).toHaveText("2");
    await expect(panel.getByTestId("notification-reviews-count")).toHaveText("1");
    await expect(panel.getByTestId("notification-alerts-count")).toHaveText("3");
    // 連結：待簽核→Dashboard 的待審批卡；待審核與告警→目前專案的執行／監控頁
    await expect(panel.getByTestId("notification-signoffs")).toHaveAttribute("href", "/#pending-signoff");
    await expect(panel.getByTestId("notification-reviews")).toHaveAttribute("href", `/projects/${P1}/execute`);
    await expect(panel.getByTestId("notification-alerts")).toHaveAttribute("href", `/projects/${P1}/monitor`);
    await snap(page, "00-notification-panel.png");

    // Esc 關閉
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
  });

  test("全部為 0：沒有徽章；Dashboard「待審批草案數」KPI 取自摘要（跨專案、含目標與任務層級），不是專案列表算出的近似值", async ({ page }) => {
    let summary: Record<string, unknown> = { pendingSignoffs: 0, pendingReviews: 0, unacknowledgedAlerts: 0 };
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(backend(() => summary)));
    await page.goto("/");
    await expect(page.getByTestId("kpi-drafts")).toHaveText("0", { timeout: 60_000 });
    await expect(page.getByTestId("bell-badge")).toHaveCount(0);
    await expect(page.getByTestId("signoff-badge")).toHaveCount(0);

    // 專案列表只有 1 個草案專案；摘要說有 7 筆（含目標、任務與匯入草案）→ KPI 顯示 7
    summary = { pendingSignoffs: 7, pendingReviews: 0, unacknowledgedAlerts: 0 };
    await page.reload();
    await expect(page.getByTestId("kpi-drafts")).toHaveText("7");
    await expect(page.getByTestId("signoff-badge")).toHaveText("7");
    await snap(page, "01-dashboard-kpi-drafts.png");
  });
});
