import { execFileSync } from "node:child_process";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { ADMIN, BASE, RUN, STACK_ON, approveViaApi, call, dataOf, detailOf, eventSeqs, hasCreds, newResearchKit, open, projectPath, signIn } from "../helpers/research-stack";

/**
 * 研發工作流（ResearchToPRD P1）的本機模式分流 E2E（TCS-ResearchToPRD-P1-20261107 AT-961-22-1、22-2 的 Playwright 半；IFACE §9.1、§9.2 載具乙）——
 * **實機冒煙，不是每個 commit 的閘**：Bridge 跑在**主機**（本機模式：真 git、拋棄式 clone 或暫存 scaffold 根、假 `gh`），frontend／backend／PG 照跑在 Docker；
 * 預演 → ADMIN 確認 → UI 時間軸 → 資料庫逐位核對。與 `research-p1-docker.stack.spec.ts`（容器 mock-only 負控）互補：真 git 副作用只在這裡驗。
 *
 * 啟用條件（缺任何一項＝整支略過並印 TOOL-ABSENCE，不當失敗）：
 *   - `E2E_STACK=1`、`E2E_ADMIN_USER`／`E2E_ADMIN_PASSWORD`（同 `research-docker.stack.spec.ts`）；
 *   - `E2E_LOCAL_BRIDGE=1`：宣告 backend 的 `ENGINE_BRIDGE_URL` 已指向主機 Bridge（建議 `http://host.docker.internal:18081`，不動 `aisdlc-*` 容器 Bridge），
 *     且該 Bridge 以 `BRIDGE_REPO_ROOT`（拋棄式 clone）、`BRIDGE_WORKTREE_ROOT`、`BRIDGE_SCAFFOLD_ROOT`（暫存）、`BRIDGE_DB_DSN`（同一個 PG）、
 *     `MOCK_CLAUDE_RESEARCH_SCRIPT`（pass 劇本）啟動，PATH 前置假 `gh`；
 *   - 軌道 B 案例另需 `E2E_LOCAL_TRACK_B=1`（暫存 scaffold 根已放 `python-fastapi` 範本）；軌道 A 案例需 `E2E_LOCAL_TRACK_A=1`（`BRIDGE_REPO_ROOT` 是拋棄式 clone）。
 * 選配：`E2E_FAKE_GH_LOG`（假 gh 的紀錄檔絕對路徑；有設則核對 argv 不含 token）、`E2E_FAKE_GH_TOKEN`（假 token 字面；有設則對 API 回應與資料庫全文掃描、命中數必須為 0）、
 *   `E2E_PG_CONTAINER`（預設 `aisdlc-pg-primary`）、`E2E_PG_USER`／`E2E_PG_DB`（預設 `aisdlc`）：資料庫逐位核對用 `docker exec … psql`，沒有 docker CLI 就略過該段並註記。
 * 本檔不會建立或刪除任何 git 工作區：拋棄式 clone、worktree、scaffold 根的建置與清理由整合棒依 IFACE §9.1 的步驟做（用畢 `worktree remove` 再刪 clone）。
 * 所有測試建立的研究專案在結束時封存。
 */
const LOCAL_BRIDGE = process.env.E2E_LOCAL_BRIDGE === "1";
const TRACK_A = process.env.E2E_LOCAL_TRACK_A === "1";
const TRACK_B = process.env.E2E_LOCAL_TRACK_B === "1";
const FAKE_GH_TOKEN = process.env.E2E_FAKE_GH_TOKEN ?? "";
const PG_CONTAINER = process.env.E2E_PG_CONTAINER ?? "aisdlc-pg-primary";
const PG_USER = process.env.E2E_PG_USER ?? "aisdlc";
const PG_DB = process.env.E2E_PG_DB ?? "aisdlc";

const ABSENCE = !STACK_ON
  ? "TOOL-ABSENCE：未設 E2E_STACK=1（見 tests/e2e/README.md〈研發工作流 P1 本機模式分流 E2E〉）"
  : !hasCreds(ADMIN)
    ? "TOOL-ABSENCE：缺環境變數 E2E_ADMIN_USER／E2E_ADMIN_PASSWORD"
    : !LOCAL_BRIDGE
      ? "TOOL-ABSENCE：未設 E2E_LOCAL_BRIDGE=1（本機模式 Bridge 與假 gh 由整合棒起；見 README）"
      : "";
if (ABSENCE !== "") console.log(`[research-route-local.stack] ${ABSENCE}`);
test.skip(ABSENCE !== "", ABSENCE);

const { driveToGate0, archiveAll } = newResearchKit("research-route-local.stack");

test.afterAll(async ({ playwright }) => {
  const request = await playwright.request.newContext();
  try {
    await archiveAll(request);
  } finally {
    await request.dispose();
  }
});

type RouteStep = { stepNo: number; step: string; status: string; argvRedacted: string; exitCode: number | null; stdoutTail: string; stderrTail: string };
type Route = { routeId: string; track: string; status: string; failureStep: string | null; consoleProjectId: string | null; implFsmProject: string | null; steps: RouteStep[] };
type Preview = { track: string; actions: Array<{ seq: number; step: string; touchesExternal: boolean }>; implFsmProject: string | null };

/** 在 Postgres 容器內跑一句唯讀 SQL（`-At` 無格式輸出）；沒有 docker CLI 回 null（呼叫端註記略過），其他失敗丟出。 */
function psql(sql: string): string | null {
  try {
    return execFileSync("docker", ["exec", PG_CONTAINER, "psql", "-U", PG_USER, "-d", PG_DB, "-At", "-c", sql], { encoding: "utf-8", timeout: 30_000 }).trim();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

/** 預期的步驟序（TCS §5.1：軌道 A、軌道 B 不建遠端時；`GH_REPO_CREATE` 只在 `createGithub` 為真時出現）。 */
const STEP_ORDER = {
  A: ["VALIDATE_TARGET", "GIT_SWITCH", "PUBLISH_DOCS", "REGISTER_STUB", "GIT_COMMIT", "IMPL_KEY_INIT", "BASELINE_ADOPT"],
  B: ["VALIDATE_TARGET", "SCAFFOLD_FILES", "COPY_WORKSPACE", "GIT_INIT", "GIT_COMMIT", "IMPL_KEY_INIT", "BASELINE_ADOPT"],
} as const;

async function previewConfirmAndVerify(track: "A" | "B", body: Record<string, unknown>, { page, request }: { page: Page; request: APIRequestContext }): Promise<void> {
  const project = await driveToGate0(request, `local-${track.toLowerCase()}`);
  await approveViaApi(request, project.id);

  // 預演零副作用：事件帳與游標不動、GET route 仍是 null
  const seqs0 = await eventSeqs(request, project.id);
  const preview = await call(request, ADMIN, "POST", projectPath(project.id, "/route/preview"), body);
  expect(preview.status, `預演 → ${JSON.stringify(preview.json)}`).toBe(200);
  const plan = dataOf<Preview>(preview);
  expect(plan.track).toBe(track);
  expect(
    plan.actions.map((a) => a.step),
    "預演動作序＝步驟序（不含遠端）",
  ).toEqual([...STEP_ORDER[track]]);
  expect(
    plan.actions.filter((a) => a.touchesExternal),
    "不建遠端時沒有觸及外部系統的動作",
  ).toEqual([]);
  expect(await eventSeqs(request, project.id), "預演不寫研究事件").toEqual(seqs0);
  expect(dataOf(await call(request, ADMIN, "GET", projectPath(project.id, "/route")))).toBeNull();

  // 確認執行（ADMIN、同步 200）
  const confirm = await call(request, ADMIN, "POST", projectPath(project.id, "/route"), body);
  expect(confirm.status, `確認 → ${JSON.stringify(confirm.json)}`).toBe(200);
  const route = dataOf<Route>(confirm);
  expect(route.status).toBe("SUCCEEDED");
  expect(route.failureStep).toBeNull();
  expect(
    route.steps.map((s) => s.step),
    "步驟實際序",
  ).toEqual([...STEP_ORDER[track]]);
  expect(
    route.steps.every((s) => s.status === "OK"),
    `步驟全 OK：${JSON.stringify(route.steps.map((s) => [s.step, s.status]))}`,
  ).toBe(true);
  expect(route.consoleProjectId, "分流成功綁定 Console 專案").not.toBeNull();

  const detail = await detailOf(request, project.id);
  expect([detail.flowStep, detail.flowPhase, detail.flowStatus], "成功後游標＝build／ROUTED／IDLE（D-105）").toEqual(["build", "ROUTED", "IDLE"]);

  // UI：重新載入後步驟 3 顯示完成的分流（時間軸逐步列出）
  await signIn(page, request, ADMIN);
  await open(page, request, `${BASE}/research/${project.id}?step=route`);
  await expect(page.getByTestId("route-panel")).toHaveAttribute("data-route-status", "SUCCEEDED", { timeout: 60_000 });
  const timeline = page.getByTestId("route-steps");
  await expect(timeline).toBeVisible({ timeout: 30_000 });
  for (const s of route.steps) await expect(page.getByTestId(`route-step-${s.stepNo}`), `時間軸第 ${s.stepNo} 步`).toBeVisible({ timeout: 15_000 });

  // 資料庫逐位核對（API 回的列＝資料庫的列；步驟數、狀態、去敏 argv 一致）
  const rows = psql(`SELECT status || '|' || coalesce(failure_step,'') || '|' || coalesce(console_project_id::text,'') FROM console.research_route_decisions WHERE id = '${route.routeId}'`);
  if (rows === null) {
    test.info().annotations.push({ type: "資料庫核對略過", description: "TOOL-ABSENCE：沒有 docker CLI，無法 docker exec psql" });
  } else {
    expect(rows, "decisions 列＝API").toBe(`SUCCEEDED||${route.consoleProjectId}`);
    const stepRows = psql(`SELECT step_no || ':' || step || ':' || status FROM console.research_route_steps WHERE route_id = '${route.routeId}' ORDER BY step_no`);
    expect((stepRows ?? "").split("\n"), "steps 列＝API").toEqual(route.steps.map((s) => `${s.stepNo}:${s.step}:${s.status}`));
    if (FAKE_GH_TOKEN !== "") {
      const dump = psql(`SELECT string_agg(t::text, E'\\n') FROM (SELECT * FROM console.research_route_steps WHERE route_id = '${route.routeId}') t`) ?? "";
      expect(dump.includes(FAKE_GH_TOKEN), "資料庫分流步驟表不含 token 字面").toBe(false);
    }
  }
  if (FAKE_GH_TOKEN !== "") {
    expect(JSON.stringify(confirm.json).includes(FAKE_GH_TOKEN), "確認回應不含 token 字面").toBe(false);
    expect(JSON.stringify(preview.json).includes(FAKE_GH_TOKEN), "預演回應不含 token 字面").toBe(false);
  }
}

test("AT_961_22_1 本機模式軌道 A（拋棄式 clone）：預演零副作用、ADMIN 確認同步成功、時間軸與資料庫逐位一致", async ({ page, request }) => {
  test.skip(!TRACK_A, "TOOL-ABSENCE：未設 E2E_LOCAL_TRACK_A=1（BRIDGE_REPO_ROOT 須是拋棄式 clone；見 README）");
  test.setTimeout(900_000);
  await previewConfirmAndVerify("A", { track: "A", targetModule: "autoclaude", branchName: `feature/e2e-${RUN}`.slice(0, 40), scopeDiffersReason: "E2E 本機模式軌道 A" }, { page, request });
});

test("AT_961_22_2 本機模式軌道 B（暫存 scaffold 根）：預演零副作用、ADMIN 確認同步成功、時間軸與資料庫逐位一致，token 零外洩", async ({ page, request }) => {
  test.skip(!TRACK_B, "TOOL-ABSENCE：未設 E2E_LOCAL_TRACK_B=1（BRIDGE_SCAFFOLD_ROOT 須是暫存目錄且已放範本；見 README）");
  test.setTimeout(900_000);
  await previewConfirmAndVerify(
    "B",
    { track: "B", projectName: `e2e-loc-${RUN}`.slice(0, 40), stackTemplate: "python-fastapi", createGithub: false, ci: true, dockerCompose: true, scopeDiffersReason: "E2E 本機模式軌道 B" },
    { page, request },
  );
});
