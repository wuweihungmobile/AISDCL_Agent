import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExecuteEntryPage, { metadata as executeMetadata } from "@/app/execute/page";
import MonitorEntryPage, { metadata as monitorMetadata } from "@/app/monitor/page";
import { qk } from "@/lib/api/queries";
import { projectStatus } from "@/lib/domain/status";
import { getLastProjectId } from "@/lib/nav/lastProject";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall } from "@/tests/helpers/api";
import { CenterEntryView } from "./CenterEntryView";

/**
 * 執行中心／監控中心的無專案入口頁（TCS-ExecMonitorEntry-20261101 F-905、AC-953-2；W-E1；Console PRD §0.8）：
 * AT_953_2_1（空列表：標題、說明、空狀態與兩個去處）、AT_953_2_2（有專案：「選擇專案」清單；不跳轉、不寫入、不記住專案）、
 * AT_953_2_3（載入中、錯誤重試、已有清單後背景重抓失敗清單照常）、AT_953_2_E_1（VIEWER：新建專案停用、匯入仍在）、
 * AT_953_2_4（頁殼：app/execute 與 app/monitor 各組出正確 kind 的入口頁，metadata.title 各對各）。
 * 兩個 kind（execute／monitor）共用一個元件（⚖3），所以凡是依 kind 變化的斷言（標題、說明、連結目的路徑）都兩個 kind 各跑一次——只測一個 kind 抓不到「寫死 execute」這類錯。
 * SCG-4 一審（2026-11-02）三個存活突變的補強（TCS 勘誤 3、4）：頁殼 kind（F-01 → AT_953_2_4）、有舊資料時重抓失敗換錯誤卡（F-02 → AT_953_2_3 第三個 it）、進入頁記住專案（F-03 → AT_953_2_2 的 getLastProjectId 斷言）。
 * 判定指令：npx vitest run components/domain/entry/CenterEntryView.test.tsx -t "<AT 底線形>"
 */
const nav = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: nav.push, replace: nav.replace, back: vi.fn() }),
  usePathname: () => "/execute",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

type Kind = "execute" | "monitor";

/** 兩個變體：標題、目的頁字樣（副標）與標題圖示（lucide-react 在 svg 上標 `lucide-<名稱>`）。 */
const KINDS: ReadonlyArray<{ kind: Kind; title: string; target: string; icon: string }> = [
  { kind: "execute", title: "執行中心", target: "選擇專案進入它的執行頁", icon: "lucide-play" },
  { kind: "monitor", title: "監控中心", target: "選擇專案進入它的監控頁", icon: "lucide-activity" },
];

const TS = "2026-11-01T08:30:12Z";
const summary = (id: string, name: string, status: string) => ({
  id,
  name,
  executionPath: `/work/${name}`,
  status,
  autonomyLevel: 3,
  signedOff: true,
  goalsCount: 2,
  tasksCount: 3,
  tasksDone: 1,
  updatedAt: TS,
});
const page = (content: object[]) => ({ content, page: 0, size: 100, totalElements: content.length, totalPages: 1 });

const listCalls = (calls: ApiCall[]) => calls.filter((c) => c.method === "GET" && c.path === "/api/v1/projects");

function backend(content: object[]) {
  return stubApi((c) => (c.method === "GET" && c.path === "/api/v1/projects" ? { data: page(content) } : undefined));
}

function view(kind: Kind) {
  return render(
    <Providers client={makeClient()}>
      <CenterEntryView kind={kind} />
    </Providers>,
  );
}

const emptyStateOf = (container: HTMLElement) => container.querySelector<HTMLElement>('[data-slot="empty-state"]');

beforeEach(() => {
  nav.push.mockClear();
  nav.replace.mockClear();
  signIn("OPERATOR", "operator");
});

describe("AT_953_2 入口頁三態與動作（W-E1）", () => {
  it.each(KINDS)("AT_953_2_1 $kind：OPERATOR、專案列表為空 → 標題與圖示、說明、空狀態，以及兩個去處（新建專案、BRD/PRD 匯入）；沒有清單", async ({ kind, title, target, icon }) => {
    backend([]);
    const { container } = view(kind);
    const empty = await waitFor(() => {
      const found = emptyStateOf(container);
      expect(found, "空狀態出現").not.toBeNull();
      return found as HTMLElement;
    });

    const root = screen.getByTestId("center-entry-view");
    expect(root).toHaveAttribute("data-kind", kind);
    const heading = screen.getByRole("heading", { name: title });
    expect(heading.querySelector("svg")?.getAttribute("class") ?? "", "標題前的圖示依 kind 而異").toContain(icon);
    expect(root, "副標寫明目的頁").toHaveTextContent(`以專案為單位 · ${target}`);
    expect(screen.getByTestId("entry-intro")).toHaveTextContent(`${title}以專案為單位`);

    expect(within(empty).getByText("還沒有任何專案")).toBeInTheDocument();
    expect(empty).toHaveTextContent(`${title}需要一個專案。先按「新建專案」，或從「BRD/PRD 匯入」讓 AI 拆解，建立後再回到這裡選擇它進入。`);

    // 兩個去處：OPERATOR 的「新建專案」是連到 /projects/new 的連結（也是下面 VIEWER 對照的基準）
    expect(screen.getByRole("link", { name: "新建專案" })).toHaveAttribute("href", "/projects/new");
    expect(screen.getByRole("link", { name: "BRD/PRD 匯入" })).toHaveAttribute("href", "/import");
    expect(screen.queryByRole("list"), "沒有專案時不渲染清單").toBeNull();
    expect(screen.queryByTestId("entry-project-list")).toBeNull();
  });

  it.each(KINDS)(
    "AT_953_2_2 $kind：OPERATOR、兩個專案（Alpha 就緒、Beta 執行中）→「選擇專案」清單恰兩個連結，依序 Alpha、Beta，各連到 /projects/<id>/$kind，每列有狀態標籤；沒有空狀態；不跳轉、不寫入",
    async ({ kind }) => {
      const { calls } = backend([summary("pa", "Alpha", "READY"), summary("pb", "Beta", "EXECUTING")]);
      const { container } = view(kind);
      const list = await screen.findByRole("list", { name: "選擇專案" });
      expect(list).toHaveAttribute("data-testid", "entry-project-list");

      const links = within(list).getAllByRole("link");
      expect(links).toHaveLength(2);
      expect(links[0]).toHaveAccessibleName("Alpha");
      expect(links[1]).toHaveAccessibleName("Beta");
      expect(links.map((a) => a.getAttribute("href"))).toEqual([`/projects/pa/${kind}`, `/projects/pb/${kind}`]);

      // 每列的狀態標籤各自是自己的狀態（不是全部同一個）
      const items = within(list).getAllByRole("listitem");
      expect(items).toHaveLength(2);
      expect(within(items[0]).getByText(projectStatus("READY").label)).toBeInTheDocument();
      expect(within(items[0]).queryByText(projectStatus("EXECUTING").label)).toBeNull();
      expect(within(items[1]).getByText(projectStatus("EXECUTING").label)).toBeInTheDocument();

      expect(emptyStateOf(container), "有專案時不渲染空狀態").toBeNull();
      expect(screen.queryByText("還沒有任何專案")).toBeNull();

      // ⚖7：沿用 useAllProjects 的取數（最多 100 筆、更新時間新到舊），不另加端點；W-E1 (d)／⚖2：不自動跳轉、不呼叫任何 mutation
      const request = listCalls(calls)[0];
      expect(request.query.get("size")).toBe("100");
      expect(request.query.get("sort")).toBe("updatedAt,desc");
      expect(calls.every((c) => c.method === "GET")).toBe(true);
      expect(nav.push).not.toHaveBeenCalled();
      expect(nav.replace).not.toHaveBeenCalled();
      // W-E1 (d)／W-E5：入口頁不記住專案（「最近造訪」只由專案頁的 useCurrentProjectId 寫入）；SCG-4 一審 F-03（突變「進入頁 rememberProjectId」須轉紅）
      expect(getLastProjectId(), "最近造訪記錄未被寫入").toBeNull();
      expect(window.sessionStorage.getItem("aisdlc.console.lastProject")).toBeNull();
    },
  );

  it("AT_953_2_3 API 永不回應 → 骨架（標題與動作仍在）、沒有清單、沒有空狀態、沒有錯誤卡", async () => {
    const requested: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        requested.push(String(input));
        return new Promise<Response>(() => undefined);
      }),
    );
    const { container } = view("execute");
    await waitFor(() => expect(requested, "列表請求已送出、卻永不回應").toHaveLength(1));

    expect(screen.getByLabelText("頁面載入中"), "PageSkeleton").toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("heading", { name: "執行中心" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "BRD/PRD 匯入" })).toBeInTheDocument();
    expect(screen.queryByTestId("entry-project-list")).toBeNull();
    expect(emptyStateOf(container)).toBeNull();
    expect(screen.queryByText("還沒有任何專案")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("AT_953_2_3 API 回 500 → 錯誤卡「無法載入專案列表」（沒有清單與空狀態）；按「重試」後再呼叫一次列表 API（請求計數 1→2）", async () => {
    const { calls } = stubApi((c) => (c.method === "GET" && c.path === "/api/v1/projects" ? failure(500, { message: "伺服器錯誤" }) : undefined));
    const { container } = view("monitor");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("無法載入專案列表");
    expect(listCalls(calls), "第一次請求").toHaveLength(1);
    expect(screen.queryByTestId("entry-project-list")).toBeNull();
    expect(emptyStateOf(container)).toBeNull();
    expect(screen.queryByLabelText("頁面載入中")).toBeNull();

    await userEvent.click(within(alert).getByRole("button", { name: "重試" }));
    await waitFor(() => expect(listCalls(calls), "按重試後再打一次").toHaveLength(2));
  });

  it("AT_953_2_3 已有清單後背景重抓失敗 → 清單照常、沒有錯誤卡（只有「根本沒有資料」才換成錯誤畫面；W-E1 (c)）", async () => {
    // SCG-4 一審 F-02：突變「projects === undefined || all.isError 就換錯誤卡」須轉紅
    let served = 0;
    const { calls } = stubApi((c) => {
      if (c.method !== "GET" || c.path !== "/api/v1/projects") return undefined;
      served += 1;
      return served === 1 ? { data: page([summary("pa", "Alpha", "READY")]) } : failure(500, { message: "伺服器錯誤" });
    });
    const client = makeClient();
    render(
      <Providers client={client}>
        <CenterEntryView kind="execute" />
      </Providers>,
    );
    expect(within(await screen.findByRole("list", { name: "選擇專案" })).getAllByRole("link")).toHaveLength(1);

    await client.refetchQueries({ queryKey: qk.allProjects });
    await waitFor(() => expect(listCalls(calls), "背景重抓已發出且失敗").toHaveLength(2));
    const list = screen.getByRole("list", { name: "選擇專案" });
    expect(within(list).getAllByRole("link"), "清單仍是上一份資料").toHaveLength(1);
    expect(screen.queryByRole("alert"), "不換成錯誤卡").toBeNull();
    expect(screen.queryByText("無法載入專案列表")).toBeNull();
  });

  it.each(KINDS)("AT_953_2_E_1 $kind：VIEWER、專案列表為空 →「新建專案」是停用按鈕（title 權限不足）、頁內沒有連到 /projects/new 的連結；「BRD/PRD 匯入」連結仍在；空狀態照常", async ({ kind }) => {
    signIn("VIEWER", "viewer");
    backend([]);
    const { container } = view(kind);
    expect(await screen.findByText("還沒有任何專案")).toBeInTheDocument();

    const create = screen.getByRole("button", { name: "新建專案" });
    expect(create).toBeDisabled();
    expect(create).toHaveAttribute("title", "權限不足（唯讀角色）");
    expect(screen.queryByRole("link", { name: "新建專案" }), "唯讀角色沒有「新建專案」連結").toBeNull();
    expect(container.querySelector('a[href="/projects/new"]'), "頁內任何位置都沒有連到 /projects/new 的連結").toBeNull();

    // 「BRD/PRD 匯入」三種角色皆顯示（⚖5：匯入頁自管權限）
    expect(screen.getByRole("link", { name: "BRD/PRD 匯入" })).toHaveAttribute("href", "/import");
    expect(screen.getByTestId("center-entry-view")).toHaveAttribute("data-kind", kind);
  });
});

describe("AT_953_2_4 頁殼（W-E1 (e)）：app/execute 與 app/monitor 只殼組 CenterEntryView，kind 與 metadata.title 各對各", () => {
  // SCG-4 一審 F-01：突變「execute 頁殼改 kind=monitor」在 vitest 層須轉紅（原本只有 E2E AT-953-4-2 承擔）；F-06：metadata.title 也釘住
  it.each([
    { Page: ExecuteEntryPage, meta: executeMetadata, kind: "execute", title: "執行中心" },
    { Page: MonitorEntryPage, meta: monitorMetadata, kind: "monitor", title: "監控中心" },
  ])("AT_953_2_4 $kind：頁殼渲染出 data-kind=$kind 的入口頁、標題「$title」，metadata.title 為「$title」", async ({ Page, meta, kind, title }) => {
    backend([]);
    render(
      <Providers client={makeClient()}>
        <Page />
      </Providers>,
    );
    expect(await screen.findByTestId("center-entry-view")).toHaveAttribute("data-kind", kind);
    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(meta.title).toBe(title);
  });
});
