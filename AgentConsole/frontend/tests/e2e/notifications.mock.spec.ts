import { expect, test } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { compose, installApiMock, paged, signInAs, snap, type MockHandler } from "./mockApi";

/**
 * 通知徽章（契約 §1.4、§4.5 G-01／G-02／G-06）——route mock 版：
 * 頂列「通知鈴」徽章＝待審核項目＋未確認告警；「signoff 佇列」徽章＝待簽核草案；兩者與 Dashboard「待審批草案數」KPI
 * 都來自 GET /notifications/summary（每 30 秒輪詢，輪詢節奏由 lib/api/queries.polling.test.tsx 驗證）。
 *
 * v1.4（契約 §4.6 G-G4、§4.5 G-10、E2E-16 第 6 列）：摘要的三個數字都是**全部專案的合計**、沒有 projectId，
 * 所以「待審核項目」「未確認告警」兩列的連結只看**路由上的 projectId**——人在專案頁→該專案的執行頁／監控頁，其他頁面（含 Dashboard）→ /projects；
 * 「待簽核草案」列一律導向 Dashboard 的「待人工審批」卡（卡片清單取 GET /signoffs/pending，與摘要同源）。
 */
const P1 = "0c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f";
const NOW = "2026-10-15T08:30:12Z";

const project = { id: P1, name: "通知測試專案", executionPath: "/e2e/notify", status: "DRAFT", autonomyLevel: 3, signedOff: false, goalsCount: 0, tasksCount: 0, tasksDone: 0, updatedAt: NOW };
const projectDetail = { ...project, description: "通知測試用專案", passCriteria: "- [ ] 通過", createdAt: NOW, goals: [] };

/** 待審批清單與摘要同源（契約 §1.8.1：後端以同一組述詞算兩者）：摘要說有 n 筆，清單就給 n 筆目標草案（同一個專案，最多 limit 筆）。 */
function pendingOf(n: number, limit: number) {
  const items = Array.from({ length: n }, (_, i) => ({
    kind: "GOAL",
    id: `f0000000-0000-4000-8000-${String(i + 1).padStart(12, "0")}`,
    projectId: P1,
    projectName: project.name,
    parentId: P1,
    title: `目標 ${i + 1}`,
    createdAt: NOW,
  })).slice(0, limit);
  return { counts: { projects: 0, goals: n, tasks: 0, imports: 0, total: n }, items };
}

function backend(summary: () => Record<string, unknown>): MockHandler {
  return (call) => {
    if (call.method !== "GET") return undefined;
    if (call.path === "/api/v1/notifications/summary") return { data: { bridgeConnected: null, bridgeCheckedAt: null, ...summary() } };
    if (call.path === "/api/v1/signoffs/pending") return { data: pendingOf(Number(summary().pendingSignoffs ?? 0), Number(call.query.get("limit") ?? 50)) };
    if (call.path === "/api/v1/projects") return { data: paged([project], 100) };
    if (call.path === `/api/v1/projects/${P1}`) return { data: projectDetail };
    if (call.path === `/api/v1/projects/${P1}/goals`) return { data: [] };
    // Dashboard 的「本週完成任務數」打全域端點（v1.2，C-1）：這個 spec 沒有任何執行紀錄
    if (call.path === "/api/v1/monitor/task-totals") return { data: { from: NOW, to: NOW, started: 0, completed: 0, failed: 0, retried: 0, projectsCounted: 0 } };
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
    await expect(page.getByRole("button", { name: "通知 4 筆待處理" })).toBeVisible();

    await page.getByTestId("bell-trigger").click();
    const panel = page.getByTestId("notification-panel");
    await expect(panel).toBeVisible();
    await expect(panel.getByTestId("notification-signoffs-count")).toHaveText("2");
    await expect(panel.getByTestId("notification-reviews-count")).toHaveText("1");
    await expect(panel.getByTestId("notification-alerts-count")).toHaveText("3");
    // 連結：待簽核→Dashboard 的待人工審批卡；待審核與告警→人在 Dashboard（路由上沒有專案）時前往專案列表，不猜「最近造訪」或「列表第一筆」
    // （列表第一筆就是 P1，舊版會在這裡連到 P1 的執行頁／監控頁，把全部專案的合計說成屬於它）
    await expect(panel.getByTestId("notification-signoffs")).toHaveAttribute("href", "/#pending-signoff");
    await expect(panel.getByTestId("notification-reviews")).toHaveAttribute("href", "/projects");
    await expect(panel.getByTestId("notification-alerts")).toHaveAttribute("href", "/projects");
    // 連結文案不暗示「目前專案」：每列的提示講「全部專案的合計」與落點，面板底下再說明一次
    await expect(panel.getByTestId("notification-signoffs")).toHaveAttribute("title", "前往儀表板的「待人工審批」卡");
    await expect(panel.getByTestId("notification-reviews")).toHaveAttribute("title", "數字是全部專案的合計；點進去前往專案列表，請自行挑選有待辦的專案");
    await expect(panel.getByTestId("notification-alerts")).toHaveAttribute("title", "數字是全部專案的合計；點進去前往專案列表，請自行挑選有待辦的專案");
    await expect(panel.getByTestId("notification-scope-note")).toHaveText("待審核項目與未確認告警是全部專案的合計；在專案頁點進去前往該專案，其他頁面前往專案列表。");
    await expectNoA11yViolations(page, "通知面板（開啟）");
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
    // 待人工審批卡的徽章取自 GET /signoffs/pending 的 counts.total：與 KPI、頂列徽章是同一個 7
    await expect(page.getByTestId("pending-count")).toHaveText("7");
    await expect(page.getByTestId("pending-item")).toHaveCount(7);
    await snap(page, "01-dashboard-kpi-drafts.png");
  });

  test("人在專案頁：待審核項目與未確認告警連到該專案的執行頁與監控頁；待簽核草案列導向儀表板的「待人工審批」卡（契約 G-G4）", async ({ page }) => {
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(backend(() => ({ pendingSignoffs: 2, pendingReviews: 1, unacknowledgedAlerts: 3 }))));
    await page.goto(`/projects/${P1}`);
    await expect(page.getByTestId("project-title")).toHaveText("通知測試專案", { timeout: 60_000 });

    await page.getByTestId("bell-trigger").click();
    const panel = page.getByTestId("notification-panel");
    await expect(panel).toBeVisible();
    // 落點取路由上的專案；數字仍是全部專案的合計，所以提示照樣先講「合計」再講落點
    await expect(panel.getByTestId("notification-reviews")).toHaveAttribute("href", `/projects/${P1}/execute`);
    await expect(panel.getByTestId("notification-alerts")).toHaveAttribute("href", `/projects/${P1}/monitor`);
    await expect(panel.getByTestId("notification-reviews")).toHaveAttribute("title", "數字是全部專案的合計；點進去前往這個專案的執行頁");
    await expect(panel.getByTestId("notification-alerts")).toHaveAttribute("title", "數字是全部專案的合計；點進去前往這個專案的監控頁");
    await expect(panel.getByTestId("notification-signoffs-count")).toHaveText("2");

    // 待簽核草案列：離開專案頁、回到儀表板並停在「待人工審批」卡（錨點），卡片清單與徽章同為摘要的 2
    await panel.getByTestId("notification-signoffs").click();
    await expect(page).toHaveURL(/\/#pending-signoff$/);
    await expect(page.getByRole("heading", { name: "總覽儀表板" })).toBeVisible();
    await expect(page.getByTestId("pending-signoff-card")).toBeInViewport();
    await expect(page.getByTestId("pending-count")).toHaveText("2");
    await expect(page.getByTestId("pending-item")).toHaveCount(2);
  });
});
