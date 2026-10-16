import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { RUN } from "./helpers";
import { snap } from "./mockApi";
import { E2E_ROOT, NEEDS_BRIDGE, bootstrapSettings, call, createFixture, dataOf, ensureQuota, getRun, poll, signIn, waitRun, type Fixture } from "./realBackend";

/**
 * Phase 4 補充情境（p4-execute.spec.ts 沒有覆蓋的契約規則）——對真後端＋真 Bridge＋aisdlc-mock-claude：
 *   執行範圍（US-E-02）、手動暫停／恢復（US-E-04／05，契約 §1.2.4～1.2.6）、等級 2 的目標確認閘（API-AUT-02）、
 *   審核 REJECT 三型（契約 §3.5.3 對照表）、路徑 A 匯入的專案被引擎執行且 evaluator（pytest）真的跑了、
 *   連續失敗告警（API-ALR-03：逐批各失敗一個任務，第 3 個觸發 CONSECUTIVE_FAILURES）。
 * 前置同 p4-execute.spec.ts（見 realBackend.ts 檔頭）。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const MOCK_CLAUDE = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");
const nm = (base: string) => `${base} ${RUN}`;

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
  const reset = await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true"); // 執行類情境要求 apiKey 為空
  expect(reset.status).toBe(200);
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator");
});

async function openExec(page: Page, request: APIRequestContext, f: Fixture): Promise<void> {
  await signIn(page, request, "operator");
  await page.goto(`/projects/${f.projectId}/execute`);
  await expect(page.getByRole("heading", { name: `專案執行：${f.name}` })).toBeVisible(FIRST_LOAD);
}

async function latestRun(request: APIRequestContext, projectId: string, runNumber: number): Promise<{ id: string; runNumber: number; status: string }> {
  const r = await call(request, "viewer", "GET", `/api/v1/projects/${projectId}/executions?sort=runNumber,desc&size=10`);
  expect(r.status).toBe(200);
  const hit = dataOf<{ content: Array<{ id: string; runNumber: number; status: string }> }>(r).content.find((x) => x.runNumber === runNumber);
  expect(hit, `找不到批次 ${runNumber}`).toBeTruthy();
  return hit!;
}

/** 審核卡：點某個決定 → 確認對話框（可填意見）→ 送出。 */
async function decide(page: Page, decision: "approve" | "retry" | "skip" | "reject", comment?: string): Promise<void> {
  await page.getByTestId(`review-${decision}`).click();
  await expect(page.getByTestId("review-dialog")).toBeVisible();
  if (comment) await page.getByTestId("review-comment").fill(comment);
  await page.getByTestId("review-confirm").click();
  await expect(page.getByTestId("review-dialog")).toHaveCount(0);
}

const statusOf = async (request: APIRequestContext, kind: "projects" | "goals" | "tasks", id: string): Promise<string> =>
  dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/${kind}/${id}`)).status;

/** 契約 §2.4：Bridge 直接寫 DB 的終態／暫停狀態，比 Console 消費事件建審核項早一步——GET run 看到狀態時審核項可能還沒建好，所以等到它出現。 */
const waitWithReview = (request: APIRequestContext, runId: string, status: "FAILED" | "PAUSED", timeoutMs = 120_000) =>
  poll(
    () => getRun(request, runId),
    (r) => r.status === status && (r.pendingReviews ?? []).length > 0,
    `批次 ${runId} 進入 ${status} 且審核項已建立`,
    timeoutMs,
  );

test.describe("Phase 4 補充情境（真後端＋真 Bridge＋mock claude）", () => {
  test.setTimeout(240_000);

  test("執行範圍（US-E-02）：只勾目標 1 → 只跑 G1 的兩個任務、專案回 READY、G2 仍 PENDING；重新整理後以預設範圍跑完剩下的", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 範圍"), kind: "A", level: 4 });
    await openExec(page, request, f);
    await expect(page.getByTestId("scope-all")).toHaveAttribute("data-state", "checked");
    await page.getByTestId(`scope-goal-${f.goalIds[1]}`).click(); // 取消勾選目標「核心」
    await expect(page.getByTestId(`scope-goal-${f.goalIds[1]}`)).toHaveAttribute("data-state", "unchecked");
    await expect(page.getByTestId("scope-all")).toHaveAttribute("data-state", "indeterminate");
    await page.getByTestId("exec-budget").fill("100,000");
    await snap(page, "p4b-execute-scope.png");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 2 任務完成");
    const run1 = await latestRun(request, f.projectId, 1);
    const d1 = await getRun(request, run1.id);
    expect(d1).toMatchObject({ status: "COMPLETED", completedSteps: 2, totalSteps: 2, totalTokensUsed: 2480 });
    expect((d1 as unknown as { scope?: { mode?: string; goalIds?: string[] } }).scope).toMatchObject({ mode: "SELECTED", goalIds: [f.goalIds[0]] });
    const steps1 = dataOf<{ content: Array<{ stepId: string; status: string }> }>(await call(request, "viewer", "GET", `/api/v1/executions/${run1.id}/steps?size=200`)).content;
    expect(steps1.map((s) => `${s.stepId}:${s.status}`)).toEqual(["G1-T1:STARTED", "G1-T1:COMPLETED", "G1-T2:STARTED", "G1-T2:COMPLETED"]);
    expect(await statusOf(request, "projects", f.projectId)).toBe("READY"); // 還有未完成的目標：專案不是 COMPLETED
    expect(await statusOf(request, "goals", f.goalIds[0])).toBe("COMPLETED");
    expect(await statusOf(request, "goals", f.goalIds[1])).toBe("PENDING");
    expect(await statusOf(request, "tasks", f.taskIds[2])).toBe("PENDING");

    // 第二批：重新整理 → 預設範圍（ALL＝專案內全部「可執行」任務，已完成的不算）只剩 T3
    await page.reload();
    await expect(page.getByTestId("control-start")).toBeEnabled(FIRST_LOAD);
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #2", { timeout: 30_000 });
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 1 任務完成");
    const run2 = await latestRun(request, f.projectId, 2);
    expect(await getRun(request, run2.id)).toMatchObject({ status: "COMPLETED", completedSteps: 1, totalSteps: 1, totalTokensUsed: 1240 });
    expect(await statusOf(request, "projects", f.projectId)).toBe("COMPLETED");
  });

  test("手動暫停／恢復（US-E-04／05）：RUNNING 時按暫停 → 在步驟邊界 PAUSED（沒有懸空的 STARTED）→ 暫停期間不前進 → 恢復後跑完，每步恰一次", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 手動暫停"), kind: "B", level: 4 }); // 5 個任務
    await openExec(page, request, f);
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "RUNNING", { timeout: 30_000 });
    await expect(page.getByTestId("control-pause")).toBeEnabled();
    await page.getByTestId("control-pause").click();
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    await expect(page.getByTestId("run-reason")).toContainText("在步驟邊界暫停");
    await expect(page.getByTestId("control-resume")).toBeEnabled();
    await snap(page, "p4b-execute-paused-manual.png", { tall: true });
    const run = await latestRun(request, f.projectId, 1);
    const paused = await getRun(request, run.id);
    expect(paused).toMatchObject({ status: "PAUSED", bridgeStatus: "PAUSED" });
    expect(paused.completedSteps ?? 0).toBeGreaterThanOrEqual(1);
    expect(paused.completedSteps ?? 0).toBeLessThanOrEqual(4); // 暫停有效：沒有一路跑完
    expect(paused.reason ?? "").toContain("續跑點");
    expect(paused.pendingReviews ?? [], "手動暫停不建審核項").toEqual([]);
    const stepsAtPause = dataOf<{ content: Array<{ stepId: string; status: string }> }>(await call(request, "viewer", "GET", `/api/v1/executions/${run.id}/steps?size=200`)).content;
    expect(stepsAtPause.at(-1)!.status, "暫停落在步驟邊界：最後一列是 COMPLETED，沒有懸空的 STARTED").toBe("COMPLETED");
    // 暫停期間不前進
    await page.waitForTimeout(4_000);
    expect((await getRun(request, run.id)).completedSteps).toBe(paused.completedSteps);
    // 恢復 → 跑完；每個任務的「開始」只出現一次
    await page.getByTestId("control-resume").click();
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 120_000 });
    await expect(page.getByTestId("progress-tasks")).toHaveText("5 / 5 任務完成");
    for (const name of ["任務一", "任務二", "任務三", "任務四", "任務五"]) {
      await expect(page.getByTestId("log-line").filter({ hasText: `開始：${name}` })).toHaveCount(1);
    }
    expect(await getRun(request, run.id)).toMatchObject({ status: "COMPLETED", completedSteps: 5, totalTokensUsed: 6200 });
  });

  test("等級 2（API-AUT-02）：G1 最後一步之後 PAUSED＋GOAL_CONFIRM（只有通過／拒絕）→ 通過 → 跑完", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 等級2"), kind: "A", level: 2 });
    await openExec(page, request, f);
    await page.getByTestId("exec-level").selectOption("2");
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "GOAL_CONFIRM");
    await expect(page.getByTestId("review-reason")).toContainText("Level 2：請確認是否開始目標「核心」");
    await expect(page.getByTestId("review-approve")).toBeEnabled();
    await expect(page.getByTestId("review-reject")).toBeEnabled();
    await expect(page.getByTestId("review-retry")).toBeDisabled();
    await expect(page.getByTestId("review-skip")).toBeDisabled();
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成"); // 目標一的兩個任務都做完才暫停（等級 1 是每個任務之後）
    await expect(page.getByTestId("log-line").filter({ hasText: "開始：實作" })).toHaveCount(0);
    await expect(page.getByTestId("bell-badge"), "待審核項計入頂列通知鈴徽章（US-E-07）").toBeVisible();
    await snap(page, "p4b-execute-level2-review.png", { tall: true });
    const run = await latestRun(request, f.projectId, 1);
    const paused = await getRun(request, run.id);
    expect(paused).toMatchObject({ status: "PAUSED", completedSteps: 2 });
    expect(paused.pendingReviews).toHaveLength(1);
    expect(paused.pendingReviews![0]).toMatchObject({ kind: "GOAL_CONFIRM", allowedDecisions: ["APPROVE", "REJECT"] });
    await decide(page, "approve");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 90_000 });
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成");
    expect(await getRun(request, run.id)).toMatchObject({ status: "COMPLETED", totalTokensUsed: 3720 });
  });

  test("審核 REJECT（契約 §3.5.3）：等級 1 的 TASK_CONFIRM → run CANCELLED；等級 3 的 GOAL_COMPLETED → run CANCELLED 且被審目標 FAILED（人類判定優先）", async ({ page, request }) => {
    // 等級 1：第一步後暫停 → REJECT（帶意見）→ :stop → CANCELLED；專案回 READY
    const l1 = await createFixture(request, { name: nm("QA 拒絕L1"), kind: "A", level: 1 });
    await openExec(page, request, l1);
    await page.getByTestId("exec-level").selectOption("1");
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "TASK_CONFIRM");
    await decide(page, "reject", "QA 拒絕：不要繼續");
    await expect(page.getByTestId("run-status")).toContainText("已取消", { timeout: 30_000 });
    await expect(page.getByTestId("review-empty")).toBeVisible();
    await expect(page.getByTestId("log-line").filter({ hasText: "狀態：已取消" })).toHaveCount(1); // REJECT＝:stop；人類的決定不另寫 REVIEW 日誌行（系統自動關閉才寫）
    await snap(page, "p4b-execute-rejected-l1.png", { tall: true });
    const r1 = await latestRun(request, l1.projectId, 1);
    const v1 = await getRun(request, r1.id);
    expect(v1).toMatchObject({ status: "CANCELLED", completedSteps: 1 });
    expect(v1.pendingReviews ?? []).toEqual([]);
    expect(await statusOf(request, "projects", l1.projectId)).toBe("READY");

    // 等級 3：G1 完成後 GOAL_COMPLETED 待審核 → REJECT → CANCELLED；G1 被標 FAILED，G2 維持 PENDING
    await ensureQuota(request, "operator", 60);
    const l3 = await createFixture(request, { name: nm("QA 拒絕L3"), kind: "A", level: 3 });
    await openExec(page, request, l3);
    await page.getByTestId("exec-level").selectOption("3");
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 60_000 });
    await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "GOAL_COMPLETED");
    await decide(page, "reject", "QA 拒絕：目標不合格");
    await expect(page.getByTestId("run-status")).toContainText("已取消", { timeout: 30_000 });
    const r3 = await latestRun(request, l3.projectId, 1);
    expect(await getRun(request, r3.id)).toMatchObject({ status: "CANCELLED", completedSteps: 2 });
    expect(await statusOf(request, "goals", l3.goalIds[0])).toBe("FAILED");
    expect(await statusOf(request, "goals", l3.goalIds[1])).toBe("PENDING");
    expect(await statusOf(request, "projects", l3.projectId)).not.toBe("EXECUTING");
  });

  test("審核 REJECT（ESCALATED）：只關閉審核項——run 維持 FAILED、任務維持失敗、不呼叫 Bridge", async ({ page, request }) => {
    const f = await createFixture(request, { name: nm("QA 拒絕ESC"), kind: "A", level: 4, failTasks: [2] });
    await openExec(page, request, f);
    await page.getByTestId("exec-budget").fill("100,000");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "FAILED", { timeout: 90_000 });
    await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "ESCALATED");
    const run = await latestRun(request, f.projectId, 1);
    await decide(page, "reject", "QA 拒絕：放棄這個任務");
    await expect(page.getByTestId("review-empty")).toBeVisible();
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "FAILED");
    const after = await getRun(request, run.id);
    expect(after).toMatchObject({ status: "FAILED", completedSteps: 1 });
    expect(after.pendingReviews ?? []).toEqual([]);
    expect(["ESCALATED", "FAILED"]).toContain(await statusOf(request, "tasks", f.taskIds[1]));
    expect(await statusOf(request, "goals", f.goalIds[0])).toBe("FAILED");
    // 重複決定：審核項已不是 PENDING
    const again = await call(request, "operator", "POST", `/api/v1/executions/${run.id}/review/00000000-0000-4000-8000-000000000000`, { decision: "REJECT" });
    expect(again.status).toBe(404);
  });

  test("E2E-05 變體：V1 第一步失敗的 RETRY（沒有還原點→後續批次）、V3 新批次取代舊審核項、V4 等級 5 與等級 4 同樣建 ESCALATED 審核項（API-AUT-05）", async ({ request }) => {
    test.setTimeout(420_000);
    const start = (f: Fixture, level: number) => call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: level, tokenBudget: 100000, scope: { mode: "ALL" } });
    const idOf = (r: Awaited<ReturnType<typeof start>>) => {
      expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(201);
      return dataOf<{ id: string }>(r).id;
    };
    // V1：T1 帶 [FAIL_ME]；RETRY → 沒有 step_idx=0 的快照 → 204＋X-Follow-Up-Run-Id；新批次重跑並再度失敗，舊審核項已處置
    const v1 = await createFixture(request, { name: nm("QA 變體V1"), kind: "A", level: 4, failTasks: [1] });
    const run1 = idOf(await start(v1, 4));
    const failed1 = await waitWithReview(request, run1, "FAILED");
    expect(failed1.pendingReviews).toHaveLength(1);
    const retry = await call(request, "operator", "POST", `/api/v1/executions/${run1}/review/${failed1.pendingReviews![0].id}`, { decision: "RETRY", comment: "第一步失敗，沒有還原點" });
    expect(retry.status).toBe(204);
    const followUp = retry.headers["x-follow-up-run-id"];
    expect(followUp, "第一步失敗沒有還原點：RETRY 開後續批次").toBeTruthy();
    const run1b = await waitWithReview(request, followUp, "FAILED");
    expect(run1b).toMatchObject({ runNumber: 2, status: "FAILED" });
    expect(run1b.pendingReviews, "後續批次再度失敗：新的 ESCALATED 審核項").toHaveLength(1);
    expect((await getRun(request, run1)).pendingReviews ?? [], "舊審核項已被處置（RETRIED）").toEqual([]);

    // V3：run FAILED 且審核項 PENDING 時直接開新批次 → 舊審核項被系統關閉
    await ensureQuota(request, "operator", 60);
    const v3 = await createFixture(request, { name: nm("QA 變體V3"), kind: "A", level: 4, failTasks: [2] });
    const a = idOf(await start(v3, 4));
    expect((await waitWithReview(request, a, "FAILED")).pendingReviews).toHaveLength(1);
    const b = idOf(await start(v3, 4));
    const afterNew = await getRun(request, a);
    expect(afterNew.status).toBe("FAILED");
    expect(afterNew.pendingReviews ?? [], "新批次建立時，前一批仍 PENDING 的審核項自動 REJECTED").toEqual([]);
    await waitRun(request, b, ["FAILED"], 120_000);

    // V4：等級 5 與等級 4 同樣在失敗時建 ESCALATED 審核項（沒有任何暫停閘）
    await ensureQuota(request, "operator", 60);
    const v4 = await createFixture(request, { name: nm("QA 變體V4"), kind: "A", level: 5, failTasks: [2] });
    const c = idOf(await start(v4, 5));
    const failed4 = await waitWithReview(request, c, "FAILED");
    expect(failed4).toMatchObject({ status: "FAILED", completedSteps: 1 });
    expect(failed4.pendingReviews).toHaveLength(1);
    expect(failed4.pendingReviews![0]).toMatchObject({ kind: "ESCALATED", allowedDecisions: ["RETRY", "SKIP", "REJECT"] });
  });

  test("execute 前置檢查補充（契約 §1.2.1 #3／#7b／#7c／#10）：依賴未選未完成、併發啟動只放行一個（Bridge 鎖＋補償）、專案執行中、無可執行任務", async ({ request }) => {
    const f = await createFixture(request, { name: nm("QA 前置檢查"), kind: "A", level: 4 });
    const body = { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } };
    const exec = (b: unknown) => call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, b);
    // #7b：只選目標「核心」，但它依賴沒被選、也還沒完成的「基礎」
    const dep = await exec({ autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "SELECTED", goalIds: [f.goalIds[1]] } });
    expect([dep.status, dep.json.reason]).toEqual([409, "所選目標依賴未完成的前置目標"]);
    expect((dep.json.details as { missingGoalIds: string[] }).missingGoalIds).toEqual([f.goalIds[0]]);
    expect(await statusOf(request, "projects", f.projectId), "被擋下的啟動沒有副作用").not.toBe("EXECUTING");
    // #10：兩個同時啟動 → 只放行一個；另一個是 409（專案已在執行中，或 Bridge 的同專案同路徑鎖，視誰先提交），且不留批次列（補償刪除）
    const both = await Promise.all([exec(body), exec(body)]);
    expect(both.map((r) => r.status).sort(), JSON.stringify(both.map((r) => [r.status, r.json.reason]))).toEqual([201, 409]);
    const loser = both.find((r) => r.status === 409)!;
    expect(["專案正在執行中", "同專案同路徑已有執行中的批次"]).toContain(loser.json.reason);
    const runId = dataOf<{ id: string }>(both.find((r) => r.status === 201)!).id;
    // #3：執行中再啟動 → 409 專案正在執行中（details 帶專案與目前批次）
    const busy = await exec(body);
    expect([busy.status, busy.json.reason]).toEqual([409, "專案正在執行中"]);
    expect(busy.json.details).toMatchObject({ projectId: f.projectId, runId });
    const list = dataOf<{ totalElements: number }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}/executions`));
    expect(list.totalElements, "輸家的批次列已補償刪除，只剩一個批次").toBe(1);
    await waitRun(request, runId, ["COMPLETED"], 120_000);
    // #7c：全部跑完後再啟動 → 沒有可執行的任務
    const none = await exec(body);
    expect([none.status, none.json.reason]).toEqual([409, "沒有可執行的任務"]);
  });

  test("路徑 A 匯入的專案被引擎執行：凍結規格 → signoff → confirm → Level 4 → COMPLETED，evaluator（pytest）真的在專案目錄跑了", async ({ request }) => {
    const root = path.join(E2E_ROOT, "projects", `sdd-exec-${RUN}`);
    const ids = [1, 2, 3].map((n) => `AT-00${n}-1-1`);
    mkdirSync(path.join(root, "build", "reports", "fsm"), { recursive: true });
    mkdirSync(path.join(root, "docs", "03_testing", "contracts"), { recursive: true });
    mkdirSync(path.join(root, "tests"), { recursive: true });
    writeFileSync(
      path.join(root, "build", "reports", "fsm", "FSM-STATE-demo.yaml"),
      "fsm_state:\n  project: demo\n  session_id: sid-1\n  current_state: IMPLEMENTATION\n  current_sprint: 2\n  updated_at: '2026-10-14T00:00:00+00:00'\n  frozen_stages:\n  - stage: SCG-0\n  decision_trace:\n  - {ts: t0, from: S0, to: S1, reason: r0}\n",
      "utf-8",
    );
    // Then 斷言是引號包住的 [ATn_DONE]：expected_output_regex 即該字面，mock claude 會回放 prompt 裡的 [KEYWORD]
    const rows = ids.map((at, i) => `| AC-00${i + 1}-1 | 驗收 ${i + 1} | ${at} | 情境 ${i + 1} | ✅ | Unit | □ |`);
    const blocks = ids.map((at, i) => `\`\`\`gherkin\n# ${at}\nScenario: 情境 ${i + 1}\n  Given 前置條件\n  When 執行動作\n  Then 輸出「[AT${i + 1}_DONE]」\n\`\`\``);
    writeFileSync(
      path.join(root, "docs", "03_testing", "contracts", "TEST-CONTRACT-SPEC-Demo.md"),
      `# Test Contract Specification — Demo\n\n場景：brownfield 既有系統改進\n\n## 1. AC → AT 映射表\n\n| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |\n|-------|---------|-------|---------|-------|---------|------|\n${rows.join("\n")}\n\n## 2. AT 格式\n\n${blocks.join("\n\n")}\n`,
      "utf-8",
    );
    // evaluator 模板：pytest tests -k "AT_001_1_1" -q（引擎在專案目錄以裸 pytest 執行）→ 測試函式名要含 AT_001_1_1
    writeFileSync(path.join(root, "tests", "test_demo.py"), ids.map((at) => `def test_${at.replace(/-/g, "_")}_basic():\n    assert True\n`).join("\n"), "utf-8");

    const rec = dataOf<{ id: string }>(await call(request, "operator", "POST", "/api/v1/import/text", { content: "凍結規格匯入後執行（短內容）", sourceType: "PLAIN_TEXT" })).id;
    const parsed = await call(request, "operator", "POST", `/api/v1/import/${rec}/parse`, { executionPath: root, autonomyLevel: 4 });
    expect(parsed.status, JSON.stringify(parsed.json).slice(0, 300)).toBe(200);
    expect(dataOf(parsed)).toMatchObject({ path: "SDD", status: "PARSED" });
    expect((await call(request, "operator", "POST", `/api/v1/import/${rec}/signoff`, { approver: "e2e-approver" })).status).toBe(200);
    const confirm = await call(request, "operator", "POST", `/api/v1/import/${rec}/confirm`);
    expect(confirm.status).toBe(201);
    const projectId = dataOf<{ id: string }>(confirm).id;

    await ensureQuota(request, "operator", 30);
    const started = await call(request, "operator", "POST", `/api/v1/projects/${projectId}/execute`, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
    expect(started.status, JSON.stringify(started.json).slice(0, 300)).toBe(201);
    const runId = dataOf<{ id: string }>(started).id;
    const done = await waitRun(request, runId, ["COMPLETED", "FAILED", "CANCELLED"], 150_000);
    expect(done, `run 終態＝${done.status}；reason＝${done.reason}`).toMatchObject({ status: "COMPLETED", completedSteps: 3, totalSteps: 3, totalTokensUsed: 3720 });
    expect(existsSync(path.join(root, ".pytest_cache")), "evaluator 的 pytest 在專案目錄執行過（留下 .pytest_cache）").toBe(true);
    expect(await statusOf(request, "projects", projectId)).toBe("COMPLETED");
  });

  test("連續失敗告警（API-ALR-03，契約 §3.7）：同一目標逐批各失敗一個任務（scope.taskIds），第 3 個觸發 CONSECUTIVE_FAILURES，並在該次 ESCALATED 審核項的 reason 註明", async ({ request }) => {
    // 引擎遇到第一個升級就結束批次，所以要累計 3 個終局失敗只能「逐批各選一個任務」；SKIP 會把任務變成 SKIPPED 而從序列消失，
    // 重跑 ALL 又會卡在同一個任務，因此用 REJECT（只關審核項、任務維持 ESCALATED）搭配 SELECTED 的 taskIds。
    const f = await createFixture(request, { name: nm("QA 連續失敗"), kind: "B", level: 4, failTasks: [1, 2, 3] });
    type AlertRow = { rule: string; severity: string; subject: string; message: string; acknowledged: boolean };
    const alertsOf = async (runId: string): Promise<AlertRow[]> => dataOf<AlertRow[]>(await call(request, "viewer", "GET", `/api/v1/monitor/projects/${f.projectId}/alerts?runId=${runId}`));
    for (let i = 0; i < 3; i += 1) {
      const started = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, {
        autonomyLevel: 4,
        tokenBudget: 100000,
        scope: { mode: "SELECTED", taskIds: [f.taskIds[i]] },
      });
      expect(started.status, `第 ${i + 1} 批 execute → ${JSON.stringify(started.json).slice(0, 300)}`).toBe(201);
      const runId = dataOf<{ id: string }>(started).id;
      const failed = await waitWithReview(request, runId, "FAILED");
      expect(failed.pendingReviews).toHaveLength(1);
      const review = failed.pendingReviews![0];
      expect(review.kind).toBe("ESCALATED");
      const rules = (await alertsOf(runId)).map((a) => a.rule);
      if (i < 2) {
        expect(review.reason, "前兩個失敗還不構成連續 3 個").not.toContain("CONSECUTIVE_FAILURES");
        expect(rules).not.toContain("CONSECUTIVE_FAILURES");
      } else {
        expect(review.reason).toMatch(/（連續 3 個任務失敗，已觸發 CONSECUTIVE_FAILURES 告警）$/);
        const hit = (await alertsOf(runId)).filter((a) => a.rule === "CONSECUTIVE_FAILURES");
        expect(hit).toHaveLength(1);
        expect(hit[0]).toMatchObject({ severity: "CRITICAL", subject: `goal:${f.goalIds[0]}`, message: "目標「基礎」連續 3 個任務失敗", acknowledged: false });
      }
      const rejected = await call(request, "operator", "POST", `/api/v1/executions/${runId}/review/${review.id}`, { decision: "REJECT" });
      expect(rejected.status).toBe(204);
    }
    for (const taskId of f.taskIds.slice(0, 3)) expect(await statusOf(request, "tasks", taskId), "REJECT 只關審核項，三個任務都維持 ESCALATED").toBe("ESCALATED");
  });
});
