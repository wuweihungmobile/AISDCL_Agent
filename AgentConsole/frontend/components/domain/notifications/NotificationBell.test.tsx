import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NotificationSummary } from "@/lib/api/types";
import { rememberProjectId } from "@/lib/nav/lastProject";
import { NotificationBell } from "./NotificationBell";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

// 落點只看「路由上的 projectId」（契約 §4.6 G-G4）：用 pathname 替身控制
let pathname = "/projects/p1";
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

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
  pathname = "/projects/p1";
  window.sessionStorage.clear();
  document.addEventListener("click", blockNavigation);
});

afterEach(() => {
  document.removeEventListener("click", blockNavigation);
});

async function openPanel(summary: NotificationSummary | undefined) {
  render(<NotificationBell summary={summary} />);
  await userEvent.click(screen.getByTestId("bell-trigger"));
  return within(screen.getByTestId("notification-panel"));
}

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

  it("點開小面板：列出三個數字與連結（待簽核→Dashboard 的待人工審批卡；在專案頁時，待審核→該專案執行頁、告警→該專案監控頁）", async () => {
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

  it("專案頁底下的任何子頁（目標、任務、監控…）都算「在專案頁」：落點取路由上的專案", async () => {
    pathname = "/projects/p7/goals/g1/tasks/t2";
    const panel = await openPanel(SUMMARY);
    expect(panel.getByTestId("notification-reviews")).toHaveAttribute("href", "/projects/p7/execute");
    expect(panel.getByTestId("notification-alerts")).toHaveAttribute("href", "/projects/p7/monitor");
  });

  it.each([
    ["Dashboard", "/"],
    ["專案列表", "/projects"],
    ["新建專案", "/projects/new"],
    ["匯入頁", "/import"],
    ["系統設定", "/settings"],
  ])("🔴 G-G4／E2E-16 第 6 列：在%s（路由上沒有專案）時，待審核項目與未確認告警都導向專案列表；待簽核草案恆為 /#pending-signoff", async (_name, path) => {
    pathname = path;
    const panel = await openPanel(SUMMARY);
    expect(panel.getByTestId("notification-reviews")).toHaveAttribute("href", "/projects");
    expect(panel.getByTestId("notification-alerts")).toHaveAttribute("href", "/projects");
    expect(panel.getByTestId("notification-signoffs")).toHaveAttribute("href", "/#pending-signoff");
  });

  it("不猜「最近造訪的專案」：就算 sessionStorage 記著上次的專案，在 Dashboard 的落點仍是專案列表（那個專案不一定有待辦）", async () => {
    rememberProjectId("p9");
    pathname = "/";
    const panel = await openPanel(SUMMARY);
    expect(panel.getByTestId("notification-reviews")).toHaveAttribute("href", "/projects");
    expect(panel.getByTestId("notification-alerts")).toHaveAttribute("href", "/projects");
  });

  it("連結文案不把計數說成屬於某個專案：標題列說「全部專案的合計」、連結 tooltip 寫明落點；摘要未載入的數字顯示「—」", async () => {
    pathname = "/";
    const panel = await openPanel(undefined);
    expect(panel.getByTestId("notification-reviews-count")).toHaveTextContent("—");
    expect(panel.getByTestId("notification-scope-note")).toHaveTextContent("待審核項目與未確認告警是全部專案的合計");
    expect(panel.getByTestId("notification-reviews")).toHaveAttribute("title", "數字是全部專案的合計；點進去前往專案列表，請自行挑選有待辦的專案");
    expect(panel.getByTestId("notification-alerts")).toHaveAttribute("title", "數字是全部專案的合計；點進去前往專案列表，請自行挑選有待辦的專案");
    expect(panel.getByTestId("notification-signoffs")).toHaveAttribute("title", "前往儀表板的「待人工審批」卡");
    // 面板與連結文案沒有「目前專案」「本專案」這類暗示計數屬於單一專案的字樣
    expect(screen.getByTestId("notification-panel").textContent).not.toMatch(/目前專案|本專案|當前專案/);
    expect(panel.getByTestId("notification-reviews").getAttribute("title")).not.toMatch(/目前專案|本專案|當前專案/);
  });

  it("在專案頁時 tooltip 寫「前往這個專案的執行頁／監控頁」，仍強調數字是全部專案的合計", async () => {
    const panel = await openPanel(SUMMARY);
    expect(panel.getByTestId("notification-reviews")).toHaveAttribute("title", "數字是全部專案的合計；點進去前往這個專案的執行頁");
    expect(panel.getByTestId("notification-alerts")).toHaveAttribute("title", "數字是全部專案的合計；點進去前往這個專案的監控頁");
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
