import { expect, test, type Page } from "@playwright/test";

import { collectConsoleErrors, compose, installApiMock, shellHandler, signInAs, type MockHandler } from "./mockApi";

/**
 * Markdown 編輯器預覽不渲染內嵌 HTML（DEF-AC-013，P2 資安；與詳情頁 MarkdownView 一致）——route mock 版，對 production 建置：
 * 套件預設鏈的 rehype-raw 會把 Markdown 內嵌的 `<iframe srcdoc>`、`<script>`、`<img onerror>`、`<a href=javascript:>`、`<base>`、
 * `<meta http-equiv=refresh>` 建成真元素（srcdoc 與父頁同源，可讀 sessionStorage 裡的 session；儲存式：operator 存、admin 開編輯頁即中）。
 * 修法在 MarkdownEditorImpl 的 omitRawHtml＋safeUrlTransform；單元測試（markdown.test.tsx）在 jsdom 驗，這裡在真瀏覽器的 production 建置驗一次
 * （bundler 若讓 rehype-raw 的函式身分對不上，jsdom 看不到、這裡才看得到）。腳本只寫旗標與讀 sessionStorage 的鍵名，不外送任何東西。
 * 真後端版是 QA 的 p9-w7-html.spec.ts；這支不需要後端與資料庫。
 */
const P = "0c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f";
const NOW = "2026-10-17T08:30:12Z";

const IFRAME = `<iframe srcdoc="<script>parent.__w8xss='iframe-srcdoc';parent.__w8keys=Object.keys(parent.sessionStorage).join(',')</script>"></iframe>`;
/** 所有載體放進同一份文件：預覽一次渲染，任何一個被建成元素都會在下面的掃描裡現形。 */
const PAYLOAD = [
  IFRAME,
  "",
  `<script>window.__w8xss = 'script-tag'</script>`,
  "",
  `<img src="x" onerror="window.__w8xss = 'img-onerror'">`,
  "",
  `前文 <img src="y" onerror="window.__w8xss = 'img-inline'"> 後文`,
  "",
  `<a id="w8js" href="javascript:window.__w8xss='js-href'">HTML 連結</a>`,
  "",
  `[Markdown 連結](javascript:window.__w8xss='md-link') 與 <javascript:window.__w8xss='autolink'>`,
  "",
  `<meta http-equiv="refresh" content="3600;url=https://evil.example/">`,
  "",
  `<base href="https://evil.example/">`,
  "",
  `<object data="javascript:window.__w8xss='object'"></object>`,
  "",
  `<svg onload="window.__w8xss='svg-onload'"></svg>`,
  "",
  `<details open ontoggle="window.__w8xss='details-ontoggle'"><summary>摘要</summary>內容</details>`,
  "",
  "結尾",
].join("\n");

/** 預覽與文件層級的掃描：這些東西一個都不該出現。 */
async function scan(page: Page) {
  return page.evaluate(() => {
    const preview = document.querySelector(".w-md-editor-preview") as HTMLElement;
    const count = (sel: string) => preview.querySelectorAll(sel).length;
    const w = window as unknown as { __w8xss?: string; __w8keys?: string };
    return {
      fired: w.__w8xss ?? null,
      keys: w.__w8keys ?? null,
      elements: count("iframe, script, img, object, embed, form, meta, base, link, style, details, summary, [onerror], [onload], [ontoggle], [srcdoc]"),
      anchorsWithHref: count("a[href]"),
      headInjected: document.head.querySelectorAll("meta[http-equiv], base").length + document.querySelectorAll("base").length,
      text: preview.textContent ?? "",
    };
  });
}

function expectInert(r: Awaited<ReturnType<typeof scan>>) {
  expect(r.fired, "沒有任何腳本執行").toBeNull();
  expect(r.keys, "srcdoc 內的腳本沒有讀到 sessionStorage").toBeNull();
  expect(r.elements, "預覽裡沒有任何 iframe、script、img、object、form、meta、base、details 或事件屬性").toBe(0);
  expect(r.anchorsWithHref, "沒有任何帶 href 的連結（全部是 javascript: 連結，不合格的網址拿掉 href）").toBe(0);
  expect(r.headInjected, "沒有東西被搬進 document.head（React 會把 meta、link、title 搬進 head），也沒有 base").toBe(0);
  expect(r.text, "原文以文字顯示（與詳情頁相同），不是被吞掉").toContain("<iframe srcdoc=");
  expect(r.text).toContain("結尾");
}

const project = {
  id: P,
  name: "儲存式 payload 專案",
  description: PAYLOAD,
  executionPath: "/work/x",
  passCriteria: "- [ ] 通過",
  status: "DRAFT",
  autonomyLevel: 3,
  signedOff: false,
  goalsCount: 0,
  tasksCount: 0,
  tasksDone: 0,
  createdAt: NOW,
  updatedAt: NOW,
  goals: [],
};
const projectBackend: MockHandler = (call) => {
  if (call.method !== "GET") return undefined;
  if (call.path === `/api/v1/projects/${P}`) return { data: project };
  if (call.path === `/api/v1/projects/${P}/goals`) return { data: [] };
  return undefined;
};

test.describe("Markdown 編輯器預覽不渲染內嵌 HTML（route mock；DEF-AC-013）", () => {
  test.setTimeout(120_000);

  test("新建專案對話框：貼入 iframe srcdoc、script、img onerror、javascript: 連結、meta refresh、base、object、svg onload 與 details，預覽只當成文字顯示、沒有任何東西執行", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler()));
    await page.goto("/projects");
    await page.getByRole("button", { name: "新建專案" }).click();
    const dialog = page.getByRole("dialog", { name: "新建專案" });
    await dialog.getByRole("textbox", { name: "說明描述", exact: true }).fill(PAYLOAD);
    await expect(dialog.locator(".w-md-editor-preview").first()).toContainText("結尾", { timeout: 60_000 });
    await page.waitForTimeout(1500); // 給「如果會執行」的載體足夠時間（srcdoc 載入、onerror 觸發、meta refresh 計時）
    expectInert(await scan(page));
    // 左欄原始碼著色不受影響：原文逐字在、沒有建出元素
    const left = dialog.locator(".w-md-editor-text-pre").first();
    await expect(left).toContainText("<iframe srcdoc=");
    expect(await left.locator("iframe, script, img, object, svg, meta, base").count()).toBe(0);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("儲存式：專案說明已存著 iframe srcdoc payload，管理者開「編輯專案」頁，預覽不執行；同一份內容在唯讀的詳情頁也不渲染（兩處一致）", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "ADMIN"); // 受害者用管理者：腳本若在這個 session 內執行＝權限提升
    await installApiMock(page, compose(shellHandler(), projectBackend));
    await page.goto(`/projects/${P}/edit`);
    await expect(page.locator(".w-md-editor-preview").first()).toContainText("結尾", { timeout: 60_000 });
    await page.waitForTimeout(1500);
    expectInert(await scan(page));

    await page.goto(`/projects/${P}`);
    await expect(page.getByRole("heading", { name: "儲存式 payload 專案" })).toBeVisible({ timeout: 60_000 });
    await page.waitForTimeout(1000);
    expect(await page.evaluate(() => (window as unknown as { __w8xss?: string }).__w8xss ?? null), "詳情頁沒有任何腳本執行").toBeNull();
    expect(await page.locator("iframe, object, embed, [onerror], [srcdoc], [data-slot='markdown-view'] script, [data-slot='markdown-view'] img").count(), "詳情頁沒有建出任何危險元素").toBe(0);
    await expect(page.locator("[data-slot='markdown-view']", { hasText: "<iframe srcdoc=" }), "原文以文字顯示：詳情頁與編輯器預覽一致").toHaveCount(1);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("不合格網址的連結（javascript:、tel: 等）在預覽端是沒有 href 的文字：點了不導頁、不重新載入本頁，編輯中還沒存的內容不會丟；一般連結照常", async ({ page }) => {
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler()));
    await page.goto("/projects");
    await page.getByRole("button", { name: "新建專案" }).click();
    const dialog = page.getByRole("dialog", { name: "新建專案" });
    const source = "[撥號](tel:+886-2-1234-5678) 與 [壞連結](javascript:alert(1)) 與 [官網](https://example.com) 與 [站內](/projects)";
    await dialog.getByRole("textbox", { name: "說明描述", exact: true }).fill(source);
    const preview = dialog.locator(".w-md-editor-preview").first();
    await expect(preview.getByText("撥號")).toBeVisible({ timeout: 60_000 });
    for (const name of ["撥號", "壞連結"]) {
      const a = preview.locator("a", { hasText: name });
      await expect(a, `${name}：沒有 href`).not.toHaveAttribute("href", /.*/);
      await a.click();
    }
    await page.waitForTimeout(800);
    await expect(page, "沒有導頁").toHaveURL(/\/projects$/);
    await expect(dialog, "對話框還在（頁面沒有重新載入）").toBeVisible();
    await expect(dialog.getByRole("textbox", { name: "說明描述", exact: true }), "編輯中的內容還在").toHaveValue(source);
    await expect(preview.getByRole("link", { name: "官網" })).toHaveAttribute("href", "https://example.com");
    await expect(preview.getByRole("link", { name: "站內" })).toHaveAttribute("href", "/projects");
  });
});
