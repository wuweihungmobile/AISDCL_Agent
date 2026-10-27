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
