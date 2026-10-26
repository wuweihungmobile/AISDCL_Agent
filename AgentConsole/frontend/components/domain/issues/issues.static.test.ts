import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

/**
 * 議題中心前端的靜態守衛（TCS-IssueCenter-20261027 R-IC-68、R-IC-72、R-IC-73；AT-IC-06-2-3、06-2-E-2、08-7-2、08-7-E-1、10-3-1、10-3-E-1）：
 *  - 單一真相：議題的七狀態對照表只住根層 `issuemap.py`；前端新檔（`components/domain/issues/**`、`lib/domain/issues.ts`）不得自己持有一份狀態詞清單——
 *    判準＝同一個檔不得含 ≥4 個**不同**的狀態名（同一個詞出現幾次都只算一個）。詞表**現讀**黃金檔 `tests/fixtures/si/A.camel.json` 的 `issues.legend.statuses[].name`，這裡不另抄。
 *    掃描沿 `si.static.test.ts` 的 walk（略過 `tests` 目錄、`*.test.ts(x)`、`*.d.ts`），另明寫排除 `*.fixtures.ts`（夾具內的七個狀態詞不是違規）；
 *  - 純文字：沒有 dangerouslySetInnerHTML、沒有任何 Markdown／HTML 渲染器；
 *  - 寫入面：議題中心唯一的寫入是 PUT／DELETE 優先順序（經 `useSetIssuePriority`、`useClearIssuePriority`）加兩個既有的自我進化對話框；
 *    原始碼沒有對自我進化寫入端點的直接呼叫、沒有 `/si/` 路徑字面、沒有直接 `fetch(`、沒有「si decide」與「obs-close」字樣。
 * 每個掃描器都是純函式（輸入原始碼文字、輸出違規清單），各有負控樣本；掃描範圍有防反空轉斷言。
 */
const ROOT = process.cwd();
const rel = (file: string) => path.relative(ROOT, file).split(path.sep).join("/");
const SKIP_DIRS = new Set(["node_modules", ".next", "tests", "coverage", "test-results", "playwright-report"]);

/** 掃描對象判準：ts／tsx、非測試檔、非 .d.ts、非 `*.fixtures.ts`（夾具檔內容不受單一真相鎖約束）。 */
function isScannedFile(name: string): boolean {
  return /\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) && !/\.d\.ts$/.test(name) && !/\.fixtures\.ts$/.test(name);
}

function walk(dir: string, out: string[] = []): string[] {
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (!SKIP_DIRS.has(name)) walk(full, out);
    } else if (isScannedFile(name)) {
      out.push(full);
    }
  }
  return out;
}

/** 議題中心的非測試原始碼：components/domain/issues/** 與 lib/domain/issues.ts。 */
function issueSources(): Array<{ file: string; text: string }> {
  const files = [...walk(path.join(ROOT, "components/domain/issues")), path.join(ROOT, "lib/domain/issues.ts")];
  return files.map((f) => ({ file: rel(f), text: readFileSync(f, "utf-8") }));
}

/** 黃金檔的七個狀態名（現讀；不在測試裡另抄）。 */
function statusWords(): string[] {
  const golden = JSON.parse(readFileSync(path.join(ROOT, "tests", "fixtures", "si", "A.camel.json"), "utf-8")) as { issues: { legend: { statuses: Array<{ name: string }> } } };
  return golden.issues.legend.statuses.map((s) => s.name);
}

function parse(source: string): ts.SourceFile {
  return ts.createSourceFile("scan.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
}

function walkAst(node: ts.Node, visit: (n: ts.Node) => void): void {
  visit(node);
  ts.forEachChild(node, (child) => walkAst(child, visit));
}

function moduleNames(source: string): string[] {
  const names: string[] = [];
  walkAst(parse(source), (n) => {
    if ((ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) && n.moduleSpecifier && ts.isStringLiteralLike(n.moduleSpecifier)) names.push(n.moduleSpecifier.text);
    if (
      ts.isCallExpression(n) &&
      n.arguments.length > 0 &&
      ts.isStringLiteralLike(n.arguments[0]) &&
      (n.expression.kind === ts.SyntaxKind.ImportKeyword || (ts.isIdentifier(n.expression) && n.expression.text === "require"))
    )
      names.push(n.arguments[0].text);
  });
  return names;
}

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

// ── AT-IC-06-2-3、06-2-E-2：不持有狀態詞清單 ─────────────────────────────────────────

/** 該檔含幾個不同的狀態名；≥4 即違規（回非空清單）。含註解：註解裡寫出一份詞表也算持有。 */
function stateKeyViolations(file: string, source: string, words: ReadonlyArray<string>): string[] {
  const present = words.filter((w) => source.includes(w));
  return present.length >= 4 ? [`${file} 含 ${present.length} 個不同的狀態名：${present.join("、")}`] : [];
}

describe("AT_IC_06_2_3 議題中心前端不持有狀態詞清單（R-IC-73）", () => {
  it("AT_IC_06_2_3 components/domain/issues/** 與 lib/domain/issues.ts 的每個非測試檔都含不到 4 個不同的狀態名（詞表現讀黃金檔）", () => {
    const words = statusWords();
    expect(words, "詞表現讀黃金檔：七個狀態名").toHaveLength(7);
    const sources = issueSources();
    const files = sources.map((s) => s.file);
    // 防反空轉：掃到議題中心的五個元件與純函式層；夾具檔（tests/issues.fixtures.ts）不在掃描範圍
    expect(files).toEqual(
      expect.arrayContaining([
        "components/domain/issues/IssuesView.tsx",
        "components/domain/issues/IssueTable.tsx",
        "components/domain/issues/IssueDetail.tsx",
        "components/domain/issues/IssueLegend.tsx",
        "components/domain/issues/IssuePriorityDialog.tsx",
        "lib/domain/issues.ts",
      ]),
    );
    expect(files.some((f) => f.endsWith(".fixtures.ts") || f.includes("/tests/"))).toBe(false);
    const violations = sources.flatMap(({ file, text }) => stateKeyViolations(file, text, words));
    expect(violations).toEqual([]);
  });

  it("AT_IC_06_2_E_2 掃描器的負控：含 4 個不同狀態名者回非空、含 3 個者回空、同一個詞重複 4 次者回空；排除規則——tests/issues.fixtures.ts 不被掃進，同內容但檔名不是 *.fixtures.ts 的檔被抓到", () => {
    const words = statusWords();
    const four = words.slice(0, 4).join(" ");
    expect(stateKeyViolations("樣本.ts", four, words)).not.toEqual([]);
    expect(stateKeyViolations("樣本.ts", words.join(" "), words)).not.toEqual([]);
    expect(stateKeyViolations("樣本.ts", words.slice(0, 3).join(" "), words)).toEqual([]);
    expect(stateKeyViolations("樣本.ts", `${words[0]} `.repeat(4), words)).toEqual([]);
    expect(stateKeyViolations("樣本.ts", "const x = 1;", words)).toEqual([]);

    // 排除規則：在暫存目錄照 repo 的形狀擺兩個內容相同（含全部七個狀態詞）的檔，跑同一個 walk
    const tmp = mkdtempSync(path.join(tmpdir(), "issues-static-"));
    try {
      const dir = path.join(tmp, "components", "domain", "issues");
      mkdirSync(path.join(dir, "tests"), { recursive: true });
      const body = `export const WORDS = ${JSON.stringify(words)};\n`;
      writeFileSync(path.join(dir, "tests", "issues.fixtures.ts"), body, "utf-8"); // 夾具：位於 tests 目錄且檔名為 *.fixtures.ts
      writeFileSync(path.join(dir, "issues.fixtures.ts"), body, "utf-8"); // 檔名是 *.fixtures.ts：即使放在元件目錄也不掃
      writeFileSync(path.join(dir, "issues.statusWords.sample.ts"), body, "utf-8"); // 同內容、檔名不是 *.fixtures.ts：要被掃進
      writeFileSync(path.join(dir, "issues.statusWords.test.ts"), body, "utf-8"); // 測試檔不掃
      const scanned = walk(dir).map((f) => path.relative(dir, f).split(path.sep).join("/"));
      expect(scanned).toEqual(["issues.statusWords.sample.ts"]);
      const hits = scanned.flatMap((f) => stateKeyViolations(f, readFileSync(path.join(dir, f), "utf-8"), words));
      expect(hits).toHaveLength(1);
      expect(hits[0]).toContain("issues.statusWords.sample.ts");
      // 判準函式本身：*.fixtures.ts、測試檔、.d.ts 不是掃描對象；一般 ts／tsx 是
      for (const name of ["a.fixtures.ts", "a.test.ts", "a.test.tsx", "a.d.ts", "a.css", "a.md"]) expect(isScannedFile(name), name).toBe(false);
      for (const name of ["a.ts", "a.tsx", "issues.statusWords.sample.ts"]) expect(isScannedFile(name), name).toBe(true);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });
});

// ── AT-IC-08-7-2、08-7-E-1：純文字渲染 ───────────────────────────────────────────────

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

describe("AT_IC_08_7 帳本與備註文字一律純文字（R-IC-68）", () => {
  it("AT_IC_08_7_2 components/domain/issues/** 與 lib/domain/issues.ts 沒有 dangerouslySetInnerHTML、沒有 Markdown 渲染器 import", () => {
    const sources = issueSources();
    expect(sources.length, "掃描範圍太小：防反空轉").toBeGreaterThanOrEqual(6);
    for (const { file, text } of sources) expect(rendererViolations(text), file).toEqual([]);
  });

  it("AT_IC_08_7_E_1 掃描器的負控：dangerouslySetInnerHTML 與各種渲染器 import 的違規樣本逐一回非空，良性樣本回空", () => {
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
      'import { useIssues } from "@/lib/api/queries";',
      "const html = '<b>字面文字</b>';",
      'import { markdownLike } from "./markdownLike";',
    ];
    for (const sample of good) expect(rendererViolations(sample), sample).toEqual([]);
  });
});

// ── AT-IC-10-3-1、10-3-E-1：寫入面只有優先順序與兩個既有對話框 ─────────────────────────────

/** 議題中心自己可以 import 的寫入型 query hook（優先順序的 PUT 與 DELETE）；其餘寫入 hook 都住既有的對話框。 */
const ALLOWED_WRITE_HOOKS = ["useClearIssuePriority", "useSetIssuePriority"];
const WRITE_HOOK = /^(use(Create|Update|Delete|Post|Put|Patch|Retry|Approve|Signoff|Execute|Set|Clear)|useSi(Decide|AddObservation|CloseObservation|ValidateObservation))/;
/** 寫入型 endpoint 函式（post／put／patch／delete 開頭）。 */
const WRITE_ENDPOINT = /^(post|put|patch|delete)[A-Z]/;

/** 字串字面值（含樣板字串的各段）；import／export from、動態 import()、require() 的模組位址不是「字面值」的檢查對象（例：既有對話框的 import 路徑含 /si/）。 */
function literalTexts(source: string): string[] {
  const sf = parse(source);
  const specs = new Set<ts.Node>();
  walkAst(sf, (n) => {
    if ((ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) && n.moduleSpecifier) specs.add(n.moduleSpecifier);
    if (ts.isCallExpression(n) && n.arguments.length > 0 && (n.expression.kind === ts.SyntaxKind.ImportKeyword || (ts.isIdentifier(n.expression) && n.expression.text === "require")))
      specs.add(n.arguments[0]);
  });
  const out: string[] = [];
  walkAst(sf, (n) => {
    if (specs.has(n)) return;
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) out.push(n.text);
    else if (ts.isTemplateExpression(n)) {
      out.push(n.head.text);
      for (const span of n.templateSpans) out.push(span.literal.text);
    }
  });
  return out;
}

/** 對自我進化寫入端點的呼叫形跡與直接的網路層寫入。字樣檢查含註解（註解裡寫出呼叫形跡也算）；路徑檢查只看字串字面值。 */
function writeFaceViolations(source: string): string[] {
  const found: string[] = [];
  if (/\bfetch\s*\(/.test(source)) found.push("fetch(");
  if (/si decide/i.test(source)) found.push("si decide");
  if (/obs-close/.test(source)) found.push("obs-close");
  const directCall = /\b(postSi|putIssue|deleteIssue)[A-Za-z]*\s*\(/.exec(source);
  if (directCall) found.push(`寫入端點函式直呼：${directCall[0]}`);
  const siPath = literalTexts(source).find((t) => t.includes("/si/"));
  if (siPath !== undefined) found.push(`/si/ 路徑字面：${siPath}`);
  const method = /method\s*:\s*["'](POST|PUT|PATCH|DELETE)["']/i.exec(source);
  if (method) found.push(`method: ${method[1]}`);
  for (const name of importedNames(source, /(^|\/)endpoints$/)) if (WRITE_ENDPOINT.test(name)) found.push(`import ${name}`);
  for (const name of importedNames(source, /(^|\/)queries$/)) if (WRITE_HOOK.test(name) && !ALLOWED_WRITE_HOOKS.includes(name)) found.push(`import ${name}`);
  return found;
}

describe("AT_IC_10_3 議題中心唯一的寫入是優先順序加兩個既有對話框（R-IC-72）", () => {
  it("AT_IC_10_3_1 components/domain/issues/** 與 lib/domain/issues.ts 沒有對 /si/ 寫入端點的直接呼叫、沒有 si decide 與 obs-close 字樣；寫入 hook 只有優先順序的兩個，決定與關閉由既有對話框承擔", () => {
    const sources = issueSources();
    expect(sources.length, "掃描範圍太小：防反空轉").toBeGreaterThanOrEqual(6);
    for (const { file, text } of sources) expect(writeFaceViolations(text), file).toEqual([]);
    // 防反空轉：掃描器在這棵樹上確實看得到寫入形態——優先順序對話框 import 了兩個寫入 hook，頁面掛了兩個既有對話框
    const hooks = sources.flatMap(({ text }) => importedNames(text, /(^|\/)queries$/)).filter((n) => WRITE_HOOK.test(n));
    expect(hooks.sort()).toEqual([...ALLOWED_WRITE_HOOKS].sort());
    const view = sources.find((s) => s.file === "components/domain/issues/IssuesView.tsx")?.text ?? "";
    expect(view).toContain("SiDecideDialog");
    expect(view).toContain("SiObsCloseDialog");
    // 取點擊當下的提案快照走既有的唯讀函式（GET），不是自己拼網址
    expect(importedNames(view, /(^|\/)endpoints$/)).toEqual(["getSiProposal"]);
  });

  it("AT_IC_10_3_E_1 掃描器的負控：fetch(…decide)、「si decide」、postSiDecide 直呼、obs-close 與其他寫入形態的樣本逐一回非空，良性樣本回空", () => {
    const bad = [
      'await fetch("/api/v1/si/proposals/PROP-SI-004/decide", { method: "POST" });',
      "// 這裡改呼叫 si decide 子命令",
      'import { postSiDecide } from "@/lib/api/endpoints";',
      "await postSiDecide(id, body);",
      'import { postSiObservationClose as close } from "@/lib/api/endpoints";',
      'const verb = "obs-close";',
      'const url = "/api/v1/si/observations";',
      'send({ method: "DELETE" });',
      'import { useSiDecide } from "@/lib/api/queries";',
      'import { useSiCloseObservation, useSetIssuePriority } from "@/lib/api/queries";',
      'import { useUpdateProject } from "@/lib/api/queries";',
      'import { putIssuePriority } from "@/lib/api/endpoints";',
    ];
    for (const sample of bad) expect(writeFaceViolations(sample), sample).not.toEqual([]);
    const good = [
      'import { getSiProposal } from "@/lib/api/endpoints";',
      'import { SiDecideDialog } from "@/components/domain/si/SiDecideDialog";',
      'const lazy = await import("@/components/domain/si/SiObsCloseDialog");',
      'import { useSetIssuePriority, useClearIssuePriority } from "@/lib/api/queries";',
      'import { useIssues, useIssue } from "@/lib/api/queries";',
      "const text = '決定';",
      "// Bridge 的 GET 路徑由 console-api 轉遞",
      'send({ method: "GET" });',
      "const prefetch = 1;",
    ];
    for (const sample of good) expect(writeFaceViolations(sample), sample).toEqual([]);
  });
});
