import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import ts from "typescript";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ResearchPrdVersion } from "@/lib/api/types";
import { fsmView } from "@/tests/fixtures/research/fsm";
import { R2, T0, sha } from "@/tests/fixtures/research/ids";
import { EVIDENCE } from "@/tests/fixtures/research/misc";
import { detailVariant } from "@/tests/fixtures/research/projects";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { PRD_PREVIEW_MAX_BYTES, StudioPanel } from "./StudioPanel";

/**
 * PRD 工作室預覽的 Markdown 管線延遲載入（PKG-FE-D；AC-R2P-09-8、TCS-ResearchToPRD-P0-20261102 AT-960-17-1 的首屏補強）：
 * react-markdown、remark-gfm、rehype-highlight 與語法高亮的語言表合計約 326KB（gzip 94KB），原本被 StudioPanel 靜態 import，進了 `/research/[researchId]` 的首屏 chunk
 * （首次載入比 FE-C 之前多 54%）；現在是非同步 chunk、不在首屏路徑（編輯器套件與它共用同一個 chunk，這裡的編輯器是替身，所以測試裡「切到預覽才載入」成立）。這支測試守三件事：
 *  ① 靜態 import 圖：StudioPanel.tsx 對 Markdown 渲染器只有動態 import；頁殼 `app/research/[researchId]/page.tsx` 的靜態 import 圖沒有任何 Markdown 渲染管線（掃描有負控）；
 *  ② 行為：載入中只有骨架（沒有 `prd-preview` 容器，不會有「容器在、內容還沒到」的半成品）、載入中收到的目錄捲動請求備妥後補做、備妥後再切預覽不再出現骨架、
 *     PRD 超過 200KB 改走純文字時完全不載入 Markdown 管線；
 *  ③ 判定指令：npx vitest run components/domain/research/StudioPanel.lazy.test.tsx
 * `MarkdownView` 以閘門式模組替身隔開：替身的工廠函式在第一次 import 時才執行、卡在閘門上，測試決定何時放行（放行後交還真模組）——
 * 動態載入的結果在同一個測試檔裡只有第一次是「載入中」（模組快取），所以下面的行為測試依序進行：先驗沒載入過的、再驗載入中、最後驗已載入。
 */
const nav = vi.hoisted(() => ({ researchId: "22222222-2222-4222-8222-222222222222", search: "step=studio", router: { push: vi.fn(), replace: vi.fn(), back: vi.fn() } }));
vi.mock("next/navigation", () => ({
  useRouter: () => nav.router,
  usePathname: () => `/research/${nav.researchId}`,
  useParams: () => ({ researchId: nav.researchId }),
  useSearchParams: () => new URLSearchParams(nav.search),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: (props: { value: string; onChange: (value: string) => void; label: string }) => (
    <textarea data-testid="rich-editor-stub" aria-label={props.label} value={props.value} onChange={(event) => props.onChange(event.target.value)} />
  ),
}));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  RadarChart: ({ children }: { children?: ReactNode }) => <div data-testid="radar-chart-stub">{children}</div>,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
  Radar: () => null,
}));

/** 閘門：`imports` 記錄工廠函式被執行的次數（＝管線被要求載入的次數）；`open()` 放行。 */
const gate = vi.hoisted(() => {
  let release: () => void = () => {};
  const opened = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { opened, open: () => release(), imports: 0 };
});
vi.mock("@/components/markdown/MarkdownView", async (importOriginal) => {
  gate.imports += 1;
  await gate.opened;
  return importOriginal();
});

function setViewport(width: number): void {
  window.matchMedia = ((query: string) => {
    const match = /\(min-width:\s*(\d+)px\)/.exec(query);
    return {
      matches: match !== null && width >= Number(match[1]),
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    };
  }) as unknown as typeof window.matchMedia;
}

/** 被呼叫 scrollIntoView 的預覽區塊（以標題行索引標記者）。 */
const scrolled: Element[] = [];
const blocksScrolled = (): Element[] => scrolled.filter((el) => el.hasAttribute("data-prd-line"));

beforeEach(() => {
  setViewport(1440);
  scrolled.length = 0;
  Element.prototype.scrollIntoView = function (this: Element) {
    scrolled.push(this);
  };
  nav.researchId = R2;
  FakeEventSource.reset();
  vi.stubGlobal("EventSource", FakeEventSource);
  window.localStorage.clear();
});
afterEach(() => {
  window.localStorage.clear();
});

// ── 夾具 ─────────────────────────────────────────────────────────────────────────────

/** 六個章節的 PRD（標題行索引：0、3、7、10、11、13、17、18、21、22；「4.2 效能」在第 18 行）。 */
const SIX = [
  "# PRD — 向量資料庫選型",
  "",
  "<!-- r2p:section=1 -->",
  "## 1. 背景",
  "為何需要向量資料庫 [E-001]",
  "",
  "<!-- r2p:section=2 -->",
  "## 2. 痛點",
  "自架與雲端的取捨 [E-002]",
  "",
  "## 3. 功能需求",
  "### 3.1 檢索",
  "支援 HNSW",
  "### 3.2 寫入",
  "批次寫入",
  "",
  "<!-- r2p:section=4 -->",
  "## 4. 驗收",
  "### 4.2 效能",
  "P95 小於 100 毫秒",
  "",
  "## 5. 非功能需求",
  "## 6. 架構",
].join("\n");
const SIX_HEADINGS = 10;

const version = (versionNo: number): ResearchPrdVersion => ({
  versionNo,
  semver: `v0.${versionNo}.0-draft`,
  kind: "DRAFT",
  authorKind: "AGENT",
  author: "spec-engineer",
  parentVersionNo: versionNo === 1 ? null : versionNo - 1,
  sha256: sha(String(versionNo)),
  bytes: 100,
  evidenceRefs: [],
  changeSummary: "",
  createdAt: T0,
});

/** 恰為指定位元組數的 PRD（每 20 行一個標題；最後補 ASCII 湊到剛好）。 */
function docOfBytes(target: number): string {
  const lines: string[] = [];
  let size = 0;
  for (let i = 0; size < target - 200; i += 1) {
    const line = i % 20 === 0 ? `## 章節 ${i}` : `第 ${i} 行：preview batching filler text ${"x".repeat(40)}`;
    lines.push(line);
    size += Buffer.byteLength(line) + 1;
  }
  return `${lines.join("\n")}\n${"a".repeat(target - size)}`;
}

function mount(prd: string) {
  const project = detailVariant("studio");
  const api = stubResearchApi({
    details: { [R2]: project },
    events: [],
    rounds: [],
    fsm: fsmView("SPEC_DRAFTING", {}, 0),
    prdVersions: [version(1), version(2)],
    prdContent: () => prd,
    evidence: EVIDENCE,
  });
  return { ...renderResearch(<StudioPanel researchId={R2} project={project} completed={false} />, "OPERATOR"), ...api };
}

const modeTab = (name: string) => screen.getByRole("tab", { name });
const settle = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

// ── ① 靜態 import 圖（AST）────────────────────────────────────────────────────────────

type ImportRef = { spec: string; kind: "static" | "dynamic" | "type" };

/** 以 TypeScript 編譯器的語法樹取出一個檔的所有模組參照（靜態、動態 `import()`、僅型別的 `import type`／`export type`）。 */
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

/** 解析專案內的模組參照（`@/…` 與相對路徑）；套件參照回 null。 */
function resolveLocal(from: string, spec: string): string | null {
  const base = spec.startsWith("@/") ? path.join(ROOT, spec.slice(2)) : spec.startsWith(".") ? path.resolve(path.dirname(from), spec) : null;
  if (base === null) return null;
  for (const candidate of [base, `${base}.ts`, `${base}.tsx`, path.join(base, "index.ts"), path.join(base, "index.tsx")]) if (existsSync(candidate)) return candidate;
  return null;
}

/** 自入口檔沿「靜態」import 走完整張圖（動態 `import()` 與僅型別的參照不追：那正是延遲載入的出口）。 */
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
      if (target !== null && /\.tsx?$/.test(target)) queue.push(target);
    }
  }
  return seen;
}

/** Markdown 渲染管線的套件：react-markdown 與它的 remark／rehype 外掛、編輯器套件（@uiw/*）、語法高亮函式庫。 */
const MARKDOWN_PACKAGES = /^(react-markdown|remark(-[\w-]+)?|rehype(-[\w-]+)?|@uiw\/[\w-]+|unified|lowlight|highlight\.js)(\/|$)/;
/** `components/markdown` 裡的檔：只有 `MarkdownEditor.tsx`（next/dynamic 的薄殼，本體 `MarkdownEditorImpl` 只以型別與動態 import 參照）可以在靜態圖裡。 */
const isMarkdownModule = (file: string): boolean => rel(file).startsWith("components/markdown/") && path.basename(file) !== "MarkdownEditor.tsx";

/** 靜態圖裡「靜態」走進 Markdown 渲染管線的邊（`檔 → 參照`）；空陣列＝首屏沒有管線。 */
function markdownStaticEdges(closure: Map<string, ImportRef[]>, resolve: (from: string, spec: string) => string | null = resolveLocal): string[] {
  const edges: string[] = [];
  for (const [file, refs] of closure)
    for (const ref of refs) {
      if (ref.kind !== "static") continue;
      const target = resolve(file, ref.spec);
      if (MARKDOWN_PACKAGES.test(ref.spec) || (target !== null && isMarkdownModule(target))) edges.push(`${rel(file)} → ${ref.spec}`);
    }
  return edges;
}

describe("AT_960_17_1 首屏補強：Markdown 渲染管線不在頁殼的靜態 import 圖裡（只經 StudioPanel 的動態 import 載入）", () => {
  const studio = path.join(ROOT, "components", "domain", "research", "StudioPanel.tsx");
  const page = path.join(ROOT, "app", "research", "[researchId]", "page.tsx");

  it("AT_960_17_1 StudioPanel.tsx 對 MarkdownView 恰有一個動態 import、沒有任何靜態 import（也沒有 react-markdown、remark、rehype 的靜態 import）", () => {
    const refs = importsOf(studio, readFileSync(studio, "utf-8"));
    expect(refs.filter((r) => r.kind === "dynamic" && r.spec === "@/components/markdown/MarkdownView")).toHaveLength(1);
    expect(refs.filter((r) => r.kind === "static" && (MARKDOWN_PACKAGES.test(r.spec) || r.spec.startsWith("@/components/markdown/MarkdownView")))).toEqual([]);
  });

  it("AT_960_17_1 頁殼 app/research/[researchId]/page.tsx 的靜態 import 圖（含 lib、components 一路走到底）沒有任何 Markdown 渲染管線；StudioPanel 仍在圖內（頁殼真的接了）", () => {
    const closure = staticClosure(page);
    expect(closure.size, "靜態 import 圖非空").toBeGreaterThan(10);
    expect([...closure.keys()].map(rel)).toEqual(expect.arrayContaining(["components/domain/research/StudioPanel.tsx", "components/markdown/MarkdownEditor.tsx"]));
    expect(markdownStaticEdges(closure)).toEqual([]);
  });

  it("AT_960_17_1 掃描器負控：靜態 import、react-markdown 套件、components/markdown 的檔各被抓到；next/dynamic 包的 import()、僅型別 import、MarkdownEditor 薄殼不算", () => {
    const edges = (file: string, text: string): string[] => markdownStaticEdges(new Map([[file, importsOf(file, text)]]));
    expect(edges(studio, 'import { MarkdownView } from "@/components/markdown/MarkdownView";')).toEqual(["components/domain/research/StudioPanel.tsx → @/components/markdown/MarkdownView"]);
    expect(edges(studio, 'import ReactMarkdown from "react-markdown";')).toHaveLength(1);
    expect(edges(studio, 'import remarkGfm from "remark-gfm";')).toHaveLength(1);
    expect(edges(studio, 'import rehypeHighlight from "rehype-highlight";')).toHaveLength(1);
    expect(edges(studio, 'import MDEditor from "@uiw/react-md-editor";')).toHaveLength(1);
    expect(edges(studio, 'import { MarkdownEditorImpl } from "@/components/markdown/MarkdownEditorImpl";')).toHaveLength(1);
    expect(edges(studio, 'const V = dynamic(() => import("@/components/markdown/MarkdownView").then((m) => m.MarkdownView));')).toEqual([]);
    expect(edges(studio, 'import type { MarkdownEditorProps } from "@/components/markdown/MarkdownEditorImpl";')).toEqual([]);
    expect(edges(studio, 'import { MarkdownEditor } from "@/components/markdown/MarkdownEditor";')).toEqual([]);
    expect(edges(studio, 'import { remarkable } from "remarkable-extra-not-a-plugin";')).toEqual([]);
  });
});

// ── ② 行為（依序：先驗沒載入過的、再驗載入中、最後驗已載入）───────────────────────────

describe("AT_960_17_1 首屏補強：預覽延遲載入的行為", () => {
  it("AT_960_17_1 超過 200KB 改走純文字預覽：完全不載入 Markdown 管線（也沒有載入骨架）", async () => {
    const user = userEvent.setup();
    mount(docOfBytes(PRD_PREVIEW_MAX_BYTES + 1024));
    await screen.findByTestId("prd-textarea");
    await user.click(modeTab("預覽"));
    expect(await screen.findByTestId("prd-preview-degraded")).toHaveTextContent("PRD 超過 200KB");
    await settle(50);
    expect(screen.queryByTestId("prd-preview-loading")).toBeNull();
    expect(screen.queryByTestId("prd-preview")).toBeNull();
    expect(gate.imports, "純文字預覽不需要 Markdown 管線").toBe(0);
  }, 30_000);

  it("AT_960_17_1 編輯模式不載入 Markdown 管線；第一次切到預覽才載入——載入中只有骨架（沒有 prd-preview 容器），載入中點目錄項不立刻捲動，備妥後補做一次", async () => {
    const user = userEvent.setup();
    mount(SIX);
    await screen.findByTestId("rich-editor-stub");
    await settle(50);
    expect(gate.imports, "編輯模式不需要 Markdown 管線").toBe(0);

    await user.click(modeTab("預覽"));
    const loading = await screen.findByTestId("prd-preview-loading");
    expect(loading).toHaveAttribute("aria-busy", "true");
    expect(loading).toHaveAccessibleName("PRD 預覽載入中");
    expect(gate.imports, "切到預覽才要求載入").toBe(1);
    expect(screen.queryByTestId("prd-preview"), "載入中沒有預覽容器（沒有半成品）").toBeNull();
    expect(screen.queryByTestId("prd-block")).toBeNull();

    // 載入中就離開預覽（切回編輯）：不丟例外、不留骨架；再切回預覽仍是同一次載入（不重複要求）
    await user.click(modeTab("編輯"));
    expect(await screen.findByTestId("rich-editor-stub")).toBeInTheDocument();
    expect(screen.queryByTestId("prd-preview-loading")).toBeNull();
    await user.click(modeTab("預覽"));
    expect(await screen.findByTestId("prd-preview-loading")).toBeInTheDocument();
    expect(gate.imports, "重複切換不重複要求載入").toBe(1);

    // 載入中點目錄項：預覽還沒有區塊可捲，請求保留（不丟失、不報錯）
    await user.click(await screen.findByRole("button", { name: /4\.2 效能/ }));
    expect(blocksScrolled()).toHaveLength(0);
    expect(screen.getByTestId("prd-preview-loading")).toBeInTheDocument();
    expect(modeTab("預覽")).toHaveAttribute("aria-selected", "true");

    // 放行：預覽容器出現（骨架消失）、Markdown 已渲染成真元素、保留的捲動請求補做一次、落在目標章節的區塊上
    gate.open();
    const preview = await screen.findByTestId("prd-preview");
    expect(screen.queryByTestId("prd-preview-loading")).toBeNull();
    expect(within(preview).getAllByTestId("prd-block")).toHaveLength(SIX_HEADINGS);
    expect(within(preview).getByRole("heading", { name: "4.2 效能" })).toBeInTheDocument();
    await waitFor(() => expect(blocksScrolled()).toHaveLength(1));
    expect(blocksScrolled()[0]).toHaveAttribute("data-prd-line", "18");
    await settle(50);
    expect(blocksScrolled(), "只補做一次").toHaveLength(1);
    expect(gate.imports, "整段流程只載入一次").toBe(1);
  }, 30_000);

  it("AT_960_17_1 管線已載入之後：再切到預覽立刻有容器（不再出現骨架）、點目錄項照舊立即捲動、不再要求載入", async () => {
    const user = userEvent.setup();
    mount(SIX);
    await screen.findByTestId("rich-editor-stub");
    await user.click(modeTab("預覽"));
    expect(screen.getByTestId("prd-preview"), "已載入：同一次互動就有預覽，沒有載入中的畫格").toBeInTheDocument();
    expect(screen.queryByTestId("prd-preview-loading")).toBeNull();
    scrolled.length = 0;
    await user.click(await screen.findByRole("button", { name: /3\.1 檢索/ }));
    expect(blocksScrolled()).toHaveLength(1);
    expect(blocksScrolled()[0]).toHaveAttribute("data-prd-line", "11");
    await user.click(modeTab("編輯"));
    await user.click(modeTab("預覽"));
    expect(screen.getByTestId("prd-preview")).toBeInTheDocument();
    expect(gate.imports).toBe(1);
  }, 30_000);
});
