import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

/**
 * 備份頁前端的靜態守衛（TCS-SysAdminBackup-20261027 載具 FS；AT-BK-02-3-2、04-1-E-2、04-3-3；R-BK-06、R-BK-15、R-BK-18）：
 *  - AT-BK-02-3-2：格式化沿用既有函式——新檔沒有定義 `formatBytes`、`formatDuration`、`formatDateTime`、`formatClock`（函式宣告、變數宣告、本地的 export 清單都掃），
 *    且用到它們的檔都是從 `@/lib/format` 或 `@/lib/domain/metrics` 匯入；
 *  - AT-BK-04-1-E-2：純文字——沒有 dangerouslySetInnerHTML、沒有任何 Markdown 渲染器的 import（輸出尾段與 reason 文字只以文字節點渲染）；
 *  - AT-BK-04-3-3：前端不判逾期——沒有 cron 解析函式庫的匯入、沒有識別字含 grace（不分大小寫）、沒有以 lastDueAt 做算術或比較、沒有寫入 overdue 的指派。
 * 掃描範圍＝`components/domain/sysadmin/**` 與 `lib/domain/sysadminBackup.ts` 的非測試原始碼（略過 `tests` 目錄、`*.test.ts(x)`、`*.fixtures.ts`、`*.d.ts`）。
 * 每個掃描器都是純函式（輸入原始碼文字、輸出違規清單），各有負控樣本；掃描範圍有防反空轉斷言。
 * 判定指令：npx vitest run components/domain/sysadmin/sysadmin.static.test.ts -t "<AT 底線形>"
 */
const ROOT = process.cwd();
const rel = (file: string) => path.relative(ROOT, file).split(path.sep).join("/");
const SKIP_DIRS = new Set(["node_modules", ".next", "tests", "coverage", "test-results", "playwright-report"]);

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

/** 備份頁的非測試原始碼。 */
function sources(): Array<{ file: string; text: string }> {
  const files = [...walk(path.join(ROOT, "components/domain/sysadmin")), path.join(ROOT, "lib/domain/sysadminBackup.ts")];
  return files.map((f) => ({ file: rel(f), text: readFileSync(f, "utf-8") }));
}

function parse(source: string): ts.SourceFile {
  return ts.createSourceFile("scan.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
}

function walkAst(node: ts.Node, visit: (n: ts.Node) => void): void {
  visit(node);
  ts.forEachChild(node, (child) => walkAst(child, visit));
}

/** 去掉註解與字串之外的原始碼文字（以 AST 的 token 重組太貴；這裡只去註解，字串內容保留）。 */
function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/.*$/gm, "$1");
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

// ── AT-BK-02-3-2：格式化沿用既有函式 ───────────────────────────────────────────────────

const FORMAT_NAMES = ["formatBytes", "formatDuration", "formatDateTime", "formatClock"] as const;
const FORMAT_MODULES = new Set(["@/lib/format", "@/lib/domain/metrics"]);

/** 定義了同名函式或常數（函式宣告、變數宣告、沒有來源模組的 export 清單）；回傳違規描述。 */
function formatRedefinitions(source: string): string[] {
  const found: string[] = [];
  const names = new Set<string>(FORMAT_NAMES);
  walkAst(parse(source), (n) => {
    if (ts.isFunctionDeclaration(n) && n.name && names.has(n.name.text)) found.push(`function ${n.name.text}`);
    if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && names.has(n.name.text)) found.push(`const ${n.name.text}`);
    if (ts.isExportDeclaration(n) && !n.moduleSpecifier && n.exportClause && ts.isNamedExports(n.exportClause)) {
      for (const el of n.exportClause.elements) if (names.has(el.name.text)) found.push(`export { ${el.name.text} }`);
    }
  });
  return found;
}

/** 用到這四個名字（呼叫或引用）卻不是自 `@/lib/format`、`@/lib/domain/metrics` 匯入的；回傳名稱清單。 */
function formatNotImported(source: string): string[] {
  const used = new Set<string>();
  const imported = new Set<string>();
  const sf = parse(source);
  walkAst(sf, (n) => {
    if (ts.isImportDeclaration(n) && ts.isStringLiteral(n.moduleSpecifier)) {
      const bindings = n.importClause?.namedBindings;
      if (bindings && ts.isNamedImports(bindings)) for (const el of bindings.elements) if (FORMAT_MODULES.has(n.moduleSpecifier.text)) imported.add((el.propertyName ?? el.name).text);
      return;
    }
    if (
      ts.isIdentifier(n) &&
      (FORMAT_NAMES as readonly string[]).includes(n.text) &&
      !(n.parent && (ts.isImportSpecifier(n.parent) || ts.isFunctionDeclaration(n.parent) || ts.isVariableDeclaration(n.parent)))
    )
      used.add(n.text);
  });
  return [...used].filter((name) => !imported.has(name));
}

describe("AT_BK_02_3_2 格式化沿用既有函式（R-BK-06）", () => {
  it("AT_BK_02_3_2 備份頁的每個非測試檔都沒有定義 formatBytes、formatDuration、formatDateTime、formatClock；用到它們的檔都自 @/lib/format 或 @/lib/domain/metrics 匯入", () => {
    const files = sources();
    expect(
      files.map((f) => f.file),
      "防反空轉：必掃的檔",
    ).toEqual(expect.arrayContaining(["components/domain/sysadmin/BackupList.tsx", "components/domain/sysadmin/BackupView.tsx", "lib/domain/sysadminBackup.ts"]));
    const users = files.filter((f) => FORMAT_NAMES.some((name) => f.text.includes(name))).map((f) => f.file);
    expect(users.length, "防反空轉：至少有檔用到格式化函式").toBeGreaterThan(0);
    for (const { file, text } of files) {
      expect(formatRedefinitions(text), `${file} 不得重定義格式化函式`).toEqual([]);
      expect(formatNotImported(text), `${file} 用到的格式化函式必須自既有模組匯入`).toEqual([]);
    }
    // 四個函式在既有模組裡確實存在（沒有被改名而讓上面的檢查空過）
    expect(readFileSync(path.join(ROOT, "lib/format.ts"), "utf-8")).toMatch(/export function formatBytes\b/);
    expect(readFileSync(path.join(ROOT, "lib/format.ts"), "utf-8")).toMatch(/export function formatDateTime\b/);
    expect(readFileSync(path.join(ROOT, "lib/format.ts"), "utf-8")).toMatch(/export function formatClock\b/);
    expect(readFileSync(path.join(ROOT, "lib/domain/metrics.ts"), "utf-8")).toMatch(/export function formatDuration\b/);
  });

  it("AT_BK_02_3_2 掃描器自帶負控：含 function formatBytes、const formatDateTime、export { formatClock } 的合成原始碼各回非空；自別處匯入或沒有重定義的回空", () => {
    expect(formatRedefinitions("function formatBytes(n: number) { return String(n); }")).toEqual(["function formatBytes"]);
    expect(formatRedefinitions("export const formatDateTime = (v: string) => v;")).toEqual(["const formatDateTime"]);
    expect(formatRedefinitions("const formatDuration = 1;")).toEqual(["const formatDuration"]);
    expect(formatRedefinitions("const formatClock = () => '';\nexport { formatClock };")).toEqual(["const formatClock", "export { formatClock }"]);
    expect(formatRedefinitions('import { formatBytes } from "@/lib/format";\nexport const sizeText = (n: number) => formatBytes(n);')).toEqual([]);
    expect(formatRedefinitions("export { formatBytes } from '@/lib/format';")).toEqual([]);
    // 用到卻不是自既有模組匯入
    expect(formatNotImported('import { formatBytes } from "./elsewhere";\nformatBytes(1);')).toEqual(["formatBytes"]);
    expect(formatNotImported("formatClock(new Date().toISOString());")).toEqual(["formatClock"]);
    expect(formatNotImported('import { formatBytes } from "@/lib/format";\nimport { formatDuration } from "@/lib/domain/metrics";\nformatBytes(1);\nformatDuration(2);')).toEqual([]);
  });
});

// ── AT-BK-04-1-E-2：純文字（沒有 HTML 注入、沒有 Markdown 渲染器）─────────────────────────

const MARKDOWN_MODULES = /^(react-markdown|marked|markdown-it|@uiw\/react-md-editor|remark|remark-.+|rehype|rehype-.+)$|^@\/components\/markdown(\/|$)/;

function plainTextViolations(source: string): string[] {
  const found: string[] = [];
  if (/dangerouslySetInnerHTML/.test(stripComments(source))) found.push("dangerouslySetInnerHTML");
  for (const name of moduleNames(source)) if (MARKDOWN_MODULES.test(name)) found.push(`import ${name}`);
  return found;
}

describe("AT_BK_04_1_E_2 備份頁只以文字節點渲染（R-BK-15）", () => {
  it("AT_BK_04_1_E_2 備份頁的每個非測試檔都沒有 dangerouslySetInnerHTML，也沒有 react-markdown、marked、remark 之類 Markdown 渲染器的 import", () => {
    const files = sources();
    expect(files.length, "防反空轉：掃描檔數（七個元件、tone.ts 與純函式模組）").toBeGreaterThanOrEqual(9);
    for (const { file, text } of files) expect(plainTextViolations(text), file).toEqual([]);
  });

  it("AT_BK_04_1_E_2 掃描器自帶負控：含 dangerouslySetInnerHTML、import react-markdown／marked／remark-gfm／@/components/markdown 的合成原始碼各回非空；純文字渲染回空", () => {
    expect(plainTextViolations("const el = <div dangerouslySetInnerHTML={{ __html: tail }} />;")).toEqual(["dangerouslySetInnerHTML"]);
    expect(plainTextViolations('import ReactMarkdown from "react-markdown";')).toEqual(["import react-markdown"]);
    expect(plainTextViolations('import { marked } from "marked";')).toEqual(["import marked"]);
    expect(plainTextViolations('import remarkGfm from "remark-gfm";')).toEqual(["import remark-gfm"]);
    expect(plainTextViolations('import { MarkdownView } from "@/components/markdown/MarkdownView";')).toEqual(["import @/components/markdown/MarkdownView"]);
    expect(plainTextViolations('const lazy = await import("react-markdown");')).toEqual(["import react-markdown"]);
    expect(plainTextViolations("const el = <pre>{tail}</pre>; // 沒有 dangerouslySetInnerHTML")).toEqual([]);
  });
});

// ── AT-BK-04-3-3：前端不判逾期 ───────────────────────────────────────────────────────────

const CRON_LIBRARIES = new Set(["cron-parser", "croner", "cronstrue", "node-cron"]);
const ARITHMETIC_OR_COMPARISON = new Set<ts.SyntaxKind>([
  ts.SyntaxKind.PlusToken,
  ts.SyntaxKind.MinusToken,
  ts.SyntaxKind.AsteriskToken,
  ts.SyntaxKind.SlashToken,
  ts.SyntaxKind.PercentToken,
  ts.SyntaxKind.LessThanToken,
  ts.SyntaxKind.GreaterThanToken,
  ts.SyntaxKind.LessThanEqualsToken,
  ts.SyntaxKind.GreaterThanEqualsToken,
  ts.SyntaxKind.EqualsEqualsToken,
  ts.SyntaxKind.EqualsEqualsEqualsToken,
  ts.SyntaxKind.ExclamationEqualsToken,
  ts.SyntaxKind.ExclamationEqualsEqualsToken,
]);

function mentions(node: ts.Node, name: string): boolean {
  let hit = false;
  walkAst(node, (n) => {
    if (ts.isIdentifier(n) && n.text === name) hit = true;
  });
  return hit;
}

function overdueViolations(source: string): string[] {
  const found: string[] = [];
  for (const name of moduleNames(source)) if (CRON_LIBRARIES.has(name)) found.push(`import ${name}`);
  if (/grace/i.test(stripComments(source))) found.push("識別字或字串含 grace");
  walkAst(parse(source), (n) => {
    if (ts.isIdentifier(n) && /grace/i.test(n.text)) found.push(`識別字 ${n.text}`);
    if (ts.isBinaryExpression(n)) {
      const op = n.operatorToken.kind;
      if (ARITHMETIC_OR_COMPARISON.has(op) && (mentions(n.left, "lastDueAt") || mentions(n.right, "lastDueAt"))) found.push("對 lastDueAt 做算術或比較");
      if (op === ts.SyntaxKind.EqualsToken) {
        const left = n.left;
        const target = ts.isIdentifier(left) ? left.text : ts.isPropertyAccessExpression(left) ? left.name.text : "";
        if (target === "overdue") found.push("寫入 overdue 的指派");
      }
    }
    if (ts.isPropertyAssignment(n) && ts.isIdentifier(n.name) && n.name.text === "overdue") found.push("物件字面值寫入 overdue");
    if (ts.isShorthandPropertyAssignment(n) && n.name.text === "overdue") found.push("物件字面值寫入 overdue");
  });
  return [...new Set(found)];
}

describe("AT_BK_04_3_3 前端不判逾期（R-BK-18）", () => {
  it("AT_BK_04_3_3 備份頁的每個非測試檔都沒有 cron-parser、croner、cronstrue、node-cron 的匯入，沒有識別字含 grace，沒有以 lastDueAt 做算術或比較，沒有寫入 overdue 的指派（overdue 只作為 card.overdue 讀取並顯示）", () => {
    const files = sources();
    expect(files.length, "防反空轉：掃描檔數（七個元件、tone.ts 與純函式模組）").toBeGreaterThanOrEqual(9);
    // 前端確實讀取了 card.overdue（沒有被改名而讓這個鎖空過）
    expect(files.some((f) => f.text.includes("card.overdue"))).toBe(true);
    for (const { file, text } of files) expect(overdueViolations(text), file).toEqual([]);
    // package.json 也沒有 cron 函式庫的相依（前端沒有任何管道取得 cron 計算）
    const pkg = JSON.parse(readFileSync(path.join(ROOT, "package.json"), "utf-8")) as { dependencies?: Record<string, string>; devDependencies?: Record<string, string> };
    for (const lib of CRON_LIBRARIES) expect({ ...pkg.dependencies, ...pkg.devDependencies }, lib).not.toHaveProperty(lib);
  });

  it("AT_BK_04_3_3 掃描器自帶負控：含 cron 函式庫匯入、graceMinutes、lastDueAt 的加減與比較、overdue 的指派（含物件字面值）的合成原始碼各回非空；只讀取 card.overdue 並顯示的回空", () => {
    expect(overdueViolations('import { parseExpression } from "cron-parser";')).toEqual(["import cron-parser"]);
    expect(overdueViolations('import Cronstrue from "cronstrue";')).toEqual(["import cronstrue"]);
    expect(overdueViolations("const graceMinutes = 30;")).toEqual(expect.arrayContaining(["識別字 graceMinutes", "識別字或字串含 grace"]));
    expect(overdueViolations("const late = Date.parse(card.lastDueAt) + 30 * 60_000 < Date.now();")).toEqual(["對 lastDueAt 做算術或比較"]);
    expect(overdueViolations("const is = card.lastDueAt > other;")).toEqual(["對 lastDueAt 做算術或比較"]);
    expect(overdueViolations("card.overdue = true;")).toEqual(["寫入 overdue 的指派"]);
    expect(overdueViolations("overdue = Date.now() > due;")).toEqual(["寫入 overdue 的指派"]);
    expect(overdueViolations("const c = { overdue: true };")).toEqual(["物件字面值寫入 overdue"]);
    expect(overdueViolations("const overdue = card.x; const c = { overdue };")).toEqual(["物件字面值寫入 overdue"]);
    // 合規：讀取 card.overdue、顯示 lastDueAt、註解裡寫 lastDueAt 的算術不算
    expect(overdueViolations("const tag = card.overdue ? '逾期' : null;\nconst when = formatDateTime(card.lastDueAt);\n// lastDueAt + 寬限 的算術在 console-api，不在這裡")).toEqual([]);
  });
});
