import { act, render, screen, waitFor, within } from "@testing-library/react";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import ts from "typescript";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MERMAID_CONFIG, MERMAID_RENDER_TIMEOUT_MS, MERMAID_SECURITY_LEVEL, MermaidBlock, mermaidThemeVariables, parseMermaidSvg } from "./MermaidBlock";

/**
 * Mermaid 圖區塊（TCS-ResearchToPRD-P0-20261102 AT-960-16-3、AT-960-17-3；AC-R2P-09-3、09-9）：
 * `mermaid` 以模組替身（記錄 `initialize` 與 `render`）驗：初始化固定 `securityLevel: "strict"`、合法圖渲染成 SVG、語法錯誤退回錯誤與原始碼且整頁不崩潰、
 * 含 script 與事件屬性的輸出被淨化、3 秒逾時（假計時器）改顯示原始碼、每個區塊都有原始碼文字替代；另以 AST 掃描驗 `mermaid`、`diff` 只以動態形態載入。
 * 判定指令：npx vitest run components/domain/research/MermaidBlock.test.tsx -t "<AT 底線形>"
 */
const mm = vi.hoisted(() => ({ initialize: vi.fn(), render: vi.fn() }));
vi.mock("mermaid", () => ({ default: mm }));

const GOOD = "graph TD\n  A[需求] --> B[設計]";
const BAD = "graph TD\n  A[需求 --> ";
const HOSTILE = 'graph TD\n  A["<script>alert(1)</script>"] --> B\n  click A call alert(2)\n  A:::x onclick="alert(3)"';

const SVG_OK = '<svg xmlns="http://www.w3.org/2000/svg" id="mermaid-x" viewBox="0 0 10 10"><style>.node{fill:none}</style><g class="node"><text>需求</text></g></svg>';
/** 函式庫（或日後的版本）若回了不該有的東西：script、事件屬性、javascript: 網址、iframe、foreignObject 內的 HTML 事件屬性。 */
const SVG_HOSTILE = [
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">',
  "<script>window.__mermaid_xss = 'script'</script>",
  `<g onclick="window.__mermaid_xss = 'onclick'"><a href="javascript:window.__mermaid_xss = 'href'"><text>連結文字</text></a></g>`,
  "<a xlink:href=\"java\tscript:window.__mermaid_xss = 'split'\"><text>拆字連結</text></a>",
  '<iframe src="https://evil.test/"></iframe>',
  `<foreignObject><div onmouseover="window.__mermaid_xss = 'hover'">標籤文字</div></foreignObject>`,
  "</svg>",
].join("");

beforeEach(() => {
  mm.initialize.mockReset();
  mm.render.mockReset();
  mm.render.mockImplementation(async () => ({ svg: SVG_OK }));
});

describe("AT_960_16_3 Mermaid 嚴格模式渲染、錯誤退回原始碼、逾時退回原始碼", () => {
  it("AT_960_16_3 initialize 的設定固定 securityLevel: strict（常數、實際傳入值兩處都釘住）；startOnLoad 關閉；主題變數只放讀得到的設計 token", async () => {
    expect(MERMAID_SECURITY_LEVEL).toBe("strict");
    expect(MERMAID_CONFIG).toMatchObject({ securityLevel: "strict", startOnLoad: false, htmlLabels: false });
    render(<MermaidBlock code={GOOD} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-block")).toHaveAttribute("data-state", "ready"));
    expect(mm.initialize).toHaveBeenCalledTimes(1);
    const config = mm.initialize.mock.calls[0][0] as Record<string, unknown>;
    expect(config.securityLevel).toBe("strict");
    expect(config.startOnLoad).toBe(false);
    // 標籤畫成 SVG 文字：函式庫量測版面時不會把標籤的 HTML 放進真文件（strict 只淨化腳本與事件屬性、留下 img src，淨化之前瀏覽器就已對外發請求；真瀏覽器版見 AT_960_16_3 的 E2E）
    expect(config.htmlLabels).toBe(false);
    expect(config.suppressErrorRendering).toBe(true);
    expect(typeof config.themeVariables).toBe("object");
    // 沒有 CSS 的單元測試環境讀不到 token：不放空字串、不放猜的色碼
    expect(Object.values(mermaidThemeVariables()).every((v) => v !== "")).toBe(true);
  });

  it("AT_960_16_3 themeVariables 取自 :root 的設計 token（有值才放），字型取頁面字型；程式碼本身不含任何色碼", () => {
    document.documentElement.style.setProperty("--color-primary", "#498428");
    document.documentElement.style.setProperty("--color-text-main", "#2A3626");
    try {
      const vars = mermaidThemeVariables();
      expect(vars.primaryBorderColor).toBe("#498428");
      expect(vars.primaryTextColor).toBe("#2A3626");
      expect(vars.textColor).toBe("#2A3626");
      expect(vars).not.toHaveProperty("lineColor"); // --color-text-muted 沒設定＝不放
    } finally {
      document.documentElement.style.removeProperty("--color-primary");
      document.documentElement.style.removeProperty("--color-text-main");
    }
    const source = readFileSync(path.join(process.cwd(), "components", "domain", "research", "MermaidBlock.tsx"), "utf-8")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/(^|[^:"'`])\/\/.*$/gm, "$1");
    expect(source).not.toMatch(/#[0-9a-fA-F]{3,6}\b|\b(rgb|rgba|hsl|oklch)\(/);
  });

  it("AT_960_16_3 合法區塊渲染為 SVG 容器；每個區塊都附原始碼文字替代（成功者收在「檢視原始碼」裡）", async () => {
    render(<MermaidBlock code={GOOD} label="Mermaid 圖表 1" />);
    const block = await screen.findByTestId("mermaid-block");
    await waitFor(() => expect(block).toHaveAttribute("data-state", "ready"));
    expect(mm.render).toHaveBeenCalledTimes(1);
    expect(mm.render.mock.calls[0][1]).toBe(GOOD);
    const canvas = screen.getByRole("region", { name: "Mermaid 圖表 1" });
    expect(canvas.querySelector("svg")).not.toBeNull();
    expect(within(canvas).getByText("需求")).toBeInTheDocument();
    expect(canvas).toHaveAttribute("tabindex", "0"); // 可橫向捲動的區域要能用鍵盤聚焦
    const details = block.querySelector("details");
    expect(details, "成功的圖也有原始碼文字替代").not.toBeNull();
    expect(within(details as HTMLElement).getByTestId("mermaid-source").textContent).toBe(GOOD);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("AT_960_16_3 語法錯誤的區塊顯示錯誤訊息與原始碼文字，整頁不崩潰（兄弟節點照常）", async () => {
    mm.render.mockImplementation(async (_id: string, code: string) => {
      if (code === BAD) throw new Error("Parse error on line 2: Expecting 'SQE'");
      return { svg: SVG_OK };
    });
    render(
      <main>
        <h1>PRD 標題</h1>
        <MermaidBlock code={BAD} label="Mermaid 圖表 1" />
        <MermaidBlock code={GOOD} label="Mermaid 圖表 2" />
        <p>結尾段落</p>
      </main>,
    );
    await waitFor(() => expect(screen.getAllByTestId("mermaid-block").map((b) => b.getAttribute("data-state"))).toEqual(["error", "ready"]));
    const [bad, good] = screen.getAllByTestId("mermaid-block");
    expect(within(bad).getByTestId("mermaid-error")).toHaveTextContent("Parse error on line 2");
    expect(within(bad).getByRole("alert")).toHaveTextContent("改顯示原始碼");
    expect(within(bad).getByTestId("mermaid-source").textContent, "錯誤區塊直接顯示原始碼文字").toBe(BAD);
    expect(within(good).getByRole("region", { name: "Mermaid 圖表 2" }).querySelector("svg")).not.toBeNull();
    expect(screen.getByRole("heading", { name: "PRD 標題" })).toBeInTheDocument();
    expect(screen.getByText("結尾段落")).toBeInTheDocument();
  });

  it("AT_960_16_3 含 <script> 與事件屬性的圖：函式庫即使回了可執行內容，輸出也不含任何可執行節點（script、iframe、on* 屬性、javascript: 網址）", async () => {
    mm.render.mockImplementation(async () => ({ svg: SVG_HOSTILE }));
    const { container } = render(<MermaidBlock code={HOSTILE} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-block")).toHaveAttribute("data-state", "ready"));
    expect(container.querySelector("script, iframe, object, embed")).toBeNull();
    const attrs = Array.from(container.querySelectorAll("*")).flatMap((el) => Array.from(el.attributes).map((a) => `${a.name}=${a.value}`));
    expect(attrs.filter((a) => /^on/i.test(a))).toEqual([]);
    expect(attrs.filter((a) => /javascript:/i.test(a.replace(/[\u0000- ]/g, "")))).toEqual([]);
    // 安全的內容保留：圖上的文字還在
    expect(within(screen.getByTestId("mermaid-canvas")).getByText("連結文字")).toBeInTheDocument();
    expect(within(screen.getByTestId("mermaid-canvas")).getByText("標籤文字")).toBeInTheDocument();
    expect((window as unknown as { __mermaid_xss?: string }).__mermaid_xss, "沒有任何腳本執行").toBeUndefined();
    // 原始碼（含 <script> 字樣）只當文字顯示
    expect(screen.getByTestId("mermaid-source").textContent).toBe(HOSTILE);
  });

  it("AT_960_16_3 渲染逾時 3 秒（假計時器）：差一毫秒仍在渲染中、滿 3 秒改顯示原始碼與說明；之後函式庫才回應也不覆蓋", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      let release: (value: { svg: string }) => void = () => {};
      mm.render.mockImplementation(() => new Promise<{ svg: string }>((resolve) => (release = resolve)));
      render(<MermaidBlock code={GOOD} />);
      for (let i = 0; i < 50 && mm.render.mock.calls.length === 0; i += 1) await act(async () => Promise.resolve());
      expect(mm.render).toHaveBeenCalledTimes(1);
      expect(MERMAID_RENDER_TIMEOUT_MS).toBe(3000);
      await act(async () => {
        vi.advanceTimersByTime(MERMAID_RENDER_TIMEOUT_MS - 1);
      });
      expect(screen.getByTestId("mermaid-block")).toHaveAttribute("data-state", "loading");
      expect(screen.getByRole("status")).toHaveTextContent("圖表渲染中");
      await act(async () => {
        vi.advanceTimersByTime(1);
      });
      expect(screen.getByTestId("mermaid-block")).toHaveAttribute("data-state", "timeout");
      expect(screen.getByTestId("mermaid-timeout")).toHaveTextContent("渲染超過 3 秒，改顯示原始碼");
      expect(screen.getByTestId("mermaid-source").textContent).toBe(GOOD);
      await act(async () => {
        release({ svg: SVG_OK });
        await Promise.resolve();
      });
      expect(screen.getByTestId("mermaid-block"), "逾時後函式庫才回應：不覆蓋已顯示的原始碼").toHaveAttribute("data-state", "timeout");
    } finally {
      vi.useRealTimers();
    }
  });

  it("AT_960_16_3 程式碼換了就重新渲染：舊程式碼的結果即使較晚到也不顯示", async () => {
    let releaseOld: (value: { svg: string }) => void = () => {};
    mm.render.mockImplementation((_id: string, code: string) =>
      code === GOOD ? new Promise<{ svg: string }>((resolve) => (releaseOld = resolve)) : Promise.resolve({ svg: SVG_OK.replace("需求", "新圖") }),
    );
    const { rerender } = render(<MermaidBlock code={GOOD} />);
    await waitFor(() => expect(mm.render).toHaveBeenCalledTimes(1));
    rerender(<MermaidBlock code={"graph LR\n  X --> Y"} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-block")).toHaveAttribute("data-state", "ready"));
    expect(within(screen.getByTestId("mermaid-canvas")).getByText("新圖")).toBeInTheDocument();
    await act(async () => {
      releaseOld({ svg: SVG_OK });
      await Promise.resolve();
    });
    expect(within(screen.getByTestId("mermaid-canvas")).getByText("新圖")).toBeInTheDocument();
    expect(within(screen.getByTestId("mermaid-canvas")).queryByText("需求")).toBeNull();
  });

  it("AT_960_16_3 淨化函式：沒有 <svg> 回 null；保留 style 與文字；拆字的 javascript: 也被擋；解析結果不含 body 外的東西", () => {
    expect(parseMermaidSvg("<p>不是圖</p>")).toBeNull();
    expect(parseMermaidSvg("")).toBeNull();
    const ok = parseMermaidSvg(SVG_OK) as SVGSVGElement;
    expect(ok.querySelector("style")).not.toBeNull();
    expect(ok.textContent).toContain("需求");
    const hostile = parseMermaidSvg(SVG_HOSTILE) as SVGSVGElement;
    expect(hostile.querySelector("script, iframe")).toBeNull();
    expect(Array.from(hostile.querySelectorAll("*")).some((el) => Array.from(el.attributes).some((a) => /^on/i.test(a.name) || /javascript/i.test(a.value.replace(/[\u0000- ]/g, ""))))).toBe(false);
    expect(hostile.textContent).toContain("拆字連結");
    // data: 的 HTML、vbscript: 同樣擋
    const odd = parseMermaidSvg(
      '<svg><a href="data:text/html,<b>x</b>"><text>d</text></a><a href="vbscript:x"><text>v</text></a><a href="https://example.com/"><text>ok</text></a></svg>',
    ) as SVGSVGElement;
    const hrefs = Array.from(odd.querySelectorAll("a")).map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual([null, null, "https://example.com/"]);
  });

  it("AT_960_16_3 淨化函式不留任何會對外發請求的東西：圖片與影音元素、src／srcset／poster、外部 url()（屬性與 style 元素的 @import）、指向文件外的 use 參照、SMIL 動畫都拿掉；圖內的 url(#id) 參照與一般外部連結保留（連結補 noopener noreferrer）", () => {
    const svg = [
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">',
      '<defs><marker id="arrow"><path d="M0 0"/></marker></defs>',
      '<path id="p" marker-end="url(#arrow)" stroke="url(#arrow)" fill="url(https://evil.test/f)" d="M0 0 L5 5"/>',
      '<image href="https://evil.test/pixel.png"/>',
      '<foreignObject><div><img src="https://evil.test/a.png"><video src="https://evil.test/v.mp4" poster="https://evil.test/p.png"></video>',
      '<span style="background:url(https://evil.test/b.png)">標籤文字</span><picture><source srcset="https://evil.test/c.png"></picture></div></foreignObject>',
      '<style>@import url("https://evil.test/x.css"); .a{fill:red}</style>',
      '<use href="https://evil.test/sprite.svg#a"/><use href="#arrow"/>',
      '<a href="https://example.com/ok"><text>外部連結</text></a>',
      '<a href="https://x.test/"><animate attributeName="href" values="javascript:alert(1)"/><text>動畫連結</text></a>',
      "</svg>",
    ].join("");
    const root = parseMermaidSvg(svg) as SVGSVGElement;
    expect(root.querySelectorAll("img, image, picture, source, video, audio, animate, style")).toHaveLength(0);
    expect(root.outerHTML, "輸出裡沒有任何指向外部的網址").not.toContain("evil.test");
    const path = root.querySelector("#p") as Element;
    expect(path.getAttribute("marker-end"), "圖內的 url(#id) 參照保留").toBe("url(#arrow)");
    expect(path.getAttribute("stroke")).toBe("url(#arrow)");
    expect(path.hasAttribute("fill"), "外部 url() 的填色屬性拿掉").toBe(false);
    expect(root.querySelector("span")?.hasAttribute("style"), "內嵌樣式裡的外部 url() 連同屬性拿掉").toBe(false);
    expect(root.textContent).toContain("標籤文字");
    expect(
      Array.from(root.querySelectorAll("use")).map((u) => u.getAttribute("href")),
      "use 的參照只准指向圖內",
    ).toEqual([null, "#arrow"]);
    const link = root.querySelector('a[href="https://example.com/ok"]') as Element;
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(root.textContent).toContain("動畫連結");
  });
});

// ── AT_960_17_3 import 圖掃描（AST）────────────────────────────────────────────────────

type ImportRef = { spec: string; kind: "static" | "dynamic" | "type" };

/** 以 TypeScript 編譯器的語法樹取出一個檔的所有模組參照（靜態、動態 `import()`、僅型別的 `import type`）。 */
function importsOf(file: string, text: string): ImportRef[] {
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const out: ImportRef[] = [];
  const visit = (node: ts.Node): void => {
    if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) out.push({ spec: node.moduleSpecifier.text, kind: node.importClause?.isTypeOnly === true ? "type" : "static" });
    else if (ts.isExportDeclaration(node) && node.moduleSpecifier !== undefined && ts.isStringLiteral(node.moduleSpecifier))
      out.push({ spec: node.moduleSpecifier.text, kind: node.isTypeOnly ? "type" : "static" });
    else if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword && node.arguments.length > 0 && ts.isStringLiteralLike(node.arguments[0]))
      out.push({ spec: node.arguments[0].text, kind: "dynamic" });
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return out;
}

const ROOT = process.cwd();
const rel = (full: string): string => path.relative(ROOT, full).split(path.sep).join("/");

function sourceFiles(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) sourceFiles(full, out);
    else if (/\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name)) out.push(full);
  }
  return out;
}

/** 解析專案內的模組參照（`@/…` 與相對路徑）；套件參照（`react`、`mermaid`…）回 null。 */
function resolveLocal(from: string, spec: string): string | null {
  const base = spec.startsWith("@/") ? path.join(ROOT, spec.slice(2)) : spec.startsWith(".") ? path.resolve(path.dirname(from), spec) : null;
  if (base === null) return null;
  for (const candidate of [base, `${base}.ts`, `${base}.tsx`, path.join(base, "index.ts"), path.join(base, "index.tsx")]) if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  return null;
}

/** 自某個入口檔沿「靜態」import 走完整張圖（動態 `import()` 不追：那正是延遲載入的出口）。 */
function staticClosure(entry: string): Map<string, ImportRef[]> {
  const seen = new Map<string, ImportRef[]>();
  const queue = [entry];
  while (queue.length > 0) {
    const file = queue.pop() as string;
    if (seen.has(file)) continue;
    const refs = importsOf(file, readFileSync(file, "utf-8"));
    seen.set(file, refs);
    for (const ref of refs) {
      if (ref.kind !== "static") continue;
      const target = resolveLocal(file, ref.spec);
      if (target !== null) queue.push(target);
    }
  }
  return seen;
}

const isLib = (spec: string, name: string): boolean => spec === name || spec.startsWith(`${name}/`);

describe("AT_960_17_3 mermaid 只經動態載入、不進首屏 chunk；diff 只在 Diff 模式載入", () => {
  const files = [...sourceFiles(path.join(ROOT, "components", "domain", "research")), ...sourceFiles(path.join(ROOT, "app", "research"))];
  const refsByFile = new Map(files.map((f) => [rel(f), importsOf(f, readFileSync(f, "utf-8"))] as const));

  it("AT_960_17_3 掃描範圍非空；沒有任何靜態 import mermaid 或 diff；mermaid 的動態載入限於 MermaidBlock.tsx、diff 限於 PrdDiffView.tsx", () => {
    expect(files.length, "掃描範圍非空（components/domain/research 與 app/research 的非測試原始碼）").toBeGreaterThanOrEqual(10);
    expect([...refsByFile.keys()]).toEqual(
      expect.arrayContaining(["components/domain/research/MermaidBlock.tsx", "components/domain/research/PrdDiffView.tsx", "components/domain/research/StudioPanel.tsx"]),
    );
    const dynamicIn = (name: string): string[] => [...refsByFile].filter(([, refs]) => refs.some((r) => r.kind === "dynamic" && isLib(r.spec, name))).map(([file]) => file);
    const staticOf = (name: string): string[] => [...refsByFile].filter(([, refs]) => refs.some((r) => r.kind === "static" && isLib(r.spec, name))).map(([file]) => file);
    expect(staticOf("mermaid")).toEqual([]);
    expect(staticOf("diff")).toEqual([]);
    expect(dynamicIn("mermaid")).toEqual(["components/domain/research/MermaidBlock.tsx"]);
    expect(dynamicIn("diff")).toEqual(["components/domain/research/PrdDiffView.tsx"]);
  });

  it("AT_960_17_3 app/research 下每個 page.tsx 的靜態 import 圖（含 lib、components 一路走到底）沒有 mermaid 與 diff；StudioPanel 在圖內（頁殼真的接了）而 MermaidBlock 不在（只能動態載入）", () => {
    const pages = files.filter((f) => rel(f).startsWith("app/research/") && f.endsWith("page.tsx"));
    expect(pages.map(rel).sort()).toEqual(["app/research/[researchId]/page.tsx", "app/research/page.tsx"]);
    for (const page of pages) {
      const closure = staticClosure(page);
      expect(closure.size, `${rel(page)} 的靜態 import 圖非空`).toBeGreaterThan(10);
      for (const [file, refs] of closure)
        for (const ref of refs) expect(ref.kind === "static" && (isLib(ref.spec, "mermaid") || isLib(ref.spec, "diff")), `${rel(file)} 靜態 import 了 ${ref.spec}`).toBe(false);
      if (rel(page) === "app/research/[researchId]/page.tsx") {
        const members = [...closure.keys()].map(rel);
        expect(members).toContain("components/domain/research/StudioPanel.tsx");
        expect(members).not.toContain("components/domain/research/MermaidBlock.tsx");
      }
    }
  });

  it("AT_960_17_3 掃描器負控：靜態 import、動態 import()、next/dynamic 包的 import()、僅型別 import 各自分類正確", () => {
    expect(importsOf("a.tsx", 'import mermaid from "mermaid";')).toEqual([{ spec: "mermaid", kind: "static" }]);
    expect(importsOf("a.tsx", 'import { diffLines } from "diff";')).toEqual([{ spec: "diff", kind: "static" }]);
    expect(importsOf("a.tsx", 'export { x } from "mermaid/dist/x";')).toEqual([{ spec: "mermaid/dist/x", kind: "static" }]);
    expect(importsOf("a.tsx", 'const m = await import("mermaid");')).toEqual([{ spec: "mermaid", kind: "dynamic" }]);
    expect(importsOf("a.tsx", 'const X = dynamic(() => import("diff").then((m) => m.diffLines));')).toEqual([{ spec: "diff", kind: "dynamic" }]);
    expect(importsOf("a.tsx", 'import type { MermaidConfig } from "mermaid";')).toEqual([{ spec: "mermaid", kind: "type" }]);
    expect(importsOf("a.tsx", '// import mermaid from "mermaid";\nconst s = "import(\\"mermaid\\")";')).toEqual([]);
    expect(isLib("mermaid/dist/x", "mermaid")).toBe(true);
    expect(isLib("mermaid-extra", "mermaid")).toBe(false);
    expect(isLib("diffable", "diff")).toBe(false);
  });
});
