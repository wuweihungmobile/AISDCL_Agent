/**
 * IssueLegend 的元件測試（TCS-IssueCenter-20261027 AT-IC-08-2-1、AT-IC-08-2-E-1；R-IC-63）：
 * 「狀態說明」對話框的每一句說明都逐字取自清單回應的 `legend`——圖例換字、這裡跟著換；`updatedAtNote` 缺席就不顯示（不寫死）。
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { IssueLegend as Legend } from "@/lib/api/types";
import { IssueLegend } from "./IssueLegend";
import { LEGEND, clone } from "./tests/issues.fixtures";

const dialog = () => screen.getByRole("dialog", { name: "狀態說明" });
const group = (testId: string) => within(dialog()).getByTestId(testId);

/** 把每個 meaning 換成「哨兵＋序號」的字串（逐一不同，才分得出各行用的是自己的那一句）；註記換成註記哨兵。 */
function sentinelLegend(): Legend {
  let n = 0;
  const swap = <T extends { meaning: string }>(rows: T[]): T[] => rows.map((r) => ({ ...r, meaning: `§哨兵${(n += 1)}§` }));
  const legend = clone(LEGEND);
  return { ...legend, statuses: swap(legend.statuses), results: swap(legend.results), sources: swap(legend.sources), severities: swap(legend.severities), updatedAtNote: "§註記哨兵§" };
}

/** 回應沒帶 `updatedAtNote` 這個鍵。 */
function withoutNote(legend: Legend): Legend {
  return Object.fromEntries(Object.entries(legend).filter(([key]) => key !== "updatedAtNote")) as unknown as Legend;
}

describe("AT_IC_08_2_1 狀態說明對話框由 legend 渲染", () => {
  it("AT_IC_08_2_1 七狀態、八結果、四來源、四嚴重度各一行（名稱加說明逐字取自 legend），updatedAtNote 同在其中", () => {
    render(<IssueLegend legend={LEGEND} open onClose={() => undefined} />);
    const expectations: Array<[string, ReadonlyArray<{ name: string; meaning: string }>]> = [
      ["issues-legend-statuses", LEGEND.statuses],
      ["issues-legend-results", LEGEND.results],
      ["issues-legend-sources", LEGEND.sources],
      ["issues-legend-severities", LEGEND.severities],
    ];
    expect(expectations.map(([, rows]) => rows.length)).toEqual([7, 8, 4, 4]);
    for (const [testId, rows] of expectations) {
      const terms = Array.from(group(testId).querySelectorAll("dt")).map((el) => el.textContent);
      const meanings = Array.from(group(testId).querySelectorAll("dd")).map((el) => el.textContent);
      expect(terms, testId).toEqual(rows.map((r) => r.name));
      expect(meanings, testId).toEqual(rows.map((r) => r.meaning));
    }
    expect(LEGEND.updatedAtNote).toContain("最後已知動靜");
    expect(within(dialog()).getByTestId("issues-legend-note")).toHaveTextContent(LEGEND.updatedAtNote);
    // 四個分組標題
    expect(
      within(dialog())
        .getAllByRole("heading", { level: 3 })
        .map((h) => h.textContent),
    ).toEqual(["狀態", "結果", "來源", "嚴重度"]);
  });

  it("沒開、或圖例還沒載入時不渲染對話框；Esc 關閉呼叫 onClose", async () => {
    const onClose = vi.fn();
    const view = render(<IssueLegend legend={LEGEND} open={false} onClose={onClose} />);
    expect(screen.queryByRole("dialog")).toBeNull();
    view.rerender(<IssueLegend legend={undefined} open onClose={onClose} />);
    expect(screen.queryByRole("dialog")).toBeNull();
    view.rerender(<IssueLegend legend={LEGEND} open onClose={onClose} />);
    expect(dialog()).toBeInTheDocument();
    await userEvent.setup().keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("AT_IC_08_2_E_1 圖例換字、缺註記", () => {
  it("AT_IC_08_2_E_1 每個 meaning 換成哨兵字串：對話框只顯示哨兵（標題、分組標題與名稱之外沒有第二份說明文字）", () => {
    const legend = sentinelLegend();
    render(<IssueLegend legend={legend} open onClose={() => undefined} />);
    const text = dialog().textContent ?? "";
    const sentinels = text.match(/§哨兵\d+§/g) ?? [];
    expect(sentinels).toHaveLength(23);
    expect(new Set(sentinels).size).toBe(23);
    expect(text).toContain("§註記哨兵§");
    // 扣掉標題、分組標題、各項名稱、哨兵之後不得剩下任何字
    const names = [...legend.statuses, ...legend.results, ...legend.sources, ...legend.severities].map((r) => r.name);
    let rest = text.replace(/§哨兵\d+§/g, "").replace("§註記哨兵§", "");
    for (const word of ["狀態說明", "狀態", "結果", "來源", "嚴重度", ...names].sort((a, b) => b.length - a.length)) rest = rest.split(word).join("");
    expect(rest).toBe("");
    // 原本的說明文字一句都不在
    for (const row of [...LEGEND.statuses, ...LEGEND.results, ...LEGEND.sources, ...LEGEND.severities]) expect(text).not.toContain(row.meaning);
    expect(text).not.toContain(LEGEND.updatedAtNote);
  });

  it("AT_IC_08_2_E_1 legend 缺 updatedAtNote（鍵不在、或為空字串）時不出現註記（不寫死「最後已知動靜」）", () => {
    for (const legend of [withoutNote(clone(LEGEND)), { ...clone(LEGEND), updatedAtNote: "" }]) {
      const view = render(<IssueLegend legend={legend} open onClose={() => undefined} />);
      expect(screen.queryByTestId("issues-legend-note")).toBeNull();
      expect(dialog().textContent).not.toContain("最後已知動靜");
      view.unmount();
    }
  });
});
