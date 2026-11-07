import { render, screen, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import type { ResearchTraceRow, ResearchTraceability } from "@/lib/api/types";
import { DELIVER_LABEL } from "@/lib/domain/research";
import { TRACEABILITY } from "@/tests/fixtures/research/p2";
import { TRACE_STATUS_TEXT, TraceabilityTable, uncoveredRows } from "./TraceabilityTable";

/**
 * 追溯表（TCS-ResearchToPRD-P2-20261107 AT-962-17-8、21-E-2；AC-R2P-20-1、20-2）：一 AC 一列、非 PASS 標紅且有文字、「未覆蓋 n」＝totals.uncovered、摘要純文字、表格有可及名稱。
 * 判定指令：npx vitest run components/domain/research/TraceabilityTable.test.tsx -t "<AT 底線形>"
 */
const row = (patch: Partial<ResearchTraceRow> & Pick<ResearchTraceRow, "ac">): ResearchTraceRow => ({
  userStory: "US-09",
  gherkinSummary: { given: "a", when: "b", then: "c" },
  unitStatus: "PASS",
  e2eStatus: "NOT_RUN",
  lastRunAt: "2026-11-07T10:00:00+08:00",
  source: ["task:t9", "RTM-COVERAGE-demo.yaml"],
  ...patch,
});

/** 夾具：PASS、FAIL、NOT_RUN、NONE 各一，另含一列摘要夾 `<script>` 的 PASS。 */
const FIXTURE: ResearchTraceability = {
  rows: [
    row({ ac: "AC-R2P-01-1" }),
    row({ ac: "AC-R2P-01-2", unitStatus: "FAIL" }),
    row({ ac: "AC-R2P-01-3", unitStatus: "NOT_RUN", lastRunAt: null }),
    row({ ac: "AC-R2P-01-4", unitStatus: "NONE", lastRunAt: null, source: [] }),
    row({ ac: "AC-R2P-01-5", gherkinSummary: { given: "<script>window.__pwned=1</script>", when: "x", then: "y" } }),
  ],
  totals: { acTotal: 5, covered: 2, uncovered: 3, frTotal: 2 },
  rtm: { runId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", fullyCovered: false, acPct: 40, advisory: true },
  generatedAt: "2026-11-07T10:00:00+08:00",
};

describe("AT_962_17_8 追溯表呈現：一 AC 一列、紅標、未覆蓋計數、摘要純文字、可及名稱", () => {
  it("AT_962_17_8 列數等於 acTotal；每列的 AC 與 rows 逐一對應", () => {
    render(<TraceabilityTable data={FIXTURE} />);
    const rows = screen.getAllByTestId("trace-row");
    expect(rows).toHaveLength(FIXTURE.totals.acTotal);
    expect(rows.map((r) => r.getAttribute("data-ac"))).toEqual(FIXTURE.rows.map((r) => r.ac));
  });

  it("AT_962_17_8 非 PASS 列標紅（data-red）且單元欄有文字標記：失敗、未執行、無覆蓋任務；PASS 列不紅", () => {
    render(<TraceabilityTable data={FIXTURE} />);
    const byAc = (ac: string) => screen.getAllByTestId("trace-row").find((r) => r.getAttribute("data-ac") === ac) as HTMLElement;
    const expected: Array<[string, string, string]> = [
      ["AC-R2P-01-1", "false", TRACE_STATUS_TEXT.PASS],
      ["AC-R2P-01-2", "true", "失敗"],
      ["AC-R2P-01-3", "true", "未執行"],
      ["AC-R2P-01-4", "true", "無覆蓋任務"],
      ["AC-R2P-01-5", "false", TRACE_STATUS_TEXT.PASS],
    ];
    for (const [ac, red, text] of expected) {
      const tr = byAc(ac);
      expect(tr, ac).toHaveAttribute("data-red", red);
      expect(within(tr).getByTestId("trace-unit"), ac).toHaveTextContent(text);
    }
  });

  it("AT_962_17_8 「未覆蓋 n」＝totals.uncovered（只算單元欄；端對端欄的「未執行」不計入）", () => {
    render(<TraceabilityTable data={FIXTURE} />);
    expect(screen.getByTestId("trace-uncovered")).toHaveTextContent(`${DELIVER_LABEL.uncovered} 3`);
    expect(screen.getByTestId("trace-uncovered")).toHaveAttribute("data-count", "3");
    // 五列的端對端欄全是「未執行」，但紅列只有單元欄非 PASS 的三列
    expect(screen.getAllByTestId("trace-e2e").every((cell) => cell.textContent === "未執行")).toBe(true);
    expect(screen.getAllByTestId("trace-row").filter((r) => r.getAttribute("data-red") === "true")).toHaveLength(3);
    expect(uncoveredRows(FIXTURE.rows).map((r) => r.ac)).toEqual(["AC-R2P-01-2", "AC-R2P-01-3", "AC-R2P-01-4"]);
  });

  it("AT_962_17_8 摘要為純文字：<script> 以文字顯示、不產生 script 元素、不執行", () => {
    const { container } = render(<TraceabilityTable data={FIXTURE} />);
    expect(container.querySelector("script")).toBeNull();
    expect(container).toHaveTextContent("<script>window.__pwned=1</script>");
    expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
  });

  it("AT_962_17_8 表格有可及名稱：table 的 aria-label、欄標頭 scope=col、每列以 AC 當 scope=row 的列標頭；RTM 彙總帶「諮詢」標記", () => {
    render(<TraceabilityTable data={FIXTURE} />);
    const table = screen.getByRole("table", { name: /追溯表/ });
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["AC", "使用者故事", "Gherkin 摘要", "單元狀態", "端對端狀態", "最近執行", "來源"]);
    expect(
      within(table)
        .getAllByRole("rowheader")
        .map((h) => h.textContent),
    ).toEqual(FIXTURE.rows.map((r) => r.ac));
    expect(screen.getByTestId("trace-rtm")).toHaveTextContent("諮詢");
    expect(screen.getByTestId("trace-rtm")).toHaveTextContent("40%");
  });

  it("AT_962_17_8 Gherkin 摘要渲染三段（Given／When／Then 標籤各一段，純文字）；來源渲染為清單，無覆蓋任務時顯示「無」（D-158）", () => {
    render(<TraceabilityTable data={FIXTURE} />);
    const first = screen.getAllByTestId("trace-row")[0];
    expect(within(first).getByTestId("trace-gherkin-given")).toHaveTextContent("Given a");
    expect(within(first).getByTestId("trace-gherkin-when")).toHaveTextContent("When b");
    expect(within(first).getByTestId("trace-gherkin-then")).toHaveTextContent("Then c");
    expect(
      within(within(first).getByTestId("trace-source"))
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["task:t9", "RTM-COVERAGE-demo.yaml"]);
    const none = screen.getAllByTestId("trace-row")[3];
    expect(within(none).getByTestId("trace-source")).toHaveTextContent("無");
    expect(within(none).queryAllByRole("listitem")).toHaveLength(0);
    // 缺段（空字串）仍顯示標籤，不崩潰
    render(
      <TraceabilityTable data={{ ...FIXTURE, rows: [row({ ac: "AC-X-1", gherkinSummary: { given: "g", when: "", then: "" } })], totals: { acTotal: 1, covered: 1, uncovered: 0, frTotal: 1 } }} />,
    );
    expect(screen.getAllByTestId("trace-gherkin-when").at(-1)).toHaveTextContent("When");
  });

  it("AT_962_17_8 黃金夾具 TRACEABILITY 渲染：三列、未覆蓋 2；rtm 為 null 時顯示「尚無 RTM 彙總」", () => {
    const { rerender } = render(<TraceabilityTable data={TRACEABILITY} />);
    expect(screen.getAllByTestId("trace-row")).toHaveLength(3);
    expect(screen.getByTestId("trace-uncovered")).toHaveTextContent("未覆蓋 2");
    rerender(<TraceabilityTable data={{ ...TRACEABILITY, rtm: null }} />);
    expect(screen.getByTestId("trace-rtm-none")).toBeInTheDocument();
    expect(screen.queryByTestId("trace-rtm")).toBeNull();
  });
});

describe("AT_962_21_E_2 純文字渲染：摘要含 HTML 不執行", () => {
  const HOSTILE: ResearchTraceability = {
    ...FIXTURE,
    rows: [
      row({
        ac: "AC-R2P-09-1",
        gherkinSummary: { given: `<img src=x onerror="window.__pwned2=1">`, when: `<script>window.__pwned2=1</script>`, then: "y" },
        userStory: `<img src=y onerror="window.__pwned2=1">`,
        source: [`<a href="javascript:alert(1)" onclick="x()">src</a>`],
      }),
    ],
    totals: { acTotal: 1, covered: 1, uncovered: 0, frTotal: 1 },
  };

  it("AT_962_21_E_2 無 img 元素、無 on* 屬性、無 javascript: 連結；HTML 字樣原樣顯示為文字", () => {
    const { container } = render(<TraceabilityTable data={HOSTILE} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("a")).toBeNull();
    const withOn = [...container.querySelectorAll("*")].filter((el) => el.getAttributeNames().some((name) => name.toLowerCase().startsWith("on")));
    expect(withOn).toHaveLength(0);
    expect(container).toHaveTextContent('<img src=x onerror="window.__pwned2=1">');
    expect((window as unknown as { __pwned2?: number }).__pwned2).toBeUndefined();
  });

  it("AT_962_21_E_2 原始碼沒有 dangerouslySetInnerHTML（負控：掃描函式抓得到）", () => {
    const code = readFileSync(path.join(process.cwd(), "components/domain/research/TraceabilityTable.tsx"), "utf8");
    expect(code.length).toBeGreaterThan(500);
    expect(code.replace(/\/\*[\s\S]*?\*\//g, "")).not.toContain("dangerouslySetInnerHTML");
    expect("<div dangerouslySetInnerHTML={x} />").toContain("dangerouslySetInnerHTML");
  });
});
