import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

/**
 * SelfImproving 頁的靜態守衛（P1b：TCS-SelfImprovingMirror-P1b R11、R18；P2b：TCS-SelfImprovingDecide-P2b W22）：
 *  - AT_932_1_E_8：純文字渲染——沒有 dangerouslySetInnerHTML、沒有任何 Markdown／HTML 渲染器；
 *  - AT_950_9_E_2：寫入形態收斂——`<form`、mutation hook 與非 GET 字樣只准出現在三個寫入元件（取代 P1b 的 AT_932_2_8「零寫入」）；
 *    全樹（含三個寫入元件）無直接 `fetch(`、無 PUT／PATCH／DELETE 方法字樣；
 *  - AT_932_4_3：瀏覽器不直連 Bridge——前端原始碼沒有 Bridge 路徑字面（以 /si/ 起頭）、沒有 8081、沒有 BRIDGE 環境變數讀取。
 * 每個掃描器都是純函式（輸入原始碼文字、輸出違規清單），各有負控樣本；掃描範圍有防反空轉斷言。
 */
const ROOT = process.cwd();
const rel = (file: string) => path.relative(ROOT, file).split(path.sep).join("/");
const SKIP_DIRS = new Set(["node_modules", ".next", "tests", "coverage", "test-results", "playwright-report"]);

function walk(dir: string, out: string[] = []): string[] {
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (!SKIP_DIRS.has(name)) walk(full, out);
    } else if (/\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) && !/\.d\.ts$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

/** SelfImproving 頁面的非測試原始碼：components/domain/si/** 與 app/self-improving/**。 */
function siSources(): Array<{ file: string; text: string }> {
  return ["components/domain/si", "app/self-improving"].flatMap((d) => walk(path.join(ROOT, d))).map((f) => ({ file: rel(f), text: readFileSync(f, "utf-8") }));
}

function parse(source: string): ts.SourceFile {
  return ts.createSourceFile("scan.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
}

function walkAst(node: ts.Node, visit: (n: ts.Node) => void): void {
  visit(node);
  ts.forEachChild(node, (child) => walkAst(child, visit));
}

/** import／export from、動態 import()、require() 的模組名稱字串（它們是模組位址，不是「字串字面值」的檢查對象）。 */
function moduleSpecifierNodes(source: ts.SourceFile): Set<ts.Node> {
  const specs = new Set<ts.Node>();
  walkAst(source, (n) => {
    if ((ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) && n.moduleSpecifier) specs.add(n.moduleSpecifier);
    if (ts.isCallExpression(n) && n.arguments.length > 0 && (n.expression.kind === ts.SyntaxKind.ImportKeyword || (ts.isIdentifier(n.expression) && n.expression.text === "require")))
      specs.add(n.arguments[0]);
  });
  return specs;
}

function moduleNames(source: string): string[] {
  const sf = parse(source);
  return [...moduleSpecifierNodes(sf)].filter(ts.isStringLiteralLike).map((n) => n.text);
}

// ── AT_932_1_E_8：純文字渲染 ─────────────────────────────────────────────────

/** Markdown 與 HTML 渲染器：react-markdown、rehype*、remark*、@uiw/react-md-editor、本專案 components/markdown/*（含相對路徑引用）。 */
function isRendererModule(spec: string): boolean {
  if (/^(react-markdown|rehype|remark|@uiw\/react-md-editor)/.test(spec)) return true;
  return (spec.startsWith("@/") || spec.startsWith(".")) && /(^|\/)markdown(\/|$)/.test(spec);
}

function rendererViolations(source: string): string[] {
  const found: string[] = [];
  if (source.includes("dangerouslySetInnerHTML")) found.push("dangerouslySetInnerHTML");
  for (const spec of moduleNames(source)) if (isRendererModule(spec)) found.push(`import ${spec}`);
  return found;
}

describe("AT_932_1_E_8 SI 原始碼無 dangerouslySetInnerHTML 與 Markdown 渲染器（R18）", () => {
  it("AT_932_1_E_8 components/domain/si/** 與 app/self-improving/** 的非測試原始碼都沒有違規；page.tsx 全文不含四個區塊的名字", () => {
    const sources = siSources();
    expect(sources.map((s) => s.file)).toEqual(expect.arrayContaining(["components/domain/si/SiView.tsx", "app/self-improving/page.tsx"]));
    expect(sources.length, "掃描範圍太小：防反空轉").toBeGreaterThanOrEqual(6);
    for (const { file, text } of sources) expect(rendererViolations(text), file).toEqual([]);
    const page = sources.find((s) => s.file === "app/self-improving/page.tsx") as { text: string };
    expect(page.text).not.toMatch(/TopRegion|ToolsRegion|ContentRegion|BottomRegion/);
  });

  it("AT_932_1_E_8 掃描器的負控：違規樣本逐一回非空，良性樣本回空", () => {
    const bad = [
      "<div dangerouslySetInnerHTML={{ __html: x }} />",
      'import ReactMarkdown from "react-markdown";',
      'import rehypeRaw from "rehype-raw";',
      'import remarkGfm from "remark-gfm";',
      'import MDEditor from "@uiw/react-md-editor";',
      'import { MarkdownView } from "@/components/markdown/MarkdownView";',
      'import { MarkdownView } from "../../markdown/MarkdownView";',
      'const m = await import("react-markdown");',
    ];
    for (const sample of bad) expect(rendererViolations(sample), sample).not.toEqual([]);
    const good = [
      'import { Button } from "@/components/ui/button";',
      'import { useSiStatus } from "@/lib/api/queries";',
      "const html = '<b>字面文字</b>';",
      'import { markdownLike } from "./markdownLike";',
    ];
    for (const sample of good) expect(rendererViolations(sample), sample).toEqual([]);
  });
});

// ── AT_950_9_E_2：寫入形態只准在三個寫入元件（P2b W22；取代 P1b 的 AT_932_2_8）────────────

function importedNames(source: string, fromPattern: RegExp): string[] {
  const names: string[] = [];
  walkAst(parse(source), (n) => {
    if (ts.isImportDeclaration(n) && ts.isStringLiteral(n.moduleSpecifier) && fromPattern.test(n.moduleSpecifier.text)) {
      const bindings = n.importClause?.namedBindings;
      if (bindings && ts.isNamedImports(bindings)) for (const el of bindings.elements) names.push((el.propertyName ?? el.name).text);
    }
  });
  return names;
}

/** 三個寫入元件：`<form`、mutation hook 與非 GET 字樣只准出現在它們（W22）。 */
const WRITE_COMPONENTS: ReadonlyArray<string> = ["components/domain/si/SiDecideDialog.tsx", "components/domain/si/SiObsForm.tsx", "components/domain/si/SiObsCloseDialog.tsx"];
/** 各寫入元件預期 import 的寫入 hook（防反空轉：掃描器看得到 import；少了＝元件不再走這條路）。 */
const EXPECTED_WRITE_HOOKS: Readonly<Record<string, string[]>> = {
  "components/domain/si/SiDecideDialog.tsx": ["useSiDecide"],
  "components/domain/si/SiObsForm.tsx": ["useSiAddObservation", "useSiValidateObservation"],
  "components/domain/si/SiObsCloseDialog.tsx": ["useSiCloseObservation"],
};
/** 寫入型 query hook：P1b 的「寫入動詞開頭」加 P2b 的四個 useSi 寫入 hook（`useSiConsoleWrites` 是讀取，不在內）。 */
const WRITE_HOOK = /^(use(Create|Update|Delete|Post|Put|Patch|Retry|Approve|Signoff|Execute)|useSi(Decide|AddObservation|CloseObservation|ValidateObservation))/;

/** 只准在三個寫入元件出現的形態。 */
function writeFormViolations(source: string): string[] {
  const found: string[] = [];
  if (/<form[\s>]/.test(source)) found.push("<form");
  if (/type\s*[=:]\s*["']submit["']/.test(source)) found.push("type submit");
  if (/\buseMutation\b/.test(source)) found.push("useMutation");
  if (/\buseWrite\b/.test(source)) found.push("useWrite");
  if (/\buseSiWrite\b/.test(source)) found.push("useSiWrite");
  const method = /method\s*:\s*["'](POST|PUT|PATCH|DELETE)["']/i.exec(source);
  if (method) found.push(`method: ${method[1]}`);
  for (const name of importedNames(source, /(^|\/)queries$/)) if (WRITE_HOOK.test(name)) found.push(`import ${name}`);
  return found;
}

/** 全樹（含三個寫入元件）一律不准的形態：直接 fetch、PUT／PATCH／DELETE 方法字樣（刪除、覆寫、局部更新在 SelfImproving 沒有任何用途）。 */
function everywhereViolations(source: string): string[] {
  const found: string[] = [];
  if (/\bfetch\s*\(/.test(source)) found.push("fetch(");
  const method = /method\s*:\s*["'](PUT|PATCH|DELETE)["']/i.exec(source);
  if (method) found.push(`method: ${method[1]}`);
  const literal = /["'`](PUT|PATCH|DELETE)["'`]/.exec(source);
  if (literal) found.push(`方法字樣：${literal[1]}`);
  return found;
}

describe("AT_950_9_E_2 SI 前端寫入形態只在三個寫入元件，全樹無直接 fetch 與 PUT／PATCH／DELETE（W22）", () => {
  it("AT_950_9_E_2 `<form`、mutation hook 呼叫與非 GET 字樣只出現在 SiDecideDialog、SiObsForm、SiObsCloseDialog；其餘檔案（SiView、各面板、對帳面板、共用小件）一個都沒有，也不 import 寫入型 query hook", () => {
    const sources = siSources();
    expect(sources.length, "掃描範圍太小：防反空轉").toBeGreaterThanOrEqual(10);
    expect(sources.map((s) => s.file)).toEqual(expect.arrayContaining([...WRITE_COMPONENTS, "components/domain/si/SiWritesPanel.tsx", "components/domain/si/SiView.tsx"]));
    for (const { file, text } of sources) {
      if (WRITE_COMPONENTS.includes(file)) continue;
      expect(writeFormViolations(text), `${file} 不得有寫入形態`).toEqual([]);
    }
    // 防反空轉：掃描器在三個寫入元件上確實看得到寫入形態——有 <form、import 了預期的寫入 hook，且整棵樹只有這四個寫入 hook
    const allWriteHooks = new Set<string>();
    for (const file of WRITE_COMPONENTS) {
      const { text } = sources.find((s) => s.file === file) as { text: string };
      const imported = importedNames(text, /(^|\/)queries$/).filter((n) => WRITE_HOOK.test(n));
      expect(imported.sort(), `${file} import 的寫入 hook`).toEqual([...EXPECTED_WRITE_HOOKS[file]].sort());
      expect(writeFormViolations(text), `${file} 應被掃描器看見寫入形態`).toEqual(expect.arrayContaining(["<form", ...EXPECTED_WRITE_HOOKS[file].map((h) => `import ${h}`)]));
      imported.forEach((n) => allWriteHooks.add(n));
    }
    expect([...allWriteHooks].sort()).toEqual(["useSiAddObservation", "useSiCloseObservation", "useSiDecide", "useSiValidateObservation"]);
    // 讀取 hook 不受限：對帳面板與 SiView 照常 import 讀取型的 useSiConsoleWrites 等
    const reads = sources.flatMap((s) => importedNames(s.text, /(^|\/)queries$/)).filter((n) => !WRITE_HOOK.test(n));
    expect(reads).toEqual(expect.arrayContaining(["useSiStatus", "useSiObservations", "useSiProposals", "useSiEvents", "useSiRuns", "useSiConsoleWrites"]));
  });

  it("AT_950_9_E_2 全樹（含三個寫入元件）無直接 fetch(、無 PUT／PATCH／DELETE 方法字樣、無 dangerouslySetInnerHTML 與 Markdown 渲染器", () => {
    const sources = siSources();
    for (const { file, text } of sources) {
      expect(everywhereViolations(text), file).toEqual([]);
      expect(rendererViolations(text), file).toEqual([]);
    }
  });

  it("AT_950_9_E_2 掃描器的負控：各種寫入形態與全樹禁止形態的樣本逐一回非空，唯讀樣本回空", () => {
    const badForm = [
      "<form onSubmit={go}>",
      '<button type="submit">x</button>',
      "const t = { type: 'submit' };",
      "const m = useMutation({ mutationFn });",
      "const w = useWrite(fn);",
      "const w = useSiWrite(fn);",
      'fetch(u, { method: "POST" })',
      "fetch(u, { method: 'delete' })",
      'import { useCreateProject } from "@/lib/api/queries";',
      'import { useSignoffTask as s } from "@/lib/api/queries";',
      'import { useExecuteX, useSiStatus } from "./queries";',
      'import { useSiDecide } from "@/lib/api/queries";',
      'import { useSiAddObservation } from "@/lib/api/queries";',
      'import { useSiCloseObservation as c } from "@/lib/api/queries";',
      'import { useSiValidateObservation, useSiStatus } from "./queries";',
    ];
    for (const sample of badForm) expect(writeFormViolations(sample), sample).not.toEqual([]);
    const goodForm = [
      'import { useSiStatus, useSiRuns } from "@/lib/api/queries";',
      'import { useSiConsoleWrites } from "@/lib/api/queries";',
      'fetch(u, { method: "GET" })',
      '<button type="button">重試</button>',
      'import { useAllProjects } from "@/lib/api/queries";',
    ];
    for (const sample of goodForm) expect(writeFormViolations(sample), sample).toEqual([]);

    const badEverywhere = ['const r = await fetch("/api/v1/x");', "fetch (url)", 'send({ method: "DELETE" })', "send({ method: 'put' })", 'const verb = "PATCH";', "const verb = `DELETE`;"];
    for (const sample of badEverywhere) expect(everywhereViolations(sample), sample).not.toEqual([]);
    const goodEverywhere = ['import { postSiDecide } from "@/lib/api/endpoints";', "const prefetch = 1;", 'const label = "Deleted rows";', "<p>PUT 是方法名</p>", 'send({ method: "POST" })'];
    for (const sample of goodEverywhere) expect(everywhereViolations(sample), sample).toEqual([]);
  });
});

// ── AT_932_4_3：瀏覽器不直連 Bridge ────────────────────────────────────────────

function bridgeLeaks(source: string): string[] {
  const sf = parse(source);
  const specs = moduleSpecifierNodes(sf);
  const found: string[] = [];
  const checkText = (text: string) => {
    if (text.startsWith("/si/")) found.push(`Bridge 路徑字面：${text}`);
    else if (/\/si\//.test(text) && !text.startsWith("/api/v1/si/")) found.push(`含 /si/ 路徑段但不是 /api/v1/si/ 起頭：${text}`);
    if (text.includes("8081")) found.push(`8081：${text}`);
  };
  walkAst(sf, (n) => {
    if (specs.has(n)) return;
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) checkText(n.text);
    else if (ts.isTemplateExpression(n)) {
      checkText(n.head.text);
      for (const span of n.templateSpans) checkText(span.literal.text);
    } else if (ts.isNumericLiteral(n) && n.text === "8081") found.push("8081：數字字面");
    else if (ts.isPropertyAccessExpression(n) && /BRIDGE/i.test(n.name.text) && n.expression.getText(sf).includes("process.env")) found.push(`環境變數讀取：${n.getText(sf)}`);
    else if (ts.isElementAccessExpression(n) && n.expression.getText(sf).includes("process.env") && ts.isStringLiteralLike(n.argumentExpression) && /BRIDGE/i.test(n.argumentExpression.text))
      found.push(`環境變數讀取：${n.getText(sf)}`);
  });
  return found;
}

describe("AT_932_4_3 前端原始碼不含 Bridge 路徑字面（R11）", () => {
  const sources = ["app", "components", "lib", "hooks"].flatMap((d) => walk(path.join(ROOT, d))).map((f) => ({ file: rel(f), text: readFileSync(f, "utf-8") }));

  it("AT_932_4_3 app、components、lib、hooks 的非測試原始碼：沒有以 /si/ 起頭的字面、含 si/ 路徑段的字面皆以 /api/v1/si/ 起頭、沒有 8081、沒有 BRIDGE 環境變數讀取", () => {
    expect(sources.length, "掃描範圍太小：防反空轉").toBeGreaterThan(100);
    const endpoints = sources.find((s) => s.file === "lib/api/endpoints.ts");
    expect(endpoints, "掃描範圍必須含 lib/api/endpoints.ts").toBeDefined();
    // 防反空轉：掃描器真的看得到 endpoints.ts 裡的 SI 路徑字面（以 /api/v1/si/ 起頭者合法）
    const literals: string[] = [];
    walkAst(parse((endpoints as { text: string }).text), (n) => {
      if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) literals.push(n.text);
      else if (ts.isTemplateExpression(n)) literals.push(n.head.text);
    });
    expect(literals).toEqual(
      expect.arrayContaining([
        "/api/v1/si/status",
        "/api/v1/si/observations",
        "/api/v1/si/events",
        "/api/v1/si/proposals",
        "/api/v1/si/proposals/",
        "/api/v1/si/runs",
        "/api/v1/si/observations/validate",
        "/api/v1/si/observations/",
        "/api/v1/si/console-writes",
      ]),
    );
    for (const { file, text } of sources) expect(bridgeLeaks(text), file).toEqual([]);
  });

  it("AT_932_4_3 掃描器的負控：Bridge 路徑、指向 engine-bridge:8081 的網址與 BRIDGE 環境變數讀取逐一回非空；/api/v1/si/ 與模組位址回空", () => {
    const bad = [
      'const u = "/si/status";',
      "const u = `/si/runs?limit=${n}`;",
      'const u = "http://engine-bridge:8081/si/runs";',
      "const port = 8081;",
      "const base = process.env.NEXT_PUBLIC_BRIDGE_URL;",
      'const base = process.env["BRIDGE_URL"];',
      "const u = `${base}/si/proposals/${id}`;",
    ];
    for (const sample of bad) expect(bridgeLeaks(sample), sample).not.toEqual([]);
    const good = [
      'const u = "/api/v1/si/status";',
      "const u = `/api/v1/si/proposals/${id}`;",
      'import { SiView } from "@/components/domain/si/SiView";',
      "const base = process.env.NEXT_PUBLIC_API_URL;",
    ];
    for (const sample of good) expect(bridgeLeaks(sample), sample).toEqual([]);
  });
});
