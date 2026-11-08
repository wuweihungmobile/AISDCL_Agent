/**
 * 自癒監視器（TCS-ResearchToPRD-P2-20261107 AT-962-12-1～12-5、12-E-1～12-E-3）：嘗試次數對上限、純文字、升級連到決策彈窗、規格漂移預填 SCR、日誌落後、空狀態、VIEWER、長摘錄版面。
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import type { ResearchHealing, ResearchHealingRow } from "@/lib/api/types";
import { R3 } from "@/tests/fixtures/research/ids";
import { HEALING, PENDING_ESCALATED, RUN_ID, kanbanPending } from "@/tests/fixtures/research/p2";
import { renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { HealingMonitor } from "./HealingMonitor";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useParams: () => ({}),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const row = (patch: Partial<ResearchHealingRow>): ResearchHealingRow => ({ ...HEALING.rows[0], ...patch });
const withRows = (rows: ResearchHealingRow[], extra: Partial<ResearchHealing> = {}): ResearchHealing => ({ ...HEALING, rows, ...extra });

async function mount(healing: ResearchHealing = HEALING, role: "ADMIN" | "OPERATOR" | "VIEWER" = "OPERATOR", kanban?: Parameters<typeof stubResearchApi>[0]) {
  const stub = stubResearchApi({ healing, ...kanban });
  const view = renderResearch(<HealingMonitor researchId={R3} />, role);
  await screen.findByTestId("healing-monitor");
  return { ...stub, ...view };
}

describe("自癒監視器", () => {
  it("AT_962_12_1 每任務顯示嘗試 n／上限（上限取 maxRetries）、純文字摘錄；歸因與補丁結果為 null 時顯示引擎未提供", async () => {
    await mount();
    const rows = screen.getAllByTestId("healing-row");
    expect(rows.map((r) => r.getAttribute("data-task"))).toEqual(["task-3", "task-7"]);
    expect(within(rows[0]).getByTestId("healing-attempt").textContent).toBe("嘗試 2／3"); // 兩列合併：最近一次嘗試
    expect(within(rows[1]).getByTestId("healing-attempt").textContent).toBe("嘗試 3／3");
    expect(within(rows[0]).getByTestId("healing-excerpt").textContent).toBe("AssertionError: expected 3 got 5");
    expect(within(rows[0]).getByTestId("healing-attribution").textContent).toBe("歸因：引擎未提供");
    expect(within(rows[0]).getByTestId("healing-patch").textContent).toBe("補丁結果：引擎未提供");
  });

  it("AT_962_12_1 上限取資料：maxRetries=5 時顯示 嘗試 n／5", async () => {
    await mount(withRows([row({ attempt: 4 })], { maxRetries: 5 }));
    expect(screen.getByTestId("healing-attempt").textContent).toBe("嘗試 4／5");
  });

  it("AT_962_12_2 摘錄含 HTML 與 on* 屬性：容器內 script 與 img 為 0、無 on* 屬性、哨兵呼叫 0", async () => {
    const sentinel = vi.fn();
    (window as unknown as Record<string, unknown>).__sentinel = sentinel;
    const { container } = await mount(withRows([row({ excerpt: '<script>__sentinel()</script><img src=x onerror="__sentinel()">' })]));
    expect(container.querySelectorAll("script, img")).toHaveLength(0);
    expect([...container.querySelectorAll("*")].filter((el) => [...el.attributes].some((a) => a.name.startsWith("on")))).toHaveLength(0);
    expect(sentinel).not.toHaveBeenCalled();
    expect(screen.getByTestId("healing-excerpt").textContent).toContain("<script>");
    delete (window as unknown as Record<string, unknown>).__sentinel;
  });

  it("AT_962_12_3 escalated 列顯示已升級徽章；點徽章開決策彈窗（同一殼）；沒有直接重試的按鈕", async () => {
    await mount(HEALING, "OPERATOR", { kanban: kanbanPending(PENDING_ESCALATED) });
    const badge = await screen.findByRole("button", { name: "已升級，等待人工決定" });
    expect(screen.queryByRole("button", { name: /重試/ })).toBeNull();
    expect(screen.queryByTestId("decision-modal")).toBeNull();
    fireEvent.click(badge);
    const modal = await screen.findByTestId("decision-modal");
    expect(within(modal).getByTestId("decision-kind").getAttribute("data-kind")).toBe("ESCALATED");
    expect(within(modal).getByTestId("decision-reason").textContent).toBe(PENDING_ESCALATED.reason);
    expect(RUN_ID).toBe(PENDING_ESCALATED.runId);
  });

  it("AT_962_12_3 兩個任務各有一則 ESCALATED 審核：點第二個任務的徽章，彈窗是該任務的那一則（以 taskId 配對，不是第一則 ESCALATED）", async () => {
    const reviewOf3 = { ...PENDING_ESCALATED, reviewId: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", taskId: "task-3", reason: "任務三：重試耗盡" };
    const reviewOf7 = { ...PENDING_ESCALATED, taskId: "task-7", reason: "任務七：重試耗盡" };
    const rows = [row({ taskId: "task-3", escalated: true }), row({ taskId: "task-7", escalated: true })];
    await mount(withRows(rows), "OPERATOR", { kanban: kanbanPending(reviewOf3, reviewOf7) });
    const badges = await screen.findAllByRole("button", { name: "已升級，等待人工決定" });
    expect(badges).toHaveLength(2);
    fireEvent.click(badges[1]);
    const modal = await screen.findByTestId("decision-modal");
    expect(within(modal).getByTestId("decision-reason").textContent).toBe("任務七：重試耗盡");
  });

  it("AT_962_12_3 只有別的任務有 ESCALATED 審核時，本任務的徽章不是按鈕（不開錯彈窗）", async () => {
    const rows = [row({ taskId: "task-3", escalated: true })];
    await mount(withRows(rows), "OPERATOR", { kanban: kanbanPending(PENDING_ESCALATED) }); // 審核屬於 task-7
    await screen.findByTestId("healing-escalated");
    expect(screen.queryByRole("button", { name: "已升級，等待人工決定" })).toBeNull();
  });

  it("AT_962_12_1 已修復只看該任務最後一列：先 resolved 後又失敗＝重試中、先失敗後 resolved＝已修復", async () => {
    await mount(
      withRows([
        row({ taskId: "task-3", attempt: 1, resolved: true }),
        row({ taskId: "task-3", attempt: 2, resolved: false, status: "RETRYING" }),
        row({ taskId: "task-7", attempt: 1, resolved: false, status: "RETRYING" }),
        row({ taskId: "task-7", attempt: 2, resolved: true }),
      ]),
    );
    const [first, second] = screen.getAllByTestId("healing-row");
    expect(first.textContent).toContain("重試中");
    expect(first.textContent).not.toContain("已修復");
    expect(second.textContent).toContain("已修復");
  });

  it("AT_962_12_4 規格漂移列：顯示引導；點發起 SCR 開對話框且 sourceKind 預填 HEALING_FAILED", async () => {
    await mount(withRows([row({ specChangeForbidden: true })]));
    expect(screen.getByTestId("healing-spec-change").textContent).toContain("補丁觸及凍結規格，請發起 SCR");
    fireEvent.click(screen.getByTestId("healing-scr"));
    const dialog = await screen.findByTestId("scr-dialog");
    expect((within(dialog).getByTestId("scr-source") as HTMLSelectElement).value).toBe("HEALING_FAILED");
  });

  it("AT_962_12_5 日誌落後 3 筆顯示『日誌落後 3 筆』；0 筆不顯示", async () => {
    const first = await mount(withRows(HEALING.rows, { logLag: 3 }));
    expect(screen.getByTestId("healing-log-behind").textContent).toBe("日誌落後 3 筆");
    first.unmount();
    await mount(withRows(HEALING.rows, { logLag: 0 }));
    expect(screen.queryByTestId("healing-log-behind")).toBeNull();
    expect(document.body.textContent).not.toContain("日誌落後");
  });

  it("AT_962_12_E_1 rows 為空：顯示目前沒有自癒嘗試，沒有 0／3 假進度", async () => {
    await mount(withRows([]));
    expect(screen.getByTestId("healing-empty").textContent).toBe("目前沒有自癒嘗試");
    expect(document.body.textContent).not.toMatch(/0\s*[／/]\s*3/);
    expect(screen.queryByTestId("healing-attempt")).toBeNull();
  });

  it("AT_962_12_E_2 VIEWER：發起 SCR 鈕停用且 title 為權限不足", async () => {
    await mount(withRows([row({ specChangeForbidden: true })]), "VIEWER");
    const button = screen.getByTestId("healing-scr") as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.title).toContain("權限不足");
    fireEvent.click(button);
    await waitFor(() => expect(screen.queryByTestId("scr-dialog")).toBeNull());
  });

  it("AT_962_12_E_3 300 字元不含空白的摘錄：容器有換行與溢出處理類別，文字不被截成 299", async () => {
    const long = "x".repeat(300);
    await mount(withRows([row({ excerpt: long })]));
    const pre = screen.getByTestId("healing-excerpt");
    expect(pre.textContent).toHaveLength(300);
    expect(pre.className).toContain("break-all");
    expect(pre.className).toContain("overflow-x-auto");
    expect(pre.className).toContain("whitespace-pre-wrap");
    expect(pre.className).toContain("max-w-full");
  });
});
