import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import { E2E_ROOT, NEEDS_BRIDGE, bootstrapSettings, call, createFixture, dataOf, ensureQuota, poll, signIn, type Fixture } from "./realBackend";
import { MOCK_CLAUDE, createLongFixture } from "./w7";

/**
 * W7 複驗：契約 v1.3 E2E-14 第 8～9 列（D-12、US-M-10）——引擎行程樹的資源取樣，從 Bridge 經 console-api 到 Agent 即時狀態卡。
 *  列 8：長批次執行中，viewer 輪詢 GET /executions/{runId}，`bridge.resources` 四欄位型別與範圍、`sampledAt` 含 offset 且距現在 ≤ 15 秒、兩次輪詢前進、回應沒有 pid；
 *        同時用瀏覽器看卡片「資源使用」顯示 `CPU x.x%・記憶體 N MB・M 行程`，且 title 的取樣時間隨輪詢前進。
 *  列 9：沒有資料時——終態、PAUSED、Bridge 停掉——API 為 null 或缺席、卡片顯示 `—`，畫面沒有「目前沒有提供這項資料」。
 * 長批次：契約要求「5 個任務、MOCK_CLAUDE_DELAY 調到 ≥ 3 秒」；backend 以 --console.execution.mock-env[MOCK_CLAUDE_DELAY] 啟動時設 E2E_MOCK_DELAY（秒）
 * 讓本檔走契約形態（PRJ-B 五個任務）；沒設（預設 0.6 秒）時改用 40 個任務的單一目標把批次撐到約 1 分鐘（偏離契約的第二種形態，報告有寫）。
 * 「Bridge 停掉」需要兩支腳本（E2E_STOP_BRIDGE、E2E_START_BRIDGE，powershell -File）：它會真的結束共用的 Bridge 再重啟，沒設就略過那一支。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const execFileAsync = promisify(execFile);
const FIRST_LOAD = { timeout: 60_000 };
const MOCK_DELAY = Number(process.env.E2E_MOCK_DELAY ?? "0.6");
const SLOW = MOCK_DELAY >= 3;
const STOP_BRIDGE = process.env.E2E_STOP_BRIDGE ?? "";
const START_BRIDGE = process.env.E2E_START_BRIDGE ?? "";
const nm = (base: string) => `${base} ${RUN}`;
const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED"];
const SHAPE = /^CPU \d+\.\d%・記憶體 (<1 MB|\d+ MB|\d+\.\d GB)・\d+ 行程$/;

type Resources = { cpuPercent: number; memoryBytes: number; processCount: number; sampledAt: string };
type Detail = { id: string; projectId: string; status: string; bridge?: { connected: boolean; instance?: string; status?: string; runKnown?: boolean; resources?: Resources | null } };

const detail = async (request: APIRequestContext, runId: string): Promise<Detail> => dataOf<Detail>(await call(request, "viewer", "GET", `/api/v1/executions/${runId}`));
const pad = (n: number) => String(n).padStart(2, "0");
const clock = (iso: string) => {
  const d = new Date(iso);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};
const formatMemory = (bytes: number): string => {
  const mb = bytes / 1_048_576;
  if (mb < 1) return "<1 MB";
  if (mb >= 1024) return `${(bytes / 1_073_741_824).toFixed(1)} GB`;
  return `${Math.round(mb)} MB`;
};
/** 契約 §4.3 M-19 的顯示格式（測試端獨立實作一份，不 import 前端程式）。 */
const expectedText = (r: Resources) => `CPU ${r.cpuPercent.toFixed(1)}%・記憶體 ${formatMemory(r.memoryBytes)}・${r.processCount} 行程`;

const longFixture = (request: APIRequestContext, name: string): Promise<Fixture> => (SLOW ? createFixture(request, { name, kind: "B", level: 4 }) : createLongFixture(request, name, 40));

async function startRun(request: APIRequestContext, f: Fixture, level = 4): Promise<string> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: level, tokenBudget: 100000, scope: { mode: "ALL" } });
  expect(r.status, `execute ${f.name} → ${JSON.stringify(r.json).slice(0, 300)}`).toBe(201);
  return dataOf<{ id: string }>(r).id;
}

async function openMonitor(page: Page, request: APIRequestContext, f: Fixture): Promise<void> {
  await signIn(page, request, "operator");
  await page.goto(`/projects/${f.projectId}/monitor`);
  await expect(page.getByRole("heading", { name: `專案監控：${f.name}` })).toBeVisible(FIRST_LOAD);
  await expect(page.getByTestId("agent-card")).toBeVisible(FIRST_LOAD);
}

async function cancelAndWait(request: APIRequestContext, runId: string): Promise<void> {
  await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`);
  await poll(
    () => detail(request, runId),
    (d) => TERMINAL.includes(d.status),
    `批次 ${runId} 取消後進入終態`,
    60_000,
    1500,
  );
}

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200); // 執行類情境要求 apiKey 為空
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 60);
  await ensureQuota(request, "viewer", 70);
});

test.describe("E2E-14 列 8～9：資源使用（D-12；US-M-10）", () => {
  test.setTimeout(420_000);

  test(`列 8｜執行中：bridge.resources 欄位型別與範圍、sampledAt 前進、沒有 pid；卡片「資源使用」格式＝契約 M-19（${SLOW ? `契約形態：5 任務、MOCK_CLAUDE_DELAY＝${MOCK_DELAY} 秒` : "預設延遲 0.6 秒、40 任務長批次"}）`, async ({
    page,
    request,
  }) => {
    const errors = collectConsoleErrors(page);
    const f = await longFixture(request, nm("QA E2E-14 列8"));
    const runId = await startRun(request, f);
    const t0 = Date.now();
    // viewer 每 ≥2 秒輪詢，最長 20 秒直到 bridge.resources 出現
    const first = await poll(
      () => detail(request, runId),
      (d) => !!d.bridge?.resources,
      "bridge.resources 出現",
      20_000,
      2_000,
    );
    const r1 = first.bridge!.resources!;
    const firstAt = Date.now() - t0;
    expect(first.bridge).toMatchObject({ connected: true, instance: "e2e-bridge" });
    expect(Object.keys(r1).sort(), "四個欄位").toEqual(["cpuPercent", "memoryBytes", "processCount", "sampledAt"]);
    expect(r1.cpuPercent).toBeGreaterThanOrEqual(0);
    expect(r1.cpuPercent).toBeLessThanOrEqual(100);
    expect(Math.round(r1.cpuPercent * 10) / 10, "小數 1 位").toBe(r1.cpuPercent);
    expect(Number.isInteger(r1.memoryBytes) && r1.memoryBytes > 0, "memoryBytes 為正整數").toBe(true);
    expect(Number.isInteger(r1.processCount) && r1.processCount >= 1, "processCount ≥ 1（Windows 的 venv 啟動器會多一層殼，不斷言精確值）").toBe(true);
    expect(r1.sampledAt, "ISO-8601 含 offset").toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/);
    expect(Date.now() - Date.parse(r1.sampledAt), "距現在 ≤ 15 秒").toBeLessThanOrEqual(15_000);
    expect(JSON.stringify(first), "回應沒有 pid").not.toMatch(/"pid"|pid_create|lock_key/i);

    // 瀏覽器：Agent 即時狀態卡
    await openMonitor(page, request, f);
    const seen: Resources[] = [];
    page.on("response", async (res) => {
      if (res.url().includes(`/api/v1/executions/${runId}`) && !res.url().includes("/stream") && res.request().method() === "GET" && res.status() === 200) {
        const body = (await res.json().catch(() => null)) as { data?: Detail } | null;
        if (body?.data?.bridge?.resources) seen.push(body.data.bridge.resources);
      }
    });
    await page.reload();
    await expect(page.getByTestId("agent-card")).toBeVisible(FIRST_LOAD);
    const cell = page.getByTestId("agent-resources");
    await expect(cell, "資源使用顯示 CPU x.x%・記憶體 N MB・M 行程").toHaveText(SHAPE, FIRST_LOAD);
    await expect(cell.locator("xpath=preceding-sibling::div[1]")).toHaveText("資源使用");
    await expect(page.getByTestId("agent-card")).not.toContainText("目前沒有提供這項資料");
    await expect(page.getByTestId("agent-light")).toContainText("已連線，執行中");
    const text1 = (await cell.textContent()) ?? "";
    const title1 = (await cell.getAttribute("title")) ?? "";
    expect(title1, "tooltip 放取樣時間").toMatch(/^取樣時間 \d{2}:\d{2}:\d{2}$/);
    expect(seen.length, "頁面至少收到一份帶 resources 的詳情").toBeGreaterThanOrEqual(1);
    expect(
      seen.some((r) => expectedText(r) === text1 && `取樣時間 ${clock(r.sampledAt)}` === title1),
      `畫面（${text1}／${title1}）等於某一份網路回應的 resources 依 M-19 格式化（回應：${JSON.stringify(seen.slice(-3))}）`,
    ).toBe(true);
    await snap(page, "p9-w7-agent-resources.png", { focus: page.getByTestId("agent-card") });

    // 再等 ≥6 秒輪詢一次：sampledAt 前進（取樣週期 5 秒）
    await new Promise((r) => setTimeout(r, 6_500));
    const second = await detail(request, runId);
    expect(TERMINAL.includes(second.status), `第二次輪詢時批次必須還在跑（${second.status}；長批次要夠長）`).toBe(false);
    const r2 = second.bridge!.resources!;
    expect(r2, "第二次輪詢仍有資源資料").toBeTruthy();
    expect(Date.parse(r2.sampledAt), "sampledAt 前進").toBeGreaterThan(Date.parse(r1.sampledAt));
    expect(JSON.stringify(second)).not.toMatch(/"pid"/i);

    // 卡片的取樣時間隨詳情輪詢（15 秒）前進
    await expect.poll(async () => (await cell.getAttribute("title")) ?? "", { timeout: 45_000, intervals: [1_000] }).not.toBe(title1);
    await expect(cell).toHaveText(SHAPE);
    console.log(
      `[w7-resources] 列 8：首筆樣本在起跑後 ${firstAt}ms 出現＝${JSON.stringify(r1)}；6.5 秒後第二筆＝${JSON.stringify(r2)}；畫面「${text1}」（${title1}）→ 之後 title 前進；批次形態＝${SLOW ? `5 任務／延遲 ${MOCK_DELAY}s` : "40 任務／預設延遲"}`,
    );
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
    await cancelAndWait(request, runId);
  });

  test("列 9｜沒有資料時：終態、PAUSED 的批次 resources 為 null 或缺席，卡片顯示單一「—」且沒有舊說明句", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    // ① 終態：A 夾具跑完（約 5 秒）
    const done = await createFixture(request, { name: nm("QA E2E-14 列9 終態"), kind: "A", level: 4 });
    const doneRun = await startRun(request, done);
    const fin = await poll(
      () => detail(request, doneRun),
      (d) => TERMINAL.includes(d.status),
      "夾具 A 批次進入終態",
      90_000,
      2_000,
    );
    expect(fin.status).toBe("COMPLETED");
    expect(fin.bridge?.resources ?? null, "終態：null 或缺席").toBeNull();
    await openMonitor(page, request, done);
    await expect(page.getByTestId("agent-run-status")).toHaveText("Run #1 · 已完成", FIRST_LOAD);
    await expect(page.getByTestId("agent-resources")).toHaveText("—");
    await expect(page.getByTestId("agent-card")).not.toContainText("目前沒有提供這項資料");
    await expect(page.getByTestId("agent-card")).not.toContainText("CPU");

    // ② PAUSED：等級 1 夾具在第一個步驟邊界暫停（Bridge 的 pause 會終止整棵引擎行程樹，沒有行程可取樣）
    const paused = await createFixture(request, { name: nm("QA E2E-14 列9 暫停"), kind: "A", level: 1 });
    const pausedRun = await startRun(request, paused, 1);
    const pd = await poll(
      () => detail(request, pausedRun),
      (d) => d.status === "PAUSED",
      "等級 1 批次暫停",
      90_000,
      2_000,
    );
    expect(pd.bridge?.resources ?? null, "PAUSED：null 或缺席").toBeNull();
    await openMonitor(page, request, paused);
    await expect(page.getByTestId("agent-run-status")).toContainText("已暫停", FIRST_LOAD);
    await expect(page.getByTestId("agent-resources")).toHaveText("—");
    await expect(page.getByTestId("agent-card")).not.toContainText("目前沒有提供這項資料");
    await cancelAndWait(request, pausedRun);
    console.log(`[w7-resources] 列 9：終態 resources＝${JSON.stringify(fin.bridge?.resources ?? null)}、卡片「—」；PAUSED resources＝${JSON.stringify(pd.bridge?.resources ?? null)}、卡片「—」`);
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("列 9｜Bridge 停掉後：bridge.connected＝false、resources 為 null；卡片連線燈變「Engine Bridge 未連線」、資源使用「—」（會真的結束共用的 Bridge 再重啟）", async ({ page, request }) => {
    test.skip(!STOP_BRIDGE || !START_BRIDGE, "需要 E2E_STOP_BRIDGE 與 E2E_START_BRIDGE：結束／重啟共用 Bridge 的 PowerShell 腳本（見 tests/e2e/README.md〈W7 複驗〉）");
    const errors = collectConsoleErrors(page);
    const f = await longFixture(request, nm("QA E2E-14 列9 斷線"));
    const runId = await startRun(request, f);
    const live = await poll(
      () => detail(request, runId),
      (d) => !!d.bridge?.resources,
      "批次執行中的 resources",
      20_000,
      2_000,
    );
    expect(live.bridge?.connected).toBe(true);
    try {
      await execFileAsync("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", STOP_BRIDGE], { timeout: 60_000 });
      const down = await poll(
        () => detail(request, runId),
        (d) => d.bridge?.connected === false,
        "Bridge 停掉後 bridge.connected＝false",
        30_000,
        2_000,
      );
      expect(down.bridge?.resources ?? null, "Bridge 不可達：resources 為 null 或缺席").toBeNull();
      expect(down.bridge?.status ?? null, "Bridge 不可達：status 為 null").toBeNull();
      await openMonitor(page, request, f);
      await expect(page.getByTestId("agent-light")).toContainText("Engine Bridge 未連線", FIRST_LOAD);
      await expect(page.getByTestId("agent-light")).toHaveAttribute("data-connected", "false");
      await expect(page.getByTestId("agent-resources")).toHaveText("—");
      await expect(page.getByTestId("agent-card")).not.toContainText("目前沒有提供這項資料");
      await snap(page, "p9-w7-agent-bridge-down.png", { focus: page.getByTestId("agent-card") });
      console.log(`[w7-resources] 列 9：Bridge 結束後 bridge＝${JSON.stringify(down.bridge)}；畫面連線燈「Engine Bridge 未連線」、資源使用「—」`);
    } finally {
      await execFileAsync("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", START_BRIDGE], { timeout: 120_000 });
    }
    // Bridge 回來後（孤兒回收會把這個被殺掉的批次收尾）：連線恢復
    const back = await poll(
      () => detail(request, runId),
      (d) => d.bridge?.connected === true,
      "Bridge 重啟後 bridge.connected＝true",
      60_000,
      2_000,
    );
    console.log(`[w7-resources] 列 9：Bridge 重啟後 status＝${back.status}、bridge＝${JSON.stringify(back.bridge)}`);
    void errors;
  });
});
