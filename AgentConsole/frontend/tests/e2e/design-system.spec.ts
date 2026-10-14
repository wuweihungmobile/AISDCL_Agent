import { expect, test } from "@playwright/test";

import { loginViaStorage } from "./helpers";

/**
 * 設計系統在真瀏覽器的執行期守衛（靜態規則見 tests/design-rules.test.ts）：
 * 字型（UI-DS-02）、扁平無 box-shadow（UI-DS-03，含開著的 Dialog 與 Markdown 編輯器）、2px 主色焦點環（UI-DS-05）。
 */
const noShadow = (page: import("@playwright/test").Page) =>
  page.evaluate(() =>
    [...document.querySelectorAll("*")]
      .filter((el) => {
        const s = getComputedStyle(el);
        return s.boxShadow !== "none" || s.filter.includes("drop-shadow");
      })
      .map((el) => `${el.tagName.toLowerCase()}.${(el.getAttribute("class") ?? "").split(/\s+/).slice(0, 3).join(".")}`),
  );

test("字型：內文用 Inter Variable＋Noto Sans TC Variable，且自託管（沒有對 Google Fonts 的請求）", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await page.goto("/projects");
  await expect(page.locator("body")).toHaveCSS("font-family", /Inter Variable.*Noto Sans TC Variable/);
  const loaded = await page.evaluate(async () => {
    await document.fonts.ready;
    return [...document.fonts].filter((f) => f.status === "loaded").map((f) => f.family.replace(/"/g, ""));
  });
  expect(loaded.some((f) => f.startsWith("Inter"))).toBe(true);
  // 沒有任何對 Google Fonts 的網路請求（自託管）
  const external = await page.evaluate(() =>
    performance
      .getEntriesByType("resource")
      .map((e) => e.name)
      .filter((u) => /fonts\.(googleapis|gstatic)\.com/.test(u)),
  );
  expect(external).toEqual([]);
});

test("扁平：頁面、開著的建立 Dialog 與 Markdown 編輯器裡沒有任何元素帶 box-shadow", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await page.goto("/");
  await expect(page.getByTestId("kpi-grid")).toBeVisible();
  expect(await noShadow(page)).toEqual([]);

  await page.goto("/projects");
  await page.getByRole("button", { name: "新建專案" }).click();
  await expect(page.locator(".w-md-editor").first()).toBeVisible();
  expect(await noShadow(page)).toEqual([]);
});

test("焦點環：鍵盤依序 Tab 過頂列的每個停駐點，皆為 2px 實線主色外框（搜尋框改畫在內側）", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "專案管理" })).toBeVisible();

  // 全域 transition 0.2s：toHaveCSS 會重試到過場結束
  const expectRing = async (target: import("@playwright/test").Locator, offset: string | RegExp) => {
    await expect(target).toHaveCSS("outline-style", "solid");
    await expect(target).toHaveCSS("outline-width", "2px");
    await expect(target).toHaveCSS("outline-color", "rgb(73, 132, 40)");
    await expect(target).toHaveCSS("outline-offset", offset);
  };

  // 第一個停駐點是「跳到主要內容」；之後的頂列／側欄停駐點逐一檢查（不假設順序，只要求每一站都有環）
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "跳到主要內容" })).toBeFocused();
  await expectRing(page.getByRole("link", { name: "跳到主要內容" }), "2px");
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press("Tab");
    await expectRing(page.locator(":focus"), /^-?2px$/);
  }

  // 搜尋框在白底圓角（overflow-hidden）容器內：環改畫在內側（-2px）——
  // 曾因 outline-none 把環整個吃掉，是這支測試抓到的真缺陷
  const search = page.getByRole("searchbox", { name: "搜尋專案、目標、任務" });
  await search.focus();
  await expect(search).toBeFocused();
  await expectRing(search, "-2px");
});
