import { readFile } from "node:fs/promises";

import { expect, test, type Page } from "@playwright/test";

import { Engine, PROJECT_ID, TASKS } from "./execFixture";
import { SHOTS } from "./helpers";
import { CSV_BODY, CSV_FILENAME, MonitorWorld } from "./monitorFixture";
import { collectConsoleErrors, compose, installApiMock, signInAs, snap, type MockHandler } from "./mockApi";

/**
 * 專案監控頁（設計稿畫面 8；契約 §1.3、§4.3；PRD US-M-01～10）——route mock 版：
 * 假引擎（execFixture）提供三個批次（Run #1 完成、Run #2 失敗、Run #3 進行中）與步驟事件，
 * 假監控後端（monitorFixture）提供指標、趨勢、告警、日誌查詢與報表。
 * 這裡驗「前端對契約形狀的行為」：帶什麼參數去查、數字怎麼呈現、樂觀更新、下載、拖曳排版；真後端的欄位漂移由 QA 波另驗。
 */
const MONITOR_URL = `/projects/${PROJECT_ID}/monitor`;
const DAY = 86_400_000;

type OpenOptions = { role?: "ADMIN" | "OPERATOR" | "VIEWER"; before?: MockHandler };

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
  const world = new MonitorWorld(engine);
  await signInAs(page, opts.role ?? "OPERATOR");
  const unhandled: string[] = [];
  const tail: MockHandler = (call) => {
    unhandled.push(`${call.method} ${call.path}`);
    return undefined;
  };
  const { calls } = await installApiMock(page, compose(...(opts.before ? [opts.before] : []), world.handler, engine.handler, tail));
  const errors = collectConsoleErrors(page);
  await page.goto(MONITOR_URL);
  await expect(page.getByRole("heading", { name: "專案監控：AISDLC Core Platform" })).toBeVisible({ timeout: 60_000 });
  const runId = (n: number) => engine.runs.find((r) => r.runNumber === n)?.id as string;
  return { engine, world, calls, errors, unhandled, runId };
}

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
    const primary = await page.locator('[data-testid="token-trend-card"] span.bg-wg-primary').first().evaluate((el) => getComputedStyle(el).backgroundColor);
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
    const keywords = world.seen.filter((s) => s.path.endsWith("/logs")).slice(before).map((s) => s.query.get("q"));
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

  test("匯出報表：CSV 下載（檔名取自 Content-Disposition、帶 Accept: text/csv、範圍＝目前選擇）；PDF 回 501 顯示「尚未提供」", async ({ page }) => {
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

    await page.getByTestId("export-pdf").click();
    await expect(page.getByText("PDF 報表尚未提供（預計 W5 提供），請先匯出 CSV")).toBeVisible();
    expect(lastOf(world, "/report")!.query.get("format")).toBe("pdf");
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
    expect(calls.filter((c) => c.path.includes("/metrics") && c.query.has("runId")), "比較批次不另外查 metrics").toHaveLength(0);

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
    await expect(page.getByTestId("agent-note")).toContainText("Bridge 實例：e2e-bridge。");
    await expect(page.getByTestId("agent-note")).toContainText("資源使用情況（CPU／記憶體）：Engine Bridge 目前沒有提供這項資料");
    expectClean(errors, unhandled);
  });

  test("自訂儀表板：拖曳重排區塊，順序存 localStorage、重新整理後保留、可重設", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 3600 }); // 九個區塊都在視窗內，拖曳不必捲動
    const { errors, unhandled } = await open(page);
    const DEFAULT = ["kpi", "token", "distribution", "trends", "timeline", "logs", "alerts", "compare", "agent"];
    expect(await sectionOrder(page)).toEqual(DEFAULT);
    await expect(page.getByTestId("drag-kpi")).toHaveCount(0); // 沒進入編輯模式沒有把手
    await page.getByTestId("layout-toggle").click();
    await expect(page.getByTestId("layout-toggle")).toHaveText("完成自訂");
    await expect(page.locator('[data-testid^="drag-"]')).toHaveCount(9);
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
    const MOVED = ["kpi", "token", "distribution", "trends", "timeline", "logs", "alerts", "agent", "compare"];
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
