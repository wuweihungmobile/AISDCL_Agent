import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TopRegion } from "@/components/layout/TopRegion";
import type { PendingSignoffItem } from "@/lib/api/types";
import { Providers, envelope, failure, makeClient, signIn, stubApi as stubApiRaw, type ApiCall, type Reply } from "@/tests/helpers/api";
import { DashboardView } from "./DashboardView";

/** 待審批清單端點（契約 §1.8.1）：這支檔前半段的 KPI 情境不關心待人工審批卡，預設回「沒有待審批」；驗卡片的情境用 stubApiRaw 自己提供清單。 */
const PENDING_PATH = "/api/v1/signoffs/pending";
const PENDING_NONE = { data: { counts: { projects: 0, goals: 0, tasks: 0, imports: 0, total: 0 }, items: [] } };
const stubApi = (handler: (c: ApiCall) => Reply) => stubApiRaw((c) => (c.path === PENDING_PATH ? PENDING_NONE : handler(c)));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
// 圖表（recharts）與本測試無關，且在 jsdom 沒有版面可量：換成空殼
vi.mock("@/components/charts/ProjectStatusChart", () => ({ ProjectStatusChart: () => null }));

const PROJECTS = {
  content: [
    { id: "p1", name: "專案甲", status: "EXECUTING", signedOff: true, goalsCount: 1, tasksCount: 2, tasksDone: 1, autonomyLevel: 3, executionPath: "/x", updatedAt: "2026-01-01T00:00:00Z" },
    { id: "p2", name: "專案乙", status: "DRAFT", signedOff: false, goalsCount: 0, tasksCount: 0, tasksDone: 0, autonomyLevel: 3, executionPath: "/y", updatedAt: "2026-01-01T00:00:00Z" },
  ],
  page: 0,
  size: 100,
  totalElements: 2,
  totalPages: 1,
};

beforeEach(() => signIn("OPERATOR", "operator"));

const SUMMARY_ZERO = { data: { pendingSignoffs: 0, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null } };
const runPage = (runs: object[]) => ({ data: { content: runs, page: 0, size: 1, totalElements: runs.length, totalPages: 1 } });
const run = (patch: object) => ({
  id: "r1",
  projectId: "p1",
  runNumber: 3,
  status: "RUNNING",
  autonomyLevel: 4,
  scopeMode: "ALL",
  totalTokensUsed: 1,
  startedAt: "2026-10-15T08:30:00Z",
  tasksTotal: 23,
  tasksCompleted: 13,
  tasksFailed: 0,
  ...patch,
});
/** GET /monitor/task-totals 的回應（契約 §1.3.8）：跨專案的步驟列數，不分桶 */
const totals = (completed: number, projectsCounted = 2) => ({
  data: { from: "2026-10-12T00:00:00Z", to: "2026-10-15T08:40:00Z", started: completed + 1, completed, failed: 1, retried: 0, projectsCounted },
});
const TOTALS_PATH = "/api/v1/monitor/task-totals";

describe("Dashboard「本週完成任務數」與「執行中 run 數」KPI（契約 §4.5 G-07、G-08、§1.3.8；DEF-AC-009）", () => {
  const MORE = {
    content: [
      ...PROJECTS.content,
      { id: "p3", name: "專案丙", status: "COMPLETED", signedOff: true, goalsCount: 1, tasksCount: 4, tasksDone: 4, autonomyLevel: 3, executionPath: "/z", updatedAt: "2026-01-01T00:00:00Z" },
      { id: "p4", name: "專案丁（封存）", status: "ARCHIVED", signedOff: true, goalsCount: 1, tasksCount: 4, tasksDone: 4, autonomyLevel: 3, executionPath: "/w", updatedAt: "2026-01-01T00:00:00Z" },
    ],
    totalElements: 4,
  };

  it("本週完成任務數＝GET /monitor/task-totals 的 completed（一次請求，不再對各專案扇出 task-trend）；from 是本週一 00:00（本機）、to 省略＝現在", async () => {
    const { calls } = stubApi((c) => {
      if (c.path === "/api/v1/notifications/summary") return SUMMARY_ZERO;
      if (c.path === "/api/v1/projects") return { data: { ...PROJECTS, ...MORE } };
      if (c.path === TOTALS_PATH) return totals(7, 2);
      if (c.path === "/api/v1/projects/p1/executions") return runPage([run({})]);
      return { data: [] };
    });
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    await waitFor(() => expect(screen.getByTestId("kpi-week-done")).toHaveTextContent("7"));
    expect(screen.getByText("本週一起 · 跨 2 個專案")).toBeInTheDocument();
    expect(screen.queryByText(/近似值/)).toBeNull(); // 全域端點是精確值，不再標「近似值」
    // 缺陷版本（DEF-AC-009）：對每個專案各打一次 task-trend（最多 30 次）；現在只有 1 次 task-totals
    expect(calls.filter((c) => c.path.includes("/task-trend"))).toHaveLength(0);
    const totalCalls = calls.filter((c) => c.path === TOTALS_PATH);
    expect(totalCalls).toHaveLength(1);
    expect(totalCalls[0].method).toBe("GET");
    const from = new Date(totalCalls[0].query.get("from")!);
    expect(from.getDay()).toBe(1); // 週一
    expect([from.getHours(), from.getMinutes(), from.getSeconds()]).toEqual([0, 0, 0]);
    expect(Date.now() - from.getTime()).toBeLessThan(7 * 86_400_000);
    expect(totalCalls[0].query.has("to")).toBe(false); // 契約 §1.3.8：to 省略＝現在（伺服器處理當下）
  });

  it("本週完成任務數的請求次數與專案數無關：30 個專案也只有 1 次 task-totals、0 次 task-trend（限流額度不再被總覽頁吃掉）", async () => {
    const many = Array.from({ length: 30 }, (_, i) => ({ ...PROJECTS.content[0], id: `m${i}`, name: `專案${i}`, status: "COMPLETED", tasksDone: 3 }));
    const { calls } = stubApi((c) => {
      if (c.path === "/api/v1/notifications/summary") return SUMMARY_ZERO;
      if (c.path === "/api/v1/projects") return { data: { ...PROJECTS, content: many, totalElements: 30 } };
      if (c.path === TOTALS_PATH) return totals(90, 30);
      return { data: [] };
    });
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    await waitFor(() => expect(screen.getByTestId("kpi-week-done")).toHaveTextContent("90"));
    expect(calls.filter((c) => c.path.includes("/task-trend"))).toHaveLength(0);
    expect(calls.filter((c) => c.path === TOTALS_PATH)).toHaveLength(1);
  });

  it("載入中顯示「—」與「統計中…」；task-totals 失敗：本週完成數顯示「—」與錯誤說明（不編數字），其餘 KPI 照常", async () => {
    // task-totals 先卡住（看得到載入中），放行後回 500；stubApi 的 handler 是同步的，所以這支自己接 fetch
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string) => {
        const path = new URL(input, "http://api.test").pathname;
        if (path === "/api/v1/notifications/summary") return envelope(SUMMARY_ZERO.data);
        if (path === PENDING_PATH) return envelope(PENDING_NONE.data);
        if (path === "/api/v1/projects") return envelope({ ...PROJECTS, ...MORE });
        if (path === TOTALS_PATH) {
          await gate;
          return failure(500, { message: "伺服器錯誤" });
        }
        return envelope([]);
      }),
    );
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    await screen.findByTestId("kpi-active");
    expect(screen.getByTestId("kpi-week-done")).toHaveTextContent("—");
    expect(screen.getByText("統計中…")).toBeInTheDocument();
    release();
    expect(await screen.findByText("無法載入本週完成任務數")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-week-done")).toHaveTextContent("—");
    expect(screen.getByTestId("kpi-active")).toHaveTextContent("2"); // 其餘 KPI 不受影響
  });

  it("執行中 run 數＝EXECUTING 專案中「最新批次仍在跑」者；「進行中的執行」卡顯示最新批次的 Run 與進度（tasksCompleted／tasksTotal）", async () => {
    stubApi((c) => {
      if (c.path === "/api/v1/notifications/summary") return SUMMARY_ZERO;
      if (c.path === "/api/v1/projects") return { data: PROJECTS };
      if (c.path === TOTALS_PATH) return totals(0, 0);
      if (c.path === "/api/v1/projects/p1/executions") return runPage([run({ tasksCompleted: 13, tasksTotal: 23 })]);
      return { data: [] };
    });
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    await waitFor(() => expect(screen.getByTestId("kpi-runs")).toHaveTextContent("1"));
    expect(screen.getByText("進行中的執行批次")).toBeInTheDocument();
    const row = screen.getByTestId("active-run");
    await waitFor(() => expect(within(row).getByTestId("active-run-progress")).toHaveTextContent("Run #3 · 13 / 23 任務完成"));
    expect(within(row).getByText("57%")).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: "專案甲" })).toHaveAttribute("href", "/projects/p1/execute");
  });

  it("EXECUTING 專案的最新批次已結束（專案狀態還沒更新）：不算進「執行中 run 數」", async () => {
    stubApi((c) => {
      if (c.path === "/api/v1/notifications/summary") return SUMMARY_ZERO;
      if (c.path === "/api/v1/projects") return { data: PROJECTS };
      if (c.path === TOTALS_PATH) return totals(0, 0);
      if (c.path === "/api/v1/projects/p1/executions") return runPage([run({ status: "COMPLETED" })]);
      return { data: [] };
    });
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    await waitFor(() => expect(screen.getByTestId("kpi-runs")).toHaveTextContent("0"));
    expect(screen.getByText("目前沒有執行中的批次")).toBeInTheDocument();
  });

  it("沒有任何執行中專案、也沒有完成過任務的專案：執行中 run 數是 0（不為空集合發批次請求），本週完成任務數取全域端點回的 0", async () => {
    const { calls } = stubApi((c) => {
      if (c.path === "/api/v1/notifications/summary") return SUMMARY_ZERO;
      if (c.path === "/api/v1/projects") return { data: { ...PROJECTS, content: [PROJECTS.content[1]], totalElements: 1 } };
      if (c.path === TOTALS_PATH) return totals(0, 0);
      return { data: [] };
    });
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    await waitFor(() => expect(screen.getByTestId("kpi-runs")).toHaveTextContent("0"));
    await waitFor(() => expect(screen.getByTestId("kpi-week-done")).toHaveTextContent("0"));
    expect(calls.some((c) => c.path.endsWith("/executions"))).toBe(false);
  });
});

describe("Dashboard「待審批草案數」KPI（契約 §4.5 G-06）", () => {
  it("取通知摘要的 pendingSignoffs（跨專案、含目標與任務層級），不是專案列表算出的近似值", async () => {
    stubApi((c) =>
      c.path === "/api/v1/notifications/summary"
        ? { data: { pendingSignoffs: 9, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null } }
        : c.path === "/api/v1/projects"
          ? { data: PROJECTS }
          : c.path === TOTALS_PATH
            ? totals(0, 0)
            : { data: [] },
    );
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    expect(await screen.findByTestId("kpi-drafts")).toBeInTheDocument();
    // 專案列表只有 1 個草案專案（會算出 1），KPI 必須顯示摘要的 9
    await screen.findByText("9");
    expect(screen.getByTestId("kpi-drafts")).toHaveTextContent("9");
    expect(within(screen.getByTestId("kpi-drafts").parentElement!).getByText("需 signoff 才可執行")).toBeInTheDocument();
  });

  it("摘要為 0：顯示「全部已審批」；摘要載入失敗：顯示「—」而不是編一個數字", async () => {
    stubApi((c) =>
      c.path === "/api/v1/notifications/summary"
        ? { data: { pendingSignoffs: 0, pendingReviews: 0, unacknowledgedAlerts: 0 } }
        : c.path === "/api/v1/projects"
          ? { data: PROJECTS }
          : c.path === TOTALS_PATH
            ? totals(0, 0)
            : { data: [] },
    );
    const { unmount } = render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    expect(await screen.findByText("全部已審批")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-drafts")).toHaveTextContent("0");
    unmount();

    stubApi((c) =>
      c.path === "/api/v1/notifications/summary" ? failure(500, { message: "伺服器錯誤" }) : c.path === "/api/v1/projects" ? envelope(PROJECTS) : c.path === TOTALS_PATH ? totals(0, 0) : { data: [] },
    );
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    expect(await screen.findByTestId("kpi-drafts")).toHaveTextContent("—");
    expect(screen.getByText("待通知摘要載入")).toBeInTheDocument();
  });
});

describe("Dashboard「待人工審批」卡（契約 §1.8.1、§4.5 G-10；v1.4 D-18，API-SGN-05）", () => {
  const AT = "2026-10-15T08:30:12Z";
  const pend = (kind: PendingSignoffItem["kind"], id: string, title: string): PendingSignoffItem => ({
    kind,
    id,
    projectId: kind === "IMPORT" ? null : kind === "PROJECT" ? id : "pj1",
    projectName: kind === "IMPORT" ? null : kind === "PROJECT" ? title : "專案甲",
    parentId: kind === "GOAL" ? "pj1" : kind === "TASK" ? "g1" : null,
    title,
    createdAt: AT,
  });
  /** 伺服器給的順序＝建立時間升冪（契約 §1.8.1）；四種各一筆。 */
  const FOUR = [pend("IMPORT", "i1", "需求文件.md"), pend("PROJECT", "pj1", "新專案"), pend("GOAL", "g1", "基礎"), pend("TASK", "t1", "初始化")];
  const countsOf = (items: PendingSignoffItem[], total = items.length) => ({
    projects: items.filter((i) => i.kind === "PROJECT").length,
    goals: items.filter((i) => i.kind === "GOAL").length,
    tasks: items.filter((i) => i.kind === "TASK").length,
    imports: items.filter((i) => i.kind === "IMPORT").length,
    total,
  });

  /**
   * 假後端：待審批清單與通知摘要由同一份 items 產生（後端以同一組述詞算兩者，不變量：counts.total＝pendingSignoffs）；
   * 四個 signoff 端點成功就把該筆從 items 拿掉。totalOverride＝總數大於清單（模擬 limit 截斷）。
   */
  function backend(initial: PendingSignoffItem[], opts: { totalOverride?: number; failList?: () => boolean } = {}) {
    let items = [...initial];
    const total = () => opts.totalOverride ?? items.length;
    const { calls } = stubApiRaw((c) => {
      if (c.path === PENDING_PATH) {
        if (opts.failList?.()) return failure(500, { message: "伺服器錯誤" });
        const limit = Number(c.query.get("limit") ?? 50);
        return { data: { counts: countsOf(items, total()), items: items.slice(0, limit) } };
      }
      if (c.path === "/api/v1/notifications/summary") return { data: { pendingSignoffs: total(), pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null } };
      if (c.path === "/api/v1/projects") return { data: PROJECTS };
      if (c.path === TOTALS_PATH) return totals(0, 0);
      const signoff = /^\/api\/v1\/(projects|goals|tasks|import)\/([^/]+)\/signoff$/.exec(c.path);
      if (c.method === "POST" && signoff) {
        items = items.filter((i) => i.id !== signoff[2]);
        return { data: { id: signoff[2], status: "REVIEWING", signedOff: true, signedOffBy: "operator", signedOffAt: AT } };
      }
      return { data: [] };
    });
    return { calls, remaining: () => items };
  }

  const view = (...extra: ReactNode[]) =>
    render(
      <Providers client={makeClient()}>
        {extra}
        <DashboardView />
      </Providers>,
    );
  const pendingCalls = (calls: ApiCall[]) => calls.filter((c) => c.path === PENDING_PATH);

  it("清單取 GET /signoffs/pending?limit=50（一次）：四種草案各一列，連結與副標依契約 G-10，順序照伺服器給的；徽章＝counts.total；不再為草案專案逐一查目標", async () => {
    const { calls } = backend(FOUR);
    view();
    const rows = await screen.findAllByTestId("pending-item");
    expect(rows.map((r) => r.getAttribute("data-kind"))).toEqual(["IMPORT", "PROJECT", "GOAL", "TASK"]);
    const links = rows.map((r) => within(r).getByRole("link"));
    expect(links.map((l) => [l.textContent, l.getAttribute("href")])).toEqual([
      ["需求文件.md", "/import"], // 匯入頁沒有以 id 深連結某筆記錄的路由
      ["新專案", "/projects/pj1"],
      ["基礎", "/projects/pj1/goals/g1"],
      ["初始化", "/projects/pj1/goals/g1/tasks/t1"],
    ]);
    expect(rows.map((r) => within(r).getByText(/草案/).textContent)).toEqual(["匯入草案", "專案草案", "目標草案・專案甲", "任務草案・專案甲"]);
    expect(screen.getByTestId("pending-count")).toHaveTextContent("4");
    expect(pendingCalls(calls)).toHaveLength(1);
    expect(pendingCalls(calls)[0].query.get("limit")).toBe("50");
    expect(
      calls.some((c) => /\/projects\/[^/]+\/goals$/.test(c.path)),
      "舊做法：對每個草案專案各查一次目標清單",
    ).toBe(false);
    expect(screen.queryByTestId("pending-truncated")).toBeNull(); // 清單沒被截斷
  });

  it("每列的「審批」鈕名稱含標題；清單與 KPI 同源：沒有任何「KPI 大於點得到的項目」的情形", async () => {
    backend(FOUR);
    view();
    await screen.findAllByTestId("pending-item");
    for (const title of ["需求文件.md", "新專案", "基礎", "初始化"]) expect(screen.getByRole("button", { name: `審批：${title}` })).toBeEnabled();
    await waitFor(() => expect(screen.getByTestId("kpi-drafts")).toHaveTextContent("4"));
    expect(screen.getAllByTestId("pending-item")).toHaveLength(Number(screen.getByTestId("kpi-drafts").textContent));
  });

  it("🔴 同源：卡片徽章（counts.total）、KPI「待審批草案數」、頂列 signoff 徽章（通知摘要 pendingSignoffs）是同一個數字；簽核一筆後三者同步減 1、那一列消失（不必整頁重載）", async () => {
    const { calls, remaining } = backend(FOUR);
    view(<TopRegion key="top" />);
    await waitFor(() => expect(screen.getByTestId("pending-count")).toHaveTextContent("4"));
    await waitFor(() => expect(screen.getByTestId("kpi-drafts")).toHaveTextContent("4"));
    await waitFor(() => expect(screen.getByTestId("signoff-badge")).toHaveTextContent("4"));

    await userEvent.click(screen.getByRole("button", { name: "審批：新專案" }));
    const dialog = await screen.findByRole("dialog", { name: "審批 signoff：專案" });
    await userEvent.click(within(dialog).getByRole("button", { name: "確認 signoff" }));

    await waitFor(() => expect(screen.getByTestId("pending-count")).toHaveTextContent("3"));
    await waitFor(() => expect(screen.getByTestId("kpi-drafts")).toHaveTextContent("3"));
    await waitFor(() => expect(screen.getByTestId("signoff-badge")).toHaveTextContent("3"));
    expect(screen.queryByRole("link", { name: "新專案" })).toBeNull();
    expect(screen.getAllByTestId("pending-item")).toHaveLength(3);
    expect(remaining().map((i) => i.id)).toEqual(["i1", "g1", "t1"]);
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ approver: "operator" });
  });

  it.each([
    ["PROJECT", "審批：新專案", "審批 signoff：專案", "/api/v1/projects/pj1/signoff"],
    ["GOAL", "審批：基礎", "審批 signoff：目標", "/api/v1/goals/g1/signoff"],
    ["TASK", "審批：初始化", "審批 signoff：任務", "/api/v1/tasks/t1/signoff"],
    ["IMPORT", "審批：需求文件.md", "審批 signoff：匯入草案", "/api/v1/import/i1/signoff"],
  ])("%s 草案按「審批」：開 SignoffDialog（%s → %s）、POST %s；成功後清單與通知摘要立即重抓（簽核類寫入讓 notifications 家族標為過期）", async (_kind, button, dialogName, path) => {
    const { calls } = backend(FOUR);
    view();
    await screen.findAllByTestId("pending-item");
    const listBefore = pendingCalls(calls).length;
    const summaryBefore = calls.filter((c) => c.path === "/api/v1/notifications/summary").length;
    await userEvent.click(screen.getByRole("button", { name: button }));
    await userEvent.click(within(await screen.findByRole("dialog", { name: dialogName })).getByRole("button", { name: "確認 signoff" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST" && c.path === path)).toBe(true));
    await waitFor(() => expect(pendingCalls(calls).length).toBeGreaterThan(listBefore));
    await waitFor(() => expect(calls.filter((c) => c.path === "/api/v1/notifications/summary").length).toBeGreaterThan(summaryBefore));
    await waitFor(() => expect(screen.getAllByTestId("pending-item")).toHaveLength(3));
  });

  it("清單被 limit 截斷（counts.total 大於清單）：徽章仍是 counts.total，卡片底部寫「僅列出最早的 N 筆，共 M 筆」", async () => {
    backend(FOUR, { totalOverride: 63 });
    view();
    expect(await screen.findByTestId("pending-truncated")).toHaveTextContent("僅列出最早的 4 筆，共 63 筆");
    expect(screen.getByTestId("pending-count")).toHaveTextContent("63");
    await waitFor(() => expect(screen.getByTestId("kpi-drafts")).toHaveTextContent("63"));
  });

  it("沒有待審批：空狀態「沒有待審批的草案」，徽章 0，沒有截斷說明", async () => {
    backend([]);
    view();
    expect(await screen.findByText("沒有待審批的草案")).toBeInTheDocument();
    expect(screen.getByTestId("pending-count")).toHaveTextContent("0");
    expect(screen.queryByTestId("pending-item")).toBeNull();
    expect(screen.queryByTestId("pending-truncated")).toBeNull();
  });

  it("清單載入失敗：卡片內顯示錯誤與重試（沒有徽章、不編造清單），KPI 與其他卡照常；重試成功後清單出現", async () => {
    let failing = true;
    const { calls } = backend(FOUR, { failList: () => failing });
    view();
    expect(await screen.findByText("無法載入待審批清單")).toBeInTheDocument();
    expect(screen.queryByTestId("pending-count")).toBeNull();
    expect(screen.queryByTestId("pending-item")).toBeNull();
    await waitFor(() => expect(screen.getByTestId("kpi-drafts")).toHaveTextContent("4")); // KPI 取通知摘要，不受影響
    expect(screen.getByTestId("kpi-active")).toBeInTheDocument();

    failing = false;
    const before = pendingCalls(calls).length;
    await userEvent.click(within(screen.getByTestId("pending-signoff-card")).getByRole("button", { name: "重試" }));
    await waitFor(() => expect(pendingCalls(calls).length).toBeGreaterThan(before));
    expect(await screen.findAllByTestId("pending-item")).toHaveLength(4);
    expect(screen.getByTestId("pending-count")).toHaveTextContent("4");
  });

  it("唯讀角色（VIEWER）：清單與連結照常，「審批」鈕全部停用並附權限說明", async () => {
    signIn("VIEWER", "viewer");
    backend(FOUR);
    view();
    const rows = await screen.findAllByTestId("pending-item");
    for (const row of rows) {
      const button = within(row).getByRole("button", { name: /^審批：/ });
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute("title", "權限不足（唯讀角色不可審批）");
    }
    expect(within(rows[1]).getByRole("link")).toHaveAttribute("href", "/projects/pj1");
  });

  it("卡片是 Dashboard 上 #pending-signoff 的錨點（頂列「待審批佇列」鈕與通知鈴「待簽核草案」列都連到 /#pending-signoff）", async () => {
    backend(FOUR);
    view();
    const card = await screen.findByTestId("pending-signoff-card");
    expect(card).toHaveAttribute("id", "pending-signoff");
    expect(within(card).getByText("待人工審批")).toBeInTheDocument();
  });
});
