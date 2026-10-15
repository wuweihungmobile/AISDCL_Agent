import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import { parseFailureFromError, parseFailureFromRecord } from "./gateErrors";
import { ParseFailurePanel, ParseWarnings, StepHeader } from "./parts";

const apiError = (init: Record<string, unknown>) => new ApiError(init as unknown as ConstructorParameters<typeof ApiError>[0]);

/** 契約 §5 E2E-01 的有界閘變體：三條違規（空 prompt、步驟超限、成環）。 */
const THREE_GATES = [
  { field: "goals[0].tasks[3].description", message: "x", gate: "empty_prompt", detail: "任務「（未命名）」的描述為空（goals[0].tasks[3]）", location: "goals[0].tasks[3].description" },
  { field: "goals[0].tasks", message: "y", gate: "max_steps", detail: "目標「建立基礎架構」的任務數 25 超過上限 24（不截斷、不修剪）", location: "goals[0].tasks" },
  { field: "goals[1].dependsOn", message: "z", gate: "cycle", detail: "目標依賴成環：基礎 -> 核心 -> 基礎", location: "goals[1].dependsOn" },
];

describe("有界閘錯誤呈現（US-I-10：完整列出、不截斷）", () => {
  it("給 3 條 errors：三條全部顯示，各帶閘別、位置與完整原因，順序與後端回報一致", () => {
    const failure = parseFailureFromError(
      apiError({ status: 422, message: "解析結果未通過有界閘", reason: REASONS.IMPORT_GATE_REJECTED, errors: THREE_GATES, traceId: "tr-422" }),
    );
    render(<ParseFailurePanel failure={failure} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByTestId("parse-failure-title")).toHaveTextContent("解析結果未通過有界閘（共 3 項）");
    const rows = screen.getAllByTestId("gate-error-row");
    expect(rows).toHaveLength(3);

    const expected: Array<[string, string, string]> = [
      ["empty_prompt", "goals[0].tasks[3].description", "任務「（未命名）」的描述為空（goals[0].tasks[3]）"],
      ["max_steps", "goals[0].tasks", "目標「建立基礎架構」的任務數 25 超過上限 24（不截斷、不修剪）"],
      ["cycle", "goals[1].dependsOn", "目標依賴成環：基礎 -> 核心 -> 基礎"],
    ];
    rows.forEach((row, i) => {
      const [gate, location, detail] = expected[i];
      expect(within(row).getByText(gate)).toBeInTheDocument(); // 閘別逐字常數
      expect(within(row).getByTestId("gate-error-location")).toHaveTextContent(location);
      expect(within(row).getByTestId("gate-error-detail")).toHaveTextContent(detail); // 全文
    });
    // 閘別徽章有中文說明
    expect(within(rows[1]).getByTestId("gate-error-gate")).toHaveTextContent("步驟上限（≤ 24）");
    expect(screen.getByText("traceId：tr-422")).toBeInTheDocument();
  });

  it("很長的原因也全文顯示：沒有 truncate／line-clamp，也沒有被「…」縮短", () => {
    const long = `任務「實作」的 prompt 長度 23412 超過上限 20000${"，請拆成較小的任務並重述需求".repeat(40)}`;
    const failure = parseFailureFromError(
      apiError({
        status: 422,
        message: "m",
        reason: REASONS.IMPORT_GATE_REJECTED,
        errors: [{ field: "goals[0].tasks[0]", message: "m", gate: "prompt_too_long", detail: long, location: "goals[0].tasks[0]" }],
      }),
    );
    render(<ParseFailurePanel failure={failure} />);
    const detail = screen.getByTestId("gate-error-detail");
    expect(detail.textContent).toBe(long);
    expect(detail.className).not.toMatch(/truncate|line-clamp|overflow-hidden/);
    expect(detail.className).toContain("break-words");
  });

  it("20 條違規一條不少（清單沒有列數上限）", () => {
    const errors = Array.from({ length: 20 }, (_, i) => ({
      field: `goals[${i}].tasks`,
      message: "m",
      gate: "max_steps",
      detail: `目標 ${i} 的任務數 25 超過上限 24`,
      location: `goals[${i}].tasks`,
    }));
    render(
      <ParseFailurePanel
        failure={parseFailureFromError(apiError({ status: 422, message: "m", reason: REASONS.IMPORT_GATE_REJECTED, errors }))}
      />,
    );
    expect(screen.getAllByTestId("gate-error-row")).toHaveLength(20);
    expect(screen.getByTestId("parse-failure-title")).toHaveTextContent("（共 20 項）");
  });

  it("重新整理後以 lastParseErrors 還原的清單與當場 422 長得一樣", () => {
    const failure = parseFailureFromRecord([
      { gate: "empty_prompt", detail: "任務「A」的描述為空", location: "goals[0].tasks[0].description" },
      { gate: "cycle", detail: "目標依賴成環：A -> B -> A", location: "goals[1].dependsOn" },
    ]);
    render(<ParseFailurePanel failure={failure!} />);
    expect(screen.getAllByTestId("gate-error-row")).toHaveLength(2);
    expect(screen.getByText("目標依賴成環：A -> B -> A")).toBeInTheDocument();
  });

  it("沒有逐項清單的失敗（SDD 規格被拒）：顯示標題與 Bridge 的原因說明", () => {
    const failure = parseFailureFromError(
      apiError({
        status: 422,
        message: "SDD 規格未凍結",
        reason: REASONS.IMPORT_SDD_SPEC_REJECTED,
        errors: [],
        details: { bridgeReason: "spec_not_frozen", detail: "請先完成凍結" },
      }),
    );
    render(<ParseFailurePanel failure={failure} />);
    expect(screen.getByTestId("parse-failure-title")).toHaveTextContent("SDD 規格檢查未通過");
    expect(screen.getByText("引擎回報：spec_not_frozen")).toBeInTheDocument();
    expect(screen.queryByTestId("gate-error-list")).toBeNull();
  });
});

describe("解析提示與步驟標題", () => {
  it("warnings 逐項列出，已知 code 有中文說明、未知 code 退回原字串；沒有 warnings 就不渲染", () => {
    const { rerender } = render(
      <ParseWarnings
        warnings={[
          { code: "passcriteria_placeholder", detail: "通過標準為佔位字串", location: "goals[0].tasks[1]" },
          { code: "evaluator_command_dropped", detail: "含禁用字元 ;", location: "goals[0].tasks[2]" },
          { code: "future_code", detail: "未知" },
        ]}
      />,
    );
    const rows = screen.getAllByTestId("parse-warning");
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent("通過標準是佔位字串，signoff 前請補齊");
    expect(rows[1]).toHaveTextContent("驗證命令含禁用字元，已被清空");
    expect(rows[2]).toHaveTextContent("future_code");
    rerender(<ParseWarnings warnings={[]} />);
    expect(screen.queryByTestId("parse-warnings")).toBeNull();
  });

  it("StepHeader：步驟號與標題", () => {
    render(<StepHeader step={2} title="結構預覽與編輯" />);
    expect(screen.getByRole("heading", { name: "結構預覽與編輯" })).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
