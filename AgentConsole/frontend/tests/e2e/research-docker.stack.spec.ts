import { execFileSync } from "node:child_process";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { axeViolations, formatViolations } from "./a11y";

/**
 * 研發工作流（ResearchToPRD P0）的 Docker 全棧 E2E（TCS-ResearchToPRD-P0-20261102 AT-960-22-2、22-3、22-4、22-5、22-E-1；AC-R2P-04-11、06-2、06-4、08-3、10-1、10-6、21-3）——
 * **實機冒煙，不是每個 commit 的閘**（沿 `*.stack.ts` 的形態）：`docker compose --profile db --profile app --profile full up -d --build` 之後，經 nginx 同源、真 console-api →
 * 真 Bridge →（mock claude 的研究劇本）→ 真 PostgreSQL。啟用方式與環境變數見 tests/e2e/README.md〈研發工作流 Docker 全棧 E2E〉。
 *
 * 這支把 PKG-INT 整合代驗的腳本（scratchpad 的 library 腳本）整理成可重跑的 spec；與 mock 版（vitest／`*.mock.spec.ts`）的差別是這裡沒有任何假資料：
 * 資料庫、事件序號、凍結摘要、對帳、RBAC 都是真的，所以只驗「跨服務才現形」的事（INT 代驗抓到的四類契約錯位：對帳欄位名、範圍鍵大小寫、失敗游標語意、取消後死路）。
 *
 * 啟用條件（缺任何一項＝整支略過並印 TOOL-ABSENCE，不當失敗）：`E2E_STACK=1`、`E2E_ADMIN_USER`／`E2E_ADMIN_PASSWORD`（開發預設帳號見 backend/README.md；不寫進程式碼）。
 * 選配：`E2E_OPERATOR_USER`／`E2E_OPERATOR_PASSWORD`、`E2E_VIEWER_USER`／`E2E_VIEWER_PASSWORD`（缺＝該角色的子斷言略過並註記）；
 * `MOCK_CLAUDE_RESEARCH_SCRIPT`（與 compose `.env` 同值：指向 fail3 才跑 22-2、指向 pass 或未設跑路徑 B）；`E2E_BRIDGE_CONTAINER`（預設 `aisdlc-engine-bridge`，凍結摘要對檔案位元組用）。
 *
 * 帶 `[新 frontend]` 的斷言是 PKG-FIX-FE 才有的行為（INT-08 有效抓取主機區、INT-09 凍結後不標已過期、INT-12 重連後沒有新事件也補齊、INT-14⑤ 即時預覽沒有來源節錨點文字）：
 * 用軟斷言，舊映像上會紅在這幾條、其餘照跑，重建 frontend 映像後應全綠。
 * 所有測試建立的專案在結束時封存（資料庫不留未封存的測試專案，下一次的零專案空狀態才成立）；工作區目錄留在 Bridge 容器的 volume 內（封存不刪檔）。
 */
const STACK_ON = process.env.E2E_STACK === "1";
const BASE = (process.env.E2E_API_URL ?? "http://localhost").replace(/\/+$/, "");

type Creds = { user: string; password: string };
const credsOf = (role: string): Creds => ({ user: process.env[`E2E_${role}_USER`] ?? "", password: process.env[`E2E_${role}_PASSWORD`] ?? "" });
const hasCreds = (c: Creds): boolean => c.user !== "" && c.password !== "";
const ADMIN = credsOf("ADMIN");
const OPERATOR = credsOf("OPERATOR");
const VIEWER = credsOf("VIEWER");
const BRIDGE_CONTAINER = process.env.E2E_BRIDGE_CONTAINER ?? "aisdlc-engine-bridge";
const SCRIPT = process.env.MOCK_CLAUDE_RESEARCH_SCRIPT ?? "";
const SCRIPT_KIND: "fail3" | "pass" | "unknown" = /fail3/.test(SCRIPT) ? "fail3" : /pass/.test(SCRIPT) ? "pass" : "unknown";
const RUN = Date.now().toString(36);

const ABSENCE = !STACK_ON
  ? "TOOL-ABSENCE：未設 E2E_STACK=1（這支只對 Docker 全棧跑；啟用方式見 tests/e2e/README.md〈研發工作流 Docker 全棧 E2E〉）"
  : !hasCreds(ADMIN)
    ? "TOOL-ABSENCE：缺環境變數 E2E_ADMIN_USER／E2E_ADMIN_PASSWORD（開發預設帳號見 backend/README.md）"
    : "";
if (ABSENCE !== "") console.log(`[research-docker.stack] ${ABSENCE}`);
test.skip(ABSENCE !== "", ABSENCE);

// ── REST 與登入 ──────────────────────────────────────────────────────────────────────────

type Json = Record<string, unknown>;
type Reply = { status: number; json: Json };
type Tokens = { accessToken: string; refreshToken: string; expiresIn: number; role: string };

const tokenCache = new Map<string, { at: number; tokens: Tokens }>();

/** 取該帳號的 token（快取 20 分鐘；access token 效期 30 分鐘）。 */
async function tokensOf(request: APIRequestContext, c: Creds): Promise<Tokens> {
  const hit = tokenCache.get(c.user);
  if (hit !== undefined && Date.now() - hit.at < 20 * 60_000) return hit.tokens;
  const res = await request.post(`${BASE}/api/v1/auth/login`, { data: { username: c.user, password: c.password }, failOnStatusCode: false });
  expect(res.ok(), `登入 ${c.user} 失敗：HTTP ${res.status()}`).toBeTruthy();
  const tokens = ((await res.json()) as { data: Tokens }).data;
  tokenCache.set(c.user, { at: Date.now(), tokens });
  return tokens;
}

/**
 * 呼叫 REST（任何狀態碼都回傳，由呼叫端斷言）。限流是固定視窗：每個使用者每 60 秒 100 次，UI 與 REST 共用同一個桶（總覽頁一次載入就約 30 次）；
 * 撞到 429 就等視窗過去再試（最多四次）——否則流程中途的 429 會被誤判成功能缺陷（第一次實跑的 22-5 就是這樣在載入工作區時撞牆）。
 */
async function call(request: APIRequestContext, c: Creds, method: "GET" | "POST" | "PUT" | "PATCH", apiPath: string, body?: unknown): Promise<Reply> {
  for (let attempt = 0; ; attempt += 1) {
    const { accessToken } = await tokensOf(request, c);
    const res = await request.fetch(`${BASE}${apiPath}`, { method, headers: { Authorization: `Bearer ${accessToken}` }, data: body, failOnStatusCode: false });
    if (res.status() === 429 && attempt < 4) {
      const retryAfter = Number(res.headers()["retry-after"] ?? "20");
      await new Promise((resolve) => setTimeout(resolve, (Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : 20) * 1000 + 1000));
      continue;
    }
    let json: Json = {};
    try {
      json = (await res.json()) as Json;
    } catch {
      json = {};
    }
    return { status: res.status(), json };
  }
}

/** 限流的餘額（`X-RateLimit-Remaining`）不夠就等視窗過去：接下來要開頁面（每頁約 30 次請求）前呼叫，不然頁面載入到一半撞 429（UI 的請求這裡沒法重試）。 */
async function ensureQuota(request: APIRequestContext, c: Creds, need = 50): Promise<void> {
  for (let i = 0; i < 3; i += 1) {
    const { accessToken } = await tokensOf(request, c);
    const res = await request.get(`${BASE}/api/v1/notifications/summary`, { headers: { Authorization: `Bearer ${accessToken}` }, failOnStatusCode: false });
    const remaining = Number(res.headers()["x-ratelimit-remaining"] ?? "100");
    if (res.status() === 200 && remaining >= need) return;
    await new Promise((resolve) => setTimeout(resolve, 62_000));
  }
}

/** 導覽到 ADMIN 的頁面：先確認限流餘額夠載入一整頁（工作區頁約 20～30 次請求，且那些請求這裡沒法重試），不夠就等下一個視窗。 */
async function open(page: Page, request: APIRequestContext, url: string): Promise<void> {
  await ensureQuota(request, ADMIN);
  await page.goto(url);
}
const dataOf = <T = Json>(reply: Reply): T => reply.json.data as T;
const projectPath = (id: string, rest = ""): string => `/api/v1/research/projects/${id}${rest}`;

/** 登入狀態直接寫進 sessionStorage（須在 page.goto 之前呼叫）。 */
async function signIn(page: Page, request: APIRequestContext, c: Creds): Promise<void> {
  const t = await tokensOf(request, c);
  const session = JSON.stringify({ accessToken: t.accessToken, refreshToken: t.refreshToken, expiresAt: Date.now() + t.expiresIn * 1000, role: t.role, username: c.user });
  await page.addInitScript((value) => window.sessionStorage.setItem("aisdlc.console.session", value), session);
}

async function poll<T>(fn: () => Promise<T>, done: (value: T) => boolean, what: string, timeoutMs = 240_000, intervalMs = 2500): Promise<T> {
  const start = Date.now();
  let last: T | undefined;
  while (Date.now() - start < timeoutMs) {
    last = await fn();
    if (done(last)) return last;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(`等待逾時（${timeoutMs}ms）：${what}；最後一次值＝${JSON.stringify(last)}`);
}

// ── 專案夾具（路徑 B：pass 劇本走到 Gate 0；路徑 A：fail3 劇本走到 ESCALATION）─────────────────────────

type Project = { id: string; slug: string; rpNo: string };
type Detail = { flowStep: string; flowPhase: string; flowStatus: string; flowDetail: string; headPrdVersion: number | null; scope: Json; fsmProject: string; flow: { effective: Json } };
type Round = { roundNo: number; weightedScore: number | null; verdict: string; passed: boolean };

const created: string[] = [];
/** 議題軸：mock 劇本的證據夾具寫死全六軸，專案軸取子集會在證據 gate 的 R8 失敗（INT-11；README 已載明），所以 API 直呼一律建六軸。 */
const SIX_AXES = ["技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本"];

async function createProject(request: APIRequestContext, tag: string): Promise<Project> {
  const slug = `e2e-${tag}-${RUN}`.slice(0, 30);
  const reply = await call(request, ADMIN, "POST", "/api/v1/research/projects", {
    slug,
    title: `E2E ${tag} ${RUN}`,
    topic: `E2E 研發工作流 ${tag} ${RUN}`,
    scope: {
      layers: { academic: true, industry: false, oss: true, community: false },
      techStack: "Python / PostgreSQL",
      inScope: ["E2E 範圍"],
      outOfScope: ["不在範圍的東西"],
      recencyYears: 2,
      applicabilityAxes: SIX_AXES,
    },
    depthLevel: "QUICK",
  });
  expect(reply.status, `建立專案 ${slug} → ${JSON.stringify(reply.json)}`).toBe(201);
  const data = dataOf<{ id: string; rpNo: string }>(reply);
  created.push(data.id);
  return { id: data.id, slug, rpNo: data.rpNo };
}

const detailOf = async (request: APIRequestContext, id: string): Promise<Detail> => {
  const reply = await call(request, ADMIN, "GET", projectPath(id));
  expect(reply.status, `GET 專案 → ${JSON.stringify(reply.json)}`).toBe(200);
  return dataOf<Detail>(reply);
};
const roundsOf = async (request: APIRequestContext, id: string): Promise<Round[]> => dataOf<Round[]>(await call(request, ADMIN, "GET", projectPath(id, "/review-rounds")));
const eventSeqs = async (request: APIRequestContext, id: string): Promise<number[]> =>
  dataOf<{ items: Array<{ seq: number }> }>(await call(request, ADMIN, "GET", projectPath(id, "/events?afterSeq=0&limit=500"))).items.map((e) => e.seq);

/** 事件帳的一次請求取得：這個 stage run 的狀態（最後一筆 `research.run`）與游標的 `flowStatus`（最後一筆 `research.step`）；還沒有事件回空字串。 */
async function progressOf(request: APIRequestContext, id: string, stageRunId: string): Promise<{ run: string; cursor: string }> {
  const page = dataOf<{ items: Array<{ eventType: string; payload: { stageRunId?: string; status?: string; flowStatus?: string } }> }>(
    await call(request, ADMIN, "GET", projectPath(id, "/events?afterSeq=0&limit=500")),
  );
  const run = page.items.filter((e) => e.eventType === "research.run" && e.payload.stageRunId === stageRunId).at(-1)?.payload.status;
  const cursor = page.items.filter((e) => e.eventType === "research.step").at(-1)?.payload.flowStatus;
  return { run: run ?? "", cursor: cursor ?? "" };
}

/**
 * 啟動一個階段並等它收尾。202 回的游標是**啟動前**的（`IDLE`，引擎在背景才開始），所以不能以「游標不是 RUNNING」判結束（會在啟動前就誤判）；
 * 判準＝這個 stage run 已到終態（事件帳的 `research.run`）**且**游標離開 RUNNING（一鍵迭代是 REVISE 接 REVIEW 兩個 run，REVISE 收尾時游標仍是 RUNNING，REVIEW 結束才離開）。
 * 輪詢只打事件帳一個端點、每 3 秒一次（限流是每使用者每分鐘 100 次，與 UI 共用）。全站同時只跑一個 stage run（`stage_conflict`／`max_concurrent_runs`，D-67）：
 * 下一個階段必須等這一個真的結束才能送。
 */
async function runStage(request: APIRequestContext, id: string, stage: "research" | "draft" | "review" | "iterate"): Promise<Detail> {
  const started = await call(request, ADMIN, "POST", projectPath(id, `/stages/${stage}`), {});
  expect(started.status, `stages/${stage} → ${JSON.stringify(started.json)}`).toBe(202);
  const { stageRunId } = dataOf<{ stageRunId: string }>(started);
  await poll(
    () => progressOf(request, id, stageRunId),
    ({ run, cursor }) => ["SUCCEEDED", "FAILED", "CANCELLED"].includes(run) && cursor !== "" && cursor !== "RUNNING",
    `${stage} 結束（stage run 到終態且游標離開 RUNNING）`,
    300_000,
    3000,
  );
  return detailOf(request, id);
}

/** 路徑 B：研究 → 草擬 → 送審（第 1 輪 79.90 未過）→ 一鍵迭代（第 2 輪 90.30 通過）→ GATE0_PENDING。 */
async function driveToGate0(request: APIRequestContext, tag: string): Promise<Project> {
  const project = await createProject(request, tag);
  const researched = await runStage(request, project.id, "research");
  expect([researched.flowPhase, researched.flowStatus], `研究結束：${JSON.stringify(researched)}`).toEqual(["EVIDENCE_READY", "IDLE"]);
  const drafted = await runStage(request, project.id, "draft");
  expect(drafted.headPrdVersion, "草擬後有第 1 版 PRD").toBe(1);
  await runStage(request, project.id, "review");
  const first = await roundsOf(request, project.id);
  expect(
    first.map((r) => [r.roundNo, r.weightedScore?.toFixed(2), r.verdict]),
    "第 1 輪（pass 劇本）",
  ).toEqual([[1, "79.90", "REVISE"]]);
  const iterated = await runStage(request, project.id, "iterate");
  expect([iterated.flowPhase, iterated.flowStatus], `迭代結束：${JSON.stringify(iterated)}`).toEqual(["GATE0_PENDING", "WAITING_HUMAN"]);
  const rounds = await roundsOf(request, project.id);
  expect(
    rounds.map((r) => [r.roundNo, r.weightedScore?.toFixed(2), r.verdict]),
    "第 2 輪（pass 劇本）",
  ).toEqual([
    [1, "79.90", "REVISE"],
    [2, "90.30", "PASS"],
  ]);
  return project;
}

/** 共用的「GATE0_PENDING」專案：E-1 先用（不核准），22-3 再核准；單獨跑任一個都會自己建。 */
let gate0: Promise<Project> | null = null;
const gate0Project = (request: APIRequestContext): Promise<Project> => (gate0 ??= driveToGate0(request, "gate0"));

test.afterAll(async ({ playwright }) => {
  // 清場：封存所有測試建立的專案（`archived_at` 寫入、列保留）；失敗不擋收尾，但要說出來（留著未封存的測試專案，下一次的零專案空狀態就不成立）。afterAll 只能用 worker 級的 fixture，所以自建一個 request 環境
  const request = await playwright.request.newContext();
  try {
    for (const id of created) {
      const reply = await call(request, ADMIN, "POST", projectPath(id, "/archive"), {}).catch(() => null);
      if (reply === null || reply.status !== 200) console.warn(`[research-docker.stack] 專案 ${id} 沒有封存成功（${reply === null ? "請求失敗" : `HTTP ${reply.status}`}），請手動封存`);
    }
  } finally {
    await request.dispose();
  }
});

// ── AT-960-22-5 UI 殼層 ──────────────────────────────────────────────────────────────────

test("AT_960_22_5 UI 殼層：側欄入口與 aria-current、390 底部 Tab 不含它、零專案空狀態、超前的 ?step= 導回、步驟 3～5 占位、mock-only 停用啟動深研、角色（VIEWER 唯讀、OPERATOR 無研究來源設定入口、ADMIN 有）", async ({
  page,
  request,
  browser,
}) => {
  test.setTimeout(900_000);
  // 空狀態只在「資料庫沒有任何未封存的研究專案」時成立：共用的全棧可能有別人留下的，這時只略過這一小段並註記（不當失敗）
  const active = dataOf<unknown[]>(await call(request, ADMIN, "GET", "/api/v1/research/projects"));

  await signIn(page, request, ADMIN);
  await open(page, request, `${BASE}/projects`);
  const nav = page.getByRole("navigation", { name: "主導覽" });
  await nav.getByRole("link", { name: "研發工作流" }).click();
  await expect(page).toHaveURL(/\/research$/);
  await expect(page.getByTestId("research-list-view")).toBeVisible({ timeout: 60_000 });
  await expect(nav.getByRole("link", { name: "研發工作流" })).toHaveAttribute("aria-current", "page");

  if (active.length === 0) {
    await expect(page.getByText("還沒有任何研究專案")).toBeVisible();
    await expect(page.getByRole("button", { name: "新建研究專案" })).toBeEnabled();
    expect(page.url(), "零專案不自動跳轉").toMatch(/\/research$/);
  } else {
    test.info().annotations.push({ type: "空狀態略過", description: `資料庫已有 ${active.length} 個未封存的研究專案（非本測試建立），零專案空狀態無從驗證` });
  }

  // 390 像素寬：主導覽變底部 Tab，不含「研發工作流」（登記表 mobile:false）
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page, request, `${BASE}/research`);
  await expect(page.getByTestId("research-list-view")).toBeVisible({ timeout: 60_000 });
  const tabNames = await page
    .getByRole("navigation", { name: "主導覽" })
    .getByRole("link")
    .evaluateAll((links) => links.map((a) => a.getAttribute("aria-label") ?? a.textContent ?? ""));
  expect(tabNames.length, "390 寬的主導覽（底部 Tab）有項目").toBeGreaterThan(0);
  expect(tabNames, "底部 Tab 不含研發工作流").not.toContain("研發工作流");
  await page.setViewportSize({ width: 1440, height: 900 });

  // ADMIN：研究來源設定入口、新建專案（UI）、mock-only 停用啟動深研
  await open(page, request, `${BASE}/research`);
  await expect(page.getByRole("button", { name: "研究來源設定" })).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: "新建研究專案" }).click();
  const create = page.getByRole("dialog", { name: "新建研究專案" });
  await create.getByLabel("研究命題").fill(`E2E UI 建立 ${RUN}`);
  await expect(create.getByLabel("網址代號"), "代號由命題自動產生").not.toHaveValue("");
  await create.getByRole("button", { name: "建立" }).click();
  await expect(page).toHaveURL(/\/research\/[0-9a-f-]{36}/, { timeout: 60_000 });
  const uiId = /\/research\/([0-9a-f-]{36})/.exec(page.url())?.[1] ?? "";
  created.push(uiId);
  await expect(page.getByTestId("research-workspace")).toHaveAttribute("data-step", "topic", { timeout: 60_000 });
  await expect(page.getByRole("button", { name: "啟動深研" }), "mock-only：啟動深研停用").toBeDisabled();
  await expect(page.getByTestId("launch-hint")).toContainText("容器模式只跑 mock claude 的驗收；真研究限本機模式");

  // INT-03：議題面板的範圍欄位取自 API 的 camelCase 鍵（不再恆顯示「—」）；UI 建立的預設範圍＝納入範圍為命題本身、近 3 年、六個適用性軸
  const topicScope = page.getByTestId("topic-scope");
  await expect(topicScope).toContainText("近 3 年", { timeout: 30_000 });
  await expect(topicScope).toContainText("技術可行");

  // 超前的 ?step= 導回游標步
  await open(page, request, `${BASE}/research/${uiId}?step=deliver`);
  await expect(page).toHaveURL(/step=topic/, { timeout: 30_000 });
  await expect(page.getByTestId("research-workspace")).toHaveAttribute("data-step", "topic");

  // 步驟 3～5 占位：需要游標已過規格工作室的專案（pass 劇本走到核准；以 API 核准，UI 核准另見 AT_960_22_3）
  test.skip(SCRIPT_KIND === "fail3", "步驟 3～5 占位面板需要游標已過規格工作室的專案：劇本是 fail3，走不到 Gate 0（其餘子斷言已完成）");
  const frozen = await driveToGate0(request, "shell");
  await approveViaApi(request, frozen.id);
  // P0 的游標最遠只到 route（步驟 3）：步驟 3 是占位面板；步驟 4、5 超前於游標，`?step=build|deliver` 一律導回游標所在步（同一個占位面板）——TCS 寫「看步驟 3 至 5」，P0 實際可達的只有步驟 3
  await open(page, request, `${BASE}/research/${frozen.id}?step=route`);
  await expect(page.getByTestId("research-workspace")).toHaveAttribute("data-step", "route", { timeout: 60_000 });
  await expect(page.getByTestId("research-placeholder")).toContainText("第 3 步：分流");
  await expect(page.getByTestId("research-placeholder")).toContainText("本步驟於後續階段提供");
  for (const step of ["build", "deliver"] as const) {
    await open(page, request, `${BASE}/research/${frozen.id}?step=${step}`);
    await expect(page, `超前的 ?step=${step} 導回游標所在步`).toHaveURL(/step=route/, { timeout: 30_000 });
    await expect(page.getByTestId("research-workspace")).toHaveAttribute("data-step", "route");
    await expect(page.getByTestId("research-placeholder")).toContainText("第 3 步：分流");
  }
  await open(page, request, `${BASE}/research/${frozen.id}?step=studio`);
  await expect(page.getByTestId("studio-frozen")).toBeVisible({ timeout: 60_000 });

  // ADMIN 的研究來源設定：有效清單與（[新 frontend]）有效抓取主機區
  await open(page, request, `${BASE}/research`);
  await page.getByRole("button", { name: "研究來源設定" }).click();
  const allowlist = page.getByRole("dialog", { name: "研究來源設定" });
  await expect(allowlist.getByTestId("allowlist-row").first()).toBeVisible({ timeout: 60_000 });
  await expect.soft(allowlist.getByTestId("effective-hosts"), "[新 frontend] INT-08：有效抓取主機區列出 fetchHosts").toBeVisible({ timeout: 30_000 });
  await page.keyboard.press("Escape");

  // VIEWER：全頁唯讀；OPERATOR：沒有研究來源設定入口（選配帳號）
  if (hasCreds(VIEWER)) {
    const viewer = await browser.newContext({ locale: "zh-TW", viewport: { width: 1440, height: 900 } });
    const vp = await viewer.newPage();
    await signIn(vp, request, VIEWER);
    await vp.goto(`${BASE}/research`);
    await expect(vp.getByTestId("research-list-view")).toBeVisible({ timeout: 60_000 });
    await expect(vp.getByRole("button", { name: "新建研究專案" }), "VIEWER：新建停用").toBeDisabled();
    await expect(vp.getByRole("button", { name: "研究來源設定" })).toHaveCount(0);
    await vp.goto(`${BASE}/research/${frozen.id}?step=studio`);
    await expect(vp.getByTestId("gatekeeper-panel")).toBeVisible({ timeout: 60_000 });
    await expect(vp.getByRole("button", { name: "核准 PRD" })).toBeDisabled();
    await expect(vp.getByRole("button", { name: "對帳" })).toBeDisabled();
    await viewer.close();
  } else {
    test.info().annotations.push({ type: "VIEWER 略過", description: "TOOL-ABSENCE：缺 E2E_VIEWER_USER／E2E_VIEWER_PASSWORD" });
  }
  if (hasCreds(OPERATOR)) {
    const operator = await browser.newContext({ locale: "zh-TW", viewport: { width: 1440, height: 900 } });
    const op = await operator.newPage();
    await signIn(op, request, OPERATOR);
    await op.goto(`${BASE}/research`);
    await expect(op.getByTestId("research-list-view")).toBeVisible({ timeout: 60_000 });
    await expect(op.getByRole("button", { name: "研究來源設定" }), "OPERATOR 看不到研究來源設定入口").toHaveCount(0);
    await expect(op.getByRole("button", { name: "新建研究專案" })).toBeEnabled();
    await operator.close();
  } else {
    test.info().annotations.push({ type: "OPERATOR 略過", description: "TOOL-ABSENCE：缺 E2E_OPERATOR_USER／E2E_OPERATOR_PASSWORD" });
  }
});

/** 以 API 核准（head 版本、帶 PRD 與證據矩陣兩個摘要；Gate 0 的 API 側；回 API 的 `specDocDigests`）。 */
async function approveViaApi(request: APIRequestContext, id: string): Promise<Record<string, string>> {
  const detail = await detailOf(request, id);
  const versions = dataOf<Array<{ versionNo: number; sha256: string }>>(await call(request, ADMIN, "GET", projectPath(id, "/prd/versions")));
  const head = versions.reduce((a, v) => (v.versionNo > a.versionNo ? v : a));
  const matrix = dataOf<{ sha256: string }>(await call(request, ADMIN, "GET", projectPath(id, "/evidence")));
  const sha = (hex: string): string => (hex.startsWith("sha256:") ? hex : `sha256:${hex}`);
  expect(detail.headPrdVersion, "head 版本").toBe(head.versionNo);
  const reply = await call(request, ADMIN, "POST", projectPath(id, "/approve"), {
    prdVersion: head.versionNo,
    expectedDigests: { "01_specs/PRD-v1.0.0.md": sha(head.sha256), "00_research/evidence_matrix.md": sha(matrix.sha256) },
    reason: "E2E 核准",
  });
  expect(reply.status, `approve → ${JSON.stringify(reply.json)}`).toBe(200);
  const data = dataOf<{ specDocDigests: Record<string, string>; fsmState: string }>(reply);
  expect(data.fsmState).toBe("SPEC_FROZEN");
  return data.specDocDigests;
}

// ── AT-960-22-E-1 無障礙與響應式（真棧資料；共用 GATE0_PENDING 專案）────────────────────────────

test("AT_960_22_E_1 無障礙與響應式：清單、議題、工作室在 1440、1000、600 寬度無水平溢出且 axe 無 serious／critical 違規；Studio 在 600 為分頁籤；對話框焦點陷阱與歸還", async ({ page, request }) => {
  test.setTimeout(900_000);
  test.skip(SCRIPT_KIND === "fail3", "劇本是 fail3：共用的 GATE0_PENDING 專案走不到（工作室的真棧 axe 請改設 pass 劇本）");
  const project = await gate0Project(request);
  await signIn(page, request, ADMIN);

  const views: Array<{ label: string; url: string; ready: string }> = [
    { label: "清單", url: `${BASE}/research`, ready: "research-list-view" },
    { label: "議題步", url: `${BASE}/research/${project.id}?step=topic`, ready: "topic-panel" },
    // 600 寬時工作室是分頁籤（一次只顯示一個區塊，審批欄預設是隱藏的），所以以工作室根節點判載入完成
    { label: "工作室", url: `${BASE}/research/${project.id}?step=studio`, ready: "studio-panel" },
  ];
  for (const width of [1440, 1000, 600]) {
    await page.setViewportSize({ width, height: 900 });
    for (const view of views) {
      await open(page, request, view.url);
      await expect(page.getByTestId(view.ready)).toBeVisible({ timeout: 60_000 });
      await page.waitForTimeout(1500); // 串流與資料載入後的靜止畫面
      const overflow = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
      expect(overflow.scroll, `${view.label} 在 ${width} 寬的水平溢出（scrollWidth ${overflow.scroll}／clientWidth ${overflow.client}）`).toBeLessThanOrEqual(overflow.client + 1);
      const findings = await axeViolations(page);
      const serious = findings.filter((f) => f.impact === "serious" || f.impact === "critical");
      expect(serious, `${view.label} 在 ${width} 寬的 axe serious／critical 違規\n${formatViolations(serious)}`).toEqual([]);
      if (findings.length > 0) test.info().annotations.push({ type: "axe 非嚴重", description: `${view.label}@${width}：${findings.map((f) => `${f.id}[${f.impact}]`).join("、")}` });
      if (view.label === "工作室" && width === 1440) {
        // 草稿未凍結的工作室預設是編輯器的左右分欄；右欄的即時預覽不該把來源節錨點（整行 `<!-- r2p:section=N -->`）當文字顯示（INT-14⑤）
        const preview = page.getByTestId("md-preview-region");
        await expect(preview, "1440 寬的工作室（草稿、未凍結）有編輯器的即時預覽").toContainText(/\S/);
        await expect.soft(preview, "[新 frontend] INT-14⑤：即時預覽沒有 `r2p:section` 錨點文字（舊映像整行以文字出現）").not.toContainText("r2p:section");
      }
      if (view.label === "工作室" && width === 600) {
        for (const name of ["目錄", "編輯器", "審批"]) await expect(page.getByRole("tab", { name }), `600 寬的工作室分頁籤「${name}」`).toBeVisible();
      }
    }
  }

  // 彈窗焦點陷阱與歸還：研究來源設定（ADMIN）與 Gate 0 對話框
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, request, `${BASE}/research`);
  const trigger = page.getByRole("button", { name: "研究來源設定" });
  await expect(trigger).toBeVisible({ timeout: 60_000 });
  await trigger.click();
  const allowlist = page.getByRole("dialog", { name: "研究來源設定" });
  await expect(allowlist).toBeVisible();
  for (let i = 0; i < 14; i += 1) {
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => document.activeElement?.closest("[role=dialog]") !== null), `研究來源設定：Tab 第 ${i + 1} 次仍在對話框內`).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(allowlist).toBeHidden();
  await expect(trigger, "Esc 關閉後焦點歸還到觸發鈕").toBeFocused();

  await open(page, request, `${BASE}/research/${project.id}?step=studio`);
  const approve = page.getByRole("button", { name: "核准 PRD" });
  await expect(approve).toBeEnabled({ timeout: 60_000 });
  await approve.click();
  const gate = page.getByRole("dialog", { name: "Gate 0：核准或退回 PRD" });
  await expect(gate).toBeVisible();
  for (let i = 0; i < 10; i += 1) {
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => document.activeElement?.closest("[role=dialog]") !== null), `Gate 0 對話框：Tab 第 ${i + 1} 次仍在對話框內`).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(gate).toBeHidden();
  await expect(approve, "Esc 關閉後焦點歸還到「核准 PRD」").toBeFocused();
});

// ── AT-960-22-3 路徑 B：pass 劇本、ADMIN 核准、FSM 凍結 ───────────────────────────────────────

test("AT_960_22_3 路徑 B：審查通過、ADMIN 於 UI 核准、FSM 凍結；凍結摘要＝FSM 視圖＝容器內檔案位元組；二次核准 409；OPERATOR 403；對帳一致", async ({ page, request }) => {
  test.setTimeout(900_000);
  test.skip(SCRIPT_KIND === "fail3", "劇本是 fail3：路徑 B 需要 pass 劇本（MOCK_CLAUDE_RESEARCH_SCRIPT）");
  const project = await gate0Project(request);

  // OPERATOR 嘗試核准：403（選配帳號）；核准前先試，確認狀態不因被拒而改變
  if (hasCreds(OPERATOR)) {
    const denied = await call(request, OPERATOR, "POST", projectPath(project.id, "/approve"), { prdVersion: 2, expectedDigests: { "01_specs/PRD-v1.0.0.md": `sha256:${"0".repeat(64)}` } });
    expect(denied.status, `OPERATOR 核准 → ${JSON.stringify(denied.json)}`).toBe(403);
    expect((await detailOf(request, project.id)).flowPhase, "被拒的核准不改狀態").toBe("GATE0_PENDING");
  } else {
    test.info().annotations.push({ type: "OPERATOR 略過", description: "TOOL-ABSENCE：缺 E2E_OPERATOR_USER／E2E_OPERATOR_PASSWORD" });
  }

  // ADMIN 於 UI 核准
  await signIn(page, request, ADMIN);
  await open(page, request, `${BASE}/research/${project.id}?step=studio`);
  await expect(page.getByTestId("gatekeeper-panel")).toBeVisible({ timeout: 60_000 });
  const approve = page.getByRole("button", { name: "核准 PRD" });
  await expect(approve).toBeEnabled({ timeout: 60_000 });
  await approve.click();
  const dialog = page.getByRole("dialog", { name: "Gate 0：核准或退回 PRD" });
  await expect(dialog.getByTestId("gate-summary")).toContainText("90.30");
  await dialog.getByLabel(/理由/).fill("E2E 路徑 B：核准");
  await dialog.getByRole("button", { name: "核准並凍結" }).click();
  await expect(page.getByText("已核准並凍結", { exact: false }).first()).toBeVisible({ timeout: 60_000 });

  // 核准後：flow 為 route／FROZEN；工作室唯讀且（[新 frontend]）通過的審查不標「已過期」（INT-09）
  const frozen = await poll(
    () => detailOf(request, project.id),
    (d) => d.flowPhase === "FROZEN",
    "核准後游標進到 FROZEN",
    60_000,
    1500,
  );
  expect([frozen.flowStep, frozen.flowPhase]).toEqual(["route", "FROZEN"]);
  await expect(page.getByTestId("studio-frozen")).toBeVisible({ timeout: 30_000 });
  await expect.soft(page.getByTestId("review-stale"), "[新 frontend] INT-09：凍結後（BASELINE 版與通過版同內容）不標「已過期」").toHaveCount(0);

  // 凍結摘要：FSM 視圖的 frozen_stages[-1].spec_doc_digests（＝`show`）四個檔，且與容器內檔案位元組的 sha256 逐位元相同
  const fsm = dataOf<{ currentState: string; frozenStages: Array<{ spec_doc_digests?: Record<string, string> }> }>(await call(request, ADMIN, "GET", projectPath(project.id, "/fsm")));
  expect(fsm.currentState).toBe("SPEC_FROZEN");
  const digests = fsm.frozenStages.at(-1)?.spec_doc_digests ?? {};
  expect(Object.keys(digests).sort(), "凍結四檔").toEqual(["00_research/evidence_matrix.md", "00_research/issue_scope.json", "01_specs/PRD-v1.0.0.md", "01_specs/adr_draft.md"]);
  for (const value of Object.values(digests)) expect(value).toMatch(/^sha256:[0-9a-f]{64}$/);
  const capabilities = dataOf<{ researchRoot?: string | null }>(await call(request, ADMIN, "GET", "/api/v1/research/capabilities"));
  const root = capabilities.researchRoot ?? "";
  if (root === "") {
    test.info().annotations.push({ type: "檔案位元組略過", description: "能力探針沒有 researchRoot：無從組出容器內路徑" });
  } else {
    for (const [relative, digest] of Object.entries(digests)) {
      const out = inContainer(["sha256sum", `${root}/${project.slug}/${relative}`]);
      if (out === null) {
        test.info().annotations.push({ type: "檔案位元組略過", description: "TOOL-ABSENCE：沒有 docker CLI" });
        break;
      }
      expect(`sha256:${out.split(/\s+/)[0]}`, `${relative} 的凍結摘要與容器內檔案位元組`).toBe(digest);
    }
  }

  // 二次核准：409 fsm_state_conflict（狀態機已不在 HUMAN_PENDING）。送的是剛核准的那一版（最新的 DRAFT）：核准後多出來的 BASELINE 版不是 Bridge 認的「head」，
  // 送它會先撞 review_not_passed（Bridge 先比版本、再比狀態機現態），那是另一條路徑
  const versions = dataOf<Array<{ versionNo: number; kind: string }>>(await call(request, ADMIN, "GET", projectPath(project.id, "/prd/versions")));
  const approved = versions.filter((v) => v.kind === "DRAFT").reduce((a, v) => (v.versionNo > a.versionNo ? v : a));
  const again = await call(request, ADMIN, "POST", projectPath(project.id, "/approve"), {
    prdVersion: approved.versionNo,
    expectedDigests: { "01_specs/PRD-v1.0.0.md": digests["01_specs/PRD-v1.0.0.md"] },
  });
  expect(again.status, `二次核准 → ${JSON.stringify(again.json)}`).toBe(409);
  expect(again.json.reason).toBe("fsm_state_conflict");

  // 對帳：一致（INT-01／05／10 修復後；對帳結果列以 id 命名）
  const reconcile = await call(request, ADMIN, "POST", projectPath(project.id, "/reconcile"), {});
  expect(reconcile.status, `對帳 → ${JSON.stringify(reconcile.json)}`).toBe(200);
  const result = dataOf<{ consistent: boolean; checks: Array<{ name: string; status: string }> }>(reconcile);
  expect(result.checks.map((c) => c.name).sort(), "對帳六項以 Bridge 的 id 命名（INT-01）").toEqual([
    "evidence_matrix",
    "fsm_flow_mapping",
    "prd_sha256",
    "review_card",
    "route_decision",
    "task_decomposition",
  ]);
  expect(result.consistent, `對帳結果 ${JSON.stringify(result.checks)}`).toBe(true);
});

/** 在 Bridge 容器內執行指令；沒有 docker CLI 回 null（呼叫端註記略過）；容器不存在或指令失敗＝真錯誤，丟出。 */
function inContainer(args: string[]): string | null {
  try {
    return execFileSync("docker", ["exec", BRIDGE_CONTAINER, ...args], { encoding: "utf-8", timeout: 30_000 }).trim();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

// ── AT-960-22-4 SSE 斷線重播無缺漏、重整後動態欄由資料庫重建 ───────────────────────────────────

test("AT_960_22_4 SSE 斷線重播無缺漏：載入前 route.abort 串流（Playwright 的 setOffline 切不斷已建立的 EventSource，INT-12）、期間有事件，解除後自動重連、seq 連續無缺漏無重複；重載後動態欄與資料庫相同", async ({
  page,
  context,
  request,
}) => {
  test.setTimeout(900_000);
  const project = await createProject(request, "sse");
  await runStage(request, project.id, "research");
  await signIn(page, request, ADMIN);

  const feed = page.getByTestId("research-timeline");
  const uiSeqs = (): Promise<number[]> => page.getByTestId("timeline-event").evaluateAll((els) => els.map((e) => Number(e.getAttribute("data-seq"))));
  const contiguous = (seqs: number[]): boolean => seqs.every((seq, i) => seq === i + 1);

  // 載入前就擋住串流：連線失敗、狀態顯示不是「即時連線中」；期間（以 API）再產生一批事件
  let blocked = 0;
  await context.route("**/api/v1/stream/research/**", (route) => {
    blocked += 1;
    return route.abort("connectionrefused");
  });
  await open(page, request, `${BASE}/research/${project.id}?step=topic`);
  await expect(feed).toBeVisible({ timeout: 60_000 });
  await expect.poll(async () => feed.getAttribute("data-connection"), { message: "串流被擋：連線狀態不是 open", timeout: 30_000 }).not.toBe("open");
  expect(blocked, "串流請求確實被攔到").toBeGreaterThan(0);
  const draft = await runStage(request, project.id, "draft");
  expect(draft.headPrdVersion).toBe(1);
  const duringBlock = await eventSeqs(request, project.id);

  // 解除封鎖：自動重連（不必按鈕），事件補齊，序號自 1 連續、無重複、與資料庫相同
  await context.unroute("**/api/v1/stream/research/**");
  await expect.poll(async () => feed.getAttribute("data-connection"), { message: "解除後自動重連（open）", timeout: 90_000, intervals: [1000] }).toBe("open");
  // [新 frontend] INT-12：出過錯的連線（第一次連線就被擋）重新開啟時以 REST 補抓，沒有任何新事件也補齊；舊映像要等下一筆即時事件才靠缺口偵測補齊（下面的對帳事件）
  const backfilled = await expect
    .poll(async () => JSON.stringify(await uiSeqs()), { message: "動態欄補齊到資料庫的事件（不靠新事件）", timeout: 30_000 })
    .toBe(JSON.stringify(duringBlock))
    .then(
      () => true,
      () => false,
    );
  expect.soft(backfilled, "[新 frontend] INT-12：重連後（沒有新事件）動態欄就補齊到資料庫").toBe(true);

  // 重連後的即時事件：對帳會追加一筆 research.reconcile，應在數秒內到畫面（走串流，不是整頁重抓）；之後動態欄＝資料庫（缺口偵測也會補齊）、seq 自 1 連續無缺漏無重複
  const before = (await uiSeqs()).length;
  expect((await call(request, ADMIN, "POST", projectPath(project.id, "/reconcile"), {})).status).toBe(200);
  await expect.poll(async () => (await uiSeqs()).length, { message: "重連後的即時事件到畫面", timeout: 15_000, intervals: [250] }).toBeGreaterThan(before);
  await expect.poll(async () => JSON.stringify(await uiSeqs()), { message: "即時事件之後動態欄＝資料庫", timeout: 30_000 }).toBe(JSON.stringify(await eventSeqs(request, project.id)));
  expect(contiguous(await uiSeqs()), "重連後 seq 自 1 連續、無缺漏、無重複").toBe(true);

  // 重新載入：動態欄內容與結束前最後畫面相同（由資料庫重建）
  const lastScreen = await uiSeqs();
  await ensureQuota(request, ADMIN);
  await page.reload();
  await expect(feed).toBeVisible({ timeout: 60_000 });
  await expect.poll(async () => JSON.stringify(await uiSeqs()), { message: "重載後動態欄＝重載前最後畫面", timeout: 60_000 }).toBe(JSON.stringify(lastScreen));
  expect(JSON.stringify(lastScreen), "重載前最後畫面＝資料庫").toBe(JSON.stringify(await eventSeqs(request, project.id)));
});

// ── AT-960-22-2 路徑 A：fail3 劇本、三輪 FAIL、ESCALATION ──────────────────────────────────────

test("AT_960_22_2 路徑 A：三輪審查都未通過、第 3 輪 ESCALATE；FSM 現態 ESCALATION（不是 AUTO_RECOVERY_ATTEMPT）；工作室有 ESCALATION 區塊與可複製的恢復指令、沒有恢復動詞按鈕；R1～R5、R9、R13、R14 各至少一筆、R6 為零", async ({
  page,
  request,
}) => {
  test.setTimeout(900_000);
  test.skip(
    SCRIPT_KIND !== "fail3",
    `需要 fail3 劇本：compose 的 MOCK_CLAUDE_RESEARCH_SCRIPT 指向 mock_claude_script_fail3.json，且執行 Playwright 的 shell 設同一個值（目前＝${SCRIPT === "" ? "（未設）" : SCRIPT}；切換劇本要重建／重啟 Bridge 容器）`,
  );
  const project = await createProject(request, "fail3");
  await runStage(request, project.id, "research");
  await runStage(request, project.id, "draft");
  await runStage(request, project.id, "review");
  let detail = await detailOf(request, project.id);
  for (let i = 0; i < 3 && detail.flowStatus !== "ESCALATED"; i += 1) detail = await runStage(request, project.id, "iterate");
  expect(detail.flowStatus, `迭代停止後的游標 ${JSON.stringify(detail)}`).toBe("ESCALATED");

  const rounds = await roundsOf(request, project.id);
  expect(
    rounds.map((r) => [r.roundNo, r.weightedScore?.toFixed(2), r.verdict]),
    "三輪（fail3 劇本）",
  ).toEqual([
    [1, "79.90", "REVISE"],
    [2, "82.75", "REVISE"],
    [3, "84.60", "ESCALATE"],
  ]);
  const fsm = dataOf<{ currentState: string }>(await call(request, ADMIN, "GET", projectPath(project.id, "/fsm")));
  expect(fsm.currentState).toBe("ESCALATION");
  expect(fsm.currentState).not.toBe("AUTO_RECOVERY_ATTEMPT");

  // 紀錄稽核：R1～R5、R9、R13、R14 各至少一筆、R6（Gate 決定）為零
  const audit = dataOf<{ classes: Array<{ id: string; count: number }> }>(await call(request, ADMIN, "GET", projectPath(project.id, "/records/audit")));
  const countOf = (id: string): number => audit.classes.find((c) => c.id === id)?.count ?? -1;
  for (const id of ["R1", "R2", "R3", "R4", "R5", "R9", "R13", "R14"]) expect(countOf(id), `${id} 至少一筆`).toBeGreaterThanOrEqual(1);
  expect(countOf("R6"), "R6（Gate 決定）為零").toBe(0);

  // UI：ESCALATION 區塊、可複製恢復指令、沒有恢復動詞按鈕
  await signIn(page, request, ADMIN);
  await open(page, request, `${BASE}/research/${project.id}?step=studio`);
  const section = page.getByTestId("escalation-section");
  await expect(section).toBeVisible({ timeout: 60_000 });
  await expect(section).toContainText("resume-from-escalation");
  await expect(section.getByTestId("escalation-state")).toContainText("ESCALATION");
  await expect(section.getByRole("button", { name: /複製/ }).first()).toBeVisible();
  const buttons = (await section.getByRole("button").allInnerTexts()).map((t) => t.trim()).filter((t) => !/複製/.test(t));
  expect(buttons, "區塊內的動作按鈕恰為兩顆（我已恢復，繼續／換世代）").toEqual(["我已恢復，繼續（僅一次機會）", "換世代"]);
  expect(
    buttons.filter((t) => /恢復|resume/i.test(t) && t !== "我已恢復，繼續（僅一次機會）"),
    "沒有任何恢復動詞按鈕",
  ).toEqual([]);
});
