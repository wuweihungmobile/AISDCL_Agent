import { render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Providers, envelope, failure, makeClient, signIn, stubApi } from "@/tests/helpers/api";
import { DashboardView } from "./DashboardView";

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
