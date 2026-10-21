import type { ReactElement, ReactNode } from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RootLayout from "@/app/layout";
import { SiView } from "@/components/domain/si/SiView";
import { clearSession, resetSessionCache } from "@/lib/auth/store";
import { GA, signInAs, stubSiApi, type SiStub } from "@/tests/helpers/si";

// ── Next 路由相關：測試環境沒有 App Router，換成可控且穩定的替身 ───────────────────
const nav = vi.hoisted(() => ({ pathname: "/self-improving", replace: vi.fn(), push: vi.fn(), back: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => nav.pathname,
  useRouter: () => nav,
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

/** RootLayout 的 <html><body>…</body></html> 不適合塞進測試容器；取出 body 內的組裝結果來渲染（同 layout.test.tsx）。 */
function layoutBody(children: ReactNode): ReactElement {
  const html = RootLayout({ children }) as ReactElement<{ children: ReactElement<{ children: ReactElement }> }>;
  return html.props.children.props.children;
}

beforeEach(() => {
  nav.pathname = "/self-improving";
  window.history.pushState({}, "", "/self-improving");
  resetSessionCache();
  clearSession();
});

describe("AT_932_4_2 未登入開 /self-improving：導向登入且不發 SI 請求（R12）", () => {
  it("AT_932_4_2 router.replace 帶 next、SiView 不渲染、沒有任何 SI 請求", async () => {
    const stub: SiStub = { fixture: GA, overrides: {}, calls: [] };
    stubSiApi(stub);
    render(layoutBody(<SiView />));

    await waitFor(() => expect(nav.replace).toHaveBeenCalledTimes(1));
    expect(nav.replace).toHaveBeenCalledWith(`/login?next=${encodeURIComponent("/self-improving")}`);
    // 內容區是載入中指示（Spinner），SiView 沒有被渲染，也沒有任何對 SI 端點的請求
    expect(screen.queryByTestId("si-view")).toBeNull();
    expect(within(screen.getByRole("main")).getByRole("status")).toBeInTheDocument();
    // 讓可能的後續 effect 與查詢跑完，再確認從頭到尾沒有 SI 請求
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(stub.calls.filter((c) => c.path.startsWith("/api/v1/si/"))).toEqual([]);
    expect(nav.replace).toHaveBeenCalledTimes(1);
  });

  it("AT_932_4_2 對照組：以 OPERATOR 的 session 渲染時，si-view 存在且對 /api/v1/si/status 有請求", async () => {
    const stub: SiStub = { fixture: GA, overrides: {}, calls: [] };
    signInAs("OPERATOR");
    stubSiApi(stub);
    render(layoutBody(<SiView />));

    expect(await screen.findByTestId("si-view")).toBeInTheDocument();
    await waitFor(() => expect(stub.calls.map((c) => c.path)).toContain("/api/v1/si/status"));
    expect(nav.replace).not.toHaveBeenCalled();
    // 同一個版面裡，導覽有「自我進化」入口（登記表第七項）並在 /self-improving 時為 active
    const link = within(screen.getByRole("navigation", { name: "主導覽" })).getByRole("link", { name: "自我進化" });
    expect(link).toHaveAttribute("href", "/self-improving");
    expect(link).toHaveAttribute("aria-current", "page");
  });
});
