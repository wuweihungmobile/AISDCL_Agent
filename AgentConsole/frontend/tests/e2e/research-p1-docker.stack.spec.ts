import { expect, test } from "@playwright/test";

import { ADMIN, BASE, RUN, STACK_ON, approveViaApi, call, dataOf, detailOf, eventSeqs, hasCreds, newResearchKit, open, projectPath, signIn } from "../helpers/research-stack";

/**
 * 研發工作流（ResearchToPRD P1）的 Docker 全棧 mock-only 負控（TCS-ResearchToPRD-P1-20261107 AT-961-22-5、22-6；AC-961-22；IFACE §9.3 載具丙）——
 * **實機冒煙，不是每個 commit 的閘**（沿 `*.stack.spec.ts` 的形態）：Docker 全棧（真 console-api、真 Bridge 容器、mock claude、真 PostgreSQL）
 * 只驗「容器模式的分流一律停用，而且停得乾淨」：①`capabilities` 讀回 mock-only ②`route/preview` 與 `route` 一律 422 `route_unsupported_in_deployment`、
 * `details.missing` 逐項列缺 ③研究側零寫入（事件序號、游標、分流／SCR／拆解三個讀端點都沒有新列）④UI 步驟 3 兩張卡停用並說明。
 * 真 git／真 `gh` 的副作用**只**在本機模式（`research-route-local.stack.spec.ts`）與 Bridge 的整合測試驗。
 *
 * 啟用條件與環境變數同 `research-docker.stack.spec.ts`（見 tests/e2e/README.md〈研發工作流 Docker 全棧 E2E〉）；另需 `MOCK_CLAUDE_RESEARCH_SCRIPT` 指向 pass 劇本
 * （要走到 Gate 0 核准才有「游標在步驟 3」的專案）。
 * 誠實劃界（AT-961-22-6）：mock-only 無法分流，游標到不了步驟 4；步驟 4 前半面板與步驟 5 占位的呈現由 mock 版 `research-build-front.mock.spec.ts` 驗，
 * 這裡只驗「超前的 ?step=build／deliver 一律導回游標步」與步驟 4 相關 API 在無分流時的空值／前置不成立。
 */
const SCRIPT = process.env.MOCK_CLAUDE_RESEARCH_SCRIPT ?? "";

const ABSENCE = !STACK_ON
  ? "TOOL-ABSENCE：未設 E2E_STACK=1（這支只對 Docker 全棧跑；啟用方式見 tests/e2e/README.md〈研發工作流 Docker 全棧 E2E〉）"
  : !hasCreds(ADMIN)
    ? "TOOL-ABSENCE：缺環境變數 E2E_ADMIN_USER／E2E_ADMIN_PASSWORD（開發預設帳號見 backend/README.md）"
    : /fail3/.test(SCRIPT)
      ? "TOOL-ABSENCE：MOCK_CLAUDE_RESEARCH_SCRIPT 是 fail3，走不到 Gate 0（本支需要 pass 劇本才有游標在步驟 3 的專案）"
      : "";
if (ABSENCE !== "") console.log(`[research-p1-docker.stack] ${ABSENCE}`);
test.skip(ABSENCE !== "", ABSENCE);

const { driveToGate0, archiveAll } = newResearchKit("research-p1-docker.stack");

test.afterAll(async ({ playwright }) => {
  const request = await playwright.request.newContext();
  try {
    await archiveAll(request);
  } finally {
    await request.dispose();
  }
});

const MOCK_ONLY_TEXT = "容器模式只跑 mock claude 的驗收；真分流限本機模式";

type Capabilities = { mode: string; repoWritable: boolean; scaffoldRoot: string | null; scaffoldTemplates: string[] };
type ErrorJson = { reason?: string; details?: { missing?: Array<{ item: string; reason: string }> }; violations?: Array<{ field: string; rule: string }> };

/** 軌道 A 的最小合格請求（`scopeDiffersReason` 一律帶，免得 PRD 範圍與軌道不同時先卡在欄位驗證而看不到部署缺項）。 */
const trackA = { track: "A", targetModule: "autoclaude", scopeDiffersReason: "E2E 負控：只驗容器模式停用" };
const trackB = { track: "B", projectName: `e2e-neg-${RUN}`.slice(0, 40), stackTemplate: "python-fastapi", scopeDiffersReason: "E2E 負控：只驗容器模式停用" };

test("AT_961_22_5 Docker 全棧（mock-only）：capabilities 如實、預演與確認一律 422 route_unsupported_in_deployment 且研究側零寫入、UI 步驟 3 兩張卡停用並說明", async ({ page, request }) => {
  test.setTimeout(900_000);
  const project = await driveToGate0(request, "p1neg");
  await approveViaApi(request, project.id);

  // ①capabilities 讀回：容器模式（mock-only）、monorepo 不可寫、無範本根
  const caps = dataOf<Capabilities>(await call(request, ADMIN, "GET", "/api/v1/research/capabilities"));
  expect(caps.mode, "Docker 全棧是 mock-only").toBe("mock-only");
  expect(caps.repoWritable, "容器內 monorepo 不可寫").toBe(false);
  expect(caps.scaffoldRoot, "BRIDGE_SCAFFOLD_ROOT 未設").toBeNull();
  expect(caps.scaffoldTemplates).toEqual([]);

  // 基準：研究側目前的事件序號、游標與三個讀端點
  const before = { seqs: await eventSeqs(request, project.id), detail: await detailOf(request, project.id) };
  expect(before.detail.flowPhase, "核准後游標在步驟 3 的 FROZEN").toBe("FROZEN");
  const readEmpty = async (): Promise<void> => {
    expect(dataOf(await call(request, ADMIN, "GET", projectPath(project.id, "/route"))), "GET route 尚無列＝data:null（D-106）").toBeNull();
    expect(dataOf<unknown[]>(await call(request, ADMIN, "GET", projectPath(project.id, "/scr"))), "SCR 清單為空").toEqual([]);
    expect(dataOf(await call(request, ADMIN, "GET", projectPath(project.id, "/decomposition"))), "GET decomposition 尚無列＝data:null（D-120）").toBeNull();
  };
  await readEmpty();

  // ②預演：軌道 A 缺 repo_writable；軌道 B 因範本清單為空先被欄位驗證擋下（422 invalid_request，stack_template）——兩者皆 422、皆零寫入
  const previewA = await call(request, ADMIN, "POST", projectPath(project.id, "/route/preview"), trackA);
  const previewAJson = previewA.json as ErrorJson;
  expect(previewA.status, `preview A → ${JSON.stringify(previewA.json)}`).toBe(422);
  expect(previewAJson.reason).toBe("route_unsupported_in_deployment");
  expect(
    (previewAJson.details?.missing ?? []).map((m) => m.item),
    "缺項逐項列出且含 repo_writable",
  ).toContain("repo_writable");
  for (const m of previewAJson.details?.missing ?? []) expect(m.reason.length, `缺項 ${m.item} 有說明`).toBeGreaterThan(0);

  const previewB = await call(request, ADMIN, "POST", projectPath(project.id, "/route/preview"), trackB);
  const previewBJson = previewB.json as ErrorJson;
  expect(previewB.status, `preview B → ${JSON.stringify(previewB.json)}`).toBe(422);
  expect(["route_unsupported_in_deployment", "invalid_request"], "軌道 B：缺範本根或範本不在清單").toContain(previewBJson.reason);

  // ③確認：同樣 422，且 Bridge 沒有寫任何東西（console-api 先建的專案列由補償封存；研究側不留痕）
  const confirm = await call(request, ADMIN, "POST", projectPath(project.id, "/route"), trackA);
  const confirmJson = confirm.json as ErrorJson;
  expect(confirm.status, `route A → ${JSON.stringify(confirm.json)}`).toBe(422);
  expect(confirmJson.reason).toBe("route_unsupported_in_deployment");
  expect((confirmJson.details?.missing ?? []).map((m) => m.item)).toContain("repo_writable");

  const after = { seqs: await eventSeqs(request, project.id), detail: await detailOf(request, project.id) };
  expect(after.seqs, "預演與確認都失敗：研究事件帳零新增").toEqual(before.seqs);
  expect([after.detail.flowStep, after.detail.flowPhase, after.detail.flowStatus], "游標原地不動").toEqual([before.detail.flowStep, before.detail.flowPhase, before.detail.flowStatus]);
  await readEmpty();

  // ④UI：步驟 3 開啟分流精靈，兩張卡皆停用並顯示 mock-only 說明；VIEWER／OPERATOR 的角色停用文案由 mock 版驗
  await signIn(page, request, ADMIN);
  await open(page, request, `${BASE}/research/${project.id}?step=route`);
  await expect(page.getByTestId("research-workspace")).toHaveAttribute("data-step", "route", { timeout: 60_000 });
  await expect(page.getByTestId("route-panel")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("route-drawer")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("route-card-a-disabled")).toContainText(MOCK_ONLY_TEXT, { timeout: 30_000 });
  await expect(page.getByTestId("route-card-b-disabled")).toContainText(MOCK_ONLY_TEXT);
  await expect(page.getByTestId("route-card-a")).toBeVisible();
  await expect(page.getByRole("button", { name: "確認執行" }), "mock-only：確認執行停用").toBeDisabled();
});

test("AT_961_22_6 Docker 全棧（mock-only）：步驟 4 與 5 在無分流時的呈現——超前導回游標步、拆解與 SCR 讀端點為空、tcs-draft 前置不成立 409", async ({ page, request }) => {
  test.setTimeout(900_000);
  const project = await driveToGate0(request, "p1build");
  await approveViaApi(request, project.id);

  // 游標在步驟 3：?step=build／deliver 都導回 route，且沒有占位面板（步驟 3 是真面板）
  await signIn(page, request, ADMIN);
  for (const step of ["build", "deliver"] as const) {
    await open(page, request, `${BASE}/research/${project.id}?step=${step}`);
    await expect(page, `超前的 ?step=${step} 導回游標所在步`).toHaveURL(/step=route/, { timeout: 30_000 });
    await expect(page.getByTestId("route-panel")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("research-placeholder")).toHaveCount(0);
  }

  // API：無分流時拆解與 SCR 為空；tcs-draft 啟動的前置（分流＋拆解簽核）不成立＝409，且沒有任何 stage run 被建立
  expect(dataOf(await call(request, ADMIN, "GET", projectPath(project.id, "/decomposition")))).toBeNull();
  const seqsBefore = await eventSeqs(request, project.id);
  const started = await call(request, ADMIN, "POST", projectPath(project.id, "/stages/tcs-draft"), {});
  expect(started.status, `tcs-draft（無分流）→ ${JSON.stringify(started.json)}`).toBe(409);
  expect(await eventSeqs(request, project.id), "前置不成立：沒有新事件").toEqual(seqsBefore);

  // 拆解觸發需 MINIMAX_API_KEY 或注入 brain，Docker 內不可真跑——標 TOOL-ABSENCE（與 P0 INT 同口徑）
  test.info().annotations.push({ type: "拆解觸發略過", description: "TOOL-ABSENCE：Docker 內無拆解 brain（MINIMAX_API_KEY）；步驟 4 前半面板的呈現由 research-build-front.mock.spec.ts 驗" });
});
