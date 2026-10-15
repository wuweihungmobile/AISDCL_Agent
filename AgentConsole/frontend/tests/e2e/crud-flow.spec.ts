import { expect, test } from "@playwright/test";

import { SHOTS, fillMarkdown, loginViaUi, uniq } from "./helpers";

/**
 * 主流程（對真後端）：登入 → 新建專案 → 進詳情 → 新增兩個目標並設依賴 → 新增任務 →
 * 專案列表顯示目標 2／任務 0 / 1 → 依賴成環顯示後端原因 → 拖曳排序並重新整理後仍保持 →
 * 刪除任務／目標／專案 → 列表消失。每個重點畫面存一張截圖到 __screenshots__。
 */
test("登入 → 專案／目標／任務完整流程 → 刪除", async ({ page }) => {
  const project = uniq("E2E 專案");
  const goalA = uniq("目標甲");
  const goalB = uniq("目標乙");
  const task = uniq("任務一");
  const toast = (text: string | RegExp) => page.getByRole("status").filter({ hasText: text });

  await test.step("未登入造訪受保護頁會導向 /login，登入後導回原頁", async () => {
    await page.goto("/projects");
    await expect(page).toHaveURL(/\/login\?next=%2Fprojects/);
    await expect(page.getByRole("heading", { name: "登入 AISDLC Console" })).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/00-login.png` });
    await loginViaUi(page);
    await expect(page).toHaveURL(/\/projects$/);
  });

  await test.step("Dashboard 與專案列表（截圖）", async () => {
    await page.getByRole("navigation", { name: "主導覽" }).getByRole("link", { name: "儀表板" }).click();
    await expect(page.getByRole("heading", { name: "總覽儀表板" })).toBeVisible();
    await expect(page.getByTestId("kpi-grid")).toBeVisible();
    // 「本週完成任務數」已接真值（W4-F2：各專案 task-trend 加總），載入完成後是一個整數
    await expect(page.getByTestId("kpi-week-done")).toHaveText(/^\d+$/);
    await page.screenshot({ path: `${SHOTS}/01-dashboard.png` });
    await page.getByRole("navigation", { name: "主導覽" }).getByRole("link", { name: "專案管理" }).click();
    await expect(page.getByRole("heading", { name: "專案管理" })).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/02-projects.png` });
  });

  await test.step("新建專案（Dialog：名稱空 → 行內錯誤；填妥後建立）", async () => {
    await page.getByRole("button", { name: "新建專案" }).click();
    const dialog = page.getByRole("dialog", { name: "新建專案" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "建立" }).click();
    await expect(dialog.getByText("名稱不能為空")).toBeVisible();
    await expect(dialog.getByText("通過標準不能為空")).toBeVisible();

    await dialog.getByLabel("專案名稱").fill(project);
    await dialog.getByLabel("執行路徑").fill("relative/path");
    await dialog.getByRole("button", { name: "建立" }).click();
    await expect(dialog.getByText(/必須是絕對路徑/)).toBeVisible();

    await dialog.getByLabel("執行路徑").fill("/tmp/e2e-console");
    await fillMarkdown(dialog, "說明描述", "## 概述\n\n端對端測試建立的專案。");
    await fillMarkdown(dialog, "通過標準", "- 所有單元測試通過\n- [x] 已完成項目\n- [ ] 待辦項目");
    await dialog.getByLabel(/自治等級/).fill("4");
    await page.screenshot({ path: `${SHOTS}/10-dialog-project-create.png` });
    await dialog.getByRole("button", { name: "建立" }).click();
    await expect(toast(`已建立專案「${project}」`)).toBeVisible();
    await expect(dialog).toBeHidden();
  });

  await test.step("進專案詳情：基本資訊與 Markdown 渲染", async () => {
    const card = page.getByTestId("project-card").filter({ hasText: project });
    await expect(card).toBeVisible();
    await expect(card).toContainText("Lv.4 自治");
    await card.getByRole("link", { name: project }).click();
    await expect(page.getByTestId("project-title")).toHaveText(project);
    await expect(page.getByTestId("project-path")).toHaveText("/tmp/e2e-console");
    await expect(page.getByRole("heading", { name: "概述" })).toBeVisible();
    await expect(page.getByRole("checkbox").first()).toBeVisible(); // 通過標準的 checklist
    await expect(page.getByTestId("signoff-banner")).toHaveCount(0); // 手動建立＝已 signoff
  });

  await test.step("新增目標甲，再新增目標乙並設前置依賴＝甲", async () => {
    await page.getByRole("button", { name: "新增目標" }).click();
    let dialog = page.getByRole("dialog", { name: "新建目標" });
    await dialog.getByLabel("目標名稱").fill(goalA);
    await fillMarkdown(dialog, "通過標準", "- [ ] 甲的通過標準");
    await dialog.getByRole("button", { name: "建立" }).click();
    await expect(toast(`已建立目標「${goalA}」`)).toBeVisible();
    await expect(page.getByTestId("goal-row")).toHaveCount(1);

    await page.getByRole("button", { name: "新增目標" }).click();
    dialog = page.getByRole("dialog", { name: "新建目標" });
    await dialog.getByLabel("目標名稱").fill(goalB);
    await fillMarkdown(dialog, "說明描述", "乙依賴甲。");
    await fillMarkdown(dialog, "通過標準", "- [ ] 乙的通過標準");
    await dialog.getByRole("checkbox", { name: new RegExp(goalA) }).click();
    await page.screenshot({ path: `${SHOTS}/11-dialog-goal-dependency.png` });
    await dialog.getByRole("button", { name: "建立" }).click();
    await expect(toast(`已建立目標「${goalB}」`)).toBeVisible();
    await expect(page.getByTestId("goal-row")).toHaveCount(2);
    await page.screenshot({ path: `${SHOTS}/03-project-detail.png` });
  });

  await test.step("目標乙詳情：前置依賴 chips、草案橫幅不出現；新增任務", async () => {
    await page.getByTestId("goal-row").filter({ hasText: goalB }).getByRole("link", { name: goalB }).click();
    await expect(page.getByTestId("goal-title")).toHaveText(goalB);
    await expect(page.getByTestId("goal-deps")).toContainText(goalA);
    await expect(page.getByTestId("signoff-banner")).toHaveCount(0);

    await page.getByRole("button", { name: "新增任務" }).click();
    const dialog = page.getByRole("dialog", { name: "新建任務" });
    await dialog.getByLabel("任務名稱").fill(task);
    await fillMarkdown(dialog, "說明描述", "以 `pytest` 驗證。");
    await fillMarkdown(dialog, "通過標準", "- [ ] 測試全綠");
    await dialog.getByLabel("驗證命令").fill("echo hi; rm -rf /");
    await dialog.getByRole("button", { name: "建立" }).click();
    await expect(dialog.getByText(/不可包含/)).toBeVisible(); // 前端即時驗證 NFR-SEC-03
    await dialog.getByLabel("驗證命令").fill("pytest -q");
    await dialog.getByLabel("期望輸出 Regex").fill("OK");
    await dialog.getByLabel("最大重試次數").fill("2");
    await dialog.getByRole("button", { name: "建立" }).click();
    await expect(toast(`已建立任務「${task}」`)).toBeVisible();
    await expect(page.getByTestId("task-row")).toHaveCount(1);
    await page.screenshot({ path: `${SHOTS}/04-goal-detail.png` });
  });

  await test.step("任務詳情：指標卡、日誌面板、重試鈕在 PENDING 時停用", async () => {
    await page.getByTestId("task-row").getByRole("link", { name: task }).first().click();
    await expect(page.getByTestId("task-title")).toHaveText(task);
    await expect(page.getByTestId("metric-retries")).toHaveText("0 / 2");
    await expect(page.getByTestId("metric-tokens")).toHaveText("—");
    await expect(page.getByTestId("task-meta")).toContainText(project);
    await expect(page.getByTestId("task-meta")).toContainText(goalB);
    await expect(page.getByRole("log", { name: "執行日誌" })).toContainText("尚無執行日誌");
    await expect(page.getByRole("button", { name: "重試" })).toBeDisabled();
    await page.screenshot({ path: `${SHOTS}/05-task-detail.png` });
  });

  await test.step("編輯任務：改最大重試次數與說明，詳情頁即時更新", async () => {
    await page.getByRole("button", { name: "編輯", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "編輯任務" });
    await expect(dialog.getByLabel("任務名稱")).toHaveValue(task);
    await expect(dialog.getByLabel("驗證命令")).toHaveValue("pytest -q");
    await dialog.getByLabel("最大重試次數").fill("5");
    await fillMarkdown(dialog, "說明描述", "已改寫的說明。");
    await dialog.getByRole("button", { name: "儲存" }).click();
    await expect(toast(`已更新任務「${task}」`)).toBeVisible();
    await expect(dialog).toBeHidden();
    await expect(page.getByTestId("metric-retries")).toHaveText("0 / 5");
    await expect(page.getByText("已改寫的說明。")).toBeVisible();
  });

  await test.step("專案列表顯示：目標 2、任務 0 / 1", async () => {
    await page.getByRole("navigation", { name: "主導覽" }).getByRole("link", { name: "專案管理" }).click();
    const card = page.getByTestId("project-card").filter({ hasText: project });
    await expect(card).toContainText("目標 2");
    await expect(card).toContainText("任務 0 / 1");
  });

  await test.step("目標甲改依賴乙 → 後端 400 依賴成環，原因與名稱顯示在欄位下", async () => {
    await page.getByTestId("project-card").filter({ hasText: project }).getByRole("link", { name: project }).click();
    await page.getByTestId("goal-row").filter({ hasText: goalA }).getByRole("link", { name: goalA }).first().click();
    await page.getByRole("button", { name: "編輯目標" }).click();
    const dialog = page.getByRole("dialog", { name: "編輯目標" });
    await expect(dialog.getByLabel("目標名稱")).toHaveValue(goalA);
    await dialog.getByRole("checkbox", { name: new RegExp(goalB) }).click();
    await dialog.getByRole("button", { name: "儲存" }).click();
    await expect(dialog.getByText(/依賴成環/)).toBeVisible();
    await expect(dialog.getByText(new RegExp(`${goalA} → ${goalB} → ${goalA}`))).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/12-dialog-goal-cycle-error.png` });
    await dialog.getByRole("button", { name: "取消" }).click();
    await expect(dialog).toBeHidden();
  });

  await test.step("拖曳排序目標（指標拖曳）→ PUT reorder，重新整理後順序保持", async () => {
    await page.getByRole("link", { name: "返回專案" }).click();
    const rows = page.getByTestId("goal-row");
    await expect(rows).toHaveCount(2);
    await expect(rows.nth(0)).toContainText(goalA);
    const handle = page.getByRole("button", { name: `拖曳排序：${goalB}` });
    const box = (await handle.boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2, box.y - 30, { steps: 8 });
    await page.mouse.move(box.x + box.width / 2, box.y - 70, { steps: 8 });
    await page.mouse.up();
    await expect(toast("已更新目標順序")).toBeVisible();
    await expect(rows.nth(0)).toContainText(goalB);
    await page.reload();
    await expect(page.getByTestId("goal-row").nth(0)).toContainText(goalB);
  });

  await test.step("刪除任務 → 目標 → 專案，列表中消失", async () => {
    // 任務
    await page.getByTestId("goal-row").filter({ hasText: goalB }).getByRole("link", { name: goalB }).first().click();
    await page.getByTestId("task-row").getByRole("link", { name: task }).first().click();
    await page.getByRole("button", { name: "刪除" }).click();
    await expect(page.getByRole("dialog", { name: "刪除任務" })).toBeVisible();
    await page.getByRole("button", { name: "確認刪除" }).click();
    await expect(toast(`已刪除任務「${task}」`)).toBeVisible();
    await expect(page.getByTestId("goal-title")).toHaveText(goalB);
    await expect(page.getByTestId("task-row")).toHaveCount(0);
    // 目標乙、目標甲
    await page.getByRole("button", { name: "刪除目標" }).click();
    await page.getByRole("button", { name: "確認刪除" }).click();
    await expect(toast(`已刪除目標「${goalB}」`)).toBeVisible();
    await expect(page.getByTestId("project-title")).toHaveText(project);
    await page.getByTestId("goal-row").getByRole("link", { name: goalA }).first().click();
    await page.getByRole("button", { name: "刪除目標" }).click();
    await page.getByRole("button", { name: "確認刪除" }).click();
    await expect(toast(`已刪除目標「${goalA}」`)).toBeVisible();
    await expect(page.getByTestId("goal-row")).toHaveCount(0);
    // 專案
    await page.getByRole("button", { name: "刪除專案" }).click();
    await page.getByRole("button", { name: "確認刪除" }).click();
    await expect(page).toHaveURL(/\/projects$/);
    await expect(page.getByTestId("project-card").filter({ hasText: project })).toHaveCount(0);
  });
});
