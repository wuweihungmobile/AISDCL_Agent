import { expect, test } from "@playwright/test";

import { SHOTS, loginViaStorage } from "./helpers";

/**
 * 圖表 spike 的回歸守衛：Tremor Raw AreaChart（recharts 2.15）在 Tailwind 4／React 19 下真的畫出面積與座標軸。
 * （曾踩到的坑：react-is 版本不符時圖表缺 Area／YAxis 且沒有任何錯誤——所以不能只看「頁面沒報錯」。）
 */
test("Dashboard 專案狀態分佈圖：面積線用主色、座標軸有刻度、附文字替代說明", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await page.goto("/");
  const card = page.getByTestId("status-chart-card");
  await expect(card).toBeVisible();
  const curve = card.locator(".recharts-area-curve");
  await expect(curve).toHaveCount(1);
  await expect(card.locator(".recharts-yAxis .recharts-cartesian-axis-tick")).not.toHaveCount(0);
  // 線色＝設計 token --color-primary（#498428）
  await expect(curve).toHaveCSS("stroke", "rgb(73, 132, 40)");
  await expect(card.getByRole("img", { name: /專案狀態分佈圖：草稿 \d+、就緒 \d+、執行中 \d+/ })).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/01b-dashboard-chart.png`, fullPage: false });
});
