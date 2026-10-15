import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Highlights } from "./gateErrors";
import { toTree } from "./tree";
import { TreeEditor, type TreeEditorProps } from "./TreeEditor";

const tree = toTree({
  project: { name: "E2E 匯入專案", executionPath: "/e2e/proj-import", passCriteria: "三個目標全部完成", description: "由 BRD 匯入", autonomyLevel: 3 },
  goals: [
    {
      key: "g1",
      name: "基礎",
      description: "打好基礎",
      passCriteria: "基礎任務完成",
      dependsOn: [],
      tasks: [
        { name: "初始化", description: "請輸出 [T1_DONE]", passCriteria: "- [ ] 輸出含 [T1_DONE]", evaluatorCommand: "pytest -q", maxRetries: 2 },
        { name: "設定", description: "請輸出 [T2_DONE]", passCriteria: "輸出含 [T2_DONE]" },
      ],
    },
    {
      key: "g2",
      name: "核心",
      passCriteria: "核心任務完成",
      dependsOn: ["g1"],
      tasks: [{ name: "實作", description: "請輸出 [T3_DONE]", passCriteria: "輸出含 [T3_DONE]" }],
    },
  ],
});

function setup(overrides: Partial<TreeEditorProps> = {}) {
  const handlers = {
    onEditProject: vi.fn(),
    onAddGoal: vi.fn(),
    onEditGoal: vi.fn(),
    onDeleteGoal: vi.fn(),
    onAddTask: vi.fn(),
    onEditTask: vi.fn(),
    onDeleteTask: vi.fn(),
    onMoveGoal: vi.fn(),
    onMoveTask: vi.fn(),
  };
  render(<TreeEditor tree={tree} canEdit highlights={null} {...handlers} {...overrides} />);
  return handlers;
}

describe("三層樹預覽（US-I-03）", () => {
  it("專案 → 目標 → 任務逐層呈現，目標標示任務數、專案標示自治等級與執行路徑", () => {
    setup();
    expect(screen.getByTestId("project-name")).toHaveTextContent("E2E 匯入專案");
    expect(screen.getByTestId("tree-project")).toHaveTextContent("Lv.3");
    expect(screen.getByTestId("tree-project")).toHaveTextContent("/e2e/proj-import");
    const goals = screen.getAllByTestId("tree-goal");
    expect(goals).toHaveLength(2);
    expect(within(goals[0]).getByTestId("goal-name")).toHaveTextContent("基礎");
    expect(goals[0]).toHaveTextContent("目標 · 2 任務");
    expect(
      within(goals[0])
        .getAllByTestId("tree-task")
        .map((t) => within(t).getByTestId("task-name").textContent),
    ).toEqual(["初始化", "設定"]);
    expect(within(goals[1]).getAllByTestId("tree-task")).toHaveLength(1);
  });

  it("展開任務看說明與通過標準（含驗證命令與重試次數）；再按一次收合", async () => {
    setup();
    expect(screen.queryByTestId("task-details")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "展開詳情：初始化" }));
    const details = within(screen.getByTestId("task-details"));
    expect(details.getByText("請輸出 [T1_DONE]")).toBeInTheDocument();
    expect(details.getByText("輸出含 [T1_DONE]")).toBeInTheDocument(); // checklist 渲染
    expect(details.getByText("pytest -q")).toBeInTheDocument();
    expect(details.getByText("最大重試次數：2")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "收合詳情：初始化" }));
    expect(screen.queryByTestId("task-details")).toBeNull();
  });

  it("DEF-AC-001：maxRetries 為 null（真後端對 AI 解析的任務回 null，契約 §0.2 與缺席等價）時預覽不印「最大重試次數：null」", async () => {
    const withNull = toTree({
      project: { name: "p", executionPath: "/x", passCriteria: "c" },
      goals: [
        {
          key: "g1",
          name: "基礎",
          passCriteria: "c",
          tasks: [{ name: "初始化", description: "d", passCriteria: "c", maxRetries: null as unknown as number }],
        },
      ],
    });
    setup({ tree: withNull });
    await userEvent.click(screen.getByRole("button", { name: "展開詳情：初始化" }));
    const details = screen.getByTestId("task-details");
    expect(details).not.toHaveTextContent("最大重試次數");
    expect(details).not.toHaveTextContent("null");
  });

  it("展開目標看前置依賴（以目標名稱顯示，不露出 key）", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: "展開詳情：核心" }));
    const details = within(screen.getByTestId("goal-details"));
    expect(details.getByText("基礎")).toBeInTheDocument();
    expect(screen.getByTestId("goal-details")).not.toHaveTextContent("g1");
  });

  it("沒有名稱的節點顯示「（未命名）」並標紅字，方便找到要補的地方", () => {
    const blank = toTree({
      project: { name: "p", executionPath: "/x", passCriteria: "c" },
      goals: [{ key: "g1", name: "", passCriteria: "c", tasks: [{ name: "", description: "", passCriteria: "" }] }],
    });
    setup({ tree: blank });
    expect(screen.getByTestId("goal-name")).toHaveTextContent("（未命名）");
    expect(screen.getByTestId("task-name")).toHaveTextContent("（未命名）");
    expect(screen.getByTestId("task-name").className).toContain("text-wg-error");
  });
});

describe("編輯操作（US-I-04）：每個節點可編輯、刪除；目標可新增任務；樹尾可新增目標", () => {
  it("各按鈕回報對應的節點", async () => {
    const h = setup();
    await userEvent.click(screen.getByRole("button", { name: "編輯專案：E2E 匯入專案" }));
    expect(h.onEditProject).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole("button", { name: "編輯目標：核心" }));
    expect(h.onEditGoal).toHaveBeenCalledWith("g2");
    await userEvent.click(screen.getByRole("button", { name: "刪除目標：核心" }));
    expect(h.onDeleteGoal).toHaveBeenCalledWith("g2");
    await userEvent.click(screen.getByRole("button", { name: "編輯任務：設定" }));
    expect(h.onEditTask).toHaveBeenCalledWith("g1", tree.goals[0].tasks[1].uid);
    await userEvent.click(screen.getByRole("button", { name: "刪除任務：初始化" }));
    expect(h.onDeleteTask).toHaveBeenCalledWith("g1", tree.goals[0].tasks[0].uid);
    await userEvent.click(screen.getByRole("button", { name: "新增任務到目標：基礎" }));
    expect(h.onAddTask).toHaveBeenCalledWith("g1");
    await userEvent.click(screen.getByRole("button", { name: "新增目標" }));
    expect(h.onAddGoal).toHaveBeenCalledTimes(1);
  });

  it("兩個目標以上才有目標拖曳把手；同一目標有兩個以上任務才有任務拖曳把手", () => {
    setup();
    expect(screen.getByRole("button", { name: "拖曳排序：基礎" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "拖曳排序：初始化" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "拖曳排序：實作" })).toBeNull(); // g2 只有一個任務
  });

  it("契約要求至少 1 個目標、每個目標至少 1 個任務：最後一個不能刪", () => {
    const single = toTree({
      project: { name: "p", executionPath: "/x", passCriteria: "c" },
      goals: [{ key: "g1", name: "唯一目標", passCriteria: "c", tasks: [{ name: "唯一任務", description: "d", passCriteria: "c" }] }],
    });
    setup({ tree: single });
    expect(screen.getByRole("button", { name: "刪除目標：唯一目標" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "刪除任務：唯一任務" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: /拖曳排序/ })).toBeNull();
  });

  it("唯讀角色：只能看，沒有任何編輯、刪除、新增、拖曳控制項", () => {
    setup({ canEdit: false });
    for (const name of [/^編輯/, /^刪除/, /^新增/, /^拖曳排序/]) expect(screen.queryByRole("button", { name })).toBeNull();
    expect(screen.getAllByTestId("tree-task")).toHaveLength(3);
  });
});

describe("錯誤節點標紅（讓使用者知道要改哪裡）", () => {
  it("highlights 指到的專案、目標、任務帶 data-highlighted；其餘不帶", () => {
    const highlights: Highlights = { project: false, goals: new Set([1]), tasks: new Set(["0.1"]) };
    setup({ highlights });
    const goals = screen.getAllByTestId("tree-goal");
    expect(goals[0]).not.toHaveAttribute("data-highlighted");
    expect(goals[1]).toHaveAttribute("data-highlighted");
    const tasks = screen.getAllByTestId("tree-task");
    expect(tasks[0]).not.toHaveAttribute("data-highlighted");
    expect(tasks[1]).toHaveAttribute("data-highlighted");
    expect(screen.getByTestId("tree-project")).not.toHaveAttribute("data-highlighted");
  });
});
