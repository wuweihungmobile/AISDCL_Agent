import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

import { HELP_COMMON } from "@/lib/help/common";
import { codePointLength } from "@/lib/help/lint";
import { HELP_PAGES, PENDING_HELP_PAGES } from "@/lib/help/registry";
import type { HelpId, PageHelp } from "@/lib/help/types";

/**
 * 說明的靜態鎖（TCS-PageHelp-20261027 D-PH-12、R-PH-18、R-PH-19；載具 HS，輪 1a 起建出處鎖與表單抽取器、輪 1b 補元件靜態鎖）：
 *  - AT-PH-05-5-1、5-2、5-3、5-E-1：出處鎖——每頁（與全站共通）的欄位名（≥ 3 個 code point）須出現在該頁 `sourceFiles` 展開後非測試檔的
 *    字串字面值、樣板字串片段或 JSX 文字（不含註解與 import 位址）；改名或刪欄位而說明沒改＝紅；
 *  - AT-PH-05-7-1、7-2：表單欄位清單鎖——`entity/EntityForms.tsx` 的 ProjectForm、GoalForm（含 DependsOnField）、TaskForm 內
 *    `<Field>`、`<MarkdownField>` 的 label 字串屬性，須都在對應說明項（project-form、goal-form、task-form）的欄位名集合內。
 *    表單頁於輪 2 才寫：輪 1 它們在 PENDING_HELP_PAGES，這支先斷言「它們在 pending 內、抽取結果非空」，頁一寫完就自動轉為真正的涵蓋鎖（所以輪 2 不必改測試邏輯）。
 * 輪 1b 補的元件靜態鎖（R-PH-24、R-PH-26、R-PH-27、R-PH-29、R-PH-31、R-PH-11、R-PH-12）：
 *  - AT-PH-01-1-E-2：`<PageHelpButton />` 全 repo 恰一個使用處、在 TopRegion 的 showTools 為真的分支內（JSX 標籤名比對，不看 import 形態——TopRegion 以 next/dynamic 載入）；
 *  - AT-PH-02-3-2、02-3-E-1：lib/help/** 與 components/domain/help/** 非測試檔沒有 dangerouslySetInnerHTML 與 Markdown 渲染器 import（含負控）；
 *  - AT-PH-04-4-3、04-4-E-1：議題中心不持有狀態詞清單——只掃 lib/help/issues.ts 與 components/domain/help/**，每檔含不到 4 個不同的議題狀態名（詞表現讀黃金檔）；
 *  - AT-PH-04-5-E-3：IssuesLegendGroups 的取數面（getIssues、SI_QUERY_OPTIONS、query key 不掛 issues 家族、不 import useIssues）；
 *  - AT-PH-07-2-1、07-2-E-1：對話框建於 DialogContent，不自刻、不傳 onCloseAutoFocus、不覆寫尺寸類別；
 *  - AT-PH-07-5-1、07-5-E-1：說明鈕的圖示與顏色（BookOpen、白底主色字；不得半透明底白字、不得 outline-none）。
 * 掃描器全部住本檔（不進生產碼）、以既有 devDependency `typescript` 的 AST 實作，沿 issues.static.test.ts 的 walk／parse／walkAst／literalTexts 並另加 JSX 文字（B-13）；
 * 每個掃描器是純函式並各有負控樣本，掃描範圍有防反空轉斷言。
 * 判定指令：npx vitest run components/domain/help/help.static.test.ts -t "<AT 底線形>"
 */

const ROOT = process.cwd();
const rel = (file: string) => path.relative(ROOT, file).split(path.sep).join("/");
const SKIP_DIRS = new Set(["node_modules", ".next", "tests", "coverage", "test-results", "playwright-report"]);

/** 每頁 sourceFiles 展開後的檔數上限（PRD AC-PH-05-5；現況單一目錄最大 12 個）。 */
const MAX_EXPANDED_FILES = 30;

/** 掃描對象：ts／tsx、非測試檔、非 .d.ts、非 `*.fixtures.ts`。 */
function isScannedFile(name: string): boolean {
  return /\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) && !/\.d\.ts$/.test(name) && !/\.fixtures\.ts$/.test(name);
}

function walkDir(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir).sort()) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (!SKIP_DIRS.has(name)) walkDir(full, out);
    } else if (isScannedFile(name)) out.push(full);
  }
  return out;
}

function parse(source: string): ts.SourceFile {
  return ts.createSourceFile("scan.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
}

function walkAst(node: ts.Node, visit: (n: ts.Node) => void): void {
  visit(node);
  ts.forEachChild(node, (child) => walkAst(child, visit));
}

/** import／export from、動態 import()、require() 的模組位址節點（它們是位址，不是「文字」）。 */
function moduleSpecifierNodes(sf: ts.SourceFile): Set<ts.Node> {
  const specs = new Set<ts.Node>();
  walkAst(sf, (n) => {
    if ((ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) && n.moduleSpecifier) specs.add(n.moduleSpecifier);
    if (ts.isCallExpression(n) && n.arguments.length > 0 && (n.expression.kind === ts.SyntaxKind.ImportKeyword || (ts.isIdentifier(n.expression) && n.expression.text === "require")))
      specs.add(n.arguments[0]);
  });
  return specs;
}

/**
 * 出處鎖的文字抽取器：字串字面值（含 JSX 屬性值）、樣板字串片段與 JSX 文字；**不含**註解與 import／export from 位址。
 * 名稱被拆在兩個字面值之間就找不到（刻意：不做拼接，避免鎖被「碰巧湊出來」的字串架空）。
 */
function collectTexts(source: string): string[] {
  const sf = parse(source);
  const specs = moduleSpecifierNodes(sf);
  const out: string[] = [];
  walkAst(sf, (n) => {
    if (specs.has(n)) return;
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) out.push(n.text);
    else if (ts.isTemplateExpression(n)) {
      out.push(n.head.text);
      for (const span of n.templateSpans) out.push(span.literal.text);
    } else if (ts.isJsxText(n)) out.push(n.text);
  });
  return out;
}

/**
 * 展開 `sourceFiles`：條目是相對 `root` 的檔案或 `dir/**`。回傳展開後的檔（絕對路徑，去重排序）與全部違規：
 * 頂層萬用（單段目錄的 `components/**` 這類）一律拒、含 `..` 或絕對路徑拒、不存在的檔與目錄拒、測試檔與型別宣告與夾具不算來源、展開後超過 30 個檔拒。
 * `dir/**` 展開時略過測試檔、`*.d.ts`、`*.fixtures.ts` 與 `tests/` 子目錄。
 */
function expandSourceFiles(entries: readonly string[], root: string): { files: string[]; problems: string[] } {
  const files = new Set<string>();
  const problems: string[] = [];
  for (const entry of entries) {
    if (entry.split("/").includes("..") || path.isAbsolute(entry) || /^[A-Za-z]:/.test(entry)) {
      problems.push(`路徑不可含 .. 或為絕對路徑：${entry}`);
      continue;
    }
    if (entry.endsWith("/**")) {
      const dirRel = entry.slice(0, -"/**".length);
      if (dirRel === "" || !dirRel.includes("/")) {
        problems.push(`頂層萬用路徑被拒（請寫到具體的子目錄）：${entry}`);
        continue;
      }
      const dir = path.join(root, dirRel);
      if (!existsSync(dir) || !statSync(dir).isDirectory()) {
        problems.push(`目錄不存在：${entry}`);
        continue;
      }
      for (const file of walkDir(dir)) files.add(file);
    } else if (entry.includes("*")) {
      problems.push(`只支援檔案路徑或 dir/**：${entry}`);
    } else {
      const file = path.join(root, entry);
      if (!existsSync(file) || !statSync(file).isFile()) problems.push(`檔案不存在：${entry}`);
      else if (!isScannedFile(path.basename(file))) problems.push(`測試檔、型別宣告與夾具不算來源：${entry}`);
      else files.add(file);
    }
  }
  if (files.size > MAX_EXPANDED_FILES) problems.push(`展開後有 ${files.size} 個檔，超過上限 ${MAX_EXPANDED_FILES}`);
  if (files.size === 0 && problems.length === 0) problems.push("展開後沒有任何檔");
  return { files: [...files].sort(), problems };
}

/** 出處鎖：每個欄位名（≥ 3 個 code point；更短者免掃）須出現在 texts 內某一段文字；同頁欄位名須互異。 */
function sourceLockProblems(page: { fields: ReadonlyArray<{ name: string }> }, texts: readonly string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const field of page.fields) {
    if (seen.has(field.name)) out.push(`同頁欄位名重複：『${field.name}』`);
    seen.add(field.name);
    if (codePointLength(field.name) < 3) continue;
    if (!texts.some((text) => text.includes(field.name))) out.push(`欄位『${field.name}』在 sourceFiles 找不到`);
  }
  return out;
}

/** 這一頁（或全站共通）的出處鎖：展開 sourceFiles → 抽文字 → 逐欄位名比對；順便回傳展開檔數與「真的被掃描且找到」的欄位名數（防反空轉用）。 */
function pageSourceLock(page: { fields: ReadonlyArray<{ name: string }>; sourceFiles: readonly string[] }): { problems: string[]; fileCount: number; verified: number } {
  const { files, problems } = expandSourceFiles(page.sourceFiles, ROOT);
  const texts = files.flatMap((file) => collectTexts(readFileSync(file, "utf-8")));
  const lockProblems = sourceLockProblems(page, texts);
  const verified = page.fields.filter((field) => codePointLength(field.name) >= 3 && texts.some((text) => text.includes(field.name))).length;
  return { problems: [...problems, ...lockProblems], fileCount: files.length, verified };
}

// ── AC-PH-05-5：出處鎖 ───────────────────────────────────────────────────────────────

describe("AT_PH_05_5 出處鎖（R-PH-18）", () => {
  it("AT_PH_05_5_1 每個已寫頁與全站共通：欄位名（≥ 3 個字）都在 sourceFiles 展開後的字串字面值、樣板片段或 JSX 文字內；同頁欄位名互異；展開檔數 ≤ 30 且都存在；全站共通的 sourceFiles 含 layout 目錄與連線狀態 hook", () => {
    const pages = Object.values(HELP_PAGES).filter((page): page is PageHelp => page !== undefined);
    expect(pages.length, "防反空轉：已寫頁數（輪 1a 起至少三頁）").toBeGreaterThanOrEqual(3);
    for (const page of pages) {
      const result = pageSourceLock(page);
      expect(result.problems, `${page.id} 的出處鎖`).toEqual([]);
      expect(result.fileCount, `${page.id} 展開後的檔數`).toBeGreaterThanOrEqual(1);
      expect(result.fileCount, `${page.id} 展開後的檔數`).toBeLessThanOrEqual(MAX_EXPANDED_FILES);
      expect(result.verified, `防反空轉：${page.id} 至少有一個欄位名真的被掃描並找到`).toBeGreaterThanOrEqual(1);
    }
    const common = pageSourceLock(HELP_COMMON);
    expect(common.problems, "全站共通的出處鎖").toEqual([]);
    expect(common.verified, "防反空轉：全站共通至少有欄位名被掃描並找到").toBeGreaterThanOrEqual(1);
    expect(HELP_COMMON.sourceFiles).toEqual(expect.arrayContaining(["components/layout/**", "hooks/useServiceStatus.ts"]));
  });

  it("AT_PH_05_5_2 expandSourceFiles：頂層萬用（components、lib、app、hooks 各一段的 /**）、含 ..、不存在的檔各被拒；components/layout/** 通過；components/domain/** 展開超過 30 個而被拒；測試檔、型別宣告、夾具與 tests 目錄不被展開進去", () => {
    for (const entry of ["components/**", "lib/**", "app/**", "hooks/**"]) expect(expandSourceFiles([entry], ROOT).problems.join("\n"), entry).toContain("頂層萬用");
    expect(expandSourceFiles(["lib/../lib/help/types.ts"], ROOT).problems.join("\n")).toContain("..");
    expect(expandSourceFiles(["../x.ts"], ROOT).problems).not.toEqual([]);
    expect(expandSourceFiles(["components/nope/Missing.tsx"], ROOT).problems.join("\n")).toContain("不存在");
    expect(expandSourceFiles(["components/nope/**"], ROOT).problems.join("\n")).toContain("不存在");
    expect(expandSourceFiles(["components/layout/*.tsx"], ROOT).problems.join("\n")).toContain("dir/**");
    expect(existsSync(path.join(ROOT, "components/layout/layout.test.tsx")), "對照：這個測試檔真的存在").toBe(true);
    expect(expandSourceFiles(["components/layout/layout.test.tsx"], ROOT).problems.join("\n")).toContain("測試檔");

    const layout = expandSourceFiles(["components/layout/**"], ROOT);
    expect(layout.problems).toEqual([]);
    expect(layout.files.map(rel)).toEqual(expect.arrayContaining(["components/layout/TopRegion.tsx", "components/layout/BottomRegion.tsx", "components/layout/ToolsRegion.tsx"]));

    const wide = expandSourceFiles(["components/domain/**"], ROOT);
    expect(wide.files.length, "components/domain/** 在真樹展開的檔數遠大於上限").toBeGreaterThan(MAX_EXPANDED_FILES);
    expect(wide.problems.join("\n")).toContain("超過上限");

    const issues = expandSourceFiles(["components/domain/issues/**"], ROOT);
    expect(issues.problems).toEqual([]);
    const names = issues.files.map(rel);
    expect(names).toContain("components/domain/issues/IssuesView.tsx");
    for (const name of names) {
      expect(/\.test\.tsx?$/.test(name) || /\.d\.ts$/.test(name) || /\.fixtures\.ts$/.test(name) || name.includes("/tests/"), `${name} 不該被展開進來`).toBe(false);
    }
    // 對照：目錄內確實有測試檔與夾具，只是沒被展開
    expect(readdirSync(path.join(ROOT, "components/domain/issues")).some((n) => /\.test\.tsx?$/.test(n))).toBe(true);
    expect(existsSync(path.join(ROOT, "components/domain/issues/tests/issues.fixtures.ts"))).toBe(true);
  });

  it("AT_PH_05_5_2 expandSourceFiles 的合成目錄樹：只展開一般 ts／tsx（含子目錄），不展開測試檔、.d.ts、.fixtures.ts 與 tests 目錄；30 個檔通過、31 個檔被拒", () => {
    const tmp = mkdtempSync(path.join(tmpdir(), "help-expand-"));
    try {
      const put = (name: string) => {
        mkdirSync(path.dirname(path.join(tmp, name)), { recursive: true });
        writeFileSync(path.join(tmp, name), "export const x = 1;\n", "utf-8");
      };
      for (const name of ["x/y/a.ts", "x/y/a.test.ts", "x/y/b.d.ts", "x/y/c.fixtures.ts", "x/y/tests/d.ts", "x/y/sub/e.tsx", "x/y/sub/e.test.tsx", "x/y/notes.md"]) put(name);
      const result = expandSourceFiles(["x/y/**"], tmp);
      expect(result.problems).toEqual([]);
      expect(result.files.map((f) => path.relative(tmp, f).split(path.sep).join("/"))).toEqual(["x/y/a.ts", "x/y/sub/e.tsx"]);

      for (let i = 0; i < 30; i += 1) put(`many/m/f${i}.ts`);
      expect(expandSourceFiles(["many/m/**"], tmp).problems, "恰 30 個檔通過").toEqual([]);
      put("many/m/f30.ts");
      expect(expandSourceFiles(["many/m/**"], tmp).problems.join("\n"), "31 個檔被拒").toContain("超過上限");
      // 重複條目去重：同一個檔列兩次只算一個
      expect(expandSourceFiles(["x/y/a.ts", "x/y/**"], tmp).files).toHaveLength(2);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });

  it("AT_PH_05_5_3 collectTexts 負控：名稱只在註解、在 import 位址、被拆在兩個字面值之間都找不到；在字串字面值（含 JSX 屬性值）、樣板字串片段、JSX 文字都找得到", () => {
    const found = (source: string, name: string) => collectTexts(source).some((text) => text.includes(name));
    expect(found("// 欄位名稱\nconst a = 1;", "欄位名稱")).toBe(false);
    expect(found("/* 欄位名稱 */\nconst a = 1;", "欄位名稱")).toBe(false);
    expect(found('import { x } from "@/lib/欄位名稱";', "欄位名稱")).toBe(false);
    expect(found('const a = "欄位" + "名稱";', "欄位名稱")).toBe(false);
    expect(found('const a = "這是欄位名稱";', "欄位名稱")).toBe(true);
    expect(found('const el = <Input aria-label="欄位名稱" />;', "欄位名稱")).toBe(true);
    expect(found("const a = `前綴 ${n} 欄位名稱`;", "欄位名稱")).toBe(true);
    expect(found("const a = `欄位名稱 ${n} 後綴`;", "欄位名稱")).toBe(true);
    expect(found("const a = `整段欄位名稱`;", "欄位名稱")).toBe(true);
    expect(found("const el = <p>欄位名稱</p>;", "欄位名稱")).toBe(true);
    expect(found("const el = <p>\n  欄位名稱\n</p>;", "欄位名稱")).toBe(true);
  });

  it("AT_PH_05_5_E_1 sourceLockProblems 負控：把某欄位名所在字面值改名後回「欄位『X』在 sourceFiles 找不到」；同頁重複欄位名回非空；2 個字的名稱免掃；剛好 3 個字的名稱要掃", () => {
    const page = { fields: [{ name: "專案名稱" }, { name: "執行路徑" }] };
    const original = collectTexts('const a = "專案名稱"; const b = "執行路徑";');
    expect(sourceLockProblems(page, original)).toEqual([]);
    const renamed = collectTexts('const a = "專案名稱（新）"; const b = "路徑";');
    expect(sourceLockProblems(page, renamed)).toEqual(["欄位『執行路徑』在 sourceFiles 找不到"]);
    // 把第一個名稱的字面值改名（拆掉）
    const broken = collectTexts('const a = "專案名"; const b = "執行路徑";');
    expect(sourceLockProblems(page, broken)).toEqual(["欄位『專案名稱』在 sourceFiles 找不到"]);

    expect(sourceLockProblems({ fields: [{ name: "專案" }, { name: "專案" }] }, ["任何文字"]).join("\n"), "重複欄位名").toContain("重複");
    expect(sourceLockProblems({ fields: [{ name: "專案" }] }, ["完全沒有這個詞"]), "2 個字免掃").toEqual([]);
    expect(sourceLockProblems({ fields: [{ name: "專案名" }] }, ["完全沒有這個詞"]), "3 個字要掃").toEqual(["欄位『專案名』在 sourceFiles 找不到"]);
    // 以 code point 計：3 個代理對字元也算 3 個
    const astral = String.fromCodePoint(0x20bb7).repeat(3);
    expect(sourceLockProblems({ fields: [{ name: astral }] }, ["沒有"]), "3 個代理對字元要掃").toHaveLength(1);
  });
});

// ── AC-PH-05-7：表單欄位清單鎖 ───────────────────────────────────────────────────────

/** 一個函式（函式宣告，或變數指派的箭頭函式／函式運算式）的本體節點。 */
function functionBodyOf(n: ts.Node, names: readonly string[]): ts.Node | undefined {
  if (ts.isFunctionDeclaration(n) && n.name && names.includes(n.name.text)) return n.body;
  if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && names.includes(n.name.text) && n.initializer && (ts.isArrowFunction(n.initializer) || ts.isFunctionExpression(n.initializer)))
    return n.initializer.body;
  return undefined;
}

/**
 * 表單欄位標籤抽取器：指定函式（`fnNames`）的本體內，`<Field>`、`<MarkdownField>` 元素的 `label` **字串屬性**（`label={x}` 這種運算式不抽）。
 * 只抽指定函式體內的元素（其他函式內的 `<Field>` 不算）；GoalForm 內呼叫的 DependsOnField，其標籤由呼叫端把它的函式名一併傳進 `fnNames` 計入。
 */
function formLabels(source: string, fnNames: readonly string[]): string[] {
  const sf = parse(source);
  const labels: string[] = [];
  walkAst(sf, (n) => {
    const body = functionBodyOf(n, fnNames);
    if (!body) return;
    walkAst(body, (m) => {
      if ((ts.isJsxOpeningElement(m) || ts.isJsxSelfClosingElement(m)) && ["Field", "MarkdownField"].includes(m.tagName.getText(sf))) {
        for (const attr of m.attributes.properties) {
          if (ts.isJsxAttribute(attr) && attr.name.getText(sf) === "label" && attr.initializer !== undefined && ts.isStringLiteral(attr.initializer)) labels.push(attr.initializer.text);
        }
      }
    });
  });
  return labels;
}

/** 三個表單頁對應的函式（GoalForm 含 DependsOnField）。 */
const FORM_FUNCTIONS: ReadonlyArray<readonly [id: HelpId, fnNames: readonly string[]]> = [
  ["project-form", ["ProjectForm"]],
  ["goal-form", ["GoalForm", "DependsOnField"]],
  ["task-form", ["TaskForm"]],
];

/** 撰寫時（2026-10-27 於 HEAD 複核）的標籤快照（TCS §5.4 FORM_LABELS）：真檔的抽取結果必須涵蓋它；表單日後新增欄位不影響此斷言。 */
const FORM_LABELS: Readonly<Record<string, readonly string[]>> = {
  "project-form": ["專案名稱", "執行路徑", "說明描述", "通過標準", "自治等級"],
  "goal-form": ["目標名稱", "說明描述", "通過標準", "前置依賴"],
  "task-form": ["任務名稱", "說明描述", "通過標準", "最大重試次數", "驗證命令", "期望輸出 Regex"],
};

const entityFormsSource = () => readFileSync(path.join(ROOT, "components/domain/entity/EntityForms.tsx"), "utf-8");

describe("AT_PH_05_7 表單欄位清單鎖（R-PH-19）", () => {
  it("AT_PH_05_7_1 三個表單頁：已寫者其欄位名集合 ⊇ 對應函式抽出的 label 集合（表單新增欄位而說明沒補＝紅）；未寫者（輪 1 在 pending 內）先斷言它們在 pending 且抽取結果非空", () => {
    const source = entityFormsSource();
    for (const [id, fnNames] of FORM_FUNCTIONS) {
      const labels = formLabels(source, fnNames);
      expect(labels.length, `${id} 的表單標籤抽取結果不得為空（防反空轉）`).toBeGreaterThan(0);
      const page = HELP_PAGES[id];
      if (page === undefined) {
        expect(PENDING_HELP_PAGES, `${id} 還沒寫，必須在 PENDING_HELP_PAGES`).toContain(id);
        continue;
      }
      const names = new Set(page.fields.map((field) => field.name));
      expect(
        labels.filter((label) => !names.has(label)),
        `${id} 的說明沒有涵蓋表單欄位`,
      ).toEqual([]);
    }
  });

  it("AT_PH_05_7_2 formLabels 負控：抽到 Field 與 MarkdownField 的 label 字串屬性；label={x} 的運算式不抽；只抽指定函式體內的元素；DependsOnField 的標籤計入 GoalForm", () => {
    const sample = [
      "export function AForm() {",
      "  return (",
      "    <Shell>",
      '      <Field label="X"><Input /></Field>',
      '      <MarkdownField control={c} name="n" label="Y" placeholder="p" />',
      "      <Field label={dynamicLabel}><Input /></Field>",
      '      <Input label="不是 Field" />',
      "    </Shell>",
      "  );",
      "}",
      "function BForm() {",
      '  return <Field label="B 表單的欄位" />;',
      "}",
      "function DependsOnField() {",
      '  return <Field label="Z" hint="h" />;',
      "}",
      'const CForm = () => <Field label="箭頭函式內" />;',
    ].join("\n");
    expect(formLabels(sample, ["AForm"])).toEqual(["X", "Y"]);
    expect(formLabels(sample, ["BForm"])).toEqual(["B 表單的欄位"]);
    expect(formLabels(sample, ["AForm", "DependsOnField"])).toEqual(["X", "Y", "Z"]);
    expect(formLabels(sample, ["CForm"])).toEqual(["箭頭函式內"]);
    expect(formLabels(sample, ["NoSuchForm"])).toEqual([]);
  });

  it("AT_PH_05_7_2 對真檔 EntityForms.tsx：三組抽取結果各 ⊇ 撰寫時的快照清單（防反空轉；新增欄位不影響此斷言）", () => {
    const source = entityFormsSource();
    expect(Object.keys(FORM_LABELS)).toHaveLength(3);
    for (const [id, fnNames] of FORM_FUNCTIONS) {
      const labels = formLabels(source, fnNames);
      for (const expected of FORM_LABELS[id]) expect(labels, `${id} 的快照標籤 ${expected}`).toContain(expected);
    }
    // GoalForm 的「前置依賴」只在 DependsOnField 內：不傳 DependsOnField 就抽不到
    expect(formLabels(source, ["GoalForm"])).not.toContain("前置依賴");
    expect(formLabels(source, ["GoalForm", "DependsOnField"])).toContain("前置依賴");
  });
});

// ══ 輪 1b：元件靜態鎖 ═══════════════════════════════════════════════════════════════════

/** import／export from、動態 import()、require() 的模組位址（字面值）。 */
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

/** 自「位址符合 fromPattern 的 import」引入的具名成員（取原名，不看 as 別名）。 */
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

const readRel = (file: string): string => readFileSync(path.join(ROOT, file), "utf-8");

// ── AC-PH-01-1：說明鈕只有一個使用處 ────────────────────────────────────────────────────

const TOP_REGION = "components/layout/TopRegion.tsx";

type ButtonUsage = { file: string; inShowToolsBranch: boolean };

/** `<PageHelpButton …/>` 的 JSX 使用處（比對標籤名，不看 import 形態）；`inShowToolsBranch`＝元素在「條件為識別字 showTools 的三元運算式」為真的那一側。 */
function pageHelpButtonUsages(file: string, source: string): ButtonUsage[] {
  const sf = parse(source);
  const usages: ButtonUsage[] = [];
  walkAst(sf, (n) => {
    const tag = ts.isJsxSelfClosingElement(n) || ts.isJsxOpeningElement(n) ? n.tagName.getText(sf) : null;
    if (tag !== "PageHelpButton") return;
    let inBranch = false;
    let child: ts.Node = n;
    for (let parent: ts.Node | undefined = n.parent; parent; parent = parent.parent) {
      if (ts.isConditionalExpression(parent) && ts.isIdentifier(parent.condition) && parent.condition.text === "showTools" && parent.whenTrue === child) inBranch = true;
      child = parent;
    }
    usages.push({ file, inShowToolsBranch: inBranch });
  });
  return usages;
}

/** 使用處必須恰 1 個、在 TopRegion、且在 showTools 為真的分支內；回違規清單（空陣列＝合規）。 */
function buttonUsageProblems(sources: ReadonlyArray<{ file: string; source: string }>): string[] {
  const usages = sources.flatMap(({ file, source }) => pageHelpButtonUsages(file, source));
  const problems: string[] = [];
  if (usages.length !== 1) problems.push(`<PageHelpButton /> 應恰有 1 個使用處，實際 ${usages.length} 個：${usages.map((usage) => usage.file).join("、")}`);
  for (const usage of usages) {
    if (usage.file !== TOP_REGION) problems.push(`使用處不在 ${TOP_REGION}：${usage.file}`);
    else if (!usage.inShowToolsBranch) problems.push("TopRegion 的 <PageHelpButton /> 不在 showTools 為真的分支內");
  }
  return problems;
}

describe("AT_PH_01_1 說明鈕全站只有一個使用處、在 showTools 分支內（R-PH-24）", () => {
  it("AT_PH_01_1_E_2 components/** 與 app/** 非測試檔：<PageHelpButton /> 恰 1 個使用處，在 TopRegion 的 showTools 為真的分支內", () => {
    const files = [...walkDir(path.join(ROOT, "components")), ...walkDir(path.join(ROOT, "app"))];
    expect(files.length, "防反空轉：掃描檔數").toBeGreaterThan(50);
    expect(files.map(rel)).toContain(TOP_REGION);
    const sources = files.map((file) => ({ file: rel(file), source: readFileSync(file, "utf-8") }));
    expect(buttonUsageProblems(sources)).toEqual([]);
    expect(
      sources.flatMap(({ file, source }) => pageHelpButtonUsages(file, source)).map((usage) => usage.file),
      "防反空轉：掃描器看得到那一個使用處",
    ).toEqual([TOP_REGION]);
  });

  it("AT_PH_01_1_E_2 掃描器負控（合成樣本）：寫在分支外、寫在為假的一側、寫在 app 某頁、寫兩處、沒有使用處者各回非空；合規樣本（含 next/dynamic 載入的寫法）回空", () => {
    const top = (body: string, head = "") => ({ file: TOP_REGION, source: `${head}export function TopRegion() { const showTools = true; return (<header>${body}</header>); }` });
    const dynamicHead = 'const PageHelpButton = dynamic(() => import("@/components/domain/help/PageHelpButton").then((m) => m.PageHelpButton));\n';
    const compliant = top("{showTools ? (<><A /><PageHelpButton /></>) : null}", dynamicHead);
    expect(buttonUsageProblems([compliant, { file: "components/other/A.tsx", source: "export const A = () => <div />;" }])).toEqual([]);
    expect(buttonUsageProblems([top("{showTools ? <PageHelpButton /> : null}")]), "不用括號的寫法也合規").toEqual([]);

    expect(buttonUsageProblems([top("<PageHelpButton />{showTools ? <A /> : null}")]), "寫在分支外").not.toEqual([]);
    expect(buttonUsageProblems([top("{showTools ? null : <PageHelpButton />}")]), "寫在為假的一側").not.toEqual([]);
    expect(buttonUsageProblems([top("{other ? <PageHelpButton /> : null}")]), "條件不是 showTools").not.toEqual([]);
    expect(buttonUsageProblems([compliant, { file: "app/x/page.tsx", source: "export default function P() { return <PageHelpButton />; }" }]), "app 某頁多一個").not.toEqual([]);
    expect(buttonUsageProblems([{ file: "app/x/page.tsx", source: "export default function P() { return <PageHelpButton />; }" }]), "只寫在 app 某頁").not.toEqual([]);
    expect(buttonUsageProblems([top("{showTools ? (<><PageHelpButton /><PageHelpButton /></>) : null}")]), "寫兩處").not.toEqual([]);
    expect(buttonUsageProblems([top("{showTools ? <A /> : null}")]), "沒有使用處").not.toEqual([]);
  });
});

// ── AC-PH-02-3：純文字（沒有 HTML 與 Markdown 渲染器）────────────────────────────────────

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

/** 說明相關的非測試原始碼：lib/help/** 與 components/domain/help/**。 */
function helpSources(root = ROOT): Array<{ file: string; text: string }> {
  const dirs = [path.join(root, "lib", "help"), path.join(root, "components", "domain", "help")];
  return dirs.flatMap((dir) => (existsSync(dir) ? walkDir(dir) : [])).map((file) => ({ file: path.relative(root, file).split(path.sep).join("/"), text: readFileSync(file, "utf-8") }));
}

describe("AT_PH_02_3 說明一律以文字節點渲染（R-PH-31）", () => {
  it("AT_PH_02_3_2 lib/help/** 與 components/domain/help/** 的非測試檔沒有 dangerouslySetInnerHTML，也沒有任何 Markdown 或 HTML 渲染器的 import", () => {
    const sources = helpSources();
    const files = sources.map((source) => source.file);
    expect(files.length, "防反空轉：掃描檔數").toBeGreaterThanOrEqual(8);
    expect(files).toEqual(expect.arrayContaining(["lib/help/registry.ts", "components/domain/help/PageHelpDialog.tsx"]));
    for (const { file, text } of sources) expect(rendererViolations(text), file).toEqual([]);
  });

  it("AT_PH_02_3_E_1 掃描器負控：dangerouslySetInnerHTML、react-markdown、rehype-raw、remark-gfm、@uiw/react-md-editor、@/components/markdown、相對路徑的 markdown、動態 import 逐一回非空；一般寫法回空", () => {
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
    const good = ['import { Button } from "@/components/ui/button";', "const html = '<b>字面文字</b>';", 'import { markdownLike } from "./markdownLike";'];
    for (const sample of good) expect(rendererViolations(sample), sample).toEqual([]);
  });
});

// ── AC-PH-04-4：議題中心不持有狀態詞清單 ─────────────────────────────────────────────────

/** 黃金檔的議題狀態名（現讀；不在測試裡另抄）。 */
function statusWords(): string[] {
  const golden = JSON.parse(readRel("tests/fixtures/si/A.camel.json")) as { issues: { legend: { statuses: Array<{ name: string }> } } };
  return golden.issues.legend.statuses.map((status) => status.name);
}

/** 該檔含幾個不同的狀態名；≥ 4 即違規（回非空清單）。含註解（註解裡寫出一份詞表也算持有）；同一個詞出現幾次都只算一個。 */
function stateKeyViolations(file: string, source: string, words: ReadonlyArray<string>): string[] {
  const present = words.filter((word) => source.includes(word));
  return present.length >= 4 ? [`${file} 含 ${present.length} 個不同的狀態名：${present.join("、")}`] : [];
}

/** 狀態詞鎖的掃描範圍（AC-PH-04-4）：lib/help/issues.ts（含 issues.* 同名族）與 components/domain/help/** 的非測試檔；**不含** lib/help/states.ts 與其他頁檔。 */
function stateWordScope(root: string): string[] {
  const files: string[] = [];
  const helpDir = path.join(root, "components", "domain", "help");
  if (existsSync(helpDir)) files.push(...walkDir(helpDir));
  const libDir = path.join(root, "lib", "help");
  if (existsSync(libDir)) {
    for (const name of readdirSync(libDir).sort()) if (/^issues(\..+)?\.tsx?$/.test(name) && isScannedFile(name)) files.push(path.join(libDir, name));
  }
  return files.map((file) => path.relative(root, file).split(path.sep).join("/")).sort();
}

describe("AT_PH_04_4 議題中心說明不持有狀態詞清單（R-PH-11）", () => {
  it("AT_PH_04_4_3 lib/help/issues.ts 與 components/domain/help/** 的每個非測試檔都含不到 4 個不同的議題狀態名（詞表現讀黃金檔）；不掃 states.ts 與其他頁檔", () => {
    const words = statusWords();
    expect(words, "詞表現讀黃金檔：恰七個狀態名").toHaveLength(7);
    const scope = stateWordScope(ROOT);
    expect(scope, "防反空轉：必掃的三個檔").toEqual(expect.arrayContaining(["lib/help/issues.ts", "components/domain/help/PageHelpDialog.tsx", "components/domain/help/IssuesLegendGroups.tsx"]));
    expect(scope, "states.ts 與其他頁檔不掃（「進行中」「已完成」「延後」是一般詞）").not.toContain("lib/help/states.ts");
    expect(scope).not.toContain("lib/help/projects.ts");
    const violations = scope.flatMap((file) => stateKeyViolations(file, readRel(file), words));
    expect(violations).toEqual([]);
  });

  it("AT_PH_04_4_E_1 掃描器負控：含 4 個不同詞者回非空、含 3 個者回空、同一詞重複 4 次者回空；範圍規則——states.ts 不被掃進，issues.* 與 components/domain/help/** 的樣本被掃進", () => {
    const words = statusWords();
    expect(stateKeyViolations("樣本.ts", words.slice(0, 4).join(" "), words)).not.toEqual([]);
    expect(stateKeyViolations("樣本.ts", words.slice(0, 3).join(" "), words)).toEqual([]);
    expect(stateKeyViolations("樣本.ts", `${words[0]} `.repeat(4), words)).toEqual([]);
    expect(stateKeyViolations("樣本.ts", `// ${words.join("、")}`, words), "註解裡列出一份詞表也算").not.toEqual([]);

    const tmp = mkdtempSync(path.join(tmpdir(), "help-statewords-"));
    try {
      const body = `export const WORDS = ${JSON.stringify(words)};\n`;
      for (const name of ["lib/help/states.ts", "lib/help/issues.statusWords.sample.ts", "lib/help/projects.ts", "components/domain/help/X.sample.ts", "components/domain/help/X.test.ts"]) {
        mkdirSync(path.dirname(path.join(tmp, name)), { recursive: true });
        writeFileSync(path.join(tmp, name), body, "utf-8");
      }
      const scope = stateWordScope(tmp);
      expect(scope).toEqual(["components/domain/help/X.sample.ts", "lib/help/issues.statusWords.sample.ts"]);
      const hits = scope.flatMap((file) => stateKeyViolations(file, readFileSync(path.join(tmp, file), "utf-8"), words));
      expect(hits).toHaveLength(2);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });
});

// ── AC-PH-04-5：詞表的取數面 ────────────────────────────────────────────────────────────

/** `queryKey:` 屬性的初始值若是陣列字面值，回它的元素文字（字串字面值）；不是陣列字面值回 null。 */
function queryKeyHeads(source: string): string[][] {
  const sf = parse(source);
  const keys: string[][] = [];
  walkAst(sf, (n) => {
    if (ts.isPropertyAssignment(n) && n.name.getText(sf) === "queryKey" && ts.isArrayLiteralExpression(n.initializer)) {
      keys.push(n.initializer.elements.map((el) => (ts.isStringLiteralLike(el) ? el.text : "")));
    }
  });
  return keys;
}

/** IssuesLegendGroups 的取數面：getIssues、SI_QUERY_OPTIONS，query key 含 "help" 與 "issuesLegend"、不以 "issues" 起頭，不 import useIssues、useIssue、useIssueLookups、qk。 */
function legendQueryProblems(source: string): string[] {
  const problems: string[] = [];
  const endpoints = importedNames(source, /(^|\/)endpoints$/);
  const queries = importedNames(source, /(^|\/)queries$/);
  if (!endpoints.includes("getIssues")) problems.push("沒有自 endpoints import getIssues");
  if (!queries.includes("SI_QUERY_OPTIONS")) problems.push("沒有自 queries import SI_QUERY_OPTIONS");
  for (const banned of ["useIssues", "useIssue", "useIssueLookups", "qk"]) if (queries.includes(banned)) problems.push(`不得自 queries import ${banned}`);
  const texts = collectTexts(source);
  if (!texts.includes("help") || !texts.includes("issuesLegend")) problems.push('字面值須含 "help" 與 "issuesLegend"');
  for (const key of queryKeyHeads(source)) if (key[0] === "issues") problems.push(`query key 不得掛在 ["issues"] 家族：${JSON.stringify(key)}`);
  return problems;
}

describe("AT_PH_04_5 詞表查詢不掛議題家族、不用議題清單 hook（R-PH-12）", () => {
  it("AT_PH_04_5_E_3 components/domain/help/IssuesLegendGroups.tsx：自 endpoints import getIssues、自 queries import SI_QUERY_OPTIONS；不 import useIssues、useIssue、useIssueLookups、qk；字面值含 help 與 issuesLegend", () => {
    const source = readRel("components/domain/help/IssuesLegendGroups.tsx");
    expect(legendQueryProblems(source)).toEqual([]);
    expect(queryKeyHeads(source), "防反空轉：掃描器看得到 query key").toContainEqual(["help", "issuesLegend"]);
  });

  it("AT_PH_04_5_E_3 掃描器負控：import useIssues 者、query key 為 [issues, …] 者各回非空；合規樣本回空", () => {
    const good = [
      'import { getIssues } from "@/lib/api/endpoints";',
      'import { SI_QUERY_OPTIONS } from "@/lib/api/queries";',
      'const q = useQuery({ queryKey: ["help", "issuesLegend"], queryFn: () => getIssues({ limit: 1 }), ...SI_QUERY_OPTIONS });',
    ].join("\n");
    expect(legendQueryProblems(good)).toEqual([]);
    expect(legendQueryProblems(good.replace("import { SI_QUERY_OPTIONS }", "import { SI_QUERY_OPTIONS, useIssues }")), "import useIssues").not.toEqual([]);
    expect(legendQueryProblems(good.replace("import { SI_QUERY_OPTIONS }", "import { SI_QUERY_OPTIONS, qk }")), "import qk").not.toEqual([]);
    expect(legendQueryProblems(good.replace('["help", "issuesLegend"]', '["issues", "legend"]')), 'query key 為 ["issues", …]').not.toEqual([]);
    expect(legendQueryProblems(good.replace('import { getIssues } from "@/lib/api/endpoints";', "")), "沒有 getIssues").not.toEqual([]);
    expect(legendQueryProblems(good.replace('import { SI_QUERY_OPTIONS } from "@/lib/api/queries";', "").replace("...SI_QUERY_OPTIONS", "")), "沒有 SI_QUERY_OPTIONS").not.toEqual([]);
  });
});

// ── AC-PH-07-2：對話框沿用 DialogContent ─────────────────────────────────────────────────

/** 一個 JSX 屬性的初始值內的全部字串（字串字面值、樣板片段、巢狀的 cn(...) 引數），逐個分開回傳。 */
function attributeStrings(attr: ts.JsxAttribute): string[] {
  const out: string[] = [];
  if (attr.initializer) {
    walkAst(attr.initializer, (m) => {
      if (ts.isStringLiteral(m) || ts.isNoSubstitutionTemplateLiteral(m)) out.push(m.text);
      else if (ts.isTemplateExpression(m)) {
        out.push(m.head.text);
        for (const span of m.templateSpans) out.push(span.literal.text);
      }
    });
  }
  return out;
}

/** 全部 JSX `className` 屬性內的字串，逐個分開回傳。 */
function classNameLiterals(source: string): string[] {
  const sf = parse(source);
  const out: string[] = [];
  walkAst(sf, (n) => {
    if (ts.isJsxAttribute(n) && n.name.getText(sf) === "className") out.push(...attributeStrings(n));
  });
  return out;
}

/** 對話框的違規：傳 onCloseAutoFocus 或呼叫 preventDefault、自刻 role="dialog"、直接 import radix-ui、<DialogContent> 的 className 覆寫 max-h-／max-w-／overflow-。回空＝合規。 */
function dialogViolations(source: string): string[] {
  const sf = parse(source);
  const found: string[] = [];
  walkAst(sf, (n) => {
    if (ts.isIdentifier(n) && (n.text === "onCloseAutoFocus" || n.text === "preventDefault")) found.push(`含 ${n.text}`);
    if (ts.isJsxAttribute(n) && n.name.getText(sf) === "role" && n.initializer && ts.isStringLiteral(n.initializer) && n.initializer.text === "dialog") found.push('自刻 role="dialog"');
    if ((ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) && n.tagName.getText(sf) === "DialogContent") {
      for (const attr of n.attributes.properties) {
        if (!ts.isJsxAttribute(attr) || attr.name.getText(sf) !== "className") continue;
        for (const literal of attributeStrings(attr)) if (/(^|\s)(max-h-|max-w-|overflow-)/.test(literal)) found.push(`<DialogContent> 的 className 覆寫尺寸類別：${literal}`);
      }
    }
  });
  for (const spec of moduleNames(source)) if (spec === "radix-ui" || spec.startsWith("@radix-ui/")) found.push(`直接 import ${spec}`);
  return found;
}

describe("AT_PH_07_2 對話框建於 DialogContent，不自刻（R-PH-26）", () => {
  it("AT_PH_07_2_1 components/domain/help/PageHelpDialog.tsx：自 @/components/ui/dialog import DialogContent（含 Dialog 或 DialogBody 之一）並以 <DialogContent 渲染；不傳 onCloseAutoFocus、不呼叫 preventDefault、不 import radix-ui、不含字面 role=dialog、不覆寫尺寸類別", () => {
    const source = readRel("components/domain/help/PageHelpDialog.tsx");
    const fromDialog = importedNames(source, /^@\/components\/ui\/dialog$/);
    expect(fromDialog).toContain("DialogContent");
    expect(fromDialog.some((name) => name === "Dialog" || name === "DialogBody")).toBe(true);
    const sf = parse(source);
    let renders = 0;
    walkAst(sf, (n) => {
      if ((ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) && n.tagName.getText(sf) === "DialogContent") renders += 1;
    });
    expect(renders, "以 <DialogContent 渲染").toBeGreaterThanOrEqual(1);
    expect(dialogViolations(source)).toEqual([]);
  });

  it("AT_PH_07_2_E_1 掃描器負控：onCloseAutoFocus 搭 preventDefault、自刻 role=dialog、import radix-ui、覆寫 max-w 與 overflow 的 className 各回非空；只用 DialogContent 者回空", () => {
    const base = 'import { Dialog, DialogBody, DialogContent } from "@/components/ui/dialog";\n';
    const wrap = (props: string) => `${base}export const X = () => (<Dialog open><DialogContent title="t" ${props}><DialogBody>內容</DialogBody></DialogContent></Dialog>);`;
    expect(dialogViolations(wrap('data-testid="x"'))).toEqual([]);
    expect(dialogViolations(wrap("onCloseAutoFocus={(e) => e.preventDefault()}")), "onCloseAutoFocus 與 preventDefault").not.toEqual([]);
    expect(dialogViolations(`${base}export const X = () => <div role="dialog">自刻</div>;`), '自刻 role="dialog"').not.toEqual([]);
    expect(dialogViolations('import { Dialog } from "radix-ui";\nexport const X = Dialog.Root;'), "import radix-ui").not.toEqual([]);
    expect(dialogViolations('import * as D from "@radix-ui/react-dialog";'), "import @radix-ui/*").not.toEqual([]);
    expect(dialogViolations(wrap('className="w-[640px] max-w-none"')), "覆寫 max-w-（R-PH-27 的寫死寬度）").not.toEqual([]);
    expect(dialogViolations(wrap('className="overflow-hidden"')), "覆寫 overflow-").not.toEqual([]);
    expect(dialogViolations(wrap('className={cn("max-h-[50vh]", x)}')), "cn(...) 內覆寫 max-h-").not.toEqual([]);
    expect(dialogViolations(wrap('className="gap-2"')), "不涉及尺寸類別的 className").toEqual([]);
  });
});

// ── AC-PH-07-5：說明鈕的圖示與顏色 ───────────────────────────────────────────────────────

/** 說明鈕的違規：import CircleHelp（與公告列的「幫助中心」區別）、className 含 outline-none／outline-hidden、同一個 className 字面值內「半透明白底」與「text-white」並存。回空＝合規。 */
function buttonStyleViolations(source: string): string[] {
  const found: string[] = [];
  if (importedNames(source, /^lucide-react$/).includes("CircleHelp")) found.push("import CircleHelp");
  for (const literal of classNameLiterals(source)) {
    const tokens = literal.split(/\s+/);
    if (tokens.some((token) => token === "outline-none" || token === "outline-hidden")) found.push(`className 含 outline-none：${literal}`);
    if (tokens.some((token) => /^bg-white\/(\d|\[)/.test(token)) && tokens.includes("text-white")) found.push(`半透明白底搭白字：${literal}`);
  }
  return found;
}

describe("AT_PH_07_5 說明鈕：Lucide BookOpen、白底主色字（R-PH-25、R-PH-28、R-PH-29）", () => {
  it("AT_PH_07_5_1 PageHelpButton.tsx：自 lucide-react import BookOpen 而非 CircleHelp；className 含 bg-white、text-wg-primary、font-medium、rounded-full；沒有 outline-none，也沒有半透明底搭白字；BookOpen 在安裝版真的存在", async () => {
    const source = readRel("components/domain/help/PageHelpButton.tsx");
    expect(importedNames(source, /^lucide-react$/)).toContain("BookOpen");
    expect(buttonStyleViolations(source)).toEqual([]);
    const literals = classNameLiterals(source);
    expect(
      literals.some((literal) => ["bg-white", "text-wg-primary", "font-medium", "rounded-full"].every((token) => literal.split(/\s+/).includes(token))),
      "同一個 className 字面值含四個類別",
    ).toBe(true);
    const lucide = await import("lucide-react");
    expect(lucide.BookOpen, "安裝版有 BookOpen").toBeDefined();
  });

  it("AT_PH_07_5_E_1 掃描器負控：import CircleHelp、半透明底搭白字、含 outline-none 各回非空；BookOpen 搭 bg-white text-wg-primary 回空；單獨出現的 text-white（例如 hover 換深色底）回空", () => {
    expect(buttonStyleViolations('import { CircleHelp } from "lucide-react";')).not.toEqual([]);
    expect(buttonStyleViolations('const a = <button className="bg-white/[0.14] text-white" />;'), "半透明底（方括號）搭白字").not.toEqual([]);
    expect(buttonStyleViolations('const a = <button className="bg-white/20 text-white" />;'), "半透明底（數字）搭白字").not.toEqual([]);
    expect(buttonStyleViolations('const a = <button className="bg-white text-wg-primary outline-none" />;'), "outline-none").not.toEqual([]);
    expect(buttonStyleViolations('const a = <button className="bg-white text-wg-primary outline-hidden" />;'), "outline-hidden").not.toEqual([]);
    expect(buttonStyleViolations('import { BookOpen } from "lucide-react";\nconst a = <button className="bg-white text-wg-primary" />;')).toEqual([]);
    expect(buttonStyleViolations('const a = <button className="bg-white text-wg-primary hover:bg-wg-primary hover:text-white" />;'), "單獨出現的 hover:text-white").toEqual([]);
    expect(buttonStyleViolations('const a = <button className={cn("bg-white/50", flag && "text-white")} />;'), "分在兩個字面值：不是同一個 className 字面值內的組合").toEqual([]);
  });
});
