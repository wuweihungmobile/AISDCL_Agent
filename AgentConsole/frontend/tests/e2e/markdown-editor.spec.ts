import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

import { SHOTS, fillMarkdown, loginViaStorage } from "./helpers";

/**
 * Markdown 編輯器八項功能（RTM UI-MD-01～08，PRD §5.1.4）——真瀏覽器、對真後端登入：
 * 在「新建專案」Dialog 的「說明描述」欄逐項實操（即時預覽、原始碼著色、工具列、GFM 表格、程式碼區塊語言高亮、
 * Checklist、匯入 .md、匯出 .md）。只開 Dialog、不送出，因此不在資料庫留資料。
 */
const DOC = [
  "## 標題二",
  "",
  "這是 **粗體** 與 *斜體*。",
  "",
  "| 欄位 | 說明 |",
  "| --- | --- |",
  "| A | 第一列 |",
  "",
  "```ts",
  "const answer: number = 42;",
  "```",
  "",
  "- [x] 已完成",
  "- [ ] 待辦",
].join("\n");

const TOOLBAR = ["bold", "italic", "strikethrough", "quote", "link", "code", "codeBlock", "table", "unordered-list", "ordered-list", "checked-list"];

test.describe("Markdown 編輯器（UI-MD-01～08）", () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaStorage(page, request);
    await page.goto("/projects");
    await page.getByRole("button", { name: "新建專案" }).click();
    await expect(page.getByRole("dialog", { name: "新建專案" })).toBeVisible();
    await expect(page.locator(".w-md-editor").first()).toBeVisible();
  });

  const editor = (page: import("@playwright/test").Page) => page.getByRole("dialog", { name: "新建專案" }).locator(".w-md-editor").first();
  const box = (page: import("@playwright/test").Page) => page.getByRole("dialog", { name: "新建專案" }).locator('[data-slot="markdown-editor"]').first();
  const textarea = (page: import("@playwright/test").Page) => page.getByRole("dialog", { name: "新建專案" }).getByRole("textbox", { name: "說明描述", exact: true });

  test("UI-MD-01／04／05／06：左原始碼右預覽（live）、輸入後預覽即時渲染標題、GFM 表格、程式碼區塊語言高亮、Checklist 核取方塊", async ({ page }) => {
    const dialog = page.getByRole("dialog", { name: "新建專案" });
    await expect(editor(page).locator(".w-md-editor-input")).toBeVisible(); // 左：原始碼
    await expect(editor(page).locator(".w-md-editor-preview")).toBeVisible(); // 右：預覽
    await fillMarkdown(dialog, "說明描述", DOC);
    const preview = editor(page).locator(".w-md-editor-preview");
    await expect(preview.getByRole("heading", { name: "標題二", level: 2 })).toBeVisible();
    await expect(preview.locator("strong")).toHaveText("粗體");
    await expect(preview.locator("em")).toHaveText("斜體");
    // GFM 表格：兩欄表頭、一列資料
    await expect(preview.locator("table th")).toHaveText(["欄位", "說明"]);
    await expect(preview.locator("table td")).toHaveText(["A", "第一列"]);
    // 程式碼區塊與語言高亮：<code class="hljs language-ts code-highlight">，內容被切成 prism 的 token span（實測 DOM；與單元測試看到的 hljs class 不同）
    const code = preview.locator("pre code.language-ts");
    await expect(code).toContainText("const answer");
    await expect(code).toHaveClass(/hljs/);
    await expect(code.locator(".token.keyword").first()).toHaveText("const");
    await expect(code.locator(".token.number").first()).toHaveText("42");
    // Checklist：兩個核取方塊，第一個已勾、第二個未勾
    const checks = preview.getByRole("checkbox");
    await expect(checks).toHaveCount(2);
    await expect(checks.nth(0)).toBeChecked();
    await expect(checks.nth(1)).not.toBeChecked();
    await page.screenshot({ path: `${SHOTS}/30-markdown-editor.png` });
  });

  test("UI-MD-02：編輯區是 Markdown 原始碼著色（prism token：標題、粗體、程式碼區塊標記…）", async ({ page }) => {
    await fillMarkdown(page.getByRole("dialog", { name: "新建專案" }), "說明描述", DOC);
    const pre = editor(page).locator(".w-md-editor-text-pre");
    await expect(pre.locator(".token.title").first()).toBeVisible();
    await expect(pre.locator(".token.bold").first()).toBeVisible();
    await expect(pre.locator(".token.code").first()).toBeVisible();
    await expect(pre.locator(".token.table").first()).toBeVisible();
  });

  test("UI-MD-03：常用語法工具列（標題、粗體、斜體、刪除線、引用、連結、行內碼、程式碼區塊、表格、無序／有序／核取清單）；按下去會把語法寫進原始碼", async ({ page }) => {
    for (const name of TOOLBAR) {
      await expect(editor(page).locator(`.w-md-editor-toolbar button[data-name="${name}"]`), `工具列缺少 ${name}`).toHaveCount(1);
    }
    await expect(editor(page).locator('.w-md-editor-toolbar button[data-name="title"]'), "標題按鈕（含下拉）").toHaveCount(1);
    const ta = textarea(page);
    await ta.fill("");
    await editor(page).locator('.w-md-editor-toolbar button[data-name="bold"]').click();
    await expect(ta).toHaveValue(/\*\*.*\*\*/);
    await ta.fill("");
    await editor(page).locator('.w-md-editor-toolbar button[data-name="checked-list"]').click();
    await expect(ta).toHaveValue(/- \[ \]/);
    await ta.fill("");
    await editor(page).locator('.w-md-editor-toolbar button[data-name="table"]').click();
    await expect(ta).toHaveValue(/\|.*\|/);
  });

  test("UI-MD-07：匯入 .md——讀入本機檔案並覆蓋欄位、成功提示；不支援的副檔名被擋下並提示、欄位不變", async ({ page }) => {
    const ta = textarea(page);
    await page
      .getByTestId("md-import-input")
      .first()
      .setInputFiles({ name: "spec.md", mimeType: "text/markdown", buffer: Buffer.from(DOC, "utf-8") });
    await expect(ta).toHaveValue(DOC);
    await expect(page.getByRole("status").filter({ hasText: "已匯入 spec.md" })).toBeVisible();
    await page
      .getByTestId("md-import-input")
      .first()
      .setInputFiles({ name: "evil.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4", "utf-8") });
    await expect(page.getByRole("status").filter({ hasText: "只支援 .md／.markdown／.txt 文字檔" })).toBeVisible();
    await expect(ta, "被拒絕的檔案不改動欄位").toHaveValue(DOC);
    await page
      .getByTestId("md-import-input")
      .first()
      .setInputFiles({ name: "big.md", mimeType: "text/markdown", buffer: Buffer.alloc(1024 * 1024 + 1, 0x61) });
    await expect(page.getByRole("status").filter({ hasText: "檔案超過 1 MB 上限" })).toBeVisible();
    await expect(ta, "超過 1 MB 的檔案不改動欄位").toHaveValue(DOC);
  });

  test("UI-MD-08：匯出 .md——欄位空白時停用；有內容時下載 .md 檔，內容與欄位逐字相同，並有成功提示", async ({ page }) => {
    const exportBtn = box(page).getByRole("button", { name: "匯出 .md" });
    await expect(exportBtn).toBeDisabled();
    await fillMarkdown(page.getByRole("dialog", { name: "新建專案" }), "說明描述", DOC);
    await expect(exportBtn).toBeEnabled();
    const [download] = await Promise.all([page.waitForEvent("download"), exportBtn.click()]);
    expect(download.suggestedFilename()).toMatch(/\.md$/);
    const saved = await download.path();
    expect(readFileSync(saved, "utf-8")).toBe(DOC);
    await expect(page.getByRole("status").filter({ hasText: /已匯出 .+\.md/ })).toBeVisible();
  });
});
