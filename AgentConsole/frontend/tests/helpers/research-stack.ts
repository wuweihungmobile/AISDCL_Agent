import { expect, type APIRequestContext, type Page } from "@playwright/test";

/**
 * 研發工作流（ResearchToPRD）Docker 全棧 E2E 的共用工具（P1 PKG-FE-W 自 `research-docker.stack.spec.ts` 抽出；P0 候選「真棧 spec helper 合併」）：
 * 環境變數與帳號、REST 呼叫（含 429 重試）、限流餘額守門、登入狀態注入、輪詢、研究專案夾具（建專案、跑階段、走到 Gate 0、API 核准）、清場封存。
 * 用於 `research-docker.stack.spec.ts`（P0）、`research-p1-docker.stack.spec.ts`（P1 Docker mock 負控）與 `research-route-local.stack.spec.ts`（P1 本機模式）。
 * 每支 spec 各自 `newResearchKit()` 取得一份「建立過的專案清單」，各自在 `afterAll` 封存，互不干擾。
 */
export const STACK_ON = process.env.E2E_STACK === "1";
export const BASE = (process.env.E2E_API_URL ?? "http://localhost").replace(/\/+$/, "");

export type Creds = { user: string; password: string };
export const credsOf = (role: string): Creds => ({ user: process.env[`E2E_${role}_USER`] ?? "", password: process.env[`E2E_${role}_PASSWORD`] ?? "" });
export const hasCreds = (c: Creds): boolean => c.user !== "" && c.password !== "";
export const ADMIN = credsOf("ADMIN");
export const OPERATOR = credsOf("OPERATOR");
export const VIEWER = credsOf("VIEWER");
export const RUN = Date.now().toString(36);

// ── REST 與登入 ──────────────────────────────────────────────────────────────────────────

export type Json = Record<string, unknown>;
export type Reply = { status: number; json: Json };
export type Tokens = { accessToken: string; refreshToken: string; expiresIn: number; role: string };

export const tokenCache = new Map<string, { at: number; tokens: Tokens }>();

/** 取該帳號的 token（快取 20 分鐘；access token 效期 30 分鐘）。 */
export async function tokensOf(request: APIRequestContext, c: Creds): Promise<Tokens> {
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
export async function call(request: APIRequestContext, c: Creds, method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE", apiPath: string, body?: unknown): Promise<Reply> {
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
export async function ensureQuota(request: APIRequestContext, c: Creds, need = 50): Promise<void> {
  for (let i = 0; i < 3; i += 1) {
    const { accessToken } = await tokensOf(request, c);
    const res = await request.get(`${BASE}/api/v1/notifications/summary`, { headers: { Authorization: `Bearer ${accessToken}` }, failOnStatusCode: false });
    const remaining = Number(res.headers()["x-ratelimit-remaining"] ?? "100");
    if (res.status() === 200 && remaining >= need) return;
    await new Promise((resolve) => setTimeout(resolve, 62_000));
  }
}

/** 導覽到 ADMIN 的頁面：先確認限流餘額夠載入一整頁（工作區頁約 20～30 次請求，且那些請求這裡沒法重試），不夠就等下一個視窗。 */
export async function open(page: Page, request: APIRequestContext, url: string): Promise<void> {
  await ensureQuota(request, ADMIN);
  await page.goto(url);
}
export const dataOf = <T = Json>(reply: Reply): T => reply.json.data as T;
export const projectPath = (id: string, rest = ""): string => `/api/v1/research/projects/${id}${rest}`;

/** 登入狀態直接寫進 sessionStorage（須在 page.goto 之前呼叫）。 */
export async function signIn(page: Page, request: APIRequestContext, c: Creds): Promise<void> {
  const t = await tokensOf(request, c);
  const session = JSON.stringify({ accessToken: t.accessToken, refreshToken: t.refreshToken, expiresAt: Date.now() + t.expiresIn * 1000, role: t.role, username: c.user });
  await page.addInitScript((value) => window.sessionStorage.setItem("aisdlc.console.session", value), session);
}

export async function poll<T>(fn: () => Promise<T>, done: (value: T) => boolean, what: string, timeoutMs = 240_000, intervalMs = 2500): Promise<T> {
  const start = Date.now();
  let last: T | undefined;
  while (Date.now() - start < timeoutMs) {
    last = await fn();
    if (done(last)) return last;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(`等待逾時（${timeoutMs}ms）：${what}；最後一次值＝${JSON.stringify(last)}`);
}

// ── 專案夾具 ─────────────────────────────────────────────────────────────────────────────

export type Project = { id: string; slug: string; rpNo: string };
export type Detail = { flowStep: string; flowPhase: string; flowStatus: string; flowDetail: string; headPrdVersion: number | null; scope: Json; fsmProject: string; flow: { effective: Json } };
export type Round = { roundNo: number; weightedScore: number | null; verdict: string; passed: boolean };

/** 議題軸：mock 劇本的證據夾具寫死全六軸，專案軸取子集會在證據 gate 的 R8 失敗（INT-11；README 已載明），所以 API 直呼一律建六軸。 */
export const SIX_AXES = ["技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本"];

export const detailOf = async (request: APIRequestContext, id: string): Promise<Detail> => {
  const reply = await call(request, ADMIN, "GET", projectPath(id));
  expect(reply.status, `GET 專案 → ${JSON.stringify(reply.json)}`).toBe(200);
  return dataOf<Detail>(reply);
};
export const roundsOf = async (request: APIRequestContext, id: string): Promise<Round[]> => dataOf<Round[]>(await call(request, ADMIN, "GET", projectPath(id, "/review-rounds")));
export const eventSeqs = async (request: APIRequestContext, id: string): Promise<number[]> =>
  dataOf<{ items: Array<{ seq: number }> }>(await call(request, ADMIN, "GET", projectPath(id, "/events?afterSeq=0&limit=500"))).items.map((e) => e.seq);

/** 事件帳的一次請求取得：這個 stage run 的狀態（最後一筆 `research.run`）與游標的 `flowStatus`（最後一筆 `research.step`）；還沒有事件回空字串。 */
export async function progressOf(request: APIRequestContext, id: string, stageRunId: string): Promise<{ run: string; cursor: string }> {
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
export async function runStage(request: APIRequestContext, id: string, stage: "research" | "draft" | "review" | "iterate"): Promise<Detail> {
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

/** 以 API 核准（head 版本、帶 PRD 與證據矩陣兩個摘要；Gate 0 的 API 側；回 API 的 `specDocDigests`）。 */
export async function approveViaApi(request: APIRequestContext, id: string): Promise<Record<string, string>> {
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

/** 一份專案夾具工具：`created` 記下本 spec 建立的專案，`archiveAll` 於 afterAll 封存（失敗不擋收尾，但要說出來）。 */
export function newResearchKit(logTag: string) {
  const created: string[] = [];

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

  /** 共用的「GATE0_PENDING」專案：同一支 spec 內先用的不核准，後用的再核准；單獨跑任一個都會自己建。 */
  let gate0: Promise<Project> | null = null;
  const gate0Project = (request: APIRequestContext): Promise<Project> => (gate0 ??= driveToGate0(request, "gate0"));

  /**
   * 清場：封存所有測試建立的研究專案（`archived_at` 寫入、列保留），並先軟刪分流時綁上的 Console 專案（`is_deleted`，30 天內可 restore）；
   * 封存撞 409（階段還在跑）就等它收尾再試。留著未封存的測試專案，下一次的零專案空狀態就不成立——2026-11-07 INT-P1 實例：首跑失敗的
   * RP-0050（封存時階段未結束）與分流建立的 Console 專案 RP-0052／RP-0053（舊版只封存研究專案）留在共用棧，掌舵者在專案管理與執行中心看到不明草稿。
   */
  async function archiveAll(request: APIRequestContext): Promise<void> {
    for (const id of created) {
      const route = await call(request, ADMIN, "GET", projectPath(id, "/route")).catch(() => null);
      const consoleProjectId = route !== null && route.status === 200 ? (dataOf<{ consoleProjectId?: string | null }>(route).consoleProjectId ?? null) : null;
      if (consoleProjectId !== null) {
        const gone = await call(request, ADMIN, "DELETE", `/api/v1/projects/${consoleProjectId}`).catch(() => null);
        if (gone === null || (gone.status !== 204 && gone.status !== 404)) {
          console.warn(`[${logTag}] Console 專案 ${consoleProjectId} 沒有軟刪成功（${gone === null ? "請求失敗" : `HTTP ${gone.status}`}），請手動封存`);
        }
      }
      let reply: Reply | null = null;
      for (let attempt = 0; attempt < 6; attempt += 1) {
        reply = await call(request, ADMIN, "POST", projectPath(id, "/archive"), {}).catch(() => null);
        if (reply === null || reply.status !== 409) break;
        await new Promise((resolve) => setTimeout(resolve, 10_000));
      }
      if (reply === null || reply.status !== 200) console.warn(`[${logTag}] 專案 ${id} 沒有封存成功（${reply === null ? "請求失敗" : `HTTP ${reply.status}`}），請手動封存`);
    }
  }

  return { created, createProject, driveToGate0, gate0Project, archiveAll };
}
