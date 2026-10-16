import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { RUN, loginViaStorage } from "./helpers";
import { collectConsoleErrors } from "./mockApi";
import { DEFECTS_OPEN, E2E_ROOT, NEEDS_BRIDGE, call, dataOf, ensureQuota, signIn } from "./realBackend";

/**
 * W7 複驗：FE 回填檔〈九〉第 3 點留給「另案評估」的疑慮——Markdown 編輯器的預覽走套件預設鏈的 rehype-raw，內嵌的 HTML 會變成真元素。
 * FE 沒有驗證「腳本類元素」的處置，QA 在這裡探測，並把結果分成三層：
 *  ① 編輯器預覽：img onerror、script 標籤、javascript: 連結三種載體都不執行（正向斷言，通過）。
 *  ② DEF-AC-013（P2）：同一個預覽裡 `<iframe srcdoc>` 內的腳本**會**執行（srcdoc 與父頁同源，可讀 sessionStorage 內的 session）——用 test.fail(DEFECTS_OPEN) 釘住。
 *  ③ 已儲存的內容：專案說明含 iframe srcdoc 時，管理者開「編輯專案」頁（編輯器預覽會渲染儲存的內容）腳本同樣執行（DEF-AC-013 的儲存式向量，test.fail 釘住）；
 *     同一份內容在唯讀的專案詳情頁（react-markdown，不渲染原始 HTML）不會執行（對照，通過）。
 * 這支不改任何產品行為；腳本只做「寫一個旗標」與「讀 sessionStorage 的鍵名（不讀值、不外送）」。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const SAFE_PAYLOAD = [
  '<img src="x" onerror="window.__w7xss = \'img-onerror\'">',
  "",
  "<script>window.__w7xss = 'script-tag'</script>",
  "",
  '<a id="w7js" href="javascript:window.__w7xss=\'js-href\'">點我</a>',
  "",
  "<details><summary>摘要</summary>內容</details>",
].join("\n");

// 腳本只寫旗標與 sessionStorage 的「鍵名」（值不讀、不外送）；srcdoc 的文件與父頁同源，所以 parent.* 可直接存取
const IFRAME_PAYLOAD = [
  "<iframe srcdoc=\"<script>parent.__w7xss='iframe-srcdoc';parent.__w7keys=Object.keys(parent.sessionStorage).join(',')</script>\"></iframe>",
  "",
  "<details><summary>摘要</summary>內容</details>",
].join("\n");

type Probe = { fired: string | null; keys: string | null };
const probe = (page: Page): Promise<Probe> =>
  page.evaluate(() => {
    const w = window as unknown as { __w7xss?: string; __w7keys?: string };
    return { fired: w.__w7xss ?? null, keys: w.__w7keys ?? null };
  });

async function fillCreateDialog(page: Page, text: string): Promise<void> {
  await page.goto("/projects");
  await page.getByRole("button", { name: "新建專案" }).click();
  const dialog = page.getByRole("dialog", { name: "新建專案" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("textbox", { name: "說明描述", exact: true }).fill(text);
  await expect(dialog.locator(".w-md-editor-preview").first()).toContainText("摘要"); // 預覽已渲染到最後一段（不論 HTML 被建成元素或被當成文字）
}

let savedProjectId = "";

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 40);
  await ensureQuota(request, "admin", 40);
});

test.afterAll(async ({ request }) => {
  if (savedProjectId) await call(request, "operator", "DELETE", `/api/v1/projects/${savedProjectId}`);
});

test("① 編輯器預覽：img onerror、script 標籤、javascript: 連結都不執行", async ({ page, request }) => {
  const errors = collectConsoleErrors(page);
  const popups: Page[] = [];
  page.context().on("page", (p) => popups.push(p));
  await loginViaStorage(page, request);
  await fillCreateDialog(page, SAFE_PAYLOAD);
  const preview = page.getByRole("dialog", { name: "新建專案" }).locator(".w-md-editor-preview").first();
  const built = await preview.evaluate((el) => {
    const count = (sel: string) => el.querySelectorAll(sel).length;
    const a = el.querySelector<HTMLAnchorElement>("#w7js");
    return {
      img: count("img"),
      imgHasOnerror: el.querySelector("img")?.hasAttribute("onerror") ?? false,
      script: count("script"),
      anchorHref: a?.getAttribute("href") ?? null,
      details: count("details"),
    };
  });
  const link = preview.locator("#w7js"); // 點「點我」：javascript: 連結若沒被擋，這一下會執行
  if ((await link.count()) > 0) await link.click().catch(() => undefined);
  await page.waitForTimeout(1500);
  const fired = await probe(page);
  const poppedFired = await Promise.all(popups.map((p) => p.evaluate(() => (window as unknown as { __w7xss?: string }).__w7xss ?? null).catch(() => "（無法讀取）")));
  console.log(
    `[w7-html] ①預覽端建出的元素＝${JSON.stringify(built)}；window.__w7xss＝${JSON.stringify(fired.fired)}；點連結後開出的視窗數＝${popups.length}、其 __w7xss＝${JSON.stringify(poppedFired)}；主控台錯誤數＝${errors.length}${errors.length > 0 ? `（${errors.map((e) => e.slice(0, 160)).join(" ／ ")}）` : ""}`,
  );
  expect(fired.fired, "img onerror、script 標籤、javascript: 連結都沒有執行").toBeNull();
  expect(
    poppedFired.filter((v) => v !== null && v !== "（無法讀取）"),
    "點連結開出的視窗裡也沒有腳本執行",
  ).toEqual([]);
});

test("② DEF-AC-013（P2）：編輯器預覽裡 <iframe srcdoc> 內的腳本不應執行（目前會執行，釘住）", async ({ page, request }) => {
  test.fail(DEFECTS_OPEN, "DEF-AC-013：編輯器預覽走 rehype-raw，iframe srcdoc 內的腳本與父頁同源並執行；修好後這支會意外通過，請移除本行");
  await loginViaStorage(page, request);
  await fillCreateDialog(page, IFRAME_PAYLOAD);
  await page.waitForTimeout(1500);
  const r = await probe(page);
  console.log(`[w7-html] ②DEF-AC-013 預覽端：window.__w7xss＝${JSON.stringify(r.fired)}；srcdoc 內腳本讀到的 sessionStorage 鍵名＝${JSON.stringify(r.keys)}（只讀鍵名，不讀值）`);
  expect(r.fired, "iframe srcdoc 內的腳本不應在預覽端執行").toBeNull();
});

test.describe("已儲存的專案說明含 iframe srcdoc", () => {
  test.beforeAll(async ({ request }) => {
    const dir = path.join(E2E_ROOT, "projects", `w7_html_${RUN}`);
    mkdirSync(dir, { recursive: true });
    const r = await call(request, "operator", "POST", "/api/v1/projects", {
      name: `QA W7 內嵌 HTML ${RUN}`,
      executionPath: dir,
      passCriteria: "- 無",
      description: IFRAME_PAYLOAD,
      autonomyLevel: 3,
      draft: true,
    });
    expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(201);
    savedProjectId = dataOf<{ id: string }>(r).id;
  });

  test("③ DEF-AC-013（P2，儲存式）：管理者開「編輯專案」頁，儲存的 iframe srcdoc 不應在編輯器預覽執行（目前會執行，釘住）", async ({ page, request }) => {
    test.fail(DEFECTS_OPEN, "DEF-AC-013：儲存的說明在編輯頁預覽被渲染成真 iframe 並執行；修好後這支會意外通過，請移除本行");
    await signIn(page, request, "admin"); // 受害者用管理者：腳本在管理者的 session 內執行＝權限提升的向量
    await page.goto(`/projects/${savedProjectId}/edit`);
    await expect(page.locator(".w-md-editor-preview").first()).toContainText("摘要", { timeout: 60_000 });
    await page.waitForTimeout(1500);
    const r = await probe(page);
    console.log(`[w7-html] ③DEF-AC-013 儲存式（admin 開編輯頁）：window.__w7xss＝${JSON.stringify(r.fired)}；srcdoc 內腳本讀到的 sessionStorage 鍵名＝${JSON.stringify(r.keys)}（只讀鍵名，不讀值）`);
    expect(r.fired, "儲存的 iframe srcdoc 不應在編輯頁預覽執行").toBeNull();
  });

  test("④ 對照：同一份內容在唯讀的專案詳情頁不執行（react-markdown 不渲染原始 HTML）", async ({ page, request }) => {
    await signIn(page, request, "admin");
    await page.goto(`/projects/${savedProjectId}`);
    await expect(page.getByRole("heading", { name: `QA W7 內嵌 HTML ${RUN}` })).toBeVisible({ timeout: 60_000 });
    await page.waitForTimeout(1500);
    const r = await probe(page);
    const iframes = await page.locator("iframe").count();
    console.log(`[w7-html] ④唯讀詳情頁：window.__w7xss＝${JSON.stringify(r.fired)}；頁面內 iframe 元素數＝${iframes}`);
    expect(r.fired, "唯讀檢視不執行腳本").toBeNull();
    expect(iframes, "唯讀檢視沒有把 iframe 建成真元素").toBe(0);
  });
});
