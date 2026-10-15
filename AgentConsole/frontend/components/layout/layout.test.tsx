import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import type { ReactElement, ReactNode } from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RootLayout from "@/app/layout";
import { clearSession, resetSessionCache, saveSession } from "@/lib/auth/store";

// ── Next 路由相關：測試環境沒有 App Router，換成可控的替身 ───────────────────────
let pathname = "/";
vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const ROOT = process.cwd();

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (["node_modules", ".next", "tests"].includes(name)) continue;
      walk(full, out);
    } else if (/\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}
const rel = (f: string) => path.relative(ROOT, f).split(path.sep).join("/");

describe("四區塊共用版面只住 app/layout.tsx（UI-LAY-05）", () => {
  const REGION = /\b(TopRegion|ToolsRegion|ContentRegion|BottomRegion)\b/;

  it("除了 app/layout.tsx，沒有任何 app 下的檔案提到四個區塊（等同 grep 閘門回空）", () => {
    const offenders = walk(path.join(ROOT, "app"))
      .filter((f) => rel(f) !== "app/layout.tsx")
      .filter((f) => REGION.test(readFileSync(f, "utf-8")))
      .map(rel);
    expect(offenders).toEqual([]);
  });

  it("元件、hooks、lib 也不得 import 區塊（區塊不是可重用元件，全站只組裝一次）", () => {
    const files = ["components", "hooks", "lib"].flatMap((d) => walk(path.join(ROOT, d)));
    const offenders = files
      .filter((f) => !rel(f).startsWith("components/layout/"))
      .filter((f) => /from\s+["'][^"']*layout\/(Top|Tools|Content|Bottom)Region["']/.test(readFileSync(f, "utf-8")))
      .map(rel);
    expect(offenders).toEqual([]);
  });

  it("app/layout.tsx 恰好 import 四個區塊各一次", () => {
    const src = readFileSync(path.join(ROOT, "app/layout.tsx"), "utf-8");
    for (const name of ["TopRegion", "ToolsRegion", "ContentRegion", "BottomRegion"]) {
      expect(src.match(new RegExp(`from "@/components/layout/${name}"`, "g")), name).toHaveLength(1);
      expect(src.match(new RegExp(`<${name}[ />]`, "g")), `<${name}>`).toHaveLength(1);
    }
  });

  it("components/layout 底下恰好四個元件檔（每個共用區塊只有一個元件檔）", () => {
    const files = readdirSync(path.join(ROOT, "components/layout")).filter(
      (f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx"),
    );
    expect(files.sort()).toEqual(["BottomRegion.tsx", "ContentRegion.tsx", "ToolsRegion.tsx", "TopRegion.tsx"]);
  });
});

/** RootLayout 的 <html><body>…</body></html> 不適合塞進測試容器；取出 body 內的組裝結果來渲染。 */
function layoutBody(children: ReactNode): ReactElement {
  const html = RootLayout({ children }) as ReactElement<{ children: ReactElement<{ children: ReactElement }> }>;
  return html.props.children.props.children;
}

/** 通知摘要（契約 §1.4）：數字故意取得和專案資料算出來的不同（草案專案只有 1 個），證明頂列徽章讀的是這支端點。 */
const SUMMARY = { pendingSignoffs: 7, pendingReviews: 2, unacknowledgedAlerts: 3, bridgeConnected: null, bridgeCheckedAt: null };

function stubApi(summary: Record<string, unknown> = SUMMARY) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const data = url.includes("/api/v1/projects?")
        ? {
            content: [
              { id: "p1", name: "專案甲", status: "EXECUTING", signedOff: true, goalsCount: 1, tasksCount: 2, tasksDone: 1, autonomyLevel: 3, executionPath: "/x", updatedAt: "2026-01-01T00:00:00Z" },
              { id: "p2", name: "專案乙", status: "DRAFT", signedOff: false, goalsCount: 0, tasksCount: 0, tasksDone: 0, autonomyLevel: 3, executionPath: "/y", updatedAt: "2026-01-01T00:00:00Z" },
            ],
            page: 0, size: 100, totalElements: 2, totalPages: 1,
          }
        : url.includes("/api/v1/notifications/summary")
          ? summary
          : [];
      return new Response(JSON.stringify({ code: 200, message: "success", data }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }),
  );
}

beforeEach(() => {
  pathname = "/";
  resetSessionCache();
  clearSession();
});

describe("RootLayout 渲染：四區塊各一份", () => {
  it("已登入：Top／Tools／Content／Bottom 各出現恰好一次，children 在 Content 內", async () => {
    stubApi();
    saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role: "OPERATOR", username: "operator" });
    render(layoutBody(<p>頁面內容</p>));

    for (const region of ["top", "tools", "content", "bottom"]) {
      expect(document.querySelectorAll(`[data-region="${region}"]`), region).toHaveLength(1);
    }
    expect(screen.getAllByRole("banner")).toHaveLength(1);
    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getAllByRole("contentinfo")).toHaveLength(1);
    expect(screen.getAllByRole("navigation", { name: "主導覽" })).toHaveLength(1);
    expect(within(screen.getByRole("main")).getByText("頁面內容")).toBeInTheDocument();

    // 導覽六項（設計稿 Sidebar）
    const nav = within(screen.getByRole("navigation", { name: "主導覽" }));
    for (const label of ["儀表板", "專案管理", "BRD/PRD 匯入", "執行中心", "監控中心", "系統設定"]) {
      expect(nav.getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(nav.getByRole("link", { name: "儀表板" })).toHaveAttribute("aria-current", "page");
    expect(nav.getByRole("link", { name: "儀表板" })).toHaveAttribute("href", "/");
    expect(nav.getByRole("link", { name: "BRD/PRD 匯入" })).toHaveAttribute("href", "/import");
    expect(nav.getByRole("link", { name: "系統設定" })).toHaveAttribute("href", "/settings");

    // 專案資料到齊後：「我的專案」rail、頂列 chips；徽章取自通知摘要——
    // signoff 佇列鈕＝pendingSignoffs（7，不是專案算出的 1），通知鈴＝pendingReviews＋unacknowledgedAlerts（2＋3）
    expect(await screen.findByTestId("signoff-badge")).toHaveTextContent("7");
    expect(screen.getByTestId("bell-badge")).toHaveTextContent("5");
    const rail = within(screen.getByTestId("project-rail"));
    expect(rail.getByRole("link", { name: "專案甲" })).toHaveAttribute("href", "/projects/p1");
    // 「執行中心」「監控中心」從目前專案（列表第一筆）進入
    expect(nav.getByRole("link", { name: "執行中心" })).toHaveAttribute("href", "/projects/p1/execute");
    expect(nav.getByRole("link", { name: "監控中心" })).toHaveAttribute("href", "/projects/p1/monitor");

    // 底部列：連線狀態與版本
    expect(screen.getByTestId("status-console-api")).toBeInTheDocument();
    // Bridge 連線點＝通知摘要的 bridgeConnected／bridgeCheckedAt；摘要兩欄為 null（從未探測）→ 灰點「未知」
    expect(screen.getByTestId("status-Engine Bridge")).toHaveTextContent("未知");
    expect(screen.getByTestId("app-version")).toHaveTextContent(/^Console v/);
  });

  it("Engine Bridge 連線點（契約 §1.4.1、§4.5 G-03）：bridgeConnected true＝綠點「已連線」並在 title 帶最近探測時間；false＝紅點「未連線」；null＝灰點「未知」", async () => {
    const dotOf = (el: HTMLElement) => el.querySelector("span[aria-hidden]")?.className ?? "";

    stubApi({ ...SUMMARY, bridgeConnected: true, bridgeCheckedAt: new Date(2026, 9, 15, 16, 30, 12).toISOString() });
    saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role: "OPERATOR", username: "operator" });
    const online = render(layoutBody(<p>x</p>));
    await waitFor(() => expect(screen.getByTestId("status-Engine Bridge")).toHaveTextContent("已連線"));
    const up = screen.getByTestId("status-Engine Bridge");
    expect(up).toHaveAttribute("data-state", "online");
    expect(dotOf(up)).toContain("bg-wg-primary");
    expect(up).toHaveAttribute("title", "最近一次探測：16:30:12");
    // 頂列公告列是同一個來源（兩處都顯示同一個狀態）
    expect(screen.getAllByText("Engine Bridge · 已連線")).toHaveLength(2);
    online.unmount();

    stubApi({ ...SUMMARY, bridgeConnected: false, bridgeCheckedAt: new Date(2026, 9, 15, 16, 31, 0).toISOString() });
    resetSessionCache();
    saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role: "OPERATOR", username: "operator" });
    const offline = render(layoutBody(<p>x</p>));
    await waitFor(() => expect(screen.getByTestId("status-Engine Bridge")).toHaveTextContent("未連線"));
    const down = screen.getByTestId("status-Engine Bridge");
    expect(down).toHaveAttribute("data-state", "offline");
    expect(dotOf(down)).toContain("bg-wg-error");
    offline.unmount();

    stubApi({ ...SUMMARY, bridgeConnected: null, bridgeCheckedAt: null });
    resetSessionCache();
    saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role: "OPERATOR", username: "operator" });
    render(layoutBody(<p>x</p>));
    await waitFor(() => expect(screen.getByTestId("status-Engine Bridge")).toHaveTextContent("未知"));
    const unknown = screen.getByTestId("status-Engine Bridge");
    expect(unknown).toHaveAttribute("data-state", "unknown");
    expect(dotOf(unknown)).toContain("bg-wg-disabled-text");
    expect(unknown.getAttribute("title")).toContain("尚未探測過");
  });

  it("通知摘要查詢失敗（例如後端還沒提供）：Bridge 連線點是「未知」，不當成未連線也不假裝已連線", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        url.includes("/api/v1/notifications/summary")
          ? new Response(JSON.stringify({ code: 500, message: "伺服器錯誤", errors: [] }), { status: 500, headers: { "content-type": "application/json" } })
          : new Response(JSON.stringify({ code: 200, message: "success", data: url.includes("/api/v1/projects?") ? { content: [], page: 0, size: 100, totalElements: 0, totalPages: 0 } : [] }), { status: 200, headers: { "content-type": "application/json" } }),
      ),
    );
    saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role: "OPERATOR", username: "operator" });
    render(layoutBody(<p>x</p>));
    await waitFor(() => expect(screen.getByTestId("status-Engine Bridge")).toHaveAttribute("data-state", "unknown"), { timeout: 4000 });
  });

  it("在專案頁時，執行／監控導覽指向網址中的專案", async () => {
    stubApi();
    pathname = "/projects/p2/goals";
    saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role: "ADMIN", username: "admin" });
    render(layoutBody(<p>x</p>));
    const nav = within(screen.getByRole("navigation", { name: "主導覽" }));
    expect(nav.getByRole("link", { name: "執行中心" })).toHaveAttribute("href", "/projects/p2/execute");
    expect(nav.getByRole("link", { name: "專案管理" })).toHaveAttribute("aria-current", "page");
  });

  it("未登入的 /login：只剩品牌列與內容，沒有側欄、搜尋與動作；底部列仍在", () => {
    pathname = "/login";
    render(layoutBody(<p>登入表單</p>));
    expect(document.querySelectorAll('[data-region="top"]')).toHaveLength(1);
    expect(document.querySelectorAll('[data-region="tools"]')).toHaveLength(0);
    expect(document.querySelectorAll('[data-region="content"]')).toHaveLength(1);
    expect(document.querySelectorAll('[data-region="bottom"]')).toHaveLength(1);
    expect(screen.queryByRole("search")).toBeNull();
    expect(screen.getByText("登入表單")).toBeInTheDocument();
  });
});
