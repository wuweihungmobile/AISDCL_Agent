import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { Engine, FIRST_TOKEN, GOAL_IDS, PROJECT_ID, TASKS, type EngineOptions } from "./execFixture";
import { collectConsoleErrors, compose, installApiMock, signInAs, snap, type MockHandler } from "./mockApi";

/**
 * 專案執行頁（設計稿畫面 7；契約 §1.2、§2、§4.2；PRD US-E-01～11）——route mock 版：
 * 以 execFixture.ts 的「假引擎」在記憶體裡模擬 console-api 的執行端點與 SSE 串流（框架格式、Last-Event-ID 重連、收斂快照、終態 204），
 * 由測試呼叫 startNext／finishCurrent／failCurrent 推進批次，頁面透過 REST＋SSE 看到變化。
 * 這裡驗「前端對契約形狀的行為」；與真後端對接的漂移由 QA 波另驗（見 README 與交卷〈給 QA 的提醒〉）。
 */
const EXEC_URL = `/projects/${PROJECT_ID}/execute`;
const EXECUTE_API = `/api/v1/projects/${PROJECT_ID}/execute`;
const [T1, T2] = TASKS;

type OpenOptions = EngineOptions & {
  role?: "ADMIN" | "OPERATOR" | "VIEWER";
  /** 在假引擎之前先看每個請求（覆寫某個端點的回應） */
  before?: MockHandler;
  /** 開頁前先佈置假引擎（例如已在進行中的批次） */
  seed?: (engine: Engine) => void;
};

/** 這個檔案裡每個測試開一台假引擎（含真的 SSE 伺服器）：測完在 afterEach 關掉，不留任何行程或埠。 */
let active: Engine | null = null;

async function open(page: Page, opts: OpenOptions = {}) {
  const engine = new Engine(opts);
  await engine.listen();
  active = engine;
  opts.seed?.(engine);
  await signInAs(page, opts.role ?? "OPERATOR");
  const unhandled: string[] = [];
  const tail: MockHandler = (call) => {
    unhandled.push(`${call.method} ${call.path}`);
    return undefined;
  };
  const { calls } = await installApiMock(page, compose(...(opts.before ? [opts.before] : []), engine.handler, tail));
  const errors = collectConsoleErrors(page);
  await page.goto(EXEC_URL);
  await expect(page.getByRole("heading", { name: "專案執行：AISDLC Core Platform" })).toBeVisible({ timeout: 60_000 });
  return { engine, calls, errors, unhandled };
}

const tone = (page: Page, taskIdx: number) => page.getByTestId(`dag-task-${TASKS[taskIdx].id}`);
/** 批次下拉的選項值是批次 id（selectOption 不接受正規表示式）。 */
const runIdOf = (engine: Engine, runNumber: number) => engine.runs.find((r) => r.runNumber === runNumber)?.id as string;
const executeCall = (calls: Array<{ method: string; path: string; body: unknown }>) => calls.find((c) => c.method === "POST" && c.path === EXECUTE_API);

/**
 * 收尾斷言：沒有主控台錯誤、沒有 mock 沒處理的請求。
 * dropsConnections＝這個測試故意切斷了串流連線：瀏覽器為每條被切斷的串流印一行網路層錯誤，那是預期內的；其餘任何錯誤仍算失敗。
 */
function expectClean(errors: string[], unhandled: string[], opts: { dropsConnections?: boolean } = {}) {
  const real = opts.dropsConnections ? errors.filter((e) => !/net::ERR_INCOMPLETE_CHUNKED_ENCODING/.test(e)) : errors;
  expect(real, "瀏覽器主控台不應有錯誤").toEqual([]);
  expect(unhandled, "mock 沒處理的請求").toEqual([]);
}

test.describe("專案執行頁（route mock＋假引擎 SSE）", () => {
  test.setTimeout(150_000);

  test.afterEach(async () => {
    await active?.close();
    active = null;
  });

  test("鎖定橫幅：未 signoff 時啟動鈕停用；前往審批 signoff 後橫幅消失、啟動鈕可按", async ({ page }) => {
    const { calls, errors, unhandled } = await open(page, { signedOff: false });
    await expect(page.getByTestId("execute-lock-banner")).toContainText("執行已鎖定 — 草案未 signoff，啟動回 409 Conflict");
    await expect(page.getByTestId("control-start")).toBeDisabled();
    await expect(page.getByTestId("control-start")).toHaveAttribute("title", /草案未經 signoff/);
    await expect(page.getByTestId("progress-card")).toContainText("尚未啟動執行");
    await expectNoA11yViolations(page, "執行頁（鎖定橫幅）");
    await snap(page, "07-execute-locked.png", { tall: true });

    await page.getByRole("button", { name: "前往審批" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("審批 signoff：專案");
    await dialog.getByRole("button", { name: "確認 signoff" }).click();

    await expect(page.getByTestId("execute-lock-banner")).toHaveCount(0);
    await expect(page.getByTestId("control-start")).toBeEnabled();
    const signoff = calls.find((c) => c.method === "POST" && c.path === `/api/v1/projects/${PROJECT_ID}/signoff`);
    expect(signoff?.body).toMatchObject({ approver: "operator" });
    expectClean(errors, unhandled);
  });

  test("唯讀角色（VIEWER）：啟動鈕停用並說明原因；進行中批次的暫停／取消與審核按鈕也停用", async ({ page }) => {
    const { errors, unhandled } = await open(page, {
      role: "VIEWER",
      seed: (engine) => {
        engine.begin(1);
        engine.startNext();
        engine.finishCurrent(); // Level 1：停在 TASK_CONFIRM
      },
    });
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    for (const id of ["control-resume", "control-cancel", "control-restore", "review-approve", "review-reject"]) {
      await expect(page.getByTestId(id), id).toBeDisabled();
    }
    await expect(page.getByTestId("control-resume")).toHaveAttribute("title", "權限不足（唯讀角色）");
    expectClean(errors, unhandled);
  });

  test("啟動：請求帶等級／預算／範圍；進度、DAG、日誌隨 SSE 即時更新；斷線重連帶 Last-Event-ID 且不重複；Token 達閾值變色；終態收工", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await open(page);
    await expect(page.getByTestId("control-start")).toBeEnabled();
    await expect(page.getByTestId("exec-level")).toHaveValue("4"); // 預設取專案的自治等級
    await expect(page.getByTestId("exec-budget")).toHaveValue("100,000"); // 預設取系統參數 globalTokenBudget（千分位，與設計稿一致）
    await expect(page.getByTestId("autonomy-hint")).toContainText("全自動執行，僅重試失敗後升級給人類");
    await snap(page, "07-execute-idle.png", { tall: true });

    await page.getByTestId("exec-budget").fill("1,500");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    expect(executeCall(calls)?.body).toEqual({ autonomyLevel: 4, tokenBudget: 1500, scope: { mode: "ALL" } });
    await expect(page.getByTestId("run-status")).toContainText("執行中");
    await expect(page.getByTestId("progress-tasks")).toHaveText("0 / 3 任務完成");
    await expect(page.getByTestId("exec-level")).toBeDisabled(); // 批次進行中：等級／預算／範圍是給下一批用的，先停用
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open");

    // 步驟 1 開始 → 完成：目前步驟、DAG 節點、日誌、Token 條
    engine.startNext();
    await expect(page.getByTestId("progress-current")).toContainText("目前：初始化（G1-T1）");
    await expect(tone(page, 0)).toHaveAttribute("data-tone", "active");
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");
    await expect(page.getByTestId("progress-tokens")).toContainText("Token: 1,240 / 1,500");
    await expect(page.getByTestId("token-warning")).toContainText("Token 使用量已達預算的 80%");
    await expect(tone(page, 0)).toHaveAttribute("data-tone", "done");
    await expect(page.getByTestId("log-line").filter({ hasText: "完成：初始化" })).toHaveCount(1);

    // 步驟 2：超出預算 → 紅色警示
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成");
    await expect(page.getByTestId("token-warning")).toContainText("Token 已超出預算");
    await expectNoA11yViolations(page, "執行頁（進行中：進度、DAG、日誌、Token 超出預算）");
    await snap(page, "07-execute-running.png", { tall: true });

    // 引擎原始輸出預設隱藏、可開；搜尋過濾顯示「符合 / 全部」行數
    await expect(page.getByTestId("log-line").filter({ hasText: "claude 執行" })).toHaveCount(0);
    await page.getByTestId("log-engine-toggle").click();
    await expect(page.getByTestId("log-line").filter({ hasText: "claude 執行 G1-T1" })).toHaveCount(1);
    await page.getByTestId("log-search").fill("完成：");
    await expect(page.getByTestId("log-count")).toHaveText(/^2 \/ \d+ 行$/);
    await page.getByTestId("log-search").fill("");

    // 兩條串流各一個連線，自始至終沒有斷過：只連了兩次（/logs、/metrics 各一），token 以 ?access_token= 帶 JWT，第一次連線沒有 Last-Event-ID
    expect(engine.openStreams).toBe(2);
    expect(engine.sseConnections.map((c) => [c.kind, c.status, c.token, c.lastEventId]).sort()).toEqual([
      ["logs", 200, FIRST_TOKEN, null],
      ["metrics", 200, FIRST_TOKEN, null],
    ]);
    await expect(page.getByTestId("log-line").filter({ hasText: "完成：初始化" })).toHaveCount(1);

    // 步驟 3 → 整批完成：終態；串流收工
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED");
    await expect(page.getByTestId("run-status")).toContainText("已完成");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "ended", { timeout: 20_000 });
    await expect(page.getByTestId("control-start")).toBeEnabled(); // 終態批次：可再啟動
    await expect(page.getByTestId("exec-level")).toBeEnabled();
    await expect(page.getByTestId("run-select")).toContainText("已完成"); // 批次列表也跟著狀態變化重抓（invalidateRuns），不是停在「執行中」
    await expectNoA11yViolations(page, "執行頁（批次完成）");
    await snap(page, "07-execute-completed.png", { tall: true });

    // 終態批次也可從斷點恢復（契約 §1.2.10）：三個斷點，最新那個已跑完所有步驟
    await page.getByTestId("control-restore").click();
    const options = page.getByTestId("checkpoint-option");
    await expect(options).toHaveCount(3);
    await expect(options.first()).toContainText("after-G2-T1");
    await expect(options.first()).toContainText("已跑完所有步驟，還原後重新確認收尾");
    await page.getByRole("button", { name: "取消" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expectClean(errors, unhandled);
  });

  test("範圍樹：展開目標、取消其中一個任務 → 請求為 SELECTED（goalIds＋taskIds），只跑所選任務", async ({ page }) => {
    const { calls, errors, unhandled } = await open(page);
    await expect(page.getByTestId("scope-all")).toHaveAttribute("data-state", "checked");
    await page.getByTestId(`scope-expand-${GOAL_IDS[0]}`).click();
    await expect(page.getByTestId(`scope-task-${T1.id}`)).toHaveAttribute("data-state", "checked");
    await page.getByTestId(`scope-task-${T2.id}`).click();
    await expect(page.getByTestId(`scope-task-${T2.id}`)).toHaveAttribute("data-state", "unchecked");
    await expect(page.getByTestId(`scope-goal-${GOAL_IDS[0]}`)).toHaveAttribute("data-state", "indeterminate");
    await expect(page.getByTestId("scope-all")).toHaveAttribute("data-state", "indeterminate");
    await snap(page, "07-execute-scope.png", { tall: true });

    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    expect(executeCall(calls)?.body).toEqual({
      autonomyLevel: 4,
      tokenBudget: 100000,
      scope: { mode: "SELECTED", goalIds: [GOAL_IDS[1]], taskIds: [T1.id] },
    });
    await expect(page.getByTestId("progress-tasks")).toHaveText("0 / 2 任務完成");
    await expect(tone(page, 1)).toHaveCount(0); // 未選的任務不在這個批次的 DAG
    await expect(tone(page, 0)).toBeVisible();
    await expect(tone(page, 2)).toBeVisible();
    expectClean(errors, unhandled);
  });

  test("啟動被後端 409 擋下：顯示原因與未審批的任務名稱，並可前往審批", async ({ page }) => {
    const { errors, unhandled } = await open(page, {
      before: (call) =>
        call.method === "POST" && call.path === EXECUTE_API
          ? {
              status: 409,
              error: {
                message: "草案未經人工審批，禁止執行",
                reason: "未經人工審批的草案不可執行",
                details: { unsignedGoalIds: [GOAL_IDS[1]], unsignedTaskIds: [T2.id] },
              },
            }
          : undefined,
    });
    await page.getByTestId("control-start").click();
    const panel = page.getByTestId("start-error");
    await expect(panel).toContainText("啟動失敗：");
    await expect(panel).toContainText("未審批的目標：核心");
    await expect(panel).toContainText(T2.id.slice(0, 8)); // 任務名稱只在展開過的目標才知道；沒載入就顯示 id 前 8 碼
    await expect(panel.getByRole("button", { name: "前往審批" })).toBeVisible();
    await expect(page.getByTestId("run-number")).toHaveCount(0); // 沒有啟動成功
    await snap(page, "07-execute-start-error.png", { tall: true });
    expectClean(errors, unhandled);
  });

  test("暫停（步驟邊界生效）→ 恢復 → 取消（確認對話框）", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await open(page);
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    engine.startNext();
    await expect(page.getByTestId("progress-current")).toContainText("初始化（G1-T1）");

    await page.getByTestId("control-pause").click();
    expect(calls.some((c) => c.method === "POST" && c.path.endsWith("/pause"))).toBe(true);
    // 後端回 RUNNING＋bridgeStatus=PAUSING：按鈕顯示處理中並停用，狀態標籤顯示「暫停中」
    await expect(page.getByTestId("control-pause")).toHaveText("暫停中…");
    await expect(page.getByTestId("control-pause")).toBeDisabled();
    await expect(page.getByTestId("run-status")).toContainText("暫停中");
    // 批次列表項也帶 bridgeStatus（契約 §1.2.2，C-11）：暫停後的重抓讓下拉的狀態字樣與選中批次的晶片都是「暫停中」
    await expect(page.getByTestId("run-select")).toContainText("暫停中");
    await expect(page.getByTestId("bridge-chip")).toHaveText("暫停中");
    await expect(page.getByTestId("bridge-chip")).toHaveAttribute("data-bridge", "PAUSING");

    engine.finishCurrent(); // 步驟邊界：真的停下
    await expect(page.getByTestId("run-status")).toContainText("已暫停");
    // 暫停原因只在 SSE 事件裡（假引擎的 REST 詳情沒有它），事件後的去抖重抓會把它換掉：先驗它，再驗列表的晶片
    await expect(page.getByTestId("run-reason")).toContainText("在步驟邊界暫停");
    await expect(page.getByTestId("bridge-chip")).toHaveCount(0); // 過渡結束（列表重抓後），晶片消失
    await expect(page.getByTestId("control-resume")).toBeEnabled();
    await expect(page.getByTestId("control-restore")).toBeEnabled();
    await expect(page.getByTestId("run-select")).toContainText("已暫停");
    await snap(page, "07-execute-paused.png", { tall: true });

    await page.getByTestId("control-resume").click();
    await expect(page.getByTestId("run-status")).toContainText("執行中");
    await expect(page.getByTestId("control-pause")).toHaveText("暫停");

    engine.startNext();
    await page.getByTestId("control-cancel").click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("確定取消這個執行批次？");
    await dialog.getByRole("button", { name: "確認取消" }).click();
    expect(calls.some((c) => c.method === "POST" && c.path.endsWith("/cancel"))).toBe(true);
    await expect(page.getByTestId("run-status")).toContainText("已取消");
    await expect(page.getByTestId("control-start")).toBeEnabled(); // 取消後可重新啟動
    expectClean(errors, unhandled);
  });

  test("從斷點恢復：暫停後對話框列出斷點（新→舊），選舊的一個還原後從該步繼續跑到結束", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await open(page, {
      seed: (e) => {
        e.begin(4);
        e.startNext();
        e.finishCurrent(); // 斷點 after-G1-T1
        e.startNext(); // 第 2 步進行中
      },
    });
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");
    await page.getByTestId("control-pause").click();
    engine.finishCurrent(); // 步驟邊界：停下，多一個斷點 after-G1-T2
    await expect(page.getByTestId("run-status")).toContainText("已暫停");
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成");

    await page.getByTestId("control-restore").click();
    await expect(page.getByTestId("checkpoint-dialog")).toBeVisible();
    const options = page.getByTestId("checkpoint-option");
    await expect(options).toHaveCount(2);
    await expect(options.first()).toContainText("after-G1-T2"); // 新的在前
    await expect(options.first()).toContainText("已完成 2 步");
    await expect(options.first()).toContainText("還原後從 G2-T1 繼續");
    await expect(options.nth(1)).toContainText("after-G1-T1");
    await expect(options.nth(1)).toContainText("已完成 1 步");
    await expect(options.nth(1)).toContainText("還原後從 G1-T2 繼續");
    await expect(options.nth(1)).toContainText("自動");
    await expect(page.getByTestId("checkpoint-confirm")).toBeDisabled(); // 先選一個才能確認
    await snap(page, "07-execute-checkpoint.png");

    await page.getByRole("radio", { name: "斷點 after-G1-T1" }).check();
    await page.getByTestId("checkpoint-confirm").click();
    const restore = calls.find((c) => c.method === "POST" && /\/restore\/[^/]+$/.test(c.path));
    expect(restore?.path, "restore 路徑帶選到的斷點 id").toContain(`/executions/${engine.latest.id}/restore/${engine.latest.checkpoints[0].id}`);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByTestId("run-status")).toContainText("執行中");
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");
    await expect(tone(page, 0)).toHaveAttribute("data-tone", "done");
    await expect(tone(page, 1)).toHaveAttribute("data-tone", "pending");

    engine.startNext();
    engine.finishCurrent();
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED");
    expectClean(errors, unhandled);
  });
  test("Level 1：每個任務後待確認——按鈕依 allowedDecisions 啟用，確認對話框說明後果，通過後續跑", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await open(page);
    await page.getByTestId("exec-level").selectOption("1");
    await expect(page.getByTestId("autonomy-hint")).toContainText("每個任務執行前需人類確認");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    expect(executeCall(calls)?.body).toMatchObject({ autonomyLevel: 1 });

    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("run-status")).toContainText("已暫停");
    const row = page.getByTestId("review-row");
    await expect(row).toHaveCount(1);
    await expect(row).toHaveAttribute("data-kind", "TASK_CONFIRM");
    await expect(page.getByTestId("review-kind")).toHaveText("確認任務");
    await expect(page.getByTestId("review-reason")).toContainText("Level 1：請確認是否繼續執行任務「設定」");
    await expect(page.getByTestId("review-count")).toHaveText("1");
    await expect(page.getByTestId("review-approve")).toBeEnabled();
    await expect(page.getByTestId("review-reject")).toBeEnabled();
    await expect(page.getByTestId("review-retry")).toBeDisabled();
    await expect(page.getByTestId("review-skip")).toBeDisabled();
    await expect(page.getByTestId("run-select")).toContainText("已暫停");
    await snap(page, "07-execute-review.png", { tall: true });

    await page.getByTestId("review-approve").click();
    await expect(page.getByTestId("review-dialog")).toContainText("Level 1：請確認是否繼續執行任務「設定」");
    await expect(page.getByTestId("review-consequence")).toContainText("批次會恢復執行，開始下一個任務。");
    await page.getByTestId("review-comment").fill("OK 繼續");
    await page.getByTestId("review-confirm").click();
    const review = calls.find((c) => c.method === "POST" && /\/review\/[^/]+$/.test(c.path));
    expect(review?.body).toEqual({ decision: "APPROVE", comment: "OK 繼續" });
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByTestId("run-status")).toContainText("執行中");
    await expect(page.getByTestId("review-empty")).toBeVisible();

    // 拒絕＝取消批次（先確認對話框顯示後果）
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    await page.getByTestId("review-reject").click();
    await expect(page.getByTestId("review-consequence")).toContainText("批次會被取消");
    await page.getByTestId("review-confirm").click();
    await expect(page.getByTestId("run-status")).toContainText("已取消");
    expectClean(errors, unhandled);
  });

  test("Level 3：目標完成審核（GOAL_COMPLETED）——可通過／重試／拒絕，不可跳過；通過後續跑到結束", async ({ page }) => {
    const { engine, errors, unhandled } = await open(page);
    await page.getByTestId("exec-level").selectOption("3");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");

    engine.startNext();
    engine.finishCurrent(); // 同一目標內，不停
    engine.startNext();
    engine.finishCurrent(); // 目標「基礎」做完 → 待審核
    await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "GOAL_COMPLETED");
    await expect(page.getByTestId("review-kind")).toHaveText("目標完成審核");
    await expect(page.getByTestId("review-approve")).toBeEnabled();
    await expect(page.getByTestId("review-retry")).toBeEnabled();
    await expect(page.getByTestId("review-reject")).toBeEnabled();
    await expect(page.getByTestId("review-skip")).toBeDisabled();
    await expect(page.getByTestId("review-skip")).toHaveAttribute("title", "這個審核項不允許此決定");

    await page.getByTestId("review-approve").click();
    await page.getByTestId("review-confirm").click();
    await expect(page.getByTestId("run-status")).toContainText("執行中");
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED");
    expectClean(errors, unhandled);
  });

  test("任務失敗升級（ESCALATED）：RETRY 從斷點還原同一批次後重跑成功", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await open(page);
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    engine.startNext();
    engine.finishCurrent();
    engine.startNext();
    engine.failCurrent(engine.latest, "測試未通過");

    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "FAILED");
    await expect(page.getByTestId("run-reason")).toContainText("引擎升級（ESCALATION）：測試未通過");
    await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "ESCALATED");
    await expect(page.getByTestId("review-kind")).toHaveText("需人工介入");
    await expect(page.getByTestId("review-approve")).toBeDisabled(); // ESCALATED 沒有「通過」
    await expect(page.getByTestId("review-retry")).toBeEnabled();
    await expect(page.getByTestId("review-skip")).toBeEnabled();
    await expect(page.getByTestId("review-reject")).toBeEnabled();
    await expect(tone(page, 1)).toHaveAttribute("data-tone", "failed");
    await expect(page.getByTestId("log-line").filter({ hasText: "失敗：設定" })).toHaveCount(1);
    // 同一件事在日誌裡出現三種行：引擎告警、狀態變化（FAILED）、待審核（review-request）
    await expect(page.locator('[data-testid="log-line"][data-kind="alert"]')).toContainText("告警（嚴重）：引擎升級（ESCALATION）：測試未通過");
    await expect(page.locator('[data-testid="log-line"][data-kind="status"]').last()).toContainText("狀態：失敗");
    await expect(page.locator('[data-testid="log-line"][data-kind="review"]')).toContainText("待審核：任務「設定」重試 1 次仍失敗");
    await expect(page.getByTestId("run-select")).toContainText("失敗");
    await snap(page, "07-execute-escalated.png", { tall: true });

    await page.getByTestId("review-retry").click();
    await expect(page.getByTestId("review-consequence")).toContainText("從失敗步驟之前的斷點還原後重跑");
    await page.getByTestId("review-confirm").click();
    const review = calls.find((c) => c.method === "POST" && /\/review\/[^/]+$/.test(c.path));
    expect(review?.body).toEqual({ decision: "RETRY" });
    // 同一個批次被還原（沒有後續批次）：狀態回到執行中，審核項消失
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("run-status")).toContainText("執行中");
    await expect(page.getByTestId("review-empty")).toBeVisible();
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");

    // 串流在 FAILED 時已收工，還原後由前端重新連線，之後的事件照常到
    engine.startNext();
    engine.finishCurrent();
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED");
    expectClean(errors, unhandled);
  });

  test("任務失敗升級（ESCALATED）：SKIP 另開後續批次（X-Follow-Up-Run-Id）並自動切過去", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await open(page);
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    engine.startNext();
    engine.finishCurrent();
    engine.startNext();
    engine.failCurrent(engine.latest, "測試未通過");
    await expect(page.getByTestId("review-row")).toHaveAttribute("data-kind", "ESCALATED");

    await page.getByTestId("review-skip").click();
    await expect(page.getByTestId("review-consequence")).toContainText("另開一個後續批次");
    await page.getByTestId("review-confirm").click();
    const review = calls.find((c) => c.method === "POST" && /\/review\/[^/]+$/.test(c.path));
    expect(review?.body).toEqual({ decision: "SKIP" });

    await expect(page.getByTestId("run-number")).toHaveText("Run #2");
    await expect(page.getByTestId("run-status")).toContainText("執行中");
    await expect(page.getByTestId("progress-tasks")).toHaveText("0 / 1 任務完成"); // 失敗的任務跳過、已完成的不重跑，只剩第 3 個
    const select = page.getByTestId("run-select");
    await expect(select.locator("option")).toHaveCount(2);
    await expect(select).toHaveValue(engine.latest.id);
    await expect(select.locator("option").first()).toContainText("Run #2（最新）");

    // 後續批次獨立地跑完；切回 Run #1 看到的是終態（按鈕是啟動／恢復，不再有暫停）
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED");
    await select.selectOption({ index: 1 });
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "FAILED");
    await expect(page.getByTestId("control-restore")).toBeDisabled(); // 只能還原專案最新的批次
    expectClean(errors, unhandled);
  });

  test("斷線重連：連線被切斷時瀏覽器自動重連並帶 Last-Event-ID，斷線期間的事件補齊且不重複", async ({ page }) => {
    const { engine, errors, unhandled } = await open(page);
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open");
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");

    const before = engine.sseConnections.length;
    engine.dropStreams();
    engine.startNext(); // 斷線期間，引擎照常工作
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open");
    const retries = engine.sseConnections.slice(before);
    expect(retries.filter((c) => c.kind === "logs" && c.status === 200 && c.lastEventId !== null)).toHaveLength(1);
    expect(retries.filter((c) => c.kind === "metrics" && c.status === 200 && c.lastEventId !== null)).toHaveLength(1);
    // 重放的事件（含已看過的）依 (seq, n) 去重：每一行只出現一次
    for (const name of ["初始化", "設定"]) {
      await expect(page.getByTestId("log-line").filter({ hasText: `完成：${name}` })).toHaveCount(1);
    }
    expectClean(errors, unhandled, { dropsConnections: true });
  });

  test("token 過期（401）：EventSource 看不到狀態碼，前端問 REST 確認批次還活著、換新 token 後重建連線並補齊", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await open(page);
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open");

    const before = engine.sseConnections.length;
    engine.expireTokens();
    engine.dropStreams();
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open", { timeout: 30_000 });
    const attempts = engine.sseConnections.slice(before);
    expect(
      attempts.some((c) => c.status === 401 && c.token === FIRST_TOKEN),
      "舊 token 被拒",
    ).toBe(true);
    expect(
      attempts.some((c) => c.status === 200 && c.token !== FIRST_TOKEN && c.token?.startsWith(FIRST_TOKEN)),
      "換新 token 後連上",
    ).toBe(true);
    expect(calls.some((c) => c.method === "POST" && c.path === "/api/v1/auth/refresh")).toBe(true);
    await expect(page.getByTestId("log-line").filter({ hasText: "完成：初始化" })).toHaveCount(1);
    expectClean(errors, unhandled, { dropsConnections: true });
  });

  test("後端暫時不可用（503）：連續失敗兩次後以 REST 回補步驟，再重建連線；日誌不丟、不重複", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await open(page);
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open");
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");

    const before = engine.sseConnections.length;
    engine.refuseStreams(4); // /logs 與 /metrics 各被拒兩次
    engine.dropStreams();
    engine.startNext(); // 斷線期間又完成一步：只能靠 REST 回補與重連後的重放補上
    engine.finishCurrent();
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "reconnecting");
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open", { timeout: 40_000 });
    expect(engine.sseConnections.slice(before).filter((c) => c.status === 503)).toHaveLength(4);
    const backfill = calls.filter((c) => c.method === "GET" && c.path.endsWith("/steps") && c.query.has("afterSeq"));
    expect(backfill.length, "連續失敗兩次以上才改用 REST 回補（steps?afterSeq=）").toBeGreaterThan(0);
    for (const name of ["初始化", "設定"]) {
      await expect(page.getByTestId("log-line").filter({ hasText: `完成：${name}` })).toHaveCount(1);
    }
    expectClean(errors, unhandled, { dropsConnections: true });
  });

  test("後端整個暫時不可用（nginx 回 502；DEF-AC-007）：換新失敗不登出——session 原封不動、留在執行頁、狀態點「重新連線中」；恢復後換新並自動連回，日誌不丟不重複", async ({ page }) => {
    const { engine, calls, errors, unhandled } = await open(page);
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open");
    engine.startNext();
    engine.finishCurrent();
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");
    const session = () => page.evaluate(() => window.sessionStorage.getItem("aisdlc.console.session"));
    const before = await session();
    expect(before).toContain("mock-refresh-token");

    // 後端整個掛掉：REST、換新、串流一律 502；舊 token 同時失效（恢復後要靠換新才連得回來）；既有連線被切斷
    const refreshCount = () => calls.filter((c) => c.method === "POST" && c.path === "/api/v1/auth/refresh").length;
    engine.setOutage(true);
    engine.expireTokens();
    engine.dropStreams();
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "reconnecting");
    // 等到「強制換新被 502」至少發生一次——缺陷版本就在這一刻清掉 session、把頁面導向 /login
    await expect.poll(refreshCount, { timeout: 30_000 }).toBeGreaterThan(0);
    await page.waitForTimeout(3_000);
    expect(new URL(page.url()).pathname, "不得被導向 /login").toBe(EXEC_URL);
    expect(await session(), "session 原封不動（沒清、也沒被換掉）").toBe(before);
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "reconnecting"); // 不是「連線失敗」
    expect(refreshCount()).toBeGreaterThan(0);

    // 斷線期間引擎照常工作；後端恢復
    engine.startNext();
    engine.finishCurrent();
    engine.setOutage(false);
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open", { timeout: 60_000 });
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成");
    expect(new URL(page.url()).pathname).toBe(EXEC_URL);
    expect(await session(), "恢復後換新成功：session 換成新的 token").not.toBe(before);
    expect(await session()).toMatch(/"refreshToken":"mock-refresh-token-\d+"/); // 換發的 refresh token（編號依換新次數，兩條串流可能各換一次）
    expect(
      engine.sseConnections.some((c) => c.status === 200 && c.token !== FIRST_TOKEN && c.token?.startsWith(FIRST_TOKEN)),
      "用換發的新 token 連上",
    ).toBe(true);
    expect(engine.sseConnections.filter((c) => c.status === 502).length, "停機期間串流被 502 擋下").toBeGreaterThan(0);
    for (const name of ["初始化", "設定"]) {
      await expect(page.getByTestId("log-line").filter({ hasText: `完成：${name}` })).toHaveCount(1);
    }
    expectClean(errors, unhandled, { dropsConnections: true });
  });

  test("重新整理：批次已在進行中時，REST 當底＋SSE 重播還原進度、DAG 與日誌，不重複", async ({ page }) => {
    const { engine, errors, unhandled } = await open(page, {
      seed: (e) => {
        e.begin(4);
        e.startNext();
        e.finishCurrent();
        e.startNext(); // 第 2 步進行中
      },
    });
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");
    await expect(page.getByTestId("progress-current")).toContainText("設定（G1-T2）");
    await expect(page.getByTestId("exec-level")).toBeDisabled();
    await expect(tone(page, 0)).toHaveAttribute("data-tone", "done");
    await expect(tone(page, 1)).toHaveAttribute("data-tone", "active");
    await expect(tone(page, 2)).toHaveAttribute("data-tone", "pending");
    // 首次連線沒有 Last-Event-ID：伺服器重播最後 200 則，前端依 (seq, n) 去重——每一行只出現一次
    await expect(page.getByTestId("log-line").filter({ hasText: "完成：初始化" })).toHaveCount(1);
    await expect(page.getByTestId("log-line").filter({ hasText: "開始：設定" })).toHaveCount(1);
    expect(engine.sseConnections[0]?.lastEventId).toBeNull();
    await expect(page.getByTestId("control-pause")).toBeEnabled();
    expectClean(errors, unhandled);
  });

  test("引擎能力晶片（契約 E-21，v1.3 D-11）：有金鑰、Level 7 啟動 → 兩枚都「已啟用」；自演化寫明「僅提案」、tooltip 說明不自動套用；axe 零違規", async ({ page }) => {
    const { calls, errors, unhandled } = await open(page);
    await expect(page.getByTestId("engine-capabilities")).toHaveCount(0); // 還沒有批次：沒有晶片
    await page.getByTestId("exec-level").selectOption("7");
    await expect(page.getByTestId("autonomy-hint")).toContainText("審核閘行為同 Level 5");
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    expect(executeCall(calls)?.body).toMatchObject({ autonomyLevel: 7 });

    const group = page.getByRole("group", { name: "引擎能力" });
    await expect(group.getByTestId("engine-capability")).toHaveText(["自動突變：已啟用", "自演化（僅提案）：已啟用"]);
    const mutation = group.locator('[data-capability="autoMutation"]');
    const evolution = group.locator('[data-capability="selfEvolution"]');
    await expect(mutation).toHaveAttribute("data-state", "ENABLED");
    await expect(mutation).toHaveAttribute("title", /Brain 逐步校正：失敗步驟先由 Brain 改寫再重試/);
    await expect(evolution).toHaveAttribute("data-state", "ENABLED");
    await expect(evolution).toHaveAttribute("title", /僅提案、不自動套用/);
    await expectNoA11yViolations(page, "執行頁（引擎能力晶片：已啟用）");
    expectClean(errors, unhandled);
  });

  test("引擎能力晶片：各批次建立時凍結——有金鑰的 Level 4 批次是「自動突變關閉」「自演化（僅提案）已啟用」，Level 7 批次兩枚都已啟用", async ({ page }) => {
    const { engine, errors, unhandled } = await open(page, {
      seed: (e) => {
        e.begin(4);
        for (let i = 0; i < 3; i++) {
          e.startNext();
          e.finishCurrent();
        }
        e.begin(7);
        e.startNext();
      },
    });
    const chips = page.getByTestId("engine-capability");
    await expect(page.getByTestId("run-number")).toHaveText("Run #2"); // 預設看最新批次
    await expect(chips).toHaveText(["自動突變：已啟用", "自演化（僅提案）：已啟用"]);

    await page.getByTestId("run-select").selectOption(runIdOf(engine, 1));
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(chips).toHaveText(["自動突變：關閉", "自演化（僅提案）：已啟用"]); // 等級 4、有金鑰：自演化沒有開關，有金鑰就是只提案
    await expect(chips.nth(0)).toHaveAttribute("data-state", "OFF");
    await expect(chips.nth(1)).toHaveAttribute("title", /與設定和自治等級無關/);
    await expectNoA11yViolations(page, "執行頁（引擎能力晶片：關閉＋已啟用）");
    expectClean(errors, unhandled);
  });

  test("引擎能力晶片：沒有金鑰時，Level 7 批次是「無金鑰不可用」×2、Level 4 批次是「關閉」×2（批次照常執行，不報錯）", async ({ page }) => {
    const { engine, errors, unhandled } = await open(page, {
      apiKey: false,
      seed: (e) => {
        e.begin(4);
        for (let i = 0; i < 3; i++) {
          e.startNext();
          e.finishCurrent();
        }
        e.begin(7);
        e.startNext();
      },
    });
    const chips = page.getByTestId("engine-capability");
    await expect(page.getByTestId("run-number")).toHaveText("Run #2");
    await expect(chips).toHaveText(["自動突變：無金鑰不可用", "自演化：無金鑰不可用"]);
    await expect(chips.nth(0)).toHaveAttribute("data-state", "UNAVAILABLE_NO_API_KEY");
    await expect(chips.nth(0)).toHaveAttribute("title", /沒有金鑰可送：批次照常執行，只是沒有 Brain/);
    await expect(chips.nth(1)).toHaveAttribute("title", /AI 演化提案不會發生/);
    await expect(page.getByTestId("run-status")).toContainText("執行中"); // 沒有金鑰不影響批次執行
    await expectNoA11yViolations(page, "執行頁（引擎能力晶片：無金鑰不可用）");

    await page.getByTestId("run-select").selectOption(runIdOf(engine, 1));
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(chips).toHaveText(["自動突變：關閉", "自演化：關閉"]);
    await expectNoA11yViolations(page, "執行頁（引擎能力晶片：關閉）");
    expectClean(errors, unhandled);
  });

  test("引擎能力晶片：V10 之前建立的批次（回應沒有 engineCapabilities）不顯示晶片，進度卡其餘照常", async ({ page }) => {
    const { errors, unhandled } = await open(page, {
      legacyRuns: true,
      seed: (e) => {
        e.begin(4);
        e.startNext();
        e.finishCurrent();
        e.startNext();
      },
    });
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect(page.getByTestId("progress-tasks")).toHaveText("1 / 3 任務完成");
    await expect(page.getByTestId("engine-capabilities")).toHaveCount(0);
    await expect(page.getByTestId("engine-capability")).toHaveCount(0);
    expectClean(errors, unhandled);
  });

  test("DAG 全螢幕（契約 E-22，v1.4 D-20）：「全螢幕」→ 覆蓋層尺寸等於視窗；「結束全螢幕」與 Esc 都能結束、焦點回到「全螢幕」鈕；SSE 節點更新與展開／收合在全螢幕內照常、狀態進出保留；axe 零違規", async ({
    page,
  }) => {
    const { engine, errors, unhandled } = await open(page, {
      seed: (e) => {
        e.begin(4);
        e.startNext();
        e.finishCurrent();
        e.startNext(); // 第 2 步進行中
      },
    });
    const fsOpen = page.getByTestId("dag-fullscreen-open");
    const overlay = page.getByTestId("dag-fullscreen");
    await expect(tone(page, 1)).toHaveAttribute("data-tone", "active");
    await expect(fsOpen).toHaveText("全螢幕");
    await expect(fsOpen).toHaveAttribute("aria-pressed", "false");
    await expect(overlay).toHaveCount(0);

    // 進入全螢幕：頁面內覆蓋層，尺寸等於視窗（不是瀏覽器 Fullscreen API）
    await fsOpen.click();
    await expect(overlay).toBeVisible();
    await expect(page.getByRole("dialog", { name: "DAG 依賴視覺化" })).toBeVisible();
    const viewport = page.viewportSize()!;
    await expect
      .poll(async () => {
        const b = await overlay.boundingBox();
        return b ? [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)] : null;
      })
      .toEqual([0, 0, viewport.width, viewport.height]);
    expect(await page.evaluate(() => [window.innerWidth, window.innerHeight])).toEqual([viewport.width, viewport.height]);
    expect(await page.evaluate(() => document.fullscreenElement), "不使用瀏覽器 Fullscreen API").toBeNull();
    const exit = page.getByRole("button", { name: "結束全螢幕" });
    await expect(exit).toHaveAttribute("aria-pressed", "true");
    await expect(exit).toHaveAttribute("data-testid", "dag-fullscreen-exit");
    await expect(overlay.getByTestId("dag-scroll")).toHaveAttribute("tabindex", "0");
    await expect(page.getByTestId("dag-scroll")).toHaveCount(1); // 圖形只掛一份

    // SSE 驅動的節點狀態在全螢幕期間照常更新（節點就在覆蓋層裡）
    await expect(overlay.getByTestId(`dag-task-${TASKS[1].id}`)).toHaveAttribute("data-tone", "active");
    engine.finishCurrent();
    await expect(tone(page, 1)).toHaveAttribute("data-tone", "done");
    engine.startNext();
    await expect(tone(page, 2)).toHaveAttribute("data-tone", "active");
    await expect(overlay.getByTestId(`dag-task-${TASKS[2].id}`)).toBeVisible();

    // 全螢幕內的「收合任務／展開任務」可用；收合後回到卡內仍是收合（狀態保留）
    await overlay.getByTestId("dag-fs-toggle").click();
    await expect(overlay.getByTestId("dag-fs-toggle")).toHaveText("展開任務");
    await expect(tone(page, 0)).toHaveCount(0);
    await expect(overlay.getByTestId(`dag-goal-${GOAL_IDS[0]}`)).toBeVisible(); // 目標節點還在

    // Esc 結束：覆蓋層消失、焦點回到「全螢幕」鈕
    await page.keyboard.press("Escape");
    await expect(overlay).toHaveCount(0);
    await expect(fsOpen).toBeFocused();
    await expect(fsOpen).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByTestId("dag-toggle")).toHaveText("展開任務");
    await expect(tone(page, 0)).toHaveCount(0);
    await page.getByTestId("dag-toggle").click(); // 卡內展開：節點回來，狀態是即時的最新值
    await expect(tone(page, 0)).toHaveAttribute("data-tone", "done");
    await expect(tone(page, 2)).toHaveAttribute("data-tone", "active");

    // 再進一次，用「結束全螢幕」鈕結束；層內掃 axe（含 scrollable-region-focusable、焦點順序、對比）
    await fsOpen.click();
    await expect(overlay).toBeVisible();
    await expectNoA11yViolations(page, "執行頁（DAG 全螢幕）");
    await page.getByRole("button", { name: "結束全螢幕" }).click();
    await expect(overlay).toHaveCount(0);
    await expect(fsOpen).toBeFocused();
    expectClean(errors, unhandled);
  });
});
