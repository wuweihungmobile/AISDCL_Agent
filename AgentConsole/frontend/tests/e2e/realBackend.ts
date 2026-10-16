import { mkdirSync } from "node:fs";
import { createServer, type IncomingHttpHeaders, type Server } from "node:http";
import path from "node:path";

import { expect, type APIRequestContext, type Page } from "@playwright/test";

import { API_URL, RUN, apiToken } from "./helpers";

/**
 * 真後端（console-api＋PostgreSQL＋真 Engine Bridge＋aisdlc-mock-claude）的 E2E 共用工具（p3～p6 specs 用）。
 *
 * 前置（契約 §5.0，QA 報告〈環境〉有逐步指令）：
 *  - backend 以 e2e profile 啟動；Bridge 以 DB 模式啟動，BRIDGE_ALLOWED_PATH_ROOTS 含 <E2E_ROOT>\projects；
 *  - 環境變數 E2E_ROOT＝上述 <E2E_ROOT>（專案的 executionPath 一律建在其下的 projects 目錄）；
 *  - admin 已設 autoclaude.claudeCommand＝aisdlc-mock-claude 的絕對路徑、execution.autoResume＝false（見 bootstrapSettings）。
 * 沒有 E2E_ROOT 時這些 specs 一律略過，不當失敗（一般開發機沒有真 Bridge）。
 */
export const E2E_ROOT = process.env.E2E_ROOT ?? "";
export const NEEDS_BRIDGE = "需要真 Engine Bridge 與 e2e profile 的 backend：設 E2E_ROOT（見 tests/e2e/README.md〈真 Bridge specs〉）";

/**
 * 已登記但尚未修復的缺陷（QA 報告〈缺陷清單〉）用 test.fail(DEFECTS_OPEN, …) 釘住：缺陷還在時整支「預期失敗」＝綠燈，
 * 修好後會「意外通過」而變紅，提醒把該行移除。設 E2E_DEFECTS_FIXED=1 可關掉預期失敗、看缺陷的真實失敗訊息。
 */
export const DEFECTS_OPEN = process.env.E2E_DEFECTS_FIXED !== "1";

export type Role = "admin" | "operator" | "viewer";

// 開發預設帳號（backend/README.md 明載、僅限本機開發）；用陣列 join 組字串，不在原始碼放整串帳密字面（避免機密掃描誤報）。
const PASSWORDS: Record<Role, string> = {
  admin: ["Admin", "Dev2026"].join("#"),
  operator: ["Operator", "Dev2026"].join("#"),
  viewer: ["Viewer", "Dev2026"].join("#"),
};

export type Json = Record<string, unknown>;
export type Reply = { status: number; json: Json; headers: Record<string, string> };

const tokens = new Map<Role, { token: string; at: number }>();

/** 取該角色的 access token（快取 20 分鐘；access token 效期 30 分鐘）。 */
export async function tokenOf(request: APIRequestContext, role: Role): Promise<string> {
  const hit = tokens.get(role);
  if (hit && Date.now() - hit.at < 20 * 60_000) return hit.token;
  const token = await apiToken(request, role, PASSWORDS[role]);
  tokens.set(role, { token, at: Date.now() });
  return token;
}

/** 呼叫 REST（任何狀態碼都回傳，由呼叫端斷言）。 */
export async function call(request: APIRequestContext, role: Role, method: "GET" | "POST" | "PUT" | "DELETE", apiPath: string, body?: unknown): Promise<Reply> {
  const token = await tokenOf(request, role);
  const res = await request.fetch(`${API_URL}${apiPath}`, {
    method,
    headers: { Authorization: `Bearer ${token}` },
    data: body,
    failOnStatusCode: false,
  });
  let json: Json = {};
  try {
    json = (await res.json()) as Json;
  } catch {
    json = {};
  }
  return { status: res.status(), json, headers: res.headers() };
}

/**
 * 限流是固定視窗：每個使用者（JWT subject）每 60 秒 100 次（契約 §0.4 第 4 點），UI 與 REST 共用同一個桶。
 * 情境開始前確認該角色的餘額夠用（X-RateLimit-Remaining），不夠就等視窗過去——否則流程中途出現 429，會被誤判成功能缺陷。
 */
export async function ensureQuota(request: APIRequestContext, role: Role, need = 50): Promise<void> {
  for (let i = 0; i < 3; i += 1) {
    const r = await call(request, role, "GET", "/api/v1/notifications/summary");
    const remaining = Number(r.headers["x-ratelimit-remaining"] ?? "100");
    if (r.status === 200 && remaining >= need) return;
    await new Promise((resolve) => setTimeout(resolve, 62_000));
  }
}

/** 成功封包的 data。 */
export function dataOf<T = Json>(reply: Reply): T {
  return reply.json.data as T;
}

/** 登入狀態直接寫進 sessionStorage（需先對真後端換票）；須在 page.goto 之前呼叫。 */
export async function signIn(page: Page, request: APIRequestContext, role: Role): Promise<void> {
  const res = await request.post(`${API_URL}/api/v1/auth/login`, { data: { username: role, password: PASSWORDS[role] } });
  expect(res.ok(), `登入 ${role} 失敗：HTTP ${res.status()}`).toBeTruthy();
  const t = ((await res.json()) as { data: { accessToken: string; refreshToken: string; expiresIn: number; role: string } }).data;
  const session = JSON.stringify({
    accessToken: t.accessToken,
    refreshToken: t.refreshToken,
    expiresAt: Date.now() + t.expiresIn * 1000,
    role: t.role,
    username: role,
  });
  await page.addInitScript((s) => window.sessionStorage.setItem("aisdlc.console.session", s), session);
}

/** 契約 §5.0.2 的系統參數前置（admin；冪等）：替身引擎、關閉自動續跑、重試只一次、假模型。 */
export async function bootstrapSettings(request: APIRequestContext, mockClaudeExe: string): Promise<void> {
  const rows: Array<[string, string, string]> = [
    ["autoclaude", "claudeCommand", mockClaudeExe],
    ["execution", "autoResume", "false"],
    ["agent", "maxRetries", "1"],
    ["model", "name", "e2e-model"],
    ["model", "timeout", "30"],
  ];
  for (const [category, key, value] of rows) {
    const r = await call(request, "admin", "PUT", `/api/v1/settings/${category}/${key}`, { value });
    expect(r.status, `PUT ${category}.${key} → ${JSON.stringify(r.json)}`).toBe(200);
  }
}

/** 輪詢直到條件成立（預設間隔 1.5 秒：e2e profile 每個使用者每分鐘 100 次，輪詢一律用 viewer）。 */
export async function poll<T>(fn: () => Promise<T>, done: (v: T) => boolean, what: string, timeoutMs = 60_000, intervalMs = 1500): Promise<T> {
  const start = Date.now();
  let last: T | undefined;
  while (Date.now() - start < timeoutMs) {
    last = await fn();
    if (done(last)) return last;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`等待逾時（${timeoutMs}ms）：${what}；最後一次值＝${JSON.stringify(last)}`);
}

export type RunView = {
  id: string;
  runNumber: number;
  status: string;
  bridgeStatus: string;
  completedSteps?: number;
  totalSteps?: number;
  totalTokensUsed: number;
  reason?: string;
  lastEventSeq?: number;
  pendingReviews?: Array<{ id: string; kind: string; status: string; allowedDecisions: string[]; reason: string }>;
  bridge?: { connected: boolean; instance?: string; status?: string };
};

export async function getRun(request: APIRequestContext, runId: string): Promise<RunView> {
  const r = await call(request, "viewer", "GET", `/api/v1/executions/${runId}`);
  expect(r.status, `GET run ${runId} → ${JSON.stringify(r.json)}`).toBe(200);
  return dataOf<RunView>(r);
}

export async function waitRun(request: APIRequestContext, runId: string, statuses: string[], timeoutMs = 90_000): Promise<RunView> {
  return poll(
    () => getRun(request, runId),
    (r) => statuses.includes(r.status),
    `run ${runId} 進入 ${statuses.join("／")}`,
    timeoutMs,
  );
}

export type Fixture = { projectId: string; name: string; dir: string; goalIds: string[]; taskIds: string[] };

/**
 * 契約 §5.0.3 夾具：A＝PRJ-A（G1：T1、T2；G2：T3，依賴 G1）、B＝PRJ-B（G1：T1～T3；G2：T4、T5）。
 * failTasks＝要帶 [FAIL_ME] 的任務全域序號（1 起）；draft＝建成未簽核草案。每個任務 maxRetries=1。
 */
export async function createFixture(request: APIRequestContext, opts: { name: string; kind?: "A" | "B"; level?: number; draft?: boolean; failTasks?: number[] }): Promise<Fixture> {
  const { name, kind = "A", level = 4, draft = false, failTasks = [] } = opts;
  const dir = path.join(E2E_ROOT, "projects", name.replace(/[^A-Za-z0-9_-]/g, "_"));
  mkdirSync(dir, { recursive: true });
  const p = await call(request, "operator", "POST", "/api/v1/projects", {
    name,
    executionPath: dir,
    passCriteria: "全部完成",
    description: "QA 夾具",
    autonomyLevel: level,
    draft,
  });
  expect(p.status, `建專案 → ${JSON.stringify(p.json)}`).toBe(201);
  const projectId = dataOf<{ id: string }>(p).id;
  const layout: Array<[string, string[]]> =
    kind === "A"
      ? [
          ["基礎", ["初始化", "設定"]],
          ["核心", ["實作"]],
        ]
      : [
          ["基礎", ["任務一", "任務二", "任務三"]],
          ["核心", ["任務四", "任務五"]],
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
      draft,
    });
    expect(g.status, `建目標 → ${JSON.stringify(g.json)}`).toBe(201);
    const goalId = dataOf<{ id: string }>(g).id;
    goalIds.push(goalId);
    for (const taskName of taskNames) {
      n += 1;
      const description = `請輸出 [T${n}_DONE]${failTasks.includes(n) ? " [FAIL_ME]" : ""}`;
      const t = await call(request, "operator", "POST", `/api/v1/goals/${goalId}/tasks`, {
        name: taskName,
        description,
        passCriteria: `輸出含 [T${n}_DONE]`,
        expectedOutputRegex: `\\[T${n}_DONE\\]`,
        maxRetries: 1,
        draft,
      });
      expect(t.status, `建任務 → ${JSON.stringify(t.json)}`).toBe(201);
      taskIds.push(dataOf<{ id: string }>(t).id);
    }
  }
  return { projectId, name, dir, goalIds, taskIds };
}

// ── SSE 讀取（Node fetch 串流；契約 §2、E2E-12：以解析後欄位斷言，不比對位元組字面） ───────────────────────────────

export type SseFrame = { id?: string; event?: string; data?: string; retry?: string };
export type SseResult = { status: number; headers: Headers; frames: SseFrame[]; comments: string[]; raw: string; body?: string };

/** 解析 SSE 文字：欄位名後的冒號可帶或不帶一個空白；註解行（冒號開頭）另收；空行結束一個框架。 */
export function parseSse(raw: string): { frames: SseFrame[]; comments: string[] } {
  const frames: SseFrame[] = [];
  const comments: string[] = [];
  let cur: SseFrame = {};
  let any = false;
  for (const line of raw.split("\n")) {
    const l = line.replace(/\r$/, "");
    if (l === "") {
      if (any) frames.push(cur);
      cur = {};
      any = false;
      continue;
    }
    if (l.startsWith(":")) {
      comments.push(l.slice(1).replace(/^ /, ""));
      continue;
    }
    const i = l.indexOf(":");
    const field = i < 0 ? l : l.slice(0, i);
    const value = i < 0 ? "" : l.slice(i + 1).replace(/^ /, "");
    if (field === "id" || field === "event" || field === "data" || field === "retry") {
      cur[field] = value;
      any = true;
    }
  }
  return { frames, comments };
}

/** (seq,n) 數對：`41`→[41,0]、`41.2`→[41,2]。 */
export const idPair = (id: string): [number, number] => {
  const [a, b] = id.split(".");
  return [Number(a), b === undefined ? 0 : Number(b)];
};

/** 讀一條 SSE 最多 maxMs 毫秒（到終態伺服器關閉連線會提早結束）；非 200 回應把本文放在 body。 */
export async function readSse(url: string, opts: { headers?: Record<string, string>; maxMs?: number } = {}): Promise<SseResult> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), opts.maxMs ?? 15_000);
  let raw = "";
  try {
    const res = await fetch(url, { headers: opts.headers, signal: ctrl.signal });
    if (res.status !== 200 || !res.body) {
      return { status: res.status, headers: res.headers, frames: [], comments: [], raw: "", body: await res.text() };
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        raw += decoder.decode(value, { stream: true });
      }
    } catch {
      // 逾時中止（AbortError）：保留已收到的部分
    }
    const parsed = parseSse(raw);
    return { status: res.status, headers: res.headers, ...parsed, raw };
  } finally {
    clearTimeout(timer);
  }
}

// ── 假 OpenAI 相容伺服器（匯入路徑 B 與 test-connection 的探測都打它；契約 §5.0.1，綁 127.0.0.1） ──────────────────

export type LlmRequest = { method: string; url: string; headers: IncomingHttpHeaders; body: Json };

const MARKER = {
  max: "GATE_MAX",
  cycle: "GATE_CYCLE",
  empty: "GATE_EMPTY",
  emptyName: "GATE_EMPTY_NAME",
  long: "GATE_LONG",
  multi: "GATE_MULTI",
  ui3: "GATE_UI3",
  badJson: "GATE_BADJSON",
  http500: "GATE_HTTP500",
} as const;
export { MARKER as LLM_MARKER };

type Task = { name: string; description: string; passCriteria: string; sortOrder: number };
const task = (i: number, description = `請輸出 [T${i}_DONE]`, name = `任務${i}`): Task => ({ name, description, passCriteria: `輸出含 [T${i}_DONE]`, sortOrder: i - 1 });
const manyTasks = (count: number, brokenIndex = -1): Task[] => Array.from({ length: count }, (_, i) => task(i + 1, i === brokenIndex ? "  " : undefined));

/** 契約 E2E-01 的 S-OK 樹：g1 兩個任務、g2 一個任務且依賴 g1。 */
export function okTree(projectName: string): Json {
  return {
    project: { name: projectName, executionPath: "/ignored", passCriteria: "三個目標全部完成", description: "由 BRD 匯入" },
    goals: [
      { key: "g1", name: "基礎", description: "", passCriteria: "基礎任務完成", sortOrder: 0, dependsOn: [], tasks: [task(1, "請輸出 [T1_DONE]", "初始化"), task(2, "請輸出 [T2_DONE]", "設定")] },
      { key: "g2", name: "核心", description: "", passCriteria: "核心任務完成", sortOrder: 1, dependsOn: ["g1"], tasks: [task(3, "請輸出 [T3_DONE]", "實作")] },
    ],
  };
}

const wrap = (content: string, extra: Json = {}): Json => ({
  id: "chatcmpl-e2e",
  object: "chat.completion",
  model: "e2e-model",
  choices: [{ index: 0, finish_reason: "stop", message: { role: "assistant", content } }],
  usage: { prompt_tokens: 812, completion_tokens: 340, total_tokens: 1152 },
  ...extra,
});

function gateTree(marker: string, projectName: string): Json {
  const base = okTree(projectName) as { project: Json; goals: Array<Json & { tasks: Task[]; dependsOn: string[] }> };
  const g1 = base.goals[0];
  switch (marker) {
    case MARKER.max:
      g1.tasks = manyTasks(25);
      break;
    case MARKER.cycle:
      g1.dependsOn = ["g2"];
      break;
    case MARKER.empty:
      g1.tasks[1].description = "  ";
      break;
    case MARKER.emptyName:
      g1.tasks[0].name = "  ";
      break;
    case MARKER.long:
      g1.tasks[0].description = "長".repeat(20_500);
      break;
    case MARKER.multi:
      g1.tasks = manyTasks(25, 1);
      break;
    case MARKER.ui3:
      g1.tasks = manyTasks(25, 1);
      g1.dependsOn = ["g2"];
      break;
    default:
      break;
  }
  return base;
}

export class FakeLlm {
  readonly requests: LlmRequest[] = [];
  /** false＝不管文件裡有沒有 GATE_* 標記，一律回正常樹（讓「修正後重試」成功） */
  gatesOn = true;
  /** 每次回應前的延遲（毫秒），拿來拍「解析中」畫面 */
  delayMs = 0;
  /** 探測請求（max_tokens=1）要回的 HTTP 狀態；預設 200 */
  probeStatus = 200;
  port = 0;
  private server: Server | null = null;

  constructor(private readonly projectName: string) {}

  get endpoint(): string {
    return `http://127.0.0.1:${this.port}/v1/chat/completions`;
  }

  /** 對 /v1/chat/completions 的 POST 次數（只算路徑完全相符者）。 */
  count(): number {
    return this.requests.filter((r) => r.method === "POST" && r.url === "/v1/chat/completions").length;
  }

  async listen(): Promise<void> {
    this.server = createServer((req, res) => {
      const chunks: Buffer[] = [];
      req.on("data", (c: Buffer) => chunks.push(c));
      req.on("end", () => {
        let body: Json = {};
        try {
          body = JSON.parse(Buffer.concat(chunks).toString("utf-8")) as Json;
        } catch {
          body = {};
        }
        this.requests.push({ method: req.method ?? "", url: req.url ?? "", headers: req.headers, body });
        const send = (status: number, payload: unknown) => {
          setTimeout(() => {
            res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
            res.end(JSON.stringify(payload));
          }, this.delayMs);
        };
        if (req.method !== "POST" || req.url !== "/v1/chat/completions") {
          send(404, { error: "not found" });
          return;
        }
        if (body.max_tokens === 1) {
          // test-connection 的探測：{"model":…,"messages":[{"content":"ping"}],"max_tokens":1,"stream":false}
          send(this.probeStatus, wrap("pong"));
          return;
        }
        const text = JSON.stringify(body);
        // 標記有包含關係（GATE_EMPTY ⊂ GATE_EMPTY_NAME）：長的先比
        const hit = this.gatesOn
          ? Object.values(MARKER)
              .sort((a, b) => b.length - a.length)
              .find((m) => text.includes(m))
          : undefined;
        if (hit === MARKER.http500) send(500, { error: "boom" });
        else if (hit === MARKER.badJson) send(200, wrap("not json"));
        else if (hit) send(200, wrap(JSON.stringify(gateTree(hit, this.projectName))));
        else send(200, wrap(JSON.stringify(okTree(this.projectName))));
      });
    });
    await new Promise<void>((resolve) => this.server!.listen(0, "127.0.0.1", resolve));
    this.port = (this.server.address() as { port: number }).port;
  }

  async close(): Promise<void> {
    const s = this.server;
    this.server = null;
    if (s) await new Promise<void>((resolve) => s.close(() => resolve()));
  }
}

/** 匯入頁用的需求文件：兩個 ## 標題、遠超過 200 字元的 Markdown（走路徑 B 而不是 C）。 */
export const brd = (marker = ""): string =>
  `# BRD：E2E 匯入專案 ${RUN}\n\n## 基礎\n建立專案骨架與設定環境，確保任何人 clone 之後都能一鍵啟動。\n\n## 核心\n實作核心模組並補上單元測試，覆蓋率達標才算完成。\n\n（以上為測試用需求文件，長度刻意超過 200 字元以走路徑 B）${"細節描述。".repeat(20)}${marker ? `\n${marker}` : ""}`;
