import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { ColumnChart, RatioChart, StatusBars } from "./SimpleCharts";
import { TokenTrendChart } from "./TokenTrendChart";

/**
 * 圖表裡的列表用「標籤」當 key 會出事：兩個任務同名（執行時間分佈取任務名稱當標籤）、
 * 或時間範圍剛切換、查詢還留著上一份資料時，不同時間點被標成同一個日期（例如 6 個整點在「日」粒度下全是 10/15）。
 * 重複的 key 讓 React 警告並可能讓列表項互相取代——這裡確認重複標籤時每一項都還在、且沒有警告。
 */
let errors: MockInstance<typeof console.error>;
beforeEach(() => {
  errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
});
afterEach(() => errors.mockRestore());

const duplicateKeyWarnings = () => errors.mock.calls.filter((call) => String(call[0]).includes("same key"));

describe("圖表列表的 key：標籤重複時每一項都還在、沒有重複 key 警告", () => {
  it("ColumnChart：兩個任務同名（同標籤）→ 兩根柱子都畫出來，螢幕閱讀器清單也各一行", () => {
    render(
      <ColumnChart
        columns={[
          { label: "測試", value: 90, heightPct: 100, highlight: true },
          { label: "測試", value: 30, heightPct: 33, highlight: false },
        ]}
        formatValue={(v) => `${v}s`}
        ariaLabel="執行時間分佈圖"
        testId="duration-chart"
      />,
    );
    expect(screen.getAllByTestId("duration-chart-col")).toHaveLength(2);
    expect(document.querySelectorAll("ul.sr-only li")).toHaveLength(2);
    expect(duplicateKeyWarnings()).toHaveLength(0);
  });

  it("RatioChart：不同時間桶被標成同一個標籤 → 每個桶一根堆疊柱", () => {
    render(
      <RatioChart
        rows={[
          { label: "10/15", success: 100, failure: 0, total: 2 },
          { label: "10/15", success: 50, failure: 50, total: 2 },
          { label: "10/15", success: 0, failure: 100, total: 1 },
        ]}
      />,
    );
    expect(screen.getAllByTestId("ratio-col")).toHaveLength(3);
    expect(document.querySelectorAll("ul.sr-only li")).toHaveLength(3);
    expect(duplicateKeyWarnings()).toHaveLength(0);
  });

  it("TokenTrendChart：切換範圍的瞬間（保留上一份資料）多個時間點同標籤 → 螢幕閱讀器清單逐點列出", () => {
    const rows = [0, 1, 2].map((i) => ({ time: "10/15", used: (i + 1) * 1000, tokens: 1000, budget: 100000 }));
    render(<TokenTrendChart rows={rows} />);
    expect(document.querySelectorAll("ul.sr-only li")).toHaveLength(3);
    expect(screen.getByRole("img", { name: /Token 使用趨勢圖：3 個時間點，最新累計 3,000 Token，預算 100,000/ })).toBeInTheDocument();
    expect(duplicateKeyWarnings()).toHaveLength(0);
  });

  it("StatusBars：四條 bar 以狀態群組 id 當 key，各自標示數量", () => {
    render(
      <StatusBars
        rows={[
          { id: "done", label: "完成", count: 4 },
          { id: "running", label: "執行中", count: 2 },
          { id: "failed", label: "失敗", count: 1 },
          { id: "pending", label: "待處理", count: 0 },
        ]}
      />,
    );
    expect(screen.getByTestId("status-bar-done")).toHaveTextContent("完成 (4)");
    expect(screen.getByTestId("status-bar-pending")).toHaveTextContent("待處理 (0)");
    expect(screen.getByRole("img", { name: "任務狀態分佈：完成 4、執行中 2、失敗 1、待處理 0" })).toBeInTheDocument();
  });
});
