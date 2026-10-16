import { execFile } from "node:child_process";
import { mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";

import { expect, test, type APIRequestContext } from "@playwright/test";

import { API_URL, RUN } from "./helpers";
import { collectConsoleErrors } from "./mockApi";
import { bootstrapSettings, call, dataOf, ensureQuota, poll, signIn } from "./realBackend";
import { REAL_FSM, realSddLatest, writeText, yamlLoad } from "./w7";

/**
 * W7 複驗（Docker 全棧，經 nginx 同源）——契約 v1.3／v1.4 的全棧側：
 *  · E2E-14 列 8～9：真的 Linux 容器內的引擎行程樹資源取樣（`bridge.resources`）與終態的「—」；
 *  · E2E-15 列 9（全棧半邊）＋ NFR-OBS-01：Bridge 容器 `/health/deep` 的 `checks.sdd`、`GET /engines/sdd` 與主機上真實的 FSM-STATE 檔逐值比對、
 *    乾淨 clone 等價（只有入口文件的唯讀掛載）與不存在的 SDD_ROOT 的 Bridge 容器（用同一個映像另起，不碰全棧）；
 *  · E2E-16 列 1（全新資料庫的探測預設）與列 10（Redis 降級：停掉 redis 後撤銷仍有效、backend 維持 healthy、日誌恰一筆 WARN、恢復後一筆 INFO、
 *    Redis 回來後新的撤銷寫進 Redis）。
 * Docker 全棧不載入 e2e profile（沒有 allow-loopback、mock-env），所以 E2E-14 列 1～7 不在這裡（假模型伺服器不可達，§5.0.1）。
 * 容器名稱預設為 compose 的 container_name；需要 docker CLI。
 */
const execFileAsync = promisify(execFile);
const BRIDGE = process.env.E2E_BRIDGE_CONTAINER ?? "aisdlc-engine-bridge";
const BACKEND = process.env.E2E_BACKEND_CONTAINER ?? "aisdlc-backend";
const REDIS = process.env.E2E_REDIS_CONTAINER ?? "aisdlc-redis";
const BRIDGE_IMAGE = process.env.E2E_BRIDGE_IMAGE ?? "aisdlc-engine-bridge:dev";
const MOCK_CLAUDE = process.env.E2E_MOCK_CLAUDE ?? "aisdlc-mock-claude";
const FIRST_LOAD = { timeout: 60_000 };
const nm = (base: string) => `${base} ${RUN}`;
const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED"];
const LATEST = realSddLatest() ?? "";

async function docker(...args: string[]): Promise<{ stdout: string; stderr: string }> {
  return execFileAsync("docker", args, { timeout: 180_000, maxBuffer: 64 * 1024 * 1024 });
}
const health = async (container: string): Promise<string> => (await docker("inspect", "-f", "{{.State.Health.Status}}", container)).stdout.trim();
const bridgeGet = async (p: string): Promise<{ status: number; body: Record<string, unknown> }> => {
  const probe =
    "import sys,json,urllib.request as u,urllib.error as e\ntry:\n r=u.urlopen(sys.argv[1],timeout=10); print(r.status, r.read().decode())\nexcept e.HTTPError as x:\n print(x.code, x.read().decode())";
  const { stdout } = await docker("exec", BRIDGE, "python", "-c", probe, `http://127.0.0.1:8081${p}`);
  const i = stdout.indexOf(" ");
  return { status: Number(stdout.slice(0, i)), body: JSON.parse(stdout.slice(i + 1)) as Record<string, unknown> };
};

type Resources = { cpuPercent: number; memoryBytes: number; processCount: number; sampledAt: string };
type Detail = { id: string; status: string; bridge?: { connected: boolean; resources?: Resources | null } };
type Tokens = { accessToken: string; refreshToken: string };

const pad = (n: number) => String(n).padStart(2, "0");
const localTime = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

/** 專案目錄建在 Bridge 容器的 /workspace/projects 底下（Docker 全棧的路徑白名單）。單一目標、N 個任務。 */
async function createStackLongFixture(request: APIRequestContext, name: string, tasks: number): Promise<{ projectId: string; name: string }> {
  const dir = `/workspace/projects/${name.replace(/[^A-Za-z0-9_-]/g, "_")}`;
  await docker("exec", BRIDGE, "mkdir", "-p", dir);
  const p = await call(request, "operator", "POST", "/api/v1/projects", { name, executionPath: dir, passCriteria: "全部完成", description: "QA Docker 長批次", autonomyLevel: 4, draft: false });
  expect(p.status, JSON.stringify(p.json)).toBe(201);
  const projectId = dataOf<{ id: string }>(p).id;
  const g = await call(request, "operator", "POST", `/api/v1/projects/${projectId}/goals`, { name: "長批次", passCriteria: "全部完成", description: "", dependsOn: [], draft: false });
  expect(g.status, JSON.stringify(g.json)).toBe(201);
  const goalId = dataOf<{ id: string }>(g).id;
  for (let n = 1; n <= tasks; n += 1) {
    const t = await call(request, "operator", "POST", `/api/v1/goals/${goalId}/tasks`, {
      name: `長任務 ${n}`,
      description: `請輸出 [T${n}_DONE]`,
      passCriteria: `輸出含 [T${n}_DONE]`,
      expectedOutputRegex: `\\[T${n}_DONE\\]`,
      maxRetries: 1,
      draft: false,
    });
    expect(t.status, JSON.stringify(t.json)).toBe(201);
  }
  return { projectId, name };
}

const detail = async (request: APIRequestContext, runId: string): Promise<Detail> => dataOf<Detail>(await call(request, "viewer", "GET", `/api/v1/executions/${runId}`));

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await bootstrapSettings(request, MOCK_CLAUDE);
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator", 60);
  await ensureQuota(request, "viewer", 60);
});

test.describe("Docker 全棧：W7 新增面", () => {
  test.setTimeout(600_000);

  test("E2E-16 列 1＋探測：全新資料庫的 healthCheckPath 預設為 /health/deep；Bridge 容器的 healthcheck 與 console-api 探測環都打深度探針，頂列為已連線", async ({ request }) => {
    const rows = dataOf<Array<{ key: string; value: string; defaultValue: string }>>(await call(request, "admin", "GET", "/api/v1/settings/autoclaude"));
    const row = rows.find((r) => r.key === "healthCheckPath")!;
    expect({ value: row.value, defaultValue: row.defaultValue }).toEqual({ value: "/health/deep", defaultValue: "/health/deep" });
    const s = dataOf<{ bridgeConnected: boolean }>(await call(request, "viewer", "GET", "/api/v1/notifications/summary"));
    expect(s.bridgeConnected, "深度探針 200 → 頂列已連線").toBe(true);
    expect((await docker("inspect", "-f", "{{json .Config.Healthcheck.Test}}", BRIDGE)).stdout).toContain("/health/deep");
    console.log(
      `[w7-docker] 列 1：healthCheckPath value＝${row.value}／default＝${row.defaultValue}；bridgeConnected＝${s.bridgeConnected}；Bridge 容器 ${await health(BRIDGE)}、backend ${await health(BACKEND)}`,
    );
  });

  test("E2E-14 列 8～9（全棧）：Linux 容器內引擎行程樹的資源取樣——fields、sampledAt 前進、卡片格式；終態後 resources 為 null 且卡片「—」", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    // Docker 全棧沒有 e2e profile 的 mock-env：mock claude 用預設延遲 0.2 秒，批次要靠任務數撐長（90 個約一分鐘）；
    // 建夾具要 92 次呼叫，限流每分鐘 100 次，所以先確認餘額夠。
    await ensureQuota(request, "operator", 96);
    const f = await createStackLongFixture(request, nm("QA W7 Docker 資源"), 90);
    const r = await call(request, "operator", "POST", `/api/v1/projects/${f.projectId}/execute`, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
    expect(r.status, JSON.stringify(r.json).slice(0, 300)).toBe(201);
    const runId = dataOf<{ id: string }>(r).id;
    const first = await poll(
      () => detail(request, runId),
      (d) => !!d.bridge?.resources,
      "bridge.resources 出現",
      30_000,
      2_000,
    );
    const r1 = first.bridge!.resources!;
    expect(Object.keys(r1).sort()).toEqual(["cpuPercent", "memoryBytes", "processCount", "sampledAt"]);
    expect(r1.cpuPercent >= 0 && r1.cpuPercent <= 100 && Math.round(r1.cpuPercent * 10) / 10 === r1.cpuPercent).toBe(true);
    expect(Number.isInteger(r1.memoryBytes) && r1.memoryBytes > 0).toBe(true);
    expect(Number.isInteger(r1.processCount) && r1.processCount >= 1).toBe(true);
    expect(r1.sampledAt).toMatch(/[+-]\d{2}:\d{2}$|Z$/);
    expect(JSON.stringify(first)).not.toMatch(/"pid"/i);
    // 建夾具用掉了這一分鐘的大半額度（92 次呼叫）；頁面一載入就是 30 次上下的呼叫，會撞 429 而不是在驗資源卡，所以先等限流視窗重置
    await ensureQuota(request, "operator", 60);
    await signIn(page, request, "operator");
    await page.goto(`/projects/${f.projectId}/monitor`);
    await expect(page.getByTestId("agent-card")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("agent-resources")).toHaveText(/^CPU \d+\.\d%・記憶體 (<1 MB|\d+ MB|\d+\.\d GB)・\d+ 行程$/, FIRST_LOAD);
    const title1 = (await page.getByTestId("agent-resources").getAttribute("title")) ?? "";
    await new Promise((res) => setTimeout(res, 6_500));
    const second = await detail(request, runId);
    expect(TERMINAL.includes(second.status), `第二次輪詢時批次還在跑（${second.status}）`).toBe(false);
    const r2 = second.bridge!.resources!;
    expect(Date.parse(r2.sampledAt), "sampledAt 前進").toBeGreaterThan(Date.parse(r1.sampledAt));
    await expect.poll(async () => (await page.getByTestId("agent-resources").getAttribute("title")) ?? "", { timeout: 45_000, intervals: [1_000] }).not.toBe(title1);
    console.log(
      `[w7-docker] 列 8（全棧）：首筆＝${JSON.stringify(r1)}；第二筆（與首筆的 sampledAt 相隔 ${Math.round((Date.parse(r2.sampledAt) - Date.parse(r1.sampledAt)) / 1000)} 秒）＝${JSON.stringify(r2)}；畫面「${await page.getByTestId("agent-resources").textContent()}」`,
    );
    // 列 9：取消後終態
    await call(request, "operator", "POST", `/api/v1/executions/${runId}/cancel`);
    const fin = await poll(
      () => detail(request, runId),
      (d) => TERMINAL.includes(d.status),
      "批次取消後進入終態",
      90_000,
      2_000,
    );
    expect(fin.bridge?.resources ?? null, "終態 resources 為 null 或缺席").toBeNull();
    await page.reload();
    await expect(page.getByTestId("agent-resources")).toHaveText("—", FIRST_LOAD);
    await expect(page.getByTestId("agent-card")).not.toContainText("目前沒有提供這項資料");
    console.log(`[w7-docker] 列 9（全棧）：終態 ${fin.status}，resources＝${JSON.stringify(fin.bridge?.resources ?? null)}，卡片「—」`);
    expect(errors.filter((e) => !/Failed to load|ERR_/.test(e))).toEqual([]);
  });

  test("E2E-15 列 9（全棧半邊）＋NFR-OBS-01：Bridge 容器 /health/deep 的 checks.sdd＝ok（掛載真實 AISDLC_SDD）；GET /engines/sdd 與主機上真實的 FSM-STATE 檔逐值一致；三個容器 healthy", async ({
    request,
  }) => {
    expect(await health(BRIDGE), "engine-bridge healthy").toBe("healthy");
    expect(await health(BACKEND), "backend healthy").toBe("healthy");
    const deep = await bridgeGet("/health/deep");
    expect(deep.status).toBe(200);
    const sddCheck = (deep.body.checks as Record<string, Record<string, unknown>>).sdd;
    expect(LATEST, "主機上找得到 AISDLC_SDD 的最新版本目錄").not.toBe("");
    expect(sddCheck).toMatchObject({ ok: true, latest: LATEST });
    const list = dataOf<{
      available: boolean;
      reason: string | null;
      version: { latest: string; root: string } | null;
      projects: Array<{ project: string; currentState: string | null; updatedAt: string | null }>;
    }>(await call(request, "viewer", "GET", "/api/v1/engines/sdd"));
    expect(list.available).toBe(true);
    expect(list.version?.latest).toBe(LATEST);
    expect(list.version?.root, "Docker 下 root 是容器內路徑").toContain(`/sdd/${LATEST}`);
    expect(
      list.projects.map((p) => p.project),
      "含真實專案（掛載的是主機上的 AISDLC_SDD，同目錄的 test-<數字> 殘留檔也會列出）",
    ).toContain("AISDLC_SDD");
    const real = (await yamlLoad<{ fsm_state: Record<string, unknown> }>(REAL_FSM)).fsm_state;
    const f = dataOf<{ fsm: Record<string, unknown> | null }>(await call(request, "viewer", "GET", "/api/v1/engines/sdd?project=AISDLC_SDD")).fsm!;
    expect({ currentState: f.currentState, currentSprint: f.currentSprint, updatedAt: f.updatedAt, sessionId: f.sessionId }).toEqual({
      currentState: real.current_state,
      currentSprint: real.current_sprint,
      updatedAt: real.updated_at,
      sessionId: real.session_id,
    });
    console.log(
      `[w7-docker] 列 9／NFR-OBS-01（全棧）：checks.sdd＝${JSON.stringify(sddCheck)}；/engines/sdd＝${list.version?.latest}（${list.projects.length} 個專案）；AISDLC_SDD 的 ${f.currentState}／Sprint ${f.currentSprint}／${localTime(String(f.updatedAt))} 與主機檔逐值一致`,
    );
  });

  test("E2E-15 列 8～9（Linux 映像）：同一個 Bridge 映像另起容器——乾淨 clone 等價（只有入口文件的唯讀掛載）checks.sdd＝ok；SDD_ROOT 不存在 checks.sdd＝false 且整體仍 200", async () => {
    const fixture = path.join(tmpdir(), `w7qa-sdd-fresh-${RUN}`);
    mkdirSync(path.join(fixture, "AISDLC_SDD_v9.98"), { recursive: true });
    writeText(path.join(fixture, "AISDLC_SDD_v9.98", "AISDLC_SDD_INIT.md"), "# AISDLC_SDD（乾淨 clone 等價）\n");
    const names = [`w7qa-fresh-${RUN}`, `w7qa-nodir-${RUN}`];
    const get = async (port: number, p: string): Promise<{ status: number; body: Record<string, unknown> }> => {
      for (let i = 0; i < 60; i += 1) {
        try {
          const res = await fetch(`http://127.0.0.1:${port}${p}`);
          return { status: res.status, body: (await res.json()) as Record<string, unknown> };
        } catch {
          await new Promise((r) => setTimeout(r, 1000));
        }
      }
      throw new Error(`容器 ${port} 60 秒內沒有回應`);
    };
    try {
      await docker("run", "-d", "--rm", "--name", names[0], "-p", "18097:8081", "-v", `${fixture}:/sdd:ro`, "-e", "SDD_ROOT=/sdd", BRIDGE_IMAGE);
      await docker("run", "-d", "--rm", "--name", names[1], "-p", "18098:8081", "-e", "SDD_ROOT=/no/such/dir", BRIDGE_IMAGE);
      const fresh = await get(18097, "/health/deep");
      expect(fresh.status, JSON.stringify(fresh.body)).toBe(200);
      expect((fresh.body.checks as Record<string, Record<string, unknown>>).sdd).toMatchObject({ ok: true, latest: "AISDLC_SDD_v9.98" });
      const freshFsm = await get(18097, "/sdd/fsm");
      expect(freshFsm.status).toBe(200);
      expect(freshFsm.body.projects, "乾淨 clone：沒有 build/reports/fsm → 空清單、不是錯誤").toEqual([]);
      const nodir = await get(18098, "/health/deep");
      expect(nodir.status, "sdd 無效只當資訊：整體仍 200").toBe(200);
      expect((nodir.body.checks as Record<string, Record<string, unknown>>).sdd).toMatchObject({ ok: false });
      expect(nodir.body.reason, "頂層沒有 reason").toBeUndefined();
      const nodirSdd = await get(18098, "/sdd/fsm");
      expect(nodirSdd.status, "SDD_ROOT 無效 → /sdd/fsm 503 sdd_unavailable").toBe(503);
      expect(nodirSdd.body.reason).toBe("sdd_unavailable");
      console.log(
        `[w7-docker] 列 9（Linux 映像 ${BRIDGE_IMAGE}）：乾淨 clone 等價 checks.sdd＝${JSON.stringify((fresh.body.checks as Record<string, unknown>).sdd)}、/sdd/fsm projects＝[]；SDD_ROOT 不存在 checks.sdd＝${JSON.stringify((nodir.body.checks as Record<string, unknown>).sdd)}、整體 ${nodir.status}、/sdd/fsm＝${nodirSdd.status}`,
      );
    } finally {
      for (const n of names) await docker("stop", n).catch(() => undefined);
      rmSync(fixture, { recursive: true, force: true });
    }
  });

  test("E2E-16 列 10：Redis 降級——停掉 redis 後登入／換新／登出的撤銷仍有效、backend 維持 healthy、日誌恰一筆 WARN；redis 回來後恰一筆 INFO，新的撤銷寫進 Redis", async ({ request }) => {
    const t0 = new Date().toISOString();
    const login = async (): Promise<Tokens> => {
      const r = await request.post(`${API_URL}/api/v1/auth/login`, { data: { username: "operator", password: ["Operator", "Dev2026"].join("#") } });
      expect(r.status()).toBe(200);
      return ((await r.json()) as { data: Tokens }).data;
    };
    const refresh = async (rt: string) => {
      const r = await request.post(`${API_URL}/api/v1/auth/refresh`, { data: { refreshToken: rt }, failOnStatusCode: false });
      return { status: r.status(), json: (await r.json().catch(() => ({}))) as { reason?: string; data?: Tokens } };
    };
    const logout = async (rt: string) => (await request.post(`${API_URL}/api/v1/auth/logout`, { data: { refreshToken: rt }, failOnStatusCode: false })).status();
    const keys = async (): Promise<string[]> => (await docker("exec", REDIS, "redis-cli", "--scan", "--pattern", "console:revoked-refresh:*")).stdout.split("\n").filter((l) => l.trim() !== "");
    const logLines = async (needle: string, level: string): Promise<number> => {
      const { stdout, stderr } = await docker("logs", "--since", t0, BACKEND);
      return `${stdout}\n${stderr}`.split("\n").filter((l) => l.includes(needle) && l.includes(level)).length;
    };
    const actuator = async (): Promise<string> => {
      const { stdout } = await docker("exec", BACKEND, "sh", "-c", "(wget -qO- http://127.0.0.1:8080/actuator/health || curl -s http://127.0.0.1:8080/actuator/health)");
      return (JSON.parse(stdout) as { status: string }).status;
    };
    try {
      // 基線：Redis 在線，登出會把 jti 寫進 Redis
      const before = (await keys()).length;
      const a = await login();
      expect(await logout(a.refreshToken)).toBe(204);
      const afterBaseline = (await keys()).length;
      expect(afterBaseline, "Redis 在線：登出的撤銷寫進 Redis（console:revoked-refresh:<jti>）").toBeGreaterThan(before);
      // 停掉 redis
      await docker("stop", REDIS);
      const t1 = await login();
      const s2 = await refresh(t1.refreshToken);
      expect(s2.status, "Redis 停掉仍可換新").toBe(200);
      const replay = await refresh(t1.refreshToken);
      expect({ status: replay.status, reason: replay.json.reason }, "舊 refresh token 再換新 → 401（撤銷退到記憶體名單仍有效）").toEqual({ status: 401, reason: "INVALID_REFRESH_TOKEN" });
      expect(await logout(s2.json.data!.refreshToken), "Redis 停掉仍可登出").toBe(204);
      expect((await refresh(s2.json.data!.refreshToken)).status, "登出後換新 → 401").toBe(401);
      expect(await actuator(), "/actuator/health 仍 UP（Redis 健康指標已關閉）").toBe("UP");
      expect(await health(BACKEND), "backend 容器維持 healthy").toBe("healthy");
      const warn = await logLines("撤銷名單：Redis 不可用", "WARN");
      expect(warn, "進入降級恰一筆 WARN（只在狀態轉換時記，不在每次呼叫都記）").toBe(1);
      expect(await logLines("撤銷名單：Redis 已恢復", "INFO"), "降級期間沒有 INFO 恢復行").toBe(0);
      // redis 回來
      await docker("start", REDIS);
      await poll(
        () => health(REDIS),
        (h) => h === "healthy",
        "redis 回到 healthy",
        60_000,
        2_000,
      );
      let recovered = 0;
      for (let i = 0; i < 20 && recovered === 0; i += 1) {
        const t = await login();
        expect(await logout(t.refreshToken)).toBe(204);
        recovered = await logLines("撤銷名單：Redis 已恢復", "INFO");
        if (recovered === 0) await new Promise((res) => setTimeout(res, 2_000));
      }
      expect(recovered, "恢復後恰一筆 INFO").toBe(1);
      expect(await logLines("撤銷名單：Redis 不可用", "WARN"), "WARN 仍只有一筆").toBe(1);
      const afterRecover = (await keys()).length;
      expect(afterRecover, "Redis 回來後新的撤銷寫進 Redis").toBeGreaterThan(afterBaseline);
      console.log(
        `[w7-docker] 列 10：Redis 在線登出→鍵 ${before}→${afterBaseline}；停掉後 換新=200、舊 token 再換新=401 INVALID_REFRESH_TOKEN、登出=204、之後換新=401；actuator UP、backend healthy；WARN 1 筆；啟動後 INFO ${recovered} 筆、WARN 仍 1 筆、新撤銷寫進 Redis（鍵 ${afterBaseline}→${afterRecover}）`,
      );
    } finally {
      await docker("start", REDIS).catch(() => undefined);
    }
  });
});
