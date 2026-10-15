import { readFile } from "node:fs/promises";
import path from "node:path";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import {
  E2E_ROOT,
  NEEDS_BRIDGE,
  bootstrapSettings,
  call,
  createFixture,
  dataOf,
  ensureQuota,
  getRun,
  poll,
  signIn,
  waitRun,
  type Fixture,
  type Json,
} from "./realBackend";

/**
 * Phase 5 專案監控（畫面 8）——對真後端＋真 Bridge＋mock claude（契約 §1.3、§3.8、§5 E2E-03 步驟 9～13、15、E2E-05、E2E-08）。
 * 三個夾具專案由 REST 預先跑完（等級 4，輪詢用 viewer）：
 *   M1＝PRJ-A 全完成（3720 Token）；M2＝T2 帶 [FAIL_ME]：Run #1 FAILED（升級告警）→ SKIP → Run #2 COMPLETED；
 *   M3＝PRJ-B 小預算：預算告警兩筆 → 暫停 → resume 跑完（6200 Token）。
 * 驗「UI 顯示＝後端回的數字」（對照 API，不寫死到小數）＋契約 §5 的固定數字（M1、M3）。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const MOCK_CLAUDE = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");
const nm = (base: string) => `${base} ${RUN}`;
const kpi = (page: Page, key: string) => page.getByTestId(`kpi-${key}-value`);
const fmt = (n: number, digits = 0) => n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

type Metric = { value: number | null; previousValue: number | null; delta: number | null };
type Metrics = Record<string, Metric> & { tokenBudget?: number; taskStatusDistribution: Record<string, number>; taskDurations: unknown[]; retryDistribution: Array<{ retries: number; tasks: number }> };

let m1: Fixture;
let m2: Fixture;
let m3: Fixture;
let m1Run = "";
let m2Runs: string[] = [];
let m3Run = "";

async function execute(request: APIRequestContext, f: Fixture, body: Json): Promise<string> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, body);
  expect(r.status, `execute ${f.name} → ${JSON.stringify(r.json)}`).toBe(201);
  return dataOf<{ id: string }>(r).id;
}

test.describe.configure({ mode: "serial" });

test.describe("專案監控（真後端＋真 Bridge＋mock claude）", () => {
  test.setTimeout(300_000);

  test.beforeAll(async ({ request }) => {
    test.setTimeout(600_000);
    await bootstrapSettings(request, MOCK_CLAUDE);
    expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);
    await ensureQuota(request, "operator", 60);
    // M1：全完成
    m1 = await createFixture(request, { name: nm("QA 監控 M1"), kind: "A", level: 4 });
    m1Run = await execute(request, m1, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
    await waitRun(request, m1Run, ["COMPLETED"]);
    // M2：T2 失敗 → SKIP → 後續批次完成
    m2 = await createFixture(request, { name: nm("QA 監控 M2"), kind: "A", level: 4, failTasks: [2] });
    const r1 = await execute(request, m2, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
    // 契約 §2.4：Bridge 直接寫 DB 的終態比 Console 消費事件建審核項早一步，所以等到審核項出現再取
    const failed = await poll(() => getRun(request, r1), (r) => r.status === "FAILED" && (r.pendingReviews ?? []).length > 0, `批次 ${r1} FAILED 且審核項已建立`, 90_000);
    const review = failed.pendingReviews![0].id;
    const skip = await call(request, "operator", "POST", `/api/v1/executions/${r1}/review/${review}`, { decision: "SKIP" });
    expect(skip.status).toBe(204);
    const follow = skip.headers["x-follow-up-run-id"];
    expect(follow, "SKIP 要回 X-Follow-Up-Run-Id").toBeTruthy();
    await waitRun(request, follow, ["COMPLETED"]);
    m2Runs = [r1, follow];
    // M3：小預算
    m3 = await createFixture(request, { name: nm("QA 監控 M3"), kind: "B", level: 4 });
    m3Run = await execute(request, m3, { autonomyLevel: 4, tokenBudget: 1500, scope: { mode: "ALL" } });
    await waitRun(request, m3Run, ["PAUSED"], 90_000);
    expect((await call(request, "operator", "POST", `/api/v1/executions/${m3Run}/resume`)).status).toBe(200);
    await waitRun(request, m3Run, ["COMPLETED"], 90_000);
  });

  test.beforeEach(async ({ request }) => {
    await ensureQuota(request, "operator", 45);
  });

  async function open(page: Page, request: APIRequestContext, f: Fixture, role: "operator" | "viewer" = "operator") {
    await signIn(page, request, role);
    await page.goto(`/projects/${f.projectId}/monitor`);
    await expect(page.getByRole("heading", { name: `專案監控：${f.name}` })).toBeVisible(FIRST_LOAD);
  }

  test("M1 指標卡與圖表：UI 數字＝API 回的值；契約 E2E-03 步驟 9 的固定數字", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    await open(page, request, m1);
    const api = dataOf<Metrics>(await call(request, "viewer", "GET", `/api/v1/monitor/projects/${m1.projectId}/metrics?runId=${m1Run}`));
    // 契約固定數字（E2E-03 步驟 9）
    expect(api.totalTokens.value).toBe(3720);
    expect(api.taskCompletionRate.value).toBe(100);
    expect(api.taskSuccessRate.value).toBe(100);
    expect(api.retryRate.value).toBe(0);
    expect(api.averageRetryCount.value).toBe(0);
    expect(api.tokenBudgetUsageRate.value).toBe(3.7);
    expect(api.agentAvailability.value).toBe(100);
    expect(api.taskStatusDistribution.COMPLETED).toBe(3);
    expect(api.taskDurations).toHaveLength(3);
    // 頁面預設是「全部批次、最近 24 小時」：對 M1 只有一個批次，數字相同
    await expect(kpi(page, "totalTokens")).toHaveText(fmt(3720));
    await expect(kpi(page, "taskCompletionRate")).toHaveText("100.0%");
    await expect(kpi(page, "taskSuccessRate")).toHaveText("100.0%");
    await expect(kpi(page, "retryRate")).toHaveText("0.0%");
    await expect(kpi(page, "averageRetryCount")).toHaveText("0.00");
    await expect(kpi(page, "tokenBudgetUsageRate")).toHaveText("3.7%");
    await expect(kpi(page, "agentAvailability")).toHaveText("100.0%");
    // 圖表
    const chart = page.getByTestId("token-trend-chart");
    await expect(chart).toBeVisible();
    await expect(chart).toHaveAttribute("aria-label", /Token 使用趨勢圖：\d+ 個時間點，最新累計 3,720 Token，預算 100,000/);
    await expect(page.getByTestId("status-bar-done")).toContainText("完成 (3)");
    await expect(page.getByTestId("duration-chart-col")).toHaveCount(3);
    await expect(page.getByTestId("task-trend-chart").locator("svg")).toBeVisible();
    await expect(page.getByTestId("retry-chart-col")).toHaveCount(6);
    await page.setViewportSize({ width: 1440, height: 3400 });
    await snap(page, "p5-monitor-full.png");
    await page.setViewportSize({ width: 1440, height: 900 });
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("M2 批次比較／日誌／事件時間軸／Agent：Run #1 失敗、Run #2 完成；選批次改查該批次", async ({ page, request }) => {
    await open(page, request, m2);
    const table = page.getByTestId("compare-table");
    await expect(table).toContainText("Run #1");
    await expect(table).toContainText("Run #2");
    const cell = (row: string, col: "a" | "b") => page.getByTestId(`compare-row-${row}`).locator(`td[data-col="${col}"]`);
    // 預設最新兩批：A＝Run #2（完成）、B＝Run #1（失敗）——以實際欄位為準，不假設左右
    const statuses = [await cell("status", "a").innerText(), await cell("status", "b").innerText()];
    expect(statuses.sort()).toEqual(["失敗", "已完成"]);
    // 選 Run #1：KPI 只算該批次（T1 完成＋T2 失敗：成功率 50.0%）
    await page.getByTestId("run-select").selectOption(m2Runs[0]);
    const api1 = dataOf<Metrics>(await call(request, "viewer", "GET", `/api/v1/monitor/projects/${m2.projectId}/metrics?runId=${m2Runs[0]}`));
    expect(api1.taskSuccessRate.value).toBe(50);
    await expect(kpi(page, "taskSuccessRate")).toHaveText("50.0%");
    await expect(kpi(page, "totalTokens")).toHaveText(fmt(api1.totalTokens.value ?? 0));
    await expect(page.getByTestId("agent-run-status")).toHaveText("Run #1 · 已失敗".replace("已失敗", "失敗"));
    // 事件時間軸：Run #1 有 T1 開始／完成、T2 開始／重試／失敗
    await expect(page.getByTestId("timeline-run")).toHaveText("Run #1");
    expect(await page.getByTestId("timeline-item").count()).toBeGreaterThanOrEqual(5);
    // 日誌：ERROR 篩選只剩失敗那一行；由新到舊
    await page.getByTestId("log-level").selectOption("ERROR");
    await expect(page.getByTestId("log-row").first()).toHaveAttribute("data-level", "ERROR");
    const total = Number((await page.getByTestId("log-total").innerText()).replace(/\D/g, ""));
    expect(total).toBeGreaterThanOrEqual(1);
    await page.getByTestId("log-level").selectOption("ALL");
    await page.getByTestId("log-keyword").fill("設定");
    await expect(page.getByTestId("log-row").first()).toContainText("設定");
    await snap(page, "p5-monitor-m2-run1.png", { tall: true });
  });

  test("告警：升級告警未確認 → 確認（樂觀更新後以伺服器為準）；viewer 看得到但不能確認；去重（M3 兩筆預算告警）", async ({ page, request }) => {
    await open(page, request, m2);
    const rows = page.getByTestId("alert-row");
    await expect(rows).toHaveCount(1);
    await expect(rows.first()).toHaveAttribute("data-ack", "false");
    await expect(rows.first()).toContainText("ESCALATION");
    await expect(page.getByTestId("alerts-open-count")).toHaveText("1");
    await rows.first().getByTestId("alert-detail-toggle").click();
    await expect(rows.first().getByTestId("alert-detail")).toContainText("step:G1-T2");
    await snap(page, "p5-monitor-alerts.png", { focus: page.getByTestId("alerts-card") });
    await rows.first().getByTestId("alert-ack").click();
    await expect(rows.first()).toHaveAttribute("data-ack", "true");
    const list = dataOf<Array<{ acknowledged: boolean; acknowledgedBy?: string; rule: string }>>(
      await call(request, "viewer", "GET", `/api/v1/monitor/projects/${m2.projectId}/alerts`),
    );
    await poll(
      async () => dataOf<Array<{ acknowledged: boolean }>>(await call(request, "viewer", "GET", `/api/v1/monitor/projects/${m2.projectId}/alerts`)),
      (a) => a.every((x) => x.acknowledged),
      "告警已確認",
      15_000,
    );
    expect(list[0].rule).toBe("ENGINE_ESCALATION");
    // 冪等：再確認一次仍 204，acknowledgedBy 不變
    const id = (await call(request, "viewer", "GET", `/api/v1/monitor/projects/${m2.projectId}/alerts`)).json.data as Array<{ id: string; acknowledgedBy: string }>;
    expect((await call(request, "operator", "POST", `/api/v1/monitor/alerts/${id[0].id}/acknowledge`)).status).toBe(204);
    expect(id[0].acknowledgedBy).toBe("operator");

    // M3：預算告警兩筆（WARNING、CRITICAL），resume 後沒有重複
    await open(page, request, m3, "viewer");
    await expect(page.getByTestId("alert-row")).toHaveCount(2);
    await expect(page.getByTestId("alerts-open-count")).toHaveText("2");
    const ack = page.getByTestId("alert-ack").first();
    await expect(ack).toBeDisabled();
    await expect(ack).toHaveAttribute("title", "權限不足（唯讀角色不可確認）");
    const api = dataOf<Metrics>(await call(request, "viewer", "GET", `/api/v1/monitor/projects/${m3.projectId}/metrics?runId=${m3Run}`));
    expect(api.totalTokens.value).toBe(6200);
    expect(api.tokenBudgetUsageRate.value).toBe(413.3);
    await expect(kpi(page, "tokenBudgetUsageRate")).toHaveText("413.3%");
  });

  test("匯出報表：CSV 下載（檔名取自 Content-Disposition＝CORS 暴露）、BOM、四段內容；PDF 回 501 顯示「尚未提供」", async ({ page, request }) => {
    await open(page, request, m1);
    await page.getByTestId("run-select").selectOption(m1Run);
    await expect(kpi(page, "totalTokens")).toHaveText(fmt(3720));
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("export-csv").click()]);
    expect(download.suggestedFilename()).toMatch(/^monitor-report-[0-9a-f]{8}-\d{8}-\d{4}\.csv$/);
    expect(download.suggestedFilename().slice("monitor-report-".length, "monitor-report-".length + 8)).toBe(m1.projectId.slice(0, 8));
    const text = await readFile((await download.path()) as string, "utf8");
    expect(text.charCodeAt(0)).toBe(0xfeff);
    expect(text).toContain("#report,");
    for (const s of ["summary", "runs", "tasks", "alerts"]) expect(text).toContain(`#section,${s}`);
    expect(text).toContain("totalTokens,3720,");
    const lines = text.split("\r\n");
    const section = (name: string) => {
      const i = lines.indexOf(`#section,${name}`);
      const rest = lines.slice(i + 2);
      const end = rest.findIndex((l) => l === "");
      return end < 0 ? rest : rest.slice(0, end);
    };
    expect(section("runs")).toHaveLength(1);
    expect(section("tasks")).toHaveLength(3);
    expect(section("alerts")).toHaveLength(0);
    await expect(page.getByText(/已匯出報表：monitor-report-/)).toBeVisible();
    await page.getByTestId("export-pdf").click();
    await expect(page.getByText("PDF 報表尚未提供（預計 W5 提供），請先匯出 CSV")).toBeVisible();
    await snap(page, "p5-monitor-export.png");
  });
});
