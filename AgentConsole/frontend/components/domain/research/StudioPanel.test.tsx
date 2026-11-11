import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Link from "next/link";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { invalidateResearch } from "@/lib/api/queries";
import type { ResearchEvent, ResearchPrdVersion, ResearchProjectDetail, Role } from "@/lib/api/types";
import { READONLY_TITLE } from "@/lib/domain/research";
import { fsmView } from "@/tests/fixtures/research/fsm";
import { R2, R3, T0, sha } from "@/tests/fixtures/research/ids";
import { EVIDENCE } from "@/tests/fixtures/research/misc";
import { detailVariant } from "@/tests/fixtures/research/projects";
import { FAIL3_SCORES, defect, makeRound } from "@/tests/fixtures/research/reviews";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { callsOf, failure, renderResearch, stubResearchApi, writeCalls, type ApiCall, type Reply, type ResearchStubOptions } from "@/tests/helpers/research";
import { SECTION_ANCHOR } from "./PrdOutline";
import { ResearchWorkspaceView } from "./ResearchWorkspaceView";
import {
  DRAFT_DEBOUNCE_MS,
  DRAFT_KEY_PREFIX,
  LEAVE_MESSAGE,
  PREVIEW_BATCH_CHARS,
  PRD_PREVIEW_MAX_BYTES,
  PRD_SAVE_MAX_BYTES,
  RICH_EDIT_MAX_BYTES,
  StudioPanel,
  nextBlockCount,
  scrollTextareaToOffset,
  splitPrdBlocks,
  utf8Bytes,
} from "./StudioPanel";

/**
 * PRD 工作室（TCS-ResearchToPRD-P0-20261102 AT-960-16-1、16-6、16-7、16-E-1、17-2；AC-R2P-09-1、09-3、09-6～09-8）：
 * 三欄版面與響應式（matchMedia 替身）、目錄與缺陷定位的捲動、儲存產生新人工版本與舊審查過期、409、未儲存離開確認與瀏覽器草稿、凍結與 VIEWER 的真唯讀、
 * 預覽不渲染原始 HTML、200KB 界線（完整預覽分批渲染、超界降級為純文字）。`MarkdownEditor`（真編輯器套件）、`mermaid`、`recharts` 以替身隔開；
 * 真編輯器與真圖表的行為由 components/markdown 的測試與 Playwright 驗。fetch 與 EventSource 是替身。
 * 判定指令：npx vitest run components/domain/research/StudioPanel.test.tsx -t "<AT 底線形>"
 */
const nav = vi.hoisted(() => ({ researchId: "22222222-2222-4222-8222-222222222222", search: "step=studio", router: { push: vi.fn(), replace: vi.fn(), back: vi.fn() } }));
vi.mock("next/navigation", () => ({
  // 與 Next 一樣回傳穩定的 router 物件（工作區的導回 effect 以它為相依）
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

/** 替身編輯器收到的 `previewHiddenLines`（INT-14⑤：真編輯器的行為在 components/markdown 的測試驗，這裡只驗工作室有把規則傳進去）。 */
const editorStub = vi.hoisted(() => ({ hiddenLines: [] as Array<RegExp | undefined> }));
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: (props: { value: string; onChange: (value: string) => void; label: string; previewHiddenLines?: RegExp }) => {
    editorStub.hiddenLines.push(props.previewHiddenLines);
    return <textarea data-testid="rich-editor-stub" aria-label={props.label} value={props.value} onChange={(event) => props.onChange(event.target.value)} />;
  },
}));

const mm = vi.hoisted(() => ({ initialize: vi.fn(), render: vi.fn() }));
vi.mock("mermaid", () => ({ default: mm }));

type RadarProps = { data: unknown[]; children?: ReactNode };
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  RadarChart: (props: RadarProps) => <div data-testid="radar-chart-stub">{props.children}</div>,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
  Radar: () => null,
}));

/** 視窗寬度（matchMedia 替身）：依 `(min-width: Npx)` 判定。 */
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

/** 被呼叫 scrollIntoView 的元素（jsdom 沒有這個方法）。 */
const scrolled: Element[] = [];
/** 只看預覽區塊的捲動（以標題行索引標記者），不受其他元件偶發的捲動影響。 */
const blocksScrolled = (): Element[] => scrolled.filter((el) => el.hasAttribute("data-prd-line"));

// 暖機預覽的 Markdown 管線：工作室預覽是 `next/dynamic` 延遲載入真的 MarkdownView（react-markdown、remark-gfm、rehype-highlight 與語言表），
// 檔內第一個走預覽的案例會付冷載入的轉譯成本；同機高負載（CI 多 CPU 平行）時超過 findBy 的 1 秒預設等待而偶發「找不到 prd-preview」。
// 先載進模組快取，案例等的只剩「渲染完成」這個條件——斷言、等待條件與逾時都不變。
beforeAll(async () => {
  await import("@/components/markdown/MarkdownView");
}, 60_000);

beforeEach(() => {
  setViewport(1440);
  scrolled.length = 0;
  Element.prototype.scrollIntoView = function (this: Element) {
    scrolled.push(this);
  };
  nav.researchId = R2;
  nav.search = "step=studio";
  FakeEventSource.reset();
  vi.stubGlobal("EventSource", FakeEventSource);
  mm.initialize.mockReset();
  mm.render.mockReset();
  mm.render.mockImplementation(async () => ({ svg: '<svg xmlns="http://www.w3.org/2000/svg"><text>圖</text></svg>' }));
  window.localStorage.clear();
});
afterEach(() => {
  window.localStorage.clear();
  Reflect.deleteProperty(window, "requestIdleCallback");
  Reflect.deleteProperty(window, "cancelIdleCallback");
});

// ── 夾具 ─────────────────────────────────────────────────────────────────────────────

/** 六個章節的 PRD（第 3 章與第 4 章各有子節；標題行索引：0、3、7、10、11、13、17、18、21、22）。 */
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
const SIX_OLD = SIX.replace("支援 HNSW", "支援 IVF");
const SIX_HEADINGS = 10;
const lineOffset = (doc: string, heading: string): number => doc.indexOf(heading);

const version = (versionNo: number, patch: Partial<ResearchPrdVersion> = {}): ResearchPrdVersion => ({
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
  ...patch,
});
const VERSIONS = [version(1), version(2)];

const at = (n: number): string => `2026-11-02T11:00:${String(n).padStart(2, "0")}+08:00`;
const ev = (seq: number, eventType: string, payload: Record<string, unknown>): ResearchEvent => ({
  seq,
  eventType,
  step: "studio",
  actor: "bridge",
  refKind: null,
  refId: null,
  payload,
  occurredAt: at(seq),
});
/** 第 1 輪審查已完成（seq 自 1 連續：時間軸對缺口敏感）。 */
const BASE_EVENTS: ResearchEvent[] = [
  ev(1, "research.prd", { versionNo: 1 }),
  ev(2, "research.run", { stage: "REVIEW", roundNo: 1, attempt: 1, stageRunId: "r1", engineRunId: "e1", status: "SUCCEEDED", tokensUsed: 10 }),
  ev(3, "research.review", { roundNo: 1, weightedScore: 79.9, minDimensionScore: 70, passed: false, verdict: "REVISE", escalated: false }),
];
/** 第 1 輪未通過、審查的是第 2 版（head）；缺陷錨點 §4.2 對得上 SIX 的「4.2 效能」，§9.9 對不上任何章節。 */
const ROUND = makeRound(1, FAIL3_SCORES[0], 2, { defects: [defect(1, 1, { prdAnchor: "§4.2" }), defect(1, 2, { prdAnchor: "§9.9", severity: "P3" })] });

const STUDIO = detailVariant("studio");
type Mount = { role?: Role; project?: ResearchProjectDetail; completed?: boolean; stub?: Partial<ResearchStubOptions>; extra?: ReactNode };

function mount(opts: Mount = {}) {
  const project = opts.project ?? STUDIO;
  const api = stubResearchApi({
    details: { [R2]: project },
    events: BASE_EVENTS,
    rounds: [ROUND],
    fsm: fsmView("SPEC_DRAFTING", {}, 1),
    prdVersions: VERSIONS,
    prdContent: (n) => (n === 1 ? SIX_OLD : SIX),
    evidence: EVIDENCE,
    ...opts.stub,
  });
  const ui = renderResearch(
    <>
      <StudioPanel researchId={R2} project={project} completed={opts.completed === true} />
      {opts.extra}
    </>,
    opts.role ?? "OPERATOR",
  );
  return { ...ui, ...api };
}

/** 內容 ≤ RICH_EDIT_MAX_BYTES 時的編輯器（替身的輸入框）；唯讀或大文件則是精簡輸入框 `plainEditor`。 */
const editor = async () => (await screen.findByTestId("rich-editor-stub")) as HTMLTextAreaElement;
const plainEditor = async () => (await screen.findByTestId("prd-textarea")) as HTMLTextAreaElement;
const modeTab = (name: string) => screen.getByRole("tab", { name });
const DRAFT_KEY = `${DRAFT_KEY_PREFIX}${R2}`;
const settle = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** 恰為指定位元組數的 PRD：每 20 行一個標題；最後補一段 ASCII 湊到剛好。 */
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

// ── AT_960_16_1 三欄版面、響應式、目錄捲動 ───────────────────────────────────────────────

describe("AT_960_16_1 三欄版面與響應式：寬螢幕三欄、中寬左欄收合為圖示、窄螢幕改分頁籤，目錄點擊捲動", () => {
  it("AT_960_16_1 視窗 1440：三欄齊備（prd-outline、prd-editor、gatekeeper-panel）；編輯器含編輯、預覽、Diff 三個模式切換", async () => {
    setViewport(1440);
    mount();
    await editor();
    expect(screen.getByTestId("studio-panel")).toHaveAttribute("data-tier", "wide");
    expect(screen.getByTestId("prd-outline")).toBeVisible();
    expect(screen.getByTestId("prd-outline")).not.toHaveAttribute("data-collapsed");
    expect(await screen.findAllByTestId("outline-item")).toHaveLength(SIX_HEADINGS);
    expect(screen.getByTestId("prd-editor")).toBeVisible();
    expect(screen.getByTestId("gatekeeper-panel")).toBeVisible();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["編輯", "預覽", "Diff"]);
    expect(modeTab("編輯")).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("tab", { name: "目錄" }), "寬螢幕沒有欄位分頁籤").toBeNull();
  });

  it("AT_960_16_1 視窗 1000：目錄收合為圖示鈕且仍可操作（展開後點項目：游標移到該章節並收回）；編輯器與審批欄照常", async () => {
    setViewport(1000);
    mount();
    const textarea = await editor();
    expect(screen.getByTestId("studio-panel")).toHaveAttribute("data-tier", "medium");
    expect(screen.getByTestId("prd-outline")).toHaveAttribute("data-collapsed");
    expect(screen.queryAllByTestId("outline-item")).toHaveLength(0);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "展開 PRD 目錄" }));
    await user.click(await screen.findByRole("button", { name: /3\.1 檢索/ }));
    expect(screen.queryByTestId("prd-outline-panel")).toBeNull();
    expect(textarea.selectionStart, "編輯模式：游標移到該章節").toBe(lineOffset(SIX, "### 3.1 檢索"));
    expect(screen.getByTestId("prd-editor")).toBeVisible();
    expect(screen.getByTestId("gatekeeper-panel")).toBeVisible();
  });

  it("AT_960_16_1 視窗 600：改為分頁籤（目錄、編輯器、審批）一次顯示一個；選目錄項會回到編輯器", async () => {
    setViewport(600);
    mount();
    await editor();
    expect(screen.getByTestId("studio-panel")).toHaveAttribute("data-tier", "narrow");
    const tabs = screen.getAllByRole("tab").filter((t) => ["目錄", "編輯器", "審批"].includes(t.textContent ?? ""));
    expect(tabs.map((t) => t.textContent)).toEqual(["目錄", "編輯器", "審批"]);
    expect(screen.getByTestId("prd-editor")).toBeVisible();
    expect(screen.getByTestId("prd-outline")).not.toBeVisible();
    expect(screen.getByTestId("gatekeeper-panel")).not.toBeVisible();
    const user = userEvent.setup();
    await user.click(screen.getByRole("tab", { name: "審批" }));
    expect(screen.getByTestId("gatekeeper-panel")).toBeVisible();
    expect(screen.getByTestId("prd-editor")).not.toBeVisible();
    await user.click(screen.getByRole("tab", { name: "目錄" }));
    expect(screen.getByTestId("prd-outline")).toBeVisible();
    await user.click(await screen.findByRole("button", { name: /6\. 架構/ }));
    expect(screen.getByTestId("prd-editor"), "選了目錄項：回到編輯器").toBeVisible();
    expect(screen.getByRole("tab", { name: "編輯器" })).toHaveAttribute("aria-selected", "true");
  });

  it("INT-14⑤ 編輯器套件的即時預覽與目錄、「預覽」模式同一條錨點規則：工作室把 SECTION_ANCHOR（整行的 `<!-- r2p:section=N -->`）傳給編輯器的 previewHiddenLines，每次渲染都傳", async () => {
    editorStub.hiddenLines.length = 0;
    mount();
    await editor();
    expect(editorStub.hiddenLines.length).toBeGreaterThan(0);
    for (const pattern of editorStub.hiddenLines) expect(pattern, "傳的是目錄與預覽區塊共用的那一個樣式物件").toBe(SECTION_ANCHOR);
    expect(SECTION_ANCHOR.test("<!-- r2p:section=3 -->")).toBe(true);
    expect(SECTION_ANCHOR.test("<!-- 別的註解 -->")).toBe(false);
    expect(SECTION_ANCHOR.test("前綴 <!-- r2p:section=3 -->"), "同一行有其他內容不算錨點行").toBe(false);
  });

  it("AT_960_16_1 預覽模式點目錄項：對該章節的區塊呼叫 scrollIntoView（區塊以標題行索引標記）", async () => {
    const user = userEvent.setup();
    mount();
    await editor();
    await user.click(modeTab("預覽"));
    const preview = await screen.findByTestId("prd-preview");
    expect(within(preview).getAllByTestId("prd-block")).toHaveLength(SIX_HEADINGS);
    expect(preview, "來源節錨點是目錄用的記號，預覽不顯示").not.toHaveTextContent("r2p:section");
    await user.click(await screen.findByRole("button", { name: /4\.2 效能/ }));
    expect(blocksScrolled()).toHaveLength(1);
    expect(blocksScrolled()[0]).toBe(
      within(preview)
        .getAllByTestId("prd-block")
        .find((b) => b.getAttribute("data-prd-line") === "18"),
    );
    expect(blocksScrolled()[0]).toHaveTextContent("4.2 效能");
    // 被點的項目以 aria-current 標示
    expect(screen.getByRole("button", { name: /4\.2 效能/ })).toHaveAttribute("aria-current", "location");
    await user.click(screen.getByRole("button", { name: /1\. 背景/ }));
    expect(blocksScrolled()[1]).toHaveAttribute("data-prd-line", "3");
  });

  it("AT_960_16_1 缺陷卡的定位連結：編輯模式把游標移到對應章節、找不到章節時提示而不崩潰；Diff 模式點目錄項先回到預覽再捲到該章節", async () => {
    const user = userEvent.setup();
    mount();
    const textarea = await editor();
    // 編輯模式：缺陷定位
    await user.click(await screen.findByRole("button", { name: "定位 §4.2" }));
    expect(textarea.selectionStart).toBe(lineOffset(SIX, "### 4.2 效能"));
    expect(document.activeElement).toBe(textarea);
    await user.click(screen.getByRole("button", { name: "定位 §9.9" }));
    expect(await screen.findByText("找不到對應的章節：§9.9")).toBeInTheDocument();
    // Diff 模式 → 目錄
    await user.click(modeTab("Diff"));
    await screen.findByTestId("prd-diff");
    await user.click(await screen.findByRole("button", { name: /3\.2 寫入/ }));
    expect(modeTab("預覽")).toHaveAttribute("aria-selected", "true");
    await waitFor(() => expect(blocksScrolled().some((el) => el.getAttribute("data-prd-line") === "13")).toBe(true));
  });

  it("AT_960_16_1 預覽模式的缺陷定位：捲到對應章節的區塊", async () => {
    const user = userEvent.setup();
    mount();
    await editor();
    await user.click(modeTab("預覽"));
    await screen.findByTestId("prd-preview");
    await user.click(await screen.findByRole("button", { name: "定位 §4.2" }));
    await waitFor(() => expect(blocksScrolled().some((el) => el.getAttribute("data-prd-line") === "18")).toBe(true));
  });

  it("AT_960_16_1 三個模式切換：編輯（編輯器）、預覽（渲染）、Diff（版本差異）各自顯示；切換不丟失編輯中的內容", async () => {
    const user = userEvent.setup();
    mount();
    const textarea = await editor();
    fireEvent.change(textarea, { target: { value: `${SIX}\n新增的一行` } });
    await user.click(modeTab("預覽"));
    expect(await screen.findByTestId("prd-preview")).toHaveTextContent("新增的一行");
    expect(screen.queryByTestId("rich-editor-stub")).toBeNull();
    await user.click(modeTab("Diff"));
    expect(await screen.findByTestId("prd-diff")).toBeInTheDocument();
    await user.click(modeTab("編輯"));
    expect((await editor()).value).toBe(`${SIX}\n新增的一行`);
  });

  it("AT_960_16_1 scrollTextareaToOffset：游標放到指定位移並聚焦（量鏡像節點捲動；jsdom 沒有排版所以只驗游標），鏡像節點用完即移除", () => {
    const area = document.createElement("textarea");
    area.value = "第一行\n第二行\n第三行";
    document.body.appendChild(area);
    const before = document.body.children.length;
    scrollTextareaToOffset(area, 4);
    expect([area.selectionStart, area.selectionEnd]).toEqual([4, 4]);
    expect(document.activeElement).toBe(area);
    expect(document.body.children.length).toBe(before);
    area.remove();
  });
});

// ── 預覽切塊（純函式）──────────────────────────────────────────────────────────────────

describe("AT_960_16_1 預覽切塊：每個標題一個區塊、Mermaid 圍欄抽成圖段、連結參照定義帶進每個區塊", () => {
  it("AT_960_16_1 splitPrdBlocks：區塊起點與目錄的標題行一致（開頭前言另成一塊）；程式碼圍欄內的 # 行不切；mermaid 圍欄抽成圖段並依序編號", () => {
    const doc = ["前言一句", "# 標題一", "內文", "```bash", "# 不是標題", "```", "## 標題二", "```mermaid", "graph TD", "  A --> B", "```", "尾段", "```Mermaid", "graph LR", "```"].join("\n");
    const blocks = splitPrdBlocks(doc);
    expect(blocks.map((b) => b.line)).toEqual([0, 1, 6]);
    expect(blocks[0].segments).toEqual([{ kind: "markdown", text: "前言一句" }]);
    expect(blocks[1].segments).toEqual([{ kind: "markdown", text: "# 標題一\n內文\n```bash\n# 不是標題\n```" }]);
    expect(blocks[2].segments).toEqual([
      { kind: "markdown", text: "## 標題二" },
      { kind: "mermaid", code: "graph TD\n  A --> B", ordinal: 1 },
      { kind: "markdown", text: "尾段" },
      { kind: "mermaid", code: "graph LR", ordinal: 2 },
    ]);
    expect(blocks.reduce((sum, b) => sum + b.chars, 0)).toBe(doc.length + 1);
  });

  it("AT_960_16_1 預覽不顯示來源節錨點（目錄用的記號）：整行的 `<!-- r2p:section=N -->` 從文字段拿掉；其他註解照字面顯示、圍欄內的錨點照原樣；區塊起點不受影響", () => {
    const doc = ["<!-- r2p:section=1 -->", "# 一", "<!-- r2p:section=2 -->", "文字", "<!-- 別的註解 -->", "```", "<!-- r2p:section=3 -->", "```"].join("\n");
    const blocks = splitPrdBlocks(doc);
    expect(blocks.map((b) => b.line)).toEqual([0, 1]);
    expect(blocks[0].segments, "只有錨點的前言區塊沒有內容").toEqual([]);
    expect(blocks[1].segments).toEqual([{ kind: "markdown", text: "# 一\n文字\n<!-- 別的註解 -->\n```\n<!-- r2p:section=3 -->\n```" }]);
  });

  it("AT_960_16_1 其他圍欄內的「```mermaid」字樣不算圖；沒有結尾的 mermaid 圍欄吃到區塊尾；標題在第 0 行時沒有前言區塊；空文件沒有區塊內容", () => {
    expect(
      splitPrdBlocks("# 標題\n````md\n```mermaid\nx\n```\n````")
        .flatMap((b) => b.segments)
        .map((s) => s.kind),
    ).toEqual(["markdown"]);
    expect(splitPrdBlocks("# 標題\n```mermaid\ngraph TD\n  A --> B").flatMap((b) => b.segments)).toEqual([
      { kind: "markdown", text: "# 標題" },
      { kind: "mermaid", code: "graph TD\n  A --> B", ordinal: 1 },
    ]);
    expect(splitPrdBlocks("# 標題\n內文").map((b) => b.line)).toEqual([0]);
    expect(splitPrdBlocks("").flatMap((b) => b.segments)).toEqual([]);
  });

  it("AT_960_16_1 連結參照定義（[x]: url）附在每個文字段，使參照式連結在各區塊都解析得到；圍欄內的定義不算；CRLF 照常", () => {
    const doc = ["# 一", "見 [規格][s]", "## 二", "也見 [規格][s]", "", "[s]: https://example.com/spec", "```", "[fake]: https://evil.example", "```"].join("\r\n");
    const blocks = splitPrdBlocks(doc);
    expect(blocks.map((b) => b.line)).toEqual([0, 2]);
    for (const block of blocks) {
      for (const segment of block.segments) {
        if (segment.kind === "markdown") expect(segment.text).toContain("[s]: https://example.com/spec");
      }
    }
    // 圍欄內的 [fake] 只留在它原本所在的文字（圍欄內容）裡，不會被當成參照定義附到各區塊尾端
    const appended = blocks.flatMap((b) => b.segments).flatMap((s) => (s.kind === "markdown" ? s.text.split("\n\n").slice(-1) : []));
    expect(appended.join("\n")).not.toContain("[fake]");
  });

  it("AT_960_16_1 nextBlockCount：自第 from 個起累計到字數預算為止，至少多一個、到尾端為止；utf8Bytes 依位元組計（CJK 3、emoji 4）", () => {
    const blocks = [10, 10, 10, 10].map((chars, i) => ({ line: i, chars, segments: [] }));
    expect(nextBlockCount(blocks, 0, 15)).toBe(2);
    expect(nextBlockCount(blocks, 0, 1)).toBe(1);
    expect(nextBlockCount(blocks, 2, 1000)).toBe(4);
    expect(nextBlockCount(blocks, 4, 10)).toBe(4);
    expect(nextBlockCount([], 0, 10)).toBe(0);
    expect(utf8Bytes("abc")).toBe(3);
    expect(utf8Bytes("中文")).toBe(6);
    expect(utf8Bytes("\u{1F600}")).toBe(4);
    expect(utf8Bytes("")).toBe(0);
    expect(PREVIEW_BATCH_CHARS).toBeGreaterThan(0);
  });
});

// ── AT_960_16_6 儲存、過期、離開確認 ─────────────────────────────────────────────────────

describe("AT_960_16_6 儲存產生新 HUMAN 版本、舊審查標過期、離開有未儲存提示", () => {
  const v3 = version(3, { authorKind: "HUMAN", author: "operator" });

  it("AT_960_16_6 OPERATOR 編輯後按儲存：請求為 PUT prd 本文含 baseVersion 與 content；成功後版本清單多一筆人工版本、最新審查結果顯示「已過期」、未儲存標示消失", async () => {
    const user = userEvent.setup();
    const contents: Record<number, string> = { 1: SIX_OLD, 2: SIX };
    const holder: { options?: ResearchStubOptions } = {};
    const overrides = (call: ApiCall): Reply => {
      if (call.method === "PUT" && call.path.endsWith("/prd")) {
        contents[3] = (call.body as { content: string }).content;
        if (holder.options) holder.options.prdVersions = [...VERSIONS, v3];
        return { status: 201, data: v3 };
      }
      return undefined;
    };
    const api = mount({ stub: { overrides, prdContent: (n) => contents[n] } });
    holder.options = api.options;
    const textarea = await editor();
    expect(screen.getByRole("button", { name: "儲存" }), "沒有修改：儲存停用").toBeDisabled();
    await screen.findByTestId("review-score");
    expect(screen.queryByTestId("review-stale")).toBeNull();
    const edited = SIX.replace("支援 HNSW", "支援 HNSW 與 IVF");
    fireEvent.change(textarea, { target: { value: edited } });
    expect(screen.getByTestId("studio-dirty")).toHaveTextContent("有尚未儲存的修改");
    await user.click(screen.getByRole("button", { name: "儲存" }));
    await waitFor(() => expect(callsOf(api.calls, "PUT", /\/prd$/)).toHaveLength(1));
    expect(callsOf(api.calls, "PUT", /\/prd$/)[0].path).toBe(`/api/v1/research/projects/${R2}/prd`);
    expect(callsOf(api.calls, "PUT", /\/prd$/)[0].body).toEqual({ baseVersion: 2, content: edited });
    await waitFor(() => expect(screen.getByTestId("studio-version")).toHaveTextContent("第 3 版・人工"));
    expect(await screen.findByText(/已儲存為第 3 版（人工編輯）；先前的審查結果已過期/)).toBeInTheDocument();
    expect(screen.getByTestId("studio-dirty")).toHaveTextContent("沒有未儲存的修改");
    expect((await editor()).value, "儲存後編輯器仍是剛存的內容（沒有閃回舊版）").toBe(edited);
    await waitFor(() => expect(screen.getByTestId("review-stale")).toHaveTextContent("已過期"));
    expect(screen.getByRole("button", { name: "核准 PRD" })).toBeDisabled();
    expect(screen.getByTestId("approve-note")).toHaveTextContent("審查已過期");
    expect(window.localStorage.getItem(DRAFT_KEY), "已儲存：瀏覽器草稿清掉").toBeNull();
    expect(writeCalls(api.calls), "只有一次寫入（儲存）").toHaveLength(1);
  });

  it("AT_960_16_6 以舊 baseVersion 儲存（別人先存了新版）：409 prd_version_conflict → 顯示最新版本並提示重新整理、不覆蓋；「載入最新版本」捨棄我的修改", async () => {
    const user = userEvent.setup();
    const holder: { options?: ResearchStubOptions } = {};
    const agent3 = version(3, { authorKind: "AGENT" });
    const overrides = (call: ApiCall): Reply => {
      if (call.method === "PUT" && call.path.endsWith("/prd")) {
        if (holder.options) holder.options.prdVersions = [...VERSIONS, agent3];
        return failure(409, { message: "PRD 已有更新的版本", reason: "prd_version_conflict", details: { headVersion: 3 } });
      }
      return undefined;
    };
    const api = mount({ stub: { overrides, prdContent: (n) => (n === 3 ? "# 新版本\n別人的內容" : n === 1 ? SIX_OLD : SIX) } });
    holder.options = api.options;
    const textarea = await editor();
    fireEvent.change(textarea, { target: { value: `${SIX}\n我的修改` } });
    await user.click(screen.getByRole("button", { name: "儲存" }));
    const banner = await screen.findByTestId("studio-conflict");
    expect(banner).toHaveTextContent("PRD 已有更新的版本");
    expect(banner).toHaveTextContent("請重新整理");
    await waitFor(() => expect(banner).toHaveTextContent("最新：v0.3.0-draft，第 3 版"));
    expect((await editor()).value, "不覆蓋：我的修改仍在").toBe(`${SIX}\n我的修改`);
    expect(screen.queryByText(/已儲存為第/)).toBeNull();
    await user.click(within(banner).getByRole("button", { name: "載入最新版本（捨棄我的修改）" }));
    await waitFor(async () => expect((await editor()).value).toBe("# 新版本\n別人的內容"));
    expect(screen.queryByTestId("studio-conflict")).toBeNull();
  });

  it("AT_960_16_6 編輯當中別人先存了新版（head 變了）：不等按儲存就提示；儲存請求帶的是開始編輯時的版號（讓後端判衝突）", async () => {
    const user = userEvent.setup();
    const api = mount();
    const textarea = await editor();
    fireEvent.change(textarea, { target: { value: `${SIX}\n我的修改` } });
    api.options.prdVersions = [...VERSIONS, version(3)];
    await act(async () => {
      await invalidateResearch(api.client, R2);
    });
    expect(await screen.findByTestId("studio-conflict")).toHaveTextContent("從第 2 版開始改的");
    await user.click(screen.getByRole("button", { name: "儲存" }));
    await waitFor(() => expect(callsOf(api.calls, "PUT", /\/prd$/)).toHaveLength(1));
    expect((callsOf(api.calls, "PUT", /\/prd$/)[0].body as { baseVersion: number }).baseVersion, "帶開始編輯時的版號").toBe(2);
  });

  it("AT_960_16_6 有未儲存內容時離開：beforeunload 要求確認；站內點連結先 confirm（取消＝不離開、確定＝放行）；同頁錨點與沒有修改時不攔", async () => {
    const user = userEvent.setup();
    const stay = vi.fn((event: { preventDefault: () => void }) => event.preventDefault());
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    mount({
      extra: (
        <>
          <Link href="/projects" onClick={stay}>
            前往專案
          </Link>
          <Link href={`${window.location.pathname}#top`} onClick={stay}>
            同頁錨點
          </Link>
        </>
      ),
    });
    const textarea = await editor();
    const unload = () => {
      const event = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    };
    expect(unload(), "沒有修改：不攔").toBe(false);
    await user.click(screen.getByRole("link", { name: "前往專案" }));
    expect(confirm).not.toHaveBeenCalled();
    expect(stay).toHaveBeenCalledTimes(1);
    fireEvent.change(textarea, { target: { value: `${SIX}\n改` } });
    expect(unload(), "有未儲存內容：要求確認").toBe(true);
    await user.click(screen.getByRole("link", { name: "前往專案" }));
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(confirm).toHaveBeenCalledWith(LEAVE_MESSAGE);
    expect(stay, "取消離開：連結本身的處理不會再被呼叫").toHaveBeenCalledTimes(1);
    confirm.mockReturnValue(true);
    await user.click(screen.getByRole("link", { name: "前往專案" }));
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(stay, "確定離開：放行").toHaveBeenCalledTimes(2);
    await user.click(screen.getByRole("link", { name: "同頁錨點" }));
    expect(confirm, "同頁錨點不攔").toHaveBeenCalledTimes(2);
    // 還原成與 head 相同＝沒有修改
    fireEvent.change(textarea, { target: { value: SIX } });
    expect(unload()).toBe(false);
  });

  it("AT_960_16_6 localStorage 只存便利草稿：打字後去抖寫入；重新載入還原並標示未儲存；清掉後頁面仍正確", async () => {
    const first = mount();
    const textarea = await editor();
    fireEvent.change(textarea, { target: { value: `${SIX}\n草稿` } });
    await waitFor(() => expect(window.localStorage.getItem(DRAFT_KEY)).not.toBeNull(), { timeout: DRAFT_DEBOUNCE_MS + 1500 });
    expect(JSON.parse(window.localStorage.getItem(DRAFT_KEY) as string)).toEqual({ text: `${SIX}\n草稿`, base: 2 });
    first.unmount();
    // 重新載入：草稿還原
    const second = mount();
    await waitFor(async () => expect((await editor()).value).toBe(`${SIX}\n草稿`));
    await waitFor(() => expect(screen.getByTestId("studio-dirty")).toHaveTextContent("有尚未儲存的修改"));
    second.unmount();
    // 清掉瀏覽器儲存：頁面仍正確（顯示資料庫的版本）
    window.localStorage.clear();
    mount();
    await waitFor(async () => expect((await editor()).value).toBe(SIX));
    expect(screen.getByTestId("studio-dirty")).toHaveTextContent("沒有未儲存的修改");
  });

  it("AT_960_16_6 瀏覽器儲存不可用（讀寫都丟例外）：編輯與儲存照常，沒有未攔截的錯誤", async () => {
    // 只讓 localStorage 壞掉；登入狀態走 sessionStorage，同一個 Storage 原型上的方法依接收者分流
    const { getItem, setItem, removeItem } = Storage.prototype;
    const isLocal = (self: Storage) => self === window.localStorage;
    const get = vi.spyOn(Storage.prototype, "getItem").mockImplementation(function (this: Storage, key: string) {
      if (isLocal(this)) throw new Error("blocked");
      return getItem.call(this, key);
    });
    const set = vi.spyOn(Storage.prototype, "setItem").mockImplementation(function (this: Storage, key: string, value: string) {
      if (isLocal(this)) throw new Error("quota");
      setItem.call(this, key, value);
    });
    const remove = vi.spyOn(Storage.prototype, "removeItem").mockImplementation(function (this: Storage, key: string) {
      if (isLocal(this)) throw new Error("blocked");
      removeItem.call(this, key);
    });
    try {
      const user = userEvent.setup();
      const holder: { options?: ResearchStubOptions } = {};
      const overrides = (call: ApiCall): Reply => {
        if (call.method === "PUT" && call.path.endsWith("/prd")) {
          if (holder.options) holder.options.prdVersions = [...VERSIONS, version(3, { authorKind: "HUMAN" })];
          return { status: 201, data: version(3, { authorKind: "HUMAN" }) };
        }
        return undefined;
      };
      const api = mount({ stub: { overrides } });
      holder.options = api.options;
      const textarea = await editor();
      expect(textarea.value).toBe(SIX);
      fireEvent.change(textarea, { target: { value: `${SIX}\n仍可編輯` } });
      await settle(DRAFT_DEBOUNCE_MS + 200);
      expect(screen.getByTestId("studio-dirty")).toHaveTextContent("有尚未儲存的修改");
      await user.click(screen.getByRole("button", { name: "儲存" }));
      await waitFor(() => expect(callsOf(api.calls, "PUT", /\/prd$/)).toHaveLength(1));
      expect(await screen.findByText(/已儲存為第 3 版/)).toBeInTheDocument();
    } finally {
      get.mockRestore();
      set.mockRestore();
      remove.mockRestore();
    }
  });

  it("AT_960_16_6 草稿基於舊版本（第 1 版時開始改的、現在 head 是第 2 版）：還原後立即提示衝突，不靜默蓋掉；壞掉的草稿內容當作沒有", async () => {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify({ text: "舊草稿", base: 1 }));
    const first = mount();
    expect(await screen.findByTestId("studio-conflict")).toHaveTextContent("從第 1 版開始改的");
    expect((await editor()).value).toBe("舊草稿");
    first.unmount();
    window.localStorage.setItem(DRAFT_KEY, "{不是 JSON");
    mount();
    await waitFor(async () => expect((await editor()).value).toBe(SIX));
    expect(screen.queryByTestId("studio-conflict")).toBeNull();
  });

  it("AT_960_16_6 內容含 NUL 或超過 1 MiB：不能儲存並說明原因", async () => {
    mount();
    const textarea = await editor();
    fireEvent.change(textarea, { target: { value: `${SIX}\u0000` } });
    expect(screen.getByRole("button", { name: "儲存" })).toBeDisabled();
    expect(screen.getByTestId("studio-dirty")).toHaveTextContent("NUL");
    expect(PRD_SAVE_MAX_BYTES).toBe(1024 * 1024);
    fireEvent.change(textarea, { target: { value: "a".repeat(PRD_SAVE_MAX_BYTES + 1) } });
    await waitFor(() => expect(screen.getByTestId("studio-dirty")).toHaveTextContent("超過 1 MiB"));
    expect(screen.getByRole("button", { name: "儲存" })).toBeDisabled();
  });
});

// ── AT_960_16_7 凍結版與 VIEWER ─────────────────────────────────────────────────────────

describe("AT_960_16_7 凍結版與 VIEWER 的編輯器唯讀，儲存、迭代、核准皆停用", () => {
  it("AT_960_16_7 VIEWER：編輯器是唯讀輸入框（內容照常可讀）、儲存停用且 title 為唯讀提示；審批欄的迭代、核准、退回全部停用", async () => {
    const { calls } = mount({ role: "VIEWER" });
    const textarea = await plainEditor();
    await waitFor(() => expect(textarea.value).toBe(SIX));
    expect(textarea).toHaveAttribute("readonly");
    expect(textarea).toHaveAccessibleName("PRD 內容（唯讀）");
    expect(screen.queryByTestId("rich-editor-stub")).toBeNull();
    expect(screen.getByRole("button", { name: "儲存" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "儲存" })).toHaveAttribute("title", READONLY_TITLE);
    await screen.findByTestId("review-score");
    for (const name of ["一鍵自動迭代修正", "核准 PRD", "退回修改"]) expect(screen.getByRole("button", { name }), name).toBeDisabled();
    expect(screen.getByTestId("studio-dirty")).toHaveTextContent("唯讀");
    expect(writeCalls(calls), "唯讀：沒有任何寫入").toEqual([]);
    // 預覽與 Diff 仍可看
    const user = userEvent.setup();
    await user.click(modeTab("預覽"));
    expect(await screen.findByTestId("prd-preview")).toBeInTheDocument();
  });

  it("AT_960_16_7 已凍結（flow_phase FROZEN）：頂部顯示「前往分流」連結、編輯器唯讀；儲存、迭代、核准、退回皆停用（ADMIN 也一樣）", async () => {
    const frozen = detailVariant("frozen");
    const { calls } = mount({
      role: "ADMIN",
      project: frozen,
      completed: true,
      stub: { details: { [R2]: frozen }, prdVersions: [...VERSIONS, version(3, { kind: "BASELINE", semver: "v1.0.0" })] },
    });
    const banner = await screen.findByTestId("studio-frozen");
    expect(within(banner).getByRole("link", { name: "前往分流" })).toHaveAttribute("href", `/research/${R2}?step=route`);
    const textarea = await plainEditor();
    expect(textarea).toHaveAttribute("readonly");
    expect(screen.getByRole("button", { name: "儲存" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "儲存" })).toHaveAttribute("title", "規格已凍結，不能再修改");
    await screen.findByTestId("review-score");
    for (const name of ["一鍵自動迭代修正", "核准 PRD", "退回修改"]) expect(screen.getByRole("button", { name }), name).toBeDisabled();
    expect(screen.getByTestId("studio-version")).toHaveTextContent("v1.0.0");
    expect(writeCalls(calls), "唯讀：沒有任何寫入").toEqual([]);
  });

  it("AT_960_16_7 已完成的步驟（在工作區內檢視）：頁殼顯示「已完成，唯讀」、工作室編輯器唯讀；對 ADMIN 也一樣", async () => {
    nav.researchId = R3;
    const frozen = detailVariant("frozen"); // 游標在 route：看 studio 是已完成的步驟
    stubResearchApi({
      details: { [R3]: frozen },
      events: BASE_EVENTS,
      rounds: [ROUND],
      fsm: fsmView("SPEC_FROZEN", {}, 0),
      prdVersions: [...VERSIONS, version(3, { kind: "BASELINE", semver: "v1.0.0" })],
      prdContent: () => SIX,
      evidence: EVIDENCE,
    });
    renderResearch(<ResearchWorkspaceView panels={{ studio: StudioPanel }} />, "ADMIN");
    expect(await screen.findByTestId("completed-readonly-banner")).toHaveTextContent("已完成，唯讀");
    const textarea = await plainEditor();
    expect(textarea).toHaveAttribute("readonly");
    expect(await screen.findByTestId("studio-frozen")).toBeInTheDocument();
  });
});

// ── AT_960_16_E_1 預覽不渲染原始 HTML ───────────────────────────────────────────────────

const stripComments = (source: string): string => source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/.*$/gm, "$1");

/** `rehype-raw` 不得被匯入使用；唯一例外是編輯器套件的預設鏈過濾（拿它當「要移除的函式」比對，從不加進外掛清單）。 */
function rawHtmlViolations(file: string, source: string): string[] {
  const code = stripComments(source);
  if (!/["']rehype-raw["']/.test(code)) return [];
  if (!file.endsWith("MarkdownEditorImpl.tsx")) return [`${file}：匯入 rehype-raw`];
  const uses = [...code.matchAll(/\brehypeRaw\b/g)].length;
  const filterUses = [...code.matchAll(/!==\s*rehypeRaw\b/g)].length;
  return uses === 1 + filterUses && filterUses === 1 ? [] : [`${file}：rehype-raw 的用途不只是移除過濾`];
}
function sourceFiles(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) sourceFiles(full, out);
    else if (/\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name)) out.push(full);
  }
  return out;
}

describe("AT_960_16_E_1 PRD 預覽不渲染原始 HTML，外部連結帶 noopener noreferrer", () => {
  const HOSTILE = [
    "# 標題",
    "<script>window.__prd_xss = 1</script>",
    "",
    '<iframe src="https://evil.example/"></iframe>',
    "",
    '<a href="https://example.com/raw">原始 HTML 連結</a>',
    "",
    "[Markdown 連結](https://example.com/md) 與 [壞連結](javascript:alert(1))",
    "",
    '<img src=x onerror="window.__prd_xss = 2">',
  ].join("\n");

  it("AT_960_16_E_1 預覽：原始 HTML 以字面文字出現、DOM 沒有 script 與 iframe 等元素；Markdown 的外部連結 rel 含 noopener 與 noreferrer；javascript: 連結沒有 href", async () => {
    const user = userEvent.setup();
    mount({ stub: { prdContent: () => HOSTILE } });
    await editor();
    await user.click(modeTab("預覽"));
    const preview = await screen.findByTestId("prd-preview");
    expect(preview).toHaveTextContent("<script>window.__prd_xss = 1</script>");
    expect(preview).toHaveTextContent('<iframe src="https://evil.example/"></iframe>');
    expect(preview).toHaveTextContent('<a href="https://example.com/raw">原始 HTML 連結</a>');
    expect(preview.querySelector("script, iframe, img, object, embed, [onerror]")).toBeNull();
    const links = within(preview).getAllByRole("link");
    expect(links.map((a) => a.getAttribute("href"))).toEqual(["https://example.com/md"]);
    for (const a of links) {
      expect(a.getAttribute("rel")).toContain("noopener");
      expect(a.getAttribute("rel")).toContain("noreferrer");
    }
    expect(within(preview).getByText("壞連結").closest("a[href]"), "javascript: 連結拿掉 href、沒有行為").toBeNull();
    expect((window as unknown as { __prd_xss?: number }).__prd_xss).toBeUndefined();
  });

  it("AT_960_16_E_1 靜態掃描：rehype-raw 不在 components/domain/research 的 import 中；components/markdown 只有編輯器預設鏈的過濾比對（不加進外掛清單）；掃描範圍非空、掃描器有負控", () => {
    const research = sourceFiles(path.join(process.cwd(), "components", "domain", "research"));
    const markdown = sourceFiles(path.join(process.cwd(), "components", "markdown"));
    expect(research.length).toBeGreaterThanOrEqual(10);
    expect(markdown.map((f) => path.basename(f))).toEqual(expect.arrayContaining(["MarkdownView.tsx", "MarkdownEditorImpl.tsx"]));
    for (const file of [...research, ...markdown]) expect(rawHtmlViolations(file, readFileSync(file, "utf-8")), file).toEqual([]);
    expect(rawHtmlViolations("components/domain/research/StudioPanel.tsx", 'import rehypeRaw from "rehype-raw";')).not.toEqual([]);
    expect(rawHtmlViolations("components/markdown/MarkdownView.tsx", 'import rehypeRaw from "rehype-raw";\nconst p = [rehypeRaw];')).not.toEqual([]);
    expect(rawHtmlViolations("components/markdown/MarkdownEditorImpl.tsx", 'import rehypeRaw from "rehype-raw";\nconst p = [rehypeRaw];')).not.toEqual([]);
    expect(rawHtmlViolations("components/markdown/MarkdownEditorImpl.tsx", 'import rehypeRaw from "rehype-raw";\nplugins.filter((x) => x !== rehypeRaw);')).toEqual([]);
    expect(rawHtmlViolations("components/domain/research/StudioPanel.tsx", '// import rehypeRaw from "rehype-raw";\nconst ok = 1;')).toEqual([]);
  });

  it("AT_960_16_E_1 預覽裡的 Mermaid 圍欄交給延遲載入的圖區塊（嚴格模式初始化、區域名稱依序編號）", async () => {
    const user = userEvent.setup();
    const doc = ["# 標題", "```mermaid", "graph TD", "  A --> B", "```", "## 二", "```mermaid", "graph LR", "  C --> D", "```"].join("\n");
    mount({ stub: { prdContent: () => doc } });
    await editor();
    await user.click(modeTab("預覽"));
    const blocks = await screen.findAllByTestId("mermaid-block");
    expect(blocks).toHaveLength(2);
    await waitFor(() => expect(screen.getAllByTestId("mermaid-block").map((b) => b.getAttribute("data-state"))).toEqual(["ready", "ready"]));
    expect(screen.getByRole("region", { name: "Mermaid 圖表 1" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Mermaid 圖表 2" })).toBeInTheDocument();
    expect(mm.initialize.mock.calls[0][0]).toMatchObject({ securityLevel: "strict" });
    expect(mm.render.mock.calls.map((c) => c[1])).toEqual(["graph TD\n  A --> B", "graph LR\n  C --> D"]);
  });

  it("AT_960_16_E_1 沒有圖的 PRD 不載入 mermaid（模組替身沒有被初始化）", async () => {
    const user = userEvent.setup();
    mount();
    await editor();
    await user.click(modeTab("預覽"));
    await screen.findByTestId("prd-preview");
    await settle(50);
    expect(screen.queryByTestId("mermaid-block")).toBeNull();
    expect(mm.initialize).not.toHaveBeenCalled();
  });
});

// ── AT_960_17_2 200KB 界線 ──────────────────────────────────────────────────────────────

describe("AT_960_17_2 超過 200KB 降級為純文字預覽並說明原因，畫面不凍結", () => {
  const DOC_200 = docOfBytes(PRD_PREVIEW_MAX_BYTES);
  const DOC_201 = docOfBytes(PRD_PREVIEW_MAX_BYTES + 1024);

  it("AT_960_17_2 夾具恰為 200KB 與 201KB（位元組）", () => {
    expect(utf8Bytes(DOC_200)).toBe(200 * 1024);
    expect(utf8Bytes(DOC_201)).toBe(201 * 1024);
    expect(PRD_PREVIEW_MAX_BYTES).toBe(200 * 1024);
  });

  it("AT_960_17_2 200KB 走完整預覽：分批渲染（閒置排程呼叫次數大於 1）、首批只渲染一部分、最後全部渲染；沒有降級說明", async () => {
    const idle = vi.fn((run: () => void) => setTimeout(run, 0) as unknown as number);
    Object.assign(window, { requestIdleCallback: idle, cancelIdleCallback: (id: number) => clearTimeout(id) });
    const user = userEvent.setup();
    mount({ stub: { prdContent: () => DOC_200 } });
    await plainEditor();
    await user.click(modeTab("預覽"));
    const preview = await screen.findByTestId("prd-preview");
    const total = Number(preview.getAttribute("data-blocks"));
    expect(total).toBeGreaterThan(50);
    expect(Number(preview.getAttribute("data-rendered")), "首批只渲染一部分，其餘排到閒置時").toBeLessThan(total);
    expect(screen.getByTestId("prd-preview-progress")).toHaveTextContent("正在渲染其餘章節");
    await waitFor(() => expect(Number(screen.getByTestId("prd-preview").getAttribute("data-rendered"))).toBe(total), { timeout: 25_000 });
    expect(idle.mock.calls.length, "分批渲染：排程呼叫次數大於 1").toBeGreaterThan(1);
    expect(screen.queryByTestId("prd-preview-progress")).toBeNull();
    expect(screen.queryByTestId("prd-preview-degraded")).toBeNull();
    expect(within(screen.getByTestId("prd-preview")).getAllByTestId("prd-block")).toHaveLength(total);
  }, 60_000);

  it("AT_960_17_2 沒有 requestIdleCallback 的瀏覽器退回 setTimeout 分批；點到尚未渲染的章節時先補齊再捲動", async () => {
    expect(typeof window.requestIdleCallback).toBe("undefined");
    const user = userEvent.setup();
    mount({ stub: { prdContent: () => DOC_200 } });
    await plainEditor();
    await user.click(modeTab("預覽"));
    const preview = await screen.findByTestId("prd-preview");
    const total = Number(preview.getAttribute("data-blocks"));
    expect(Number(preview.getAttribute("data-rendered"))).toBeLessThan(total);
    const items = await screen.findAllByTestId("outline-item");
    const last = items[items.length - 1];
    await user.click(last);
    await waitFor(() => expect(blocksScrolled().length).toBeGreaterThan(0));
    expect(blocksScrolled()[blocksScrolled().length - 1]).toHaveAttribute("data-prd-line", last.getAttribute("data-line") as string);
    expect(Number(screen.getByTestId("prd-preview").getAttribute("data-rendered")), "補齊到目標章節").toBe(total);
  }, 60_000);

  it("AT_960_17_2 201KB：顯示降級說明（含「PRD 超過 200KB」與原因）、預覽是純文字 pre（內容逐字）；編輯與儲存仍可用；沒有任何 Markdown 區塊被渲染", async () => {
    const user = userEvent.setup();
    const { calls } = mount({ stub: { prdContent: () => DOC_201, overrides: (call) => (call.method === "PUT" ? { status: 201, data: version(3, { authorKind: "HUMAN" }) } : undefined) } });
    const textarea = await plainEditor();
    await waitFor(() => expect(textarea.value).toBe(DOC_201));
    expect(textarea, "OPERATOR 可編輯（精簡編輯器）").not.toHaveAttribute("readonly");
    expect(screen.getByTestId("editor-large-note")).toHaveTextContent("改用精簡編輯器");
    await user.click(modeTab("預覽"));
    const degraded = await screen.findByTestId("prd-preview-degraded");
    expect(degraded).toHaveTextContent("PRD 超過 200KB");
    expect(degraded).toHaveTextContent("為保持畫面順暢");
    expect(degraded).toHaveTextContent("目前 201 KB");
    const pre = within(degraded).getByRole("region", { name: "PRD 純文字預覽" });
    expect(pre.tagName).toBe("PRE");
    expect(pre.textContent).toBe(DOC_201);
    expect(screen.queryByTestId("prd-block")).toBeNull();
    // 編輯與儲存仍可用
    await user.click(modeTab("編輯"));
    const area = await plainEditor();
    fireEvent.change(area, { target: { value: `${DOC_201}\n多一行` } });
    expect(screen.getByRole("button", { name: "儲存" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "儲存" }));
    await waitFor(() => expect(callsOf(calls, "PUT", /\/prd$/)).toHaveLength(1));
  }, 60_000);

  it("AT_960_17_2 編輯器的選擇：小文件用編輯器套件、超過 RICH_EDIT_MAX_BYTES 改用精簡輸入框並說明；唯讀一律精簡輸入框", async () => {
    const small = mount();
    await editor();
    expect(screen.queryByTestId("prd-textarea")).toBeNull();
    expect(screen.queryByTestId("editor-large-note")).toBeNull();
    small.unmount();
    const bigDoc = docOfBytes(RICH_EDIT_MAX_BYTES + 100);
    mount({ stub: { prdContent: () => bigDoc } });
    expect(await plainEditor()).toHaveAccessibleName("PRD 內容（精簡編輯器）");
    expect(screen.getByTestId("editor-large-note")).toHaveTextContent(`文件較大（${Math.ceil(utf8Bytes(bigDoc) / 1024)} KB）`);
    expect(screen.queryByTestId("rich-editor-stub")).toBeNull();
  }, 20_000);
});

// ── 空狀態與載入失敗 ─────────────────────────────────────────────────────────────────────

describe("AT_960_16_1 工作室的空狀態與載入失敗", () => {
  it("AT_960_16_1 還沒有 PRD 版本：顯示說明（草擬中則提示會自動出現）；審批欄仍在", async () => {
    const none = mount({ stub: { prdVersions: [], rounds: [], events: [] } });
    expect(await screen.findByText("還沒有 PRD 版本")).toBeInTheDocument();
    expect(screen.getByText(/請回到第一步/)).toBeInTheDocument();
    expect(screen.getByTestId("gatekeeper-panel")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "儲存" })).toBeNull();
    none.unmount();
    const drafting = detailVariant("studio", { flowPhase: "DRAFTING", flowStatus: "RUNNING" });
    mount({ project: drafting, stub: { prdVersions: [], rounds: [], events: [] } });
    expect(await screen.findByText(/PRD 初稿正在生成/)).toBeInTheDocument();
  });

  it("AT_960_16_1 載入版本清單失敗：顯示錯誤並可重試，重試成功後出現編輯器", async () => {
    const user = userEvent.setup();
    let broken = true;
    mount({ stub: { overrides: (call) => (broken && call.path.endsWith("/prd/versions") ? failure(500, { message: "讀取失敗" }) : undefined) } });
    expect(await screen.findByText("無法載入 PRD 版本")).toBeInTheDocument();
    broken = false;
    await user.click(screen.getAllByRole("button", { name: "重試" })[0]);
    await editor();
  });
});
