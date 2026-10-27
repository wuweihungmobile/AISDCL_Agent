import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LEGEND, clone, newStub, renderIssues, unavailable, type IssuesStub } from "@/components/domain/issues/tests/issues.fixtures";
import { SERVICE_LABEL } from "@/hooks/useServiceStatus";
import type { Role } from "@/lib/api/types";
import { clearSession, resetSessionCache } from "@/lib/auth/store";
import { PROP_STATE_KEYS } from "@/lib/domain/si";
import { HELP_COMMON } from "@/lib/help/common";
import { HELP_PAGES } from "@/lib/help/registry";
import { STATE_HELP } from "@/lib/help/states";
import type { CommonHelp, HelpField, HelpStateGroup, PageHelp, StateRow, StateTableId } from "@/lib/help/types";
import { failure } from "@/tests/helpers/api";
import { PageHelpDialog, type HelpContent, type StateSource } from "./PageHelpDialog";
import { STATE_SOURCES } from "./stateSources";

/**
 * 「本頁說明」對話框的元件測試（TCS-PageHelp-20261027 R-PH-10～R-PH-14、R-PH-26、R-PH-30～R-PH-34；載具 HD〔PD〕，輪 1b 建）：
 *  - AT-PH-02-1-1、02-1-E-1：骨架（標題、恰四個 h3、預設收合的全站共通、無狀態頁的固定句）；
 *  - AT-PH-02-2-1、02-2-2：欄位表與狀態表的結構（aria-label、th scope、td data-label、列數與順序）；
 *  - AT-PH-02-3-1：登記文字一律以文字節點渲染（逸出樣本）；
 *  - AT-PH-02-4-1、02-4-E-1：沒有第二份說明（哨兵檢查）；
 *  - AT-PH-02-5-1：多張狀態表各有 h4 小標題與自己的表，順序＝登記順序；
 *  - AT-PH-02-6-1、02-6-E-1：全站共通只寫一份、位於四段之後；
 *  - AT-PH-04-3-2：狀態名稱模式（label／raw）；
 *  - AT-PH-04-6-2：自我進化頁的三張狀態表（輪 3 綁定：頁寫完才有真內容可驗）；
 *  - AT-PH-04-4-1、04-4-2：議題詞表四群取自 API 的 legend，缺註記不顯示；
 *  - AT-PH-04-5-1、04-5-2、04-5-3、04-5-4、04-5-E-1、04-5-E-2：詞表失敗句、載入中、每次開啟重取、失敗不重試、query key 與回收；
 *  - AT-PH-07-2-2：對話框沿用 DialogContent 的尺寸類別。
 * 夾具：PD＝`renderIssues`（真 `Providers`：app 預設的 QueryClient〔5xx 重試一次、staleTime 5 秒〕，D-PH-16；不用 `makeClient()`）；注入縫只有 `content` 參數、`page` 參數與 fetch 替身，
 * 不 `vi.mock` 換掉 `@/lib/help/*` 或 `stateSources`。「已寫頁」逐頁迴圈只取 `HELP_PAGES`（pending 頁豁免，被豁免的 id 由 registry.test.ts 印出）。
 * 判定指令：npx vitest run components/domain/help/PageHelpDialog.test.tsx -t "<AT 底線形>"
 */

// AuthProvider 用 useRouter；測試環境沒有 App Router
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

beforeEach(() => {
  resetSessionCache();
  clearSession();
});

// ── 夾具 ──────────────────────────────────────────────────────────────────────────

/** 已寫頁（HELP_PAGES；不含 pending）。 */
const registeredPages = (): PageHelp[] => Object.values(HELP_PAGES).filter((page): page is PageHelp => page !== undefined);

/** 合成頁：不需要登記，經 `page` 參數注入（D-PH-3）。 */
function syntheticPage(patch: Partial<PageHelp> = {}): PageHelp {
  return {
    id: "projects",
    title: "合成頁",
    purpose: ["合成的第一句。"],
    steps: ["合成的步驟一。", "合成的步驟二。"],
    fields: [{ name: "合成欄位", meaning: "合成的意思。", source: "系統自動產生" }],
    states: [],
    sourceFiles: ["components/layout/**"],
    ...patch,
  };
}

type TableSpec = { title: string; rows: ReadonlyArray<{ key: string; label: string; meaning: string; next: string }> };

/** 以真登記為底，把指定的幾張狀態表換成合成內容（鍵、標題、名稱與釋義都由測試給）；其餘表維持真登記。 */
function contentWith(tables: Partial<Record<StateTableId, TableSpec>>, common: CommonHelp = HELP_COMMON): HelpContent {
  const states: Record<string, Readonly<Record<string, StateRow>>> = { ...STATE_HELP };
  const sources: Record<string, StateSource> = { ...STATE_SOURCES };
  for (const [id, spec] of Object.entries(tables) as Array<[StateTableId, TableSpec]>) {
    states[id] = Object.fromEntries(spec.rows.map((row) => [row.key, { meaning: row.meaning, next: row.next }]));
    const labels = new Map(spec.rows.map((row) => [row.key, row.label]));
    sources[id] = { title: spec.title, keys: spec.rows.map((row) => row.key), labelOf: (key) => labels.get(key) ?? key };
  }
  return { common, states: states as HelpContent["states"], sources: sources as HelpContent["sources"] };
}

/** 外殼：對話框的開關由頁面狀態控制（真實使用就是這樣）；另有一顆對話框外的「重新開啟說明」鈕，讓測試能在 Esc 關閉後再開。 */
function Harness({ page, content }: { page: PageHelp; content?: HelpContent }) {
  const [open, setOpen] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        重新開啟說明
      </button>
      <PageHelpDialog page={page} open={open} onOpenChange={setOpen} content={content} />
    </>
  );
}

function show(page: PageHelp, options: { content?: HelpContent; role?: Role; stub?: IssuesStub } = {}) {
  return renderIssues(<Harness page={page} content={options.content} />, { role: options.role, stub: options.stub });
}

const dialogEl = (): HTMLElement => screen.getByRole("dialog");
const sectionEl = (testId: string): HTMLElement => within(dialogEl()).getByTestId(testId);
const textsOf = (nodes: Iterable<Element>): string[] => Array.from(nodes, (node) => node.textContent ?? "");
const commonEl = (): HTMLDetailsElement => dialogEl().querySelector('details[data-testid="page-help-common"]') as HTMLDetailsElement;
const FIELD_HEADS = ["欄位", "意思", "資料來源"];
const STATE_HEADS = ["狀態", "意思", "通常的下一步"];

/** 議題中心頁的詞表四群（testid 與群標題）。 */
const LEGEND_GROUPS = [
  ["page-help-legend-statuses", "狀態"],
  ["page-help-legend-results", "結果"],
  ["page-help-legend-sources", "來源"],
  ["page-help-legend-severities", "嚴重度"],
] as const;

const waitForLegend = () => screen.findByTestId("page-help-legend-statuses");

/** 詞表請求（GET /api/v1/issues，帶 limit=1）。 */
const legendCalls = (stub: IssuesStub) => stub.calls.filter((call) => call.method === "GET" && call.path === "/api/v1/issues" && call.query.get("limit") === "1");

// ── 哨兵（AC-PH-02-4）────────────────────────────────────────────────────────────

const SENTINEL = /§[a-z]+\d+§/g;

/** D-PH-6 的固定文字（TCS §5.3 FIXED_TEXT，單一出處在 TCS）：對話框內除登記內容外唯一允許的字。 */
const FIELD_SOURCES = ["您填寫或選擇", "系統自動產生", "執行引擎回報", "自我進化帳本", "系統參數", "其他頁面帶入"];
const FIXED_TEXT = [
  "・本頁說明",
  "這頁做什麼",
  "怎麼用",
  "欄位說明",
  "狀態說明",
  "全站共通",
  "欄位",
  "意思",
  "資料來源",
  "狀態",
  "通常的下一步",
  "畫面上的原值",
  "這一頁沒有會變動的狀態。",
  "結果",
  "來源",
  "嚴重度",
  "狀態詞表載入中…",
  "狀態詞表暫時取不到：",
  ...FIELD_SOURCES,
];

/** 去除標點、符號與空白（含全形括號）：比對固定文字與哨兵剩餘字時共用。 */
const normalize = (text: string): string => text.replace(/[\p{P}\p{S}\s]/gu, "");

/**
 * 偵測「第二份寫死的說明」：先確認每個預期哨兵都在文字裡（缺漏回報），再扣掉全部哨兵與固定文字，剩下的字（去標點與空白後）就是多出的文字。
 * 回空陣列＝文字只由哨兵與固定文字組成。
 */
function strayText(text: string, sentinels: readonly string[], fixed: readonly string[]): string[] {
  const problems: string[] = [];
  for (const sentinel of sentinels) if (!text.includes(sentinel)) problems.push(`缺漏哨兵：${sentinel}`);
  let rest = text;
  for (const sentinel of sentinels) rest = rest.split(sentinel).join("");
  rest = normalize(rest);
  for (const word of fixed.map(normalize).sort((a, b) => b.length - a.length)) rest = rest.split(word).join("");
  if (rest !== "") problems.push(`多出的文字：${rest}`);
  return problems;
}

/**
 * 哨兵產生器：`§<kind><序號>§`，序號遞增、全程唯一。`shown` 產生的哨兵預期會顯示在對話框裡（進 `expected`）；
 * `hidden` 產生的只當鍵用（label 模式下鍵不顯示）：它若出現在畫面上，扣掉 expected 後就會剩下，被當成多出的文字。
 */
function sentinelFactory() {
  let n = 0;
  const all: string[] = [];
  const expected: string[] = [];
  const make = (kind: string, display: boolean): string => {
    n += 1;
    const value = `§${kind}${n}§`;
    all.push(value);
    if (display) expected.push(value);
    return value;
  };
  return { shown: (kind: string) => make(kind, true), hidden: (kind: string) => make(kind, false), all, expected };
}

// ── AC-PH-02-1：骨架 ─────────────────────────────────────────────────────────────

describe("AT_PH_02_1 對話框骨架（R-PH-30）", () => {
  it("AT_PH_02_1_1 逐頁（已寫頁加合成無狀態頁）：標題「<頁名>・本頁說明」、恰四個 h3 依序、其後恰一個預設收合的全站共通、purpose 與 steps 照登記渲染、無狀態頁顯示固定一句", async () => {
    const pages = [...registeredPages(), syntheticPage({ title: "合成無狀態頁", states: [] })];
    expect(
      pages.some((page) => page.states.length > 0),
      "防反空轉：至少一個有狀態的頁",
    ).toBe(true);
    expect(
      pages.some((page) => page.states.length === 0),
      "防反空轉：至少一個無狀態的頁",
    ).toBe(true);
    for (const page of pages) {
      const view = show(page);
      const dialog = screen.getByRole("dialog", { name: `${page.title}・本頁說明` });
      expect(
        within(dialog)
          .getAllByRole("heading", { level: 3 })
          .map((h) => h.textContent),
        `${page.id} 的 h3`,
      ).toEqual(["這頁做什麼", "怎麼用", "欄位說明", "狀態說明"]);

      const commons = dialog.querySelectorAll('details[data-testid="page-help-common"]');
      expect(commons, `${page.id} 的全站共通`).toHaveLength(1);
      const details = commons[0] as HTMLDetailsElement;
      expect(details.hasAttribute("open"), "預設收合").toBe(false);
      expect(details.querySelector("summary")?.textContent).toBe("全站共通");
      const states = within(dialog).getByTestId("page-help-states");
      expect(states.compareDocumentPosition(details) & Node.DOCUMENT_POSITION_FOLLOWING, "全站共通在四段之後").toBeTruthy();

      const purpose = within(dialog).getByTestId("page-help-purpose").textContent ?? "";
      for (const item of page.purpose) expect(purpose, `${page.id} 的 purpose`).toContain(item);
      const items = within(dialog).getByTestId("page-help-steps").querySelectorAll("ol > li");
      expect(textsOf(items), `${page.id} 的 steps`).toEqual([...page.steps]);

      if (page.states.length === 0) {
        expect(states.querySelector("p")?.textContent).toBe("這一頁沒有會變動的狀態。");
        expect(states.textContent).toBe("狀態說明這一頁沒有會變動的狀態。");
        expect(states.querySelector("table, dl, h4"), `${page.id} 的狀態段不該有表、詞表或小標題`).toBeNull();
      }
      if (page.states.some((group) => "legend" in group)) await waitForLegend();
      view.unmount();
    }
  });

  it("AT_PH_02_1_E_1 全站共通預設收合：點摘要展開；關閉再開啟又是收合；任何時候 h3 都恰四個（小標題與群組標題一律 h4）", async () => {
    const user = userEvent.setup();
    show(syntheticPage({ states: [{ table: "projectStatus" }, { table: "stepStatus", name: "raw" }, { table: "alertRule" }] }));
    const h3Count = () => within(dialogEl()).getAllByRole("heading", { level: 3 }).length;
    expect(commonEl().open).toBe(false);
    expect(h3Count()).toBe(4);

    await user.click(within(commonEl()).getByText("全站共通"));
    expect(commonEl().open, "點摘要後展開").toBe(true);
    expect(h3Count()).toBe(4);

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    await user.click(screen.getByRole("button", { name: "重新開啟說明" }));
    expect(commonEl().open, "重新開啟後又是收合（details 隨對話框內容卸載重掛）").toBe(false);
    expect(h3Count()).toBe(4);
    expect(within(sectionEl("page-help-states")).getAllByRole("heading", { level: 4 })).toHaveLength(3);
  });
});

// ── AC-PH-02-2：兩種表 ───────────────────────────────────────────────────────────

describe("AT_PH_02_2 欄位表與狀態表的結構（R-PH-30）", () => {
  it("AT_PH_02_2_1 逐頁：欄位表有 aria-label、欄標題依序「欄位」「意思」「資料來源」且 th 皆 scope=col、列數與順序＝登記、每列三格、每個 td 帶 data-label＝對應欄標題", () => {
    for (const page of registeredPages()) {
      const view = show(page);
      const table = within(sectionEl("page-help-fields")).getByRole("table");
      expect((table.getAttribute("aria-label") ?? "").trim(), `${page.id} 的欄位表 aria-label`).not.toBe("");
      const heads = Array.from(table.querySelectorAll("thead th"));
      expect(textsOf(heads)).toEqual(FIELD_HEADS);
      expect(heads.every((th) => th.getAttribute("scope") === "col")).toBe(true);
      expect(textsOf(within(table).getAllByRole("columnheader"))).toEqual(FIELD_HEADS);

      const rows = Array.from(table.querySelectorAll("tbody tr"));
      expect(rows, `${page.id} 的欄位列數`).toHaveLength(page.fields.length);
      rows.forEach((row, i) => {
        const field: HelpField = page.fields[i];
        const cells = Array.from(row.querySelectorAll("td"));
        expect(cells).toHaveLength(3);
        expect(cells[0].textContent).toBe(field.name);
        expect(cells[1].textContent).toBe(field.meaning);
        expect(cells[2].textContent).toContain(field.source);
        if (field.sourceNote !== undefined) expect(cells[2].textContent).toContain(field.sourceNote);
        cells.forEach((cell, j) => expect(cell.getAttribute("data-label"), `${page.id} 第 ${i + 1} 列第 ${j + 1} 格`).toBe(FIELD_HEADS[j]));
      });
      view.unmount();
    }
  });

  it("AT_PH_02_2_2 合成頁（專案狀態＋畫面原值的步驟事件）：兩張狀態表各有 aria-label、th scope=col、td data-label；欄標題只有 raw 那張首欄是「畫面上的原值」；列數與順序＝STATE_HELP；意思與下一步逐字", () => {
    show(syntheticPage({ states: [{ table: "projectStatus" }, { table: "stepStatus", name: "raw" }] }));
    for (const [id, firstHead] of [
      ["projectStatus", "狀態"],
      ["stepStatus", "畫面上的原值"],
    ] as const) {
      const table = within(sectionEl(`page-help-states-${id}`)).getByRole("table");
      expect((table.getAttribute("aria-label") ?? "").trim(), `${id} 的 aria-label`).not.toBe("");
      const heads = Array.from(table.querySelectorAll("thead th"));
      expect(textsOf(heads)).toEqual([firstHead, "意思", "通常的下一步"]);
      expect(heads.every((th) => th.getAttribute("scope") === "col")).toBe(true);
      const registered: Readonly<Record<string, StateRow>> = STATE_HELP[id];
      const keys = Object.keys(registered);
      const rows = Array.from(table.querySelectorAll("tbody tr"));
      expect(rows, `${id} 的列數與順序`).toHaveLength(keys.length);
      rows.forEach((row, i) => {
        const cells = Array.from(row.querySelectorAll("td"));
        expect(cells).toHaveLength(3);
        expect(cells[1].textContent).toBe(registered[keys[i]].meaning);
        expect(cells[2].textContent).toBe(registered[keys[i]].next);
        cells.forEach((cell, j) => expect(cell.getAttribute("data-label")).toBe([firstHead, "意思", "通常的下一步"][j]));
      });
    }
    // 對照：label 那張的欄標題是「狀態」，不是「畫面上的原值」
    const labelHeads = textsOf(within(sectionEl("page-help-states-projectStatus")).getByRole("table").querySelectorAll("thead th"));
    expect(labelHeads[0]).toBe("狀態");
    expect(STATE_HEADS).toEqual(["狀態", "意思", "通常的下一步"]);
  });
});

// ── AC-PH-02-3：純文字 ───────────────────────────────────────────────────────────

describe("AT_PH_02_3 純文字渲染（R-PH-31）", () => {
  it("AT_PH_02_3_1 每個文字欄都換成逸出樣本：對話框 textContent 逐字含樣本（含記號本身）；沒有 script、img、a[href]；沒有元素的文字恰等於記號內的字；&amp; 顯示為五個字元；window.alert 沒被呼叫", () => {
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    const SAMPLES = ["<script>alert(1)</script>", "**粗體**", "`§反引號§`", "[連結](https://example.test)", "<img src=x onerror=alert(1)>", "&amp;"];
    const payload = (slot: string) => `${SAMPLES.join(" ")} §${slot}§`;
    const page = syntheticPage({
      title: payload("title"),
      purpose: [payload("purpose")],
      steps: [payload("step1"), payload("step2")],
      fields: [{ name: payload("fname"), meaning: payload("fmeaning"), source: "您填寫或選擇", sourceNote: payload("fnote") }],
      states: [{ table: "projectStatus" }],
    });
    const common: CommonHelp = {
      fields: [{ name: payload("cname"), meaning: payload("cmeaning"), source: "其他頁面帶入", sourceNote: payload("cnote") }],
      states: [{ table: "serviceState" }],
      sourceFiles: [],
    };
    const content = contentWith(
      {
        projectStatus: { title: payload("ptitle"), rows: [{ key: "X1", label: payload("plabel"), meaning: payload("pmeaning"), next: payload("pnext") }] },
        serviceState: { title: payload("stitle"), rows: [{ key: "Y1", label: payload("slabel"), meaning: payload("smeaning"), next: payload("snext") }] },
      },
      common,
    );
    show(page, { content });
    const dialog = dialogEl();
    const text = dialog.textContent ?? "";
    for (const slot of [
      "title",
      "purpose",
      "step1",
      "step2",
      "fname",
      "fmeaning",
      "fnote",
      "cname",
      "cmeaning",
      "cnote",
      "ptitle",
      "plabel",
      "pmeaning",
      "pnext",
      "stitle",
      "slabel",
      "smeaning",
      "snext",
    ]) {
      expect(text, `欄位 ${slot} 逐字顯示（含記號本身）`).toContain(payload(slot));
    }
    for (const sample of SAMPLES) expect(text).toContain(sample);
    expect(text).toContain("&amp;");
    expect(dialog.querySelector("script, img, a[href]"), "沒有被解析成元素").toBeNull();
    const bare = new Set(["粗體", "§反引號§", "連結"]);
    const rendered = Array.from(dialog.querySelectorAll("*")).filter((el) => bare.has(el.textContent ?? ""));
    expect(rendered, "Markdown 若被渲染，記號會消失並長出獨立元素").toEqual([]);
    expect(alertSpy).not.toHaveBeenCalled();
  });
});

// ── AC-PH-02-4：沒有第二份說明 ───────────────────────────────────────────────────

describe("AT_PH_02_4 對話框文字只由登記內容與固定文字組成（R-PH-32）", () => {
  it("AT_PH_02_4_1 登記文字與名稱來源全換成哨兵：對話框文字扣掉哨兵與固定文字後為空；每個預期哨兵都出現且互不相同；真實內容的句子一句都不在", () => {
    const { shown, hidden, all, expected } = sentinelFactory();
    // 頁：標題、purpose、steps、欄位（含 sourceNote）；狀態段一張 label 表、一張 raw 表
    const page: PageHelp = {
      id: "projects",
      title: shown("t"),
      purpose: [shown("p"), shown("p")],
      steps: [shown("s"), shown("s")],
      fields: [
        { name: shown("fn"), meaning: shown("fm"), source: "您填寫或選擇", sourceNote: shown("fs") },
        { name: shown("fn"), meaning: shown("fm"), source: "系統自動產生" },
      ],
      states: [{ table: "projectStatus" }, { table: "stepStatus", name: "raw" }],
      sourceFiles: ["components/layout/**"],
    };
    const common: CommonHelp = {
      fields: [{ name: shown("cn"), meaning: shown("cm"), source: "其他頁面帶入", sourceNote: shown("cs") }],
      states: [{ table: "serviceState" }],
      sourceFiles: [],
    };
    // label 表：鍵只當鍵用（不顯示）、名稱顯示；raw 表：鍵本身顯示；全站共通的連線狀態表以 label 模式顯示
    const row = (key: string, label: string) => ({ key, label, meaning: shown("m"), next: shown("n") });
    const content = contentWith(
      {
        projectStatus: { title: shown("h"), rows: [row(hidden("k"), shown("l")), row(hidden("k"), shown("l"))] },
        stepStatus: { title: shown("h"), rows: [row(shown("r"), ""), row(shown("r"), "")] },
        serviceState: { title: shown("h"), rows: [row(hidden("k"), shown("l"))] },
      },
      common,
    );
    show(page, { content });
    const text = dialogEl().textContent ?? "";
    expect(strayText(text, expected, FIXED_TEXT)).toEqual([]);
    expect(new Set(all).size, "哨兵互不相同").toBe(all.length);
    expect(new Set(text.match(SENTINEL) ?? []).size, "畫面上的哨兵恰為預期的那些、互不相同（只當鍵用的哨兵不得出現）").toBe(expected.length);
    for (const key of content.sources.projectStatus.keys) expect(text, "label 模式只顯示名稱，不顯示鍵").not.toContain(key);
    // 真實內容的任何一句都不在對話框內
    for (const real of [
      HELP_PAGES.projects?.purpose[0] ?? "",
      HELP_PAGES.projects?.steps[0] ?? "",
      STATE_HELP.projectStatus.DRAFT.meaning,
      STATE_HELP.stepStatus.STARTED.meaning,
      HELP_COMMON.fields[0].meaning,
    ]) {
      expect(real).not.toBe("");
      expect(text).not.toContain(real);
    }
  });

  it("AT_PH_02_4_E_1 偵測函式 strayText 的負控：多一句寫死的字回非空；只有哨兵與固定文字回空；少一個哨兵回缺漏；哨兵產生器的字串互不相同", () => {
    const sentinels = ["§a1§", "§b2§", "§t3§"];
    const base = "§t3§・本頁說明這頁做什麼§a1§怎麼用§b2§欄位意思資料來源您填寫或選擇";
    expect(strayText(base, sentinels, FIXED_TEXT)).toEqual([]);
    expect(strayText(`${base}請參閱各頁面`, sentinels, FIXED_TEXT).join("\n")).toContain("請參閱各頁面");
    expect(strayText("這頁做什麼§a1§§t3§", sentinels, FIXED_TEXT).join("\n")).toContain("缺漏哨兵：§b2§");
    expect(strayText("這一頁沒有會變動的狀態。", [], FIXED_TEXT)).toEqual([]);
    const { shown, hidden, all } = sentinelFactory();
    for (let i = 0; i < 50; i += 1) (i % 2 === 0 ? shown : hidden)("a");
    expect(new Set(all).size).toBe(all.length);
  });
});

// ── AC-PH-02-5：多張狀態表 ───────────────────────────────────────────────────────

describe("AT_PH_02_5 多張狀態表（R-PH-33）", () => {
  it("AT_PH_02_5_1 合成頁三個群與已寫頁逐頁：狀態段的 h4 數＝群數、文字依序＝STATE_SOURCES 的 title；每群各有 page-help-states-<表 id> 容器內含自己的 table；議題中心頁的狀態段是四群詞表（沒有 table、h4 恰為四個群標題）", async () => {
    const groups: HelpStateGroup[] = [{ table: "projectStatus" }, { table: "stepStatus", name: "raw" }, { table: "alertRule" }];
    const view = show(syntheticPage({ states: groups }));
    const states = sectionEl("page-help-states");
    expect(textsOf(states.querySelectorAll("h4"))).toEqual(["projectStatus", "stepStatus", "alertRule"].map((id) => STATE_SOURCES[id as StateTableId].title));
    const containers = Array.from(states.querySelectorAll('[data-testid^="page-help-states-"]'));
    expect(containers.map((el) => el.getAttribute("data-testid"))).toEqual(["page-help-states-projectStatus", "page-help-states-stepStatus", "page-help-states-alertRule"]);
    for (const container of containers) expect(container.querySelectorAll("table"), `${container.getAttribute("data-testid")} 自己的表`).toHaveLength(1);
    expect(states.querySelectorAll("table")).toHaveLength(3);
    view.unmount();

    for (const page of registeredPages()) {
      const each = show(page);
      const section = sectionEl("page-help-states");
      if (page.states.some((group) => "legend" in group)) {
        await waitForLegend();
        expect(section.querySelector("table"), `${page.id} 的詞表群不是表`).toBeNull();
        expect(textsOf(section.querySelectorAll("h4"))).toEqual(["狀態", "結果", "來源", "嚴重度"]);
      } else if (page.states.length > 0) {
        const tableGroups = page.states.filter((group): group is { table: StateTableId; name?: "label" | "raw" } => "table" in group);
        expect(textsOf(section.querySelectorAll("h4")), `${page.id} 的小標題`).toEqual(tableGroups.map((group) => STATE_SOURCES[group.table].title));
        expect(section.querySelectorAll("table")).toHaveLength(tableGroups.length);
      }
      each.unmount();
    }
  });
});

// ── AC-PH-02-6：全站共通 ─────────────────────────────────────────────────────────

/** TCS §5.3 COMMON_ANCHORS：PRD §4 末列各項（子字串錨點，每個至少被一個全站共通的欄位名包含）。 */
const COMMON_ANCHORS = ["說明文件", "下載 CLI", "GitHub", "Engine Bridge", "通知總覽", "幫助中心", "繁體中文", "搜尋", "最近專案", "通知", "待審批佇列", "console-api", "我的專案"];

describe("AT_PH_02_6 全站共通只寫一份（R-PH-34）", () => {
  it("AT_PH_02_6_1 任兩頁（議題中心、專案管理）展開全站共通：文字逐字相同；欄位名涵蓋每個錨點；狀態表為 serviceState（名稱取自 SERVICE_LABEL）且每格有 data-label；「幫助中心」列寫明目前不能點", async () => {
    const user = userEvent.setup();
    const issues = HELP_PAGES.issues;
    const projects = HELP_PAGES.projects;
    expect(issues, "議題中心已寫").toBeDefined();
    expect(projects, "專案管理已寫").toBeDefined();
    const commonTexts: string[] = [];
    for (const page of [issues as PageHelp, projects as PageHelp]) {
      const view = show(page);
      if (page.states.some((group) => "legend" in group)) await waitForLegend();
      await user.click(within(commonEl()).getByText("全站共通"));
      const details = commonEl();
      expect(details.open).toBe(true);
      commonTexts.push(details.textContent ?? "");

      const tables = Array.from(details.querySelectorAll("table"));
      expect(tables, "全站共通有兩張表：欄位表與連線狀態表").toHaveLength(2);
      const names = textsOf(tables[0].querySelectorAll("tbody tr td:first-child"));
      for (const anchor of COMMON_ANCHORS)
        expect(
          names.some((name) => name.includes(anchor)),
          `錨點「${anchor}」`,
        ).toBe(true);
      const stateNames = textsOf(tables[1].querySelectorAll("tbody tr td:first-child"));
      expect(stateNames).toEqual(Object.keys(STATE_HELP.serviceState).map((key) => SERVICE_LABEL[key as keyof typeof SERVICE_LABEL]));
      for (const cell of tables[1].querySelectorAll("td")) expect(cell.hasAttribute("data-label")).toBe(true);
      expect(textsOf(tables[1].querySelectorAll("thead th"))).toEqual(STATE_HEADS);
      view.unmount();
    }
    expect(commonTexts[0], "兩頁的全站共通逐字相同").toBe(commonTexts[1]);
    expect(commonTexts[0].length).toBeGreaterThan(0);

    const helpCenter = HELP_COMMON.fields.filter((field) => field.name.includes("幫助中心"));
    expect(helpCenter.length, "全站共通有「幫助中心」列").toBeGreaterThanOrEqual(1);
    for (const field of helpCenter) expect(/不能點|不可點/.test(field.meaning), "寫明公告列字樣目前不能點").toBe(true);
  });

  it("AT_PH_02_6_E_1 沒有任何頁的 states 登記 serviceState；全站共通位於四個 h3 段之後且不在任何段內；全站共通的欄位釋義不是任何頁欄位釋義的子字串", () => {
    for (const page of registeredPages()) {
      expect(
        page.states.some((group) => "table" in group && group.table === "serviceState"),
        `${page.id} 不得登記 serviceState`,
      ).toBe(false);
    }
    show(syntheticPage({ states: [{ table: "projectStatus" }] }));
    const details = commonEl();
    for (const id of ["page-help-purpose", "page-help-steps", "page-help-fields", "page-help-states"]) {
      const section = sectionEl(id);
      expect(section.contains(details), `全站共通不在 ${id} 之內`).toBe(false);
      expect(section.compareDocumentPosition(details) & Node.DOCUMENT_POSITION_FOLLOWING, `全站共通在 ${id} 之後`).toBeTruthy();
    }
    for (const common of HELP_COMMON.fields) {
      for (const page of registeredPages()) {
        for (const field of page.fields) expect(field.meaning.includes(common.meaning), `${page.id} 的「${field.name}」不得複製全站共通的「${common.name}」`).toBe(false);
      }
    }
  });
});

// ── AC-PH-04-3：名稱模式 ─────────────────────────────────────────────────────────

describe("AT_PH_04_3 狀態名稱模式（R-PH-10）", () => {
  it("AT_PH_04_3_2 label 模式的「狀態」欄＝labelOf(key)；raw 模式＝鍵本身；欄標題分別為「狀態」「畫面上的原值」；同一張表可同時以兩種模式渲染", () => {
    show(syntheticPage({ states: [{ table: "projectStatus" }, { table: "stepStatus", name: "raw" }, { table: "propState", name: "raw" }, { table: "stepStatus" }] }));
    const stepContainers = within(sectionEl("page-help-states")).getAllByTestId("page-help-states-stepStatus");
    expect(stepContainers, "同一張表以兩種模式並存").toHaveLength(2);

    const firstColumn = (container: HTMLElement) => textsOf(container.querySelectorAll("tbody tr td:first-child"));
    const head = (container: HTMLElement) => container.querySelector("thead th")?.textContent;

    const project = sectionEl("page-help-states-projectStatus");
    expect(firstColumn(project)).toEqual(Object.keys(STATE_HELP.projectStatus).map((key) => STATE_SOURCES.projectStatus.labelOf?.(key)));
    expect(head(project)).toBe("狀態");

    const stepRaw = stepContainers[0];
    expect(firstColumn(stepRaw)).toEqual(Object.keys(STATE_HELP.stepStatus));
    expect(firstColumn(stepRaw)).toContain("STARTED");
    expect(head(stepRaw)).toBe("畫面上的原值");

    const propRaw = sectionEl("page-help-states-propState");
    expect(firstColumn(propRaw)).toEqual(Object.keys(STATE_HELP.propState));
    expect(head(propRaw)).toBe("畫面上的原值");

    const stepLabel = stepContainers[1];
    expect(firstColumn(stepLabel)).toEqual(Object.keys(STATE_HELP.stepStatus).map((key) => STATE_SOURCES.stepStatus.labelOf?.(key)));
    expect(firstColumn(stepLabel)).not.toContain("STARTED");
    expect(head(stepLabel)).toBe("狀態");
  });
});

// ── AC-PH-04-6：自我進化的三張狀態表 ─────────────────────────────────────────────

describe("AT_PH_04_6 自我進化頁的三張狀態表（R-PH-13）", () => {
  it("AT_PH_04_6_2 自我進化頁：觀察分類首欄＝未結、延後、已完成，提案分類首欄＝待決、進行中、已完成；提案狀態首欄＝PROP_STATE_KEYS 的畫面原值且欄標題「畫面上的原值」、列鍵集合＝PROP_STATE_KEYS；retired 列寫明畫面預留", () => {
    const page = HELP_PAGES["self-improving"];
    expect(page, "輪 3 起自我進化頁已寫，不在 PENDING_HELP_PAGES").toBeDefined();
    show(page as PageHelp);

    const states = sectionEl("page-help-states");
    expect(textsOf(states.querySelectorAll("h4"))).toEqual(["obsClass", "propClass", "propState"].map((id) => STATE_SOURCES[id as StateTableId].title));
    expect(states.querySelectorAll("table"), "三張表，沒有議題詞表群").toHaveLength(3);

    const firstColumn = (container: HTMLElement) => textsOf(container.querySelectorAll("tbody tr td:first-child"));
    const head = (container: HTMLElement) => container.querySelector("thead th")?.textContent;

    const obs = sectionEl("page-help-states-obsClass");
    expect(firstColumn(obs)).toEqual(["未結", "延後", "已完成"]);
    expect(head(obs)).toBe("狀態");

    const proposals = sectionEl("page-help-states-propClass");
    expect(firstColumn(proposals)).toEqual(["待決", "進行中", "已完成"]);
    expect(head(proposals)).toBe("狀態");

    const raw = sectionEl("page-help-states-propState");
    const keys = firstColumn(raw);
    expect(keys, "首欄是畫面上的原值，不是中文標籤").toEqual(expect.arrayContaining(["proposed", "handed-off"]));
    expect([...keys].sort()).toEqual([...PROP_STATE_KEYS].sort());
    expect(head(raw)).toBe("畫面上的原值");
    expect(within(raw).getByText("retired").closest("tr")?.textContent).toContain("根層目前不會產生這個狀態，畫面為日後預留");
  });
});

// ── AC-PH-04-4：議題詞表取自 API ─────────────────────────────────────────────────

const issuesPage = (): PageHelp => HELP_PAGES.issues as PageHelp;

describe("AT_PH_04_4 議題中心的詞表四群取自 legend（R-PH-11）", () => {
  it("AT_PH_04_4_1 開啟議題中心說明：恰一個 GET /api/v1/issues（查詢串恰 limit=1）；四群的 dt、dd 逐字＝legend 的 name、meaning；註記逐字＝updatedAtNote；群標題為 h4；狀態段沒有 table", async () => {
    const view = show(issuesPage(), { role: "VIEWER" });
    await waitForLegend();
    const calls = view.stub.calls.filter((call) => call.path === "/api/v1/issues");
    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe("GET");
    expect(calls[0].query.toString()).toBe("limit=1");

    const sources: Record<string, ReadonlyArray<{ name: string; meaning: string }>> = {
      "page-help-legend-statuses": LEGEND.statuses,
      "page-help-legend-results": LEGEND.results,
      "page-help-legend-sources": LEGEND.sources,
      "page-help-legend-severities": LEGEND.severities,
    };
    for (const [testId, title] of LEGEND_GROUPS) {
      const group = sectionEl(testId);
      expect(group.tagName).toBe("SECTION");
      expect(group.getAttribute("aria-label")).toBe(title);
      expect(group.querySelector("h4")?.textContent).toBe(title);
      expect(textsOf(group.querySelectorAll("dt")), testId).toEqual(sources[testId].map((row) => row.name));
      expect(textsOf(group.querySelectorAll("dd")), testId).toEqual(sources[testId].map((row) => row.meaning));
    }
    expect(sectionEl("page-help-legend-note").textContent).toBe(LEGEND.updatedAtNote);
    const states = sectionEl("page-help-states");
    expect(textsOf(states.querySelectorAll("h4"))).toEqual(["狀態", "結果", "來源", "嚴重度"]);
    expect(states.querySelector("table"), "詞表群不是表").toBeNull();
  });

  it("AT_PH_04_4_2 legend 的每個 meaning 換成哨兵、updatedAtNote 缺席（鍵不在，或為空字串）：詞表群只顯示哨兵與名稱（沒有第二份說明）；不出現註記、也不出現「最後已知動靜」", async () => {
    const swap = <T extends { meaning: string }>(rows: T[], prefix: string): T[] => rows.map((row, i) => ({ ...row, meaning: `§${prefix}${i + 1}§` }));
    for (const variant of ["鍵不在", "空字串"] as const) {
      const legend = clone(LEGEND);
      legend.statuses = swap(legend.statuses, "a");
      legend.results = swap(legend.results, "b");
      legend.sources = swap(legend.sources, "c");
      legend.severities = swap(legend.severities, "d");
      const sent = legend as Partial<typeof legend>;
      if (variant === "鍵不在") delete sent.updatedAtNote;
      else legend.updatedAtNote = "";
      const view = show(issuesPage(), { role: "VIEWER", stub: newStub({ legend }) });
      await waitForLegend();
      const states = sectionEl("page-help-states");
      const names = [...legend.statuses, ...legend.results, ...legend.sources, ...legend.severities].map((row) => row.name);
      const sentinels = states.textContent?.match(SENTINEL) ?? [];
      expect(sentinels).toHaveLength(names.length);
      let rest = (states.textContent ?? "").replace(SENTINEL, "").replace("狀態說明", "");
      for (const word of ["狀態", "結果", "來源", "嚴重度", ...names].sort((a, b) => b.length - a.length)) rest = rest.split(word).join("");
      expect(rest, `${variant}：扣掉哨兵、群標題與名稱後不得剩下任何字`).toBe("");
      expect(screen.queryByTestId("page-help-legend-note"), variant).toBeNull();
      expect(dialogEl().textContent).not.toContain("最後已知動靜");
      view.unmount();
    }
  });
});

// ── AC-PH-04-5：詞表失敗、載入中、每次開啟重取 ──────────────────────────────────────

/** 可控的延遲：假後端的回應被擋住，直到 release()；放行後回 undefined＝照夾具（黃金檔或 stub.legend）回放。 */
function gate() {
  let release: () => void = () => undefined;
  const promise = new Promise<void>((resolve) => {
    release = resolve;
  });
  const override = async (): Promise<undefined> => {
    await promise;
    return undefined;
  };
  return { release, override };
}

const textOf = (el: HTMLElement) => el.textContent ?? "";

describe("AT_PH_04_5 詞表的載入、失敗與重取（R-PH-12）", () => {
  it("AT_PH_04_5_1 詞表請求回 503（reason、cause、detail 齊全）：前三段照常；狀態段顯示「狀態詞表暫時取不到：」並逐字含三項；role=alert；沒有詞表群、table、載入句", async () => {
    const stub = newStub({ overrides: { list: () => unavailable() } });
    show(issuesPage(), { role: "VIEWER", stub });
    const alert = await screen.findByTestId("page-help-legend-error");
    expect(alert.getAttribute("role")).toBe("alert");
    expect(textOf(alert)).toContain("狀態詞表暫時取不到：");
    for (const part of ["si_unavailable", "nonzero_rc", "rc=2; stderr=boom 全形字元"]) expect(textOf(alert), part).toContain(part);
    const page = issuesPage();
    expect(textOf(sectionEl("page-help-purpose"))).toContain(page.purpose[0]);
    expect(textsOf(sectionEl("page-help-steps").querySelectorAll("li"))).toEqual([...page.steps]);
    expect(sectionEl("page-help-fields").querySelectorAll("tbody tr")).toHaveLength(page.fields.length);
    const states = sectionEl("page-help-states");
    expect(states.querySelector("table, dd, dl")).toBeNull();
    expect(screen.queryByTestId("page-help-legend-loading")).toBeNull();
    for (const [testId] of LEGEND_GROUPS) expect(screen.queryByTestId(testId), testId).toBeNull();
  });

  it("AT_PH_04_5_2 三種失敗各渲染一次（504、網路失敗、回應沒有詞表）：都顯示「狀態詞表暫時取不到：」且冒號後非空；前三段照常；不顯示空表與詞表群", async () => {
    const cases: Array<{ name: string; override: NonNullable<IssuesStub["overrides"]["list"]>; reason?: string }> = [
      { name: "504", override: () => failure(504, { message: "上游逾時" }) },
      {
        name: "網路失敗",
        override: () => {
          throw new TypeError("Failed to fetch");
        },
      },
      { name: "200 但沒有 legend", override: () => ({ data: { items: [] } }), reason: "回應沒有詞表" },
      { name: "200 但 legend 缺 statuses", override: () => ({ data: { items: [], legend: { ...clone(LEGEND), statuses: undefined } } }), reason: "回應沒有詞表" },
    ];
    for (const { name, override, reason } of cases) {
      const view = show(issuesPage(), { role: "VIEWER", stub: newStub({ overrides: { list: override } }) });
      const alert = await screen.findByTestId("page-help-legend-error");
      const text = textOf(alert);
      expect(text, name).toContain("狀態詞表暫時取不到：");
      expect(text.replace("狀態詞表暫時取不到：", "").trim(), `${name}：冒號後有原因`).not.toBe("");
      if (reason !== undefined) expect(text, name).toContain(reason);
      expect(textOf(sectionEl("page-help-purpose"))).toContain(issuesPage().purpose[0]);
      expect(sectionEl("page-help-states").querySelector("table, dd"), `${name}：不顯示空表`).toBeNull();
      for (const [testId] of LEGEND_GROUPS) expect(screen.queryByTestId(testId), `${name}：${testId}`).toBeNull();
      view.unmount();
    }
  });

  it("AT_PH_04_5_3 詞表請求被擋住：顯示「狀態詞表載入中…」（role=status），前三段已顯示、沒有詞表群與空表；放行後載入句消失、四群出現", async () => {
    const held = gate();
    show(issuesPage(), { role: "VIEWER", stub: newStub({ overrides: { list: held.override } }) });
    const loading = await screen.findByTestId("page-help-legend-loading");
    expect(loading.getAttribute("role")).toBe("status");
    expect(textOf(loading)).toBe("狀態詞表載入中…");
    expect(textOf(sectionEl("page-help-purpose"))).toContain(issuesPage().purpose[0]);
    expect(screen.queryByTestId("page-help-legend-statuses")).toBeNull();
    expect(sectionEl("page-help-states").querySelector("table, dd")).toBeNull();
    await act(async () => held.release());
    await waitForLegend();
    expect(screen.queryByTestId("page-help-legend-loading")).toBeNull();
    for (const [testId] of LEGEND_GROUPS) expect(screen.getByTestId(testId)).toBeInTheDocument();
  });

  it("AT_PH_04_5_4 app 預設的 5 秒 staleTime 下：開啟（詞表甲）→關閉→改回詞表乙→再開啟：共 2 個請求；第二次先顯示載入句、不先顯示甲的過期資料；之後只顯示乙", async () => {
    const user = userEvent.setup();
    const legendB = clone(LEGEND);
    legendB.statuses = legendB.statuses.map((row, i) => ({ ...row, meaning: `§乙${i + 1}§` }));
    const stub = newStub();
    show(issuesPage(), { role: "VIEWER", stub });
    await waitForLegend();
    const meaningsA = LEGEND.statuses.map((row) => row.meaning);
    for (const meaning of meaningsA) expect(dialogEl().textContent).toContain(meaning);
    expect(legendCalls(stub)).toHaveLength(1);

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    stub.legend = legendB;
    const held = gate();
    stub.overrides.list = held.override;
    await user.click(screen.getByRole("button", { name: "重新開啟說明" }));
    const loading = await screen.findByTestId("page-help-legend-loading");
    expect(textOf(loading)).toBe("狀態詞表載入中…");
    for (const meaning of meaningsA) expect(dialogEl().textContent, "不先顯示甲的過期資料").not.toContain(meaning);
    await act(async () => held.release());
    await waitForLegend();
    expect(legendCalls(stub), "每次開啟都重取，不被 staleTime 擋掉").toHaveLength(2);
    const text = dialogEl().textContent ?? "";
    expect(text).toContain("§乙1§");
    for (const meaning of meaningsA) expect(text, "全程不出現甲的 meaning").not.toContain(meaning);
  });

  it("AT_PH_04_5_E_1 app 預設對 5xx 重試一次：詞表請求回 503、開啟一次並等到錯誤句：恰 1 個請求，再等 1,500 毫秒仍是 1 個（SI_QUERY_OPTIONS 的 retry:false 真的套用）", async () => {
    const stub = newStub({ overrides: { list: () => unavailable() } });
    show(issuesPage(), { role: "VIEWER", stub });
    await screen.findByTestId("page-help-legend-error");
    expect(legendCalls(stub)).toHaveLength(1);
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 1500));
    });
    expect(legendCalls(stub), "React Query 預設重試延遲 1,000 毫秒：漏掉 retry:false 就會是 2 個").toHaveLength(1);
  });

  it("AT_PH_04_5_E_2 詞表查詢的 key 是 [help, issuesLegend]，不掛 [issues] 家族；關閉對話框後該查詢被回收（gcTime:0，不留快取）", async () => {
    const user = userEvent.setup();
    const holder: { client: QueryClient | null } = { client: null };
    function Probe() {
      const client = useQueryClient();
      useEffect(() => {
        holder.client = client;
      }, [client]);
      return null;
    }
    const stub = newStub();
    renderIssues(
      <>
        <Probe />
        <Harness page={issuesPage()} />
      </>,
      { role: "VIEWER", stub },
    );
    await waitForLegend();
    const cache = () => (holder.client as QueryClient).getQueryCache();
    const keys = () =>
      cache()
        .getAll()
        .map((query) => query.queryKey);
    expect(keys()).toContainEqual(["help", "issuesLegend"]);
    expect(
      keys().filter((key) => key[0] === "issues"),
      "不得污染議題中心的快取家族",
    ).toEqual([]);

    await user.keyboard("{Escape}");
    await waitFor(() => expect(cache().find({ queryKey: ["help", "issuesLegend"] })).toBeUndefined());
  });
});

// ── AC-PH-07-2：沿用 DialogContent ────────────────────────────────────────────────

describe("AT_PH_07_2 對話框的尺寸與可捲動（R-PH-26）", () => {
  it("AT_PH_07_2_2 role=dialog 的元素沿用 DialogContent 的 max-h-[88vh]、max-w-[calc(100%-48px)]、overflow-y-auto，並帶 data-testid=page-help-dialog", async () => {
    for (const page of [HELP_PAGES.projects as PageHelp, HELP_PAGES.settings as PageHelp]) {
      const view = show(page);
      const dialog = dialogEl();
      expect(dialog.getAttribute("data-testid")).toBe("page-help-dialog");
      for (const cls of ["max-h-[88vh]", "max-w-[calc(100%-48px)]", "overflow-y-auto"]) expect(dialog.className, `${page.id} 的 ${cls}`).toContain(cls);
      view.unmount();
    }
  });
});
