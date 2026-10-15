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
const run = (patch: object) => ({ id: "r1", projectId: "p1", runNumber: 3, status: "RUNNING", autonomyLevel: 4, scopeMode: "ALL", totalTokensUsed: 1, startedAt: "2026-10-15T08:30:00Z", tasksTotal: 23, tasksCompleted: 13, tasksFailed: 0, ...patch });
const point = (completed: number) => ({ bucketStart: "2026-10-12T00:00:00Z", started: completed, completed, failed: 0, retried: 0 });

describe("Dashboard「本週完成任務數」與「執行中 run 數」KPI（契約 §4.5 G-07、G-08、§4.6 G-G3）", () => {
  const MORE = {
    content: [
      ...PROJECTS.content,
      { id: "p3", name: "專案丙", status: "COMPLETED", signedOff: true, goalsCount: 1, tasksCount: 4, tasksDone: 4, autonomyLevel: 3, executionPath: "/z", updatedAt: "2026-01-01T00:00:00Z" },
      { id: "p4", name: "專案丁（封存）", status: "ARCHIVED", signedOff: true, goalsCount: 1, tasksCount: 4, tasksDone: 4, autonomyLevel: 3, executionPath: "/w", updatedAt: "2026-01-01T00:00:00Z" },
    ],
    totalElements: 4,
  };

  it("本週完成任務數＝各專案 task-trend 的 completed 加總；只查「完成過任務或執行中、且非封存」的專案；from 是本週一 00:00（本機）、bucket=DAY", async () => {
    const { calls } = stubApi((c) => {
      if (c.path === "/api/v1/notifications/summary") return SUMMARY_ZERO;
      if (c.path === "/api/v1/projects") return { data: { ...PROJECTS, ...MORE } };
      if (c.path === "/api/v1/monitor/projects/p1/task-trend") return { data: [point(2), point(1)] };
      if (c.path === "/api/v1/monitor/projects/p3/task-trend") return { data: [point(4)] };
      if (c.path === "/api/v1/projects/p1/executions") return runPage([run({})]);
      return { data: [] };
    });
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    await waitFor(() => expect(screen.getByTestId("kpi-week-done")).toHaveTextContent("7"));
    expect(screen.getByText("本週一起 · 跨 2 個專案（近似值）")).toBeInTheDocument();
    const trendCalls = calls.filter((c) => c.path.includes("/task-trend"));
    expect(trendCalls.map((c) => c.path).sort()).toEqual(["/api/v1/monitor/projects/p1/task-trend", "/api/v1/monitor/projects/p3/task-trend"]); // p2 草稿沒完成過、p4 封存：不查
    const from = new Date(trendCalls[0].query.get("from")!);
    expect(from.getDay()).toBe(1); // 週一
    expect([from.getHours(), from.getMinutes(), from.getSeconds()]).toEqual([0, 0, 0]);
    expect(Date.now() - from.getTime()).toBeLessThan(7 * 86_400_000);
    expect(trendCalls[0].query.get("bucket")).toBe("DAY");
    expect(Date.parse(trendCalls[0].query.get("to")!)).toBeGreaterThan(from.getTime());
  });

  it("有專案的 task-trend 查詢失敗：數字照常加總其餘專案，並提示「部分專案查詢失敗，數字可能偏低」，不假裝精確", async () => {
    stubApi((c) => {
      if (c.path === "/api/v1/notifications/summary") return SUMMARY_ZERO;
      if (c.path === "/api/v1/projects") return { data: { ...PROJECTS, ...MORE } };
      if (c.path === "/api/v1/monitor/projects/p1/task-trend") return failure(500, { message: "伺服器錯誤" });
      if (c.path === "/api/v1/monitor/projects/p3/task-trend") return { data: [point(4)] };
      return { data: [] };
    });
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    await waitFor(() => expect(screen.getByTestId("kpi-week-done")).toHaveTextContent("4"));
    expect(screen.getByText("部分專案查詢失敗，數字可能偏低")).toBeInTheDocument();
  });

  it("執行中 run 數＝EXECUTING 專案中「最新批次仍在跑」者；「進行中的執行」卡顯示最新批次的 Run 與進度（tasksCompleted／tasksTotal）", async () => {
    stubApi((c) => {
      if (c.path === "/api/v1/notifications/summary") return SUMMARY_ZERO;
      if (c.path === "/api/v1/projects") return { data: PROJECTS };
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

  it("沒有任何執行中專案、也沒有完成過任務的專案：執行中 run 數與本週完成任務數都是 0（不為空集合發請求）", async () => {
    stubApi((c) => {
      if (c.path === "/api/v1/notifications/summary") return SUMMARY_ZERO;
      if (c.path === "/api/v1/projects") return { data: { ...PROJECTS, content: [PROJECTS.content[1]], totalElements: 1 } };
      return { data: [] };
    });
    render(
      <Providers client={makeClient()}>
        <DashboardView />
      </Providers>,
    );
    await waitFor(() => expect(screen.getByTestId("kpi-runs")).toHaveTextContent("0"));
    expect(screen.getByTestId("kpi-week-done")).toHaveTextContent("0");
  });
});

describe("Dashboard「待審批草案數」KPI（契約 §4.5 G-06）", () => {
  it("取通知摘要的 pendingSignoffs（跨專案、含目標與任務層級），不是專案列表算出的近似值", async () => {
    stubApi((c) =>
      c.path === "/api/v1/notifications/summary"
        ? { data: { pendingSignoffs: 9, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null } }
        : c.path === "/api/v1/projects"
          ? { data: PROJECTS }
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
      c.path === "/api/v1/notifications/summary" ? failure(500, { message: "伺服器錯誤" }) : c.path === "/api/v1/projects" ? envelope(PROJECTS) : { data: [] },
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
