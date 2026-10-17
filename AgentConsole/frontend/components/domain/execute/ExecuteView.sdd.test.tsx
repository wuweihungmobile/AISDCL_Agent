import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExecutionRunDetail, ExecutionRunSummary, ExecutionWarning, ProjectDetail } from "@/lib/api/types";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall, type Reply } from "@/tests/helpers/api";
import { checkpoints, dag, projectDetail, runDetail, runSummary, taskSummary } from "@/tests/helpers/runFixtures";
import { rtmReport } from "@/tests/helpers/sddFixtures";
import { FIXTURE } from "@/tests/helpers/settingsFixtures";
import { ExecuteView } from "./ExecuteView";

vi.mock("next/navigation", () => ({
  useParams: () => ({ projectId: "p1" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/projects/p1/execute",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

/**
 * 執行頁的 SDD 接線（整合輪 115；契約 §1.10.3、§1.10.6、§4.7.2）：
 *  ① execute 的 201 `warnings[]` 顯示在執行控制卡（toast 併進同一句）；② SDD 批次的預檢失敗白話化；③ 追溯覆蓋面板的出現條件。
 * ExecuteView 本身的行為（啟動、控制、審核…）見 ExecuteView.test.tsx。
 */
type World = {
  project: ProjectDetail;
  runs: ExecutionRunSummary[];
  details: Record<string, ExecutionRunDetail>;
  extra?: (call: ApiCall) => Reply;
};

const page = <T,>(content: T[]) => ({ content, page: 0, size: 20, totalElements: content.length, totalPages: 1 });

function backend(world: Partial<World> = {}) {
  const w: World = { project: projectDetail(), runs: [], details: {}, ...world };
  const { calls } = stubApi((c) => {
    const custom = w.extra?.(c);
    if (custom) return custom;
    if (c.method !== "GET") return undefined;
    if (c.path === "/api/v1/projects/p1") return { data: w.project };
    if (c.path === "/api/v1/projects/p1/executions") return { data: page(w.runs) };
    if (c.path === "/api/v1/settings/execution") return { data: [FIXTURE.globalTokenBudget("200000"), FIXTURE.tokenBudgetWarningThreshold("0.8")] };
    if (c.path === "/api/v1/goals/g1/tasks") return { data: [taskSummary("t1", "g1", "初始化")] };
    const m = /^\/api\/v1\/executions\/([^/]+)(?:\/(dag|checkpoints|rtm))?$/.exec(c.path);
    if (m) {
      if (m[2] === "dag") return { data: { ...dag(), runId: m[1] } };
      if (m[2] === "checkpoints") return { data: checkpoints() };
      if (m[2] === "rtm") return undefined; // 由各測試的 extra 決定
      return w.details[m[1]] ? { data: w.details[m[1]] } : undefined;
    }
    return undefined;
  });
  return { calls, world: w };
}

function view() {
  return render(
    <Providers client={makeClient()}>
      <ExecuteView />
    </Providers>,
  );
}

const created = (id: string, runNumber: number, warnings?: ExecutionWarning[]) => ({
  status: 201,
  data: {
    id,
    projectId: "p1",
    runNumber,
    status: "RUNNING",
    bridgeStatus: "RUNNING",
    autonomyLevel: 3,
    scope: { mode: "ALL" },
    totalTokensUsed: 0,
    tokenBudget: 200000,
    startedAt: "2026-10-15T08:30:12Z",
    ...(warnings ? { warnings } : {}),
  },
});

const rtmCalls = (calls: ApiCall[]) => calls.filter((c) => /\/executions\/[^/]+\/rtm$/.test(c.path));

beforeEach(() => signIn("OPERATOR", "operator"));

describe("執行頁：execute 201 的 warnings[]（契約 §1.10.6）", () => {
  const WARNINGS: ExecutionWarning[] = [
    { code: "sdd_governance_inactive", cause: "mixed_scope", detail: "範圍內有非 SDD 來源的任務，本批次不啟用 SDD 治理" },
    { code: "sdd_frozen_digest_absent", detail: "凍結時沒有記錄內容摘要" },
  ];

  it("啟動成功帶警告：toast 併進同一句；執行控制卡列出每則警告（白話標題、原因、後端說明）；批次照常啟動", async () => {
    const { world } = backend();
    world.extra = (c) => {
      if (c.method === "POST" && c.path === "/api/v1/projects/p1/execute") {
        world.runs = [runSummary()];
        world.details.r1 = runDetail();
        return created("r1", 1, WARNINGS);
      }
      return undefined;
    };
    view();
    await waitFor(() => expect(screen.getByTestId("exec-budget")).toHaveValue("200,000"));
    expect(screen.queryByTestId("execution-warnings")).toBeNull();
    await userEvent.click(screen.getByTestId("control-start"));
    expect(await screen.findByText("已啟動 Run #1（另有 2 則警告，見執行控制卡）")).toBeInTheDocument();
    const panel = await screen.findByTestId("execution-warnings");
    expect(within(screen.getByTestId("control-card")).getByTestId("execution-warnings")).toBe(panel);
    expect(panel).toHaveAttribute("role", "status");
    expect(panel).toHaveTextContent("啟動警告（共 2 項；批次已啟動，不阻擋）");
    const items = within(panel).getAllByTestId("execution-warning");
    expect(items.map((li) => li.getAttribute("data-code"))).toEqual(["sdd_governance_inactive", "sdd_frozen_digest_absent"]);
    expect(items[0]).toHaveTextContent("本批次沒有啟用 SDD 治理");
    expect(within(items[0]).getByTestId("execution-warning-cause")).toHaveTextContent("原因：範圍內有非 SDD 來源的任務");
    expect(within(items[0]).getByTestId("execution-warning-detail")).toHaveTextContent("範圍內有非 SDD 來源的任務，本批次不啟用 SDD 治理");
    expect(items[1]).toHaveTextContent("無法偵測凍結後改檔");
    expect(within(items[1]).queryByTestId("execution-warning-cause")).toBeNull(); // sdd_frozen_digest_absent 沒有 cause
    expect(await screen.findByTestId("run-number")).toHaveTextContent("Run #1");
  });

  it("沒有警告（201 沒有 warnings 欄位或空陣列）：維持 v1.4 的畫面與 toast，不顯示警告清單", async () => {
    for (const warnings of [undefined, []] as const) {
      const { world } = backend();
      world.extra = (c) => {
        if (c.method === "POST" && c.path === "/api/v1/projects/p1/execute") {
          world.runs = [runSummary()];
          world.details.r1 = runDetail();
          return created("r1", 1, warnings as ExecutionWarning[] | undefined);
        }
        return undefined;
      };
      const { unmount } = view();
      await waitFor(() => expect(screen.getByTestId("exec-budget")).toHaveValue("200,000"));
      await userEvent.click(screen.getByTestId("control-start"));
      expect(await screen.findByText("已啟動 Run #1")).toBeInTheDocument();
      expect(screen.queryByTestId("execution-warnings")).toBeNull();
      unmount();
    }
  });

  it("警告只屬於剛啟動的那個批次：切到別的批次就不顯示，切回來又在（只有 201 帶 warnings，之後取不到）", async () => {
    const { world } = backend({
      runs: [runSummary({ id: "r1", runNumber: 1, status: "COMPLETED", bridgeStatus: "COMPLETED" })],
      details: { r1: runDetail({ id: "r1", status: "COMPLETED", bridgeStatus: "COMPLETED" }) },
    });
    world.extra = (c) => {
      if (c.method === "POST" && c.path === "/api/v1/projects/p1/execute") {
        world.runs = [runSummary({ id: "r2", runNumber: 2 }), ...world.runs];
        world.details.r2 = runDetail({ id: "r2", runNumber: 2 });
        return created("r2", 2, WARNINGS);
      }
      return undefined;
    };
    view();
    await waitFor(() => expect(screen.getByTestId("exec-budget")).toHaveValue("200,000"));
    await userEvent.click(screen.getByTestId("control-start"));
    await screen.findByTestId("execution-warnings");
    await userEvent.selectOptions(screen.getByTestId("run-select"), "r1");
    await waitFor(() => expect(screen.queryByTestId("execution-warnings")).toBeNull());
    await userEvent.selectOptions(screen.getByTestId("run-select"), "r2");
    expect(await screen.findByTestId("execution-warnings")).toBeInTheDocument();
  });

  it("SDD 批次預檢失敗（409 sdd_fsm_state_conflict）：啟動失敗面板用白話列出目前狀態與處置，附代碼與 traceId", async () => {
    const { world } = backend();
    world.extra = (c) =>
      c.method === "POST" && c.path === "/api/v1/projects/p1/execute"
        ? failure(409, { message: "FSM 狀態不允許", reason: "sdd_fsm_state_conflict", details: { currentState: "ESCALATION", expectedState: "IMPLEMENTATION" } })
        : undefined;
    view();
    await waitFor(() => expect(screen.getByTestId("exec-budget")).toHaveValue("200,000"));
    await userEvent.click(screen.getByTestId("control-start"));
    const error = await screen.findByTestId("start-error");
    expect(error).toHaveTextContent("啟動失敗：FSM 狀態不允許啟動 SDD 批次");
    expect(error).toHaveTextContent("目前狀態：ESCALATION");
    expect(error).toHaveTextContent("請先在 SDD session 依恢復指令處理");
    expect(error).toHaveTextContent("代碼：sdd_fsm_state_conflict");
    expect(error).toHaveTextContent("traceId：tr-409");
    expect(screen.queryByTestId("execution-warnings")).toBeNull();
  });
});

describe("執行頁：追溯覆蓋面板的出現條件（契約 §4.7.2）", () => {
  const BOUND = () => projectDetail({ sddProject: "core-fsm", sddSpecDir: "/work/core/docs", sddSpecFile: "/work/core/docs/TCS-A.md" });
  const doneRun = () => ({
    runs: [runSummary({ status: "COMPLETED", bridgeStatus: "COMPLETED" })],
    details: { r1: runDetail({ status: "COMPLETED", bridgeStatus: "COMPLETED", completedAt: "2026-10-15T08:40:00Z" }) },
  });

  it("專案有 SDD 規格綁定且批次已終態：面板顯示報告並只取一次；放在審核項目卡之後", async () => {
    const { world, calls } = backend({ project: BOUND(), ...doneRun() });
    world.extra = (c) => (c.method === "GET" && c.path === "/api/v1/executions/r1/rtm" ? { data: rtmReport() } : undefined);
    view();
    expect(await screen.findByTestId("rtm-at")).toHaveTextContent("4／4（100.0%）");
    expect(screen.getByTestId("rtm-advisory-badge")).toHaveTextContent("諮詢視圖");
    const panel = screen.getByTestId("rtm-panel");
    expect(screen.getByTestId("review-card").compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(rtmCalls(calls)).toHaveLength(1);
  });

  it("專案沒有規格綁定（sddSpecDir 為空）：整個面板不顯示、不呼叫 rtm 端點", async () => {
    const { calls } = backend({ project: projectDetail({ sddProject: "core-fsm", sddSpecDir: null }), ...doneRun() });
    view();
    await screen.findByTestId("run-number");
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(screen.queryByTestId("rtm-panel")).toBeNull();
    expect(rtmCalls(calls)).toHaveLength(0);
  });

  it("批次還在跑：只顯示一行「批次結束後才會有追溯覆蓋報告」，不呼叫端點", async () => {
    const { calls } = backend({ project: BOUND(), runs: [runSummary()], details: { r1: runDetail() } });
    view();
    expect(await screen.findByTestId("rtm-pending")).toHaveTextContent("批次結束後才會有追溯覆蓋報告");
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(rtmCalls(calls)).toHaveLength(0);
  });

  it("終態批次沒有報告（404 rtm_not_found）：中性文字，不是錯誤樣式", async () => {
    const { world } = backend({ project: BOUND(), ...doneRun() });
    world.extra = (c) => (c.method === "GET" && c.path === "/api/v1/executions/r1/rtm" ? failure(404, { message: "沒有報告", reason: "rtm_not_found", details: { runId: "r1" } }) : undefined);
    view();
    expect(await screen.findByTestId("rtm-empty")).toHaveTextContent("此批次沒有追溯覆蓋報告");
    expect(within(screen.getByTestId("rtm-panel")).queryByRole("alert")).toBeNull();
  });
});
