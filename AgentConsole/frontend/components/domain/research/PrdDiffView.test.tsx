import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ResearchPrdVersion } from "@/lib/api/types";
import { diffLines } from "@/lib/domain/research";
import { R2, T0, sha } from "@/tests/fixtures/research/ids";
import { failure, renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { DIFF_CONTEXT_LINES, DIFF_FOLD_MIN_ROWS, PrdDiffView, computeDiffRows, diffRowsFromParts, foldRows, normalizeForDiff } from "./PrdDiffView";

/**
 * PRD 版本差異（TCS-ResearchToPRD-P0-20261102 AT-960-16-2；AC-R2P-09-2、09-8）：行級、A→B 與 B→A 互為反向、與確定性比對 `diffLines` 逐行相同、
 * 以前綴符號加文字標籤呈現（不只靠顏色）、凍結版可比對但不可編輯；另驗函式庫的結果與確定性比對一致（隨機編輯的對拍）、超過編輯上限退回確定性比對、
 * 遠離變更的相同行收合並可展開。`diff` 是真函式庫（動態載入）。
 * 判定指令：npx vitest run components/domain/research/PrdDiffView.test.tsx -t "<AT 底線形>"
 */
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(),
}));

// ── 夾具 ─────────────────────────────────────────────────────────────────────────────

/** 兩版 PRD：含新增、刪除、不變、空白變動的行（每個變動行的內容各不相同，比對結果沒有歧義）。 */
const DOC_A = ["# 向量資料庫選型", "共同行一", "刪除行甲", "空白  變動行", "共同行二", "共同行三"].join("\n");
const DOC_B = ["# 向量資料庫選型", "共同行一", "新增行乙", "空白 變動行", "共同行二", "共同行三", "新增尾行"].join("\n");
const DOC_BASELINE = `${DOC_B}\n凍結後補一行`;

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
const VERSIONS = [version(1), version(2, { authorKind: "HUMAN", author: "operator" }), version(3, { kind: "BASELINE", semver: "v1.0.0" })];
const CONTENT: Record<number, string> = { 1: DOC_A, 2: DOC_B, 3: DOC_BASELINE };

type Stub = Parameters<typeof stubResearchApi>[0];
function mount(opts: { versions?: ResearchPrdVersion[]; content?: (n: number) => string; stub?: Stub } = {}) {
  const api = stubResearchApi({ prdVersions: opts.versions ?? VERSIONS, prdContent: opts.content ?? ((n) => CONTENT[n]), ...opts.stub });
  const ui = renderResearch(<PrdDiffView researchId={R2} versions={opts.versions ?? VERSIONS} />, "VIEWER");
  return { ...ui, ...api };
}

type Shown = { kind: string | null; text: string; aLine: number | null; bLine: number | null };
const num = (value: string | null): number | null => (value === null ? null : Number(value));
const shown = (): Shown[] =>
  screen
    .queryAllByTestId("diff-row")
    .map((el) => ({ kind: el.getAttribute("data-kind"), text: el.querySelector("code")?.textContent ?? "", aLine: num(el.getAttribute("data-a-line")), bLine: num(el.getAttribute("data-b-line")) }));
const reference = (a: string, b: string): Shown[] => diffLines(a, b).map(({ kind, text, aLine, bLine }) => ({ kind, text, aLine, bLine }));
const labelsOf = (): string[] => screen.queryAllByTestId("diff-row").map((el) => el.querySelector('[data-testid="diff-label"]')?.textContent ?? "");

const selectA = () => screen.getByRole("combobox", { name: /版本 A/ });
const selectB = () => screen.getByRole("combobox", { name: /版本 B/ });
const ready = async () => await waitFor(() => expect(screen.getByTestId("prd-diff")).toHaveAttribute("data-diff-engine"));

// ── AT_960_16_2 ────────────────────────────────────────────────────────────────────────

describe("AT_960_16_2 Diff 行級、A→B 與 B→A 互為反向、與確定性比對相同，凍結版可比對不可編輯", () => {
  it("AT_960_16_2 預設 A＝前一版、B＝最新（凍結基線）以外的兩版：渲染結果與 diffLines(A,B) 逐行相同（行種類、文字、兩邊行號）", async () => {
    mount({ versions: VERSIONS.slice(0, 2) });
    await ready();
    expect(selectA()).toHaveValue("1");
    expect(selectB()).toHaveValue("2");
    expect(shown()).toEqual(reference(DOC_A, DOC_B));
    expect(screen.getByTestId("prd-diff")).toHaveAttribute("data-diff-engine", "library");
    expect(screen.getByTestId("diff-summary")).toHaveTextContent("新增 3 行、刪除 2 行");
  });

  it("AT_960_16_2 每個變更行有前綴符號與文字標籤（「+ 新增」「- 刪除」），相同的行沒有標籤——不只靠顏色", async () => {
    mount({ versions: VERSIONS.slice(0, 2) });
    await ready();
    const rows = shown();
    const labels = labelsOf();
    expect(rows.length).toBe(labels.length);
    rows.forEach((row, i) => expect(labels[i], `${row.kind}：${row.text}`).toBe(row.kind === "add" ? "+ 新增" : row.kind === "remove" ? "- 刪除" : ""));
    expect(labels.filter((l) => l === "+ 新增")).toHaveLength(3);
    expect(labels.filter((l) => l === "- 刪除")).toHaveLength(2);
    // 空白變動的行算差異（逐字比對）：兩邊各一列
    expect(rows.filter((r) => r.text.startsWith("空白")).map((r) => [r.kind, r.text])).toEqual([
      ["remove", "空白  變動行"],
      ["add", "空白 變動行"],
    ]);
  });

  it("AT_960_16_2 對調 A／B：A→B 的新增行集合等於 B→A 的刪除行集合（反之亦然），且結果同樣等於確定性比對", async () => {
    const user = userEvent.setup();
    mount({ versions: VERSIONS.slice(0, 2) });
    await ready();
    const forward = shown();
    await user.click(screen.getByRole("button", { name: "對調 A／B" }));
    await waitFor(() => expect(selectA()).toHaveValue("2"));
    await waitFor(() => expect(shown()).toEqual(reference(DOC_B, DOC_A)));
    const backward = shown();
    const texts = (rows: Shown[], kind: string) => rows.filter((r) => r.kind === kind).map((r) => r.text);
    expect(texts(forward, "add").sort()).toEqual(texts(backward, "remove").sort());
    expect(texts(forward, "remove").sort()).toEqual(texts(backward, "add").sort());
    expect(texts(forward, "add")).toHaveLength(3);
  });

  it("AT_960_16_2 其中一版為凍結基線（BASELINE）：仍可比對，並標示凍結版唯讀、不能編輯；兩版都不是凍結版時沒有這則說明", async () => {
    const user = userEvent.setup();
    mount();
    await ready();
    // 預設 A＝第 2 版、B＝第 3 版（BASELINE）
    expect(selectA()).toHaveValue("2");
    expect(selectB()).toHaveValue("3");
    expect(screen.getByTestId("diff-frozen-note")).toHaveTextContent("凍結版只能比對、不能編輯");
    expect(screen.getByTestId("prd-diff")).toHaveAttribute("data-readonly", "true");
    expect(shown()).toEqual(reference(DOC_B, DOC_BASELINE));
    expect(within(selectB()).getByRole("option", { name: /v1\.0\.0.*凍結基線/ })).toBeInTheDocument();
    await user.selectOptions(selectB(), "2");
    await user.selectOptions(selectA(), "1");
    await waitFor(() => expect(shown()).toEqual(reference(DOC_A, DOC_B)));
    expect(screen.queryByTestId("diff-frozen-note")).toBeNull();
    expect(screen.getByTestId("prd-diff")).not.toHaveAttribute("data-readonly");
  });

  it("AT_960_16_2 兩版相同：顯示「內容相同，沒有差異」、不畫任何差異列；版本不足兩個：說明至少要兩版；版本內容載入失敗：顯示錯誤並可重試", async () => {
    const user = userEvent.setup();
    const same = mount({ versions: VERSIONS.slice(0, 2), content: () => DOC_A });
    await ready();
    expect(screen.getByTestId("diff-summary")).toHaveTextContent("兩個版本的內容相同，沒有差異");
    expect(screen.queryAllByTestId("diff-row")).toHaveLength(0);
    same.unmount();

    const single = mount({ versions: [VERSIONS[0]] });
    expect(await screen.findByText("還沒有可以比對的版本")).toBeInTheDocument();
    single.unmount();

    let broken = true;
    mount({
      versions: VERSIONS.slice(0, 2),
      stub: { overrides: (call) => (broken && call.path.endsWith("/prd/versions/2") ? failure(500, { message: "讀取失敗" }) : undefined) },
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("無法載入版本內容");
    broken = false;
    await user.click(within(alert).getByRole("button", { name: "重試" }));
    await ready();
    expect(shown()).toEqual(reference(DOC_A, DOC_B));
  });
});

// ── 比對函式與收合（純函式）──────────────────────────────────────────────────────────────

/** 可重現的偽亂數（mulberry32）。 */
function rng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

describe("AT_960_16_2 比對函式：函式庫的結果與確定性比對一致、超過編輯上限退回確定性比對", () => {
  it("AT_960_16_2 normalizeForDiff：CRLF 與 LF 等價、結尾換行不多算一行、空文件為空字串、每行以換行結尾", () => {
    expect(normalizeForDiff("")).toBe("");
    expect(normalizeForDiff("a\r\nb\r\n")).toBe("a\nb\n");
    expect(normalizeForDiff("a\nb")).toBe("a\nb\n");
    expect(normalizeForDiff("a\n\nb\n")).toBe("a\n\nb\n");
    expect(normalizeForDiff("\n")).toBe("\n");
  });

  it("AT_960_16_2 diffRowsFromParts：刪除行只有 A 行號、新增行只有 B 行號、相同行兩邊都有；行號自 1 起算且逐行遞增", () => {
    const rows = diffRowsFromParts([{ value: "a\nb\n" }, { value: "c\n", removed: true }, { value: "d\ne\n", added: true }, { value: "f\n" }]);
    expect(rows.map(({ kind, text, aLine, bLine }) => [kind, text, aLine, bLine])).toEqual([
      ["same", "a", 1, 1],
      ["same", "b", 2, 2],
      ["remove", "c", 3, null],
      ["add", "d", null, 3],
      ["add", "e", null, 4],
      ["same", "f", 4, 5],
    ]);
    expect(diffRowsFromParts([])).toEqual([]);
  });

  it("AT_960_16_2 隨機編輯（只做原地取代、插入、刪除，沒有搬移＝對齊唯一）：函式庫的逐行結果與確定性比對 diffLines 逐位相同；A→B 與 B→A 互為反向", async () => {
    const random = rng(20261103);
    for (let trial = 0; trial < 25; trial += 1) {
      const base = Array.from({ length: 30 + Math.floor(random() * 40) }, (_, i) => `第 ${i} 行 ${Math.floor(random() * 1e9).toString(36)}`);
      const edited: string[] = [];
      base.forEach((line, i) => {
        const roll = random();
        if (roll < 0.1) return; // 刪除
        edited.push(roll < 0.2 ? `${line} 改` : line); // 取代
        if (roll > 0.92) edited.push(`插入 ${trial}-${i}`); // 插入
      });
      const a = base.join("\n");
      const b = edited.join("\n");
      const forward = await computeDiffRows(a, b);
      expect(forward.engine, `trial ${trial}`).toBe("library");
      expect(forward.rows, `trial ${trial}：A→B`).toEqual(diffLines(a, b));
      const backward = await computeDiffRows(b, a);
      expect(backward.rows, `trial ${trial}：B→A`).toEqual(diffLines(b, a));
      expect(
        forward.rows
          .filter((r) => r.kind === "add")
          .map((r) => r.text)
          .sort(),
        `trial ${trial}`,
      ).toEqual(
        backward.rows
          .filter((r) => r.kind === "remove")
          .map((r) => r.text)
          .sort(),
      );
    }
  });

  it("AT_960_16_2 空輸入與單行：空對空沒有任何行、空對單行是單一 add、單行對空是單一 remove", async () => {
    expect((await computeDiffRows("", "")).rows).toEqual([]);
    expect((await computeDiffRows("", "只有一行")).rows).toEqual([{ kind: "add", text: "只有一行", aLine: null, bLine: 1 }]);
    expect((await computeDiffRows("只有一行", "")).rows).toEqual([{ kind: "remove", text: "只有一行", aLine: 1, bLine: null }]);
  });

  it("AT_960_16_2 編輯距離超過上限：函式庫放棄、退回確定性比對（整段刪除加整段新增），結果仍是合法的編輯序列且畫面照常顯示", async () => {
    const a = Array.from({ length: 2600 }, (_, i) => `甲 ${i}`).join("\n");
    const b = Array.from({ length: 2600 }, (_, i) => `乙 ${i}`).join("\n");
    const result = await computeDiffRows(a, b);
    expect(result.engine).toBe("fallback");
    expect(result.rows).toEqual(diffLines(a, b));
    expect(result.rows.filter((r) => r.kind === "remove")).toHaveLength(2600);
    expect(result.rows.filter((r) => r.kind === "add")).toHaveLength(2600);
    expect(result.rows.filter((r) => r.kind === "same")).toHaveLength(0);
  });

  it("AT_960_16_2 foldRows：變更行前後各 3 行照常顯示、更遠的相同行收成一列（不足兩行不收）；沒有變更全收；重疊的上下文合併；列數不超過門檻不收合", () => {
    const same = (n: number) => Array.from({ length: n }, (_, i) => ({ kind: "same" as const, text: `s${i}`, aLine: i + 1, bLine: i + 1 }));
    const change = { kind: "add" as const, text: "新", aLine: null, bLine: 99 };
    const kinds = (rows: ReturnType<typeof foldRows>) => rows.map((r) => (r.type === "row" ? (r.row.kind === "same" ? "s" : "c") : `fold${r.rows.length}`));
    const fold = (rows: Parameters<typeof foldRows>[0]) => foldRows(rows, { minRows: 0 });
    expect(DIFF_CONTEXT_LINES).toBe(3);
    expect(DIFF_FOLD_MIN_ROWS).toBe(200);
    expect(kinds(fold([...same(10), change, ...same(10)]))).toEqual(["fold7", "s", "s", "s", "c", "s", "s", "s", "fold7"]);
    expect(kinds(fold(same(10)))).toEqual(["fold10"]);
    expect(kinds(fold([]))).toEqual([]);
    // 兩個變更中間隔 6 行：上下文剛好接上，不收合
    expect(kinds(fold([change, ...same(6), change]))).toEqual(["c", "s", "s", "s", "s", "s", "s", "c"]);
    // 隔 8 行：中間只剩 2 行被隱藏→收成一列
    expect(kinds(fold([change, ...same(8), change]))).toEqual(["c", "s", "s", "s", "fold2", "s", "s", "s", "c"]);
    // 隔 7 行：只隱藏 1 行→不值得收，照常顯示
    expect(kinds(fold([change, ...same(7), change]))).toEqual(["c", "s", "s", "s", "s", "s", "s", "s", "c"]);
    expect(fold([...same(10), change, ...same(10)])[0]).toMatchObject({ type: "fold", from: 0 });
    // 門檻：剛好 DIFF_FOLD_MIN_ROWS 列不收合、多一列就收合
    const atLimit = [...same(DIFF_FOLD_MIN_ROWS - 1), change];
    expect(foldRows(atLimit).every((r) => r.type === "row")).toBe(true);
    expect(foldRows([...atLimit, ...same(1)]).some((r) => r.type === "fold")).toBe(true);
  });

  it("AT_960_16_2 不長的文件（逐行結果不超過門檻）全部展開、沒有收合列，逐行與確定性比對相同", async () => {
    const lines = Array.from({ length: 150 }, (_, i) => `段落 ${i}`);
    const a = lines.join("\n");
    const b = lines.map((l, i) => (i === 75 ? "改過的一行" : l)).join("\n");
    mount({ versions: VERSIONS.slice(0, 2), content: (n) => (n === 1 ? a : b) });
    await ready();
    expect(screen.queryAllByTestId("diff-fold")).toHaveLength(0);
    expect(shown()).toEqual(reference(a, b));
    expect(shown()).toHaveLength(151);
  });
  it("AT_960_16_2 大文件只改一處：畫面只有變更與上下文共 7 列加兩列收合；展開收合後逐行與確定性比對相同", async () => {
    const user = userEvent.setup();
    const lines = Array.from({ length: 300 }, (_, i) => `章節 ${i} 的內容`);
    const a = lines.join("\n");
    const b = lines.map((l, i) => (i === 150 ? "被改過的一行" : l)).join("\n");
    mount({ versions: VERSIONS.slice(0, 2), content: (n) => (n === 1 ? a : b) });
    await ready();
    expect(screen.getAllByTestId("diff-row")).toHaveLength(8); // 刪除 1＋新增 1＋上下文 6
    const folds = screen.getAllByTestId("diff-fold");
    expect(folds).toHaveLength(2);
    expect(folds[0]).toHaveTextContent("顯示其餘 147 行相同的內容");
    expect(folds[1]).toHaveTextContent("顯示其餘 146 行相同的內容");
    expect(screen.getByTestId("diff-summary")).toHaveTextContent("新增 1 行、刪除 1 行（相同的行共 299 行）");
    await user.click(within(folds[0]).getByRole("button"));
    expect(screen.getAllByTestId("diff-fold")).toHaveLength(1);
    expect(screen.getAllByTestId("diff-row")).toHaveLength(8 + 147);
    await user.click(within(screen.getByTestId("diff-fold")).getByRole("button"));
    expect(screen.queryAllByTestId("diff-fold")).toHaveLength(0);
    expect(shown()).toEqual(reference(a, b));
  });
});
