import { expect, test } from "@playwright/test";

import { SHOTS, apiDelete, apiPost, apiToken, loginViaStorage, uniq, waitForQuota } from "./helpers";

/**
 * Signoff 硬閘（對真後端）：以 API 建立 draft:true 的草案（signedOff=false，後端提供的正式旗標，不需 mock），
 * 驗證：Dashboard「待人工審批」與頂列徽章、專案詳情的警示橫幅、signoff 對話框、已簽核後橫幅消失、
 * 空白審批者的行內錯誤，以及唯讀角色（viewer）的按鈕停用。
 */
type Created = { id: string; name: string };

test.describe("signoff 流程", () => {
  const name = uniq("E2E 草案專案");
  let token = "";
  let project: Created;
  let goal: Created;

  // 限流是固定視窗（每使用者每 60 秒 100 次）；前一支 spec（shells-and-layout）跑得快時 operator 的額度已見底，
  // 總覽頁每次載入又要 30 次上下（DEF-AC-009），所以每個情境前先確認餘額，不夠就等視窗過去（最多等一個視窗，故拉高逾時）。
  test.setTimeout(240_000);

  test.beforeAll(async ({ request }) => {
    test.setTimeout(240_000);
    token = await apiToken(request);
    await waitForQuota(request, token, 60);
    project = await apiPost<Created>(request, token, "/api/v1/projects", {
      name,
      executionPath: "/tmp/e2e-draft",
      passCriteria: "- 草案通過標準",
      draft: true,
    });
    goal = await apiPost<Created>(request, token, `/api/v1/projects/${project.id}/goals`, {
      name: uniq("草案目標"),
      passCriteria: "- [ ] 草案目標標準",
      draft: true,
    });
  });

  test.beforeEach(async ({ request }) => {
    await waitForQuota(request, token, 45);
  });

  test.afterAll(async ({ request }) => {
    test.setTimeout(240_000);
    const t = token || (await apiToken(request));
    await waitForQuota(request, t, 5);
    if (project) await apiDelete(request, t, `/api/v1/projects/${project.id}`); // beforeAll 失敗時 project 尚未建立
  });

  test("Dashboard 待審批卡 → 審批專案：approver 預設帶使用者名稱，確認後 toast 並從佇列消失", async ({ page, request }) => {
    await loginViaStorage(page, request);
    await page.goto("/");
    // 專案列（連結文字恰為專案名）；目標列的 meta 也含專案名，不能只用 hasText
    const item = page.getByTestId("pending-item").filter({ has: page.getByRole("link", { name, exact: true }) });
    await expect(item).toBeVisible();
    await expect(page.getByTestId("signoff-badge")).toBeVisible();
    await expect(page.getByTestId("kpi-drafts")).not.toHaveText("0");
    await page.screenshot({ path: `${SHOTS}/01c-dashboard-pending-signoff.png` });

    await item.getByRole("button", { name: /審批/ }).click();
    const dialog = page.getByRole("dialog", { name: "審批 signoff：專案" });
    await expect(dialog.getByLabel("審批者")).toHaveValue("operator");

    // 審批者不可匿名：清空後送出 → 行內錯誤、不呼叫後端
    await dialog.getByLabel("審批者").fill("   ");
    await dialog.getByRole("button", { name: "確認 signoff" }).click();
    await expect(dialog.getByText(/不可為空/)).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/13-dialog-signoff.png` });

    await dialog.getByLabel("審批者").fill("operator");
    await dialog.getByRole("button", { name: "確認 signoff" }).click();
    await expect(page.getByRole("status").filter({ hasText: `已 signoff：${name}` })).toBeVisible();
    await expect(item).toHaveCount(0);
  });

  test("目標詳情：草案橫幅 → 審批 → 橫幅消失，重新整理後仍已簽核", async ({ page, request }) => {
    await loginViaStorage(page, request);
    await page.goto(`/projects/${project.id}/goals/${goal.id}`);
    await expect(page.getByTestId("signoff-banner")).toContainText("草案未審批");
    await page.getByTestId("signoff-banner").getByRole("button", { name: "審批" }).click();
    await page.getByRole("dialog", { name: "審批 signoff：目標" }).getByRole("button", { name: "確認 signoff" }).click();
    await expect(page.getByRole("status").filter({ hasText: "已 signoff" })).toBeVisible();
    await expect(page.getByTestId("signoff-banner")).toHaveCount(0);
    await page.reload();
    await expect(page.getByTestId("goal-title")).toBeVisible();
    await expect(page.getByTestId("signoff-banner")).toHaveCount(0);
  });

  test("專案詳情：signedOff=false 顯示警示橫幅（AI 草案 — 待人工 signoff 硬閘）；審批後消失", async ({ page, request }) => {
    const t = await apiToken(request);
    const p = await apiPost<Created>(request, t, "/api/v1/projects", {
      name: uniq("E2E 橫幅專案"),
      executionPath: "/tmp/e2e-banner",
      passCriteria: "- 草案",
      draft: true,
    });
    try {
      await loginViaStorage(page, request);
      await page.goto(`/projects/${p.id}`);
      const banner = page.getByTestId("signoff-banner");
      await expect(banner).toContainText("AI 草案 — 待人工 signoff 硬閘");
      await expect(banner).toContainText("signed_off=false");
      await page.screenshot({ path: `${SHOTS}/03b-project-detail-draft-banner.png` });
      await banner.getByRole("button", { name: "審批 signoff" }).click();
      await page.getByRole("dialog").getByRole("button", { name: "確認 signoff" }).click();
      await expect(page.getByRole("status").filter({ hasText: "已 signoff" })).toBeVisible();
      await expect(banner).toHaveCount(0);
    } finally {
      await apiDelete(request, t, `/api/v1/projects/${p.id}`);
    }
  });

  test("已簽核者被他人再簽：後端 409 的原因顯示在對話框內，不關閉（保護稽核軌跡）", async ({ page, request }) => {
    const t = await apiToken(request);
    const p = await apiPost<Created>(request, t, "/api/v1/projects", {
      name: uniq("E2E 競態專案"),
      executionPath: "/tmp/e2e-race",
      passCriteria: "- 草案",
      draft: true,
    });
    try {
      await loginViaStorage(page, request);
      await page.goto(`/projects/${p.id}`);
      await page.getByTestId("signoff-banner").getByRole("button", { name: "審批 signoff" }).click();
      const dialog = page.getByRole("dialog", { name: "審批 signoff：專案" });
      // 對話框開著的期間，另一位審批者先簽了
      await apiPost(request, t, `/api/v1/projects/${p.id}/signoff`, { approver: "另一位審批者" });
      await dialog.getByRole("button", { name: "確認 signoff" }).click();
      await expect(dialog.getByRole("alert")).toContainText("不可重複簽核");
      await expect(dialog.getByRole("alert")).toContainText("traceId");
      await expect(dialog).toBeVisible();
    } finally {
      await apiDelete(request, t, `/api/v1/projects/${p.id}`);
    }
  });

  test("唯讀角色 viewer：寫入類按鈕全部停用並附說明", async ({ page, request }) => {
    const viewerPass = process.env.E2E_VIEWER_PASSWORD ?? ["Viewer", "Dev2026"].join("#");
    await loginViaStorage(page, request, "viewer", viewerPass);
    await page.goto("/projects");
    await expect(page.getByRole("button", { name: "新建專案" })).toBeDisabled();
    await page.goto(`/projects/${project.id}`);
    await expect(page.getByRole("button", { name: "編輯專案" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "刪除專案" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "新增目標" })).toBeDisabled();
    // 拖曳把手對唯讀角色不出現
    await expect(page.getByRole("button", { name: /拖曳排序/ })).toHaveCount(0);
  });
});
