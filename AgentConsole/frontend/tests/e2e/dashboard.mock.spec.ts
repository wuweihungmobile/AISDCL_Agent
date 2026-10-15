import { expect, test } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { compose, fail, installApiMock, paged, signInAs, snap, collectConsoleErrors, type MockHandler } from "./mockApi";

/**
 * 總覽儀表板（設計稿畫面 1；契約 §4.5 G-06～G-08、§1.3.8）與 BottomRegion 的 Engine Bridge 連線點——route mock 版：
 *  - 四張 KPI：活躍專案數（專案 API）、待審批草案數（GET /notifications/summary 的 pendingSignoffs，跨專案）、
 *    本週完成任務數（GET /monitor/task-totals 的 completed：一次請求；from＝本週一 00:00、to 省略＝現在；v1.2，C-1／DEF-AC-009）、
 *    執行中 run 數（各 EXECUTING 專案的最新批次）；
 *  - 「進行中的執行」卡顯示最新批次（Run #n）與其進度，專案名連到執行頁；
 *  - Engine Bridge 連線點取自通知摘要的 bridgeConnected／bridgeCheckedAt：true 綠點、false 紅點、null 灰點「未知」（不假裝已連線）。
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

type World = { summary: Record<string, unknown>; totals: "ok" | "fail" };

/** 全域任務總計（契約 §1.3.8）：跨專案的步驟列數；completed 是儀表板「本週完成」顯示的值 */
const TOTALS = { from: "2026-10-12T00:00:00Z", to: "2026-10-15T08:40:00Z", started: 8, completed: 7, failed: 1, retried: 0, projectsCounted: 2 };

function backend(world: World): MockHandler {
  return (call) => {
    if (call.method !== "GET") return undefined;
    if (call.path === "/api/v1/projects") return { data: paged(PROJECTS, 100) };
    if (call.path === "/api/v1/notifications/summary")
      return { data: { pendingSignoffs: 0, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null, ...world.summary } };
    if (call.path === `/api/v1/projects/${B}/goals`) {
      const goal = (id: string, name: string) => ({ id, projectId: B, name, status: "PENDING", sortOrder: 0, signedOff: false, taskCount: 3, completedTaskCount: 0, updatedAt: NOW });
      return { data: [goal("f0000000-0000-4000-8000-000000000001", "基礎"), goal("f0000000-0000-4000-8000-000000000002", "核心")] };
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

  test("四張 KPI 取真值；「進行中的執行」顯示最新批次進度並連到執行頁；待審批卡仍列可直接審批的項目", async ({ page }) => {
    const world: World = { summary: { pendingSignoffs: 5, pendingReviews: 1, unacknowledgedAlerts: 2 }, totals: "ok" };
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
    // 待人工審批卡：草稿專案與其未審批目標（可直接點「審批」）；這份清單與 KPI 的 5 不同，KPI 以跨專案摘要為準
    await expect(page.getByTestId("pending-count")).toHaveText("3");
    await expect(page.getByTestId("pending-item")).toHaveCount(3);
    // 無障礙（DEF-AC-004／005）：色彩對比、頂列 logo 名稱含可見文字等，只有真瀏覽器量得到
    await expectNoA11yViolations(page, "總覽儀表板");
    await snap(page, "01-dashboard-live.png", { tall: true });
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("task-totals 查詢失敗：「本週完成任務數」顯示「—」與錯誤說明（不編數字），其餘 KPI 照常（截圖檔名沿用 partial：只有一張卡缺資料）", async ({ page }) => {
    const world: World = { summary: { pendingSignoffs: 0 }, totals: "fail" };
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(backend(world)));
    await page.goto("/");
    await expect(page.getByTestId("kpi-grid")).toContainText("無法載入本週完成任務數", { timeout: 60_000 });
    await expect(page.getByTestId("kpi-week-done")).toHaveText("—");
    await expect(page.getByTestId("kpi-active")).toHaveText("2");
    await expect(page.getByTestId("kpi-drafts")).toHaveText("0");
    await expect(page.getByTestId("kpi-grid")).toContainText("全部已審批");
    await snap(page, "01-dashboard-partial.png");
  });

  test("底部 Engine Bridge 連線點：true 綠點已連線、false 紅點未連線、null 灰點「未知」（不假裝已連線）", async ({ page }) => {
    const world: World = { summary: { bridgeConnected: true, bridgeCheckedAt: NOW }, totals: "ok" };
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
