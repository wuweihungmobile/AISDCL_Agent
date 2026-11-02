"use client";

/**
 * Mermaid 圖區塊（PRD 預覽中的 ```mermaid 圍欄；FR-R2P-09；TCS-ResearchToPRD-P0-20261102 AT-960-16-3、17-3；ADR-003 D9）：
 *
 * 設計要點（為什麼這樣做）：
 *  - **`mermaid` 只在需要時才下載**：本檔沒有任何靜態 `import … from "mermaid"`，渲染當下才 `import("mermaid")`（獨立 chunk，不進首屏；AT-960-17-3 的 AST 掃描釘住）；
 *    預覽端也只以 `next/dynamic` 載入本元件，所以沒有 mermaid 圖的 PRD 一個位元組都不會多下載。
 *  - **嚴格安全等級**：`initialize` 的設定固定 `securityLevel: "strict"`（`MERMAID_CONFIG`；單元測試釘住）——`click` 回呼停用、標籤的腳本與事件屬性被淨化；
 *    標籤另設 `htmlLabels: false`（畫成 SVG 文字，見常數的說明）。
 *    本檔再加一道自己的淨化（`parseMermaidSvg`）：不信任函式庫的輸出，移除 script／iframe 等元素、`on*` 屬性與 `javascript:` 網址之後才接進 DOM；
 *    接進 DOM 用 `DOMParser`＋`replaceChildren`，不用 `dangerouslySetInnerHTML` 或 `innerHTML`（整樹靜態鎖：研究元件一律不准）。
 *  - **失敗不拖垮整頁**：語法錯誤顯示錯誤訊息與原始碼；渲染逾時 3 秒（`MERMAID_RENDER_TIMEOUT_MS`）改顯示原始碼；成功的圖也附原始碼文字替代（可及性：圖表要有文字替代）。
 *  - **色彩一律取設計 token**：執行期讀 `:root` 的 CSS 變數餵給 `themeVariables`（Mermaid 的色彩運算要真的色值，`var()` 字串不行），本檔不寫任何色碼。
 */
import { useEffect, useId, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/** 單一圖渲染的逾時（毫秒；AC-R2P-09-3 與 W-R9：3 秒）。從 `render` 開始算，不含第一次下載函式庫的時間。 */
export const MERMAID_RENDER_TIMEOUT_MS = 3000;

/** 不論呼叫端怎麼組，`securityLevel` 只有這個值（AC-R2P-09-9：初始化固定 strict，單元測試釘住）。 */
export const MERMAID_SECURITY_LEVEL = "strict" as const;

/**
 * 傳給 `mermaid.initialize` 的固定部分；色彩由 `mermaidThemeVariables` 於執行期自設計 token 補上。
 * `htmlLabels: false`：節點與連線的標籤改畫成 SVG 文字，不用 HTML。函式庫在量測版面時會把標籤的 HTML 先放進「真的文件」裡——
 * strict 等級只淨化腳本與事件屬性、留下 `<img src>`，瀏覽器就會在淨化之前對外發請求（本檔事後的淨化來不及）；標籤不用 HTML 就沒有這條路
 * （tests/e2e/research-studio-perf.mock.spec.ts 的 AT_960_16_3 以真函式庫與真瀏覽器釘住：預覽含外部圖片網址的圖不發任何請求）。
 */
export const MERMAID_CONFIG = { startOnLoad: false, securityLevel: MERMAID_SECURITY_LEVEL, suppressErrorRendering: true, theme: "base", htmlLabels: false } as const;

/** Mermaid 主題變數與設計 token 的對映（鍵：Mermaid 的 themeVariables、值：`:root` 的 CSS 變數名）。 */
const THEME_TOKENS: ReadonlyArray<readonly [string, string]> = [
  ["primaryColor", "--color-bg-base"],
  ["primaryBorderColor", "--color-primary"],
  ["primaryTextColor", "--color-text-main"],
  ["secondaryColor", "--color-tertiary"],
  ["tertiaryColor", "--color-bg-surface"],
  ["lineColor", "--color-text-muted"],
  ["textColor", "--color-text-main"],
  ["background", "--color-bg-surface"],
];

/** 設計 token 的現值（讀不到＝空字串：沒有 CSS 的環境，例如單元測試）。 */
function readToken(name: string): string {
  if (typeof document === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** 執行期的主題變數：只放讀得到值的 token；字型取頁面本身的字型，圖與內文一致。 */
export function mermaidThemeVariables(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, token] of THEME_TOKENS) {
    const value = readToken(token);
    if (value !== "") out[key] = value;
  }
  const font = typeof document === "undefined" ? "" : getComputedStyle(document.body).fontFamily;
  if (font !== "") out.fontFamily = font;
  return out;
}

/**
 * 不准出現在輸出裡的元素：可執行的（script、iframe…）、會載入外部資源的（圖片、影音；PRD 預覽不該因為看一張圖就對外發請求——
 * 圖內文字是 AI 產生的、可能來自不可信的網頁內容，外送網址就是資料外洩管道）、會在執行期改寫連結目標的 SMIL 動畫（`<animate attributeName="href" values="javascript:…">`）。
 */
const FORBIDDEN_ELEMENTS = new Set([
  "script",
  "iframe",
  "object",
  "embed",
  "applet",
  "meta",
  "link",
  "base",
  "frame",
  "frameset",
  "img",
  "image",
  "picture",
  "source",
  "video",
  "audio",
  "track",
  "feimage",
  "animate",
  "set",
  "animatemotion",
  "animatetransform",
  "discard",
  "mpath",
]);
const URL_ATTRIBUTES = new Set(["href", "xlink:href", "src", "action", "formaction", "data"]);
/** 一律拿掉的資源屬性（不論值是什麼）：它們的唯一用途就是載入東西。 */
const RESOURCE_ATTRIBUTES = new Set(["src", "srcset", "poster", "background", "ping", "lowsrc", "dynsrc"]);
/** CSS 的外部參照：`@import` 與指向文件外的 `url(…)`（`url(#id)` 是圖內的標記、漸層等內部參照，要保留）。 */
const EXTERNAL_CSS_REFERENCE = /@import|url\(\s*(?!['"]?\s*#)/i;

/** 去掉空白與控制字元後是否以可執行或可注入的協定起頭（`java\tscript:` 之類的拆字寫法也算）。 */
function isDangerousUrl(value: string): boolean {
  // 刻意比對控制字元：瀏覽器解析網址時會忽略它們，拆字寫法才擋得到
  const compact = value.replace(/[\u0000- ]/g, "").toLowerCase();
  return compact.startsWith("javascript:") || compact.startsWith("vbscript:") || compact.startsWith("data:text/html");
}

/**
 * 淨化函式庫回傳的 SVG 字串並回傳 `<svg>` 節點（解析不出 `<svg>` 回 null）。
 * 以 HTML 解析器解析（Mermaid 的輸出經過 HTML 序列化，XML 解析器會被 `<br>` 這類寫法卡住）；解析出來的文件是惰性的，淨化完成前不會有任何東西執行。
 */
export function parseMermaidSvg(svg: string): SVGSVGElement | null {
  const doc = new DOMParser().parseFromString(`<body>${svg}</body>`, "text/html");
  const root = doc.body.querySelector("svg");
  if (root === null) return null;
  for (const el of Array.from(root.querySelectorAll("*"))) {
    const tag = el.localName.toLowerCase();
    if (FORBIDDEN_ELEMENTS.has(tag) || (tag === "style" && EXTERNAL_CSS_REFERENCE.test(el.textContent ?? ""))) {
      el.remove();
      continue;
    }
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase();
      const isLink = name === "href" || name === "xlink:href";
      const drop =
        name.startsWith("on") ||
        name === "srcdoc" ||
        RESOURCE_ATTRIBUTES.has(name) ||
        (URL_ATTRIBUTES.has(name) && isDangerousUrl(attr.value)) ||
        (isLink && tag !== "a" && !attr.value.trim().startsWith("#")) || // 非連結元素（use、textPath…）的參照只准指向圖內
        EXTERNAL_CSS_REFERENCE.test(attr.value); // style、fill、filter… 任何屬性的外部 url()
      if (drop) el.removeAttribute(attr.name);
      else if (isLink && tag === "a" && /^https?:/i.test(attr.value.trim())) {
        el.setAttribute("target", "_blank");
        el.setAttribute("rel", "noopener noreferrer");
      }
    }
  }
  return root as unknown as SVGSVGElement;
}

type MermaidApi = (typeof import("mermaid"))["default"];
let mermaidLoad: Promise<MermaidApi> | null = null;

/** 第一次用到才下載函式庫；同一頁的多張圖共用同一個載入（不重複下載、也不會各自拿到不同的模組實例）。載入失敗不快取，下一張圖可以重試。 */
function loadMermaid(): Promise<MermaidApi> {
  mermaidLoad ??= import("mermaid")
    .then((module) => module.default)
    .catch((error: unknown) => {
      mermaidLoad = null;
      throw error;
    });
  return mermaidLoad;
}

type Outcome = { kind: "ready"; svg: SVGSVGElement } | { kind: "error"; message: string } | { kind: "timeout" };
/** 結果綁定它是為哪一份程式碼算的：換程式碼時舊結果自動失效（衍生出「渲染中」，不必在 effect 內同步設狀態）。 */
type Settled = { code: string; outcome: Outcome };

function errorMessage(error: unknown): string {
  return error instanceof Error && error.message !== "" ? error.message : "圖表語法有誤，無法渲染";
}

/** 原始碼文字替代：失敗與逾時時直接顯示；成功時收在「檢視原始碼」裡。 */
function SourceText({ code }: { code: string }) {
  return (
    <pre data-testid="mermaid-source" className="overflow-x-auto rounded-md border border-wg-line bg-wg-base px-3 py-2 font-mono text-xs break-words whitespace-pre-wrap">
      {code}
    </pre>
  );
}

/** `label`：同一頁有多張圖時各自的區域名稱（預覽端傳「Mermaid 圖表 1」「Mermaid 圖表 2」…，避免同名地標）。 */
export function MermaidBlock({ code, label = "Mermaid 圖表" }: { code: string; label?: string }) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const [settled, setSettled] = useState<Settled | null>(null);
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const finish = (outcome: Outcome) => {
      if (!alive) return;
      alive = false;
      if (timer !== undefined) clearTimeout(timer);
      setSettled({ code, outcome });
    };
    void (async () => {
      try {
        const mermaid = await loadMermaid();
        if (!alive) return;
        mermaid.initialize({ ...MERMAID_CONFIG, themeVariables: mermaidThemeVariables() });
        timer = setTimeout(() => finish({ kind: "timeout" }), MERMAID_RENDER_TIMEOUT_MS);
        const { svg } = await mermaid.render(`mermaid-${uid}`, code);
        const node = parseMermaidSvg(svg);
        finish(node === null ? { kind: "error", message: "渲染結果不是有效的 SVG" } : { kind: "ready", svg: node });
      } catch (error) {
        finish({ kind: "error", message: errorMessage(error) });
      }
    })();
    return () => {
      alive = false;
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [code, uid]);

  const outcome = settled !== null && settled.code === code ? settled.outcome : null;
  const svg = outcome?.kind === "ready" ? outcome.svg : null;
  useEffect(() => {
    const el = host.current;
    if (el === null) return;
    if (svg === null) el.replaceChildren();
    else el.replaceChildren(document.importNode(svg, true));
  }, [svg]);

  const state = outcome === null ? "loading" : outcome.kind;
  return (
    <figure data-testid="mermaid-block" data-state={state} className="my-3 flex flex-col gap-2">
      {outcome === null ? (
        <p role="status" className="text-sm text-wg-muted">
          圖表渲染中…
        </p>
      ) : null}
      {outcome?.kind === "error" ? (
        <div role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm">
          <p className="font-semibold text-wg-accent">圖表無法渲染，改顯示原始碼</p>
          <p data-testid="mermaid-error" className="mt-1 break-words whitespace-pre-wrap">
            {outcome.message}
          </p>
        </div>
      ) : null}
      {outcome?.kind === "timeout" ? (
        <div role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm">
          <p data-testid="mermaid-timeout" className="font-semibold text-wg-accent">
            圖表渲染超過 {MERMAID_RENDER_TIMEOUT_MS / 1000} 秒，改顯示原始碼
          </p>
        </div>
      ) : null}
      {/* 可橫向捲動的區域必須能用鍵盤聚焦（axe scrollable-region-focusable；沿 MarkdownView 表格的做法） */}
      <div ref={host} role="region" aria-label={label} tabIndex={0} data-testid="mermaid-canvas" className={cn("overflow-x-auto", svg === null && "hidden")} />
      {outcome?.kind === "ready" ? (
        <details className="text-sm text-wg-muted">
          <summary className="cursor-pointer">檢視原始碼（文字替代）</summary>
          <SourceText code={code} />
        </details>
      ) : outcome === null ? null : (
        <SourceText code={code} />
      )}
    </figure>
  );
}
