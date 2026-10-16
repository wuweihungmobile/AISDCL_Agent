import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Dag } from "@/lib/api/types";
import type { TaskLive } from "@/lib/domain/runLive";
import { dag } from "@/tests/helpers/runFixtures";
import { DagCard } from "./DagCard";

/**
 * DAG 卡的「全螢幕」（契約 §4.2 E-22，v1.4，D-20；PRD §5.3.6 wireframe 的 `[展開/收合] [全螢幕]`；US-E-09；主控指定 D-01）。
 * 驗收（契約）＝開／關／Esc／焦點歸還的前端單元測試＋一支 e2e（點「全螢幕」→ DAG 容器尺寸等於視窗；jsdom 沒有版面，尺寸那條在 execute.mock.spec.ts）。
 */
type Props = { dag?: Dag; live?: Readonly<Record<string, TaskLive>>; loading?: boolean; error?: unknown };

const noop = () => undefined;

/** 沒傳 dag 用預設夾具；明確傳 `dag: undefined`＝還沒有 DAG（解構預設值會把 undefined 當成沒傳，所以用 in 判斷）。 */
function card(props: Props = {}) {
  const { live = {}, loading = false, error = null } = props;
  return <DagCard dag={"dag" in props ? props.dag : dag()} live={live} loading={loading} error={error} onRetry={noop} />;
}

const openButton = () => screen.getByTestId("dag-fullscreen-open");
const fullscreen = () => screen.getByRole("dialog", { name: "DAG 依賴視覺化" });
const gone = () => waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
/** 鍵盤開啟：按鈕先取得焦點再按 Enter，確認焦點已被搬進覆蓋層。 */
async function openByKeyboard(user: ReturnType<typeof userEvent.setup>) {
  openButton().focus();
  await user.keyboard("{Enter}");
  const dialog = await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });
  await waitFor(() => expect(dialog).toContainElement(document.activeElement as HTMLElement));
  return dialog;
}

describe("DAG 卡：全螢幕切換鈕", () => {
  it("標題列有「收合任務」與「全螢幕」兩顆鈕；預設不在全螢幕（aria-pressed=false、沒有覆蓋層）", () => {
    render(card());
    expect(screen.getByTestId("dag-toggle")).toHaveTextContent("收合任務");
    expect(openButton()).toHaveTextContent("全螢幕");
    expect(openButton()).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByTestId("dag-fullscreen")).toBeNull();
  });

  it.each([
    ["還沒有 DAG（尚未啟動執行）", { dag: undefined }],
    ["DAG 沒有任何目標", { dag: { runId: "r1", statusAsOf: "2026-10-15T08:30:12Z", nodes: [], edges: [] } satisfies Dag }],
  ])("%s：沒有可放大的圖，「全螢幕」與「收合任務」都不顯示", (_name, props) => {
    render(card(props));
    expect(screen.queryByTestId("dag-fullscreen-open")).toBeNull();
    expect(screen.queryByTestId("dag-toggle")).toBeNull();
    expect(screen.getByText("啟動執行後，這裡會顯示目標與任務的依賴關係與即時進度。")).toBeInTheDocument();
  });
});

describe("DAG 卡：進入全螢幕", () => {
  it("點「全螢幕」→ 頁面內覆蓋層（role=dialog，名稱「DAG 依賴視覺化」）；層內按鈕變「結束全螢幕」且 aria-pressed=true；焦點進入覆蓋層", async () => {
    const user = userEvent.setup();
    render(card());
    await user.click(openButton());
    const dialog = await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });
    expect(dialog).toHaveAttribute("data-testid", "dag-fullscreen");
    const exit = within(dialog).getByTestId("dag-fullscreen-exit");
    expect(exit).toHaveTextContent("結束全螢幕");
    expect(exit).toHaveAttribute("aria-pressed", "true");
    expect(within(dialog).getByRole("button", { name: "結束全螢幕" })).toBe(exit);
    await waitFor(() => expect(dialog).toContainElement(document.activeElement as HTMLElement));
  });

  it("覆蓋層鋪滿視窗：樣式把共用層白卡的置中、560px 寬、88vh 高上限、圓角與邊框都換掉（實際尺寸等於視窗由 e2e 量）", async () => {
    const user = userEvent.setup();
    render(card());
    await user.click(openButton());
    const dialog = await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });
    const classes = dialog.className.split(/\s+/);
    for (const wanted of ["fixed", "inset-0", "h-auto", "w-auto", "max-h-none", "max-w-none", "translate-x-0", "translate-y-0", "rounded-none", "border-0"]) {
      expect(classes, `覆蓋層應有 ${wanted}`).toContain(wanted);
    }
    // 被覆寫掉的白卡類別不得殘留（Tailwind 後者不一定贏——tailwind-merge 要真的把衝突的前者拿掉）
    for (const gone of ["top-1/2", "left-1/2", "-translate-x-1/2", "-translate-y-1/2", "w-[560px]", "max-h-[88vh]", "max-w-[calc(100%-48px)]", "rounded-lg", "border"]) {
      expect(classes, `白卡類別 ${gone} 應被覆寫掉`).not.toContain(gone);
    }
  });

  it("圖形只掛一份：全螢幕時節點在覆蓋層內、卡內換成不含節點的空位；任務節點與摘要的 testid 全域唯一", async () => {
    const user = userEvent.setup();
    render(card());
    expect(within(screen.getByTestId("dag-card")).getByTestId("dag-task-t1")).toBeInTheDocument();
    await user.click(openButton());
    const dialog = await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });
    expect(screen.getAllByTestId("dag-task-t1")).toHaveLength(1);
    expect(within(dialog).getByTestId("dag-task-t1")).toBeInTheDocument();
    expect(screen.getAllByTestId("dag-scroll")).toHaveLength(1);
    expect(screen.getAllByTestId("dag-summary")).toHaveLength(1);
    expect(within(screen.getByTestId("dag-card")).queryByTestId("dag-task-t1")).toBeNull();
    expect(screen.getByTestId("dag-placeholder")).toBeInTheDocument();
    expect(openButton()).toHaveAttribute("aria-pressed", "true"); // 卡上的鈕也同步（此時被 aria-hidden 隔開，只影響程式查詢）
  });

  it("全螢幕裡的圖形捲動區有名稱與鍵盤焦點（region＋tabindex=0），鍵盤使用者捲得動；卡內的那份維持原樣（不加 tabindex）", async () => {
    const user = userEvent.setup();
    render(card());
    expect(screen.getByTestId("dag-scroll")).not.toHaveAttribute("tabindex");
    expect(screen.getByTestId("dag-scroll")).not.toHaveAttribute("role");
    await user.click(openButton());
    const region = within(await screen.findByRole("dialog", { name: "DAG 依賴視覺化" })).getByRole("region", { name: "DAG 圖形（可用方向鍵捲動）" });
    expect(region).toBe(screen.getByTestId("dag-scroll"));
    expect(region).toHaveAttribute("tabindex", "0");
  });
});

describe("DAG 卡：離開全螢幕與焦點歸還（沿用共用層 Dialog 的 DEF-AC-011 機制）", () => {
  it.each([
    ["Esc", async (user: ReturnType<typeof userEvent.setup>) => user.keyboard("{Escape}")],
    ["「結束全螢幕」鈕", async (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByTestId("dag-fullscreen-exit"))],
    ["覆蓋層標題列的「關閉」鈕", async (user: ReturnType<typeof userEvent.setup>) => user.click(within(fullscreen()).getByRole("button", { name: "關閉" }))],
  ])("以鍵盤開啟、%s 結束 → 覆蓋層消失、圖形回到卡內、焦點回到「全螢幕」鈕", async (_name, close) => {
    const user = userEvent.setup();
    render(card());
    await openByKeyboard(user);
    await close(user);
    await gone();
    await waitFor(() => expect(openButton()).toHaveFocus());
    expect(openButton()).toHaveAttribute("aria-pressed", "false");
    expect(within(screen.getByTestId("dag-card")).getByTestId("dag-task-t1")).toBeInTheDocument();
    expect(screen.queryByTestId("dag-placeholder")).toBeNull();
  });

  it("以滑鼠點擊開啟、Esc 結束：焦點同樣回到「全螢幕」鈕", async () => {
    const user = userEvent.setup();
    render(card());
    await user.click(openButton());
    await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });
    await user.keyboard("{Escape}");
    await gone();
    await waitFor(() => expect(openButton()).toHaveFocus());
  });

  it("可重複進出：第二次開啟仍是同一個流程，焦點照樣歸還", async () => {
    const user = userEvent.setup();
    render(card());
    for (let i = 0; i < 2; i++) {
      await openByKeyboard(user);
      await user.keyboard("{Escape}");
      await gone();
      await waitFor(() => expect(openButton()).toHaveFocus());
    }
  });
});

describe("DAG 卡：全螢幕裡的展開／收合與即時更新", () => {
  const taskIds = ["t1", "t2", "t3"];

  it("全螢幕內也有「收合任務／展開任務」，可正常切換（只剩目標節點、按鈕文字與 aria-expanded 同步）", async () => {
    const user = userEvent.setup();
    render(card());
    await user.click(openButton());
    const dialog = await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });
    const toggle = within(dialog).getByTestId("dag-fs-toggle");
    expect(toggle).toHaveTextContent("收合任務");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    for (const id of taskIds) expect(within(dialog).getByTestId(`dag-task-${id}`)).toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveTextContent("展開任務");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    for (const id of taskIds) expect(screen.queryByTestId(`dag-task-${id}`)).toBeNull();
    expect(within(dialog).getByTestId("dag-goal-g1")).toBeInTheDocument(); // 目標節點還在

    await user.click(toggle);
    for (const id of taskIds) expect(within(dialog).getByTestId(`dag-task-${id}`)).toBeInTheDocument();
  });

  it("展開／收合狀態進出全螢幕都保留：全螢幕裡收合 → 結束後卡內仍是收合；卡內收合 → 進全螢幕仍是收合", async () => {
    const user = userEvent.setup();
    render(card());
    await user.click(openButton());
    await user.click(await screen.findByTestId("dag-fs-toggle")); // 全螢幕內收合
    await user.keyboard("{Escape}");
    await gone();
    expect(screen.getByTestId("dag-toggle")).toHaveTextContent("展開任務");
    expect(screen.queryByTestId("dag-task-t1")).toBeNull();
    expect(screen.getByTestId("dag-goal-g1")).toBeInTheDocument();

    await user.click(openButton()); // 卡內已是收合：再進全螢幕仍收合
    const dialog = await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });
    expect(within(dialog).getByTestId("dag-fs-toggle")).toHaveTextContent("展開任務");
    expect(within(dialog).queryByTestId("dag-task-t1")).toBeNull();
  });

  it("SSE 疊上來的任務狀態在全螢幕期間照常更新節點（t2 進行中 → 完成）；結束後卡內是最新狀態", async () => {
    const user = userEvent.setup();
    const { rerender } = render(card({ live: { t2: { status: "RUNNING", seq: 5 } } }));
    await user.click(openButton());
    const dialog = await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });
    expect(within(dialog).getByTestId("dag-task-t2")).toHaveAttribute("data-tone", "active");
    expect(within(dialog).getByTestId("dag-task-t3")).toHaveAttribute("data-tone", "pending");

    rerender(card({ live: { t2: { status: "COMPLETED", seq: 9 }, t3: { status: "RUNNING", seq: 10 } } }));
    expect(within(dialog).getByTestId("dag-task-t2")).toHaveAttribute("data-tone", "done");
    expect(within(dialog).getByTestId("dag-task-t3")).toHaveAttribute("data-tone", "active");

    await user.keyboard("{Escape}");
    await gone();
    expect(within(screen.getByTestId("dag-card")).getByTestId("dag-task-t2")).toHaveAttribute("data-tone", "done");
  });

  it("全螢幕期間圖形資料消失（例如切到沒有 DAG 的批次）：覆蓋層不自己關、顯示空狀態，仍可結束；之後有資料也不會自己又彈出來", async () => {
    const user = userEvent.setup();
    const { rerender } = render(card());
    await user.click(openButton());
    await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });

    rerender(card({ dag: undefined }));
    const dialog = screen.getByRole("dialog", { name: "DAG 依賴視覺化" });
    expect(within(dialog).getByText("啟動執行後，這裡會顯示目標與任務的依賴關係與即時進度。")).toBeInTheDocument();
    expect(within(dialog).queryByTestId("dag-fs-toggle")).toBeNull(); // 沒有圖就沒有展開／收合
    await user.click(within(dialog).getByTestId("dag-fullscreen-exit"));
    await gone();

    rerender(card()); // 結束後新批次的圖到了：停在卡內，不會自動再進全螢幕
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByTestId("dag-task-t1")).toBeInTheDocument();
  });

  it("全螢幕期間 DAG 載入失敗：覆蓋層內顯示錯誤與重試，可重試也可結束", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const { rerender } = render(<DagCard dag={dag()} live={{}} loading={false} error={null} onRetry={onRetry} />);
    await user.click(openButton());
    await screen.findByRole("dialog", { name: "DAG 依賴視覺化" });
    rerender(<DagCard dag={dag()} live={{}} loading={false} error={new Error("boom")} onRetry={onRetry} />);
    const dialog = screen.getByRole("dialog", { name: "DAG 依賴視覺化" });
    await user.click(within(dialog).getByRole("button", { name: /重試/ }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    await user.keyboard("{Escape}");
    await gone();
  });
});
