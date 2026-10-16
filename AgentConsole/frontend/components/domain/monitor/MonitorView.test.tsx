import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Alert, ExecutionRunDetail, ExecutionRunSummary, ProjectMetrics } from "@/lib/api/types";
import { resetLayoutCache, LAYOUT_STORAGE_KEY } from "@/lib/nav/monitorLayout";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall, type Reply } from "@/tests/helpers/api";
import { alert, metrics, projectDetail, runDetail, runSummary, TS } from "@/tests/helpers/runFixtures";
import { FIXTURE } from "@/tests/helpers/settingsFixtures";
import { MonitorView } from "./MonitorView";

vi.mock("next/navigation", () => ({
  useParams: () => ({ projectId: "p1" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/projects/p1/monitor",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
// recharts 在 jsdom 沒有版面可量（寬高為 0）：圖表換成空殼，圖表本身由 Playwright 驗證真的畫出來
vi.mock("@/components/charts/TokenTrendChart", () => ({
  TokenTrendChart: ({ rows }: { rows: unknown[] }) => <div data-testid="token-trend-chart-stub">{rows.length} 點</div>,
  formatTokensShort: (v: number) => String(v),
}));
vi.mock("@/components/charts/tremor/AreaChart", () => ({
  AreaChart: ({ data }: { data: unknown[] }) => <div data-testid="area-chart-stub">{data.length} 列</div>,
}));

type World = {
  runs: ExecutionRunSummary[];
  metrics: ProjectMetrics;
  alerts: Alert[];
  detail: ExecutionRunDetail | null;
  extra?: (c: ApiCall) => Reply;
};

const page = <T,>(content: T[], size = 20, p = 0, total = content.length) => ({ content, page: p, size, totalElements: total, totalPages: Math.max(1, Math.ceil(total / size)) });

function backend(over: Partial<World> = {}) {
  const w: World = {
    runs: [runSummary({ id: "r2", runNumber: 2 }), runSummary({ id: "r1", runNumber: 1, status: "COMPLETED", tasksCompleted: 3, successRate: 100, totalTokensUsed: 3720, durationSec: 65 })],
    metrics: metrics(),
    alerts: [],
    detail: runDetail({ id: "r2", runNumber: 2 }),
    ...over,
  };
  const { calls } = stubApi((c) => {
    const custom = w.extra?.(c);
    if (custom) return custom;
    if (c.method !== "GET") return undefined;
    switch (c.path) {
      case "/api/v1/projects/p1":
        return { data: projectDetail() };
      case "/api/v1/projects/p1/executions":
        return { data: page(w.runs) };
      case "/api/v1/settings/monitor":
        return { data: [FIXTURE.refreshIntervalMs("10000")] };
      case "/api/v1/monitor/projects/p1/metrics":
        return { data: w.metrics };
      case "/api/v1/monitor/projects/p1/token-trend":
        return {
          data: [
            { bucketStart: "2026-10-15T08:00:00Z", tokens: 1240, cumulativeTokens: 1240, budget: 100000 },
            { bucketStart: "2026-10-15T09:00:00Z", tokens: 2480, cumulativeTokens: 3720, budget: 100000 },
          ],
        };
      case "/api/v1/monitor/projects/p1/task-trend":
        return { data: [{ bucketStart: "2026-10-15T08:00:00Z", started: 3, completed: 2, failed: 1, retried: 1 }] };
      case "/api/v1/monitor/projects/p1/alerts":
        return { data: w.alerts };
      case "/api/v1/monitor/projects/p1/logs":
        return {
          data: page(
            [
              { id: "step:1", timestamp: "2026-10-15T08:30:13Z", level: "INFO", source: "STEP", message: "開始：初始化（G1-T1，第 1 次）" },
              { id: "step:2", timestamp: "2026-10-15T08:30:20Z", level: "ERROR", source: "STEP", message: "失敗：實作（G2-T1，第 2 次）：評估未通過" },
            ],
            20,
            0,
            45,
          ),
        };
    }
    const steps = /^\/api\/v1\/executions\/([^/]+)\/steps$/.exec(c.path);
    if (steps) {
      return {
        data: page(
          [
            { id: "s1", runId: steps[1], taskId: "t1", taskName: "初始化", stepNumber: 5, stepId: "G1-T1", attempt: 1, action: "G1-T1: 初始化", status: "STARTED", timestamp: "2026-10-15T08:30:13Z" },
            {
              id: "s2",
              runId: steps[1],
              taskId: "t1",
              taskName: "初始化",
              stepNumber: 7,
              stepId: "G1-T1",
              attempt: 1,
              action: "G1-T1: 初始化",
              status: "COMPLETED",
              tokensUsed: 1240,
              timestamp: "2026-10-15T08:30:15Z",
            },
            { id: "s3", runId: steps[1], taskId: "t2", taskName: "設定", stepNumber: 9, stepId: "G1-T2", attempt: 2, action: "G1-T2: 設定", status: "RETRYING", timestamp: "2026-10-15T08:30:18Z" },
            {
              id: "s4",
              runId: steps[1],
              taskId: "t2",
              taskName: "設定",
              stepNumber: 11,
              stepId: "G1-T2",
              attempt: 2,
              action: "G1-T2: 設定",
              status: "FAILED",
              errorMessage: "評估未通過",
              timestamp: "2026-10-15T08:30:20Z",
            },
          ],
          200,
        ),
      };
    }
    const exec = /^\/api\/v1\/executions\/([^/]+)$/.exec(c.path);
    if (exec) return w.detail ? { data: { ...w.detail, id: exec[1] } } : undefined;
    return undefined;
  });
  return { calls, world: w };
}

function view() {
  return render(
    <Providers client={makeClient()}>
      <MonitorView />
    </Providers>,
  );
}

const lastOf = (calls: ApiCall[], suffix: string) => [...calls].reverse().find((c) => c.method === "GET" && c.path.endsWith(suffix));

beforeEach(() => {
  signIn("OPERATOR", "operator");
  window.localStorage.clear();
  resetLayoutCache();
});

describe("監控頁：版面（設計稿畫面 8）", () => {
  it("標題「專案監控：{名稱}」、返回連結、右側時間範圍（預設 24 小時）與執行批次下拉（含「全部批次」）", async () => {
    backend();
    view();
    expect(await screen.findByRole("heading", { name: "專案監控：AISDLC Core Platform" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回專案" })).toHaveAttribute("href", "/projects/p1");
    const range = screen.getByTestId("range-select") as HTMLSelectElement;
    expect(range.value).toBe("24h");
    expect([...range.options].map((o) => o.text)).toEqual(["最近 1 小時", "最近 24 小時", "最近 7 天", "最近 30 天"]);
    const runSel = (await screen.findByTestId("run-select")) as HTMLSelectElement;
    expect(runSel.value).toBe("");
    expect(runSel.options[0].text).toBe("全部批次");
    await waitFor(() => expect(runSel.options).toHaveLength(3));
  });

  it("九個區塊依預設順序出現；底部有「匯出報表」「設定告警」「自訂儀表板」", async () => {
    backend();
    view();
    await screen.findByTestId("kpi-cards");
    const ids = within(screen.getByTestId("monitor-sections"))
      .getAllByRole("region")
      .map((s) => s.getAttribute("data-section"));
    expect(ids).toEqual(["kpi", "token", "distribution", "trends", "timeline", "logs", "alerts", "compare", "agent"]);
    expect(screen.getByTestId("export-csv")).toHaveTextContent("匯出報表");
    expect(screen.getByTestId("alert-settings-link")).toHaveAttribute("href", "/settings");
    expect(screen.getByTestId("layout-toggle")).toHaveTextContent("自訂儀表板");
  });
});

describe("監控頁：指標卡（契約 §1.3.1；US-M-01）", () => {
  it("四張卡數值與 delta：完成率 34.8%↑、成功率 92.3%↓、重試率 7.7%↑、Token 45,230↑；顏色依語意", async () => {
    backend();
    view();
    expect(await screen.findByTestId("kpi-taskCompletionRate-value")).toHaveTextContent("34.8%");
    expect(screen.getByTestId("kpi-taskCompletionRate-delta")).toHaveTextContent("↑ 12.3%");
    expect(screen.getByTestId("kpi-taskCompletionRate-delta")).toHaveClass("text-wg-primary"); // 完成率升＝好
    expect(screen.getByTestId("kpi-taskSuccessRate-value")).toHaveTextContent("92.3%");
    expect(screen.getByTestId("kpi-taskSuccessRate-delta")).toHaveTextContent("↓ 2.1%");
    expect(screen.getByTestId("kpi-taskSuccessRate-delta")).toHaveClass("text-wg-error"); // 成功率降＝壞
    expect(screen.getByTestId("kpi-retryRate-value")).toHaveTextContent("7.7%");
    expect(screen.getByTestId("kpi-retryRate-delta")).toHaveClass("text-wg-accent"); // 重試率升＝注意
    expect(screen.getByTestId("kpi-totalTokens-value")).toHaveTextContent("45,230");
    expect(screen.getByTestId("kpi-totalTokens-delta")).toHaveTextContent("↑ 8,430");
  });

  it("PRD 另外六項：專案完成率、目標達成率、平均重試次數、Token 預算使用率、平均任務時間、Agent 可用率", async () => {
    backend();
    view();
    const secondary = await screen.findByTestId("kpi-secondary");
    expect(within(secondary).getByTestId("kpi-projectCompletionRate-value")).toHaveTextContent("13.0%");
    expect(within(secondary).getByTestId("kpi-goalAchievementRate-value")).toHaveTextContent("50.0%");
    expect(within(secondary).getByTestId("kpi-averageRetryCount-value")).toHaveTextContent("0.50");
    expect(within(secondary).getByTestId("kpi-tokenBudgetUsageRate-value")).toHaveTextContent("45.2%");
    expect(within(secondary).getByTestId("kpi-averageTaskDurationSec-value")).toHaveTextContent("48s");
    expect(within(secondary).getByTestId("kpi-agentAvailability-value")).toHaveTextContent("100.0%");
  });

  it("無法計算（value 為 null）顯示「—」；沒有比較值（delta 為 null）不顯示 delta 行", async () => {
    const m = metrics();
    backend({ metrics: { ...m, retryRate: { value: null, previousValue: null, delta: null }, totalTokens: { value: 0, previousValue: null, delta: null } } });
    view();
    expect(await screen.findByTestId("kpi-retryRate-value")).toHaveTextContent("—");
    expect(screen.queryByTestId("kpi-retryRate-delta")).toBeNull();
    expect(screen.getByTestId("kpi-totalTokens-value")).toHaveTextContent("0");
    expect(screen.queryByTestId("kpi-totalTokens-delta")).toBeNull();
  });

  it("後端失敗：指標區顯示錯誤與 traceId，其餘卡片照常", async () => {
    const { world } = backend();
    world.extra = (c) => (c.path === "/api/v1/monitor/projects/p1/metrics" ? failure(500, { message: "伺服器錯誤" }) : undefined);
    view();
    expect(await screen.findByText("無法載入指標")).toBeInTheDocument();
    expect(await screen.findByTestId("alerts-card")).toBeInTheDocument();
  });
});

describe("監控頁：時間範圍與批次選擇（M-01、M-02）", () => {
  it("改時間範圍：每個監控端點的 from／to 隨之改變（from＝現在減範圍、同一個時鐘），趨勢的 bucket 為 DAY（>48 小時）", async () => {
    const { calls } = backend();
    view();
    await screen.findByTestId("kpi-cards");
    const first = lastOf(calls, "/metrics")!;
    expect(Date.parse(first.query.get("to")!) - Date.parse(first.query.get("from")!)).toBe(86_400_000);
    expect(lastOf(calls, "/token-trend")!.query.get("bucket")).toBe("HOUR");

    await userEvent.selectOptions(screen.getByTestId("range-select"), "7d");
    await waitFor(() => {
      const m = lastOf(calls, "/metrics")!;
      expect(Date.parse(m.query.get("to")!) - Date.parse(m.query.get("from")!)).toBe(7 * 86_400_000);
    });
    for (const suffix of ["/token-trend", "/task-trend"]) {
      await waitFor(() => expect(lastOf(calls, suffix)!.query.get("bucket")).toBe("DAY"));
    }
    await waitFor(() => {
      const logs = lastOf(calls, "/logs")!;
      expect(Date.parse(logs.query.get("to")!) - Date.parse(logs.query.get("from")!)).toBe(7 * 86_400_000);
    });
  });

  it("選一個批次：metrics／趨勢／告警／日誌都帶 runId；選回「全部批次」就不帶", async () => {
    const { calls } = backend();
    view();
    const runSel = await screen.findByTestId("run-select");
    await waitFor(() => expect((runSel as HTMLSelectElement).options).toHaveLength(3));
    expect(lastOf(calls, "/metrics")!.query.get("runId")).toBeNull();
    await userEvent.selectOptions(runSel, "r1");
    for (const suffix of ["/metrics", "/token-trend", "/task-trend", "/alerts", "/logs"]) {
      await waitFor(() => expect(lastOf(calls, suffix)!.query.get("runId"), suffix).toBe("r1"));
    }
    await userEvent.selectOptions(runSel, "");
    await waitFor(() => expect(lastOf(calls, "/metrics")!.query.get("runId")).toBeNull());
  });
});

describe("監控頁：分佈與趨勢（US-M-02、M-03；UI-CHT）", () => {
  it("任務狀態分佈四條（完成 13／執行中 2／失敗 1／待處理 7）；執行時間分佈最高的標主色；重試分佈", async () => {
    backend();
    view();
    const bars = await screen.findByTestId("status-bars");
    expect(within(bars).getByTestId("status-bar-done")).toHaveTextContent("完成 (13)");
    expect(within(bars).getByTestId("status-bar-running")).toHaveTextContent("執行中 (2)");
    expect(within(bars).getByTestId("status-bar-failed")).toHaveTextContent("失敗 (1)");
    expect(within(bars).getByTestId("status-bar-pending")).toHaveTextContent("待處理 (7)");
    expect(bars).toHaveAttribute("aria-label", "任務狀態分佈：完成 13、執行中 2、失敗 1、待處理 7");

    const cols = within(screen.getByTestId("duration-chart")).getAllByTestId("duration-chart-col");
    expect(cols).toHaveLength(4);
    const highlighted = cols.filter((c) => c.querySelector('[data-highlight="true"]'));
    expect(highlighted).toHaveLength(1);
    expect(highlighted[0]).toHaveTextContent("T3");
    expect(highlighted[0]).toHaveTextContent("1m 08s");
    expect(within(screen.getByTestId("retry-chart")).getAllByTestId("retry-chart-col")).toHaveLength(6);
  });

  it("Token 趨勢取到資料就畫圖（累計＋預算線）；沒資料顯示空狀態；任務趨勢與成功失敗比率（2 完成 1 失敗＝66.7%／33.3%）", async () => {
    const first = backend();
    view();
    expect(await screen.findByTestId("token-trend-chart-stub")).toHaveTextContent("2 點");
    expect(await screen.findByTestId("area-chart-stub")).toHaveTextContent("1 列");
    const ratio = await screen.findByTestId("ratio-chart");
    expect(ratio).toHaveAttribute("aria-label", expect.stringContaining("成功 66.7% 失敗 33.3%"));
    expect(first.calls.some((c) => c.path.endsWith("/token-trend"))).toBe(true);
  });

  it("Token 趨勢沒有資料：顯示「這段時間沒有 Token 使用紀錄」", async () => {
    const { world } = backend();
    world.extra = (c) => (c.path === "/api/v1/monitor/projects/p1/token-trend" ? { data: [] } : undefined);
    view();
    expect(await screen.findByTestId("token-trend-empty")).toHaveTextContent("這段時間沒有 Token 使用紀錄");
  });
});

describe("監控頁：事件時間軸與日誌查詢（US-M-03、M-04）", () => {
  it("時間軸取最新批次的步驟事件（來源 steps）：開始／完成／重試／失敗四種色調，依 seq 排序", async () => {
    const { calls } = backend();
    view();
    const items = await screen.findAllByTestId("timeline-item");
    expect(items.map((i) => i.getAttribute("data-tone"))).toEqual(["start", "done", "retry", "failed"]);
    expect(items.map((i) => i.querySelector("span.text-xs")?.textContent)).toEqual(["G1-T1 開始", "G1-T1 完成", "G1-T2 重試", "G1-T2 失敗"]);
    expect(screen.getByTestId("timeline-run")).toHaveTextContent("Run #2");
    expect(lastOf(calls, "/steps")!.path).toBe("/api/v1/executions/r2/steps");
    expect(lastOf(calls, "/steps")!.query.get("size")).toBe("200");
  });

  it("日誌列：時間（muted）＋等級（INFO／ERROR 著色）＋訊息；預設全部、由新到舊、每頁 20、共 45 筆分 3 頁", async () => {
    const { calls } = backend();
    view();
    const rows = await screen.findAllByTestId("log-row");
    expect(rows).toHaveLength(2);
    expect(rows[1]).toHaveAttribute("data-level", "ERROR");
    expect(rows[1]).toHaveTextContent("失敗：實作（G2-T1，第 2 次）：評估未通過");
    expect(screen.getByTestId("log-total")).toHaveTextContent("共 45 筆");
    expect(screen.getByTestId("log-page")).toHaveTextContent("1 / 3");
    const q = lastOf(calls, "/logs")!.query;
    expect([q.get("level"), q.get("order"), q.get("page"), q.get("size")]).toEqual(["ALL", "desc", "0", "20"]);
  });

  it("等級下拉、關鍵字（去抖）、任務 id 篩選都帶進查詢；改篩選回第一頁；翻頁帶 page", async () => {
    const { calls } = backend();
    view();
    await screen.findAllByTestId("log-row");
    await userEvent.click(screen.getByTestId("log-next"));
    await waitFor(() => expect(lastOf(calls, "/logs")!.query.get("page")).toBe("1"));
    expect(screen.getByTestId("log-page")).toHaveTextContent("2 / 3");

    await userEvent.selectOptions(screen.getByTestId("log-level"), "ERROR");
    await waitFor(() => expect(lastOf(calls, "/logs")!.query.get("level")).toBe("ERROR"));
    expect(lastOf(calls, "/logs")!.query.get("page")).toBe("0");

    const before = calls.filter((c) => c.path.endsWith("/logs")).length;
    await userEvent.type(screen.getByTestId("log-keyword"), "評估");
    // 去抖：打字當下不立刻打後端
    expect(calls.filter((c) => c.path.endsWith("/logs")).length).toBe(before);
    await waitFor(() => expect(lastOf(calls, "/logs")!.query.get("q")).toBe("評估"), { timeout: 2000 });
    await userEvent.type(screen.getByTestId("log-task"), "t-123");
    await waitFor(() => expect(lastOf(calls, "/logs")!.query.get("taskId")).toBe("t-123"), { timeout: 2000 });
  });

  it("沒有符合條件的日誌：顯示空狀態", async () => {
    const { world } = backend();
    world.extra = (c) => (c.path === "/api/v1/monitor/projects/p1/logs" ? { data: page([], 20, 0, 0) } : undefined);
    view();
    expect(await screen.findByTestId("log-empty")).toBeInTheDocument();
    expect(screen.getByTestId("log-total")).toHaveTextContent("共 0 筆");
  });
});

describe("監控頁：告警（US-M-05）", () => {
  const warn = alert({ id: "a1" });
  const crit = alert({ id: "a2", rule: "TOKEN_BUDGET_EXCEEDED", severity: "CRITICAL", message: "Token 使用量已超出預算（2480 / 1500），已要求暫停執行", createdAt: "2026-10-15T08:30:40Z" });

  it("每列：時間、[規則] 訊息、「確認」或「已確認」；標題旁計數＝未確認數；「詳情」展開規則／對象／批次", async () => {
    backend({ alerts: [crit, { ...warn, acknowledged: true, acknowledgedBy: "operator", acknowledgedAt: TS }] });
    view();
    const rows = await screen.findAllByTestId("alert-row");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("[Token 預算超限]");
    expect(within(rows[0]).getByTestId("alert-ack")).toHaveTextContent("確認");
    expect(within(rows[1]).getByTestId("alert-acked")).toHaveTextContent("已確認");
    expect(screen.getByTestId("alerts-open-count")).toHaveTextContent("1");
    await userEvent.click(within(rows[0]).getByTestId("alert-detail-toggle"));
    const detail = within(rows[0]).getByTestId("alert-detail");
    expect(detail).toHaveTextContent("Token 預算超限（嚴重）");
    expect(detail).toHaveTextContent("run:r1");
  });

  it("按「確認」→ POST acknowledge；畫面立刻變「已確認」（樂觀更新，伺服器還沒回應就變）", async () => {
    const { world } = backend({ alerts: [warn] });
    let release: () => void = () => {};
    world.extra = (c) => {
      if (c.method === "POST" && c.path === "/api/v1/monitor/alerts/a1/acknowledge") {
        world.alerts = [{ ...warn, acknowledged: true, acknowledgedBy: "operator", acknowledgedAt: TS }];
        // 讓這次請求卡住，才看得到「伺服器回應之前」的畫面
        return new Promise<Response>((resolve) => {
          release = () => resolve(new Response(null, { status: 204 }));
        }) as unknown as Reply;
      }
      return undefined;
    };
    view();
    await userEvent.click(await screen.findByTestId("alert-ack"));
    expect(await screen.findByTestId("alert-acked")).toHaveTextContent("已確認");
    expect(screen.queryByTestId("alert-ack")).toBeNull();
    await act(async () => release());
    expect(await screen.findByText("已確認告警")).toBeInTheDocument();
  });

  it("確認失敗（例如 403／500）：樂觀更新還原回「確認」鈕，並 toast 顯示原因與 traceId", async () => {
    const { world } = backend({ alerts: [warn] });
    world.extra = (c) => (c.method === "POST" && c.path.endsWith("/acknowledge") ? failure(500, { message: "伺服器錯誤" }) : undefined);
    view();
    await userEvent.click(await screen.findByTestId("alert-ack"));
    expect(await screen.findByText(/確認告警失敗：伺服器錯誤（traceId：tr-500）/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("alert-ack")).toBeInTheDocument());
    expect(screen.queryByTestId("alert-acked")).toBeNull();
  });

  it("唯讀角色：「確認」停用並提示權限不足；沒有告警：顯示空狀態", async () => {
    signIn("VIEWER", "viewer");
    backend({ alerts: [warn] });
    const first = view();
    const ack = await screen.findByTestId("alert-ack");
    expect(ack).toBeDisabled();
    expect(ack).toHaveAttribute("title", "權限不足（唯讀角色不可確認）");
    first.unmount();
    backend({ alerts: [] });
    view();
    expect(await screen.findByTestId("alerts-empty")).toBeInTheDocument();
  });
});

describe("監控頁：批次比較與 Agent 狀態（US-M-06、M-10）", () => {
  it("批次比較：預設比較最新兩批（Run #1 對 Run #2）；列出 Token、時長、成功率…；可改選", async () => {
    backend();
    view();
    const table = await screen.findByTestId("compare-table");
    expect(within(table).getByText("Run #1")).toBeInTheDocument();
    expect(within(table).getByText("Run #2")).toBeInTheDocument();
    const row = (key: string) => screen.getByTestId(`compare-row-${key}`);
    expect(row("tokens").querySelector('[data-col="a"]')).toHaveTextContent("3,720");
    expect(row("tokens").querySelector('[data-col="b"]')).toHaveTextContent("1,240");
    expect(row("duration").querySelector('[data-col="a"]')).toHaveTextContent("1m 05s");
    expect(row("success").querySelector('[data-col="a"]')).toHaveTextContent("100.0%");
    expect(row("budget").querySelector('[data-col="b"]')).toHaveTextContent("1.2%");
    expect(row("status").querySelector('[data-col="a"]')).toHaveTextContent("已完成");
    await userEvent.selectOptions(screen.getByTestId("compare-a"), "r2");
    expect(within(screen.getByTestId("compare-table")).getAllByText("Run #2")).toHaveLength(2);
  });

  it("批次列表項的 bridgeStatus（契約 §1.2.2，C-11）：RUNNING＋PAUSING／CANCELLING 在批次比較顯示「暫停中」「取消中」晶片，下拉與比較選單的狀態字樣一併換成過渡態", async () => {
    backend({
      runs: [
        runSummary({ id: "r3", runNumber: 3, status: "RUNNING", bridgeStatus: "CANCELLING" }),
        runSummary({ id: "r2", runNumber: 2, status: "RUNNING", bridgeStatus: "PAUSING" }),
        runSummary({ id: "r1", runNumber: 1, status: "COMPLETED" }),
      ],
    });
    view();
    await screen.findByTestId("compare-table");
    // 預設比較最新兩批：A＝Run #2（PAUSING）、B＝Run #3（CANCELLING）
    const status = screen.getByTestId("compare-row-status");
    expect(within(status.querySelector('[data-col="a"]') as HTMLElement).getByTestId("bridge-chip")).toHaveTextContent("暫停中");
    expect(within(status.querySelector('[data-col="b"]') as HTMLElement).getByTestId("bridge-chip")).toHaveTextContent("取消中");
    expect(within(status.querySelector('[data-col="b"]') as HTMLElement).getByTestId("bridge-chip")).toHaveAttribute("data-bridge", "CANCELLING");
    const optionsA = [...(screen.getByTestId("compare-a") as HTMLSelectElement).options].map((o) => o.text);
    expect(optionsA).toEqual(["Run #3 · 取消中", "Run #2 · 暫停中", "Run #1 · 已完成"]);

    // 批次下拉：選項字樣是過渡態；選中過渡態的批次時，下拉旁附晶片（已完成的批次沒有）
    const runSel = (await screen.findByTestId("run-select")) as HTMLSelectElement;
    await waitFor(() => expect([...runSel.options].map((o) => o.text.split(" · ")[1])).toEqual([undefined, "取消中", "暫停中", "已完成"]));
    await userEvent.selectOptions(runSel, "r2");
    const chips = screen.getAllByTestId("bridge-chip").filter((c) => c.closest("label"));
    expect(chips.map((c) => c.textContent)).toContain("暫停中");
    await userEvent.selectOptions(runSel, "r1");
    expect(screen.getByTestId("run-select").closest("label")!.querySelector('[data-testid="bridge-chip"]')).toBeNull();
  });

  it("批次比較：已完成／失敗的批次沒有晶片，只有狀態文字（過渡態只在 RUNNING 底下成立）", async () => {
    backend({ runs: [runSummary({ id: "r2", runNumber: 2, status: "PAUSED", bridgeStatus: "PAUSING" }), runSummary({ id: "r1", runNumber: 1, status: "COMPLETED" })] });
    view();
    const status = await screen.findByTestId("compare-row-status");
    expect(within(status).queryByTestId("bridge-chip")).toBeNull();
    expect(status.querySelector('[data-col="b"]')).toHaveTextContent("已暫停");
  });

  it("只有一個批次：提示至少需要兩個", async () => {
    backend({ runs: [runSummary({ id: "r1" })] });
    view();
    expect(await screen.findByTestId("compare-empty")).toHaveTextContent("至少需要兩個執行批次");
  });

  it("Agent 狀態：Bridge 已連線＝綠燈、顯示目前任務與可用率；Bridge 不可達＝紅燈；說明只留 Bridge 實例（v1.2 的「沒有提供資源資料」說明句已移除）", async () => {
    backend({ detail: runDetail({ id: "r2", currentStep: { stepId: "G2-T1", stepNumber: 3, taskName: "實作", attempt: 1 } }) });
    const first = view();
    const light = await screen.findByTestId("agent-light");
    await waitFor(() => expect(light).toHaveTextContent("已連線，執行中"));
    expect(light).toHaveAttribute("data-connected", "true");
    expect(screen.getByTestId("agent-current")).toHaveTextContent("實作（G2-T1）");
    expect(screen.getByTestId("agent-availability")).toHaveTextContent("100.0%");
    expect(screen.getByTestId("agent-note")).toHaveTextContent("Bridge 實例：e2e-bridge。");
    expect(screen.getByTestId("agent-card")).not.toHaveTextContent("目前沒有提供這項資料");
    first.unmount();

    backend({ detail: runDetail({ id: "r2", bridge: { connected: false, checkedAt: TS } }) });
    view();
    await waitFor(() => expect(screen.getByTestId("agent-light")).toHaveTextContent("Engine Bridge 未連線"));
    expect(screen.getByTestId("agent-light")).toHaveAttribute("data-connected", "false");
    expect(screen.getByTestId("agent-note")).toBeEmptyDOMElement(); // 沒有實例資訊：段落留著但是空的（CSS :empty 隱藏）
  });
});

describe("監控頁：Agent 即時狀態的資源使用（契約 §4.3 M-19，D-12；US-M-10）", () => {
  const SAMPLE = { cpuPercent: 12.3, memoryBytes: 361_758_720, processCount: 3, sampledAt: "2026-10-15T08:30:10Z" };
  const bridge = (patch: Partial<ExecutionRunDetail["bridge"]> = {}): ExecutionRunDetail["bridge"] => ({
    connected: true,
    instance: "e2e-bridge",
    status: "RUNNING",
    runKnown: true,
    checkedAt: TS,
    ...patch,
  });
  /** 批次詳情載入完成後才有「資源使用」格（載入中整個格子區換成骨架）。 */
  const resourceCell = async () => {
    await waitFor(() => expect(screen.getByTestId("agent-run-status")).toHaveTextContent("Run #2"));
    return screen.getByTestId("agent-resources");
  };

  it("有資源：顯示 `CPU 12.3%・記憶體 345 MB・3 行程`，取樣時間放 tooltip；欄位標籤是「資源使用」", async () => {
    backend({ detail: runDetail({ id: "r2", runNumber: 2, bridge: bridge({ resources: SAMPLE }) }) });
    view();
    const cell = await resourceCell();
    expect(cell).toHaveTextContent("CPU 12.3%・記憶體 345 MB・3 行程");
    expect(cell).toHaveAttribute("title", `取樣時間 ${new Date(SAMPLE.sampledAt).toTimeString().slice(0, 8)}`);
    expect(cell.previousElementSibling).toHaveTextContent("資源使用");
    expect(screen.getByTestId("agent-card")).not.toHaveTextContent("目前沒有提供這項資料");
    expect(screen.getByTestId("agent-card")).not.toHaveTextContent("資源使用情況（CPU／記憶體）");
  });

  it("資源格自成第二列整列：既有四格（連線狀態、批次狀態、目前任務、Agent 可用率）的順序與位置不動", async () => {
    backend({ detail: runDetail({ id: "r2", runNumber: 2, bridge: bridge({ resources: SAMPLE }) }) });
    view();
    const cell = await resourceCell();
    const grid = screen.getByTestId("agent-light").closest(".grid") as HTMLElement;
    expect([...grid.children].map((c) => c.firstElementChild?.textContent)).toEqual(["連線狀態", "批次狀態", "目前任務", "Agent 可用率", "資源使用"]);
    expect(grid).toHaveClass("grid-cols-4");
    expect(cell.parentElement).toHaveClass("col-span-full");
  });

  const NO_DATA: Array<[string, Partial<ExecutionRunDetail>]> = [
    ["resources 為 null（引擎行程不存活、還沒有第一筆樣本或樣本過期）", { bridge: bridge({ resources: null }) }],
    ["resources 缺席（舊版 Bridge 沒有這個鍵）", { bridge: bridge() }],
    ["Bridge 未連線（connected=false）：就算快取裡還有舊數字也不顯示", { bridge: bridge({ connected: false, resources: SAMPLE }) }],
    ["批次已完成：詳情輪詢在終態後停止，最後一次抓到的數字不得繼續顯示", { status: "COMPLETED", bridgeStatus: "COMPLETED", bridge: bridge({ status: "COMPLETED", resources: SAMPLE }) }],
    ["批次失敗（終態）", { status: "FAILED", bridgeStatus: "FAILED", bridge: bridge({ status: "FAILED", resources: SAMPLE }) }],
    ["批次已取消（終態）", { status: "CANCELLED", bridgeStatus: "CANCELLED", bridge: bridge({ status: "CANCELLED", resources: SAMPLE }) }],
    [
      "批次暫停：pause 會終止整棵引擎行程樹，SSE 先把快取改成 PAUSED、REST 還沒重抓的空檔不得顯示暫停前的舊數字",
      { status: "PAUSED", bridgeStatus: "PAUSED", bridge: bridge({ status: "PAUSED", resources: SAMPLE }) },
    ],
  ];

  it.each(NO_DATA)("沒有資料一律單一「—」，沒有 tooltip，也沒有舊說明句：%s", async (_name, patch) => {
    backend({ detail: runDetail({ id: "r2", runNumber: 2, ...patch }) });
    view();
    const cell = await resourceCell();
    expect(cell).toHaveTextContent(/^—$/);
    expect(cell).not.toHaveAttribute("title");
    expect(screen.getByTestId("agent-card")).not.toHaveTextContent("目前沒有提供這項資料");
  });

  it("還沒有任何執行批次：資源格是「—」，不丟錯", async () => {
    backend({ runs: [], detail: null });
    view();
    await screen.findByTestId("agent-card");
    expect(screen.getByTestId("agent-resources")).toHaveTextContent(/^—$/);
    expect(screen.getByTestId("agent-light")).toHaveTextContent("尚無執行批次");
  });
});

describe("監控頁：匯出報表（US-M-07）", () => {
  function stubDownload() {
    const clicked: Array<{ download: string; href: string }> = [];
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:mock"), revokeObjectURL: vi.fn() }));
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push({ download: this.download, href: this.href });
    });
    return clicked;
  }

  it("「匯出報表」：GET report?format=csv（帶目前的時間範圍與批次），以 Content-Disposition 的檔名下載並 toast", async () => {
    const clicked = stubDownload();
    const { world, calls } = backend();
    world.extra = (c) =>
      c.path === "/api/v1/monitor/projects/p1/report"
        ? new Response("#report,AISDLC", {
            status: 200,
            headers: { "content-type": "text/csv; charset=UTF-8", "content-disposition": 'attachment; filename="monitor-report-0b8c5d1e-20261015-0840.csv"' },
          })
        : undefined;
    view();
    await userEvent.selectOptions(await screen.findByTestId("range-select"), "7d");
    await userEvent.click(screen.getByTestId("export-csv"));
    await waitFor(() => expect(clicked).toHaveLength(1));
    expect(clicked[0].download).toBe("monitor-report-0b8c5d1e-20261015-0840.csv");
    const req = lastOf(calls, "/report")!;
    expect(req.query.get("format")).toBe("csv");
    expect(Date.parse(req.query.get("to")!) - Date.parse(req.query.get("from")!)).toBe(7 * 86_400_000);
    expect(await screen.findByText("已匯出報表：monitor-report-0b8c5d1e-20261015-0840.csv")).toBeInTheDocument();
  });

  it("沒有 Content-Disposition 時用預設檔名；選了批次就帶 runId", async () => {
    const clicked = stubDownload();
    const { world, calls } = backend();
    world.extra = (c) => (c.path.endsWith("/report") ? new Response("x", { status: 200, headers: { "content-type": "text/csv" } }) : undefined);
    view();
    const runSel = await screen.findByTestId("run-select");
    await waitFor(() => expect((runSel as HTMLSelectElement).options).toHaveLength(3));
    await userEvent.selectOptions(runSel, "r1");
    await userEvent.click(screen.getByTestId("export-csv"));
    await waitFor(() => expect(clicked).toHaveLength(1));
    expect(clicked[0].download).toBe("monitor-report.csv");
    expect(lastOf(calls, "/report")!.query.get("runId")).toBe("r1");
  });

  it("「匯出 PDF」（v1.2，C-4）：GET report?format=pdf（帶目前的時間範圍與批次、Accept: application/pdf），以 Content-Disposition 的 .pdf 檔名下載並 toast", async () => {
    const clicked = stubDownload();
    const { world, calls } = backend();
    world.extra = (c) =>
      c.path === "/api/v1/monitor/projects/p1/report"
        ? new Response("%PDF-1.7", { status: 200, headers: { "content-type": "application/pdf", "content-disposition": 'attachment; filename="monitor-report-0b8c5d1e-20261015-0840.pdf"' } })
        : undefined;
    view();
    const runSel = await screen.findByTestId("run-select");
    await waitFor(() => expect((runSel as HTMLSelectElement).options).toHaveLength(3));
    await userEvent.selectOptions(runSel, "r1");
    await userEvent.click(screen.getByTestId("export-pdf"));
    await waitFor(() => expect(clicked).toHaveLength(1));
    expect(clicked[0].download).toBe("monitor-report-0b8c5d1e-20261015-0840.pdf");
    const req = lastOf(calls, "/report")!;
    expect(req.query.get("format")).toBe("pdf");
    expect(req.query.get("runId")).toBe("r1");
    expect(await screen.findByText("已匯出報表：monitor-report-0b8c5d1e-20261015-0840.pdf")).toBeInTheDocument();
    expect(screen.queryByText(/尚未提供/)).toBeNull(); // 501 與「尚未提供」提示已退役
  });

  it("匯出失敗（403）：錯誤 toast 帶 reason 與 traceId（CSV 與 PDF 同一條路徑；沒有特殊的 501 分支）", async () => {
    const { world } = backend();
    world.extra = (c) => (c.path.endsWith("/report") ? failure(403, { message: "權限不足", reason: "ACCESS_DENIED" }) : undefined);
    view();
    await userEvent.click(await screen.findByTestId("export-pdf"));
    expect(await screen.findByText(/匯出失敗：權限不足：ACCESS_DENIED（traceId：tr-403）/)).toBeInTheDocument();
  });
});

describe("監控頁：自訂儀表板（US-M-08；版面存 localStorage console.monitor.layout）", () => {
  it("存過的順序在載入時套用（未知 id 被淨化、缺的補回尾端）", async () => {
    window.localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(["agent", "alerts", "壞掉的", "kpi"]));
    resetLayoutCache();
    backend();
    view();
    await screen.findByTestId("kpi-cards");
    const ids = within(screen.getByTestId("monitor-sections"))
      .getAllByRole("region")
      .map((s) => s.getAttribute("data-section"));
    expect(ids).toEqual(["agent", "alerts", "kpi", "token", "distribution", "trends", "timeline", "logs", "compare"]);
  });

  it("「自訂儀表板」切換編輯模式：每個區塊出現拖曳把手與標題；「重設版面」回預設並清掉儲存", async () => {
    window.localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(["logs", "kpi"]));
    resetLayoutCache();
    backend();
    view();
    await screen.findByTestId("kpi-cards");
    expect(screen.queryByTestId("drag-kpi")).toBeNull();
    await userEvent.click(screen.getByTestId("layout-toggle"));
    expect(screen.getByTestId("layout-toggle")).toHaveTextContent("完成自訂");
    expect(screen.getByTestId("drag-kpi")).toHaveAttribute("aria-label", "拖曳排序：指標卡");
    expect(screen.getAllByRole("button", { name: /^拖曳排序：/ })).toHaveLength(9);

    await userEvent.click(screen.getByTestId("layout-reset"));
    const ids = within(screen.getByTestId("monitor-sections"))
      .getAllByRole("region")
      .map((s) => s.getAttribute("data-section"));
    expect(ids[0]).toBe("kpi");
    expect(ids[1]).toBe("token");
    expect(window.localStorage.getItem(LAYOUT_STORAGE_KEY)).toBeNull();
    await userEvent.click(screen.getByTestId("layout-toggle"));
    expect(screen.queryByTestId("drag-kpi")).toBeNull();
  });
});

describe("監控頁：輪詢節奏（契約 §0.4 第 4 點、§1.3）", () => {
  it("輪詢間隔＝max(監控參數 refreshIntervalMs，15 秒)：設定 10 秒時仍用 15 秒；設定 60 秒時用 60 秒；讀不到用 30 秒", async () => {
    const { useMonitorPollMs, MONITOR_POLL_FLOOR_MS, MONITOR_DEFAULT_POLL_MS } = await import("@/lib/api/queries");
    const { renderHook } = await import("@testing-library/react");
    const run = async (reply: Reply) => {
      stubApi((c) => (c.path === "/api/v1/settings/monitor" ? reply : undefined));
      const { result, unmount } = renderHook(() => useMonitorPollMs(), { wrapper: ({ children }) => <Providers client={makeClient()}>{children}</Providers> });
      await waitFor(() => expect(result.current).not.toBe(undefined));
      await new Promise((r) => setTimeout(r, 30));
      const value = result.current;
      unmount();
      return value;
    };
    expect(MONITOR_POLL_FLOOR_MS).toBe(15_000);
    expect(await run({ data: [FIXTURE.refreshIntervalMs("10000")] })).toBe(15_000);
    expect(await run({ data: [FIXTURE.refreshIntervalMs("60000")] })).toBe(60_000);
    expect(await run(failure(404, { message: "查無" }) as Reply)).toBe(MONITOR_DEFAULT_POLL_MS);
  });
});
