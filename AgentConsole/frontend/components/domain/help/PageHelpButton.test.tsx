import type { ReactElement, ReactNode } from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RootLayout from "@/app/layout";
import { LEGEND } from "@/components/domain/issues/tests/issues.fixtures";
import type { Role } from "@/lib/api/types";
import { clearSession, resetSessionCache } from "@/lib/auth/store";
import { HELP_PAGES, HELP_ROUTES, PENDING_HELP_PAGES } from "@/lib/help/registry";
import type { PageHelp } from "@/lib/help/types";
import { signIn, stubApi, type ApiCall } from "@/tests/helpers/api";

/**
 * 「本頁說明」鈕與其接入（TCS-PageHelp-20261027 R-PH-21、R-PH-24、R-PH-25、R-PH-26；載具 HB〔RL〕，輪 1b 建）：
 *  - AT-PH-01-1-1、01-1-E-1：全站一顆、同一個 testid，在頂列右側群組末端（通知鈴與待審批佇列之後），內容區、導覽區與底部都沒有；
 *  - AT-PH-01-2-1、01-2-E-1：/login、未登入、無對應說明項、前綴相似的路徑、待寫頁的路由都不渲染；已寫頁的路由恰一顆；
 *  - AT-PH-01-3-1、01-3-E-1：VIEWER、OPERATOR、ADMIN 都看得到、開得了、內容相同；VIEWER 開議題中心說明仍送詞表請求；對話框內沒有任何寫入類控制項；
 *  - AT-PH-01-4-1、01-4-E-1：路由變更即關閉、A→B→A 不重開、重繪（含頂列搜尋框狀態變動）不關；
 *  - AT-PH-01-5-1、01-5-E-1：可存取名稱含可見文字「本頁說明」、<768 文字改 sr-only、與公告列的「幫助中心」區別；
 *  - AT-PH-07-1-1、07-1-E-1：Enter、空白鍵開啟且焦點進入對話框，Esc 與關閉鈕各關一次且焦點回到該鈕。
 * 夾具：RL＝RootLayout 的 body 組裝結果（同 layout.test.tsx）；`next/navigation` 以可變的 pathname 替身取代；fetch 以 `stubApi` 提供頂列的兩個輪詢端點與議題中心頁（含 legend），其餘 404；
 * QueryClient 是 app 預設（真 Providers，D-PH-16，不用 makeClient）。
 * 非同步慣例（TCS §5.1）：TopRegion 以 next/dynamic 載入 PageHelpButton，所以「出現」類斷言一律 findBy／waitFor，「不渲染」類斷言一律先 settle() 再斷言，
 * 且每個此類 AT 內另有一個同形態的對照組（有鈕的路由）先 findBy 到鈕，證明動態載入本身已完成（防空轉）。
 * 判定指令：npx vitest run components/domain/help/PageHelpButton.test.tsx -t "<AT 底線形>"
 */

// ── Next 路由相關：測試環境沒有 App Router，換成可控的替身（同 layout.test.tsx）────────────────────
let pathname = "/projects";
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

/** RootLayout 的 <html><body>…</body></html> 不適合塞進測試容器；取出 body 內的組裝結果來渲染。 */
function layoutBody(children: ReactNode): ReactElement {
  const html = RootLayout({ children }) as ReactElement<{ children: ReactElement<{ children: ReactElement }> }>;
  return html.props.children.props.children;
}

const SUMMARY = { pendingSignoffs: 0, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null };
const EMPTY_PAGE = { content: [], page: 0, size: 100, totalElements: 0, totalPages: 0 };
const ISSUES_PAGE = {
  schemaRev: 1,
  kind: "issues",
  generatedAt: "2026-10-27T10:00:00+08:00",
  headSha: null,
  items: [],
  nextSince: null,
  truncated: false,
  ne: [],
  problems: [],
  legend: LEGEND,
  summary: { total: 0, byStatus: {}, byTab: {}, unmapped: 0 },
};

/** 頂列的輪詢端點與議題中心頁；其餘 404（頂列對 4xx 不重試，不影響說明鈕）。 */
function stubShell(): { calls: ApiCall[] } {
  return stubApi((call) => {
    if (call.path === "/api/v1/projects") return { data: EMPTY_PAGE };
    if (call.path === "/api/v1/notifications/summary") return { data: SUMMARY };
    if (call.path === "/api/v1/issues") return { data: ISSUES_PAGE };
    return undefined;
  });
}

beforeEach(() => {
  pathname = "/projects";
  resetSessionCache();
  clearSession();
});

/** 讓動態載入與查詢有機會跑完（TCS §5.1 非同步慣例）。 */
const settle = () =>
  act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 50));
  });

const registered = (id: "projects" | "settings" | "issues"): PageHelp => HELP_PAGES[id] as PageHelp;
const dialogName = (id: "projects" | "settings" | "issues") => `${registered(id).title}・本頁說明`;
const region = (name: "top" | "tools" | "content" | "bottom"): HTMLElement => document.querySelector(`[data-region="${name}"]`) as HTMLElement;
const helpButtons = () => document.querySelectorAll('[data-testid="page-help-open"]');
const findButton = () => screen.findByTestId("page-help-open");

/** 對每條 HELP_ROUTES 樣板取具體路徑：[projectId]→p1、[goalId]→g1、[taskId]→t1。 */
const concretePath = (template: string): string => template.replace("[projectId]", "p1").replace("[goalId]", "g1").replace("[taskId]", "t1");

// ── AC-PH-01-1：全站一顆、在頂列右側群組末端 ────────────────────────────────────────────

describe("AT_PH_01_1 說明鈕：全站一顆、同一個 testid（R-PH-24）", () => {
  it("AT_PH_01_1_1 /projects、OPERATOR：[data-region=top] 內恰一個 page-help-open（BUTTON、可見文字含「本頁說明」），與通知鈴、待審批佇列連結同一個父節點且在兩者之後；內容區沒有", async () => {
    stubShell();
    signIn("OPERATOR");
    render(layoutBody(<p>頁面內容</p>));
    const button = await findButton();
    const top = region("top");
    expect(top.querySelectorAll('[data-testid="page-help-open"]')).toHaveLength(1);
    expect(button.tagName).toBe("BUTTON");
    expect(button).toHaveTextContent("本頁說明");

    const bell = screen.getByTestId("bell-trigger");
    const queue = screen.getByRole("link", { name: /^待審批佇列/ });
    expect(button.parentElement, "與通知鈴同一個父節點（右側群組）").toBe(bell.parentElement);
    expect(button.parentElement, "與待審批佇列連結同一個父節點").toBe(queue.parentElement);
    expect(bell.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING, "在通知鈴之後").toBeTruthy();
    expect(queue.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING, "在待審批佇列之後").toBeTruthy();
    expect(region("content").querySelectorAll('[data-testid="page-help-open"]')).toHaveLength(0);
  });

  it("AT_PH_01_1_E_1 依序把 pathname 改成 /settings、/issues 並 rerender：每次整頁仍恰一個 page-help-open；tools、bottom、content 三區內各 0 個", async () => {
    stubShell();
    signIn("OPERATOR");
    const view = render(layoutBody(<p>x</p>));
    await findButton();
    for (const next of ["/projects", "/settings", "/issues"]) {
      pathname = next;
      view.rerender(layoutBody(<p>x</p>));
      await findButton();
      await settle();
      expect(helpButtons(), `${next} 整頁的鈕數`).toHaveLength(1);
      for (const name of ["tools", "bottom", "content"] as const) expect(region(name).querySelectorAll('[data-testid="page-help-open"]'), `${next} 的 ${name} 區`).toHaveLength(0);
    }
  });
});

// ── AC-PH-01-2：不渲染的情形 ───────────────────────────────────────────────────────────

describe("AT_PH_01_2 說明鈕不渲染的情形（R-PH-24、R-PH-07）", () => {
  it("AT_PH_01_2_1 已登入於 /login、未登入於 /projects、已登入於 /unknown、已登入於 /projects-x 都沒有鈕；對照組（已登入於 /projects）恰一顆", async () => {
    // 對照組先做：證明動態載入本身已完成，後面的「0 個」才不是空洞的真
    stubShell();
    signIn("OPERATOR");
    const control = render(layoutBody(<p>x</p>));
    await findButton();
    expect(helpButtons(), "(e) 對照組").toHaveLength(1);
    control.unmount();

    const cases: Array<{ name: string; path: string; role: Role | null }> = [
      { name: "(a) 已登入於 /login", path: "/login", role: "OPERATOR" },
      { name: "(b) 未登入於 /projects", path: "/projects", role: null },
      { name: "(c) 已登入於 /unknown", path: "/unknown", role: "OPERATOR" },
      { name: "(d) 已登入於 /projects-x", path: "/projects-x", role: "OPERATOR" },
    ];
    for (const { name, path, role } of cases) {
      resetSessionCache();
      clearSession();
      if (role !== null) signIn(role);
      pathname = path;
      stubShell();
      const view = render(layoutBody(<p>x</p>));
      await settle();
      expect(helpButtons(), name).toHaveLength(0);
      view.unmount();
    }
  });

  it("AT_PH_01_2_E_1 HELP_ROUTES 的每個樣板代入 p1／g1／t1：每條路由的鈕數＝（它的說明 id 在 HELP_PAGES 內 ? 1 : 0）；待寫頁的路由 0 個、已寫頁的路由 1 個，至少一條為 1", async () => {
    stubShell();
    signIn("OPERATOR");
    const counts: Array<{ template: string; id: string; count: number; written: boolean }> = [];
    for (const [template, id] of Object.entries(HELP_ROUTES)) {
      pathname = concretePath(template);
      const view = render(layoutBody(<p>x</p>));
      const written = HELP_PAGES[id] !== undefined;
      if (written) await findButton();
      else await settle();
      counts.push({ template, id, count: helpButtons().length, written });
      view.unmount();
    }
    expect(counts.length, "路由數").toBe(Object.keys(HELP_ROUTES).length);
    for (const { template, id, count, written } of counts) expect(count, `${template}（${id}）`).toBe(written ? 1 : 0);
    expect(
      counts.some((entry) => entry.count === 1),
      "防反空轉：至少一條路由有鈕",
    ).toBe(true);
    if (PENDING_HELP_PAGES.length === 0)
      expect(
        counts.every((entry) => entry.count === 1),
        "沒有待寫頁時全部路由都有鈕",
      ).toBe(true);
  });
});

// ── AC-PH-01-3：三種角色 ───────────────────────────────────────────────────────────────

describe("AT_PH_01_3 三種角色都看得到、開得了、內容相同（R-PH-24）", () => {
  it("AT_PH_01_3_1 VIEWER、OPERATOR、ADMIN 各登入、/projects：鈕存在且可用、點開有名稱「<頁名>・本頁說明」的對話框；三份對話框的文字（空白正規化）逐字相同", async () => {
    const texts: string[] = [];
    for (const role of ["VIEWER", "OPERATOR", "ADMIN"] as const) {
      stubShell();
      signIn(role);
      const view = render(layoutBody(<p>x</p>));
      const button = await findButton();
      expect(button, role).toBeEnabled();
      await userEvent.setup().click(button);
      const dialog = await screen.findByRole("dialog", { name: dialogName("projects") });
      texts.push((dialog.textContent ?? "").replace(/\s+/g, " ").trim());
      view.unmount();
    }
    expect(texts[0].length).toBeGreaterThan(0);
    expect(texts[1], "OPERATOR 與 VIEWER 的內容相同").toBe(texts[0]);
    expect(texts[2], "ADMIN 與 VIEWER 的內容相同").toBe(texts[0]);
  });

  it("AT_PH_01_3_E_1 VIEWER 在 /issues：鈕無 disabled 與 aria-disabled；開啟後詞表請求仍送出一次（前端不以角色擋）；對話框內沒有 input、textarea、select、送出鈕", async () => {
    const { calls } = stubShell();
    signIn("VIEWER");
    pathname = "/issues";
    render(layoutBody(<p>x</p>));
    const button = await findButton();
    expect(button).not.toBeDisabled();
    expect(button).not.toHaveAttribute("aria-disabled");
    await userEvent.setup().click(button);
    const dialog = await screen.findByRole("dialog", { name: dialogName("issues") });
    await within(dialog).findByTestId("page-help-legend-statuses");
    const legendCalls = calls.filter((call) => call.method === "GET" && call.path === "/api/v1/issues");
    expect(legendCalls).toHaveLength(1);
    expect(legendCalls[0].query.get("limit")).toBe("1");
    expect(dialog.querySelectorAll("input, textarea, select, button[type=submit]"), "沒有寫入類控制項").toHaveLength(0);
  });
});

// ── AC-PH-01-4：路由變更即關閉、重繪不關 ─────────────────────────────────────────────────

describe("AT_PH_01_4 路由變更即關閉；重繪不關閉（R-PH-24）", () => {
  it("AT_PH_01_4_1 /projects 開啟→改 /settings：已關閉；不按任何鈕直接改回 /projects：仍是關閉（A→B→A 不重開）；再改 /settings 並按鈕：開的是設定頁說明，找不到專案管理說明的文字", async () => {
    stubShell();
    signIn("OPERATOR");
    const user = userEvent.setup();
    const view = render(layoutBody(<p>x</p>));
    await user.click(await findButton());
    await screen.findByRole("dialog", { name: dialogName("projects") });

    pathname = "/settings";
    view.rerender(layoutBody(<p>x</p>));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());

    // (3) 不按任何鈕：在 B 按鈕會把「開在哪一頁」覆寫成 B，掩蓋 A→B→A 誤重開的缺陷
    pathname = "/projects";
    view.rerender(layoutBody(<p>x</p>));
    await findButton();
    await settle();
    expect(screen.queryByRole("dialog"), "A→B→A 不得重開").toBeNull();

    pathname = "/settings";
    view.rerender(layoutBody(<p>x</p>));
    await user.click(await findButton());
    expect(await screen.findByRole("dialog", { name: dialogName("settings") })).toBeInTheDocument();
    expect(document.body.textContent, "不殘留舊頁內容").not.toContain(registered("projects").purpose[0]);
  });

  it("AT_PH_01_4_E_1 對話框開啟中且 pathname 不變：同一棵樹 rerender、頂列搜尋框狀態變動（讓 TopRegion 自身重繪），對話框都仍開啟、內容不變", async () => {
    stubShell();
    signIn("OPERATOR");
    const view = render(layoutBody(<p>x</p>));
    await userEvent.setup().click(await findButton());
    const dialog = await screen.findByRole("dialog", { name: dialogName("projects") });
    const before = dialog.textContent;

    view.rerender(layoutBody(<p>x</p>));
    expect(screen.getByRole("dialog", { name: dialogName("projects") })).toBe(dialog);
    expect(dialog.textContent).toBe(before);

    fireEvent.change(screen.getByLabelText("搜尋專案、目標、任務"), { target: { value: "abc" } });
    await settle();
    expect(screen.getByRole("dialog", { name: dialogName("projects") }), "頂列重繪不關閉").toBe(dialog);
    expect(dialog.textContent).toBe(before);
  });
});

// ── AC-PH-01-5：可存取名稱含可見文字 ─────────────────────────────────────────────────────

describe("AT_PH_01_5 可存取名稱含可見文字（R-PH-25）", () => {
  it("AT_PH_01_5_1 /projects：名稱含「本頁說明」的按鈕恰一個；文字所在元素帶 max-md:sr-only；圖示 svg 帶 aria-hidden=true；沒有 aria-label 與 title（名稱來自文字節點）", async () => {
    stubShell();
    signIn("OPERATOR");
    render(layoutBody(<p>x</p>));
    await findButton();
    const buttons = screen.getAllByRole("button", { name: /本頁說明/ });
    expect(buttons).toHaveLength(1);
    const button = buttons[0];
    const text = within(button).getByText("本頁說明");
    expect(text.className).toContain("max-md:sr-only");
    expect(button.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
    expect(button.getAttribute("aria-label"), "名稱來自文字節點，不另設 aria-label").toBeNull();
    expect(button.getAttribute("title"), "不只靠 title 取名").toBeNull();
  });

  it("AT_PH_01_5_E_1 名稱恰為「本頁說明」（不因 sr-only 而變），不含「幫助中心」「說明文件」；公告列的「幫助中心」仍是不可點的 span", async () => {
    stubShell();
    signIn("OPERATOR");
    render(layoutBody(<p>x</p>));
    await findButton();
    expect(screen.getByRole("button", { name: "本頁說明" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /幫助中心|說明文件/ })).toBeNull();
    const announcement = screen.getByText("幫助中心", { exact: true });
    expect(announcement.tagName).toBe("SPAN");
    expect(announcement.closest("a, button"), "公告列的字樣不可點").toBeNull();
  });
});

// ── AC-PH-07-1：鍵盤 ────────────────────────────────────────────────────────────────────

describe("AT_PH_07_1 鍵盤開關與焦點歸還（R-PH-26）", () => {
  it("AT_PH_07_1_1 焦點在說明鈕按 Enter：對話框開啟且焦點進入對話框；按 Esc：關閉且焦點回到該鈕；以滑鼠點開再按 Esc，焦點同樣回到該鈕", async () => {
    stubShell();
    signIn("OPERATOR");
    const user = userEvent.setup();
    render(layoutBody(<p>x</p>));
    const button = await findButton();

    button.focus();
    await user.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", { name: dialogName("projects") });
    expect(dialog.contains(document.activeElement), "焦點進入對話框").toBe(true);
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(document.activeElement, "Esc 關閉後焦點回到鈕").toBe(button);

    await user.click(button);
    await screen.findByRole("dialog", { name: dialogName("projects") });
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(document.activeElement, "滑鼠點開再按 Esc，焦點同樣回到鈕").toBe(button);
  });

  it("AT_PH_07_1_E_1 空白鍵可開；右上「關閉」鈕可關；兩種關法焦點都回到說明鈕；連開連關三次後仍恰一個對話框、鈕仍恰一顆", async () => {
    stubShell();
    signIn("OPERATOR");
    const user = userEvent.setup();
    render(layoutBody(<p>x</p>));
    const button = await findButton();

    button.focus();
    await user.keyboard(" ");
    await screen.findByRole("dialog", { name: dialogName("projects") });
    await user.click(screen.getByRole("button", { name: "關閉" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(document.activeElement, "關閉鈕關閉後焦點回到鈕").toBe(button);

    for (let round = 1; round <= 3; round += 1) {
      await user.click(button);
      expect(await screen.findAllByRole("dialog"), `第 ${round} 次開啟：恰一個對話框`).toHaveLength(1);
      if (round % 2 === 1) await user.keyboard("{Escape}");
      else await user.click(screen.getByRole("button", { name: "關閉" }));
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
      expect(helpButtons(), `第 ${round} 次關閉後：鈕仍恰一顆`).toHaveLength(1);
      expect(document.activeElement).toBe(button);
    }
  });
});
