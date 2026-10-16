import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { API_URL, RUN, loginViaUi } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import { bootstrapSettings, call, dataOf, ensureQuota, getRun, parseSse, poll, tokenOf, waitRun, type SseFrame } from "./realBackend";

/**
 * Docker 全棧（經 nginx、同源）——W4-QA 矩陣 D／I 與契約 §6.2 #20：
 *   `docker compose --profile db --profile app --profile full up -d` 之後，用瀏覽器與 REST 走一次真實入口。
 * Docker 全棧不載入 e2e profile（沒有 allow-loopback、mock-env），所以：匯入走路徑 A（凍結規格放進 Bridge 容器的 /workspace），
 * 執行用映像內建的 aisdlc-mock-claude（PATH 上）；evaluator 的 `pytest tests -k …` 用 Bridge 映像自帶的 pytest。
 * 執行方式見 docker.config.ts。需要 docker CLI（寫入夾具、重啟 backend、讀 nginx 日誌）。
 */
const execFileAsync = promisify(execFile);
const BRIDGE = process.env.E2E_BRIDGE_CONTAINER ?? "aisdlc-engine-bridge";
const BACKEND = process.env.E2E_BACKEND_CONTAINER ?? "aisdlc-backend";
const NGINX = process.env.E2E_NGINX_CONTAINER ?? "aisdlc-nginx";
const MOCK_CLAUDE = process.env.E2E_MOCK_CLAUDE ?? "aisdlc-mock-claude";
const WORKSPACE = "/workspace/projects";
const FIRST_LOAD = { timeout: 60_000 };

/** 本檔用過、可能出現在 URL 查詢字串（SSE 的 access_token）的 JWT：最後拿去比對 nginx 日誌。 */
const usedTokens = new Set<string>();

async function docker(...args: string[]): Promise<{ stdout: string; stderr: string }> {
  return execFileAsync("docker", args, { timeout: 180_000, maxBuffer: 64 * 1024 * 1024 });
}

/** 在 Bridge 容器內以 bridge 使用者寫檔（內容以 base64 帶入，不經 docker cp，檔案擁有者就是 bridge）。 */
async function putFiles(files: Record<string, string>): Promise<void> {
  const encoded = Object.fromEntries(Object.entries(files).map(([p, c]) => [p, Buffer.from(c, "utf-8").toString("base64")]));
  const payload = Buffer.from(JSON.stringify(encoded), "utf-8").toString("base64");
  const script =
    "import base64,json,pathlib,sys;[(pathlib.Path(p).parent.mkdir(parents=True,exist_ok=True),pathlib.Path(p).write_bytes(base64.b64decode(b))) for p,b in json.loads(base64.b64decode(sys.argv[1])).items()]";
  await docker("exec", BRIDGE, "python", "-c", script, payload);
}

/** 凍結的 SDD 規格夾具：FSM 狀態檔、三個合約（Then 斷言是引號包住的 [ATn_DONE]，mock claude 會回放 prompt 裡的 [KEYWORD]）、對應的 pytest 測試。 */
function sddFiles(root: string): Record<string, string> {
  const ids = [1, 2, 3].map((n) => `AT-00${n}-1-1`);
  const rows = ids.map((at, i) => `| AC-00${i + 1}-1 | 驗收 ${i + 1} | ${at} | 情境 ${i + 1} | ✅ | Unit | □ |`);
  const blocks = ids.map((at, i) => `\`\`\`gherkin\n# ${at}\nScenario: 情境 ${i + 1}\n  Given 前置條件\n  When 執行動作\n  Then 輸出「[AT${i + 1}_DONE]」\n\`\`\``);
  const fsm =
    "fsm_state:\n  project: demo\n  session_id: sid-1\n  current_state: IMPLEMENTATION\n  current_sprint: 2\n  updated_at: '2026-10-14T00:00:00+00:00'\n  frozen_stages:\n  - stage: SCG-0\n  decision_trace:\n  - {ts: t0, from: S0, to: S1, reason: r0}\n";
  const md = `# Test Contract Specification — Demo\n\n場景：brownfield 既有系統改進\n\n## 1. AC → AT 映射表\n\n| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |\n|-------|---------|-------|---------|-------|---------|------|\n${rows.join("\n")}\n\n## 2. AT 格式\n\n${blocks.join("\n\n")}\n`;
  const tests = ids.map((at) => `def test_${at.replace(/-/g, "_")}_basic():\n    assert True\n`).join("\n");
  return {
    [`${root}/build/reports/fsm/FSM-STATE-demo.yaml`]: fsm,
    [`${root}/docs/03_testing/contracts/TEST-CONTRACT-SPEC-Demo.md`]: md,
    [`${root}/tests/test_demo.py`]: tests,
  };
}

type StackFixture = { projectId: string; name: string; dir: string; goalIds: string[]; taskIds: string[] };

/** 契約 §5.0.3 的 PRJ-A（G1：T1、T2；G2：T3，依賴 G1），專案目錄建在 Bridge 容器的 /workspace 底下。 */
async function createStackFixture(request: APIRequestContext, name: string, level: number): Promise<StackFixture> {
  const dir = `${WORKSPACE}/${name.replace(/[^A-Za-z0-9_-]/g, "_")}`;
  await docker("exec", BRIDGE, "mkdir", "-p", dir);
  const p = await call(request, "operator", "POST", "/api/v1/projects", { name, executionPath: dir, passCriteria: "全部完成", description: "QA Docker 夾具", autonomyLevel: level, draft: false });
  expect(p.status, `建專案 → ${JSON.stringify(p.json)}`).toBe(201);
  const projectId = dataOf<{ id: string }>(p).id;
  const layout: Array<[string, string[]]> = [
    ["基礎", ["初始化", "設定"]],
    ["核心", ["實作"]],
  ];
  const goalIds: string[] = [];
  const taskIds: string[] = [];
  let n = 0;
  for (const [goalName, taskNames] of layout) {
    const g = await call(request, "operator", "POST", `/api/v1/projects/${projectId}/goals`, {
      name: goalName,
      passCriteria: `${goalName}任務完成`,
      description: "",
      dependsOn: goalIds.length > 0 ? [goalIds[goalIds.length - 1]] : [],
      draft: false,
    });
    expect(g.status, `建目標 → ${JSON.stringify(g.json)}`).toBe(201);
    const goalId = dataOf<{ id: string }>(g).id;
    goalIds.push(goalId);
    for (const taskName of taskNames) {
      n += 1;
      const t = await call(request, "operator", "POST", `/api/v1/goals/${goalId}/tasks`, {
        name: taskName,
        description: `請輸出 [T${n}_DONE]`,
        passCriteria: `輸出含 [T${n}_DONE]`,
        expectedOutputRegex: `\\[T${n}_DONE\\]`,
        maxRetries: 1,
        draft: false,
      });
      expect(t.status, `建任務 → ${JSON.stringify(t.json)}`).toBe(201);
      taskIds.push(dataOf<{ id: string }>(t).id);
    }
  }
  return { projectId, name, dir, goalIds, taskIds };
}

/** 記下目前頁面 session 裡的 access token（EventSource 會把它放進 URL）。 */
async function noteSessionToken(page: Page): Promise<void> {
  const raw = await page.evaluate(() => window.sessionStorage.getItem("aisdlc.console.session"));
  const token = raw ? (JSON.parse(raw) as { accessToken?: string }).accessToken : undefined;
  if (token) usedTokens.add(token);
}

/** 審核卡：點某個決定 → 確認對話框 → 送出。 */
async function decide(page: Page, decision: "approve" | "retry" | "skip" | "reject"): Promise<void> {
  await page.getByTestId(`review-${decision}`).click();
  await expect(page.getByTestId("review-dialog")).toBeVisible();
  await page.getByTestId("review-confirm").click();
  await expect(page.getByTestId("review-dialog")).toHaveCount(0);
}

type TimedFrame = { at: number; frame: SseFrame };

/** 讀一條 SSE 最多 maxMs 毫秒，記下每個框架的到達時間（毫秒，自連線起算）；stillOpen＝到時間時連線仍開著（沒被伺服器結束）。 */
async function timedSse(url: string, maxMs: number): Promise<{ status: number; contentType: string; frames: TimedFrame[]; stillOpen: boolean }> {
  const ctrl = new AbortController();
  const t0 = Date.now();
  const timer = setTimeout(() => ctrl.abort(), maxMs);
  const frames: TimedFrame[] = [];
  let status = 0;
  let contentType = "";
  let stillOpen = false;
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    status = res.status;
    contentType = res.headers.get("content-type") ?? "";
    if (res.body) {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        for (let end = buffer.indexOf("\n\n"); end >= 0; end = buffer.indexOf("\n\n")) {
          const chunk = buffer.slice(0, end);
          buffer = buffer.slice(end + 2);
          for (const frame of parseSse(`${chunk}\n\n`).frames) frames.push({ at: Date.now() - t0, frame });
        }
      }
    }
  } catch {
    stillOpen = ctrl.signal.aborted; // AbortError：是我們自己在 maxMs 到時切的
  } finally {
    clearTimeout(timer);
  }
  return { status, contentType, frames, stillOpen };
}

async function backendHealth(): Promise<string> {
  const { stdout } = await docker("inspect", "-f", "{{.State.Health.Status}}", BACKEND);
  return stdout.trim();
}

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator");
});

test.describe("Docker 全棧（經 nginx、同源）", () => {
  test.setTimeout(300_000);

  test("入口：首頁 200、/nginx-health、/actuator/ 被封、無 token 401；未登入導向 /login，UI 登入後導回", async ({ page, request }) => {
    const home = await request.get(`${API_URL}/`, { failOnStatusCode: false });
    expect(home.status()).toBe(200);
    expect(home.headers()["content-type"]).toContain("text/html");
    expect((await request.get(`${API_URL}/nginx-health`, { failOnStatusCode: false })).status()).toBe(200);
    expect((await request.get(`${API_URL}/actuator/health`, { failOnStatusCode: false })).status()).toBe(403);
    const anon = await request.get(`${API_URL}/api/v1/projects`, { failOnStatusCode: false });
    expect(anon.status()).toBe(401);
    await page.goto("/projects");
    await expect(page).toHaveURL(/\/login\?next=%2Fprojects/);
    await expect(page.getByRole("heading", { name: "登入 AISDLC Console" })).toBeVisible();
    await loginViaUi(page);
    await expect(page).toHaveURL(/\/projects$/);
    await snap(page, "p8-docker-projects.png");
  });

  test("路徑 A 全鏈（UI）：凍結規格 → 規格驅動解析 → signoff → confirm → 執行 Level 4 → 進度逐步前進 → COMPLETED", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    const root = `${WORKSPACE}/sdd-${RUN}`;
    await putFiles(sddFiles(root));
    await page.goto("/login");
    await loginViaUi(page);
    await noteSessionToken(page);
    await page.goto("/import");
    await expect(page.getByRole("heading", { name: "BRD / PRD 智能匯入" })).toBeVisible(FIRST_LOAD);
    await page.getByRole("tab", { name: "貼上文字" }).click();
    await page.getByLabel("需求文字").fill("凍結規格匯入（短內容）");
    await page.getByLabel("格式").selectOption("PLAIN_TEXT");
    await page.getByLabel(/^自治等級/).selectOption("2"); // 解析前選擇自治等級（US-I-07）：成為專案的自治等級
    await page.getByLabel("執行路徑").fill(root);
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("parse-path")).toHaveText("規格驅動（SDD）");
    await expect(page.getByTestId("tree-goal")).toHaveCount(1);
    await expect(page.getByTestId("task-name")).toHaveText(["AT-001-1-1", "AT-002-1-1", "AT-003-1-1"]);
    await snap(page, "p8-docker-import-sdd.png", { tall: true });
    await page.getByRole("button", { name: "signoff 審批" }).click();
    await page.getByRole("dialog", { name: "審批 signoff：匯入草案" }).getByRole("button", { name: "確認 signoff" }).click();
    await expect(page.getByTestId("import-signed-off")).toContainText("已 signoff");
    await page.getByRole("button", { name: "確認匯入" }).click();
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/);
    const projectId = page.url().split("/").at(-1)!;

    await page.goto(`/projects/${projectId}/execute`);
    await expect(page.getByTestId("control-start")).toBeEnabled(FIRST_LOAD);
    await expect(page.getByTestId("exec-level")).toHaveValue("2"); // 解析前選的自治等級成為專案的等級
    await page.getByTestId("exec-level").selectOption("4");
    await page.getByTestId("exec-budget").fill("100,000");
    const seen: string[] = [];
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-number")).toHaveText("Run #1");
    await expect
      .poll(
        async () => {
          const text = ((await page.getByTestId("progress-tasks").textContent()) ?? "").trim();
          if (seen.at(-1) !== text) seen.push(text);
          return page.getByTestId("run-status").getAttribute("data-status");
        },
        { timeout: 150_000, intervals: [100] },
      )
      .toBe("COMPLETED");
    // SSE 經 nginx 逐步到達：進度不是一次從 0 跳到 3（觀察到的序列留在斷言訊息裡）
    expect(seen.length, `進度序列：${seen.join(" → ")}`).toBeGreaterThanOrEqual(3);
    await expect(page.getByTestId("progress-tasks")).toHaveText("3 / 3 任務完成");
    await snap(page, "p8-docker-executed.png", { tall: true });
    const runs = dataOf<{ content: Array<{ id: string }> }>(await call(request, "viewer", "GET", `/api/v1/projects/${projectId}/executions?sort=runNumber,desc&size=5`)).content;
    const run = await waitRun(request, runs[0].id, ["COMPLETED"]);
    expect(run).toMatchObject({ status: "COMPLETED", completedSteps: 3, totalSteps: 3, totalTokensUsed: 3720 });
    expect(run.bridge).toMatchObject({ connected: true });
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("SSE 經 nginx（proxy_buffering off）：暫停中的串流先送重播框架（連線仍開著、不等到結束才一次吐出）", async ({ request }) => {
    const f = await createStackFixture(request, `QA Docker 串流 ${RUN}`, 1);
    const started = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: 1, tokenBudget: 100000, scope: { mode: "ALL" } });
    expect(started.status, JSON.stringify(started.json).slice(0, 300)).toBe(201);
    const runId = dataOf<{ id: string }>(started).id;
    await waitRun(request, runId, ["PAUSED"], 90_000); // 等級 1：第一步後暫停，PAUSED 不是終態、串流不會結束
    const viewer = await tokenOf(request, "viewer");
    usedTokens.add(viewer);
    const raw = await timedSse(`${API_URL}/api/v1/stream/executions/${runId}/logs?access_token=${viewer}`, 8_000);
    expect(raw.status).toBe(200);
    expect(raw.contentType).toContain("text/event-stream");
    expect(raw.stillOpen, "到時間時連線仍開著（沒有被當成終態結束）").toBe(true);
    expect(raw.frames.length, `框架到達時間（ms）：${raw.frames.map((x) => `${x.frame.event}@${x.at}`).join("、")}`).toBeGreaterThanOrEqual(3);
    expect(raw.frames[0].at, "第一個框架在連線後 3 秒內到達（緩衝時要等到連線結束才會一次吐出）").toBeLessThan(3_000);
    expect(raw.frames.at(-1)!.at).toBeLessThan(6_000);
    expect(raw.frames.map((x) => x.frame.event)).toEqual(expect.arrayContaining(["status-change", "log"]));
    console.log(`[docker-sse] 暫停中串流：${raw.frames.length} 個框架，到達 ${raw.frames.map((x) => x.at).join("、")} ms，連線保持開著`);
    await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`);
  });

  test("重啟 backend → 前端串流重連、session 不得被清除、不重複 → 通過審核跑完（矩陣 I；DEF-AC-007／契約 E2E-13 列 5，W5 已修）", async ({ page, request }) => {
    // 缺陷 DEF-AC-007（P2，W5-FE 已修；本支在 W5-QA 移除了 test.fail）：SSE 重連路徑換 token（POST /auth/refresh）時 backend 還沒起來（nginx 回 502），
    // W4 的前端把任何換新失敗都當成登入失效，清掉 session 並導向 /login。本機直連 backend 的重啟只有約 10 秒、重連先成功所以沒踩到；全棧經 nginx 約 15～40 秒。
    // C-5：換新失敗分 renewed／invalid／unavailable 三類，只有 invalid（400／401／403）才登出；SSE 以 1→2→4→…→30 秒退避重連並維持「重新連線中」。
    const f = await createStackFixture(request, `QA Docker SSE ${RUN}`, 1);
    await page.goto("/login");
    await loginViaUi(page);
    await noteSessionToken(page);
    await page.goto(`/projects/${f.projectId}/execute`);
    await expect(page.getByRole("heading", { name: `專案執行：${f.name}` })).toBeVisible(FIRST_LOAD);
    await page.getByTestId("exec-level").selectOption("1");
    await page.getByTestId("exec-budget").fill("100,000");
    const streamReqs: Array<{ url: string; lastEventId: string | null }> = [];
    page.on("request", (r) => {
      if (r.url().includes("/api/v1/stream/")) {
        void r.allHeaders().then((h) => streamReqs.push({ url: r.url().replace(/access_token=[^&]+/, "access_token=…"), lastEventId: h["last-event-id"] ?? null }));
      }
    });
    await page.getByTestId("control-start").click();
    await expect(page.getByTestId("run-status")).toContainText("已暫停", { timeout: 90_000 });
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open"); // PAUSED 不結束串流
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    await snap(page, "p8-docker-paused.png", { tall: true });

    const runs = dataOf<{ content: Array<{ id: string }> }>(await call(request, "viewer", "GET", `/api/v1/projects/${f.projectId}/executions?sort=runNumber,desc&size=5`)).content;

    // 重啟 backend：前端的串流被切斷 → 重連中；backend 起來後連回、補齊且不重複
    const before = streamReqs.length;
    const restart = docker("restart", BACKEND);
    await expect(page.getByTestId("sse-status")).not.toHaveAttribute("data-state", "open", { timeout: 60_000 });
    await snap(page, "p8-docker-sse-reconnecting.png");
    await restart;
    await poll(backendHealth, (s) => s === "healthy", "backend 容器 healthy", 240_000, 3_000);
    await expect(page.getByTestId("sse-status")).toHaveAttribute("data-state", "open", { timeout: 120_000 });
    const reconnects = streamReqs.slice(before).filter((r) => r.url.includes("/logs"));
    expect(reconnects.length, `重連的 /logs 請求：${JSON.stringify(reconnects)}`).toBeGreaterThanOrEqual(1);
    await expect(page.getByTestId("run-status")).toContainText("已暫停");
    await expect(page.getByTestId("review-row")).toHaveCount(1);
    await expect(page.getByTestId("log-line").filter({ hasText: "開始：初始化" })).toHaveCount(1);
    await expect(page.getByTestId("log-line").filter({ hasText: "完成：初始化" })).toHaveCount(1);
    await snap(page, "p8-docker-sse-reconnected.png", { tall: true });
    await noteSessionToken(page);
    await decide(page, "approve");
    await expect(page.getByTestId("progress-tasks")).toHaveText("2 / 3 任務完成", { timeout: 90_000 });
    await expect(page.getByTestId("review-reason")).toContainText("任務「實作」", { timeout: 90_000 });
    await decide(page, "approve");
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "COMPLETED", { timeout: 120_000 });
    expect(await getRun(request, runs[0].id)).toMatchObject({ status: "COMPLETED", totalTokensUsed: 3720 });
  });

  test("上傳大小經 nginx：剛好 10MB → 201；超過 10MB 但封裝後仍 < 11MB → 後端 413；12MB → nginx 413", async ({ request }) => {
    const token = await tokenOf(request, "operator");
    const upload = (name: string, size: number) =>
      request.fetch(`${API_URL}/api/v1/import/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        multipart: { file: { name, mimeType: "application/octet-stream", buffer: Buffer.alloc(size, 97) } },
        failOnStatusCode: false,
        timeout: 120_000,
      });
    const mb = 1024 * 1024;
    const exact = await upload(`ten-${RUN}.md`, 10 * mb);
    expect(exact.status(), await exact.text()).toBe(201);
    const id = ((await exact.json()) as { data: { id: string } }).data.id;
    await call(request, "operator", "POST", `/api/v1/import/${id}/reject`);
    const over = await upload(`over-${RUN}.md`, 10 * mb + 1);
    expect([over.status(), ((await over.json()) as { reason: string }).reason]).toEqual([413, "檔案超過 10MB 上限"]);
    const huge = await upload(`huge-${RUN}.md`, 12 * mb);
    expect(huge.status()).toBe(413);
    expect(huge.headers()["content-type"] ?? "").toContain("text/html"); // nginx 自己擋下：不是後端的 JSON
  });

  test("nginx access log：access_token 的值不出現，SSE 請求只留路徑（契約 §0.7 第 4 點）", async () => {
    const { stdout } = await docker("logs", NGINX);
    expect(usedTokens.size).toBeGreaterThanOrEqual(2);
    for (const token of usedTokens) expect(stdout.includes(token), "access log 不得含 token 值").toBe(false);
    expect(stdout).toMatch(/GET \/api\/v1\/stream\/executions\/[0-9a-f-]{36}\/(logs|metrics)\?\*\*\* HTTP/);
    expect(stdout).not.toMatch(/access_token=/);
  });

  test("nginx error log：重啟 backend 造成的上游錯誤，不得把 access_token 的值印進去（契約 §0.7 第 4 點的殘留風險；DEF-AC-008，W5 已修）", async () => {
    // 缺陷 DEF-AC-008（P3，W5-INFRA 已修；本支在 W5-QA 移除了 test.fail）：W4 的 nginx 在上游被切斷時於 [error] 行印出完整請求行（含 ?access_token=<JWT>），
    // log_format 管不到 error_log。C-15：error_log 降為 crit（要除錯時暫改回 error 並清檔）。
    const { stderr } = await docker("logs", NGINX);
    const leaked = [...usedTokens].filter((t) => stderr.includes(t));
    const sample = (stderr.split("\n").find((l) => l.includes("access_token")) ?? "").replace(/access_token=[^&" ]+/g, "access_token=<redacted-in-report>");
    expect(leaked.length, `error log 出現 ${leaked.length} 個 token 的值；樣本行：${sample}`).toBe(0);
  });

  test("C-15／O-08／O-09｜經 nginx：/api/health 回前端自己的 200（不再被反代到 backend 而回 401）；/_next/static 的 Cache-Control 恰好一份", async ({ request }) => {
    const health = await request.get(`${API_URL}/api/health`, { failOnStatusCode: false });
    expect(health.status(), "W4：/api/ 整段被反代到 backend，回 401").toBe(200);
    expect(await health.json()).toEqual({ status: "ok" });
    const home = await (await request.get(`${API_URL}/`)).text();
    const asset = home.match(/\/_next\/static\/[^"'\\)]+\.(?:js|css)/)?.[0];
    expect(asset, "首頁引用了 /_next/static 的資源").toBeTruthy();
    const res = await request.get(`${API_URL}${asset}`);
    expect(res.status()).toBe(200);
    const cacheControl = res.headersArray().filter((h) => h.name.toLowerCase() === "cache-control");
    expect(
      cacheControl.map((h) => h.value),
      "W4：nginx 與 Next 各加一份（共兩份）",
    ).toEqual(["public, max-age=31536000, immutable"]);
  });

  test("BR-26／DEF-AC-003｜Bridge 深度探針（全棧）：容器 healthcheck 打 /health/deep 且 healthy、映像內 git 可執行、/health/deep 200 且四項檢查皆 ok；移走 git 後 503（淺層 /health 仍 200）並使容器轉 unhealthy；還原後回到 healthy", async () => {
    test.setTimeout(420_000);
    const state = async () => (await docker("inspect", "-f", "{{.State.Health.Status}}", BRIDGE)).stdout.trim();
    const probe =
      "import urllib.request as u,urllib.error as e,sys\ntry:\n r=u.urlopen(sys.argv[1],timeout=9); print(r.status, r.read().decode())\nexcept e.HTTPError as x:\n print(x.code, x.read().decode())";
    const get = async (p: string) => (await docker("exec", BRIDGE, "python", "-c", probe, `http://127.0.0.1:8081${p}`)).stdout.trim();
    type Deep = {
      status: string;
      reason?: string;
      checks: { git: { ok: boolean; version?: string; reason?: string }; autoclaude: { ok: boolean }; workspace: { ok: boolean }; db: { ok: boolean | null } };
    };
    const parse = (s: string): { code: number; body: Deep } => ({ code: Number(s.slice(0, 3)), body: JSON.parse(s.slice(4)) as Deep });

    expect((await docker("inspect", "-f", "{{json .Config.Healthcheck.Test}}", BRIDGE)).stdout, "容器的 healthcheck 打 /health/deep").toContain("/health/deep");
    expect(await state()).toBe("healthy");
    expect((await docker("exec", BRIDGE, "git", "--version")).stdout, "映像內 git 可執行（W4：沒有 git）").toMatch(/^git version \d+\./);
    const ok = parse(await get("/health/deep"));
    expect(ok.code, JSON.stringify(ok.body)).toBe(200);
    expect(ok.body.status).toBe("ok");
    expect(ok.body.checks.git.ok).toBe(true);
    expect(ok.body.checks.git.version ?? "").toMatch(/^git version /);
    expect([ok.body.checks.autoclaude.ok, ok.body.checks.workspace.ok, ok.body.checks.db.ok], "autoclaude／workspace／db（DB 模式：true）").toEqual([true, true, true]);

    const gitPath = (await docker("exec", BRIDGE, "sh", "-c", "command -v git")).stdout.trim();
    expect(gitPath).toMatch(/^\/.+git$/);
    await docker("exec", "-u", "root", BRIDGE, "mv", gitPath, `${gitPath}.qa-off`);
    try {
      const bad = parse(await get("/health/deep"));
      expect(bad.code, JSON.stringify(bad.body)).toBe(503);
      expect(bad.body.status).toBe("degraded");
      expect(bad.body.checks.git.ok).toBe(false);
      expect(bad.body.reason ?? "").toContain("git");
      expect(Number((await get("/health")).slice(0, 3)), "淺層 /health 仍 200——DEF-AC-003 當時看不見問題的原因").toBe(200);
      await poll(state, (s) => s === "unhealthy", "缺 git 時 bridge 容器轉 unhealthy（W4：永遠 healthy）", 180_000, 5_000);
    } finally {
      await docker("exec", "-u", "root", BRIDGE, "mv", `${gitPath}.qa-off`, gitPath);
    }
    await poll(state, (s) => s === "healthy", "git 還原後 bridge 容器回到 healthy", 180_000, 5_000);
    expect(parse(await get("/health/deep")).code).toBe(200);
  });

  test("C-12／NFR-9.4-04／INF-VOL-06（全棧）｜X-Trace-Id 貫穿：經 nginx 啟動批次，回應的 X-Trace-Id 出現在 Bridge 日誌的 POST /autoclaude/runs 行；Bridge 日誌每一行有 trace_id（容器 stderr 與卷內 bridge.log）；backend 的卷內 console.log 是 JSON 行", async ({
    request,
  }) => {
    const f = await createStackFixture(request, `QA Docker trace ${RUN}`, 4);
    const started = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
    expect(started.status, JSON.stringify(started.json).slice(0, 300)).toBe(201);
    const traceId = started.headers["x-trace-id"];
    expect(traceId).toBeTruthy();
    const runId = dataOf<{ id: string }>(started).id;
    await waitRun(request, runId, ["COMPLETED"], 150_000);

    const r = await docker("logs", BRIDGE);
    const lines = `${r.stdout}\n${r.stderr}`.split("\n").filter((l) => l.trim() !== "");
    const hit = lines.filter((l) => l.includes(`trace_id=${traceId} `));
    expect(
      hit.some((l) => l.includes("POST /autoclaude/runs") && l.includes(" 201")),
      `Bridge 容器日誌裡找不到 trace_id=${traceId} 的 POST /autoclaude/runs：${hit.slice(0, 3).join(" ⏎ ")}`,
    ).toBe(true);
    expect(hit.length, "同一個 trace id 還貫穿該批次的其他 Bridge 請求").toBeGreaterThanOrEqual(2);
    expect(
      lines.filter((l) => !/ trace_id=\S+/.test(l)),
      "容器日誌沒有 trace_id 的行",
    ).toEqual([]);
    const fileLines = (await docker("exec", BRIDGE, "cat", "/app/logs/bridge.log")).stdout.split("\n").filter((l) => l.trim() !== "");
    expect(fileLines.length).toBeGreaterThan(10);
    expect(
      fileLines.filter((l) => !/ trace_id=\S+/.test(l)),
      "卷內 bridge.log 沒有 trace_id 的行",
    ).toEqual([]);
    expect(fileLines.some((l) => l.includes(`trace_id=${traceId} `))).toBe(true);
    // backend：卷內 console.log 為 JSON 行（LOG_DIR=/app/logs）
    const back = (await docker("exec", BACKEND, "sh", "-c", "ls -l /app/logs/console.log && tail -n 40 /app/logs/console.log")).stdout.split("\n").filter((l) => l.startsWith("{"));
    expect(back.length, "console.log 有 JSON 行").toBeGreaterThan(5);
    const parsed = back.map((l) => JSON.parse(l) as Record<string, unknown>);
    console.log(`[docker-trace] traceId=${traceId}；Bridge 命中 ${hit.length} 行；Bridge 卷內 ${fileLines.length} 行；backend JSON 行鍵：${Object.keys(parsed[0]).slice(0, 8).join(",")}`);
  });

  test("O-20／C-16｜未認證限流不可被偽造 X-Forwarded-For 繞過：連打 101 次、每次偽造不同來源，仍得到 429（W4：全是 401、沒有 429）", async () => {
    test.setTimeout(240_000);
    await new Promise((r) => setTimeout(r, 62_000)); // 讓主機來源（172.31.250.1）的未認證桶回到整個視窗
    const codes: number[] = [];
    for (let i = 0; i < 101; i += 1) {
      const res = await fetch(`${API_URL}/api/v1/projects`, { headers: { "X-Forwarded-For": `203.0.113.${(i % 250) + 1}` } });
      codes.push(res.status);
    }
    const n401 = codes.filter((c) => c === 401).length;
    const n429 = codes.filter((c) => c === 429).length;
    expect(n429, `101 次的狀態分佈：401×${n401}、429×${n429}`).toBeGreaterThanOrEqual(1);
    expect(n401, "最多放 100 個 401（共用一個來源桶）").toBeLessThanOrEqual(100);
    expect(n401 + n429).toBe(101);
    console.log(`[docker-xff] 偽造 101 個不同 X-Forwarded-For：401×${n401}、429×${n429}`);
    await new Promise((r) => setTimeout(r, 62_000)); // 把桶還給後面的情境
  });
});
