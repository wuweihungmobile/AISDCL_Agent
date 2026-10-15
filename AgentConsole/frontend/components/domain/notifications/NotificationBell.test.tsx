import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NotificationSummary } from "@/lib/api/types";
import { NotificationBell } from "./NotificationBell";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

let currentProject: string | null = "p1";
vi.mock("@/hooks/useCurrentProjectId", () => ({ useCurrentProjectId: () => currentProject }));

const SUMMARY: NotificationSummary = {
  pendingSignoffs: 4,
  pendingReviews: 2,
  unacknowledgedAlerts: 3,
  bridgeConnected: null,
  bridgeCheckedAt: null,
};

/** jsdom 不實作換頁；連結被點到時會印「Not implemented: navigation」。在 document 冒泡階段擋預設動作（React 的處理器已先跑完，面板照常關閉）。 */
const blockNavigation = (e: Event) => e.preventDefault();

beforeEach(() => {
  currentProject = "p1";
  document.addEventListener("click", blockNavigation);
});

afterEach(() => {
  document.removeEventListener("click", blockNavigation);
});

describe("通知鈴（契約 §4.5 G-01、G-G2）", () => {
  it("徽章＝待審核項目＋未確認告警（前端加總）；待簽核草案不進鈴（它歸 signoff 佇列鈕）", () => {
    render(<NotificationBell summary={SUMMARY} />);
    expect(screen.getByTestId("bell-badge")).toHaveTextContent("5");
    expect(screen.getByRole("button", { name: "通知 5 筆待處理" })).toBeInTheDocument();
    // 徽章上的可見數字要出現在名稱裡（WCAG 2.5.3 Label in Name；DEF-AC-005）
    expect(screen.getByTestId("bell-trigger").getAttribute("aria-label")).toContain(screen.getByTestId("bell-badge").textContent ?? "");
  });

  it("全部為 0 或摘要尚未載入：不顯示徽章，鈴照常可點", () => {
    const { rerender } = render(<NotificationBell summary={{ ...SUMMARY, pendingReviews: 0, unacknowledgedAlerts: 0 }} />);
    expect(screen.queryByTestId("bell-badge")).toBeNull();
    rerender(<NotificationBell summary={undefined} />);
    expect(screen.queryByTestId("bell-badge")).toBeNull();
    expect(screen.getByRole("button", { name: "通知" })).toBeInTheDocument();
  });

  it("點開小面板：列出三個數字與連結（待簽核→Dashboard 待審批卡；待審核→目前專案執行頁；告警→目前專案監控頁）", async () => {
    render(<NotificationBell summary={SUMMARY} />);
    expect(screen.queryByTestId("notification-panel")).toBeNull();
    await userEvent.click(screen.getByTestId("bell-trigger"));
    const panel = within(screen.getByTestId("notification-panel"));
    expect(panel.getByTestId("notification-signoffs-count")).toHaveTextContent("4");
    expect(panel.getByTestId("notification-reviews-count")).toHaveTextContent("2");
    expect(panel.getByTestId("notification-alerts-count")).toHaveTextContent("3");
    expect(panel.getByTestId("notification-signoffs")).toHaveAttribute("href", "/#pending-signoff");
    expect(panel.getByTestId("notification-reviews")).toHaveAttribute("href", "/projects/p1/execute");
    expect(panel.getByTestId("notification-alerts")).toHaveAttribute("href", "/projects/p1/monitor");
  });

  it("沒有目前專案時，審核與告警連結退回專案列表；摘要未載入的數字顯示「—」", async () => {
    currentProject = null;
    render(<NotificationBell summary={undefined} />);
    await userEvent.click(screen.getByTestId("bell-trigger"));
    const panel = within(screen.getByTestId("notification-panel"));
    expect(panel.getByTestId("notification-reviews")).toHaveAttribute("href", "/projects");
    expect(panel.getByTestId("notification-alerts")).toHaveAttribute("href", "/projects");
    expect(panel.getByTestId("notification-reviews-count")).toHaveTextContent("—");
  });

  it("點面板內連結後面板關閉（導頁不留著擋畫面）；Esc 也能關", async () => {
    render(<NotificationBell summary={SUMMARY} />);
    await userEvent.click(screen.getByTestId("bell-trigger"));
    await userEvent.click(screen.getByTestId("notification-alerts"));
    expect(screen.queryByTestId("notification-panel")).toBeNull();
    await userEvent.click(screen.getByTestId("bell-trigger"));
    expect(screen.getByTestId("notification-panel")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByTestId("notification-panel")).toBeNull();
  });
});
