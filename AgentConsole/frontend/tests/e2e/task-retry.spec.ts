import { expect, test } from "@playwright/test";

import { loginViaStorage } from "./helpers";

/**
 * 重試只在 FAILED／ESCALATED 啟用。後端目前沒有把任務改成 FAILED 的入口（要由執行引擎事件驅動，Phase 4），
 * 所以這支用 route mock 回傳 FAILED 的任務詳情與重試結果，驗證前端：按鈕啟用、送出 POST /retry、toast 帶 x / y。
 * （PENDING 任務的重試鈕停用，已在 crud-flow 以真資料驗證。）
 */
const PROJECT = "11111111-1111-4111-8111-111111111111";
const GOAL = "22222222-2222-4222-8222-222222222222";
const TASK = "33333333-3333-4333-8333-333333333333";

const taskDetail = (status: string, retryCount: number) => ({
  id: TASK,
  goalId: GOAL,
  name: "模擬失敗的任務",
  description: "route mock",
  passCriteria: "- [ ] x",
  sortOrder: 0,
  status,
  retryCount,
  maxRetries: 3,
  assignedAgent: "AutoClaude-01",
  executionLog: "[14:32:05] 開始\n[14:32:09] ERROR: 測試失敗\n[14:32:10] 結束",
  executionHistory: [],
  signedOff: true,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  startedAt: "2026-01-01T06:32:05Z",
  actualTokens: 12450,
});
const ok = (data: unknown) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ code: 200, message: "success", data }) });

test("FAILED 任務可重試：送出 POST /retry，toast 顯示重試 1 / 3；日誌可搜尋", async ({ page, request }) => {
  await loginViaStorage(page, request);
  let current = taskDetail("FAILED", 0);
  let retryCalls = 0;

  await page.route(`**/api/v1/tasks/${TASK}`, (route) => route.fulfill(ok(current)));
  await page.route(`**/api/v1/tasks/${TASK}/retry`, (route) => {
    retryCalls += 1;
    current = taskDetail("QUEUED", 1);
    return route.fulfill(ok(current));
  });
  await page.route(`**/api/v1/goals/${GOAL}`, (route) =>
    route.fulfill(ok({ id: GOAL, projectId: PROJECT, name: "模擬目標", passCriteria: "-", sortOrder: 0, status: "IN_PROGRESS", dependsOn: [], signedOff: true, taskCount: 1, completedTaskCount: 0, completionRatio: 0, tasks: [], createdAt: "2026-01-01T00:00:00Z", updatedAt: "2026-01-01T00:00:00Z" })),
  );
  await page.route(`**/api/v1/projects/${PROJECT}`, (route) =>
    route.fulfill(ok({ id: PROJECT, name: "模擬專案", executionPath: "/x", passCriteria: "-", status: "EXECUTING", autonomyLevel: 3, signedOff: true, goalsCount: 1, tasksCount: 1, tasksDone: 0, createdAt: "2026-01-01T00:00:00Z", updatedAt: "2026-01-01T00:00:00Z", goals: [] })),
  );

  await page.goto(`/projects/${PROJECT}/goals/${GOAL}/tasks/${TASK}`);
  await expect(page.getByTestId("task-title")).toHaveText("模擬失敗的任務");
  await expect(page.getByTestId("metric-tokens")).toHaveText("12,450");

  // 日誌搜尋：只留符合的行
  await page.getByRole("searchbox", { name: "搜尋執行日誌" }).fill("error");
  await expect(page.getByRole("log", { name: "執行日誌" })).toContainText("ERROR: 測試失敗");
  await expect(page.getByRole("log", { name: "執行日誌" })).not.toContainText("開始");
  await expect(page.getByText("1 / 3 行")).toBeVisible();

  const retry = page.getByRole("button", { name: "重試" });
  await expect(retry).toBeEnabled();
  await retry.click();
  await expect(page.getByRole("status").filter({ hasText: "已重新排入佇列（重試 1 / 3）" })).toBeVisible();
  expect(retryCalls).toBe(1);
  await expect(page.getByTestId("metric-retries")).toHaveText("1 / 3");
  await expect(retry).toBeDisabled(); // 已轉 QUEUED，不可再重試
});
