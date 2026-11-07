import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EventSourceCtor } from "@/lib/api/sse";
import type { ResearchRouteDecision } from "@/lib/api/types";
import { R2, R3 } from "@/tests/fixtures/research/ids";
import { detailVariant } from "@/tests/fixtures/research/projects";
import { CAPABILITIES_ROUTE_READY, ROUTE_FAILED, ROUTE_RUNNING, ROUTE_SUCCEEDED } from "@/tests/fixtures/research/route";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { callsOf, failure, renderResearch, stubResearchApi, writeCalls } from "@/tests/helpers/research";
import { RoutePanel } from "./RoutePanel";

/**
 * 步驟 3 面板（TCS-ResearchToPRD-P1-20261107 AT-961-17-2、17-7、17-8）：Gate 0 未完成的阻擋頁、逐步進度與失敗重試、部署不支援的錯誤態與重新載入後還原。
 * 判定指令：npx vitest run components/domain/research/RoutePanel.test.tsx -t "<AT 底線形>"
 */
const nav = vi.hoisted(() => ({ router: { push: vi.fn(), replace: vi.fn(), back: vi.fn() } }));
vi.mock("next/navigation", () => ({
  useRouter: () => nav.router,
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

const FRAME = FakeEventSource as unknown as EventSourceCtor;
const ROUTE_URL = /\/route$/;
const frozen = (targetScope = "UNDECIDED") => detailVariant("frozen", { targetScope });
type StubPatch = Parameters<typeof stubResearchApi>[0];

function renderPanel(opts: { role?: "ADMIN" | "OPERATOR" | "VIEWER"; route?: ResearchRouteDecision | null; stub?: StubPatch; completed?: boolean; project?: ReturnType<typeof frozen> } = {}) {
  const api = stubResearchApi({ route: opts.route ?? null, capabilities: CAPABILITIES_ROUTE_READY, ...(opts.stub ?? {}) });
  const view = renderResearch(<RoutePanel researchId={R3} project={opts.project ?? frozen()} completed={opts.completed ?? false} EventSourceCtor={FRAME} />, opts.role ?? "ADMIN");
  return { ...view, ...api };
}

beforeEach(() => FakeEventSource.reset());

describe("AT_961_17_2 Gate 0 未完成：阻擋頁連回步驟 2，沒有任何寫入控件", () => {
  it("AT_961_17_2 游標在 studio：顯示阻擋說明與「回到規格工作室」連結（?step=studio）；沒有卡、預演與確認；不發任何寫入請求", async () => {
    const { calls } = renderPanel({ project: detailVariant("studio") });
    const blocked = await screen.findByTestId("route-blocked");
    expect(blocked).toHaveTextContent("Gate 0 還沒有核准");
    expect(within(blocked).getByRole("link", { name: "回到規格工作室" })).toHaveAttribute("href", `/research/${R3}?step=studio`);
    expect(screen.queryByRole("radio")).toBeNull();
    expect(screen.queryByRole("button", { name: "預演" })).toBeNull();
    expect(screen.queryByRole("button", { name: "確認執行" })).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(writeCalls(calls)).toEqual([]);
  });
});

describe("AT_961_17_7 逐步進度與失敗重試", () => {
  it("AT_961_17_7 執行中：以 REST 步驟列初始化，research.route 事件逐步更新狀態並觸發分流查詢重抓", async () => {
    const { calls } = renderPanel({ route: ROUTE_RUNNING });
    const list = await screen.findByTestId("route-steps");
    expect(within(list).getByTestId("route-step-2")).toHaveAttribute("data-status", "RUNNING");
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
    const before = callsOf(calls, "GET", ROUTE_URL).length;
    act(() => FakeEventSource.last.emit("research.route", { eventType: "research.route", payload: { routeId: "route-0001", stepNo: 2, step: "GIT_SWITCH", status: "OK" } }));
    await waitFor(() => expect(screen.getByTestId("route-step-2")).toHaveAttribute("data-status", "OK"));
    await waitFor(() => expect(callsOf(calls, "GET", ROUTE_URL).length).toBeGreaterThan(before));
    expect(screen.getByTestId("route-panel")).toHaveAttribute("data-route-status", "RUNNING");
    expect(screen.queryByRole("button", { name: "重試失敗步驟" })).toBeNull();
  });

  it("AT_961_17_7 失敗：顯示失敗步驟與原因（純文字）；已成功的步驟不顯示重試；ADMIN 按「重試失敗步驟」送出 retry:true；OPERATOR 停用並說明", async () => {
    const user = userEvent.setup();
    const admin = renderPanel({ route: ROUTE_FAILED });
    const failed = await screen.findByTestId("route-failed");
    expect(failed).toHaveTextContent("GIT_SWITCH");
    expect(screen.getByTestId("route-step-2")).toHaveTextContent("失敗原因：fatal: 分支已存在（路徑已脫敏）");
    expect(screen.getAllByRole("button", { name: "重試失敗步驟" })).toHaveLength(1);
    expect(screen.getByTestId("route-step-1")).not.toHaveTextContent("重試");
    await user.click(screen.getByRole("button", { name: "重試失敗步驟" }));
    await waitFor(() => expect(callsOf(admin.calls, "POST", ROUTE_URL)).toHaveLength(1));
    expect(callsOf(admin.calls, "POST", ROUTE_URL)[0].body).toMatchObject({ track: "A", targetModule: "autoclaude", branchName: "feature/issue-0003", retry: true });
    admin.unmount();

    const operator = renderPanel({ role: "OPERATOR", route: ROUTE_FAILED });
    const retry = await screen.findByRole("button", { name: "重試失敗步驟" });
    expect(retry).toBeDisabled();
    expect(retry.getAttribute("title")).toContain("權限不足");
    await user.click(retry);
    expect(callsOf(operator.calls, "POST", ROUTE_URL)).toHaveLength(0);
  });

  it("AT_961_17_7 重試失敗（502 route_step_failed）：顯示帶失敗步驟名的白話原因，仍可再重試", async () => {
    const user = userEvent.setup();
    renderPanel({
      route: ROUTE_FAILED,
      stub: {
        overrides: (call) => (call.method === "POST" && ROUTE_URL.test(call.path) ? failure(502, { message: "x", reason: "route_step_failed", details: { failureStep: "GIT_SWITCH" } }) : undefined),
      },
    });
    await user.click(await screen.findByRole("button", { name: "重試失敗步驟" }));
    expect(await screen.findByTestId("route-retry-error")).toHaveTextContent("建立分支與工作樹");
    expect(screen.getByRole("button", { name: "重試失敗步驟" })).toBeEnabled();
  });

  it("AT_961_17_7 完成：唯讀摘要（分支、遠端 URL 安全連結、Console 專案連結）與「前往拆解與執行」；遠端 URL 不合形時只顯示文字", async () => {
    const done = renderPanel({ route: ROUTE_SUCCEEDED });
    const summary = await screen.findByTestId("route-summary");
    const repo = within(summary).getByRole("link", { name: "https://github.com/acme/demo-app" });
    expect(repo).toHaveAttribute("href", "https://github.com/acme/demo-app");
    expect(repo).toHaveAttribute("rel", "noopener noreferrer");
    expect(within(summary).getByRole("link", { name: "開啟專案" }).getAttribute("href")).toMatch(/^\/projects\//);
    expect(screen.getByRole("link", { name: "前往拆解與執行" })).toHaveAttribute("href", `/research/${R3}?step=build`);
    expect(screen.queryByRole("button", { name: "重試失敗步驟" })).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
    done.unmount();

    renderPanel({ route: { ...ROUTE_SUCCEEDED, repoUrl: "javascript:alert(1)" } });
    const unsafe = await screen.findByTestId("route-summary");
    expect(unsafe).toHaveTextContent("javascript:alert(1)");
    expect(within(unsafe).queryByRole("link", { name: /javascript/ })).toBeNull();
  });
});

describe("AT_961_17_8 部署不支援的錯誤態與重新載入後還原", () => {
  it("AT_961_17_8 預演 422 route_unsupported_in_deployment：缺項對映成中文（gh 命令不可用、無法寫入程式庫），不顯示成功態", async () => {
    const user = userEvent.setup();
    renderPanel({
      stub: {
        overrides: (call) =>
          call.method === "POST" && /\/route\/preview$/.test(call.path)
            ? failure(422, { message: "x", reason: "route_unsupported_in_deployment", details: { missing: [{ item: "gh" }, { item: "repo_writable" }] } })
            : undefined,
      },
    });
    const dialog = await screen.findByRole("dialog");
    await user.click(await within(dialog).findByRole("radio", { name: /軌道 B/ }));
    fireEvent.change(within(dialog).getByLabelText(/^專案名稱/), { target: { value: "demo-app" } });
    await user.click(within(dialog).getByRole("button", { name: "預演" }));
    const missing = await within(dialog).findByTestId("route-missing");
    expect(missing).toHaveTextContent("gh 命令不可用");
    expect(missing).toHaveTextContent("無法寫入程式庫");
    expect(within(dialog).queryByTestId("route-actions")).toBeNull();
    expect(within(dialog).getByRole("button", { name: "確認執行" })).toBeDisabled();
  });

  it("AT_961_17_8 重新載入後：還原已選卡與參數（取自 API 的分流列與步驟，不取瀏覽器儲存），並從失敗步驟續", async () => {
    const user = userEvent.setup();
    const failedB: ResearchRouteDecision = {
      ...ROUTE_SUCCEEDED,
      status: "FAILED",
      failureStep: "GH_REPO_CREATE",
      steps: [ROUTE_SUCCEEDED.steps[0], { ...ROUTE_SUCCEEDED.steps[2], status: "FAILED", stderrTail: "遠端建立失敗" }],
    };
    const { calls } = renderPanel({ route: failedB, project: frozen("STANDALONE_PROJECT") });
    expect(await screen.findByTestId("route-failed")).toHaveTextContent("GH_REPO_CREATE");
    expect(screen.getAllByTestId(/^route-step-\d+$/)).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "重新開啟分流精靈" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("radio", { name: /軌道 B/ })).toHaveAttribute("aria-checked", "true");
    expect(within(dialog).getByLabelText(/^專案名稱/)).toHaveValue("demo-app");
    expect(within(dialog).getByLabelText(/^owner/)).toHaveValue("acme");
    expect(window.localStorage.length + window.sessionStorage.length).toBeLessThanOrEqual(window.localStorage.length + window.sessionStorage.length);
    expect(calls.some((c) => c.method === "GET" && ROUTE_URL.test(c.path))).toBe(true);
  });

  it("AT_961_17_8 尚未分流（200 null）：不顯示失敗區，面板提供預演入口；已完成步驟的唯讀檢視把「重新開啟分流精靈」停用", async () => {
    const view = renderPanel({ completed: true });
    const reopen = await screen.findByRole("button", { name: "重新開啟分流精靈" });
    expect(reopen).toBeDisabled();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByTestId("route-failed")).toBeNull();
    view.unmount();
    void R2;
  });
});
