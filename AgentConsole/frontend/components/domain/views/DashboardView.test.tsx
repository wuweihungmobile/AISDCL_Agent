import { render, screen, within } from "@testing-library/react";
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
