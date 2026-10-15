import { execFile } from "node:child_process";
import { createHmac } from "node:crypto";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { API_URL, RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import {
  E2E_ROOT,
  FakeLlm,
  NEEDS_BRIDGE,
  bootstrapSettings,
  brd,
  call,
  dataOf,
  ensureQuota,
  getRun,
  idPair,
  poll,
  readSse,
  signIn,
  tokenOf,
  waitRun,
  createFixture,
  type Fixture,
} from "./realBackend";

/**
 * Phase 4 專案執行（畫面 7）——對真後端（console-api＋PG）＋真 Engine Bridge＋aisdlc-mock-claude（契約 §5 E2E-03～08、12 的 UI 面）。
 * 與 *.mock.spec.ts 的分工：那邊 SSE 是 node:http 假伺服器；這裡是 Spring SseEmitter 經真 Bridge 事件串流，驗契約漂移與時序。
 * 前置：見 realBackend.ts 檔頭。每個情境用自己的夾具專案（名稱帶 RUN 後綴）；輪詢一律用 viewer（限流鍵是 JWT subject，UI 用 operator）。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const MOCK_CLAUDE = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");
/** 選配：停止並重新啟動 backend（等到 /actuator/health 才返回）的 PowerShell 腳本路徑；沒設就略過「重啟 backend」的情境。 */
const RESTART_BACKEND = process.env.E2E_RESTART_BACKEND ?? "";
const execFileAsync = promisify(execFile);

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  // 執行類情境要求 model.apiKey 為空（關閉引擎演化，契約 §5.0.2）
  const reset = await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
  expect(reset.status).toBe(200);
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator");
});

const execUrl = (f: Fixture) => `/projects/${f.projectId}/execute`;
const nm = (base: string) => `${base} ${RUN}`;
const tone = (page: Page, taskId: string) => page.getByTestId(`dag-task-${taskId}`);

async function openExec(page: Page, request: APIRequestContext, f: Fixture, role: "operator" | "viewer" = "operator") {
  await signIn(page, request, role);
  await page.goto(execUrl(f));
  await expect(page.getByRole("heading", { name: `專案執行：${f.name}` })).toBeVisible(FIRST_LOAD);
}

async function latestRun(request: APIRequestContext, projectId: string, runNumber?: number): Promise<{ id: string; runNumber: number; status: string }> {
  const r = await call(request, "viewer", "GET", `/api/v1/projects/${projectId}/executions?sort=runNumber,desc&size=10`);
  expect(r.status).toBe(200);
  const rows = dataOf<{ content: Array<{ id: string; runNumber: number; status: string }> }>(r).content;
  const hit = runNumber ? rows.find((x) => x.runNumber === runNumber) : rows[0];
  expect(hit, `找不到批次 ${runNumber ?? "最新"}`).toBeTruthy();
  return hit!;
}

/** 審核卡：點某個決定 → 確認對話框 → 送出。 */
async function decide(page: Page, decision: "approve" | "retry" | "skip" | "reject", comment?: string) {
  await page.getByTestId(`review-${decision}`).click();
  await expect(page.getByTestId("review-dialog")).toBeVisible();
  if (comment) await page.getByTestId("review-comment").fill(comment);
  await page.getByTestId("review-confirm").click();
  await expect(page.getByTestId("review-dialog")).toHaveCount(0);
}

test.describe("專案執行（真後端＋真 Bridge＋mock claude）", () => {
  test.setTimeout(240_000);

  test("Level 4 一路跑完：SSE 即時日誌與進度、Token 帳、DAG 全綠、終態收工（E2E-03）", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    const f = await createFixture(request, { name: nm("QA 執行 L4"), kind: "A", level: 4 });
    await openExec(page, request, f);
    await expect(page.getByTestId("control-start")).toBeEnabled();
    await expect(page.getByTestId("exec-level")).toHaveValue("4"); // 預設取專案的自治等級
    await snap(page, "p4-execute-idle.png", { tall: true });

    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open");

    // 跑完：3 / 3 任務、COMPLETED、串流收工（終態後伺服器關閉連線）
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成", { timeout: 60_000 });
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "ended", { timeout: 20_000 });
    await expect(page.getByTestId("progress-tokens")).toContainText("Token: 3,720 / 100,000");
    for (const id of f.taskIds) await expect(tone(page, id)).toHaveAttribute("data-tone", "done");
    // 日誌：三個任務各「開始、完成」（STEP 行），每行只出現一次（at-least-once 重播依 (seq,n) 去重）
    for (const name of ["初始化", "設定", "實作"]) {
      await expect(page.getByTestId("log-line").filter({ hasText: `開始：${name}` })).toHaveCount(1);
      await expect(page.getByTestId("log-line").filter({ hasText: `完成：${name}` })).toHaveCount(1);
    }
    await expect(page.getByTestId("log-line").filter({ hasText: "Token: 1240" }).or(page.getByTestId("log-line").filter({ hasText: "Token: 1,240" }))).toHaveCount(3);
    await snap(page, "p4-execute-completed.png", { tall: true });

    // 後端一致（契約 E2E-03 步驟 4～8、14）
    const run = await latestRun(request, f.projectId, 1);
    const detail = await getRun(request, run.id);
    expect(detail).toMatchObject({ status: "COMPLETED", bridgeStatus: "COMPLETED", completedSteps: 3, totalSteps: 3, totalTokensUsed: 3720, runNumber: 1 });
    expect(detail.pendingReviews ?? []).toEqual([]);
    expect(detail.bridge).toMatchObject({ connected: true, instance: "e2e-bridge" });
    const steps = dataOf<{ content: Array<{ stepId: string; status: string; tokensUsed?: number; stepNumber: number }> }>(
      await call(request, "viewer", "GET", `/api/v1/executions/${run.id}/steps?size=200`),
    ).content;
    expect(steps.map((s) => `${s.stepId}:${s.status}`)).toEqual(["G1-T1:STARTED", "G1-T1:COMPLETED", "G1-T2:STARTED", "G1-T2:COMPLETED", "G2-T1:STARTED", "G2-T1:COMPLETED"]);
    expect(steps.filter((s) => s.status === "COMPLETED").map((s) => s.tokensUsed)).toEqual([1240, 1240, 1240]);
    for (let i = 1; i < steps.length; i += 1) expect(steps[i].stepNumber).toBeGreaterThan(steps[i - 1].stepNumber);
    const cps = dataOf<Array<{ name: string; stepIdx: number }>>(await call(request, "viewer", "GET", `/api/v1/executions/${run.id}/checkpoints`));
    expect(cps.map((c) => c.name)).toEqual(["after-G1-T1", "after-G1-T2", "after-G2-T1"]);
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("Level 3：目標邊界 PAUSED → GOAL_COMPLETED 待審核（通過／重試／拒絕、無跳過）→ 通過 → 跑完（E2E-04 等級 3）", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 執行 L3"), kind: "A", level: 3 });
    await openExec(page, request, f);
    await page.getByTestId("exec-level").selectOption("3");
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");

    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    await expect(page.getByTestId("run-reason")).toContainText("在步驟邊界暫停");
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "GOAL_COMPLETED");
    await expect(page.getByTestId("review-kind")).toHaveText("目標完成審核");
    await expect(page.getByTestId("review-approve")).toBeEnabled();
    await expect(page.getByTestId("review-retry")).toBeEnabled();
    await expect(page.getByTestId("review-reject")).toBeEnabled();
    await expect(page.getByTestId("review-skip")).toBeDisabled();
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成");
    // 步驟邊界：PAUSED 之前沒有 G2-T1 的 STARTED（被中止的 spawn 不發 STARTED）
    await expect(page.getByTestId("log-line").filter({ hasText: "開始：實作" })).toHaveCount(0);
    await snap(page, "p4-execute-level3-review.png", { tall: true });
    const run = await latestRun(request, f.projectId, 1);
    const paused = await getRun(request, run.id);
    expect(paused).toMatchObject({ status: "PAUSED", bridgeStatus: "PAUSED", completedSteps: 2 });
    expect(paused.pendingReviews).toHaveLength(1);
    expect(paused.pendingReviews![0].allowedDecisions).toEqual(["APPROVE", "REJECT", "RETRY"]);
    const summary = dataOf<{ pendingReviews: number }>(await call(request, "viewer", "GET", "/api/v1/notifications/summary"));
    expect(summary.pendingReviews).toBeGreaterThanOrEqual(1);

    await decide(page, "approve", "ok");
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成", { timeout: 60_000 });
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED");
    await expect(page.getByTestId("log-line").filter({ hasText: "開始：實作" })).toHaveCount(1); // 通過後恰一次
    const done = await getRun(request, run.id);
    expect(done).toMatchObject({ status: "COMPLETED", totalTokensUsed: 3720 });
    const reviewed = await call(request, "viewer", "GET", `/api/v1/executions/${run.id}`);
    expect(dataOf<RunPending>(reviewed).pendingReviews).toEqual([]);
  });

  test("Level 1：第一步後 PAUSED＋TASK_CONFIRM 待審核 → 通過 → 第二次暫停 → 通過 → 跑完（E2E-04）", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 執行 L1"), kind: "A", level: 1 });
    await openExec(page, request, f);
    await page.getByTestId("exec-level").selectOption("1");
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");

    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    const row = page.getByTestId("review-row");
    await expect(row).toHaveCount(1);
    await expect(row).toHaveAttribute("data-kind", "TASK_CONFIRM");
    await expect(page.getByTestId("review-reason")).toContainText("Level 1：請確認是否繼續執行任務「設定」");
    await expect(page.getByTestId("review-retry")).toBeDisabled();
    await expect(page.getByTestId("review-skip")).toBeDisabled();
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");
    await expect(page.getByTestId("log-line").filter({ hasText: "開始：設定" })).toHaveCount(0);
    await snap(page, "p4-execute-level1-review.png", { tall: true });

    await decide(page, "approve");
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成", { timeout: 60_000 });
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    await expect(page.getByTestId("review-reason")).toContainText("任務「實作」");
    await expect(page.getByTestId("log-line").filter({ hasText: "開始：設定" })).toHaveCount(1); // 恰一次
    await decide(page, "approve");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 60_000 });
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成");
    const run = await latestRun(request, f.projectId, 1);
    expect(await getRun(request, run.id)).toMatchObject({ status: "COMPLETED", totalTokensUsed: 3720, completedSteps: 3 });
  });

  test("ESCALATED（[FAIL_ME]）：終態後待審核卡仍出現（RETRY／SKIP／REJECT，無通過）→ RETRY 再失敗 → SKIP 另開後續批次跑完（E2E-05；矩陣 I）", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 執行 ESC"), kind: "A", level: 4, failTasks: [2] });
    await openExec(page, request, f);
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");

    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "FAILED", { timeout: 90_000 });
    await expect(page.getByTestId("run-reason")).toContainText("引擎升級（ESCALATION）");
    // 終態 status-change 先到、衍生的 review-request 後到：前端以 REST 的 pendingReviews 為準，待審核卡必須出現
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "ESCALATED");
    await expect(page.getByTestId("review-kind")).toHaveText("需人工介入");
    await expect(page.getByTestId("review-approve")).toBeDisabled();
    for (const d of ["retry", "skip", "reject"]) await expect(page.getByTestId(`review-${d}`)).toBeEnabled();
    await expect(page.getByTestId("review-reason")).toContainText("重試 1 次仍失敗");
    await expect(tone(page, f.taskIds[1])).toHaveAttribute("data-tone", "failed");
    await expect(page.getByTestId("log-line").filter({ hasText: "失敗：設定" })).toHaveCount(1);
    // 日誌裡有嚴重等級的引擎告警行（Bridge 升級告警的 message 是失敗原因本身；「引擎升級（ESCALATION）」前綴只在狀態變化的 reason）
    await expect(page.locator('[data-testid="log-line"][data-kind="alert"]').filter({ hasText: "告警（嚴重）" }).filter({ hasText: "G1-T2" }).first()).toBeVisible();
    await expect(page.locator('[data-testid="log-line"][data-kind="status"]').last()).toContainText("狀態：失敗");
    await expect(page.locator('[data-testid="log-line"][data-kind="review"]')).toContainText("待審核"); // 終態後才建立的 review-request 也進日誌
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "ended", { timeout: 20_000 });
    await snap(page, "p4-execute-escalated.png", { tall: true });
    const run1 = await latestRun(request, f.projectId, 1);
    const failed = await getRun(request, run1.id);
    expect(failed).toMatchObject({ status: "FAILED", completedSteps: 1 });
    expect(failed.reason).toContain("引擎升級（ESCALATION）");
    expect(failed.pendingReviews![0].allowedDecisions).toEqual(["RETRY", "SKIP", "REJECT"]);
    const approve = await call(request, "operator", "POST", `/api/v1/executions/${run1.id}/review/${failed.pendingReviews![0].id}`, { decision: "APPROVE" });
    expect(approve.status).toBe(409);
    expect(approve.json.reason).toBe("此審核項不允許該決定");

    // RETRY：找得到還原點 after-G1-T1 → 同一個批次（Run #1）還原重跑，T2 的 prompt 沒變，所以再度失敗
    await decide(page, "retry", "再試一次");
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "FAILED", { timeout: 90_000 });
    await expect(page.getByTestId("review-row")).toHaveCount(1); // 第二個 ESCALATED 審核項
    const reviews = await call(request, "viewer", "GET", `/api/v1/executions/${run1.id}`);
    expect(dataOf<RunPending>(reviews).pendingReviews).toHaveLength(1);
    expect(dataOf<RunPending>(reviews).pendingReviews![0].id).not.toBe(failed.pendingReviews![0].id);

    // SKIP：另開後續批次（X-Follow-Up-Run-Id），畫面自動切到 Run #2，只剩 T3 要跑
    await decide(page, "skip");
    await expect(page.getByTestId("run-number")).toHaveText("Run #2", { timeout: 30_000 });
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 1 任務完成");
    await expect(page.getByTestId("run-select").locator("option")).toHaveCount(2);
    const run2 = await latestRun(request, f.projectId, 2);
    const r2 = await call(request, "viewer", "GET", `/api/v1/executions/${run2.id}`);
    expect(dataOf<RunPending & { totalTokensUsed: number }>(r2).totalTokensUsed).toBe(1240);
    const task2 = dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/tasks/${f.taskIds[1]}`));
    expect(task2.status).toBe("SKIPPED");
    const proj = dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`));
    expect(proj.status).toBe("COMPLETED");
  });

  test("restore：終態批次從 after-G1-T1 還原續跑（Token 累計跨 restore）；PAUSED 批次 restore（AR-01）並自動拒絕舊審核項（E2E-07）", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 執行 RST"), kind: "A", level: 4 });
    await openExec(page, request, f);
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });

    // 終態 restore：對話框列出 3 個斷點（新→舊），選最舊的 after-G1-T1
    await page.getByTestId("control-restore").click();
    await expect(page.getByTestId("checkpoint-dialog")).toBeVisible();
    const options = page.getByTestId("checkpoint-option");
    await expect(options).toHaveCount(3);
    await expect(options.first()).toContainText("after-G2-T1");
    await expect(options.nth(2)).toContainText("after-G1-T1");
    await snap(page, "p4-execute-checkpoints.png");
    await page.getByRole("radio", { name: "斷點 after-G1-T1" }).check();
    await page.getByTestId("checkpoint-confirm").click();
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
    const run = await latestRun(request, f.projectId, 1);
    // restore 後的終態：6200 ＝ 3720 ＋ 2 × 1240（Bridge 的累計跨 restore 持續）；T1 沒有重跑
    const after = await poll(() => getRun(request, run.id), (r) => r.status === "COMPLETED" && r.totalTokensUsed === 6200, "restore 後 COMPLETED 且 Token=6200", 60_000);
    expect(after.totalTokensUsed).toBe(6200);
    const cps = dataOf<unknown[]>(await call(request, "viewer", "GET", `/api/v1/executions/${run.id}/checkpoints`));
    expect(cps.length).toBeGreaterThan(3); // append-only
    const steps = dataOf<{ totalElements: number }>(await call(request, "viewer", "GET", `/api/v1/executions/${run.id}/steps?size=200`));
    expect(steps.totalElements).toBe(10);
    const t1 = dataOf<{ actualTokens: number }>(await call(request, "viewer", "GET", `/api/v1/tasks/${f.taskIds[0]}`));
    const t2 = dataOf<{ actualTokens: number }>(await call(request, "viewer", "GET", `/api/v1/tasks/${f.taskIds[1]}`));
    expect([t1.actualTokens, t2.actualTokens]).toEqual([1240, 2480]);

    // PAUSED 的 restore（等級 1）：先暫停在第一步之後，對話框選 after-G1-T1 → 舊審核項由系統拒絕、批次繼續
    await ensureQuota(request, "operator", 60); // 第一段已用掉大半額度：同一視窗再開頁會被限流（429）
    const g = await createFixture(request, { name: nm("QA 執行 RST1"), kind: "A", level: 1 });
    await openExec(page, request, g);
    await page.getByTestId("exec-level").selectOption("1");
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    const pausedRun = await latestRun(request, g.projectId, 1);
    // Bridge 直接寫 DB 的暫停狀態比 Console 消費事件建審核項早一步（契約 §2.4）：等審核項出現再取
    const before = await poll(() => getRun(request, pausedRun.id), (r) => r.status === "PAUSED" && (r.pendingReviews ?? []).length > 0, `批次 ${pausedRun.id} PAUSED 且審核項已建立`, 60_000);
    const oldReview = before.pendingReviews![0].id;
    await page.getByTestId("control-restore").click();
    await expect(page.getByTestId("checkpoint-option")).toHaveCount(1);
    await page.getByRole("radio", { name: "斷點 after-G1-T1" }).check();
    await page.getByTestId("checkpoint-confirm").click();
    await expect(page.getByTestId("checkpoint-dialog")).toHaveCount(0);
    // 還原後從 G1-T2 再跑：Level 1 在該步之後再暫停一次，產生新的審核項；舊審核項已被系統拒絕
    await poll(() => getRun(request, pausedRun.id), (r) => r.status === "PAUSED" && (r.pendingReviews ?? []).length === 1 && r.pendingReviews![0].id !== oldReview, "restore 後再次 PAUSED 且是新的審核項", 60_000);
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    const rows = await call(request, "viewer", "GET", `/api/v1/monitor/projects/${g.projectId}/logs?runId=${pausedRun.id}&size=200&order=asc`);
    const logText = JSON.stringify(rows.json);
    // 舊審核項由系統拒絕（日誌的 REVIEW 行「審核 REJECTED：system」；comment＝執行已還原 沒有 REST 出口，QA 報告以 SQL 佐證）
    expect(logText).toContain("審核 REJECTED：system");
    await decide(page, "approve");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
  });

  test("取消：PAUSED 時取消（確認對話框）→ 即時 CANCELLED、待決審核項自動拒絕、專案回 READY；可重新執行（E2E-06）", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 執行 CAN"), kind: "A", level: 1 });
    await openExec(page, request, f);
    await page.getByTestId("exec-level").selectOption("1");
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    await page.getByTestId("control-cancel").click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("確定取消這個執行批次？");
    await dialog.getByRole("button", { name: "確認取消" }).click();
    await expect(page.getByTestId("run-status")).toContainText("已取消", { timeout: 30_000 });
    await expect(page.getByTestId("review-empty")).toBeVisible();
    await snap(page, "p4-execute-cancelled.png", { tall: true });
    const run = await latestRun(request, f.projectId, 1);
    const view = await getRun(request, run.id);
    expect(view).toMatchObject({ status: "CANCELLED", completedSteps: 1 });
    expect(view.pendingReviews ?? []).toEqual([]);
    const proj = dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`));
    expect(proj.status).toBe("READY");
    // 再 cancel／pause／resume 都是 409 目前執行狀態不允許此操作
    for (const action of ["cancel", "pause", "resume"]) {
      const r = await call(request, "operator", "POST", `/api/v1/executions/${run.id}/${action}`);
      expect(r.status, action).toBe(409);
      expect(r.json.reason).toBe("目前執行狀態不允許此操作");
    }
    // 可重新執行：等級 4 跑完（Run #2）
    await page.getByTestId("exec-level").selectOption("4");
    await expect(page.getByTestId("control-start")).toBeEnabled();
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #2", { timeout: 30_000 });
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
  });

  test("Token 預算告警：小預算 → 超出後自動暫停、不建審核項；告警兩筆；恢復後跑完且不再被暫停（E2E-08）", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 執行 TOK"), kind: "B", level: 4 });
    await openExec(page, request, f);
    await page.getByTestId("exec-budget").fill("1,500");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    await expect(page.getByTestId("token-warning")).toContainText("Token 已超出預算");
    await expect(page.getByTestId("review-empty")).toBeVisible(); // 預算暫停不建審核項
    const completed = await page.getByTestId("progress-tasks").innerText();
    expect(Number(completed.split("/")[0].trim())).toBeGreaterThanOrEqual(2);
    expect(Number(completed.split("/")[0].trim())).toBeLessThanOrEqual(4);
    await snap(page, "p4-execute-token-paused.png", { tall: true });
    const run = await latestRun(request, f.projectId, 1);
    const alerts = dataOf<Array<{ rule: string; severity: string; acknowledged: boolean; message: string; subject: string }>>(
      await call(request, "viewer", "GET", `/api/v1/monitor/projects/${f.projectId}/alerts?runId=${run.id}`),
    );
    expect(alerts.map((a) => a.rule).sort()).toEqual(["TOKEN_BUDGET_EXCEEDED", "TOKEN_BUDGET_WARNING"]);
    expect(alerts.every((a) => !a.acknowledged)).toBe(true);
    expect(alerts.find((a) => a.rule === "TOKEN_BUDGET_WARNING")!.message).toContain("1240 / 1500");

    await page.getByTestId("control-resume").click();
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
    const done = await getRun(request, run.id);
    expect(done.totalTokensUsed).toBe(6200);
    const alerts2 = dataOf<unknown[]>(await call(request, "viewer", "GET", `/api/v1/monitor/projects/${f.projectId}/alerts?runId=${run.id}`));
    expect(alerts2).toHaveLength(2); // 去重：未確認前不重複產生
  });

  test("SSE 斷線重連（真 SseEmitter）：重啟 backend 切斷串流 → 前端顯示重連中 → 連回後帶 Last-Event-ID、已有事件不重複、後續事件照常到（矩陣 I）", async ({ page, request }) => {
    // Playwright 的離線模擬（context.setOffline）切不斷已建立的 EventSource（實測 30 秒後狀態仍是 open），所以真的把 backend 行程殺掉再起。
    test.skip(!RESTART_BACKEND, "需要 E2E_RESTART_BACKEND：停止並重新啟動 backend、等到 /actuator/health 的 PowerShell 腳本（見 tests/e2e/README.md）");
    const f = await createFixture(request, { name: nm("QA 執行 SSE"), kind: "A", level: 1 });
    await openExec(page, request, f);
    await page.getByTestId("exec-level").selectOption("1");
    await page.getByTestId("exec-budget").fill("100,000");
    const streamReqs: Array<{ url: string; lastEventId: string | null }> = [];
    page.on("request", (r) => {
      // 瀏覽器網路層自動加的標頭（Last-Event-ID）不在 request.headers()，要用 allHeaders()
      if (r.url().includes("/api/v1/stream/")) {
        void r.allHeaders().then((h) => streamReqs.push({ url: r.url().replace(/access_token=[^&]+/, "access_token=…"), lastEventId: h["last-event-id"] ?? null }));
      }
    });
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open"); // PAUSED 不結束串流
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    const before = streamReqs.length;

    const restart = execFileAsync("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", RESTART_BACKEND], { timeout: 120_000 });
    await expect(page.getByTestId("sse-status")).not.toHaveAttribute("data-state", "open", { timeout: 40_000 }); // 串流被切斷：重連中
    await snap(page, "p4-execute-sse-reconnecting.png");
    await restart;
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open", { timeout: 90_000 });
    // backend 停機約 10 秒：瀏覽器自己的重連（3 秒後、帶 Last-Event-ID）也失敗，所以走 F2 的設計——連續失敗兩次就改以 tail=1000 重建連線，
    // 靠客戶端 (seq,n) 去重補齊（契約 §2.8 第 4 點）。短暫斷線（<3 秒）的原生 Last-Event-ID 重播由下方 E2E-12 的 API 情境驗。
    const reconnects = streamReqs.slice(before).filter((r) => r.url.includes("/logs"));
    expect(reconnects.length, `重連的 /logs 請求：${JSON.stringify(reconnects)}`).toBeGreaterThanOrEqual(1);
    expect(reconnects.some((r) => r.url.includes("tail=1000")), `重建連線要帶 tail=1000：${JSON.stringify(reconnects)}`).toBe(true);
    // 重播後畫面沒有重複：已發生的事件各一次、仍是暫停＋一個待審核項
    await expect(page.getByTestId("run-status")).toContainText("已暫停");
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    await expect(page.getByTestId("log-line").filter({ hasText: "開始：初始化" })).toHaveCount(1);
    await expect(page.getByTestId("log-line").filter({ hasText: "完成：初始化" })).toHaveCount(1);
    await snap(page, "p4-execute-sse-reconnected.png", { tall: true });
    // 重啟後的批次照常往下走：通過審核 → 第二步、第二次暫停（事件由新的 SSE 連線送達）→ 通過 → 跑完
    await decide(page, "approve");
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成", { timeout: 60_000 });
    await expect(page.getByTestId("review-reason")).toContainText("任務「實作」", { timeout: 60_000 });
    await expect(page.getByTestId("log-line").filter({ hasText: "開始：設定" })).toHaveCount(1);
    await decide(page, "approve");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
    const run = await latestRun(request, f.projectId, 1);
    expect(await getRun(request, run.id)).toMatchObject({ status: "COMPLETED", totalTokensUsed: 3720 });
  });

  test("重新整理終態批次：頁面還原狀態，不為終態連線無限重連（終態 204，矩陣 I）", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 執行 REL"), kind: "A", level: 4 });
    await openExec(page, request, f);
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
    const streamHits: string[] = [];
    page.on("response", (res) => {
      if (res.url().includes("/api/v1/stream/")) streamHits.push(`${res.status()} ${res.url().split("?")[0].split("/").slice(-1)[0]}`);
    });
    await page.reload();
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 60_000 });
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成");
    await page.waitForTimeout(8_000); // 給重連一個機會：EventSource 的 retry＝3 秒，終態回 204 之後不該再連
    const logs = streamHits.filter((h) => h.endsWith("logs"));
    const metrics = streamHits.filter((h) => h.endsWith("metrics"));
    expect(logs.length, `/logs 連線：${streamHits.join("、")}`).toBeLessThanOrEqual(2);
    expect(metrics.length, `/metrics 連線：${streamHits.join("、")}`).toBeLessThanOrEqual(2);
    // 日誌重播最後 200 則：每行只出現一次
    await expect(page.getByTestId("log-line").filter({ hasText: "完成：初始化" })).toHaveCount(1);
  });

  test("跨 Phase：匯入（假 LLM）→ signoff → confirm → 專案頁 → 執行頁 Level 3 啟動 → 一路跑完（匯入專案可被引擎執行）", async ({ page, request }) => {
    const llm = new FakeLlm(nm("QA 匯入後執行"));
    await llm.listen();
    try {
      const dir = path.join(E2E_ROOT, "projects", `imp-exec-${RUN}`);
      mkdirSync(dir, { recursive: true });
      expect((await call(request, "admin", "PUT", "/api/v1/settings/model/apiUrl", { value: llm.endpoint })).status).toBe(200);
      expect((await call(request, "admin", "PUT", "/api/v1/settings/model/apiKey", { value: "sk-e2e-dummy", confirm: true })).status).toBe(200);
      const created = await call(request, "operator", "POST", "/api/v1/import/text", { content: brd(), sourceFileName: `exec-${RUN}.md`, sourceType: "MARKDOWN" });
      const id = dataOf<{ id: string }>(created).id;
      expect((await call(request, "operator", "POST", `/api/v1/import/${id}/parse`, { executionPath: dir, autonomyLevel: 3 })).status).toBe(200);
      expect((await call(request, "operator", "POST", `/api/v1/import/${id}/signoff`, { approver: "e2e-approver" })).status).toBe(200);
      const confirm = await call(request, "operator", "POST", `/api/v1/import/${id}/confirm`);
      expect(confirm.status).toBe(201);
      const projectId = dataOf<{ id: string }>(confirm).id;
      // 執行類情境要求 apiKey 為空（關閉引擎演化）
      expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);

      await ensureQuota(request, "operator", 70); // 匯入序列已用掉一批額度；專案頁＋執行頁＋SSE 每頁各約十幾次請求
      await signIn(page, request, "operator");
      await page.goto(`/projects/${projectId}`);
      await expect(page.getByTestId("project-title")).toHaveText(nm("QA 匯入後執行"), FIRST_LOAD);
      await expect(page.getByTestId("goal-row")).toHaveCount(2);
      await page.goto(`/projects/${projectId}/execute`);
      await expect(page.getByTestId("control-start")).toBeEnabled(FIRST_LOAD);
      await expect(page.getByTestId("exec-level")).toHaveValue("3"); // 解析選項的自治等級成為專案的等級
      await page.getByTestId("exec-budget").fill("100,000");
      await page.getByTestId("control-start").click();
      await expect(page.getByTestId("run-number")).toHaveText("Run #1");
      await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
      await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "GOAL_COMPLETED");
      await snap(page, "p4-execute-imported-level3.png", { tall: true });
      await decide(page, "approve");
      await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
      await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成");
      const run = await latestRun(request, projectId, 1);
      expect(await waitRun(request, run.id, ["COMPLETED"])).toMatchObject({ totalTokensUsed: 3720 });
    } finally {
      await llm.close();
      await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
    }
  });
});

/** 以 JWT_SECRET（E2E_JWT_SECRET，測試值）簽一張 HS256 token；exp 可設在過去，造「已過期的 access token」（契約 E2E-12 步驟 1）。 */
function forgeJwt(secret: string, sub: string, role: string, use: "access" | "refresh", exp: number): string {
  const b64u = (s: string) => Buffer.from(s).toString("base64url");
  const head = b64u(JSON.stringify({ alg: "HS256" }));
  const body = b64u(JSON.stringify({ sub, role, token_use: use, iat: exp - 3600, exp }));
  return `${head}.${body}.${createHmac("sha256", secret).update(`${head}.${body}`).digest("base64url")}`;
}

test.describe("契約 E2E-02／E2E-12（API 層，真 SseEmitter）", () => {
  test.setTimeout(300_000);

  test("E2E-02 execute 未 signoff → 409（details 分層列出）、無副作用；逐步 signoff 後才放行；角色與參數檢查", async ({ request }) => {
    const f = await createFixture(request, { name: nm("QA 未簽 PRJ-U"), kind: "A", level: 4, draft: true });
    const exec = (body: unknown, role: "operator" | "viewer" = "operator") => call(request, role, "POST", `/api/v1/projects/${f.projectId}/execute`, body);
    const sorted = (a: string[]) => [...a].sort();
    type Unsigned = { unsignedProjectId?: string | null; unsignedGoalIds?: string[]; unsignedTaskIds?: string[] };
    let r = await exec({});
    expect(r.status).toBe(409);
    expect(r.json.reason).toBe("未經人工審批的草案不可執行");
    expect(r.json.message).toBe("草案未經人工審批，禁止執行");
    let d = r.json.details as Unsigned;
    expect(d.unsignedProjectId).toBe(f.projectId);
    expect(sorted(d.unsignedGoalIds ?? [])).toEqual(sorted(f.goalIds));
    expect(sorted(d.unsignedTaskIds ?? [])).toEqual(sorted(f.taskIds));
    // 無副作用：沒有批次、專案維持 DRAFT
    const runs = dataOf<{ totalElements: number }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}/executions`));
    expect(runs.totalElements).toBe(0);
    expect(dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`)).status).toBe("DRAFT");
    // 只簽專案：unsignedProjectId 缺席或 null（契約 §0.2）
    expect((await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/signoff`, { approver: "qa" })).status).toBe(200);
    r = await exec({});
    expect(r.status).toBe(409);
    d = r.json.details as Unsigned;
    expect(d.unsignedProjectId ?? null).toBeNull();
    expect(d.unsignedGoalIds).toHaveLength(2);
    expect(d.unsignedTaskIds).toHaveLength(3);
    // 再簽兩個目標與前兩個任務：只剩第三個任務
    for (const g of f.goalIds) expect((await call(request, "operator", "POST", `/api/v1/goals/${g}/signoff`, { approver: "qa" })).status).toBe(200);
    for (const t of f.taskIds.slice(0, 2)) expect((await call(request, "operator", "POST", `/api/v1/tasks/${t}/signoff`, { approver: "qa" })).status).toBe(200);
    r = await exec({});
    expect(r.status).toBe(409);
    d = r.json.details as Unsigned;
    expect(d.unsignedGoalIds ?? []).toEqual([]);
    expect(d.unsignedTaskIds).toEqual([f.taskIds[2]]);
    // 檢查順序：未 signoff 先於範圍檢查；全部簽完後同一請求才是 400 所選範圍不合法
    const other = await createFixture(request, { name: nm("QA 未簽 他案"), kind: "A", level: 4 });
    const badScope = { scope: { mode: "SELECTED", goalIds: [other.goalIds[0]] } };
    expect((await exec(badScope)).status).toBe(409);
    expect((await call(request, "operator", "POST", `/api/v1/tasks/${f.taskIds[2]}/signoff`, { approver: "qa" })).status).toBe(200);
    r = await exec(badScope);
    expect(r.status).toBe(400);
    expect(r.json.reason).toBe("所選範圍不合法");
    expect((r.json.details as { invalidGoalIds: string[] }).invalidGoalIds).toEqual([other.goalIds[0]]);
    // 角色與參數
    expect((await exec({}, "viewer")).status).toBe(403);
    expect((await call(request, "operator", "POST", "/api/v1/projects/00000000-0000-4000-8000-000000000000/execute", {})).status).toBe(404);
    expect((await exec({ autonomyLevel: 11 })).status).toBe(400);
    expect((await exec({ scope: { mode: "ALL", goalIds: [f.goalIds[0]] } })).status).toBe(400);
    const maxRetries = await call(request, "operator", "PUT", `/api/v1/tasks/${f.taskIds[0]}`, { maxRetries: 25 });
    expect(maxRetries.status).toBe(400);
    expect((maxRetries.json.errors as Array<{ field: string }>)[0].field).toBe("maxRetries");
    // 全部簽完：201、專案 EXECUTING；執行中再 execute → 409 專案正在執行中（details.runId）；cancel 收尾
    r = await exec({ autonomyLevel: 4 });
    expect(r.status, JSON.stringify(r.json)).toBe(201);
    const runId = dataOf<{ id: string }>(r).id;
    const again = await exec({});
    expect(again.status).toBe(409);
    expect(again.json.reason).toBe("專案正在執行中");
    expect((again.json.details as { runId: string }).runId).toBe(runId);
    expect(dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}`)).status).toBe("EXECUTING");
    const cancel = await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`);
    expect([200, 409]).toContain(cancel.status); // 引擎很快跑完時 cancel 可能已是終態
    await waitRun(request, runId, ["COMPLETED", "CANCELLED", "FAILED"]);
  });

  test("E2E-12 SSE：認證（401 JSON）、標頭優先、404、重播（Last-Event-ID）、終態 204、/metrics 三則快照 id、PAUSED 的 keep-alive、預檢", async ({ request }) => {
    const secret = process.env.E2E_JWT_SECRET;
    const done = await createFixture(request, { name: nm("QA SSE 完成"), kind: "A", level: 4 });
    const started = await call(request, "operator", "POST", `/api/v1/projects/${done.projectId}/execute`, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
    expect(started.status).toBe(201);
    const runId = dataOf<{ id: string }>(started).id;
    const finished = await waitRun(request, runId, ["COMPLETED"]);
    const S = finished.lastEventSeq!;
    const base = `${API_URL}/api/v1/stream/executions/${runId}`;
    const opT = await tokenOf(request, "operator");
    const vwT = await tokenOf(request, "viewer");
    const login = await request.post(`${API_URL}/api/v1/auth/login`, { data: { username: "viewer", password: ["Viewer", "Dev2026"].join("#") } });
    const refresh = ((await login.json()) as { data: { refreshToken: string } }).data.refreshToken;
    const jsonOf = (r: { body?: string }) => JSON.parse(r.body ?? "{}") as { reason?: string; code?: number; traceId?: string };

    // 步驟 1：401 JSON，在串流開始之前回
    const noToken = await readSse(`${base}/logs`);
    expect(noToken.status).toBe(401);
    expect(jsonOf(noToken).reason).toBe("UNAUTHENTICATED");
    const garbage = await readSse(`${base}/logs?access_token=garbage`);
    expect([garbage.status, jsonOf(garbage).reason]).toEqual([401, "TOKEN_INVALID"]);
    const asRefresh = await readSse(`${base}/logs?access_token=${refresh}`);
    expect([asRefresh.status, jsonOf(asRefresh).reason]).toEqual([401, "TOKEN_INVALID"]);
    if (secret) {
      const expired = forgeJwt(secret, "viewer", "VIEWER", "access", Math.floor(Date.now() / 1000) - 60);
      const r = await readSse(`${base}/logs?access_token=${expired}`);
      expect([r.status, jsonOf(r).reason]).toEqual([401, "TOKEN_EXPIRED"]);
    }
    // 步驟 2～4：viewer 可看、標頭優先於查詢參數、查無 run → 404 JSON
    expect((await readSse(`${base}/logs`, { headers: { Authorization: `Bearer ${vwT}` } })).status).toBe(200);
    expect((await readSse(`${base}/logs?access_token=garbage`, { headers: { Authorization: `Bearer ${vwT}` } })).status).toBe(200);
    const missing = await readSse(`${API_URL}/api/v1/stream/executions/00000000-0000-4000-8000-000000000000/logs`, { headers: { Authorization: `Bearer ${vwT}` } });
    expect(missing.status).toBe(404);

    // 步驟 5：已完成的 R——沒有 Last-Event-ID：重播後關閉；第一個框架 retry＝3000；id 嚴格遞增；最後一則 status-change＝COMPLETED
    const full = await readSse(`${base}/logs?access_token=${opT}`);
    expect(full.status).toBe(200);
    expect(full.headers.get("content-type")).toContain("text/event-stream");
    expect(full.headers.get("cache-control")).toContain("no-store");
    expect(full.headers.get("x-accel-buffering")).toBe("no");
    expect(full.frames[0].retry).toBe("3000");
    const idFrames = full.frames.filter((fr) => fr.id !== undefined);
    const pairs = idFrames.map((fr) => idPair(fr.id!));
    for (let i = 1; i < pairs.length; i += 1) {
      const [a, b] = [pairs[i - 1], pairs[i]];
      expect(a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]), `id 必須嚴格遞增：${a} → ${b}`).toBe(true);
    }
    const statusFrames = idFrames.filter((fr) => fr.event === "status-change").map((fr) => JSON.parse(fr.data!) as { runStatus: string; bridgeStatus: string });
    expect(statusFrames.at(-1)).toMatchObject({ runStatus: "COMPLETED", bridgeStatus: "COMPLETED" });
    const steps = idFrames.filter((fr) => fr.event === "log").map((fr) => JSON.parse(fr.data!) as { source: string; stepId?: string; stepStatus?: string; message: string; taskId?: string });
    expect(steps.filter((s) => s.source === "STEP").map((s) => `${s.stepStatus} ${s.stepId}`)).toEqual(["STARTED G1-T1", "COMPLETED G1-T1", "STARTED G1-T2", "COMPLETED G1-T2", "STARTED G2-T1", "COMPLETED G2-T1"]);
    expect(steps.filter((s) => s.source === "STEP" && s.stepStatus === "COMPLETED").every((s) => s.message.endsWith("Token: 1240"))).toBe(true);
    expect(steps.some((s) => s.source === "ENGINE")).toBe(true);
    expect(idFrames.some((fr) => fr.event === "review-request" || fr.event === "alert")).toBe(false);
    // 步驟 6～7：Last-Event-ID＝S → 204；garbage 視為未帶；tail=0（無 Last-Event-ID）→ 204；中段 id → 重播其後事件（各一次）
    expect((await readSse(`${base}/logs?access_token=${opT}`, { headers: { "Last-Event-ID": String(S) } })).status).toBe(204);
    const garbageId = await readSse(`${base}/logs?access_token=${opT}`, { headers: { "Last-Event-ID": "garbage" } });
    expect([garbageId.status, garbageId.frames.filter((fr) => fr.id).length]).toEqual([200, idFrames.length]);
    expect((await readSse(`${base}/logs?access_token=${opT}&tail=0`)).status).toBe(204);
    const mid = idFrames[4].id!;
    const replay = await readSse(`${base}/logs?access_token=${opT}`, { headers: { "Last-Event-ID": mid } });
    expect(replay.status).toBe(200);
    expect(replay.frames.filter((fr) => fr.id).map((fr) => fr.id)).toEqual(idFrames.slice(5).map((fr) => fr.id));
    // 步驟 8：/metrics——恰三則收斂快照，id 互異、嚴格遞增（<S>.1／<S>.2／<S>.3），之後關閉
    const metrics = await readSse(`${base}/metrics?access_token=${opT}`);
    expect(metrics.status).toBe(200);
    const mFrames = metrics.frames.filter((fr) => fr.id);
    expect(mFrames.map((fr) => [fr.id, fr.event])).toEqual([[`${S}.1`, "progress-update"], [`${S}.2`, "token-update"], [`${S}.3`, "metric-update"]]);
    expect(JSON.parse(mFrames[0].data!)).toMatchObject({ completedSteps: 3, totalSteps: 3, progressPct: 100 });
    expect(JSON.parse(mFrames[1].data!)).toMatchObject({ tokensUsed: 3720 });
    expect(JSON.parse(mFrames[2].data!)).toMatchObject({ completedTasks: 3, totalTasks: 3, totalTokensUsed: 3720 });
    expect((await readSse(`${base}/metrics?access_token=${opT}`, { headers: { "Last-Event-ID": `${S}.3` } })).status).toBe(204);
    const partial = await readSse(`${base}/metrics?access_token=${opT}`, { headers: { "Last-Event-ID": `${S}.1` } });
    expect([partial.status, partial.frames.filter((fr) => fr.id).length]).toEqual([200, 3]);

    // 步驟 10：PAUSED 的批次——連線保持，每 ≤ keep-alive-seconds（e2e＝2 秒）收到註解行 keep-alive
    const paused = await createFixture(request, { name: nm("QA SSE 暫停"), kind: "A", level: 1 });
    const p = await call(request, "operator", "POST", `/api/v1/projects/${paused.projectId}/execute`, { autonomyLevel: 1, tokenBudget: 100000, scope: { mode: "ALL" } });
    const pausedRun = dataOf<{ id: string }>(p).id;
    // 契約 §2.4：PAUSED 的狀態比審核項早一步可見——等到審核項出現
    const pausedView = await poll(() => getRun(request, pausedRun), (r) => r.status === "PAUSED" && (r.pendingReviews ?? []).length > 0, `批次 ${pausedRun} PAUSED 且審核項已建立`, 90_000);
    expect(pausedView.pendingReviews).toHaveLength(1);
    const alive = await readSse(`${API_URL}/api/v1/stream/executions/${pausedRun}/logs?access_token=${opT}&tail=0`, { maxMs: 7_000 });
    expect(alive.status).toBe(200);
    expect(alive.comments.filter((c) => c === "keep-alive").length, `keep-alive 註解：${JSON.stringify(alive.comments)}`).toBeGreaterThanOrEqual(2);
    // PAUSED 的重播含 review-request：id＝<PAUSED 事件的 seq>.1，allowedDecisions＝[APPROVE,REJECT]
    const pausedAll = await readSse(`${API_URL}/api/v1/stream/executions/${pausedRun}/logs?access_token=${opT}`, { maxMs: 3_000 });
    const reviewFrame = pausedAll.frames.find((fr) => fr.event === "review-request")!;
    expect(reviewFrame).toBeTruthy();
    expect(reviewFrame.id).toMatch(/^\d+\.1$/);
    const rv = JSON.parse(reviewFrame.data!) as { sub: number; review: { id: string; kind: string; status: string; allowedDecisions: string[] } };
    expect(rv.review).toMatchObject({ kind: "TASK_CONFIRM", status: "PENDING", allowedDecisions: ["APPROVE", "REJECT"] });
    expect(rv.review.id).toBe(pausedView.pendingReviews![0].id);
    // 以 review-request 的 id 重連：不再重播任何事件，只有 keep-alive
    const after = await readSse(`${API_URL}/api/v1/stream/executions/${pausedRun}/logs?access_token=${opT}`, { headers: { "Last-Event-ID": reviewFrame.id! }, maxMs: 4_000 });
    expect(after.frames.filter((fr) => fr.id)).toEqual([]);
    expect(after.comments).toContain("keep-alive");
    // 審核項的決定：不允許的 SKIP → 409、隨機 uuid → 404、APPROVE → 204；再送 → 409 審核項已處理
    const rid = pausedView.pendingReviews![0].id;
    const skip = await call(request, "operator", "POST", `/api/v1/executions/${pausedRun}/review/${rid}`, { decision: "SKIP" });
    expect(skip.status).toBe(409);
    expect(skip.json.reason).toBe("此審核項不允許該決定");
    expect((skip.json.details as { allowedDecisions: string[] }).allowedDecisions).toEqual(["APPROVE", "REJECT"]);
    expect((await call(request, "operator", "POST", `/api/v1/executions/${pausedRun}/review/00000000-0000-4000-8000-000000000001`, { decision: "APPROVE" })).status).toBe(404);
    expect((await call(request, "operator", "POST", `/api/v1/executions/${pausedRun}/review/${rid}`, { decision: "APPROVE", comment: "ok" })).status).toBe(204);
    const twice = await call(request, "operator", "POST", `/api/v1/executions/${pausedRun}/review/${rid}`, { decision: "APPROVE" });
    expect(twice.status).toBe(409);
    expect(twice.json.reason).toBe("審核項已處理");
    expect(twice.json.details).toMatchObject({ status: "APPROVED", decidedBy: "operator" });
    await waitRun(request, pausedRun, ["PAUSED"]);
    expect((await call(request, "operator", "POST", `/api/v1/executions/${pausedRun}/cancel`)).status).toBe(200);
    // 步驟 11：預檢——Allow-Headers 含 Last-Event-ID
    const pre = await fetch(`${base}/logs`, { method: "OPTIONS", headers: { Origin: "http://localhost:3000", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "last-event-id,authorization" } });
    expect(pre.status).toBeLessThan(300);
    expect((pre.headers.get("access-control-allow-headers") ?? "").toLowerCase()).toContain("last-event-id");
  });
});

type RunPending = { pendingReviews?: Array<{ id: string; kind: string; status: string; allowedDecisions: string[] }> };
