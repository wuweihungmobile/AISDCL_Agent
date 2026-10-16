import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EngineCapabilities, EngineCapabilityState, ExecutionRunDetail, ExecutionRunSummary, ProjectDetail } from "@/lib/api/types";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall, type Reply } from "@/tests/helpers/api";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { checkpoints, dag, projectDetail, reviewItem, runDetail, runSummary, taskSummary } from "@/tests/helpers/runFixtures";
import { FIXTURE } from "@/tests/helpers/settingsFixtures";
import { ExecuteView, parseTokenInput } from "./ExecuteView";

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

type World = {
  project: ProjectDetail;
  runs: ExecutionRunSummary[];
  details: Record<string, ExecutionRunDetail>;
  extra?: (call: ApiCall) => Reply;
};

const page = <T,>(content: T[]) => ({ content, page: 0, size: 20, totalElements: content.length, totalPages: 1 });

/** 假後端：讀取端點照 world 回；寫入端點交給 extra（沒處理就 404，測試會看到清楚訊息）。 */
function backend(world: Partial<World> = {}) {
  const w: World = { project: projectDetail(), runs: [], details: {}, ...world };
  const { calls } = stubApi((c) => {
    const custom = w.extra?.(c);
    if (custom) return custom;
    if (c.method !== "GET") return undefined;
    if (c.path === "/api/v1/projects/p1") return { data: w.project };
    if (c.path === "/api/v1/projects/p1/executions") return { data: page(w.runs) };
    if (c.path === "/api/v1/settings/execution") return { data: [FIXTURE.globalTokenBudget("200000"), FIXTURE.tokenBudgetWarningThreshold("0.8")] };
    if (c.path === "/api/v1/goals/g1/tasks") {
      return { data: [taskSummary("t1", "g1", "初始化"), taskSummary("t2", "g1", "設定", { signedOff: false })] };
    }
    const m = /^\/api\/v1\/executions\/([^/]+)(?:\/(dag|checkpoints))?$/.exec(c.path);
    if (m) {
      if (m[2] === "dag") return { data: { ...dag(), runId: m[1] } };
      if (m[2] === "checkpoints") return { data: checkpoints() };
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

const post = (calls: ApiCall[], suffix: string) => calls.find((c) => c.method === "POST" && c.path.endsWith(suffix));

beforeEach(() => {
  FakeEventSource.reset();
  signIn("OPERATOR", "operator");
});

describe("parseTokenInput：Token 數輸入", () => {
  it("空字串＝未填；千分位逗號與空白略過；非正整數、含字母、前導 0 一律 NaN", () => {
    expect(parseTokenInput("")).toBeUndefined();
    expect(parseTokenInput("  ")).toBeUndefined();
    expect(parseTokenInput("100,000")).toBe(100000);
    expect(parseTokenInput(" 1 500 ")).toBe(1500);
    for (const bad of ["0", "-5", "12.5", "abc", "007", "1e5"]) expect(parseTokenInput(bad), bad).toBeNaN();
  });
});

describe("執行頁：版面與鎖定（設計稿畫面 7）", () => {
  it("標題「專案執行：{名稱}」、返回連結、六張卡都在；沒有批次時進度卡提示尚未啟動", async () => {
    backend();
    view();
    expect(await screen.findByRole("heading", { name: "專案執行：AISDLC Core Platform" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回專案" })).toHaveAttribute("href", "/projects/p1");
    for (const id of ["control-card", "progress-card", "dag-card", "log-card", "review-card"]) expect(screen.getByTestId(id)).toBeInTheDocument();
    expect(screen.getByText("尚未啟動執行。設定左側的範圍與預算後按「啟動執行」。")).toBeInTheDocument();
    expect(screen.queryByTestId("execute-lock-banner")).toBeNull();
    expect(screen.queryByTestId("run-select")).toBeNull();
  });

  it("專案 signedOff=false：顯示鎖定橫幅（啟動回 409 Conflict）、「啟動執行」停用；「前往審批」開 signoff 對話框", async () => {
    backend({ project: projectDetail({ signedOff: false }) });
    view();
    const banner = await screen.findByTestId("execute-lock-banner");
    expect(banner).toHaveTextContent("執行已鎖定 — 草案未 signoff，啟動回 409 Conflict");
    expect(screen.getByTestId("control-start")).toBeDisabled();
    await userEvent.click(within(banner).getByRole("button", { name: "前往審批" }));
    expect(await screen.findByText("審批 signoff：專案")).toBeInTheDocument();
  });

  it("自治等級預設取專案的等級、預算預設取系統參數 execution.globalTokenBudget；Level 6～10 說明審核閘同 Level 5、另要求自動突變／自演化（契約 §3.6.1，v1.3）", async () => {
    backend({ project: projectDetail({ autonomyLevel: 4 }) });
    view();
    const level = (await screen.findByTestId("exec-level")) as HTMLSelectElement;
    expect(level.value).toBe("4");
    expect(level.options).toHaveLength(10);
    expect(level.options[2].text).toBe("Level 3 · Review & Approve");
    await waitFor(() => expect(screen.getByTestId("exec-budget")).toHaveValue("200,000"));
    expect(screen.getByTestId("autonomy-hint")).toHaveTextContent("全自動執行，僅重試失敗後升級給人類");
    await userEvent.selectOptions(level, "7");
    const hint = screen.getByTestId("autonomy-hint");
    expect(hint).toHaveTextContent("審核閘行為同 Level 5");
    expect(hint).toHaveTextContent("Level 6 以上另要求自動突變、Level 7 以上另要求自演化");
    expect(hint).toHaveTextContent("引擎能力晶片"); // 結果看批次上的晶片，不在這裡猜
    expect(hint).not.toHaveTextContent("不另傳給引擎"); // v1.2 的說法已被 v1.3 推翻（等級 ≥ 6 現在會送 enable_kernel_brain）
  });
});

describe("執行頁：啟動執行（US-E-01、E-02、E-10）", () => {
  it("預設全部目標選中 → mode ALL；body 帶等級、預算（預設值）；成功後切到新批次並顯示 Run #1", async () => {
    const { calls, world } = backend();
    world.extra = (c) => {
      if (c.method === "POST" && c.path === "/api/v1/projects/p1/execute") {
        world.runs = [runSummary()];
        world.details.r1 = runDetail();
        return {
          status: 201,
          data: {
            id: "r1",
            projectId: "p1",
            runNumber: 1,
            status: "RUNNING",
            bridgeStatus: "RUNNING",
            autonomyLevel: 3,
            scope: { mode: "ALL" },
            totalTokensUsed: 0,
            tokenBudget: 200000,
            startedAt: "2026-10-15T08:30:12Z",
          },
        };
      }
      return undefined;
    };
    view();
    await waitFor(() => expect(screen.getByTestId("exec-budget")).toHaveValue("200,000"));
    expect(screen.getByTestId("scope-all")).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByTestId("control-start"));
    await waitFor(() => expect(post(calls, "/execute")).toBeDefined());
    expect(post(calls, "/execute")?.body).toEqual({ autonomyLevel: 3, tokenBudget: 200000, scope: { mode: "ALL" } });
    expect(await screen.findByText("已啟動 Run #1")).toBeInTheDocument();
    expect(await screen.findByTestId("run-number")).toHaveTextContent("Run #1");
    expect(calls.some((c) => c.method === "GET" && c.path === "/api/v1/executions/r1")).toBe(true);
  });

  it("取消一個目標：改送 SELECTED（goalIds 只列還選著的）；單一任務／目標 Token 上限帶進 scope.limits", async () => {
    const { calls, world } = backend();
    world.extra = (c) => (c.method === "POST" && c.path === "/api/v1/projects/p1/execute" ? failure(409, { reason: "專案正在執行中", details: { projectId: "p1", runId: "r9" } }) : undefined);
    view();
    await screen.findByTestId("scope-goal-g2");
    await userEvent.click(screen.getByTestId("scope-goal-g2"));
    expect(screen.getByTestId("scope-all")).toHaveAttribute("aria-checked", "mixed");
    await userEvent.click(screen.getByText("進階：單一任務／單一目標 Token 上限（選填）"));
    await userEvent.type(screen.getByTestId("exec-task-limit"), "5,000");
    await userEvent.type(screen.getByTestId("exec-goal-limit"), "20000");
    await userEvent.clear(screen.getByTestId("exec-budget"));
    await userEvent.click(screen.getByTestId("control-start"));
    await waitFor(() => expect(post(calls, "/execute")).toBeDefined());
    expect(post(calls, "/execute")?.body).toEqual({ autonomyLevel: 3, scope: { mode: "SELECTED", goalIds: ["g1"], taskIds: [], limits: { taskTokens: 5000, goalTokens: 20000 } } });
    // 預算清空＝不帶 tokenBudget（沿用後端預設）
    expect(await screen.findByTestId("start-error")).toHaveTextContent("專案正在執行中");
  });

  it("展開目標看任務：取消其中一個任務 → 送 SELECTED 的 taskIds；已展開才會載入該目標的任務", async () => {
    const { calls, world } = backend();
    world.extra = (c) => (c.method === "POST" && c.path === "/api/v1/projects/p1/execute" ? failure(409, { reason: "專案正在執行中" }) : undefined);
    view();
    await screen.findByTestId("scope-expand-g1");
    expect(calls.some((c) => c.path === "/api/v1/goals/g1/tasks")).toBe(false);
    await userEvent.click(screen.getByTestId("scope-expand-g1"));
    await screen.findByTestId("scope-task-t1");
    expect(within(screen.getByTestId("scope-tasks-g1")).getAllByText("未審批")).toHaveLength(1); // 任務 t2 未 signoff
    await userEvent.click(screen.getByTestId("scope-task-t1"));
    expect(screen.getByTestId("scope-goal-g1")).toHaveAttribute("aria-checked", "mixed");
    // 未簽核的任務 t2 仍被選中 → 範圍內有未 signoff：啟動鈕停用並列出名稱
    expect(screen.getByTestId("scope-unsigned")).toHaveTextContent("任務「設定」");
    expect(screen.getByTestId("control-start")).toBeDisabled();
    await userEvent.click(screen.getByTestId("scope-task-t2")); // 取消 t2，只剩 g2 整個目標
    expect(screen.getByTestId("control-start")).toBeEnabled();
    await userEvent.click(screen.getByTestId("control-start"));
    await waitFor(() => expect(post(calls, "/execute")).toBeDefined());
    expect(post(calls, "/execute")?.body).toMatchObject({ scope: { mode: "SELECTED", goalIds: ["g2"], taskIds: [] } });
  });

  it("全部取消：請至少選一個（不送請求）；預算填壞值：欄位下方紅字、不送請求", async () => {
    const { calls } = backend();
    view();
    await userEvent.click(await screen.findByTestId("scope-all"));
    await userEvent.click(screen.getByTestId("control-start"));
    expect(await screen.findByText("請至少選擇一個目標或任務")).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("scope-all"));
    await userEvent.clear(screen.getByTestId("exec-budget"));
    await userEvent.type(screen.getByTestId("exec-budget"), "12.5");
    await userEvent.click(screen.getByTestId("control-start"));
    expect(await screen.findByText("Token 數須為大於 0 的整數（預算與上限皆同）")).toBeInTheDocument();
    expect(post(calls, "/execute")).toBeUndefined();
  });

  it("後端 409「未經人工審批的草案不可執行」：用專案已載入的名稱列出未審批的目標，並提供「前往審批」", async () => {
    const { world } = backend();
    world.extra = (c) =>
      c.method === "POST" && c.path === "/api/v1/projects/p1/execute"
        ? failure(409, { message: "草案未經人工審批，禁止執行", reason: "未經人工審批的草案不可執行", details: { unsignedGoalIds: ["g2"], unsignedTaskIds: ["t-unknown-0001"] } })
        : undefined;
    view();
    await userEvent.click(await screen.findByTestId("control-start"));
    const panel = await screen.findByTestId("start-error");
    expect(panel).toHaveTextContent("啟動失敗：未經人工審批的草案不可執行");
    expect(panel).toHaveTextContent("未審批的目標：核心");
    expect(panel).toHaveTextContent("t-unknow"); // 查不到名稱的 id 退成前 8 碼
    expect(within(panel).getByRole("button", { name: "前往審批" })).toBeInTheDocument();
    expect(panel).toHaveTextContent("traceId：tr-409");
  });
});

describe("執行頁：按鈕狀態機與控制動作（US-E-04、05、06、11）", () => {
  const withRun = (patch: Partial<ExecutionRunDetail> = {}, summary: Partial<ExecutionRunSummary> = {}) => ({
    runs: [runSummary({ status: patch.status ?? "RUNNING", ...summary })],
    details: { r1: runDetail(patch) },
  });

  it("RUNNING：顯示「暫停」「取消」；沒有「啟動執行」；範圍與等級停用（給下一批次用）", async () => {
    backend(withRun());
    view();
    await screen.findByTestId("run-status"); // 詳情載入後才有進度卡
    expect(await screen.findByTestId("control-pause")).toBeEnabled();
    expect(screen.getByTestId("control-cancel")).toBeEnabled();
    expect(screen.queryByTestId("control-start")).toBeNull();
    expect(screen.queryByTestId("control-resume")).toBeNull();
    expect(screen.getByTestId("exec-level")).toBeDisabled();
    expect(screen.getByTestId("scope-all")).toBeDisabled();
    expect(screen.getByTestId("run-status")).toHaveTextContent("執行中");
  });

  it("RUNNING＋Bridge PAUSING：「暫停中…」停用、狀態顯示「暫停中」", async () => {
    backend(withRun({ bridgeStatus: "PAUSING" }));
    view();
    await screen.findByTestId("run-status"); // bridgeStatus 只在批次詳情裡
    const pause = await screen.findByTestId("control-pause");
    expect(pause).toBeDisabled();
    expect(pause).toHaveTextContent("暫停中…");
    expect(screen.getByTestId("run-status")).toHaveTextContent("暫停中");
  });

  it("PAUSED：「恢復」「取消」「從斷點恢復」；終態：「啟動執行」與「從斷點恢復」", async () => {
    backend(withRun({ status: "PAUSED", bridgeStatus: "PAUSED" }));
    const first = view();
    expect(await screen.findByTestId("control-resume")).toBeEnabled();
    expect(screen.getByTestId("control-cancel")).toBeEnabled();
    expect(screen.getByTestId("control-restore")).toBeEnabled();
    first.unmount();

    backend(withRun({ status: "COMPLETED", bridgeStatus: "COMPLETED", completedAt: "2026-10-15T08:40:00Z" }));
    view();
    expect(await screen.findByTestId("control-start")).toBeEnabled();
    expect(screen.getByTestId("control-restore")).toBeEnabled();
    expect(screen.queryByTestId("control-pause")).toBeNull();
    expect(screen.getByTestId("exec-level")).toBeEnabled();
  });

  it("按「暫停」：POST pause，toast 說明下一個步驟邊界生效；回應快照立刻寫回（按鈕變「暫停中…」）", async () => {
    const { calls, world } = backend(withRun());
    world.extra = (c) =>
      c.method === "POST" && c.path === "/api/v1/executions/r1/pause"
        ? {
            data: {
              id: "r1",
              projectId: "p1",
              runNumber: 1,
              status: "RUNNING",
              bridgeStatus: "PAUSING",
              autonomyLevel: 4,
              scope: { mode: "ALL" },
              totalTokensUsed: 1240,
              startedAt: "2026-10-15T08:30:12Z",
            },
          }
        : undefined;
    view();
    await userEvent.click(await screen.findByTestId("control-pause"));
    await waitFor(() => expect(post(calls, "/r1/pause")).toBeDefined());
    expect(await screen.findByText("已要求暫停，會在下一個步驟邊界生效")).toBeInTheDocument();
  });

  it("按「恢復」：POST resume；後端 409 時 toast 顯示 reason 與 traceId，不吞錯", async () => {
    const { calls, world } = backend(withRun({ status: "PAUSED", bridgeStatus: "PAUSED" }));
    world.extra = (c) => (c.method === "POST" && c.path === "/api/v1/executions/r1/resume" ? failure(409, { message: "草案未經人工審批，禁止執行", reason: "未經人工審批的草案不可執行" }) : undefined);
    view();
    await userEvent.click(await screen.findByTestId("control-resume"));
    await waitFor(() => expect(post(calls, "/r1/resume")).toBeDefined());
    expect(await screen.findByText(/草案未經人工審批，禁止執行：未經人工審批的草案不可執行（traceId：tr-409）/)).toBeInTheDocument();
  });

  it("按「取消」：先確認（會終止進行中的任務），確認後 POST cancel", async () => {
    const { calls, world } = backend(withRun());
    world.extra = (c) =>
      c.method === "POST" && c.path === "/api/v1/executions/r1/cancel"
        ? {
            data: {
              id: "r1",
              projectId: "p1",
              runNumber: 1,
              status: "RUNNING",
              bridgeStatus: "CANCELLING",
              autonomyLevel: 4,
              scope: { mode: "ALL" },
              totalTokensUsed: 1240,
              startedAt: "2026-10-15T08:30:12Z",
            },
          }
        : undefined;
    view();
    await userEvent.click(await screen.findByTestId("control-cancel"));
    expect(await screen.findByText(/確定取消這個執行批次？/)).toBeInTheDocument();
    expect(post(calls, "/cancel")).toBeUndefined();
    await userEvent.click(screen.getByRole("button", { name: "確認取消" }));
    await waitFor(() => expect(post(calls, "/r1/cancel")).toBeDefined());
  });

  it("「從斷點恢復」：開對話框列斷點（新→舊）、選一筆、POST restore/{checkpointId}", async () => {
    const { calls, world } = backend(withRun({ status: "PAUSED", bridgeStatus: "PAUSED" }));
    world.extra = (c) =>
      c.method === "POST" && c.path === "/api/v1/executions/r1/restore/c2"
        ? {
            data: {
              id: "r1",
              projectId: "p1",
              runNumber: 1,
              status: "RUNNING",
              bridgeStatus: "RUNNING",
              autonomyLevel: 4,
              scope: { mode: "ALL" },
              totalTokensUsed: 1240,
              startedAt: "2026-10-15T08:30:12Z",
            },
          }
        : undefined;
    view();
    await userEvent.click(await screen.findByTestId("control-restore"));
    const dialog = await screen.findByTestId("checkpoint-dialog");
    const options = await within(dialog).findAllByTestId("checkpoint-option");
    expect(options.map((o) => o.textContent)).toEqual([expect.stringContaining("after-G1-T2"), expect.stringContaining("after-G1-T1")]);
    expect(options[0]).toHaveTextContent("還原後從 G2-T1 繼續");
    expect(within(dialog).getByTestId("checkpoint-confirm")).toBeDisabled();
    await userEvent.click(within(options[0]).getByRole("radio"));
    await userEvent.click(within(dialog).getByTestId("checkpoint-confirm"));
    await waitFor(() => expect(post(calls, "/restore/c2")).toBeDefined());
    expect(await screen.findByText("已從斷點「after-G1-T2」恢復")).toBeInTheDocument();
  });

  it("唯讀角色（VIEWER）：每個控制鈕與審核鈕都停用並標示權限不足", async () => {
    signIn("VIEWER", "viewer");
    backend(withRun({ pendingReviews: [reviewItem()] }));
    view();
    await screen.findByTestId("review-row"); // 審核項在批次詳情裡
    const pause = await screen.findByTestId("control-pause");
    expect(pause).toBeDisabled();
    expect(pause).toHaveAttribute("title", "權限不足（唯讀角色）");
    expect(screen.getByTestId("control-cancel")).toBeDisabled();
    expect(screen.getByTestId("review-approve")).toBeDisabled();
  });
});

describe("執行頁：執行進度卡（US-E-09 的進度、E-10 的 Token）", () => {
  it("任務進度 completedSteps／totalSteps、Token 進度與百分比、耗時 HH:MM:SS、目前步驟", async () => {
    backend({
      runs: [runSummary()],
      details: {
        r1: runDetail({
          completedSteps: 13,
          totalSteps: 23,
          totalTokensUsed: 45230,
          tokenBudget: 100000,
          elapsedSec: 5025,
          status: "COMPLETED",
          bridgeStatus: "COMPLETED",
          currentStep: { stepId: "G2-T1", stepNumber: 3, taskName: "實作", attempt: 2 },
        }),
      },
    });
    view();
    expect(await screen.findByTestId("progress-tasks")).toHaveTextContent("13 / 23 任務完成");
    expect(screen.getByTestId("progress-tokens")).toHaveTextContent("Token: 45,230 / 100,000");
    expect(screen.getByTestId("progress-token-pct")).toHaveTextContent("45.2%");
    expect(screen.getByTestId("progress-elapsed")).toHaveTextContent("耗時：01:23:45");
    expect(screen.getByTestId("progress-current")).toHaveTextContent("目前：實作（G2-T1，第 2 次）");
    expect(screen.queryByTestId("token-warning")).toBeNull();
  });

  it("Token 達警告閾值（系統參數 0.8）顯示警示、超過預算顯示超限", async () => {
    backend({ runs: [runSummary()], details: { r1: runDetail({ totalTokensUsed: 85000, status: "PAUSED", bridgeStatus: "PAUSED" }) } });
    const first = view();
    expect(await screen.findByTestId("token-warning")).toHaveTextContent("Token 使用量已達預算的 80%");
    first.unmount();
    backend({ runs: [runSummary()], details: { r1: runDetail({ totalTokensUsed: 120000, status: "PAUSED", bridgeStatus: "PAUSED" }) } });
    view();
    expect(await screen.findByTestId("token-warning")).toHaveTextContent("Token 已超出預算");
  });

  it("Bridge 不可達：進度為資料庫衍生值，顯示提示（契約 §1.2.3 仍回 200）", async () => {
    backend({ runs: [runSummary()], details: { r1: runDetail({ bridge: { connected: false, checkedAt: "2026-10-15T08:30:12Z" } }) } });
    view();
    expect(await screen.findByTestId("bridge-down")).toHaveTextContent("Engine Bridge 目前無法連線");
  });
});

describe("執行頁：引擎能力晶片「自動突變」「自演化」（契約 §4.2 E-21，v1.3 D-11）", () => {
  const caps = (autoMutation: EngineCapabilityState, selfEvolution: EngineCapabilityState): EngineCapabilities => ({ autoMutation, selfEvolution });
  const chip = (key: "autoMutation" | "selfEvolution") =>
    within(screen.getByTestId("engine-capabilities"))
      .getAllByTestId("engine-capability")
      .find((c) => c.getAttribute("data-capability") === key)!;

  async function open(engineCapabilities: EngineCapabilities | null | undefined) {
    backend({ runs: [runSummary()], details: { r1: runDetail({ engineCapabilities }) } });
    const rendered = view();
    await screen.findByTestId("run-status"); // 批次詳情載入後才有進度卡
    return rendered;
  }

  // [晶片, 狀態, 晶片文字, tooltip 要講清楚的重點]
  const CELLS: Array<["autoMutation" | "selfEvolution", EngineCapabilityState, string, string]> = [
    ["autoMutation", "ENABLED", "自動突變：已啟用", "Brain 逐步校正：失敗步驟先由 Brain 改寫再重試"],
    ["autoMutation", "OFF", "自動突變：關閉", "失敗步驟照舊自動重試"],
    ["autoMutation", "UNAVAILABLE_NO_API_KEY", "自動突變：無金鑰不可用", "沒有金鑰可送：批次照常執行，只是沒有 Brain"],
    ["selfEvolution", "ENABLED", "自演化（僅提案）：已啟用", "不自動套用"],
    ["selfEvolution", "OFF", "自演化：關閉", "沒有 AI 演化提案"],
    ["selfEvolution", "UNAVAILABLE_NO_API_KEY", "自演化：無金鑰不可用", "AI 演化提案不會發生"],
  ];

  it.each(CELLS)("%s＝%s：晶片文字「%s」，tooltip 說明「%s」", async (key, state, text, hintPart) => {
    await open(key === "autoMutation" ? caps(state, "OFF") : caps("OFF", state));
    const c = chip(key);
    expect(c).toHaveTextContent(text);
    expect(c).toHaveAttribute("data-state", state);
    expect(c.getAttribute("title")).toContain(hintPart);
  });

  it("兩枚晶片固定順序：自動突變在前、自演化在後；整組有「引擎能力」的群組名稱", async () => {
    await open(caps("ENABLED", "ENABLED"));
    const group = screen.getByRole("group", { name: "引擎能力" });
    expect(
      within(group)
        .getAllByTestId("engine-capability")
        .map((c) => c.getAttribute("data-capability")),
    ).toEqual(["autoMutation", "selfEvolution"]);
  });

  it("🔴 自演化「已啟用」讓人看得出「只提案、不自動套用」：文字帶「僅提案」、tooltip 說明與設定和自治等級無關（有金鑰的等級 3 批次也是這個值）", async () => {
    await open(caps("OFF", "ENABLED"));
    const c = chip("selfEvolution");
    expect(c.textContent).toContain("僅提案");
    expect(c.getAttribute("title")).toContain("不自動套用");
    expect(c.getAttribute("title")).toContain("只寫進引擎日誌");
    expect(c.getAttribute("title")).toContain("與設定和自治等級無關");
  });

  it("三態的外觀互不相同（已啟用／關閉／無金鑰不可用要一眼分得出來）", async () => {
    const first = await open(caps("ENABLED", "OFF"));
    const enabled = chip("autoMutation").className;
    const off = chip("selfEvolution").className;
    first.unmount();
    await open(caps("UNAVAILABLE_NO_API_KEY", "OFF"));
    const unavailable = chip("autoMutation").className;
    expect(new Set([enabled, off, unavailable]).size).toBe(3);
  });

  it.each([
    ["缺席（V10 之前建立的批次）", undefined],
    ["null", null],
  ])("engineCapabilities %s：整列晶片不顯示（不猜測），進度卡其餘內容照常", async (_name, value) => {
    await open(value);
    expect(screen.queryByTestId("engine-capabilities")).toBeNull();
    expect(screen.queryByTestId("engine-capability")).toBeNull();
    expect(screen.getByTestId("progress-tasks")).toHaveTextContent("1 / 3 任務完成");
  });

  it("後端日後新增狀態值：顯示原值、不崩潰；缺一個欄位時只顯示另一枚", async () => {
    await open({ autoMutation: "FUTURE_STATE", selfEvolution: undefined } as unknown as EngineCapabilities);
    expect(screen.getAllByTestId("engine-capability")).toHaveLength(1);
    expect(chip("autoMutation")).toHaveTextContent("自動突變：FUTURE_STATE");
    expect(chip("autoMutation")).not.toHaveAttribute("title"); // 沒有說明文字就不放空 tooltip
  });

  it("切換批次後取該批次的值（建立時凍結，各批次不同）", async () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    backend({
      runs: [runSummary({ id: "r2", runNumber: 2 }), runSummary({ id: "r1", runNumber: 1, status: "COMPLETED" })],
      details: {
        r2: runDetail({ id: "r2", runNumber: 2, engineCapabilities: caps("ENABLED", "ENABLED") }),
        r1: runDetail({ id: "r1", runNumber: 1, status: "COMPLETED", bridgeStatus: "COMPLETED", engineCapabilities: caps("UNAVAILABLE_NO_API_KEY", "OFF") }),
      },
    });
    view();
    await waitFor(() => expect(chip("autoMutation")).toHaveTextContent("自動突變：已啟用"));
    await userEvent.selectOptions(await screen.findByTestId("run-select"), "r1");
    await waitFor(() => expect(chip("autoMutation")).toHaveTextContent("自動突變：無金鑰不可用"));
    expect(chip("selfEvolution")).toHaveTextContent("自演化：關閉");
  });
});

describe("執行頁：待審核項目與審核動作（US-E-07、E-08）", () => {
  const reviews = (...items: ReturnType<typeof reviewItem>[]) => ({
    runs: [runSummary({ status: "PAUSED" })],
    details: { r1: runDetail({ status: "PAUSED", bridgeStatus: "PAUSED", pendingReviews: items }) },
  });

  it("每列：種類中文、原因、所屬目標／任務、查看任務連結；四顆按鈕依 allowedDecisions 啟用（TASK_CONFIRM 只有通過／拒絕）", async () => {
    backend(reviews(reviewItem()));
    view();
    const row = await screen.findByTestId("review-row");
    expect(within(row).getByTestId("review-kind")).toHaveTextContent("確認任務");
    expect(within(row).getByTestId("review-reason")).toHaveTextContent("Level 1：請確認是否繼續執行任務「設定」");
    expect(row).toHaveTextContent("基礎 / 設定");
    expect(within(row).getByTestId("review-task-link")).toHaveAttribute("href", "/projects/p1/goals/g1/tasks/t2");
    expect(screen.getByTestId("review-count")).toHaveTextContent("1");
    const labels = within(row)
      .getAllByRole("button")
      .map((b) => b.textContent);
    expect(labels).toEqual(["通過", "重試", "跳過", "拒絕"]);
    expect(screen.getByTestId("review-approve")).toBeEnabled();
    expect(screen.getByTestId("review-reject")).toBeEnabled();
    expect(screen.getByTestId("review-retry")).toBeDisabled();
    expect(screen.getByTestId("review-skip")).toBeDisabled();
  });

  it("ESCALATED 沒有「通過」、gate 類沒有「跳過」（allowedDecisions 的資料化）", async () => {
    backend(reviews(reviewItem({ id: "rv-esc", kind: "ESCALATED", allowedDecisions: ["RETRY", "SKIP", "REJECT"], reason: "任務「設定」重試 1 次仍失敗，需要人類介入" })));
    view();
    await screen.findByTestId("review-row");
    expect(screen.getByTestId("review-approve")).toBeDisabled();
    expect(screen.getByTestId("review-retry")).toBeEnabled();
    expect(screen.getByTestId("review-skip")).toBeEnabled();
    expect(screen.getByTestId("review-reject")).toBeEnabled();
    expect(screen.getByTestId("review-kind")).toHaveTextContent("需人工介入");
  });

  it("按「通過」→ 確認對話框（原因、後果說明、選填意見）→ POST review/{review.id} body {decision, comment}；成功後移除該列並 toast", async () => {
    const { calls, world } = backend(reviews(reviewItem()));
    world.extra = (c) => {
      if (c.method === "POST" && c.path === "/api/v1/executions/r1/review/rv1") {
        world.details.r1 = { ...world.details.r1, pendingReviews: [] }; // 後端已處理：之後重抓不會再有這一筆
        return { status: 204 };
      }
      return undefined;
    };
    view();
    await userEvent.click(await screen.findByTestId("review-approve"));
    const dialog = await screen.findByTestId("review-dialog");
    expect(within(dialog).getByTestId("review-consequence")).toHaveTextContent("批次會恢復執行，開始下一個任務。");
    await userEvent.type(within(dialog).getByTestId("review-comment"), "確認無誤");
    await userEvent.click(within(dialog).getByTestId("review-confirm"));
    await waitFor(() => expect(post(calls, "/review/rv1")).toBeDefined());
    expect(post(calls, "/review/rv1")?.body).toEqual({ decision: "APPROVE", comment: "確認無誤" });
    await waitFor(() => expect(screen.queryByTestId("review-row")).toBeNull());
    expect(screen.getByText("已通過")).toBeInTheDocument();
    expect(screen.getByTestId("review-empty")).toBeInTheDocument();
  });

  it("沒填意見就不送 comment 欄位；四種決定各對映正確的 decision 值", async () => {
    const { calls, world } = backend(reviews(reviewItem({ id: "rv-g", kind: "GOAL_COMPLETED", allowedDecisions: ["APPROVE", "REJECT", "RETRY"] })));
    world.extra = (c) => (c.method === "POST" && c.path.includes("/review/") ? { status: 204 } : undefined);
    view();
    await userEvent.click(await screen.findByTestId("review-retry"));
    await userEvent.click(within(await screen.findByTestId("review-dialog")).getByTestId("review-confirm"));
    await waitFor(() => expect(post(calls, "/review/rv-g")).toBeDefined());
    expect(post(calls, "/review/rv-g")?.body).toEqual({ decision: "RETRY" });
  });

  it("拒絕：對話框用醒目確認鈕並說明後果（gate 類會取消批次）", async () => {
    backend(reviews(reviewItem({ id: "rv-g", kind: "GOAL_COMPLETED", allowedDecisions: ["APPROVE", "REJECT", "RETRY"] })));
    view();
    await userEvent.click(await screen.findByTestId("review-reject"));
    const dialog = await screen.findByTestId("review-dialog");
    expect(within(dialog).getByTestId("review-consequence")).toHaveTextContent("這個目標會被標為失敗");
    expect(within(dialog).getByTestId("review-confirm")).toHaveTextContent("確認拒絕");
  });

  it("後端 409「審核項已處理」：對話框內顯示 reason 與 traceId、不關閉；該列保留（樂觀移除已還原）", async () => {
    const { world } = backend(reviews(reviewItem()));
    world.extra = (c) =>
      c.method === "POST" && c.path === "/api/v1/executions/r1/review/rv1"
        ? failure(409, { message: "審核項已被處理", reason: "審核項已處理", details: { status: "APPROVED", decidedBy: "admin" } })
        : undefined;
    view();
    await userEvent.click(await screen.findByTestId("review-approve"));
    const dialog = await screen.findByTestId("review-dialog");
    await userEvent.click(within(dialog).getByTestId("review-confirm"));
    expect(await within(dialog).findByText(/審核項已被處理：審核項已處理（traceId：tr-409）/)).toBeInTheDocument();
    expect(screen.getAllByTestId("review-row").length).toBeGreaterThan(0);
  });

  it("ESCALATED 的「跳過」會另開後續批次：回應標頭 X-Follow-Up-Run-Id → 畫面切到新批次（Run #2）並 toast", async () => {
    const { calls, world } = backend({
      runs: [runSummary({ id: "r1", status: "FAILED" })],
      details: { r1: runDetail({ status: "FAILED", bridgeStatus: "FAILED", pendingReviews: [reviewItem({ id: "rv-esc", kind: "ESCALATED", allowedDecisions: ["RETRY", "SKIP", "REJECT"] })] }) },
    });
    world.extra = (c) => {
      if (c.method === "POST" && c.path === "/api/v1/executions/r1/review/rv-esc") {
        world.runs = [runSummary({ id: "r2", runNumber: 2, status: "RUNNING" }), runSummary({ id: "r1", status: "FAILED" })];
        world.details.r2 = runDetail({ id: "r2", runNumber: 2 });
        return new Response(null, { status: 204, headers: { "X-Follow-Up-Run-Id": "r2" } });
      }
      return undefined;
    };
    view();
    await userEvent.click(await screen.findByTestId("review-skip"));
    await userEvent.click(within(await screen.findByTestId("review-dialog")).getByTestId("review-confirm"));
    expect(await screen.findByText("已跳過，已開啟後續批次並切換過去")).toBeInTheDocument();
    await waitFor(() => expect(calls.some((c) => c.method === "GET" && c.path === "/api/v1/executions/r2")).toBe(true));
    expect(await screen.findByTestId("run-number")).toHaveTextContent("Run #2");
  });
});

describe("執行頁：後端暫時不可用（DEF-AC-007；經 nginx 時 backend 重啟的那幾秒一律 502）", () => {
  it("第一次就載不到專案（沒有任何資料）：顯示「無法載入專案」與重試", async () => {
    stubApi(() => failure(502, { message: "Bad Gateway" }));
    view();
    expect(await screen.findByText("無法載入專案")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重試" })).toBeInTheDocument();
    expect(screen.queryByTestId("execute-view")).toBeNull();
  });

  it("已載入之後的背景重抓失敗（502）：整頁不換成錯誤畫面——標題、串流狀態點、日誌與審核卡都還在，等後端恢復後自己回來", async () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    backend({ runs: [runSummary({ status: "RUNNING" })], details: { r1: runDetail() } });
    const client = makeClient();
    render(
      <Providers client={client}>
        <ExecuteView />
      </Providers>,
    );
    await screen.findByRole("heading", { name: "專案執行：AISDLC Core Platform" });
    await screen.findByTestId("sse-status");

    stubApi(() => failure(502, { message: "Bad Gateway" })); // 此後所有請求都是 502
    await act(async () => {
      await client.invalidateQueries({ queryKey: ["projects"] }); // 例如串流事件之後的去抖重抓
    });
    await waitFor(() => expect(client.getQueryState(["projects", "detail", "p1"])?.status).toBe("error"));
    expect(screen.queryByText("無法載入專案")).toBeNull(); // 缺陷版本：整頁換成錯誤，串流狀態點與日誌一併消失
    expect(screen.getByRole("heading", { name: "專案執行：AISDLC Core Platform" })).toBeInTheDocument();
    for (const id of ["sse-status", "log-card", "review-card"]) expect(screen.getByTestId(id)).toBeInTheDocument();
  });
});

describe("執行頁：批次下拉（預設最新；切換重訂閱）", () => {
  it("列出批次（最新標示、狀態、開始時間）；切換後改看該批次的詳情，兩條串流重新連到新批次", async () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    const { calls } = backend({
      runs: [runSummary({ id: "r2", runNumber: 2, status: "RUNNING" }), runSummary({ id: "r1", runNumber: 1, status: "COMPLETED" })],
      details: { r2: runDetail({ id: "r2", runNumber: 2 }), r1: runDetail({ id: "r1", runNumber: 1, status: "COMPLETED", bridgeStatus: "COMPLETED" }) },
    });
    view();
    const select = (await screen.findByTestId("run-select")) as HTMLSelectElement;
    expect([...select.options].map((o) => o.text.split(" · ").slice(0, 2).join(" · "))).toEqual(["Run #2（最新） · 執行中", "Run #1 · 已完成"]);
    expect(select.value).toBe("r2");
    await waitFor(() => expect(FakeEventSource.instances.length).toBe(2));
    expect(FakeEventSource.instances[0].url).toContain("/executions/r2/");

    await userEvent.selectOptions(select, "r1");
    expect(await screen.findByTestId("run-number")).toHaveTextContent("Run #1");
    expect(calls.some((c) => c.path === "/api/v1/executions/r1")).toBe(true);
    await waitFor(() => expect(FakeEventSource.instances.length).toBe(4));
    expect(FakeEventSource.instances[0].closed).toBe(true);
    expect(FakeEventSource.lastOf("logs")!.url).toContain("/executions/r1/logs");
  });

  it("批次列表項的 bridgeStatus（契約 §1.2.2，C-11）：RUNNING＋PAUSING 時下拉的狀態字樣是「暫停中」並附晶片；切到已完成的批次，晶片消失", async () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    backend({
      runs: [runSummary({ id: "r2", runNumber: 2, status: "RUNNING", bridgeStatus: "PAUSING" }), runSummary({ id: "r1", runNumber: 1, status: "COMPLETED" })],
      details: { r2: runDetail({ id: "r2", runNumber: 2, bridgeStatus: "PAUSING" }), r1: runDetail({ id: "r1", runNumber: 1, status: "COMPLETED", bridgeStatus: "COMPLETED" }) },
    });
    view();
    const select = (await screen.findByTestId("run-select")) as HTMLSelectElement;
    expect([...select.options].map((o) => o.text.split(" · ").slice(0, 2).join(" · "))).toEqual(["Run #2（最新） · 暫停中", "Run #1 · 已完成"]);
    expect(await screen.findByTestId("bridge-chip")).toHaveTextContent("暫停中");
    expect(screen.getByTestId("bridge-chip")).toHaveAttribute("data-bridge", "PAUSING");

    await userEvent.selectOptions(select, "r1");
    await waitFor(() => expect(screen.queryByTestId("bridge-chip")).toBeNull());
  });
});

describe("執行頁：即時更新（SSE → 畫面）", () => {
  it("/logs 的日誌行、狀態變化、審核請求即時出現；/metrics 的進度快照即時更新進度卡與 DAG 節點", async () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    backend({ runs: [runSummary()], details: { r1: runDetail({ completedSteps: 0, totalSteps: 3, totalTokensUsed: 0 }) } });
    view();
    await screen.findByTestId("progress-tasks");
    await waitFor(() => expect(FakeEventSource.lastOf("logs")).toBeDefined());
    const logs = FakeEventSource.lastOf("logs")!;
    const metrics = FakeEventSource.lastOf("metrics")!;
    logs.open();
    metrics.open();
    await waitFor(() => expect(screen.getByTestId("sse-status")).toHaveAttribute("data-state", "open"));

    logs.emit("log", { seq: 21, ts: "2026-10-15T08:30:13Z", source: "STEP", level: "INFO", message: "開始：初始化（G1-T1，第 1 次）", stepId: "G1-T1", taskId: "t1", stepStatus: "STARTED" }, "21");
    logs.emit("log", { seq: 22, ts: "2026-10-15T08:30:14Z", source: "ENGINE", level: "INFO", message: "引擎原始輸出一行" }, "22");
    logs.emit("status-change", { seq: 23, ts: "2026-10-15T08:30:15Z", runStatus: "PAUSED", bridgeStatus: "PAUSED", reason: "在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）" }, "23");
    metrics.emit("progress-update", { seq: 23, ts: "2026-10-15T08:30:15Z", runStatus: "PAUSED", bridgeStatus: "PAUSED", completedSteps: 1, totalSteps: 3, progressPct: 33.3 }, "23.1");
    metrics.emit("token-update", { seq: 23, ts: "2026-10-15T08:30:15Z", tokensUsed: 1240, delta: 1240, contextPct: 0.6, tokenBudget: 100000, budgetUsageRate: 1.2 }, "23.2");

    const lines = await screen.findAllByTestId("log-line");
    expect(lines.map((l) => l.textContent)).toEqual([
      expect.stringContaining("開始：初始化（G1-T1，第 1 次）"),
      expect.stringContaining("狀態：已暫停（在步驟邊界暫停（已完成 1 步，續跑點：G1-T2））"),
    ]);
    expect(lines[1]).toHaveAttribute("data-kind", "status");
    expect(screen.getByTestId("log-count")).toHaveTextContent("2 行");

    // 進度卡與按鈕跟著即時事件變化（PAUSED → 「恢復」）
    await waitFor(() => expect(screen.getByTestId("progress-tasks")).toHaveTextContent("1 / 3 任務完成"));
    expect(screen.getByTestId("progress-tokens")).toHaveTextContent("Token: 1,240 / 100,000");
    expect(await screen.findByTestId("control-resume")).toBeEnabled();

    // 「顯示引擎原始輸出」開關：打開後引擎行（淡色）才顯示
    await userEvent.click(screen.getByTestId("log-engine-toggle"));
    await waitFor(() => expect(screen.getAllByTestId("log-line")).toHaveLength(3));
    // 搜尋過濾
    await userEvent.type(screen.getByTestId("log-search"), "引擎原始");
    await waitFor(() => expect(screen.getAllByTestId("log-line")).toHaveLength(1));
    expect(screen.getByTestId("log-count")).toHaveTextContent("1 / 3 行");

    // DAG：串流看到的任務狀態即時疊到節點上（t1 STARTED → 進行中）
    expect(await screen.findByTestId("dag-task-t1")).toHaveAttribute("data-tone", "active");
  });

  it("review-request 事件即時加進「待審核項目」並更新計數徽章", async () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    backend({ runs: [runSummary({ status: "RUNNING" })], details: { r1: runDetail() } });
    view();
    await screen.findByTestId("review-empty");
    await waitFor(() => expect(FakeEventSource.lastOf("logs")).toBeDefined());
    FakeEventSource.lastOf("logs")!.emit("review-request", { seq: 41, sub: 1, ts: "2026-10-15T08:30:20Z", review: reviewItem() }, "41.1");
    expect(await screen.findByTestId("review-row")).toBeInTheDocument();
    expect(screen.getByTestId("review-count")).toHaveTextContent("1");
  });
});
