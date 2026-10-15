import { expect, test } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { collectConsoleErrors, compose, fail, installApiMock, paged, signInAs, type MockHandler } from "./mockApi";

/**
 * 無障礙掃描（axe-core；WCAG 2.0／2.1 A／AA）——route mock 版，補上其他 mock spec 沒走到的頁面與狀態：
 * 登入頁（含欄位錯誤與登入失敗）、新建專案對話框（Markdown 編輯器工具列）、專案詳情（草案橫幅）、目標詳情、任務詳情（待人工、執行歷史與日誌面板）。
 * 其餘頁面（總覽、監控、執行、匯入、設定、專案列表、通知面板）的掃描放在各自的 mock spec 裡，緊跟在該頁最豐富的狀態之後。
 * 這是 QA 報告 §11 DEF-AC-004／005 的那把尺（axe 掃 11 頁）進 CI：色彩對比、名稱含可見文字、svg 替代文字、list 結構，任何一項改壞這裡就紅。
 */
const NOW = "2026-10-15T08:30:12Z";
const P = "0c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f";
const G1 = "a1111111-0000-4000-8000-000000000001";
const G2 = "a1111111-0000-4000-8000-000000000002";
const T1 = "b2222222-0000-4000-8000-000000000001";
const T2 = "b2222222-0000-4000-8000-000000000002";

const GOALS = [
  { id: G1, projectId: P, name: "基礎建設", status: "IN_PROGRESS", sortOrder: 0, signedOff: true, taskCount: 2, completedTaskCount: 1, updatedAt: NOW },
  { id: G2, projectId: P, name: "核心功能", status: "PENDING", sortOrder: 1, signedOff: false, taskCount: 0, completedTaskCount: 0, updatedAt: NOW },
];
/** 草案專案：未 signoff（有橫幅與「未審批」標籤）、說明與通過標準帶 Markdown。 */
const PROJECT = {
  id: P,
  name: "AISDLC Core Platform",
  description: "## 概述\n\n建立 **核心平台**，含 [設計稿](https://example.com)。\n\n- 可重現\n- 可驗證",
  executionPath: "/work/core",
  passCriteria: "- [ ] 所有模組通過單元測試\n- [x] API 契約驗證通過",
  status: "DRAFT",
  autonomyLevel: 4,
  signedOff: false,
  goalsCount: 2,
  tasksCount: 2,
  tasksDone: 1,
  createdAt: NOW,
  updatedAt: NOW,
  goals: GOALS.map(({ id, name, status, sortOrder, signedOff, taskCount, completedTaskCount }) => ({ id, name, status, sortOrder, signedOff, taskCount, completedTaskCount })),
};
const TASKS = [
  { id: T1, goalId: G1, name: "初始化", sortOrder: 0, status: "COMPLETED", retryCount: 0, maxRetries: 1, signedOff: true, updatedAt: NOW },
  { id: T2, goalId: G1, name: "設定", sortOrder: 1, status: "ESCALATED", retryCount: 1, maxRetries: 1, signedOff: false, updatedAt: NOW },
];
const GOAL_DETAIL = {
  ...GOALS[0],
  description: "基礎建設：目錄、設定、CI。",
  passCriteria: "- [x] 目錄結構完成\n- [ ] CI 全綠",
  dependsOn: [],
  completionRatio: 50,
  tasks: TASKS.map(({ id, name, status, sortOrder, retryCount, maxRetries, signedOff }) => ({ id, name, status, sortOrder, retryCount, maxRetries, signedOff })),
  createdAt: NOW,
};
const TASK_DETAIL = {
  ...TASKS[1],
  description: "請輸出 `[T2_DONE]`\n\n```ts\nexport const answer = 42;\n```",
  passCriteria: "- [ ] 設定檔通過驗證",
  evaluatorCommand: "npm test",
  expectedOutputRegex: "T2_DONE",
  assignedAgent: "claude-code",
  actualTokens: 1240,
  startedAt: NOW,
  executionLog: "[08:30:12] 開始設定\n[08:30:20] 驗證失敗：缺少欄位\n[08:30:31] 升級給人工",
  executionHistory: [
    { id: "h1", stepNumber: 1, action: "STEP", status: "STARTED", tokensUsed: 0, timestamp: NOW },
    { id: "h2", stepNumber: 2, action: "STEP", status: "FAILED", tokensUsed: 1240, timestamp: NOW },
  ],
  createdAt: NOW,
};

const backend: MockHandler = (call) => {
  if (call.method !== "GET") return undefined;
  if (call.path === "/api/v1/projects") return { data: paged([PROJECT], 100) };
  if (call.path === "/api/v1/notifications/summary") return { data: { pendingSignoffs: 3, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: true, bridgeCheckedAt: NOW } };
  if (call.path === `/api/v1/projects/${P}`) return { data: PROJECT };
  if (call.path === `/api/v1/projects/${P}/goals`) return { data: GOALS };
  if (call.path === `/api/v1/goals/${G1}`) return { data: GOAL_DETAIL };
  if (call.path === `/api/v1/goals/${G1}/tasks`) return { data: TASKS };
  if (call.path === `/api/v1/tasks/${T2}`) return { data: TASK_DETAIL };
  return undefined;
};

test.describe("無障礙掃描（route mock＋axe）", () => {
  test.setTimeout(120_000);

  test("登入頁：閒置、欄位驗證錯誤、帳密錯誤（401）三個狀態", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await installApiMock(
      page,
      compose((call) => (call.method === "POST" && call.path === "/api/v1/auth/login" ? fail(401, { message: "帳號或密碼錯誤" }) : undefined)),
    );
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "登入 AISDLC Console" })).toBeVisible({ timeout: 60_000 });
    await expectNoA11yViolations(page, "登入頁（閒置）");

    await page.getByRole("button", { name: "登入", exact: true }).click(); // 兩欄都空：欄位驗證錯誤
    await expect(page.getByText(/請輸入/).first()).toBeVisible();
    await expectNoA11yViolations(page, "登入頁（欄位驗證錯誤）");

    await page.getByLabel("使用者名稱").fill("operator");
    await page.getByLabel("密碼").fill("wrong-password");
    await page.getByRole("button", { name: "登入", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "帳號或密碼錯誤" })).toBeVisible();
    await expectNoA11yViolations(page, "登入頁（帳密錯誤）");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("新建專案對話框：Markdown 編輯器（工具列圖示、說明描述與通過標準兩個編輯區）", async ({ page }) => {
    await signInAs(page, "OPERATOR");
    await installApiMock(page, backend);
    await page.goto("/projects");
    await page.getByRole("button", { name: "新建專案" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: 60_000 });
    await expect(dialog.getByRole("textbox", { name: "說明描述", exact: true })).toBeVisible({ timeout: 60_000 });
    await expect(dialog.locator(".w-md-editor-toolbar").first()).toBeVisible();
    await expectNoA11yViolations(page, "新建專案對話框（空編輯器）");

    // 編輯器裡有內容：預覽端的標題、清單、核取清單、表格、程式碼區塊（prism＋highlight 兩套上色）
    const markdown = [
      "## 概述",
      "",
      "- [x] 已完成的項目",
      "- [ ] 待辦的項目",
      "",
      "| 欄位 | 說明 |",
      "| --- | --- |",
      "| id | 唯一識別碼 |",
      "",
      "```ts",
      "const answer: number = 42; // 註解",
      "```",
    ].join("\n");
    await dialog.getByRole("textbox", { name: "說明描述", exact: true }).fill(markdown);
    await expect(dialog.locator(".w-md-editor-preview").first().locator("code.language-ts")).toBeVisible();
    await expectNoA11yViolations(page, "新建專案對話框（編輯器預覽含程式碼區塊與核取清單）");
  });

  test("專案詳情（草案）、目標詳情、任務詳情（待人工）：橫幅、標籤、目標與任務清單、Markdown 渲染、執行日誌與歷史", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, backend);

    await page.goto(`/projects/${P}`);
    await expect(page.getByTestId("project-title")).toHaveText("AISDLC Core Platform", { timeout: 60_000 });
    await expect(page.getByTestId("signoff-banner")).toContainText("AI 草案 — 待人工 signoff 硬閘");
    await expect(page.getByText("核心功能")).toBeVisible();
    await expectNoA11yViolations(page, "專案詳情（草案）");

    await page.goto(`/projects/${P}/goals/${G1}`);
    await expect(page.getByRole("heading", { name: /基礎建設/ })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("設定", { exact: true }).first()).toBeVisible();
    await expectNoA11yViolations(page, "目標詳情");

    await page.goto(`/projects/${P}/goals/${G1}/tasks/${T2}`);
    await expect(page.getByTestId("task-title")).toHaveText("設定", { timeout: 60_000 });
    await expect(page.getByTestId("signoff-banner")).toContainText("草案未審批");
    await expect(page.getByTestId("execution-history")).toBeVisible();
    await expectNoA11yViolations(page, "任務詳情（待人工）");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});
