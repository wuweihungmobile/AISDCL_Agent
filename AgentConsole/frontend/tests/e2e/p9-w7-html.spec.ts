import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

import { RUN, loginViaStorage } from "./helpers";
import { collectConsoleErrors } from "./mockApi";
import { E2E_ROOT, NEEDS_BRIDGE, call, dataOf, ensureQuota, signIn } from "./realBackend";

/**
 * W7 複驗：FE 回填檔〈九〉第 3 點留給「另案評估」的疑慮——Markdown 編輯器的預覽走套件預設鏈的 rehype-raw，內嵌的 HTML 會變成真元素。
 * FE 沒有驗證「腳本類元素」的處置，QA 在這裡探測，並把結果分成三層。W7 第一輪發現 DEF-AC-013（P2 資安：②③ 修前會執行，當時以 test.fail 釘住），
 * W8 修於 `85ed0915`（預覽端拿掉預設鏈的 rehype-raw）；W8 複驗起這支全部是正向斷言，沒有任何 test.fail：
 *  ① 編輯器預覽：img onerror、script 標籤、javascript: 連結三種載體都不執行。
 *  ② DEF-AC-013（P2，W8 已修於 85ed0915）：同一個預覽裡 `<iframe srcdoc>` 內的腳本不執行（修前會執行：srcdoc 與父頁同源，可讀 sessionStorage 內的 session）。
 *  ③ 已儲存的內容（DEF-AC-013 的儲存式向量，W8 已修於 85ed0915）：專案說明含 iframe srcdoc 時，管理者開「編輯專案」頁（編輯器預覽會渲染儲存的內容）腳本不執行；
 *     ④ 同一份內容在唯讀的專案詳情頁（react-markdown，不渲染原始 HTML）同樣不執行（對照）。
 * W8 複驗（FE 修好 DEF-AC-013 之後）再加：
 *  ⑤ `<meta http-equiv=refresh>` 與 `<base href>`：修前會被 React 19 搬進 document.head／文件（FE 新發現，QA 清單上原本沒逐一驗）；修後原文以文字顯示、文件裡兩者都是 0（新建專案的預覽、已儲存內容的編輯頁、唯讀詳情頁）。
 *  ⑥ 連結協定白名單：https 與 mailto 保有 href；javascript: 與 tel: 不在 react-markdown 預設白名單內，整個拿掉 href（無 href 的文字；`tel:` 是主控裁決接受的取捨，PRD 沒有要求）——預覽端與詳情頁一致。
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

// meta refresh 設一小時後才跳（修前的建置中它真的會被放進 head，測試不能被它導走）；base 指向不會有人聽的埠
const META_BASE_PAYLOAD = [
  '<meta http-equiv="refresh" content="3600;url=http://127.0.0.1:9/w7-meta-refresh">',
  "",
  '<base href="http://127.0.0.1:9/w7-base/">',
  "",
  "<details><summary>摘要</summary>內容</details>",
].join("\n");

// https 與 mailto 在白名單內；tel: 與 javascript: 不在
const LINKS_PAYLOAD = [
  "[官網](https://example.com/w7)",
  "",
  "[寄信](mailto:qa@example.com)",
  "",
  "[撥號](tel:+886123456789)",
  "",
  "[腳本](javascript:window.__w7xss='md-js-link')",
  "",
  "<details><summary>摘要</summary>內容</details>",
].join("\n");

const STORED_PAYLOAD = [META_BASE_PAYLOAD, "", LINKS_PAYLOAD].join("\n");

type Probe = { fired: string | null; keys: string | null };
const probe = (page: Page): Promise<Probe> =>
  page.evaluate(() => {
    const w = window as unknown as { __w7xss?: string; __w7keys?: string };
    return { fired: w.__w7xss ?? null, keys: w.__w7keys ?? null };
  });

// 文件層：meta refresh 與 base 不得進文件（Next.js 本身不放這兩個，基線＝0）
const docProbe = (page: Page): Promise<{ metaRefresh: number; base: number }> =>
  page.evaluate(() => ({
    metaRefresh: document.querySelectorAll('meta[http-equiv="refresh" i]').length,
    base: document.querySelectorAll("base").length,
  }));

type LinkInfo = { hasHref: boolean; href: string | null };
const linksIn = (scope: Locator): Promise<Record<string, LinkInfo>> =>
  scope.evaluateAll((els) => {
    const out: Record<string, { hasHref: boolean; href: string | null }> = {};
    for (const el of els) {
      for (const a of Array.from(el.querySelectorAll("a"))) out[(a.textContent ?? "").trim()] = { hasHref: a.hasAttribute("href"), href: a.getAttribute("href") };
    }
    return out;
  });

function expectLinkPolicy(links: Record<string, LinkInfo>, where: string): void {
  expect(links["官網"], `${where}：https 連結保有 href`).toEqual({ hasHref: true, href: "https://example.com/w7" });
  expect(links["寄信"], `${where}：mailto 連結保有 href`).toEqual({ hasHref: true, href: "mailto:qa@example.com" });
  expect(links["撥號"], `${where}：tel: 不在白名單，整個拿掉 href（無 href 的文字；主控裁決接受）`).toEqual({ hasHref: false, href: null });
  expect(links["腳本"], `${where}：javascript: 不在白名單，整個拿掉 href`).toEqual({ hasHref: false, href: null });
}

async function fillCreateDialog(page: Page, text: string): Promise<void> {
  await page.goto("/projects");
  await page.getByRole("button", { name: "新建專案" }).click();
  const dialog = page.getByRole("dialog", { name: "新建專案" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("textbox", { name: "說明描述", exact: true }).fill(text);
  await expect(dialog.locator(".w-md-editor-preview").first()).toContainText("摘要"); // 預覽已渲染到最後一段（不論 HTML 被建成元素或被當成文字）
}

let savedProjectId = "";
let storedProjectId = "";

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 40);
  await ensureQuota(request, "admin", 40);
});

test.afterAll(async ({ request }) => {
  if (savedProjectId) await call(request, "operator", "DELETE", `/api/v1/projects/${savedProjectId}`);
  if (storedProjectId) await call(request, "operator", "DELETE", `/api/v1/projects/${storedProjectId}`);
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

test("② DEF-AC-013（P2，W8 修於 85ed0915）：編輯器預覽裡 <iframe srcdoc> 內的腳本不執行", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await fillCreateDialog(page, IFRAME_PAYLOAD);
  await page.waitForTimeout(1500);
  const r = await probe(page);
  console.log(`[w7-html] ②DEF-AC-013 預覽端：window.__w7xss＝${JSON.stringify(r.fired)}；srcdoc 內腳本讀到的 sessionStorage 鍵名＝${JSON.stringify(r.keys)}（只讀鍵名，不讀值）`);
  expect(r.fired, "iframe srcdoc 內的腳本不應在預覽端執行").toBeNull();
});

test("⑤ meta refresh 與 base：新建專案的預覽不得把它們放進文件，原文以文字顯示", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await page.goto("/projects");
  const before = await docProbe(page);
  await fillCreateDialog(page, META_BASE_PAYLOAD);
  const preview = page.getByRole("dialog", { name: "新建專案" }).locator(".w-md-editor-preview").first();
  await page.waitForTimeout(1000);
  const after = await docProbe(page);
  console.log(
    `[w7-html] ⑤新建專案預覽：貼入前文件＝${JSON.stringify(before)}；貼入後文件＝${JSON.stringify(after)}；預覽文字含 http-equiv＝${((await preview.textContent()) ?? "").includes("http-equiv")}`,
  );
  expect(before, "基線：Next.js 本身不放 meta refresh 與 base").toEqual({ metaRefresh: 0, base: 0 });
  expect(after, "貼入 meta refresh 與 base 之後文件裡仍然沒有它們").toEqual({ metaRefresh: 0, base: 0 });
  await expect(preview, "原文以文字顯示").toContainText("http-equiv");
});

test("⑥ 連結協定白名單（新建專案的預覽）：https 與 mailto 保有 href；javascript: 與 tel: 整個拿掉 href，點了不動作", async ({ page, request }) => {
  await loginViaStorage(page, request);
  await fillCreateDialog(page, LINKS_PAYLOAD);
  const preview = page.getByRole("dialog", { name: "新建專案" }).locator(".w-md-editor-preview").first();
  const links = await linksIn(preview);
  const urlBefore = page.url();
  await preview.getByText("撥號", { exact: true }).click();
  await preview.getByText("腳本", { exact: true }).click();
  await page.waitForTimeout(800);
  const fired = await probe(page);
  console.log(
    `[w7-html] ⑥新建專案預覽的連結＝${JSON.stringify(links)}；點撥號與腳本之後網址不變＝${page.url() === urlBefore}、預覽仍在＝${((await preview.textContent()) ?? "").includes("官網")}、window.__w7xss＝${JSON.stringify(fired.fired)}`,
  );
  expectLinkPolicy(links, "新建專案預覽");
  expect(page.url(), "點無 href 的文字不導覽、不重新載入").toBe(urlBefore);
  await expect(preview, "點完之後預覽內容仍在（沒有重新載入而丟掉未存內容）").toContainText("官網");
  expect(fired.fired, "javascript: 連結沒有執行").toBeNull();
});

test.describe("已儲存的專案說明含 iframe srcdoc", () => {
  test.beforeAll(async ({ request }) => {
    const mk = async (name: string, description: string): Promise<string> => {
      const dir = path.join(E2E_ROOT, "projects", `w7_html_${RUN}_${name}`);
      mkdirSync(dir, { recursive: true });
      const r = await call(request, "operator", "POST", "/api/v1/projects", {
        name: `QA W7 內嵌 HTML ${name} ${RUN}`,
        executionPath: dir,
        passCriteria: "- 無",
        description,
        autonomyLevel: 3,
        draft: true,
      });
      expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(201);
      return dataOf<{ id: string }>(r).id;
    };
    savedProjectId = await mk("iframe", IFRAME_PAYLOAD);
    storedProjectId = await mk("meta-base-links", STORED_PAYLOAD);
  });

  test("③ DEF-AC-013（P2，儲存式，W8 修於 85ed0915）：管理者開「編輯專案」頁，儲存的 iframe srcdoc 在編輯器預覽不執行", async ({ page, request }) => {
    await signIn(page, request, "admin"); // 受害者用管理者：腳本若在管理者的 session 內執行＝權限提升的向量（修前會執行）
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
    await expect(page.getByRole("heading", { name: `QA W7 內嵌 HTML iframe ${RUN}` })).toBeVisible({ timeout: 60_000 });
    await page.waitForTimeout(1500);
    const r = await probe(page);
    const iframes = await page.locator("iframe").count();
    console.log(`[w7-html] ④唯讀詳情頁：window.__w7xss＝${JSON.stringify(r.fired)}；頁面內 iframe 元素數＝${iframes}`);
    expect(r.fired, "唯讀檢視不執行腳本").toBeNull();
    expect(iframes, "唯讀檢視沒有把 iframe 建成真元素").toBe(0);
  });

  test("⑤b meta refresh 與 base（儲存式）：管理者開編輯頁與唯讀詳情頁，文件裡都沒有它們", async ({ page, request }) => {
    await signIn(page, request, "admin");
    await page.goto(`/projects/${storedProjectId}/edit`);
    await expect(page.locator(".w-md-editor-preview").first()).toContainText("摘要", { timeout: 60_000 });
    await page.waitForTimeout(1000);
    const edit = await docProbe(page);
    const editText = (await page.locator(".w-md-editor-preview").first().textContent()) ?? "";
    await page.goto(`/projects/${storedProjectId}`);
    await expect(page.getByRole("heading", { name: `QA W7 內嵌 HTML meta-base-links ${RUN}` })).toBeVisible({ timeout: 60_000 });
    await page.waitForTimeout(1000);
    const detail = await docProbe(page);
    console.log(`[w7-html] ⑤b儲存式：編輯頁文件＝${JSON.stringify(edit)}（預覽文字含 http-equiv＝${editText.includes("http-equiv")}）；詳情頁文件＝${JSON.stringify(detail)}`);
    expect(edit, "編輯頁文件裡沒有 meta refresh 與 base").toEqual({ metaRefresh: 0, base: 0 });
    expect(detail, "詳情頁文件裡沒有 meta refresh 與 base").toEqual({ metaRefresh: 0, base: 0 });
    expect(editText, "編輯頁預覽以文字顯示原文").toContain("http-equiv");
  });

  test("⑥b 連結協定白名單（儲存式）：編輯頁預覽與唯讀詳情頁的連結規則一致（tel: 兩處皆為無 href 的文字）", async ({ page, request }) => {
    await signIn(page, request, "admin");
    await page.goto(`/projects/${storedProjectId}/edit`);
    await expect(page.locator(".w-md-editor-preview").first()).toContainText("摘要", { timeout: 60_000 });
    await page.waitForTimeout(1000);
    const editLinks = await linksIn(page.locator(".w-md-editor-preview").first());
    await page.goto(`/projects/${storedProjectId}`);
    await expect(page.getByRole("heading", { name: `QA W7 內嵌 HTML meta-base-links ${RUN}` })).toBeVisible({ timeout: 60_000 });
    await page.waitForTimeout(1000);
    const detailLinks = await linksIn(page.locator('[data-slot="markdown-view"]'));
    const fired = await probe(page);
    console.log(`[w7-html] ⑥b儲存式：編輯頁預覽的連結＝${JSON.stringify(editLinks)}；詳情頁的連結＝${JSON.stringify(detailLinks)}；window.__w7xss＝${JSON.stringify(fired.fired)}`);
    expectLinkPolicy(editLinks, "編輯頁預覽");
    expectLinkPolicy(detailLinks, "唯讀詳情頁");
    expect(fired.fired, "javascript: 連結沒有執行").toBeNull();
  });
});
