import MDEditor from "@uiw/react-md-editor";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import rehypeRaw from "rehype-raw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BULK_EDIT_CHARS, DEFER_ABOVE_CHARS, MAX_IMPORT_BYTES, MarkdownEditorImpl, SYNC_RENDER_MAX_CHARS, omitRawHtml, safeFileName, shouldDeferPreview } from "./MarkdownEditorImpl";
import { MarkdownView } from "./MarkdownView";
import { safeUrlTransform } from "./safeUrl";

/**
 * PRD §5.1.4 Markdown 編輯器八項功能的行為測試（RTM：UI-MD-01～08）。
 * 渲染端（表格、程式碼高亮、checklist）測 MarkdownView；編輯端（Split View、工具列、語法高亮、匯入匯出）測編輯器本體。
 */

function Harness({ initial = "", onNotify }: { initial?: string; onNotify?: (m: string, t: "success" | "error") => void }) {
  const [value, setValue] = useState(initial);
  return (
    <>
      <MarkdownEditorImpl value={value} onChange={setValue} label="說明描述" exportName="專案說明" onNotify={onNotify} />
      <output data-testid="value">{value}</output>
    </>
  );
}
const textarea = () => screen.getByRole("textbox", { name: "說明描述" });

describe("UI-MD-01 即時預覽（Split View）", () => {
  it("預設是左原始碼、右預覽的 live 模式；輸入後預覽即時渲染", async () => {
    const { container } = render(<Harness />);
    expect(container.querySelector(".w-md-editor-show-live")).not.toBeNull();
    expect(container.querySelector(".w-md-editor-input")).not.toBeNull();
    expect(container.querySelector(".w-md-editor-preview")).not.toBeNull();

    fireEvent.change(textarea(), { target: { value: "# 標題一\n\n**粗體**" } });
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 1, name: "標題一" })).toBeInTheDocument());
    expect(preview.querySelector("strong")?.textContent).toBe("粗體");
  });
});

/**
 * DEF-AC-013（P2 資安，W8-FE）：預覽端不渲染 Markdown 內嵌的 HTML，與唯讀的 MarkdownView 一致（兩處對同一份內容的呈現必須相同）。
 * 套件（@uiw/react-markdown-preview）的預設鏈無條件掛 rehype-raw，`<iframe srcdoc>`、`<script>`、`<img onerror>`、`<a href=javascript:>`
 * 會被建成真元素；srcdoc 的文件與父頁同源，內層腳本讀得到 sessionStorage 裡的 session（儲存式：operator 存、admin 開編輯頁即中）。
 * 判準看「元素與屬性」而不是「有沒有真的跑起來」：預覽端不得出現危險元素、任何 on* 屬性、srcdoc、或 javascript:／vbscript:／data: 開頭的網址屬性；
 * HTML 原文改以文字顯示（與詳情頁相同）。這幾支在修前都要是紅的（見 rtm_backfill_W7FE.md〈二十二〉）。
 */
const xssFlag = () => (window as unknown as { __w8xss?: string }).__w8xss;
afterEach(() => {
  delete (window as unknown as { __w8xss?: string }).__w8xss;
});
const previewOf = (container: HTMLElement) => container.querySelector(".w-md-editor-preview") as HTMLElement;
const normalizedText = (el: Element | null) => (el?.textContent ?? "").replace(/\s+/g, " ").trim();

const DANGEROUS_TAGS = ["iframe", "frame", "frameset", "script", "object", "embed", "applet", "meta", "base", "form", "style", "link", "svg", "math"];
const URL_ATTRS = ["href", "src", "srcset", "action", "formaction", "poster", "data", "background", "xlink:href"];
/** 瀏覽器解析網址時會忽略空白與控制字元（`java\tscript:` 照樣是 javascript:），所以先剝掉再比。 */
const UNSAFE_URL = /^(?:javascript|vbscript|data):/i;

/** 預覽內所有「會執行或載入東西」的跡象：危險元素、on* 屬性、srcdoc、危險網址屬性。空陣列＝乾淨。 */
function executableTraces(root: Element): string[] {
  const traces: string[] = [];
  for (const el of Array.from(root.querySelectorAll("*"))) {
    const tag = el.tagName.toLowerCase();
    // 預覽自己的核取方塊圖示與工具圖示不是 HTML 內嵌，所以 svg 只在「不是套件自己的標題錨點與複製鈕」時才算（這些圖示在 aria-hidden 的容器內）
    if (DANGEROUS_TAGS.includes(tag) && !(tag === "svg" && el.closest("[aria-hidden='true'], .copied, .anchor"))) traces.push(`<${tag}>`);
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase();
      if (name.startsWith("on")) traces.push(`<${tag} ${attr.name}>`);
      if (name === "srcdoc") traces.push(`<${tag} srcdoc>`);
      if (URL_ATTRS.includes(name) && UNSAFE_URL.test(attr.value.replace(/[\u0000- ]+/g, ""))) traces.push(`<${tag} ${name}="${attr.value.slice(0, 48)}">`);
    }
  }
  return traces;
}

describe("UI-MD-01 預覽端不渲染內嵌 HTML（DEF-AC-013，P2 資安；與詳情頁 MarkdownView 一致）", () => {
  it("內嵌 <iframe srcdoc>（內層腳本與父頁同源、讀得到 sessionStorage）：預覽端不建出 iframe、沒有 srcdoc 屬性；原文當成文字顯示", () => {
    const payload = `<iframe srcdoc="<script>parent.__w8xss='iframe-srcdoc';parent.__w8keys=Object.keys(parent.sessionStorage).join(',')</script>"></iframe>`;
    const { container } = render(<Harness initial={`${payload}\n\n後面的文字`} />);
    const preview = previewOf(container);
    expect(preview.querySelector("iframe")).toBeNull();
    expect(preview.querySelector("[srcdoc]")).toBeNull();
    expect(executableTraces(preview)).toEqual([]);
    expect(preview.textContent).toContain("<iframe srcdoc="); // 與詳情頁一致：原文當成文字，不是被吞掉
    expect(preview.textContent).toContain("後面的文字");
    expect(xssFlag()).toBeUndefined();
  });

  it("內嵌 <script>：預覽端不建出 script 元素、window 上沒有被寫旗標；原文當成文字顯示", () => {
    const payload = `<script>window.__w8xss='script-tag'</script>`;
    const before = document.querySelectorAll("script").length;
    const { container } = render(<Harness initial={`${payload}\n\n前文 <script>window.__w8xss='inline-script'</script> 後文`} />);
    const preview = previewOf(container);
    expect(preview.querySelector("script")).toBeNull();
    expect(document.querySelectorAll("script")).toHaveLength(before); // 文件裡也沒有多出任何 script
    expect(executableTraces(preview)).toEqual([]);
    expect(preview.textContent).toContain("<script>window.__w8xss='script-tag'</script>");
    expect(xssFlag()).toBeUndefined();
  });

  it("內嵌 <img onerror=…>（獨立一行與行內兩種位置）：預覽端不建出 img、沒有任何 on* 屬性，也不會因字串事件處理器讓 React 丟錯", () => {
    const block = `<img src="x" onerror="window.__w8xss='img-block'">`;
    const inline = `前文 <img src="y" onerror="window.__w8xss='img-inline'"> 後文`;
    const errors: unknown[] = [];
    const onError = (e: ErrorEvent) => errors.push(e.error ?? e.message);
    window.addEventListener("error", onError);
    try {
      const { container } = render(<Harness initial={`${block}\n\n${inline}`} />);
      const preview = previewOf(container);
      expect(preview.querySelector("img")).toBeNull();
      expect(preview.querySelector("[onerror]")).toBeNull();
      expect(executableTraces(preview)).toEqual([]);
      expect(preview.textContent).toContain(`onerror="window.__w8xss='img-block'"`);
      expect(preview.textContent).toContain("前文");
      expect(preview.textContent).toContain("後文");
      expect(errors).toEqual([]);
    } finally {
      window.removeEventListener("error", onError);
    }
    expect(xssFlag()).toBeUndefined();
  });

  it("javascript: 連結（HTML 的 <a>、Markdown 的 [文字](網址)、<自動連結>、大小寫與空白混淆）：預覽端沒有任何 javascript:／vbscript:／data: 開頭的網址屬性；連結文字仍在", () => {
    const source = [
      `<a id="w8js" href="javascript:window.__w8xss='html-anchor'">HTML 連結</a>`,
      "",
      `[Markdown 連結](javascript:window.__w8xss='md-link')`,
      "",
      `<javascript:window.__w8xss='autolink'>`,
      "",
      `[大小寫混淆](JaVaScRiPt:window.__w8xss=1) 與 [內嵌空白](java%09script:window.__w8xss=2)`,
      "",
      `![圖片](javascript:window.__w8xss=3) 與 [資料網址](data:text/html;base64,PHNjcmlwdD48L3NjcmlwdD4=)`,
    ].join("\n");
    const { container } = render(<Harness initial={source} />);
    const preview = previewOf(container);
    expect(executableTraces(preview)).toEqual([]);
    expect(preview.querySelector("#w8js")).toBeNull(); // HTML 的 <a> 不被建成元素
    expect(preview.textContent).toContain(`<a id="w8js" href="javascript:`); // 原文當成文字
    for (const text of ["Markdown 連結", "大小寫混淆", "內嵌空白", "資料網址"]) expect(within(preview).getByText(text), `連結文字「${text}」仍在`).toBeInTheDocument();
    // 不合格的網址是整個拿掉 href（沒有行為的文字），不是留下 `href=""`：空 href 點下去會重新載入本頁，編輯中還沒存的內容就丟了
    const anchors = Array.from(preview.querySelectorAll("a"));
    expect(anchors.map((a) => a.textContent)).toEqual(["Markdown 連結", "javascript:window.__w8xss='autolink'", "大小寫混淆", "內嵌空白", "資料網址"]);
    for (const a of anchors) expect(a.hasAttribute("href"), `${a.textContent} 沒有 href`).toBe(false);
    for (const img of Array.from(preview.querySelectorAll("img"))) expect(img.hasAttribute("src"), "圖片沒有 src").toBe(false);
    expect(xssFlag()).toBeUndefined();
  });

  it.each([
    ["<object data=\"javascript:window.__w8xss='object'\"></object>"],
    ["<embed src=\"javascript:window.__w8xss='embed'\">"],
    ["<svg onload=\"window.__w8xss='svg-onload'\"></svg>"],
    ['<form action="javascript:window.__w8xss=\'form\'"><input type="submit"></form>'],
    ['<meta http-equiv="refresh" content="0;url=javascript:window.__w8xss=\'meta\'">'],
    ['<iframe src="data:text/html;base64,PHNjcmlwdD53aW5kb3cucGFyZW50Ll9fdzh4c3M9J2RhdGEnPC9zY3JpcHQ+"></iframe>'],
    ['<base href="https://evil.example/">'],
    ['<link rel="stylesheet" href="https://evil.example/x.css">'],
    ["<style>body{background:url(https://evil.example/x)}</style>"],
    ["<math><mtext><script>window.__w8xss='math'</script></mtext></math>"],
    ["<details open ontoggle=\"window.__w8xss='details-ontoggle'\"><summary>摘要</summary>內容</details>"],
    ["<a href=\"&#106;avascript:window.__w8xss='entity'\">實體編碼</a>"],
  ])("整組載體（QA §10.1 第 11 點列出而尚未逐一驗的那些）：%s 不產生可執行內容", (payload) => {
    const headBefore = document.head.innerHTML;
    const { container } = render(<Harness initial={`前文\n\n${payload}\n\n後文`} />);
    const preview = previewOf(container);
    expect(executableTraces(preview)).toEqual([]);
    // React 19 會把 <meta>、<link>、<title> 從樹裡任何位置搬進 document.head（<meta http-equiv=refresh> 就是靠這條路生效）：預覽不得往 <head> 塞任何東西
    expect(document.head.innerHTML).toBe(headBefore);
    expect(preview.querySelector("details, summary, a[href], object, embed, form, input:not([type=checkbox])")).toBeNull();
    expect(preview.textContent).toContain("前文");
    expect(preview.textContent).toContain("後文");
    expect(xssFlag()).toBeUndefined();
  });

  it("與詳情頁（MarkdownView）一致：同一份含內嵌 HTML 的內容，預覽端與詳情頁顯示的文字相同，兩邊都沒有任何可執行的跡象", () => {
    const docs = [
      `<iframe srcdoc="<script>parent.__w8xss='x'</script>"></iframe>\n\n摘要`,
      `<script>window.__w8xss='x'</script>\n\n前文 <img src=x onerror="window.__w8xss='y'"> 後文`,
      `前文 <b>粗</b> 與 <kbd>Ctrl</kbd> 加 <br/> 換行\n\n<details><summary>摘要</summary>內容</details>`,
      `<a href="javascript:window.__w8xss='z'">點我</a> 與 [連結](javascript:window.__w8xss='w')`,
      `[撥號](tel:+886-2-1234-5678) 與 [官網](https://example.com) 與 [站內](/projects#top) 與 [錨點](#下一節) 與 [信箱](mailto:ops@example.com)`,
    ];
    const hrefsOf = (root: Element) => Array.from(root.querySelectorAll("a")).map((a) => a.getAttribute("href"));
    for (const doc of docs) {
      const view = render(<MarkdownView source={doc} />);
      const viewRoot = view.container.querySelector("[data-slot='markdown-view']") as HTMLElement;
      const viewText = normalizedText(viewRoot);
      const viewHrefs = hrefsOf(viewRoot);
      expect(executableTraces(viewRoot), `詳情頁：${doc.slice(0, 30)}`).toEqual([]);
      view.unmount();

      const editor = render(<Harness initial={doc} />);
      const previewRoot = previewOf(editor.container).querySelector(".wmde-markdown") as HTMLElement;
      expect(executableTraces(previewRoot), `預覽端：${doc.slice(0, 30)}`).toEqual([]);
      expect(normalizedText(previewRoot), `同一份內容兩處的文字：${doc.slice(0, 30)}`).toBe(viewText);
      expect(hrefsOf(previewRoot), `同一份內容兩處的連結網址：${doc.slice(0, 30)}`).toEqual(viewHrefs);
      editor.unmount();
    }
    expect(xssFlag()).toBeUndefined();
  });

  it("Markdown 本身的功能不退化：GFM 表格、程式碼區塊語法高亮（hljs＋prism token）、核取清單、標題、一般連結（https、站內、mailto）原樣保留", () => {
    const source = [
      "## 標題",
      "",
      "| 欄位 | 說明 |",
      "| --- | --- |",
      "| id | 唯一識別碼 |",
      "",
      "```ts",
      "const answer: number = 42;",
      "```",
      "",
      "- [x] 完成項",
      "- [ ] 待辦項",
      "",
      "[官網](https://example.com) 與 [站內](/projects) 與 [信箱](mailto:ops@example.com) 與 https://example.org/auto",
    ].join("\n");
    const { container } = render(<Harness initial={source} />);
    const preview = previewOf(container);
    expect(within(preview).getByRole("heading", { level: 2, name: "標題" })).toBeInTheDocument();
    expect(within(preview).getByRole("columnheader", { name: "欄位" })).toBeInTheDocument();
    expect(within(preview).getByRole("cell", { name: "唯一識別碼" })).toBeInTheDocument();
    const code = preview.querySelector("pre code.language-ts") as HTMLElement;
    expect(code.className).toContain("hljs");
    expect(code.querySelector(".token.keyword")?.textContent).toBe("const");
    expect(within(preview).getByRole("checkbox", { name: "完成項" })).toBeChecked();
    expect(within(preview).getByRole("checkbox", { name: "待辦項" })).not.toBeChecked();
    const hrefOf = (name: string) => within(preview).getByRole("link", { name }).getAttribute("href");
    expect(hrefOf("官網")).toBe("https://example.com");
    expect(hrefOf("站內")).toBe("/projects");
    expect(hrefOf("信箱")).toBe("mailto:ops@example.com");
    expect(hrefOf("https://example.org/auto")).toBe("https://example.org/auto");
    expect(executableTraces(preview)).toEqual([]);
  });

  it("左欄原始碼著色不受影響：含 HTML 的原文照樣被切成 token、原文逐字顯示（<、& 與引號已跳脫），左欄沒有建出任何元素", async () => {
    const source = `# 標題\n\n**粗體** 與 <iframe srcdoc="<script>1</script>"></iframe> 與 <img src=x onerror=alert(1)>`;
    const { container } = render(<Harness initial={source} />);
    await waitFor(() => expect(container.querySelector(".w-md-editor-text-pre .token.title")).not.toBeNull());
    const pre = container.querySelector(".w-md-editor-text-pre") as HTMLElement;
    expect(pre.querySelector(".token.bold")).not.toBeNull();
    expect(pre.textContent).toContain(`<iframe srcdoc="<script>1</script>"></iframe>`);
    expect(pre.textContent).toContain("<img src=x onerror=alert(1)>");
    expect(pre.querySelector("iframe, script, img")).toBeNull();
    expect(executableTraces(pre)).toEqual([]);
  });
});

describe("UI-MD-01 DEF-AC-013 的兩個零件：omitRawHtml 與 safeUrlTransform", () => {
  it("套件的預設 rehype 鏈仍含 rehype-raw（所以 pluginsFilter 才有東西可拿；套件改了做法時這支先紅，回頭重新評估 omitRawHtml）", () => {
    const seen: Array<{ type: string; plugins: unknown[] }> = [];
    render(
      <MDEditor.Markdown
        source="x"
        pluginsFilter={(type, plugins) => {
          seen.push({ type, plugins: [...plugins] });
          return plugins;
        }}
      />,
    );
    const rehype = seen.find((s) => s.type === "rehype")?.plugins ?? [];
    expect(rehype.some((p) => (Array.isArray(p) ? p[0] : p) === rehypeRaw)).toBe(true);
    expect(seen.some((s) => s.type === "remark")).toBe(true);
  });

  it("omitRawHtml 只拿掉 rehype 清單裡的 rehype-raw（含 [外掛, 選項] 的寫法），其餘外掛與順序不動；remark 清單原樣", () => {
    const a = () => undefined;
    const b = () => undefined;
    expect(omitRawHtml("rehype", [a, rehypeRaw, b])).toEqual([a, b]);
    expect(omitRawHtml("rehype", [a, [rehypeRaw, {}], [b, { x: 1 }]])).toEqual([a, [b, { x: 1 }]]);
    expect(omitRawHtml("rehype", [a, b])).toEqual([a, b]);
    expect(omitRawHtml("rehype", [])).toEqual([]);
    const remark = [a, rehypeRaw, b]; // remark 清單裡不會有 rehype-raw；就算有，也不是這支要管的
    expect(omitRawHtml("remark", remark)).toBe(remark);
  });

  it("safeUrlTransform：與 MarkdownView 同一支白名單；不合格的網址回 undefined（整個拿掉 href），不是空字串（空 href 點下去會重新載入本頁）", () => {
    for (const ok of [
      "https://example.com/a?b=1#c",
      "http://example.com",
      "mailto:ops@example.com",
      "irc://irc.example/x",
      "xmpp:me@example.com",
      "/projects",
      "projects/1",
      "../up",
      "#錨點",
      "?q=1",
      "a/b:c",
      "",
    ]) {
      expect(safeUrlTransform(ok), ok).toBe(ok);
    }
    for (const bad of [
      "javascript:alert(1)",
      "JaVaScRiPt:alert(1)",
      " javascript:alert(1)",
      "java\tscript:alert(1)",
      "java%09script:alert(1)",
      "vbscript:msgbox(1)",
      "data:text/html;base64,PHNjcmlwdD4=",
      "tel:+886-2-1234-5678",
      "file:///etc/passwd",
      "blob:https://example.com/x",
      "custom-scheme:payload",
    ]) {
      expect(safeUrlTransform(bad), JSON.stringify(bad)).toBeUndefined();
    }
  });

  it("不合格的連結在預覽端與詳情頁一樣是沒有 href 的文字（點了不導頁、不重新載入本頁，編輯中的內容不會丟）", async () => {
    const source = "[撥號](tel:+886-2-1234-5678) 與 [壞連結](javascript:alert(1))";
    const view = render(<MarkdownView source={source} />);
    expect(Array.from(view.container.querySelectorAll("a")).map((a) => a.hasAttribute("href"))).toEqual([false, false]);
    view.unmount();
    const { container } = render(<Harness initial={source} />);
    const anchors = Array.from(previewOf(container).querySelectorAll("a"));
    expect(anchors.map((a) => a.textContent)).toEqual(["撥號", "壞連結"]);
    for (const a of anchors) {
      expect(a.hasAttribute("href")).toBe(false);
      fireEvent.click(a); // jsdom 對「導頁」會報 not implemented；沒有 href 就什麼都不會發生
    }
    expect((textarea() as HTMLTextAreaElement).value).toBe(source); // 編輯器內容原封不動
  });
});

describe("UI-MD-02 語法高亮（編輯區原始碼著色）", () => {
  it("Markdown 標題／粗體在編輯區被切成帶 token 類別的節點", async () => {
    const { container } = render(<Harness initial={"# 標題\n\n**粗體**"} />);
    await waitFor(() => expect(container.querySelector(".w-md-editor-text-pre .token.title")).not.toBeNull());
    expect(container.querySelector(".w-md-editor-text-pre .token.bold")).not.toBeNull();
  });
});

describe("UI-MD-03 常用語法工具列", () => {
  it("工具列含 粗體、斜體、標題、清單、表格、程式碼區塊 等快捷按鈕，點粗體會在游標處插入語法", () => {
    const { container } = render(<Harness />);
    const toolbar = container.querySelector(".w-md-editor-toolbar") as HTMLElement;
    expect(toolbar).not.toBeNull();
    const labels = Array.from(toolbar.querySelectorAll("button")).map((b) => (b.getAttribute("aria-label") ?? "").toLowerCase());
    for (const keyword of ["bold", "italic", "title", "unordered list", "ordered list", "checked list", "table", "code"]) {
      expect(
        labels.some((l) => l.includes(keyword)),
        `工具列缺少「${keyword}」`,
      ).toBe(true);
    }
    const bold = Array.from(toolbar.querySelectorAll("button")).find((b) => /bold/i.test(b.getAttribute("aria-label") ?? ""))!;
    fireEvent.click(bold);
    expect(screen.getByTestId("value").textContent).toContain("****");
  });
});

describe("UI-A11Y-01 工具列圖示是裝飾（axe svg-img-alt；DEF-AC-005）", () => {
  it("工具列（左側指令與右側模式切換）的 svg 圖示全部 aria-hidden，沒有會被讀出卻沒有名字的 role=img", () => {
    const { container } = render(<Harness />);
    const svgs = Array.from(container.querySelectorAll(".w-md-editor-toolbar svg"));
    expect(svgs.length, "工具列應有圖示").toBeGreaterThan(10);
    for (const svg of svgs) expect(svg.getAttribute("aria-hidden"), svg.outerHTML.slice(0, 90)).toBe("true");
    expect(container.querySelectorAll('svg[role="img"]:not([aria-hidden="true"])')).toHaveLength(0);
  });

  it("圖示藏起來之後，每顆工具列按鈕仍靠自己的 aria-label 有名字（不能讓按鈕變成無名按鈕）", () => {
    const { container } = render(<Harness />);
    const buttons = Array.from(container.querySelectorAll(".w-md-editor-toolbar button"));
    expect(buttons.length).toBeGreaterThan(10);
    for (const b of buttons) expect(b.getAttribute("aria-label") || b.textContent, b.outerHTML.slice(0, 90)).toBeTruthy();
  });
});

describe("預覽窗（C-19／NFR-9.1-05：輸入與預覽分開排程；DEF-AC-005 同類：鍵盤可達）", () => {
  it("預覽窗是 tabIndex=0 的區域，名稱含欄位名（同頁多個編輯器各自唯一），並且還在套件的 .w-md-editor-preview 底下（捲動同步與外部選取器不受影響）", () => {
    const { container } = render(<Harness />);
    const region = screen.getByRole("region", { name: "說明描述 預覽" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(region.closest(".w-md-editor-preview")).not.toBeNull();
    expect(container.querySelectorAll(".w-md-editor-preview")).toHaveLength(1);
    // 預覽內容仍是套件的 Markdown 渲染（wmde-markdown），不是自己另寫的容器
    expect(region.querySelector(".wmde-markdown")).not.toBeNull();
  });

  it("輸入後輸入框立刻是新值，預覽稍後（deferred）跟上；預覽內容仍含 GFM 表格、程式碼高亮（hljs＋prism token）", async () => {
    const { container } = render(<Harness />);
    fireEvent.change(textarea(), { target: { value: "## 新標題\n\n```ts\nconst a = 1;\n```" } });
    expect((textarea() as HTMLTextAreaElement).value).toContain("新標題"); // 輸入框是急件：不等預覽
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "新標題" })).toBeInTheDocument());
    const code = preview.querySelector("pre code.language-ts") as HTMLElement;
    expect(code).not.toBeNull();
    expect(code.className).toContain("hljs"); // rehype-highlight（真後端 spec markdown-editor.spec.ts 也斷言這個 class）
  });
});

describe("預覽窗：大文件（超過 DEFER_ABOVE_CHARS 才分開排程）也要正確跟上輸入", () => {
  it("超過門檻的文件：預覽最終顯示最後一次輸入的內容（中間的值可以被跳過，但最終值不能丟）", async () => {
    const big = "## 大文件\n\n" + "這是一段說明文字，用來把文件撐到門檻以上。\n\n".repeat(Math.ceil(DEFER_ABOVE_CHARS / 20));
    expect(big.length).toBeGreaterThan(DEFER_ABOVE_CHARS);
    const { container } = render(<Harness initial={big} />);
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "大文件" })).toBeInTheDocument(), { timeout: 5000 });
    // 連續兩次輸入（模擬打字）：最終預覽必須是第二次的內容
    fireEvent.change(textarea(), { target: { value: big + "\n\n第一次" } });
    fireEvent.change(textarea(), { target: { value: big + "\n\n## 最終標題" } });
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "最終標題" })).toBeInTheDocument(), { timeout: 5000 });
    expect(within(preview).queryByText("第一次")).toBeNull();
  });

  it("批次貼入（一次差上萬字，例如把 20KB 文件貼進空欄位）：預覽一次到位，內容與區塊數都正確", async () => {
    const section = (i: number) => `## 區塊 ${i}\n\n\`\`\`python\nprint(${i})\n\`\`\`\n\n`;
    const pasted = Array.from({ length: 300 }, (_, i) => section(i + 1)).join("");
    expect(pasted.length).toBeGreaterThan(DEFER_ABOVE_CHARS);
    expect(pasted.length).toBeLessThanOrEqual(SYNC_RENDER_MAX_CHARS);
    expect(pasted.length).toBeGreaterThan(BULK_EDIT_CHARS);
    const { container } = render(<Harness />);
    fireEvent.change(textarea(), { target: { value: pasted } });
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "區塊 300" })).toBeInTheDocument(), { timeout: 15000 });
    expect(within(preview).getAllByRole("heading", { level: 2 })).toHaveLength(300);
    expect(preview.querySelectorAll("pre code.language-python")).toHaveLength(300);
    // 之後回到連續打字：落後只有幾個字，仍走排程（deferred），最終值不能丟
    fireEvent.change(textarea(), { target: { value: `${pasted}## 打字加的標題\n` } });
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "打字加的標題" })).toBeInTheDocument(), { timeout: 15000 });
  }, 30000);
});

describe("預覽何時排到輸入之後（NFR-9.1-05：shouldDeferPreview）", () => {
  const DOC_20KB = 14000; // p9 量法的 20KB 文件約 14,000 字

  it("小文件不排：一幀內就渲染完，分兩段只會多等一個畫面", () => {
    expect(shouldDeferPreview(DEFER_ABOVE_CHARS, 0)).toBe(false);
    expect(shouldDeferPreview(500, 499)).toBe(false);
  });

  it("大文件連續打字（預覽只落後幾個字）要排：連續輸入時中間的值直接被跳過；剛好在批次門檻上還不算批次", () => {
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB - 1)).toBe(true);
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB)).toBe(true); // 已追上：shown 與 source 相同，排不排結果一樣
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB - BULK_EDIT_CHARS)).toBe(true);
    expect(shouldDeferPreview(DOC_20KB - BULK_EDIT_CHARS, DOC_20KB)).toBe(true); // 刪掉一整段但沒超過門檻
  });

  it("批次變更（貼上、匯入、復原）一次渲染到位：預覽落後超過門檻，不再多插一個畫面", () => {
    expect(shouldDeferPreview(DOC_20KB, 0)).toBe(false); // 20KB 貼進空欄位（p9 的量法）
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB - BULK_EDIT_CHARS - 1)).toBe(false);
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB + 5000)).toBe(false); // 刪掉一大段後仍是大文件
  });

  it("批次但文件太大（超過 SYNC_RENDER_MAX_CHARS）：仍然排，免得一次貼進超大文件時整頁卡住", () => {
    expect(shouldDeferPreview(SYNC_RENDER_MAX_CHARS, 0)).toBe(false);
    expect(shouldDeferPreview(SYNC_RENDER_MAX_CHARS + 1, 0)).toBe(true);
    expect(shouldDeferPreview(1_000_000, 0)).toBe(true);
  });
});

describe("UI-A11Y-01 核取清單的核取方塊要有名稱（axe aria-toggle-field-name；DEF-AC-005 同類）", () => {
  it("唯讀渲染：每個核取方塊的名稱＝該項目的文字；巢狀子清單的文字不混進父項目的名稱", () => {
    render(<MarkdownView source={"- [ ] 父項目\n  - [x] 子項目一\n  - [ ] 子項目二\n- [x] **粗體** 與 `code` 的項目"} />);
    expect(screen.getByRole("checkbox", { name: "父項目" })).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("checkbox", { name: "子項目一" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("checkbox", { name: "子項目二" })).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("checkbox", { name: "粗體 與 code 的項目" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getAllByRole("checkbox")).toHaveLength(4);
  });

  it("鬆散清單（項目之間有空行，核取方塊在 <p> 裡）也有名稱；一般清單不受影響", () => {
    render(<MarkdownView source={"- [ ] 第一項\n\n- [x] 第二項\n\n- 普通項目"} />);
    expect(screen.getByRole("checkbox", { name: "第一項" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "第二項" })).toBeInTheDocument();
    expect(screen.getAllByRole("checkbox")).toHaveLength(2);
    expect(screen.getByText("普通項目")).toBeInTheDocument();
  });

  it("編輯器預覽端的核取方塊（原生 input）同樣有名稱", async () => {
    const { container } = render(<Harness initial={"- [ ] 預覽中的待辦\n- [x] 預覽中的完成項"} />);
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("checkbox", { name: "預覽中的待辦" })).toBeInTheDocument());
    expect(within(preview).getByRole("checkbox", { name: "預覽中的完成項" })).toBeChecked();
  });
});

describe("UI-MD-04／05／06 渲染端：GFM 表格、程式碼區塊語言高亮、Checklist", () => {
  it("GFM 表格渲染成 <table>（含表頭與資料列）", () => {
    const { container } = render(<MarkdownView source={"| 欄位 | 說明 |\n| --- | --- |\n| id | 唯一識別碼 |"} />);
    const table = container.querySelector("table") as HTMLElement;
    expect(table).not.toBeNull();
    expect(within(table).getByRole("columnheader", { name: "欄位" })).toBeInTheDocument();
    expect(within(table).getByRole("cell", { name: "唯一識別碼" })).toBeInTheDocument();
  });

  it("帶語言標示的程式碼區塊有語法高亮（highlight.js 類別）；沒標語言則不亂猜", () => {
    const { container } = render(<MarkdownView source={"```ts\nconst answer: number = 42;\n```\n\n```\nplain text\n```"} />);
    const blocks = container.querySelectorAll("pre code");
    expect(blocks).toHaveLength(2);
    expect(blocks[0].className).toContain("language-ts");
    expect(blocks[0].querySelector(".hljs-keyword")?.textContent).toBe("const");
    expect(blocks[1].querySelector("[class^='hljs-']")).toBeNull();
  });

  it("checklist（- [ ] / - [x]）渲染成 18px 唯讀核取方塊，勾選狀態正確", () => {
    render(<MarkdownView variant="criteria" source={"- [ ] 所有核心模組通過單元測試\n- [x] API 契約驗證通過"} />);
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes).toHaveLength(2);
    expect(boxes[0]).toHaveAttribute("aria-checked", "false");
    expect(boxes[1]).toHaveAttribute("aria-checked", "true");
    expect(boxes[1]).toHaveAttribute("aria-readonly", "true");
    expect(boxes[1].className).toContain("size-[18px]");
    expect(screen.getByText("API 契約驗證通過")).toBeInTheDocument();
  });

  it("不渲染原始 HTML（避免 XSS），空內容顯示占位文字", () => {
    const { container } = render(<MarkdownView source={'<img src=x onerror="alert(1)"><script>alert(1)</script>安全'} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    render(<MarkdownView source="   " empty="（尚未填寫）" />);
    expect(screen.getByText("（尚未填寫）")).toBeInTheDocument();
  });

  it("外部連結以新分頁開啟並帶 noopener", () => {
    render(<MarkdownView source="[官網](https://example.com) 與 [站內](/projects)" />);
    expect(screen.getByRole("link", { name: "官網" })).toHaveAttribute("target", "_blank");
    expect(screen.getByRole("link", { name: "官網" })).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByRole("link", { name: "站內" })).not.toHaveAttribute("target");
  });
});

describe("UI-MD-07 匯入 .md 檔案", () => {
  const file = (content: string, name = "spec.md", type = "text/markdown") => new File([content], name, { type });

  it("選擇 .md 檔後內容直接填入編輯器並通知成功", async () => {
    const onNotify = vi.fn();
    render(<Harness initial="舊內容" onNotify={onNotify} />);
    await userEvent.upload(screen.getByTestId("md-import-input"), file("# 匯入的標題\n\n- [x] 完成"));
    await waitFor(() => expect(screen.getByTestId("value").textContent).toBe("# 匯入的標題\n\n- [x] 完成"));
    expect(onNotify).toHaveBeenCalledWith("已匯入 spec.md", "success");
  });

  it("拒絕非文字副檔名與超過上限的檔案，編輯器內容不變", async () => {
    const onNotify = vi.fn();
    render(<Harness initial="保持不變" onNotify={onNotify} />);
    const input = screen.getByTestId("md-import-input");
    // userEvent.upload 會依 accept 過濾；改用 fireEvent 才能模擬「使用者硬選了不合規的檔」
    fireEvent.change(input, { target: { files: [file("x", "malware.exe", "application/octet-stream")] } });
    expect(onNotify).toHaveBeenLastCalledWith("只支援 .md／.markdown／.txt 文字檔", "error");
    const big = file("x".repeat(10), "big.md");
    Object.defineProperty(big, "size", { value: MAX_IMPORT_BYTES + 1 });
    fireEvent.change(input, { target: { files: [big] } });
    expect(onNotify).toHaveBeenLastCalledWith("檔案超過 1 MB 上限", "error");
    expect(screen.getByTestId("value").textContent).toBe("保持不變");
  });
});

describe("UI-MD-08 匯出 .md 檔案", () => {
  it("按「匯出 .md」以 Blob 下載，檔名為「<名稱>.md」且內容等於編輯器內容；空內容時停用", async () => {
    const createObjectURL = vi.fn(() => "blob:mock");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe("專案說明.md");
      expect(this.href).toContain("blob:mock");
    });
    const onNotify = vi.fn();
    render(<Harness initial="" onNotify={onNotify} />);
    expect(screen.getByRole("button", { name: "匯出 .md" })).toBeDisabled();

    fireEvent.change(textarea(), { target: { value: "# 匯出內容\n\n中文也 OK" } });
    await userEvent.click(screen.getByRole("button", { name: "匯出 .md" }));
    expect(click).toHaveBeenCalledTimes(1);
    const blob = (createObjectURL.mock.calls[0] as unknown as [Blob])[0];
    expect(blob.type).toContain("text/markdown");
    expect(await blob.text()).toBe("# 匯出內容\n\n中文也 OK");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock");
    expect(onNotify).toHaveBeenCalledWith("已匯出 專案說明.md", "success");
  });

  it("檔名只留安全字元（路徑穿越與跨平台非法字元）", () => {
    expect(safeFileName("../../etc/passwd")).toBe("_.._etc_passwd");
    expect(safeFileName('a:b*c?"d')).toBe("a_b_c__d");
    expect(safeFileName("   ")).toBe("content");
  });
});
