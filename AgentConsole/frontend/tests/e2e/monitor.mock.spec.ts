import { readFile } from "node:fs/promises";

import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { Engine, PROJECT_ID, TASKS } from "./execFixture";
import { SHOTS } from "./helpers";
import { CSV_BODY, CSV_FILENAME, MonitorWorld, PDF_BODY, PDF_FILENAME, type SddFile } from "./monitorFixture";
import { collectConsoleErrors, compose, installApiMock, signInAs, snap, type MockHandler } from "./mockApi";

/**
 * 專案監控頁（設計稿畫面 8；契約 §1.3、§4.3；PRD US-M-01～10）——route mock 版：
 * 假引擎（execFixture）提供三個批次（Run #1 完成、Run #2 失敗、Run #3 進行中）與步驟事件，
 * 假監控後端（monitorFixture）提供指標、趨勢、告警、日誌查詢與報表。
 * 這裡驗「前端對契約形狀的行為」：帶什麼參數去查、數字怎麼呈現、樂觀更新、下載、拖曳排版；真後端的欄位漂移由 QA 波另驗。
 */
const MONITOR_URL = `/projects/${PROJECT_ID}/monitor`;
const DAY = 86_400_000;

type OpenOptions = {
  role?: "ADMIN" | "OPERATOR" | "VIEWER";
  before?: MockHandler;
  /** 開頁前再調整假引擎（例如設定資源取樣） */
  setup?: (engine: Engine) => void;
  /** 開頁（goto）之前的最後一步：可改假監控世界（SDD 引擎狀態）、或安裝假時鐘（page.clock.install 必須在 goto 之前） */
  beforeGoto?: (page: Page, ctx: { world: MonitorWorld; engine: Engine }) => Promise<void> | void;
};

/** Run #1 完成（3 步）、Run #2 失敗（T2 完成、T3 升級）、Run #3 進行中（T1 完成、T2 進行中）。 */
function seed(e: Engine): void {
  e.begin(4);
  for (let i = 0; i < 3; i++) {
    e.startNext();
    e.finishCurrent();
  }
  e.begin(4, { scope: [1, 2] });
  e.startNext();
  e.finishCurrent();
  e.startNext();
  e.failCurrent(e.latest, "測試未通過");
  e.begin(4);
  e.startNext();
  e.finishCurrent();
  e.startNext();
}

async function open(page: Page, opts: OpenOptions = {}) {
  const engine = new Engine();
  seed(engine);
  opts.setup?.(engine);
  const world = new MonitorWorld(engine);
  await signInAs(page, opts.role ?? "OPERATOR");
  const unhandled: string[] = [];
  const tail: MockHandler = (call) => {
    unhandled.push(`${call.method} ${call.path}`);
    return undefined;
  };
  const { calls } = await installApiMock(page, compose(...(opts.before ? [opts.before] : []), world.handler, engine.handler, tail));
  const errors = collectConsoleErrors(page);
  await opts.beforeGoto?.(page, { world, engine });
  await page.goto(MONITOR_URL);
  await expect(page.getByRole("heading", { name: "專案監控：AISDLC Core Platform" })).toBeVisible({ timeout: 60_000 });
  const runId = (n: number) => engine.runs.find((r) => r.runNumber === n)?.id as string;
  return { engine, world, calls, errors, unhandled, runId };
}

/** 本機時區的「2026-10-16 09:02:03」：與卡片的時間格式相同，但由測試自己組（不引用被測程式）。 */
const pad = (n: number) => String(n).padStart(2, "0");
const localTime = (iso: string) => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};
/** 假後端依序收到的 GET /engines/sdd 的 project 參數（null＝沒帶）。 */
const sddRequests = (world: MonitorWorld) => world.seen.filter((s) => s.path === "/api/v1/engines/sdd").map((s) => s.query.get("project"));

const kpi = (page: Page, key: string) => page.getByTestId(`kpi-${key}-value`);
const span = (q: URLSearchParams) => Date.parse(q.get("to") as string) - Date.parse(q.get("from") as string);
const lastOf = (world: MonitorWorld, suffix: string) => world.seen.filter((s) => s.method === "GET" && s.path.endsWith(suffix)).at(-1);
const sectionOrder = (page: Page) => page.locator('[data-testid^="section-"]').evaluateAll((els) => els.map((e) => e.getAttribute("data-section")));

function expectClean(errors: string[], unhandled: string[]) {
  expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  expect(unhandled, "mock 沒處理的請求").toEqual([]);
}

test.describe("專案監控頁（route mock）", () => {
  test.setTimeout(120_000);

  test("指標卡：四張主卡與六項 KPI 小列顯示契約數值、delta 與顏色語意；null 不編造", async ({ page }) => {
    const { errors, unhandled } = await open(page);
    // 設計稿四張卡（完成率／任務成功率／重試率／Token 消耗）：數值＋delta（delta＝value−previousValue，百分比為百分點）
    await expect(kpi(page, "taskCompletionRate")).toHaveText("80.0%");
    await expect(page.getByTestId("kpi-taskCompletionRate-delta")).toHaveText("↑ 20.0%");
    await expect(page.getByTestId("kpi-taskCompletionRate-delta")).toHaveClass(/text-wg-primary/); // 完成率升＝好
    await expect(kpi(page, "taskSuccessRate")).toHaveText("85.7%");
    await expect(page.getByTestId("kpi-taskSuccessRate-delta")).toHaveText("↓ 4.3%");
    await expect(page.getByTestId("kpi-taskSuccessRate-delta")).toHaveClass(/text-wg-error/); // 成功率降＝壞
    await expect(kpi(page, "retryRate")).toHaveText("14.3%");
    await expect(page.getByTestId("kpi-retryRate-delta")).toHaveText("↑ 4.3%");
    await expect(page.getByTestId("kpi-retryRate-delta")).toHaveClass(/text-wg-accent/); // 重試率升＝壞（消耗類用強調色）
    await expect(kpi(page, "totalTokens")).toHaveText("8,680");
    await expect(page.getByTestId("kpi-totalTokens-delta")).toHaveText("↑ 3,720");
    // PRD §5.4.2 另外六項
    await expect(kpi(page, "projectCompletionRate")).toHaveText("66.7%");
    await expect(kpi(page, "goalAchievementRate")).toHaveText("50.0%");
    await expect(page.getByTestId("kpi-goalAchievementRate")).toContainText("→ 0.0%"); // delta 為 0：平
    await expect(kpi(page, "averageRetryCount")).toHaveText("0.40");
    await expect(kpi(page, "tokenBudgetUsageRate")).toHaveText("8.7%");
    await expect(page.getByTestId("kpi-tokenBudgetUsageRate")).not.toContainText(/[↑↓→]/); // 沒有比較值（delta 為 null）就不顯示這一行
    await expect(kpi(page, "averageTaskDurationSec")).toHaveText("2m 06s");
    await expect(kpi(page, "agentAvailability")).toHaveText("99.1%");
    expectClean(errors, unhandled);
  });

  test("圖表：Token 趨勢折線為主色、預算為虛線；狀態分佈、執行時間、任務趨勢、成功失敗比率、重試分佈都畫出來", async ({ page }) => {
    const { errors, unhandled } = await open(page);
    const chart = page.getByTestId("token-trend-chart");
    await expect(chart).toBeVisible();
    await expect(chart).toHaveAttribute("aria-label", /Token 使用趨勢圖：6 個時間點，最新累計 8,680 Token，預算 100,000/);
    // 折線顏色來自設計 token（圖例的主色小線段與折線同色），預算線是虛線
    const area = chart.locator(".recharts-area-curve");
    await expect(area).toHaveCount(1);
    const primary = await page
      .locator('[data-testid="token-trend-card"] span.bg-wg-primary')
      .first()
      .evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(await area.evaluate((el) => getComputedStyle(el).stroke)).toBe(primary);
    const budget = chart.locator(".recharts-line-curve");
    await expect(budget).toHaveCount(1);
    expect(await budget.evaluate((el) => getComputedStyle(el).strokeDasharray)).not.toBe("none");

    // 任務狀態分佈：完成／執行中（RUNNING＋VALIDATING＋QUEUED）／失敗（FAILED＋ESCALATED）／待處理（其餘）
    await expect(page.getByTestId("status-bar-done")).toContainText("完成 (4)");
    await expect(page.getByTestId("status-bar-running")).toContainText("執行中 (2)");
    await expect(page.getByTestId("status-bar-failed")).toContainText("失敗 (1)");
    await expect(page.getByTestId("status-bar-pending")).toContainText("待處理 (2)");
    // 執行時間分佈：由長到短，最高的用主色（data-highlight）
    const durations = page.getByTestId("duration-chart-col");
    await expect(durations).toHaveCount(3);
    await expect(durations.first()).toContainText("實作");
    await expect(durations.first()).toContainText("3m 30s");
    await expect(durations.first().locator("[data-highlight]")).toHaveAttribute("data-highlight", "true");
    await expect(durations.nth(1).locator("[data-highlight]")).toHaveAttribute("data-highlight", "false");
    // 設計稿沒畫、PRD §5.4.2 要的趨勢圖
    await expect(page.getByTestId("task-trend-chart").locator("svg")).toBeVisible();
    await expect(page.getByTestId("task-trend-chart")).toHaveAttribute("aria-label", /任務執行趨勢圖：/);
    await expect(page.getByTestId("ratio-col").first()).toBeVisible();
    await expect(page.getByTestId("retry-chart-col")).toHaveCount(6); // 重試次數桶 0～5 一律出現
    await expect(page.getByTestId("retry-chart")).toContainText("≥5 次");

    // 無障礙（DEF-AC-004／005）：圖例的 list 結構、卡片文字對比等
    await expectNoA11yViolations(page, "監控頁（指標＋圖表）");
    await page.setViewportSize({ width: 1440, height: 3400 }); // 整頁一次拍完
    await snap(page, "08-monitor-full.png");
    await page.setViewportSize({ width: 1440, height: 900 });
    expectClean(errors, unhandled);
  });

  test("時間範圍與批次選擇：帶 from／to／bucket／runId 重新查詢，數字、時間軸、Agent 狀態跟著換", async ({ page }) => {
    const { world, errors, unhandled, runId } = await open(page);
    // 預設最近 24 小時、全部批次
    const first = lastOf(world, "/metrics");
    expect(span(first!.query)).toBe(DAY);
    expect(first!.query.get("runId")).toBeNull();
    expect(lastOf(world, "/token-trend")!.query.get("bucket")).toBe("HOUR");
    await expect(page.getByTestId("timeline-run")).toHaveText("Run #3"); // 事件時間軸與 Agent 狀態：選「全部批次」取最新一筆

    await page.getByTestId("range-select").selectOption("1h");
    await expect(kpi(page, "totalTokens")).toHaveText("1,240");
    expect(span(lastOf(world, "/metrics")!.query)).toBe(3_600_000);
    await expect.poll(() => span(lastOf(world, "/task-trend")!.query)).toBe(3_600_000);
    await expect.poll(() => lastOf(world, "/token-trend")!.query.get("bucket")).toBe("HOUR");

    await page.getByTestId("range-select").selectOption("7d");
    await expect(kpi(page, "totalTokens")).toHaveText("15,000");
    expect(span(lastOf(world, "/metrics")!.query)).toBe(7 * DAY);
    await expect.poll(() => lastOf(world, "/token-trend")!.query.get("bucket")).toBe("DAY"); // 視窗超過 48 小時用 DAY
    await expect.poll(() => lastOf(world, "/task-trend")!.query.get("bucket")).toBe("DAY");
    await expect.poll(() => span(lastOf(world, "/logs")!.query)).toBe(7 * DAY); // 日誌查詢也跟著範圍
    await page.getByTestId("range-select").selectOption("24h");

    // 選批次：所有查詢都帶 runId；時間軸與 Agent 卡改看該批次
    await page.getByTestId("run-select").selectOption(runId(1));
    await expect(kpi(page, "totalTokens")).toHaveText("3,720");
    expect(lastOf(world, "/metrics")!.query.get("runId")).toBe(runId(1));
    expect(lastOf(world, "/alerts")!.query.get("runId")).toBe(runId(1));
    await expect(page.getByTestId("timeline-run")).toHaveText("Run #1");
    await expect(page.getByTestId("timeline-item")).toHaveCount(6); // 3 個任務各「開始、完成」
    await expect(page.getByTestId("agent-run-status")).toHaveText("Run #1 · 已完成");
    await expect(page.getByTestId("agent-light")).toContainText("已連線，閒置");
    await expect(page.getByTestId("alerts-empty")).toBeVisible(); // Run #1 沒有告警

    // 回到全部批次：查詢快取還新鮮就直接用，不必再打一次請求（所以不斷言「又送了一個沒有 runId 的請求」）
    await page.getByTestId("run-select").selectOption("");
    await expect(kpi(page, "totalTokens")).toHaveText("8,680");
    await expect(page.getByTestId("timeline-run")).toHaveText("Run #3");
    await expect(page.getByTestId("agent-run-status")).toHaveText("Run #3 · 執行中");
    expectClean(errors, unhandled);
  });

  test("日誌查詢：等級、關鍵字（去抖）、任務 id 篩選與分頁；由新到舊", async ({ page }) => {
    const { world, errors, unhandled } = await open(page);
    const rows = page.getByTestId("log-row");
    await expect(page.getByTestId("log-total")).toHaveText("共 45 筆");
    await expect(page.getByTestId("log-page")).toHaveText("1 / 3");
    await expect(rows).toHaveCount(20);
    await expect(rows.first()).toContainText("#0"); // 最新的在最上面
    await expect(page.getByTestId("log-prev")).toBeDisabled();

    await page.getByTestId("log-next").click();
    await expect(page.getByTestId("log-page")).toHaveText("2 / 3");
    expect(lastOf(world, "/logs")!.query.get("page")).toBe("1");
    await expect(rows.first()).toContainText("#20");
    await page.getByTestId("log-next").click();
    await expect(page.getByTestId("log-page")).toHaveText("3 / 3");
    await expect(rows).toHaveCount(5);
    await expect(page.getByTestId("log-next")).toBeDisabled();

    // 等級：篩選條件一變回到第一頁
    await page.getByTestId("log-level").selectOption("ERROR");
    await expect(page.getByTestId("log-total")).toHaveText("共 5 筆");
    await expect(page.getByTestId("log-page")).toHaveText("1 / 1");
    for (const level of await rows.evaluateAll((els) => els.map((e) => e.getAttribute("data-level")))) expect(level).toBe("ERROR");
    expect(lastOf(world, "/logs")!.query.get("level")).toBe("ERROR");
    await snap(page, "08-monitor-logs-error.png", { focus: page.getByTestId("log-query-card") });
    await page.getByTestId("log-level").selectOption("ALL");
    await expect(page.getByTestId("log-total")).toHaveText("共 45 筆");

    // 關鍵字：去抖 400ms——連續輸入只送最後一個
    const before = world.seen.filter((s) => s.path.endsWith("/logs")).length;
    await page.getByTestId("log-keyword").pressSequentially("重試", { delay: 80 });
    await expect(page.getByTestId("log-total")).toHaveText("共 10 筆");
    const keywords = world.seen
      .filter((s) => s.path.endsWith("/logs"))
      .slice(before)
      .map((s) => s.query.get("q"));
    expect(keywords, "去抖：沒有為輸入到一半的「重」送請求").not.toContain("重");
    expect(keywords).toContain("重試");
    await page.getByTestId("log-keyword").fill("");

    // 任務 id
    await page.getByTestId("log-task").fill(TASKS[0].id);
    await expect(page.getByTestId("log-total")).toHaveText("共 23 筆");
    expect(lastOf(world, "/logs")!.query.get("taskId")).toBe(TASKS[0].id);
    await page.getByTestId("log-keyword").fill("不存在的關鍵字");
    await expect(page.getByTestId("log-empty")).toHaveText("沒有符合條件的日誌");
    expectClean(errors, unhandled);
  });

  test("告警：未確認計數與詳情；確認走樂觀更新（先變已確認，再等伺服器）；失敗時還原並提示", async ({ page }) => {
    const { world, calls, errors, unhandled } = await open(page);
    const rows = page.getByTestId("alert-row");
    await expect(rows).toHaveCount(3);
    await expect(page.getByTestId("alerts-open-count")).toHaveText("2");
    // 由新到舊
    await expect(rows.first()).toContainText("[Token 預算警告] Token 使用量已達預算的 80%");
    await expect(rows.first()).toHaveAttribute("data-severity", "WARNING");
    await expect(rows.first()).toHaveAttribute("data-ack", "false");
    await expect(rows.nth(2)).toHaveAttribute("data-ack", "true");
    await expect(rows.nth(2).getByTestId("alert-acked")).toBeVisible();
    await rows.first().getByTestId("alert-detail-toggle").click();
    const detail = rows.first().getByTestId("alert-detail");
    await expect(detail).toContainText("Token 預算警告（警告）");
    await expect(detail).toContainText("run:");
    await rows.first().getByTestId("alert-detail-toggle").click();
    await expectNoA11yViolations(page, "監控頁（告警）");
    await snap(page, "08-monitor-alerts.png", { focus: page.getByTestId("alerts-card") });

    // 失敗：先樂觀、再還原並 toast
    world.ackFails = true;
    world.ackDelayMs = 900;
    await rows.first().getByTestId("alert-ack").click();
    await expect(rows.first()).toHaveAttribute("data-ack", "true"); // 樂觀：伺服器還沒回應
    await expect(page.getByTestId("alerts-open-count")).toHaveText("1");
    await expect(page.getByText(/確認告警失敗/)).toBeVisible();
    await expect(rows.first()).toHaveAttribute("data-ack", "false"); // 還原
    await expect(page.getByTestId("alerts-open-count")).toHaveText("2");
    expect(world.alerts[0].acknowledged).toBe(false);

    // 成功：樂觀後以伺服器為準
    world.ackFails = false;
    await rows.first().getByTestId("alert-ack").click();
    await expect(rows.first()).toHaveAttribute("data-ack", "true");
    await expect(page.getByText("已確認告警")).toBeVisible();
    await expect.poll(() => world.alerts[0].acknowledged).toBe(true);
    await expect(rows.first()).toHaveAttribute("data-ack", "true"); // 重抓之後仍是已確認
    await expect(page.getByTestId("alerts-open-count")).toHaveText("1");
    const acks = calls.filter((c) => c.method === "POST" && c.path.endsWith("/acknowledge"));
    expect(acks.map((c) => c.path)).toEqual([`/api/v1/monitor/alerts/${world.alerts[0].id}/acknowledge`, `/api/v1/monitor/alerts/${world.alerts[0].id}/acknowledge`]);
    expectClean(errors, unhandled);
  });

  test("唯讀角色（VIEWER）：看得到告警，但不能確認", async ({ page }) => {
    const { errors, unhandled } = await open(page, { role: "VIEWER" });
    await expect(page.getByTestId("alert-row")).toHaveCount(3);
    const ack = page.getByTestId("alert-ack").first();
    await expect(ack).toBeDisabled();
    await expect(ack).toHaveAttribute("title", "權限不足（唯讀角色不可確認）");
    expectClean(errors, unhandled);
  });

  test("匯出報表：CSV 與 PDF 下載（檔名取自 Content-Disposition、CSV 帶 Accept: text/csv、PDF 帶 application/pdf、範圍＝目前選擇）", async ({ page }) => {
    const { world, errors, unhandled, runId } = await open(page);
    await page.getByTestId("run-select").selectOption(runId(2));
    await expect(kpi(page, "totalTokens")).toHaveText("1,240");

    const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("export-csv").click()]);
    expect(download.suggestedFilename()).toBe(CSV_FILENAME);
    expect(await readFile((await download.path()) as string, "utf8")).toBe(CSV_BODY);
    await expect(page.getByText(`已匯出報表：${CSV_FILENAME}`)).toBeVisible();
    const req = lastOf(world, "/report");
    expect(req!.query.get("format")).toBe("csv");
    expect(req!.query.get("runId")).toBe(runId(2)); // 匯出範圍＝目前的批次選擇
    expect(span(req!.query)).toBe(DAY); // 與目前的時間範圍
    expect(req!.headers.accept).toContain("text/csv");

    // PDF（v1.2，C-4）：同樣回 200，檔名取自 Content-Disposition（.pdf）、位元組原樣存檔、範圍與 CSV 相同
    const [pdf] = await Promise.all([page.waitForEvent("download"), page.getByTestId("export-pdf").click()]);
    expect(pdf.suggestedFilename()).toBe(PDF_FILENAME);
    expect(await readFile((await pdf.path()) as string, "utf8")).toBe(PDF_BODY);
    await expect(page.getByText(`已匯出報表：${PDF_FILENAME}`)).toBeVisible();
    const pdfReq = lastOf(world, "/report");
    expect(pdfReq!.query.get("format")).toBe("pdf");
    expect(pdfReq!.query.get("runId")).toBe(runId(2));
    expect(span(pdfReq!.query)).toBe(DAY);
    expect(pdfReq!.headers.accept).toContain("application/pdf");
    await expect(page.getByText(/尚未提供/)).toHaveCount(0); // 501 與「尚未提供」提示已退役
    await expect(page.getByTestId("alert-settings-link")).toHaveAttribute("href", "/settings");
    expectClean(errors, unhandled);
  });

  test("批次比較、事件時間軸、Agent 即時狀態：列表欄位直接比較（零額外請求）、步驟事件成軸、連線燈", async ({ page }) => {
    const { calls, errors, unhandled } = await open(page);
    // 批次比較：預設最新兩批（A＝Run #2 失敗、B＝Run #3 進行中）
    const table = page.getByTestId("compare-table");
    await expect(table).toContainText("Run #2");
    await expect(table).toContainText("Run #3");
    const cell = (row: string, col: "a" | "b") => page.getByTestId(`compare-row-${row}`).locator(`td[data-col="${col}"]`);
    await expect(cell("status", "a")).toHaveText("失敗");
    await expect(cell("status", "b")).toHaveText("執行中");
    await expect(cell("level", "a")).toHaveText("Level 4");
    await expect(cell("tokens", "a")).toHaveText("1,240");
    await expect(cell("budget", "a")).toHaveText("1.2%"); // 1,240 / 100,000
    await expect(cell("tasks", "a")).toHaveText("1 / 2");
    await expect(cell("tasks", "b")).toHaveText("1 / 3");
    await expect(cell("failed", "a")).toHaveText("1");
    await expect(cell("failed", "b")).toHaveText("0");
    await expect(cell("success", "a")).toHaveText("50.0%");
    await expect(cell("success", "b")).toHaveText("100.0%");
    await page.getByTestId("compare-a").selectOption({ label: "Run #1 · 已完成" });
    await expect(cell("status", "a")).toHaveText("已完成");
    await expect(cell("tokens", "a")).toHaveText("3,720");
    await expect(cell("tasks", "a")).toHaveText("3 / 3");
    await expect(cell("success", "a")).toHaveText("100.0%");
    expect(
      calls.filter((c) => c.path.includes("/metrics") && c.query.has("runId")),
      "比較批次不另外查 metrics",
    ).toHaveLength(0);

    // 事件時間軸：最新批次（Run #3）的步驟事件——T1 開始、T1 完成、T2 開始
    const items = page.getByTestId("timeline-item");
    await expect(items).toHaveCount(3);
    await expect(items.nth(0)).toContainText("G1-T1 開始");
    await expect(items.nth(0)).toHaveAttribute("data-tone", "start");
    await expect(items.nth(1)).toContainText("G1-T1 完成");
    await expect(items.nth(1)).toHaveAttribute("data-tone", "done");
    await expect(items.nth(2)).toContainText("G1-T2 開始");

    // Agent 即時狀態
    await expect(page.getByTestId("agent-light")).toContainText("已連線，執行中");
    await expect(page.getByTestId("agent-light")).toHaveAttribute("data-connected", "true");
    await expect(page.getByTestId("agent-run-status")).toHaveText("Run #3 · 執行中");
    await expect(page.getByTestId("agent-current")).toHaveText("設定（G1-T2）");
    await expect(page.getByTestId("agent-availability")).toHaveText("99.1%");
    await expect(page.getByTestId("agent-note")).toHaveText("Bridge 實例：e2e-bridge。");
    // v1.3（D-12）：說明句「Engine Bridge 目前沒有提供這項資料」已移除；這個假引擎沒有資源取樣（resources 鍵缺席）→ 資源格是單一「—」
    await expect(page.getByTestId("agent-resources")).toHaveText("—");
    await expect(page.getByTestId("agent-card")).not.toContainText("目前沒有提供這項資料");
    await expectNoA11yViolations(page, "監控頁（批次比較＋事件時間軸＋Agent 狀態）");
    expectClean(errors, unhandled);
  });

  test("Agent 即時狀態的資源使用（契約 §4.3 M-19，D-12；E2E-14 第 8～9 列的前端那一半）：有取樣＝`CPU x.x%・記憶體 N MB・M 行程`；已結束的批次與沒有取樣＝單一「—」", async ({ page }) => {
    const { errors, unhandled, runId } = await open(page, {
      setup: (e) => {
        e.resources = { cpuPercent: 12.3, memoryBytes: 361_758_720, processCount: 3 };
      },
    });
    // Run #3 進行中、引擎行程樹有取樣
    await expect(page.getByTestId("agent-run-status")).toHaveText("Run #3 · 執行中");
    await expect(page.getByTestId("agent-resources")).toHaveText("CPU 12.3%・記憶體 345 MB・3 行程");
    await expect(page.getByTestId("agent-resources")).toHaveAttribute("title", /^取樣時間 \d{2}:\d{2}:\d{2}$/);
    await expect(page.getByTestId("agent-resources").locator("xpath=preceding-sibling::div[1]")).toHaveText("資源使用");
    await expect(page.getByTestId("agent-note")).toHaveText("Bridge 實例：e2e-bridge。"); // 只留實例資訊
    await expect(page.getByTestId("agent-card")).not.toContainText("目前沒有提供這項資料");
    await expectNoA11yViolations(page, "監控頁（Agent 即時狀態：有資源使用）");

    // 既有四格的版面不動：同一列四欄，資源使用自成第二列整列
    const boxes = await Promise.all(["agent-light", "agent-run-status", "agent-current", "agent-availability", "agent-resources"].map((id) => page.getByTestId(id).boundingBox()));
    const [light, status, current, availability, resources] = boxes.map((b) => b!);
    expect(new Set([light, status, current, availability].map((b) => Math.round(b.y))).size, "前四格在同一列").toBe(1);
    expect(light.x).toBeLessThan(status.x);
    expect(status.x).toBeLessThan(current.x);
    expect(current.x).toBeLessThan(availability.x);
    expect(resources.y, "資源使用在第二列").toBeGreaterThan(light.y + light.height);

    // 切到已結束的批次（Run #1 完成）：行程樹已不存在，顯示單一「—」，沒有 tooltip
    await page.getByTestId("run-select").selectOption(runId(1));
    await expect(page.getByTestId("agent-run-status")).toHaveText("Run #1 · 已完成");
    await expect(page.getByTestId("agent-resources")).toHaveText("—");
    await expect(page.getByTestId("agent-resources")).not.toHaveAttribute("title");
    await page.getByTestId("run-select").selectOption(runId(2));
    await expect(page.getByTestId("agent-run-status")).toHaveText("Run #2 · 失敗");
    await expect(page.getByTestId("agent-resources")).toHaveText("—");

    // 回到進行中的批次：數字又回來
    await page.getByTestId("run-select").selectOption(runId(3));
    await expect(page.getByTestId("agent-resources")).toHaveText("CPU 12.3%・記憶體 345 MB・3 行程");
    expectClean(errors, unhandled);
  });

  test("資源使用：引擎行程樹沒有取樣（resources 為 null：還沒有第一筆樣本或樣本過期）→ 單一「—」，不顯示舊數字也不編造", async ({ page }) => {
    const { errors, unhandled } = await open(page, {
      setup: (e) => {
        e.resources = null;
      },
    });
    await expect(page.getByTestId("agent-run-status")).toHaveText("Run #3 · 執行中");
    await expect(page.getByTestId("agent-resources")).toHaveText("—");
    await expect(page.getByTestId("agent-card")).not.toContainText("CPU");
    expectClean(errors, unhandled);
  });

  test("AISDLC_SDD 引擎卡（契約 §4.3 M-20；E2E-15 第 5 列的前端那一半）：兩段請求；選 e2e-alpha 的狀態、Sprint、更新時間、待人工與最近決策 5 筆與「檔案」逐值一致；改選 e2e-bravo 顯示等待人工確認；選擇被記住", async ({
    page,
  }) => {
    const { world, errors, unhandled } = await open(page);
    const card = page.getByTestId("sdd-card");
    await expect(card.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION");
    // 兩段請求：先不帶 project 取清單，選定第一個專案後再帶 project 取它的 FSM
    expect(sddRequests(world)).toEqual([null, "e2e-alpha"]);
    await expect(card.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    await expect(card.getByTestId("sdd-version")).toHaveText("AISDLC_SDD_v9.99"); // 只秀 latest；version.root 是 Bridge 端路徑，不顯示
    await expect(card).not.toContainText("/sdd/AISDLC_SDD_v9.99");
    await expect(card.getByTestId("sdd-project-select")).toHaveValue("e2e-alpha");
    await expect(card.getByTestId("sdd-project-select").locator("option")).toHaveText(["e2e-alpha", "e2e-bravo"]);

    // 檔案 ↔ 畫面：卡片的每個值都與假「FSM 檔」的原值一致
    const alpha = world.sdd.files["e2e-alpha"] as SddFile;
    await expect(card.getByTestId("sdd-sprint")).toHaveText(`Sprint ${alpha.current_sprint}`);
    await expect(card.getByTestId("sdd-updated")).toHaveText(localTime(alpha.updated_at as string));
    await expect(card.getByTestId("sdd-human-pending")).toHaveText("無");
    const newestFirst = (alpha.decision_trace ?? []).slice(-5).reverse(); // 檔內 7 筆的最後 5 筆，倒序（新→舊）
    const decisions = card.getByTestId("sdd-decision");
    await expect(decisions).toHaveCount(5);
    for (const [i, d] of newestFirst.entries()) {
      await expect(decisions.nth(i).getByTestId("sdd-decision-transition")).toHaveText(`${d.from} → ${d.to}`);
      await expect(decisions.nth(i).getByTestId("sdd-decision-reason")).toHaveText(String(d.reason));
    }
    await expect(card).not.toContainText("SCG_VALIDATION"); // retryHistory、frozenStages、rtmCoverage 不顯示
    await expectNoA11yViolations(page, "監控頁（AISDLC_SDD 引擎卡：e2e-alpha）");

    // 改選 e2e-bravo：待人工 1 筆（可展開看進入時間）、沒有決策紀錄
    await card.getByTestId("sdd-project-select").selectOption("e2e-bravo");
    await expect(card.getByTestId("sdd-state")).toHaveText("HUMAN_PENDING");
    expect(sddRequests(world)).toEqual([null, "e2e-alpha", "e2e-bravo"]);
    await expect(card.getByTestId("sdd-sprint")).toHaveText("Sprint 1");
    await expect(card.getByTestId("sdd-human-pending")).toHaveText("等待人工確認");
    await card.getByTestId("sdd-human-pending").click();
    const bravo = world.sdd.files["e2e-bravo"] as SddFile;
    await expect(card.getByTestId("sdd-human-pending-items")).toContainText(`進入時間：${localTime(bravo.human_pending_tracking?.entered_at as string)}`);
    await expect(card.getByTestId("sdd-decision")).toHaveCount(0);
    await expect(card.getByTestId("sdd-decisions-empty")).toBeVisible();
    await expectNoA11yViolations(page, "監控頁（AISDLC_SDD 引擎卡：e2e-bravo、待人工已展開）");

    // 記住選擇（localStorage，只是方便）：重新整理後預設就是 bravo
    expect(await page.evaluate(() => window.localStorage.getItem("console.monitor.sddProject"))).toBe("e2e-bravo");
    await page.reload();
    await expect(card.getByTestId("sdd-state")).toHaveText("HUMAN_PENDING");
    await expect(card.getByTestId("sdd-project-select")).toHaveValue("e2e-bravo");
    expect(sddRequests(world).slice(-2)).toEqual([null, "e2e-bravo"]);
    expectClean(errors, unhandled);
  });

  test("AISDLC_SDD 引擎卡不隨 Console 專案的批次下拉與時間範圍變動（SDD 引擎是全域的，契約 M-20）", async ({ page }) => {
    const { world, runId, errors, unhandled } = await open(page);
    const card = page.getByTestId("sdd-card");
    await expect(card.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION");
    const before = sddRequests(world);

    await page.getByTestId("range-select").selectOption("7d");
    await page.getByTestId("run-select").selectOption(runId(1));
    await expect.poll(() => lastOf(world, "/metrics")?.query.get("runId")).toBe(runId(1)); // 其他區塊確實跟著重查了
    expect(sddRequests(world)).toEqual(before); // SDD 卡沒有任何新請求
    await expect(card.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION");
    expectClean(errors, unhandled);
  });

  test("檔案變動後下一輪輪詢跟上（E2E-15 第 6 列的前端那一半）：快轉 30 秒，卡片換成新狀態與新決策、沒有整頁重載；讀到寫一半的檔顯示「FSM 狀態檔無法讀取」，下一輪恢復", async ({ page }) => {
    const { world, errors, unhandled } = await open(page, { beforeGoto: (p) => p.clock.install() });
    const card = page.getByTestId("sdd-card");
    await expect(card.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION");
    await page.evaluate(() => ((window as unknown as { __kept?: number }).__kept = 1)); // 整頁重載會清掉它
    expect(sddRequests(world)).toEqual([null, "e2e-alpha"]);

    // 改寫檔案：current_state 換值、updated_at 更新、decision_trace 加一筆
    const alpha = world.sdd.files["e2e-alpha"] as SddFile;
    alpha.current_state = "REVIEW";
    alpha.updated_at = "2026-10-16T02:30:00+00:00";
    alpha.decision_trace = [
      ...(alpha.decision_trace ?? []),
      { ts: new Date(2026, 9, 16, 9, 0, 0).toISOString(), from: "S7", to: "REVIEW", reason: "新的一筆決策", spec_refs: [], agents_consulted: [], trigger: "auto" },
    ];
    await page.clock.fastForward(31_000);
    await expect(card.getByTestId("sdd-state")).toHaveText("REVIEW");
    await expect(card.getByTestId("sdd-updated")).toHaveText(localTime("2026-10-16T02:30:00+00:00"));
    await expect(card.getByTestId("sdd-decision").first().getByTestId("sdd-decision-transition")).toHaveText("S7 → REVIEW");
    await expect(card.getByTestId("sdd-decision").first().getByTestId("sdd-decision-reason")).toHaveText("新的一筆決策");
    await expect(card.getByTestId("sdd-decision")).toHaveCount(5);
    expect(await page.evaluate(() => (window as unknown as { __kept?: number }).__kept)).toBe(1);
    expect(sddRequests(world).filter((p) => p === null)).toHaveLength(1); // 選定專案後只輪詢帶 project 的那一份

    // 恰好讀到寫一半的檔：卡片顯示無法讀取（不崩潰），下一輪恢復
    world.sdd.files["e2e-alpha"] = "broken";
    await page.clock.fastForward(31_000);
    await expect(card.getByTestId("sdd-message")).toHaveText("FSM 狀態檔無法讀取");
    await expect(card.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    world.sdd.files["e2e-alpha"] = alpha;
    await page.clock.fastForward(31_000);
    await expect(card.getByTestId("sdd-state")).toHaveText("REVIEW");
    await expect(card.getByTestId("sdd-message")).toHaveCount(0);
    expectClean(errors, unhandled);
  });

  test("引擎不可用與空清單（E2E-15 第 7～9 列的前端那一半）：Bridge 無法連線、SDD 目錄無效、回應異常各有文案；沒有 FSM 狀態檔顯示「尚無 FSM 狀態檔」；復原後下一輪輪詢回來", async ({ page }) => {
    const { world, errors, unhandled } = await open(page, {
      beforeGoto: async (p, ctx) => {
        ctx.world.sdd.mode = "bridge_unreachable";
        await p.clock.install();
      },
    });
    const card = page.getByTestId("sdd-card");
    const message = card.getByTestId("sdd-message");
    // 第 7 列：Bridge 不可達——回 200、卡片顯示不可用與原因，沒有下拉
    await expect(message).toHaveText("Engine Bridge 無法連線");
    await expect(card.getByTestId("sdd-status")).toHaveAttribute("data-available", "false");
    await expect(card.getByTestId("sdd-status")).toContainText("不可用");
    await expect(card.getByTestId("sdd-project-select")).toHaveCount(0);
    await expect(card.getByTestId("sdd-state")).toHaveCount(0);
    await expectNoA11yViolations(page, "監控頁（AISDLC_SDD 引擎卡：Bridge 無法連線）");

    // 第 8 列：SDD 目錄無效
    world.sdd.mode = "sdd_unavailable";
    await page.clock.fastForward(31_000);
    await expect(message).toHaveText("找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）");
    world.sdd.mode = "bridge_error";
    await page.clock.fastForward(31_000);
    await expect(message).toHaveText("Engine Bridge 回應異常");

    // 第 9 列：目錄有效但還沒有任何 FSM 狀態檔——不是錯誤
    const files = world.sdd.files;
    world.sdd.mode = "ok";
    world.sdd.files = {};
    await page.clock.fastForward(31_000);
    await expect(card.getByTestId("sdd-empty")).toHaveText("尚無 FSM 狀態檔（SDD runtime 執行後才會產生）");
    await expect(card.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    await expect(card.getByTestId("sdd-version")).toHaveText("AISDLC_SDD_v9.99");
    await expect(card.getByTestId("sdd-project-select")).toHaveCount(0);

    // 復原：檔案出現，下一輪輪詢自動選定第一個專案並顯示
    world.sdd.files = files;
    await page.clock.fastForward(31_000);
    await expect(card.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION");
    await expect(card.getByTestId("sdd-empty")).toHaveCount(0);
    expectClean(errors, unhandled);
  });

  test("自訂儀表板：拖曳重排區塊，順序存 localStorage、重新整理後保留、可重設", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 3600 }); // 被拖的 agent 與 compare 在視窗內（第十個區塊 sdd 在最下面，拖曳不必捲動）
    const { errors, unhandled } = await open(page);
    const DEFAULT = ["kpi", "token", "distribution", "trends", "timeline", "logs", "alerts", "compare", "agent", "sdd"];
    expect(await sectionOrder(page)).toEqual(DEFAULT);
    await expect(page.getByTestId("drag-kpi")).toHaveCount(0); // 沒進入編輯模式沒有把手
    await page.getByTestId("layout-toggle").click();
    await expect(page.getByTestId("layout-toggle")).toHaveText("完成自訂");
    await expect(page.locator('[data-testid^="drag-"]')).toHaveCount(10);
    await page.screenshot({ path: `${SHOTS}/08-monitor-customize.png`, clip: { x: 0, y: 0, width: 1440, height: 1400 } });

    // 把「Agent 即時狀態」拖到「批次比較」之前
    const agent = (await page.getByTestId("section-agent").boundingBox())!;
    const compare = (await page.getByTestId("section-compare").boundingBox())!;
    const handle = (await page.getByTestId("drag-agent").boundingBox())!;
    const x = handle.x + handle.width / 2;
    const y = handle.y + handle.height / 2;
    const dy = compare.y + compare.height / 2 - (agent.y + agent.height / 2);
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x, y + dy / 2, { steps: 8 });
    await page.mouse.move(x, y + dy, { steps: 8 });
    await page.mouse.up();
    const MOVED = ["kpi", "token", "distribution", "trends", "timeline", "logs", "alerts", "agent", "compare", "sdd"];
    await expect.poll(() => sectionOrder(page)).toEqual(MOVED);
    expect(await page.evaluate(() => window.localStorage.getItem("console.monitor.layout"))).toBe(JSON.stringify(MOVED));

    // 重新整理後保留
    await page.reload();
    await expect(page.getByRole("heading", { name: "專案監控：AISDLC Core Platform" })).toBeVisible({ timeout: 60_000 });
    await expect.poll(() => sectionOrder(page)).toEqual(MOVED);

    // 重設版面
    await page.getByTestId("layout-toggle").click();
    await page.getByTestId("layout-reset").click();
    await expect.poll(() => sectionOrder(page)).toEqual(DEFAULT);
    expect(await page.evaluate(() => window.localStorage.getItem("console.monitor.layout"))).toBeNull();
    await page.getByTestId("layout-toggle").click();
    await expect(page.getByTestId("layout-toggle")).toHaveText("自訂儀表板");
    expectClean(errors, unhandled);
  });
});
