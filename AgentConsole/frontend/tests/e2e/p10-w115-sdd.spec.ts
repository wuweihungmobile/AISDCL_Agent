import { execFile } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

import { expect, test, type APIRequestContext } from "@playwright/test";

import { API_URL, RUN } from "./helpers";
import { collectConsoleErrors } from "./mockApi";
import { E2E_ROOT, NEEDS_BRIDGE, bootstrapSettings, call, dataOf, ensureQuota, poll, signIn, waitRun, type Json, type Reply } from "./realBackend";
import { MOCK_CLAUDE, REPO_PY, REPO_ROOT, realSddLatest, startBridge, walkFiles, yamlLoad, type VariantBridge } from "./w7";

/**
 * 整合輪 115 W5 QA：契約 v1.5 E2E-17（SDD 迴圈；API-SGN-06、API-PRJ-07／08、API-EXE-15／16、API-ENG-02、API-IMP-11／12、BR-27～BR-33、UI-SDD-01～03、NFR-OBS-01）。
 * 對**真後端**（console-api＋PostgreSQL＋真 Engine Bridge＋aisdlc-mock-claude）與**真的 SDD CLI／真的 FSM 狀態檔**：測試自己扮演「SDD session」，以 SDD CLI 把 FSM 專案推進到
 * HUMAN_PENDING（不手寫 YAML，Rule 9 絕對禁令第 1 條）；FSM、稽核與 PG 一律用獨立讀取（PyYAML、Bridge 稽核檔、psql），不經被測 API。
 * 前置（QA 報告〈環境〉）：backend（e2e profile）與 Bridge（18081）都設 BRIDGE_SDD_WRITE_TOKEN＝E2E_SDD_TOKEN（≥32 字元的拋棄式測試值，不入檔、不印出）；
 * BRIDGE_ALLOWED_PATH_ROOTS 含 E2E_ROOT；backend 的 mock-env 設 MOCK_CLAUDE_DELAY≥3（讓 AUTOCLAUDE_DELEGATED 觀察得到）。
 * 沒有 E2E_ROOT／E2E_SDD_TOKEN 時整支略過（一般開發機沒有真 Bridge）。第二個 Bridge（18086）不設權杖，專驗第 1 列。
 */
test.skip(!process.env.E2E_SDD_TOKEN, "需要寫入權杖：兩端設同一個 BRIDGE_SDD_WRITE_TOKEN，並把該值放進 E2E_SDD_TOKEN（見 tests/e2e/README.md〈真 Bridge specs〉）");
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const execFileAsync = promisify(execFile);
const TOKEN = process.env.E2E_SDD_TOKEN ?? "";
const BRIDGE = process.env.E2E_BRIDGE_URL ?? "http://127.0.0.1:18081";
const PG = process.env.E2E_PG_CONTAINER ?? "qa-pg";
const NO_TOKEN_PORT = 18086;
const SDD_LATEST = realSddLatest() ?? "";
const SDD_DIR = path.join(REPO_ROOT, "AISDLC_SDD", SDD_LATEST);
const SUITE = path.join(E2E_ROOT, "sdd-e2e", RUN);
const AUDIT = path.join(process.env.E2E_BRIDGE_WORKSPACE ?? path.join(E2E_ROOT, "workspace"), "_audit.jsonl");
const MOCK_TRACE = process.env.E2E_MOCK_TRACE ?? path.join(E2E_ROOT, "mock-trace.jsonl");
const FIRST_LOAD = { timeout: 60_000 };
const CONTRACTS_REL = "docs/03_testing/contracts";

const pad = (n: number) => String(n).padStart(2, "0");
/** 契約 M-20 的時間顯示：本機時區的 `YYYY-MM-DD HH:MM:SS`（測試端獨立實作）。 */
const localTime = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

// ── 夾具：TCS、專案根、摘要 ─────────────────────────────────────────────────────────────────────────────────────
type Row = [ac: string, at: string, kind: string, literal: string];

/** 官方模板格式的最小 TCS（與 Bridge 夾具測試同形）；extraMap 加在 §1 映射表尾（unmapped 夾具用）、extraBlocks 加在 Gherkin 區塊尾。 */
function tcsText(rows: Row[], title: string, extra: { map?: string; blocks?: string } = {}): string {
  const head =
    `# Test Contract Specification — ${title}\n\n**spec-format-version**: 1.0\n**scenario**: greenfield\n\n## 1. AC → AT 映射表\n\n` +
    "| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |\n|-------|---------|-------|---------|-------|---------|------|\n";
  const table = rows.map(([ac, at, kind]) => `| ${ac} | 夾具驗收 | ${at} | 夾具 | ✅ | ${kind} | □ |\n`).join("") + (extra.map ?? "");
  const blocks = rows.map(([, at, , lit]) => `\`\`\`gherkin\n# ${at}\nScenario: 夾具 ${at}\n  Given 系統就緒\n  When 執行\n  Then 輸出 "${lit}"\n\`\`\`\n\n`).join("") + (extra.blocks ?? "");
  return `${head}${table}\n## 2. AT 格式\n\n${blocks}`;
}
/** 換行正規化後的 UTF-8 文字的 sha256（ADR-XPLAT-016 §4.3；測試獨立實作，不引用任何產品碼）。 */
const digestOf = (text: string): string => `sha256:${createHash("sha256").update(text.replace(/\r\n/g, "\n").replace(/\r/g, "\n"), "utf8").digest("hex")}`;
const fileDigest = (file: string): string => digestOf(readFileSync(file, "utf8"));

const OK_ROWS: Row[] = [
  ["AC-001-1", "AT-001-1-1", "Unit", "[AT_OK_1]"],
  ["AC-001-1", "AT-001-1-2", "Integration", "[AT_OK_2]"],
  ["AC-001-2", "AT-001-2-1", "Unit", "[AT_OK_3]"],
  ["AC-001-2", "AT-001-2-E-1", "Unit", "[AT_OK_4]"],
];
const FAIL_ROWS: Row[] = [["AC-001-1", "AT-001-1-1", "E2E", "NEVER_PRINTED_1"]];
const ONE_ROW = (n: number): Row[] => [["AC-001-1", "AT-001-1-1", "Unit", `[AT_OK_${n}]`]];

type Fx = { name: string; root: string; tcsName: string; tcsRel: string; tcsAbs: string; contracts: string; text: string; digest: string; fsmDir: string };
/** 專案根（SUITE 之下）：TCS 放 contracts；tests/ 預置會通過的測試檔（函式名含 AT 的底線化 token，評估指令 `pytest tests -k` 不依賴 AI）；.gitignore 含 build/reports/。 */
function makeFixture(dirName: string, name: string, tcsName: string, rows: Row[], text?: string): Fx {
  const root = path.join(SUITE, dirName);
  const contracts = path.join(root, ...CONTRACTS_REL.split("/"));
  mkdirSync(contracts, { recursive: true });
  const body = text ?? tcsText(rows, name);
  writeFileSync(path.join(contracts, tcsName), body, { encoding: "utf-8" });
  mkdirSync(path.join(root, "tests"), { recursive: true });
  for (const [, at] of rows) {
    const token = at.replace(/-/g, "_");
    writeFileSync(path.join(root, "tests", `test_${token}.py`), `def test_${token}_basic():\n    assert True\n`, { encoding: "utf-8" });
  }
  writeFileSync(path.join(root, ".gitignore"), "build/reports/\n", { encoding: "utf-8" });
  return {
    name,
    root,
    tcsName,
    tcsRel: `${CONTRACTS_REL}/${tcsName}`,
    tcsAbs: path.join(contracts, tcsName),
    contracts,
    text: body,
    digest: digestOf(body),
    fsmDir: path.join(root, "build", "reports", "fsm"),
  };
}

// ── 扮演「人在 SDD session」：真 CLI 子行程（外部專案模式，狀態檔住專案根） ──────────────────────────────────────────
function cliEnv(root: string): NodeJS.ProcessEnv {
  const env: Record<string, string | undefined> = {};
  for (const [k, v] of Object.entries(process.env)) {
    if (/^(BRIDGE_|SDD_)/i.test(k) || k.toUpperCase() === "PYTHONPATH") continue;
    env[k] = v;
  }
  return {
    ...env,
    SDD_STATE_DIR: path.join(root, "build", "reports", "fsm"),
    PYTHONPATH: SDD_DIR,
    PYTHONUTF8: "1",
    PYTHONDONTWRITEBYTECODE: "1",
    SDD_ENABLE_RULE_FIRE_TELEMETRY: "0",
    SDD_ENABLE_RULE_CATCH_TELEMETRY: "0",
  } as unknown as NodeJS.ProcessEnv;
}
async function sdd(root: string, ...argv: string[]): Promise<{ rc: number; out: string; err: string }> {
  try {
    const { stdout, stderr } = await execFileAsync(REPO_PY, ["-W", "ignore::RuntimeWarning", "-m", "tools.fsm_runtime.fsm_runtime", ...argv], {
      cwd: SDD_DIR,
      env: cliEnv(root),
      encoding: "utf8",
      timeout: 180_000,
      windowsHide: true,
      maxBuffer: 8 * 1024 * 1024,
    });
    return { rc: 0, out: stdout, err: stderr };
  } catch (e) {
    const x = e as { code?: number | string; stdout?: string; stderr?: string };
    return { rc: typeof x.code === "number" ? x.code : 1, out: x.stdout ?? "", err: x.stderr ?? "" };
  }
}
/** SCG 閘門走到 HUMAN_PENDING（SDD_SPEC_FIRST_GATE.md〈FSM 寫入指令〉：逐步 transition，最後一個 gate --result PASS）。 */
async function walkToHumanPending(root: string, key: string): Promise<void> {
  const steps: Array<[string, string]> = [
    ["SCENARIO_DETECT", "夾具：建立 FSM 專案"],
    ["AGENT_LOAD", "夾具：載入角色"],
    ["SPEC_DRAFTING", "夾具：規格撰寫"],
    ["SCG_VALIDATION", "夾具：SCG 驗證開始"],
  ];
  for (const [to, why] of steps) {
    const r = await sdd(root, "transition", "--project", key, "--to", to, "--reason", why);
    expect(r.rc, `transition → ${to}：${r.out}${r.err}`).toBe(0);
  }
  const g = await sdd(root, "gate", "--project", key, "--gate", "SCG_VALIDATION", "--result", "PASS", "--reason", "夾具：SCG 通過");
  expect(g.rc, `gate PASS：${g.out}${g.err}`).toBe(0);
  expect((await fsmOf(root, key)).current_state).toBe("HUMAN_PENDING");
}

type FsmState = Json & {
  current_state: string;
  decision_trace: Array<{ ts: string; from: string; to: string; trigger: string; reason: string; spec_refs?: string[] }>;
  frozen_stages: Array<{ stage: string; frozen_at: string; spec_docs: string[]; spec_doc_digests?: Record<string, string>; approved_by?: string }>;
  escalation_history: Array<Json & { resolved_at: string | null; resolution?: string }>;
  escalation_provenance?: { source?: string } | null;
  autoclaude_delegated_tracking?: { playbook_ref?: string; resume_state?: string } | null;
};
const fsmFile = (root: string, key: string) => path.join(root, "build", "reports", "fsm", `FSM-STATE-${key}.yaml`);
const fsmOf = async (root: string, key: string): Promise<FsmState> => (await yamlLoad<{ fsm_state: FsmState }>(fsmFile(root, key))).fsm_state;
const waitFsm = (root: string, key: string, state: string, ms = 30_000): Promise<FsmState> =>
  poll(
    () => fsmOf(root, key),
    (s) => s.current_state === state,
    `FSM ${key} 進入 ${state}`,
    ms,
    1000,
  );
const fsmDirSnapshot = (root: string): Record<string, string> => {
  const dir = path.join(root, "build", "reports", "fsm");
  const out: Record<string, string> = {};
  if (!existsSync(dir)) return out;
  for (const n of readdirSync(dir))
    out[n] = createHash("sha256")
      .update(readFileSync(path.join(dir, n)))
      .digest("hex");
  return out;
};

// ── Bridge 直打、稽核檔、PG ───────────────────────────────────────────────────────────────────────────────────
type BridgeReply = { status: number; json: Json; text: string };
async function bridge(method: "GET" | "POST", p: string, opts: { token?: string | null; body?: unknown; base?: string } = {}): Promise<BridgeReply> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (opts.token) headers["X-Bridge-Token"] = opts.token;
  const res = await fetch(`${opts.base ?? BRIDGE}${p}`, { method, headers, body: opts.body === undefined ? undefined : JSON.stringify(opts.body) });
  const text = await res.text();
  let json: Json = {};
  try {
    json = JSON.parse(text) as Json;
  } catch {
    json = {};
  }
  return { status: res.status, json, text };
}
const bridgeFsm = (key: string, root: string, base?: string) => bridge("GET", `/sdd/fsm/${encodeURIComponent(key)}?root=${encodeURIComponent(root)}`, { base });
const auditRows = (): Json[] =>
  existsSync(AUDIT)
    ? readFileSync(AUDIT, "utf8")
        .split("\n")
        .filter(Boolean)
        .map((l) => JSON.parse(l) as Json)
    : [];
const SEP = "\u001f";
async function psql(sql: string): Promise<string[][]> {
  const { stdout } = await execFileAsync("docker", ["exec", PG, "psql", "-U", "aisdlc", "-d", "aisdlc", "-t", "-A", "-F", SEP, "-c", sql], { encoding: "utf8", timeout: 30_000, windowsHide: true });
  return stdout
    .split(/\r?\n/)
    .filter(Boolean)
    .map((l) => l.split(SEP));
}
const sqlq = (s: string) => `'${s.replace(/'/g, "''")}'`;
type TraceRow = { keywords?: string[]; sdd_env?: { SDD_PROJECT: string | null; SDD_STATE_DIR: string | null; has_write_token: boolean } };
/** 替身 claude 的呼叫軌跡（backend 的 mock-env 帶 MOCK_CLAUDE_TRACE）：每次 `-p` 一行，含引擎子行程環境的三個 SDD 相關事實。 */
const traceRows = (): TraceRow[] =>
  existsSync(MOCK_TRACE)
    ? readFileSync(MOCK_TRACE, "utf8")
        .split("\n")
        .filter(Boolean)
        .map((l) => JSON.parse(l) as TraceRow)
    : [];

// ── Console API 小工具 ─────────────────────────────────────────────────────────────────────────────────────────
const errOf = (r: Reply) => r.json as { reason?: string; details?: Json; errors?: Array<{ field?: string }>; message?: string; traceId?: string };
type Project = Json & { id: string; sddProject: string | null; sddSpecDir: string | null; sddSpecFile: string | null; goals?: Array<{ id: string; name: string }> };
type SddStatus = { available: boolean; reason: string | null; version: { latest: string; root: string } | null; projects: Array<{ project: string; currentState: string | null }>; fsm: Fsm | null };
type Fsm = {
  project: string;
  fsmProject: string | null;
  currentState: string;
  frozenStages: Array<{ stage: string; spec_docs: string[]; spec_doc_digests?: Record<string, string>; approved_by?: string }>;
  phase: { name: string; order: number; blocking: boolean; observation: boolean } | null;
  escalationHistory: Array<{ resolved_at: string | null }>;
  escalationProvenance: { source?: string } | null;
  recovery?: { target: string; powershell: string; posix: string } | null;
  decisionTrace: Array<{ from: string; to: string; reason: string }>;
};
const engines = (request: APIRequestContext, q: string, role: "viewer" | "operator" | "admin" = "viewer") => call(request, role, "GET", `/api/v1/engines/sdd${q}`);
const statusOf = async (request: APIRequestContext, q: string): Promise<SddStatus> => {
  const r = await engines(request, q);
  expect(r.status, JSON.stringify(r.json).slice(0, 400)).toBe(200);
  return dataOf<SddStatus>(r);
};
async function consoleProject(request: APIRequestContext, name: string, root: string): Promise<string> {
  const p = await call(request, "operator", "POST", "/api/v1/projects", { name, executionPath: root, passCriteria: "全部完成", description: "E2E-17 夾具", autonomyLevel: 4, draft: false });
  expect(p.status, `建專案 ${name} → ${JSON.stringify(p.json)}`).toBe(201);
  return dataOf<{ id: string }>(p).id;
}
const projectOf = async (request: APIRequestContext, id: string): Promise<Project> => {
  const r = await call(request, "viewer", "GET", `/api/v1/projects/${id}`);
  expect(r.status, JSON.stringify(r.json)).toBe(200);
  return dataOf<Project>(r);
};
const freezeApi = (request: APIRequestContext, role: "viewer" | "operator" | "admin", projectId: string, body: unknown) =>
  call(request, role, "POST", `/api/v1/projects/${projectId}/sdd/freeze`, body);
/** 路徑 A 匯入：貼一段文字（不參與解析）→ parse（併入 targetProjectId）。 */
async function importParse(request: APIRequestContext, opts: { root: string; targetProjectId?: string; specDir?: string; specFile?: string }): Promise<{ importId: string; parse: Reply }> {
  const r1 = await call(request, "operator", "POST", "/api/v1/import/text", { content: "E2E-17 規格文字（不參與解析）", sourceType: "MARKDOWN", sourceFileName: "e2e17.md" });
  expect(r1.status, JSON.stringify(r1.json)).toBe(201);
  const importId = dataOf<{ id: string }>(r1).id;
  const body: Json = { executionPath: opts.root, autonomyLevel: 4 };
  if (opts.targetProjectId) body.targetProjectId = opts.targetProjectId;
  if (opts.specDir) body.specDir = opts.specDir;
  if (opts.specFile) body.specFile = opts.specFile;
  return { importId, parse: await call(request, "operator", "POST", `/api/v1/import/${importId}/parse`, body) };
}
/**
 * 專案層簽核（Phase 2）。手動建立（draft:false）的專案本來就是已簽核，再簽回 409「已 signoff」；契約 E2E-17 第 8 列寫「再以 Phase 2 簽核專案」只對草稿專案成立
 * （W5 審查 Q-05：契約沒有交代夾具專案要建成草稿）。這裡兩種都接受，真正要斷言的是之後 execute 不被「整案 signedOff」擋下。
 */
async function signProject(request: APIRequestContext, pid: string): Promise<void> {
  const r = await call(request, "operator", "POST", `/api/v1/projects/${pid}/signoff`, { approver: "operator" });
  expect([200, 409], `專案 signoff → ${JSON.stringify(r.json)}`).toContain(r.status);
}
/** 凍結 → 匯入併入 → 匯入簽核 → confirm → 專案簽核（E2E-17 第 5、8 列的共同前半）。回傳 Console 專案 id。 */
async function frozenImportedProject(request: APIRequestContext, fx: Fx, dirName = path.basename(fx.root)): Promise<string> {
  await walkToHumanPending(fx.root, fx.name);
  const pid = await consoleProject(request, fx.name, fx.root);
  const f = await freezeApi(request, "operator", pid, { reason: `E2E 核准（${dirName}）`, docs: [fx.tcsRel] });
  expect(f.status, `freeze ${fx.name} → ${JSON.stringify(f.json).slice(0, 400)}`).toBe(200);
  const { importId, parse } = await importParse(request, { root: fx.root, targetProjectId: pid, specDir: fx.contracts, specFile: fx.tcsName });
  expect(parse.status, `parse ${fx.name} → ${JSON.stringify(parse.json).slice(0, 500)}`).toBe(200);
  const so = await call(request, "operator", "POST", `/api/v1/import/${importId}/signoff`, { approver: "operator" });
  expect(so.status, JSON.stringify(so.json)).toBe(200);
  const cf = await call(request, "operator", "POST", `/api/v1/import/${importId}/confirm`);
  expect(cf.status, `confirm ${fx.name} → ${JSON.stringify(cf.json).slice(0, 400)}`).toBe(201);
  await signProject(request, pid);
  return pid;
}
const execute = (request: APIRequestContext, pid: string) => call(request, "operator", "POST", `/api/v1/projects/${pid}/execute`, { autonomyLevel: 4, tokenBudget: 1_000_000, scope: { mode: "ALL" } });
/**
 * 凍結後改檔 → execute 回 409 `sdd_spec_digest_changed`（G-06；BR-30）：details 帶 pair／doc／兩個摘要；零副作用＝沒有新的 execution_runs 列（已補償刪除）、
 * FSM 的狀態、軌跡筆數與 updated_at 都不變。不論斷言成敗，離開前一律把規格檔還原成凍結時的內容（避免污染後續情境）。
 */
async function expectDigestGate(request: APIRequestContext, fx: Fx, pid: string, expectState: string): Promise<void> {
  const runsBefore = await psql(`select count(*) from console.execution_runs where project_id = ${sqlq(pid)}`);
  const fsmBefore = await fsmOf(fx.root, fx.name);
  expect(fsmBefore.current_state).toBe(expectState);
  writeFileSync(fx.tcsAbs, fx.text + "\n凍結後多的一行\n", "utf-8");
  try {
    const r = await execute(request, pid);
    expect(r.status, JSON.stringify(r.json).slice(0, 400)).toBe(409);
    expect(errOf(r).reason).toBe("sdd_spec_digest_changed");
    const d = errOf(r).details as { pair: string; doc: string; frozenDigest: string; currentDigest: string };
    expect(d.pair).toBe("frozen_vs_file");
    expect(d.doc).toBe(fx.tcsRel);
    expect(d.frozenDigest).toBe(fx.digest);
    expect(d.currentDigest).toBe(fileDigest(fx.tcsAbs));
    expect(d.currentDigest).not.toBe(d.frozenDigest);
    const runsAfter = await psql(`select count(*) from console.execution_runs where project_id = ${sqlq(pid)}`);
    expect(runsAfter[0][0], "沒有新的 execution_runs 列（已補償刪除）").toBe(runsBefore[0][0]);
    const fsmAfter = await fsmOf(fx.root, fx.name);
    expect(fsmAfter.current_state, "FSM 狀態不動").toBe(expectState);
    expect(fsmAfter.decision_trace.length, "FSM 沒有新增軌跡").toBe(fsmBefore.decision_trace.length);
    expect(fsmAfter.updated_at, "FSM updated_at 不變").toBe(fsmBefore.updated_at);
  } finally {
    writeFileSync(fx.tcsAbs, fx.text, "utf-8");
  }
}
type RunData = { id: string; runNumber: number; status: string; reason?: string; warnings?: Array<{ code: string; cause?: string; detail?: string }> };
const stepIds = async (request: APIRequestContext, runId: string): Promise<string[]> => {
  const r = await call(request, "viewer", "GET", `/api/v1/executions/${runId}/steps?size=200`);
  expect(r.status, JSON.stringify(r.json)).toBe(200);
  const rows = dataOf<{ content: Array<{ stepId: string; status: string }> }>(r).content;
  return [...new Set(rows.map((s) => s.stepId))];
};

let noToken: VariantBridge | null = null;
test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  mkdirSync(SUITE, { recursive: true });
  await bootstrapSettings(request, MOCK_CLAUDE);
});
test.afterAll(async () => {
  await noToken?.stop();
});
test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "viewer", 60);
  await ensureQuota(request, "operator", 60);
});

type Ctx = { alpha: Fx; pid: string; runId: string };
const ctx: Partial<Ctx> = {};

test.describe("E2E-17：SDD 迴圈（真後端、真 Bridge、真 SDD CLI；替身引擎）", () => {
  test.setTimeout(300_000);

  test("列 1｜Bridge 沒設權杖：寫入面停用（503 sdd_write_disabled），唯讀照常、FSM 不動、沒建 run 目錄（BR-33）", async () => {
    const alpha = makeFixture("alpha", "e2e17-alpha", `TCS-Alpha-${RUN}.md`, OK_ROWS);
    ctx.alpha = alpha;
    await walkToHumanPending(alpha.root, alpha.name);
    noToken = await startBridge({ port: NO_TOKEN_PORT, root: path.join(SUITE, "b18086"), instance: "e2e17-notoken", extraEnv: { BRIDGE_ALLOWED_PATH_ROOTS: E2E_ROOT } });
    const base = noToken.url;
    const before = fsmDirSnapshot(alpha.root);
    const freeze = await bridge("POST", `/sdd/fsm/${alpha.name}:freeze`, {
      base,
      token: "any-token-value-with-no-meaning-0123456789abc",
      body: { root: alpha.root, docs: [alpha.tcsRel], approver: "operator", reason: "E2E 核准" },
    });
    expect(freeze.status, freeze.text).toBe(503);
    expect(freeze.json.reason).toBe("sdd_write_disabled");
    const runId = randomUUID();
    const runBody = {
      run_id: runId,
      project: alpha.name,
      execution_path: alpha.root,
      playbook: { version: "1.0", project: alpha.name, tasks: [{ step_id: "sdd-greenfield-at-001-1-1", name: "x", prompt: "請輸出 [AT_OK_1]" }] },
      sdd: { spec_dir: alpha.contracts, fsm_project: alpha.name, root: alpha.root },
    };
    const run = await bridge("POST", "/autoclaude/runs", { base, token: "any-token-value-with-no-meaning-0123456789abc", body: runBody });
    expect(run.status, run.text).toBe(503);
    expect(run.json.reason).toBe("sdd_write_disabled");
    const read = await bridgeFsm(alpha.name, alpha.root, base);
    expect(read.status, "唯讀不需要權杖").toBe(200);
    expect((read.json as { current_state: string }).current_state).toBe("HUMAN_PENDING");
    expect(fsmDirSnapshot(alpha.root), "FSM 檔不變").toEqual(before);
    const ws = path.join(SUITE, "b18086", "ws");
    expect(existsSync(path.join(ws, runId)), "帶 sdd 的請求沒有建立任何 run 目錄").toBe(false);
    console.log("[w115-sdd] 列 1：18086 兩個寫入皆 503 sdd_write_disabled；GET 200；FSM 檔 sha256 不變；沒有 run 目錄");
    // 第 1 列「不含 sdd 的 run 照舊 201」不跑：18086 沒有替身引擎設定，會誤起真 claude（見審查證據檔 §8）
  });

  test("列 2｜權杖缺或錯：403 sdd_write_forbidden（缺與錯同一個 reason）；回應與稽核不含權杖值；FSM 檔不變（BR-33）", async () => {
    const alpha = ctx.alpha!;
    const before = fsmDirSnapshot(alpha.root);
    const body = { root: alpha.root, docs: [alpha.tcsRel], approver: "operator", reason: "E2E 核准" };
    const wrong = "wrong-token-value-for-qa-0123456789abcdefghij";
    const missing = await bridge("POST", `/sdd/fsm/${alpha.name}:freeze`, { token: null, body });
    const bad = await bridge("POST", `/sdd/fsm/${alpha.name}:freeze`, { token: wrong, body });
    for (const r of [missing, bad]) {
      expect(r.status, r.text).toBe(403);
      expect(r.json.reason).toBe("sdd_write_forbidden");
      expect(r.text.includes(TOKEN) || r.text.includes(wrong), "回應不含權杖值").toBe(false);
    }
    expect(fsmDirSnapshot(alpha.root)).toEqual(before);
    const rejected = auditRows().filter((a) => a.event === "sdd_write" && String(a.result).startsWith("rejected:sdd_write_forbidden") && a.project === alpha.name);
    expect(rejected.length, "Bridge 稽核有兩筆拒絕事件").toBeGreaterThanOrEqual(2);
    const raw = existsSync(AUDIT) ? readFileSync(AUDIT, "utf8") : "";
    expect(raw.includes(TOKEN) || raw.includes(wrong), "稽核檔不含任何權杖值（含被拒的那個）").toBe(false);
  });

  test("列 3｜前置狀態不符：FSM 專案停在 INIT 時帶正確權杖 :freeze → 409 fsm_state_conflict（BR-27）", async () => {
    const init = makeFixture("init", "e2e17-init", `TCS-Init-${RUN}.md`, ONE_ROW(1));
    const shown = await sdd(init.root, "show", "--project", init.name);
    expect(shown.rc, shown.err).toBe(0);
    expect((await fsmOf(init.root, init.name)).current_state).toBe("INIT");
    const before = fsmDirSnapshot(init.root);
    const r = await bridge("POST", `/sdd/fsm/${init.name}:freeze`, { token: TOKEN, body: { root: init.root, docs: [init.tcsRel], approver: "operator", reason: "E2E 核准" } });
    expect(r.status, r.text).toBe(409);
    expect(r.json.reason).toBe("fsm_state_conflict");
    const detail = (r.json.detail ?? r.json) as { current_state?: string; expected_state?: string };
    expect(detail.current_state ?? (r.json as { current_state?: string }).current_state).toBe("INIT");
    expect(detail.expected_state ?? (r.json as { expected_state?: string }).expected_state).toBe("HUMAN_PENDING");
    expect(fsmDirSnapshot(init.root)).toEqual(before);
  });

  test("列 4｜多專案狀態共處只認指定者：m-alpha 未凍結、m-zeta 已凍結（G-02／F-2 的 E2E 面）", async () => {
    const multi = path.join(SUITE, "multi");
    const a = makeFixture("multi", "m-alpha", "TCS-MAlpha-x.md", ONE_ROW(1));
    const z = makeFixture("multi", "m-zeta", "TCS-MZeta-x.md", [["AC-001-1", "AT-001-1-1", "Unit", "[AT_OK_2]"]]);
    expect(a.root).toBe(z.root);
    expect(a.root).toBe(multi);
    expect((await sdd(multi, "show", "--project", "m-alpha")).rc).toBe(0); // m-alpha 停在 INIT
    await walkToHumanPending(multi, "m-zeta");
    const fz = await bridge("POST", "/sdd/fsm/m-zeta:freeze", { token: TOKEN, body: { root: multi, docs: [z.tcsRel], approver: "operator", reason: "E2E 核准" } });
    expect(fz.status, fz.text).toBe(200);
    const compile = (body: Json) => bridge("POST", "/sdd/compile", { body: { spec_dir: a.contracts, ...body } });
    const c1 = await compile({ spec_file: "TCS-MAlpha-x.md", fsm_project: "m-alpha" });
    expect(c1.status, "m-alpha 未凍結：不得因 m-zeta 已凍結而放行").toBe(422);
    expect(c1.json.reason).toBe("spec_not_frozen");
    const c2 = await compile({ spec_file: "TCS-MZeta-x.md", fsm_project: "m-zeta" });
    expect(c2.status, c2.text).toBe(200);
    expect((c2.json as { fsm_project: string; frozen_digest: string }).fsm_project).toBe("m-zeta");
    expect((c2.json as { frozen_digest: string }).frozen_digest).toBe("verified");
    const c3 = await compile({ spec_file: "TCS-MAlpha-x.md" });
    expect(c3.status).toBe(422);
    expect(c3.json.reason).toBe("spec_not_frozen");
    expect(String(c3.json.detail), "detail 說明狀態檔不唯一").toContain("不唯一");
    const c4 = await compile({ spec_file: "TCS-MAlpha-x.md", fsm_project: "nope" });
    expect(c4.status).toBe(422);
    expect(c4.json.reason).toBe("spec_not_frozen");
    expect(String(c4.json.detail), "detail 列出現有專案鍵").toContain("m-alpha");
    expect(String(c4.json.detail)).toContain("m-zeta");
  });

  test("列 5｜核准凍結：人工閘（C2）——畫面送出，FSM decision_trace／Bridge 稽核／audit_log／PG 綁定同 approver 與 trace_id（API-SGN-06、API-PRJ-07、BR-27）", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    const alpha = ctx.alpha!;
    ctx.pid = await consoleProject(request, alpha.name, alpha.root);
    const pid = ctx.pid;
    expect((await projectOf(request, pid)).sddProject, "凍結前 sddProject 為 null（用預設）").toBeNull();
    await signIn(page, request, "operator");
    await page.goto(`/projects/${pid}`);
    await expect(page.getByTestId("project-title")).toHaveText(alpha.name, FIRST_LOAD);
    await page.getByRole("button", { name: /SDD 治理/ }).click();
    const gov = page.getByTestId("sdd-governance");
    await expect(gov.getByTestId("sdd-gov-state")).toHaveText("HUMAN_PENDING", FIRST_LOAD);
    await expect(gov.getByTestId("sdd-gov-pending")).toHaveText("等待人工確認");
    await expect(gov.getByTestId("sdd-phase-label")).toHaveText("人工確認");
    await expect(page.getByTestId("sdd-freeze-button")).toBeEnabled();
    await page.getByTestId("sdd-freeze-button").click();
    const dialog = page.getByRole("dialog", { name: "核准凍結規格" });
    await expect(dialog.getByTestId("sdd-freeze-approver")).toContainText("核准人：operator");
    await dialog.getByTestId("sdd-freeze-docs").fill(alpha.tcsRel);
    await dialog.getByTestId("sdd-freeze-reason").fill("E2E 核准");
    const [freezeResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes(`/api/v1/projects/${pid}/sdd/freeze`) && r.request().method() === "POST"),
      dialog.getByRole("button", { name: "核准凍結" }).click(),
    ]);
    expect(freezeResp.status()).toBe(200);
    const traceId = freezeResp.headers()["x-trace-id"];
    await expect(page.getByText("已核准凍結")).toBeVisible();
    await expect(gov.getByTestId("sdd-gov-state")).toHaveText("SPEC_FROZEN");
    await expect(gov.getByTestId("sdd-phase-label")).toHaveText("規格凍結");
    await expect(page.getByTestId("sdd-freeze-button")).toBeDisabled();

    // FSM 檔（獨立 PyYAML）：decision_trace 末筆、frozen_stages 末筆
    const fsm = await fsmOf(alpha.root, alpha.name);
    const last = fsm.decision_trace[fsm.decision_trace.length - 1];
    expect([last.from, last.to, last.trigger, last.reason]).toEqual(["HUMAN_PENDING", "SPEC_FROZEN", "spec_frozen", "console-freeze approver=operator; reason=E2E 核准"]);
    expect(last.spec_refs).toEqual([alpha.tcsRel]);
    const stage = fsm.frozen_stages[fsm.frozen_stages.length - 1];
    expect(stage.stage).toBe("Stage-1");
    expect(stage.spec_docs).toEqual([alpha.tcsRel]);
    expect(stage.spec_doc_digests).toEqual({ [alpha.tcsRel]: alpha.digest });
    expect(stage.approved_by).toBe("operator");
    // Bridge 稽核：同一個 trace_id、approver、無權杖
    const audits = auditRows().filter((a) => a.trace_id === traceId && String(a.project) === alpha.name);
    const cli = audits.find((a) => a.event === "sdd_cli" && a.verb === "spec-frozen");
    const write = audits.find((a) => a.event === "sdd_write" && a.verb === "freeze");
    expect(cli, `稽核 sdd_cli（trace ${traceId}）`).toMatchObject({ result: "ok", rc: 0, approver: "operator" });
    expect(write, `稽核 sdd_write（trace ${traceId}）`).toMatchObject({ result: "ok", approver: "operator" });
    expect(JSON.stringify(audits).includes(TOKEN), "稽核列不含權杖").toBe(false);
    // Console 稽核（PG audit_log）與綁定寫回
    const audit = await psql(`select subject, method, path, http_status, trace_id from console.audit_log where trace_id = ${sqlq(traceId)}`);
    expect(audit.length, "audit_log 一列").toBe(1);
    expect(audit[0].slice(0, 2)).toEqual(["operator", "POST"]);
    expect(audit[0][2]).toBe(`/api/v1/projects/${pid}/sdd/freeze`);
    expect(audit[0][3]).toBe("200");
    const pg = await psql(`select sdd_project, sdd_spec_dir, sdd_spec_file from console.projects where id = ${sqlq(pid)}`);
    expect(pg[0]).toEqual([alpha.name, "", ""]);
    const p = await projectOf(request, pid);
    expect([p.sddProject, p.sddSpecDir ?? null, p.sddSpecFile ?? null]).toEqual([alpha.name, null, null]);
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
    console.log(`[w115-sdd] 列 5：畫面核准凍結 → FSM SPEC_FROZEN／Stage-1／摘要＝獨立計算；稽核 trace ${traceId} 三處同 approver；PG sdd_project=${alpha.name}`);
  });

  test("列 6｜凍結的不可重做、權限與驗證（API-SGN-06）：①409 ②403 ③401 ④400 ⑤400 ⑥422 ⑦409 ⑧400 ⑨400", async ({ request }) => {
    const alpha = ctx.alpha!;
    const pid = ctx.pid!;
    const snap = fsmDirSnapshot(alpha.root);
    const r1 = await freezeApi(request, "operator", pid, { reason: "E2E 再核准", docs: [alpha.tcsRel] });
    expect(r1.status).toBe(409);
    expect(errOf(r1).reason).toBe("sdd_fsm_state_conflict");
    expect(errOf(r1).details).toMatchObject({ currentState: "SPEC_FROZEN", expectedState: "HUMAN_PENDING" });
    expect((await freezeApi(request, "viewer", pid, { reason: "x", docs: [alpha.tcsRel] })).status).toBe(403);
    const anon = await request.post(`${API_URL}/api/v1/projects/${pid}/sdd/freeze`, { data: { reason: "x", docs: [alpha.tcsRel] }, failOnStatusCode: false });
    expect(anon.status()).toBe(401);
    const p1xDir = path.join(E2E_ROOT, "projects", `p1x-${RUN}`);
    mkdirSync(p1xDir, { recursive: true });
    const p1x = await consoleProject(request, `e2e17-p1x-${RUN}`, p1xDir);
    const r4 = await freezeApi(request, "operator", p1x, { reason: "x" });
    expect(r4.status).toBe(400);
    expect(errOf(r4).errors?.[0]?.field).toBe("docs");
    const r5 = await freezeApi(request, "operator", pid, { reason: "   ", docs: [alpha.tcsRel] });
    expect(r5.status).toBe(400);
    expect(errOf(r5).errors?.[0]?.field).toBe("reason");
    // ⑥ ⑦：HUMAN_PENDING 的另兩個 FSM 專案
    const notcs = makeFixture("notcs", "e2e17-notcs", "TCS-NoTcs-x.md", ONE_ROW(1));
    writeFileSync(path.join(notcs.root, "README.md"), "# readme\n", "utf-8");
    await walkToHumanPending(notcs.root, notcs.name);
    const pNo = await consoleProject(request, notcs.name, notcs.root);
    const r6 = await freezeApi(request, "operator", pNo, { reason: "E2E 核准", docs: ["README.md"] });
    expect(r6.status, JSON.stringify(r6.json)).toBe(422);
    expect(errOf(r6).details).toMatchObject({ violations: [{ field: "docs", rule: "missing_tcs" }] });
    const expectFx = makeFixture("expect", "e2e17-expect", "TCS-Expect-x.md", ONE_ROW(2));
    await walkToHumanPending(expectFx.root, expectFx.name);
    const pEx = await consoleProject(request, expectFx.name, expectFx.root);
    const wrongDigest = `sha256:${"0".repeat(64)}`;
    const r7 = await freezeApi(request, "operator", pEx, { reason: "E2E 核准", docs: [expectFx.tcsRel], expectedDigests: { [expectFx.tcsRel]: wrongDigest } });
    expect(r7.status, JSON.stringify(r7.json)).toBe(409);
    expect(errOf(r7).reason).toBe("sdd_spec_digest_changed");
    expect(errOf(r7).details).toMatchObject({ pair: "expected_vs_file" });
    for (const fx of [notcs, expectFx]) expect((await fsmOf(fx.root, fx.name)).current_state, `${fx.name} 仍 HUMAN_PENDING`).toBe("HUMAN_PENDING");
    const r8 = await freezeApi(request, "operator", pid, { reason: "x", docs: ["../x.md"] });
    expect(r8.status).toBe(400);
    // 契約 E2E-17 第 6 列⑧寫 `errors[0].field=docs`，實作對單一項回 `docs[<索引>]`（W5 審查 Q-02：契約字面與實作不同，前端欄位對映只認 `docs`）：這裡認兩種寫法，另案對齊。
    expect(errOf(r8).errors?.[0]?.field).toMatch(/^docs(\[\d+\])?$/);
    const r9 = await freezeApi(request, "operator", pid, { reason: "第一行\n第二行", docs: [alpha.tcsRel] });
    expect(r9.status).toBe(400);
    expect(errOf(r9).errors?.[0]?.field).toBe("reason");
    expect(fsmDirSnapshot(alpha.root), "①～⑨ 之後 alpha 的 FSM 檔不再變動").toEqual(snap);
  });

  test("列 7｜綁定唯一性與編輯（D-115-14；API-PRJ-08）：重複綁定 409 且 Bridge 沒收到任何寫入；PUT sdd-binding 的角色、驗證、稽核", async ({ request }) => {
    const alpha = ctx.alpha!;
    const pid = ctx.pid!;
    const writesBefore = auditRows().filter((a) => a.event === "sdd_write").length;
    const snap = fsmDirSnapshot(alpha.root);
    const p1b = await consoleProject(request, alpha.name, alpha.root); // 名稱與 executionPath 都同 alpha
    const r1 = await freezeApi(request, "operator", p1b, { reason: "E2E 核准", docs: [alpha.tcsRel] });
    expect(r1.status, JSON.stringify(r1.json)).toBe(409);
    expect(errOf(r1).reason).toBe("sdd_binding_conflict");
    expect(errOf(r1).details).toMatchObject({ cause: "already_bound_elsewhere", sddProject: alpha.name, holderProjectId: pid });
    expect(auditRows().filter((a) => a.event === "sdd_write").length, "Bridge 沒有收到任何寫入呼叫（稽核檔 sdd_write 筆數不變）").toBe(writesBefore);
    expect(fsmDirSnapshot(alpha.root)).toEqual(snap);
    const put = (role: "viewer" | "operator", id: string, value: unknown) => call(request, role, "PUT", `/api/v1/projects/${id}/sdd-binding`, { sddProject: value });
    const r2 = await put("operator", p1b, alpha.name);
    expect(r2.status).toBe(409);
    expect(errOf(r2).details).toMatchObject({ cause: "already_bound_elsewhere", holderProjectId: pid });
    const r3 = await put("operator", p1b, "other");
    expect(r3.status, JSON.stringify(r3.json)).toBe(200);
    expect(dataOf<Project>(r3).sddProject).toBe("other");
    const r4 = await put("operator", p1b, null);
    expect(r4.status).toBe(200);
    expect(dataOf<Project>(r4).sddProject ?? null).toBeNull();
    expect((await put("viewer", p1b, alpha.name)).status).toBe(403);
    const r6 = await put("operator", p1b, "x".repeat(101));
    expect(r6.status).toBe(400);
    expect(errOf(r6).errors?.[0]?.field).toBe("sddProject");
    const r7 = await put("operator", p1b, "  ");
    expect(r7.status).toBe(400);
    expect(errOf(r7).errors?.[0]?.field).toBe("sddProject");
    const binds = await psql(`select count(*) from console.audit_log where path = ${sqlq(`/api/v1/projects/${p1b}/sdd-binding`)} and method = 'PUT' and http_status = 200`);
    expect(Number(binds[0][0]), "③④ 兩次成功的 PUT 各一列稽核").toBe(2);
  });

  test("列 8＋14｜路徑 A 匯入併入既有專案（G-07、G-08、API-IMP-12）；engines/sdd?projectId= 的 phase 非 null（T-G 已接線；API-ENG-02）", async ({ request }) => {
    const alpha = ctx.alpha!;
    const pid = ctx.pid!;
    const before = await projectOf(request, pid);
    const { importId, parse } = await importParse(request, { root: alpha.root, targetProjectId: pid, specDir: alpha.contracts, specFile: alpha.tcsName });
    expect(parse.status, JSON.stringify(parse.json).slice(0, 600)).toBe(200);
    const data = dataOf<{ path: string; parsedResult: Json & { goals: Array<{ tasks: Array<Json & { maxRetries: number; passCriteriaSpec: Json }> }> }; warnings: unknown[] }>(parse);
    expect(data.path).toBe("SDD");
    const tasks = data.parsedResult.goals.flatMap((g) => g.tasks);
    expect(tasks, "恰 4 個任務").toHaveLength(4);
    expect(tasks.map((t) => (t.passCriteriaSpec as { stepId: string }).stepId)).toEqual([
      "sdd-greenfield-at-001-1-1",
      "sdd-greenfield-at-001-1-2",
      "sdd-greenfield-at-001-2-1",
      "sdd-greenfield-at-001-2-e-1",
    ]);
    expect(tasks.map((t) => t.maxRetries)).toEqual([5, 5, 5, 5]);
    expect(tasks.map((t) => (t.passCriteriaSpec as { maintainContext: boolean }).maintainContext)).toEqual([false, true, false, true]);
    expect(new Set(tasks.map((t) => (t.passCriteriaSpec as { specDigest: string }).specDigest))).toEqual(new Set([alpha.digest]));
    expect(data.warnings ?? []).toEqual([]);
    const pr = data.parsedResult as { specFormatVersion?: string; sddProject?: string; sddSpecDir?: string; sddSpecFile?: string };
    expect([pr.specFormatVersion, pr.sddProject]).toEqual(["1.0", alpha.name]);
    expect(path.resolve(pr.sddSpecDir ?? "")).toBe(path.resolve(alpha.contracts));
    expect(path.resolve(pr.sddSpecFile ?? "")).toBe(path.resolve(alpha.tcsAbs));
    const so = await call(request, "operator", "POST", `/api/v1/import/${importId}/signoff`, { approver: "operator" });
    expect(so.status, JSON.stringify(so.json)).toBe(200);
    const cf = await call(request, "operator", "POST", `/api/v1/import/${importId}/confirm`);
    expect(cf.status, JSON.stringify(cf.json)).toBe(201);
    const merged = dataOf<Project>(cf);
    expect(merged.id, "沒有建立新專案").toBe(pid);
    const after = await projectOf(request, pid);
    expect([after.name, after.executionPath, after.sddProject]).toEqual([before.name, before.executionPath, alpha.name]);
    expect(path.resolve(after.sddSpecFile ?? "")).toBe(path.resolve(alpha.tcsAbs));
    const pg = await psql(`select sdd_project, sdd_spec_dir, sdd_spec_file from console.projects where id = ${sqlq(pid)}`);
    expect(pg[0][0]).toBe(alpha.name);
    expect(path.resolve(pg[0][1])).toBe(path.resolve(alpha.contracts));
    expect(path.resolve(pg[0][2])).toBe(path.resolve(alpha.tcsAbs));
    const rec = await psql(`select project_id, status from console.import_records where id = ${sqlq(importId)}`);
    expect(rec[0]).toEqual([pid, "IMPORTED"]);
    await signProject(request, pid);
    // 列 14：engines/sdd?projectId=
    const s = await statusOf(request, `?projectId=${pid}`);
    expect(s.available).toBe(true);
    expect(s.projects.map((x) => x.project)).toContain(alpha.name);
    const f = s.fsm!;
    expect(f.fsmProject).toBe(alpha.name);
    expect(f.currentState).toBe("SPEC_FROZEN");
    expect(f.phase, "T-G 接線後 phase 非 null").toEqual({ name: "FROZEN", order: 4, blocking: false, observation: false });
    expect(f.escalationHistory).toEqual([]);
    expect(f.escalationProvenance ?? null).toBeNull();
    expect(f.recovery ?? null).toBeNull();
    expect((await engines(request, "?projectId=00000000-0000-4000-8000-000000000000")).status).toBe(404);
    expect((await engines(request, "?projectId=abc")).status).toBe(400);
    expect((await engines(request, `?projectId=${pid}`, "viewer")).status).toBe(200);
    const outsideRoot = path.join(path.dirname(E2E_ROOT), `e2e17-outside-${RUN}`);
    mkdirSync(outsideRoot, { recursive: true });
    const pOut = await consoleProject(request, `e2e17-outside-${RUN}`, outsideRoot);
    const so5 = await statusOf(request, `?projectId=${pOut}`);
    expect({ available: so5.available, reason: so5.reason, projects: so5.projects, fsm: so5.fsm }).toEqual({ available: true, reason: "sdd_root_rejected", projects: [], fsm: null });
  });

  test("列 9＋10＋11＋12｜併入與匯入的錯誤、spec_file 選檔、未映射 AT 出聲、凍結後改檔編譯 fail-closed", async ({ request }) => {
    // 列 9 ①②
    const alpha = ctx.alpha!;
    const pid = ctx.pid!;
    const r1 = await importParse(request, { root: alpha.root, targetProjectId: "00000000-0000-4000-8000-000000000000" });
    expect(r1.parse.status).toBe(404);
    const r2 = await importParse(request, { root: path.join(E2E_ROOT, "projects"), targetProjectId: pid });
    expect(r2.parse.status, JSON.stringify(r2.parse.json)).toBe(409);
    expect(errOf(r2.parse).reason).toBe("sdd_binding_conflict");
    expect(errOf(r2.parse).details).toMatchObject({ cause: "request_differs_from_target", field: "executionPath" });
    // 列 9 ③：不帶 targetProjectId、規格根＝alpha 根：parse 200；signoff 後 confirm → 409 already_bound_elsewhere，且沒有建立新專案
    const projectCount = async () => Number((await psql("select count(*) from console.projects"))[0][0]);
    const projectsBefore = await projectCount();
    const r3 = await importParse(request, { root: alpha.root, specDir: alpha.contracts, specFile: alpha.tcsName });
    expect(r3.parse.status, JSON.stringify(r3.parse.json).slice(0, 400)).toBe(200);
    expect((await call(request, "operator", "POST", `/api/v1/import/${r3.importId}/signoff`, { approver: "operator" })).status).toBe(200);
    const c3 = await call(request, "operator", "POST", `/api/v1/import/${r3.importId}/confirm`);
    expect(c3.status, JSON.stringify(c3.json).slice(0, 400)).toBe(409);
    expect(errOf(c3).reason).toBe("sdd_binding_conflict");
    expect(errOf(c3).details).toMatchObject({ cause: "already_bound_elsewhere" });
    expect(await projectCount(), "沒有建立新專案").toBe(projectsBefore);
    // 列 9 ④：帶 targetProjectId＝P1 parse 並 signoff 後，先把 P1 改綁別的，再 confirm → 409 target_bound_differently；P1 的目標與任務數不變；之後改回
    const goalTaskCounts = async () =>
      (
        await psql(
          `select (select count(*) from console.goals where project_id = ${sqlq(pid)}), (select count(*) from console.tasks where goal_id in (select id from console.goals where project_id = ${sqlq(pid)}))`,
        )
      )[0];
    const countsBefore = await goalTaskCounts();
    const r4 = await importParse(request, { root: alpha.root, targetProjectId: pid, specDir: alpha.contracts, specFile: alpha.tcsName });
    expect(r4.parse.status, JSON.stringify(r4.parse.json).slice(0, 400)).toBe(200);
    expect((await call(request, "operator", "POST", `/api/v1/import/${r4.importId}/signoff`, { approver: "operator" })).status).toBe(200);
    expect((await call(request, "operator", "PUT", `/api/v1/projects/${pid}/sdd-binding`, { sddProject: "other" })).status).toBe(200);
    const c4 = await call(request, "operator", "POST", `/api/v1/import/${r4.importId}/confirm`);
    expect(c4.status, JSON.stringify(c4.json).slice(0, 400)).toBe(409);
    expect(errOf(c4).reason).toBe("sdd_binding_conflict");
    expect(errOf(c4).details).toMatchObject({ cause: "target_bound_differently" });
    expect(await goalTaskCounts(), "P1 的目標與任務數不變").toEqual(countsBefore);
    expect((await call(request, "operator", "PUT", `/api/v1/projects/${pid}/sdd-binding`, { sddProject: alpha.name })).status).toBe(200);
    expect((await projectOf(request, pid)).sddProject, "P1 已改回原綁定").toBe(alpha.name);
    // 列 10：two-tcs
    const one = makeFixture("two-tcs", "e2e17-two", "TCS-One-x.md", ONE_ROW(1));
    makeFixture("two-tcs", "e2e17-two", "TCS-Two-x.md", [["AC-001-1", "AT-001-1-1", "Unit", "[AT_OK_2]"]]);
    // 契約夾具清單：`two-tcs/` 的 FSM 專案 e2e17-two 已凍結（凍結的是被選中的那份 TCS-One）；不凍結的話 ② 會先卡在 spec_not_frozen
    await walkToHumanPending(one.root, one.name);
    const fzTwo = await bridge("POST", `/sdd/fsm/${one.name}:freeze`, { token: TOKEN, body: { root: one.root, docs: [one.tcsRel], approver: "operator", reason: "E2E 核准" } });
    expect(fzTwo.status, fzTwo.text).toBe(200);
    const parseTwo = async (opts: { specDir?: string; specFile?: string }) => (await importParse(request, { root: one.root, ...opts })).parse;
    const p10a = await parseTwo({ specDir: one.contracts });
    expect(p10a.status, JSON.stringify(p10a.json)).toBe(422);
    expect(errOf(p10a).details).toMatchObject({ bridgeReason: "spec_ambiguous" });
    const p10b = await parseTwo({ specDir: one.contracts, specFile: "TCS-One-x.md" });
    expect(p10b.status, JSON.stringify(p10b.json).slice(0, 400)).toBe(200);
    const parsedTwo = dataOf<{ parsedResult: { goals: Array<{ tasks: unknown[] }>; sddSpecFile?: string } }>(p10b).parsedResult;
    expect(
      parsedTwo.goals.flatMap((g) => g.tasks),
      "任務只含被選中那份 TCS 的 AT",
    ).toHaveLength(1);
    expect(path.resolve(parsedTwo.sddSpecFile ?? ""), "sddSpecFile 是選中那份的絕對路徑").toBe(path.resolve(one.tcsAbs));
    const p10c = await parseTwo({ specDir: one.contracts, specFile: "../escape.md" });
    expect(p10c.status).toBe(422);
    expect(errOf(p10c).details).toMatchObject({ bridgeReason: "sanitization_failed" });
    const p10d = await parseTwo({ specDir: one.contracts, specFile: "nope.md" });
    expect(p10d.status).toBe(422);
    expect(errOf(p10d).details).toMatchObject({ bridgeReason: "spec_not_found" });
    const p10e = await parseTwo({ specFile: "TCS-One-x.md" });
    expect(p10e.status).toBe(400);
    expect(errOf(p10e).errors?.[0]?.field).toBe("specFile");
    // 列 11：unmapped
    const unmappedText = tcsText([["AC-001-1", "AT-001-1-1", "Unit", "[AT_OK_1]"]], "e2e17-unmapped", {
      map: "| AC-014-2 | 舊編號 | AT-14-2-1 | 首段非三位 | ✅ | Unit | □ |\n",
      blocks: '```gherkin\n# AT-009-1-1\nScenario: 映射表沒有這一列\n  Given 系統就緒\n  When 執行\n  Then 輸出 "[AT_OK_9]"\n```\n\n',
    });
    const um = makeFixture("unmapped", "e2e17-unmapped", "TCS-Unmapped-x.md", ONE_ROW(1), unmappedText);
    await walkToHumanPending(um.root, um.name);
    const fz = await bridge("POST", `/sdd/fsm/${um.name}:freeze`, { token: TOKEN, body: { root: um.root, docs: [um.tcsRel], approver: "operator", reason: "E2E 核准" } });
    expect(fz.status, fz.text).toBe(200);
    const p11 = (await importParse(request, { root: um.root, specDir: um.contracts, specFile: um.tcsName })).parse;
    expect(p11.status, JSON.stringify(p11.json).slice(0, 500)).toBe(200);
    const warn = dataOf<{ warnings: Array<{ code: string; detail: string; location?: string }> }>(p11).warnings.find((w) => w.code === "at_unmapped");
    expect(warn, "warnings 含 at_unmapped").toBeTruthy();
    expect(warn!.detail).toContain("AT-009-1-1");
    expect(warn!.detail).toContain("AT-14-2-1");
    expect(warn!.location).toBe("specDir");
    const c11 = await bridge("POST", "/sdd/compile", { body: { spec_dir: um.contracts, fsm_project: um.name } });
    expect(c11.status, c11.text).toBe(200);
    expect((c11.json as { unmapped_at_ids: string[] }).unmapped_at_ids).toEqual(["AT-14-2-1", "AT-009-1-1"]);
    // 列 12：edit
    const ed = makeFixture("edit", "e2e17-edit", "TCS-Edit-x.md", ONE_ROW(1));
    await walkToHumanPending(ed.root, ed.name);
    const fe = await bridge("POST", `/sdd/fsm/${ed.name}:freeze`, { token: TOKEN, body: { root: ed.root, docs: [ed.tcsRel], approver: "operator", reason: "E2E 核准" } });
    expect(fe.status, fe.text).toBe(200);
    writeFileSync(ed.tcsAbs, ed.text + "\n改一個字元\n", "utf-8");
    const c12 = await bridge("POST", "/sdd/compile", { body: { spec_dir: ed.contracts, fsm_project: ed.name } });
    expect(c12.status, c12.text).toBe(409);
    expect(c12.json.reason).toBe("spec_digest_changed");
    expect((c12.json.detail as { pair?: string } | undefined)?.pair ?? (c12.json as { pair?: string }).pair).toBe("frozen_vs_file");
    const p12b = (await importParse(request, { root: ed.root, specDir: ed.contracts })).parse;
    expect(p12b.status, JSON.stringify(p12b.json).slice(0, 400)).toBe(422);
    expect(errOf(p12b).details).toMatchObject({ bridgeReason: "spec_digest_changed" });
    const p12c = (await importParse(request, { root: ed.root })).parse;
    expect(p12c.status, "不帶 specDir 以 executionPath 探測：同樣 fail-closed").toBe(422);
    expect(errOf(p12c).details).toMatchObject({ bridgeReason: "spec_digest_changed" });
    writeFileSync(ed.tcsAbs, ed.text, "utf-8");
    const p12d = (await importParse(request, { root: ed.root, specDir: ed.contracts })).parse;
    expect(p12d.status, "還原後回 200").toBe(200);
  });

  test("列 13｜專案名規則與原名等價（S-10）：CJK＋空白、a:b↔a_b；project 參數 201 字元與 NUL 回 400", async ({ request }) => {
    const names = path.join(SUITE, "names");
    mkdirSync(names, { recursive: true });
    expect((await sdd(names, "show", "--project", "訂單系統 v2")).rc).toBe(0);
    expect((await sdd(names, "show", "--project", "a:b")).rc).toBe(0);
    const list = await bridge("GET", `/sdd/fsm?root=${encodeURIComponent(names)}`);
    const projects = (list.json as { projects: Array<{ project: string }>; errors: string[] }).projects.map((p) => p.project);
    expect(projects.sort()).toEqual(["a_b", "訂單系統 v2"].sort());
    expect((list.json as { errors: string[] }).errors).toEqual([]);
    const cjk = await bridgeFsm("訂單系統 v2", names);
    expect(cjk.status, cjk.text).toBe(200);
    expect((cjk.json as { fsm_project: string }).fsm_project).toBe("訂單系統 v2");
    const colon = await bridgeFsm("a:b", names);
    const under = await bridgeFsm("a_b", names);
    expect([colon.status, under.status]).toEqual([200, 200]);
    expect([(colon.json as { project: string }).project, (colon.json as { fsm_project: string }).fsm_project, (under.json as { fsm_project: string }).fsm_project]).toEqual(["a:b", "a_b", "a_b"]);
    const pidCjk = await consoleProject(request, "訂單系統 v2", names);
    const viaConsole = await statusOf(request, `?projectId=${pidCjk}`);
    expect(viaConsole.fsm?.fsmProject).toBe("訂單系統 v2");
    for (const bad of ["x".repeat(201), "a%00b"]) {
      const r = await engines(request, `?project=${bad.includes("%") ? bad : encodeURIComponent(bad)}`);
      expect(r.status, bad.slice(0, 12)).toBe(400);
      expect(errOf(r).errors?.[0]?.field).toBe("project");
    }
  });

  test("列 15＋16＋17｜SDD 批次成功路徑（C3／C4）、追溯覆蓋（C5）、四源對拍（NFR-OBS-01）；畫面：RTM 面板與 SDD 卡（UI-SDD-02／03）", async ({ page, request }) => {
    const alpha = ctx.alpha!;
    const pid = ctx.pid!;
    const errors = collectConsoleErrors(page);
    const traceBefore = traceRows().length;
    const started = await execute(request, pid);
    expect(started.status, JSON.stringify(started.json).slice(0, 500)).toBe(201);
    const run = dataOf<RunData>(started);
    ctx.runId = run.id;
    expect(run.warnings ?? [], "成功批次沒有 warnings").toEqual([]);
    // 執行中：FSM 是 AUTOCLAUDE_DELEGATED，playbook_ref＝run:<id>
    const delegated = await waitFsm(alpha.root, alpha.name, "AUTOCLAUDE_DELEGATED", 30_000);
    expect(delegated.autoclaude_delegated_tracking?.playbook_ref).toBe(`run:${run.id}`);
    const live = await bridgeFsm(alpha.name, alpha.root);
    expect((live.json as { current_state: string }).current_state).toBe("AUTOCLAUDE_DELEGATED");
    const rtmEarly = await call(request, "viewer", "GET", `/api/v1/executions/${run.id}/rtm`);
    expect(rtmEarly.status, "進行中的批次沒有報告").toBe(404);
    expect(errOf(rtmEarly).reason).toBe("rtm_not_found");
    const done = await waitRun(request, run.id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000);
    expect(done.status, JSON.stringify(done)).toBe("COMPLETED");
    const final = await waitFsm(alpha.root, alpha.name, "IMPLEMENTATION", 30_000);
    const trace = final.decision_trace.slice(-5).map((t) => [t.from, t.to, t.reason]);
    expect(trace).toEqual([
      ["HUMAN_PENDING", "SPEC_FROZEN", "console-freeze approver=operator; reason=E2E 核准"],
      ["SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED", `console-signoff approver=operator; run=${run.id}`],
      ["TEST_CONTRACT_NEGOTIATED", "IMPLEMENTATION", `console-signoff approver=operator; oracle=${alpha.tcsRel}@${alpha.digest}; basis=import-draft-signoff; r9.20.3=not-satisfied`],
      ["IMPLEMENTATION", "AUTOCLAUDE_DELEGATED", `console-run run=${run.id} START`],
      ["AUTOCLAUDE_DELEGATED", "IMPLEMENTATION", `console-run run=${run.id} COMPLETED`],
    ]);
    // step_id＝sdd-greenfield-at-…（不是 G1-T1）；playbook.yaml 治理欄；引擎子行程環境
    expect(await stepIds(request, run.id)).toEqual(["sdd-greenfield-at-001-1-1", "sdd-greenfield-at-001-1-2", "sdd-greenfield-at-001-2-1", "sdd-greenfield-at-001-2-e-1"]);
    const wsRoot = process.env.E2E_BRIDGE_WORKSPACE ?? path.join(E2E_ROOT, "workspace");
    const runDir = path.join(wsRoot, run.id);
    const playbook = await yamlLoad<{ workflow_type: string; workflow_path: string }>(path.join(runDir, "playbook.yaml"));
    expect(playbook.workflow_type).toBe("aisdlc_sdd");
    expect(path.resolve(playbook.workflow_path)).toBe(path.resolve(alpha.tcsAbs));
    const calls = traceRows()
      .slice(traceBefore)
      .filter((t) => (t.keywords ?? []).some((k) => k.startsWith("[AT_OK_")));
    expect(calls.length, "四個 AT 各一次替身呼叫（第一次就通過）").toBe(4);
    expect(
      new Set(calls.map((t) => JSON.stringify([t.sdd_env?.SDD_PROJECT, t.sdd_env?.SDD_STATE_DIR ?? null, t.sdd_env?.has_write_token]))),
      "引擎子行程環境只有 SDD_PROJECT：沒有狀態目錄指標、沒有權杖",
    ).toEqual(new Set([JSON.stringify([alpha.name, null, false])]));
    const runJson = JSON.parse(readFileSync(path.join(runDir, "run.json"), "utf8")) as { env_keys?: string[] };
    expect(JSON.stringify(runJson.env_keys ?? []).includes("TOKEN"), "run.json 的 env_keys 不含權杖名").toBe(false);
    const leaks = walkFiles(runDir).filter((rel) => readFileSync(path.join(runDir, rel)).includes(Buffer.from(TOKEN, "utf-8")));
    expect(leaks, "run 目錄內搜不到權杖值（BR-33）").toEqual([]);
    // 列 16：RTM 三處逐值相等
    const consoleRtm = await call(request, "viewer", "GET", `/api/v1/executions/${run.id}/rtm`);
    expect(consoleRtm.status, JSON.stringify(consoleRtm.json)).toBe(200);
    const crtm = dataOf<Json>(consoleRtm);
    expect(crtm).toMatchObject({
      scenario: "greenfield",
      specDigest: alpha.digest,
      at: { passed: 4, total: 4, unmapped: 0, pct: 100 },
      ac: { covered: 2, total: 2, pct: 100 },
      failedAtIds: [],
      weakRegexAtIds: [],
      unmappedAtIds: [],
      fullyCovered: true,
      advisory: true,
    });
    const bridgeRtm = await bridge("GET", `/autoclaude/runs/${run.id}/rtm`);
    expect(bridgeRtm.status, bridgeRtm.text).toBe(200);
    expect(bridgeRtm.json).toMatchObject({
      scenario: "greenfield",
      spec_digest: alpha.digest,
      at: { passed: 4, total: 4, unmapped: 0 },
      ac: { covered: 2, total: 2 },
      fully_covered: true,
      advisory: true,
    });
    const yamlFile = walkFiles(runDir).find((rel) => /RTM-COVERAGE-.*\.yaml$/.test(rel));
    expect(yamlFile, "引擎寫了 RTM-COVERAGE-*.yaml").toBeTruthy();
    const rtmYaml = await yamlLoad<{ spec_digest: string; summary: { at_total?: number; total_at?: number; fully_covered: boolean } }>(path.join(runDir, yamlFile!));
    expect(rtmYaml.spec_digest).toBe(alpha.digest);
    expect(rtmYaml.summary.fully_covered).toBe(true);
    // 列 17：四源對拍（FSM 檔／Bridge／Console／PG）
    const bf = (await bridgeFsm(alpha.name, alpha.root)).json as {
      current_state: string;
      fsm_project: string;
      frozen_stages: Array<{ stage: string; spec_doc_digests: Record<string, string>; approved_by: string }>;
      phase: Json | null;
    };
    const cf = (await statusOf(request, `?projectId=${pid}`)).fsm!;
    const stage = final.frozen_stages[final.frozen_stages.length - 1];
    expect([bf.current_state, cf.currentState]).toEqual(["IMPLEMENTATION", "IMPLEMENTATION"]);
    expect(bf.frozen_stages[bf.frozen_stages.length - 1]).toMatchObject({ stage: stage.stage, approved_by: stage.approved_by, spec_doc_digests: stage.spec_doc_digests });
    expect(cf.frozenStages[cf.frozenStages.length - 1]).toMatchObject({ stage: stage.stage, approved_by: stage.approved_by, spec_doc_digests: stage.spec_doc_digests });
    expect(cf.phase).toEqual(bf.phase);
    expect(cf.phase).toEqual({ name: "IMPLEMENTATION", order: 5, blocking: false, observation: false });
    const dbRun = await psql(`select id, status from console.execution_runs where id = ${sqlq(run.id)}`);
    expect(dbRun[0]).toEqual([run.id, "COMPLETED"]);
    expect(delegated.autoclaude_delegated_tracking?.playbook_ref, "FSM playbook_ref 的 run id 等於 PG execution_runs.id").toBe(`run:${dbRun[0][0]}`);
    const dbDigests = await psql(`select distinct pass_criteria_spec->>'specDigest' from console.tasks where goal_id in (select id from console.goals where project_id = ${sqlq(pid)})`);
    expect(dbDigests.flat().filter(Boolean)).toEqual([alpha.digest]);
    const dbBind = await psql(`select sdd_project from console.projects where id = ${sqlq(pid)}`);
    expect(dbBind[0][0]).toBe(alpha.name);
    // 畫面：執行頁 RTM 面板、專案詳情治理區、監控頁 SDD 卡
    await signIn(page, request, "operator");
    await page.goto(`/projects/${pid}/execute`);
    await expect(page.getByTestId("run-number")).toHaveText("Run #1", FIRST_LOAD);
    const panel = page.getByTestId("rtm-panel");
    await expect(panel.getByTestId("rtm-advisory-badge")).toHaveText("諮詢視圖", FIRST_LOAD);
    await expect(panel.getByTestId("rtm-at")).toHaveText("4／4（100.0%）");
    await expect(panel.getByTestId("rtm-ac")).toHaveText("2／2（100.0%）");
    await expect(panel.getByTestId("rtm-scenario")).toHaveText("greenfield");
    await expect(panel.getByTestId("rtm-digest")).toHaveAttribute("title", alpha.digest);
    await page.goto(`/projects/${pid}`);
    await expect(page.getByTestId("project-title")).toHaveText(alpha.name, FIRST_LOAD);
    const gov = page.getByTestId("sdd-governance");
    await expect(gov.getByTestId("sdd-gov-state")).toHaveText("IMPLEMENTATION", FIRST_LOAD);
    await expect(gov.getByTestId("sdd-phase-label")).toHaveText("實作");
    await expect(gov.getByTestId("sdd-gov-frozen")).toHaveText(`已凍結：${stage.stage}（${localTime(stage.frozen_at)}）`);
    await page.goto(`/projects/${pid}/monitor`);
    await expect(page.getByTestId("sdd-card")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("sdd-state")).toHaveText("IMPLEMENTATION", FIRST_LOAD);
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
    console.log(`[w115-sdd] 列 15～17：run ${run.id} COMPLETED；FSM 四跳逐字；RTM 三處相等；四源對拍（FSM／Bridge／Console／PG）一致`);
  });

  test("列 18｜凍結後改檔 → 執行 409（G-06；BR-30）：零副作用、還原後再 execute 回 201（前置改在尚未跑過的專案做，見審查 Q-09）", async ({ request }) => {
    // 契約寫「第 15 列之後 P1 再 execute」，但 P1 的四個任務已 COMPLETED：再 execute 會先在前置檢查 7c 回 409「沒有可執行的任務」（W5 審查 Q-09）。
    // 這裡改用從未執行過的專案（FSM 停在 SPEC_FROZEN）做同一件事；IMPLEMENTATION 態的同一組斷言放在第 19 列恢復之後（任務未完成、可再執行）。
    const gate = makeFixture("digest-gate", "e2e17-gate", `TCS-Gate-${RUN}.md`, ONE_ROW(1));
    const pid = await frozenImportedProject(request, gate);
    await expectDigestGate(request, gate, pid, "SPEC_FROZEN");
    const again = await execute(request, pid);
    expect(again.status, JSON.stringify(again.json).slice(0, 400)).toBe(201);
    const run = dataOf<RunData>(again);
    expect((await waitRun(request, run.id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000)).status).toBe("COMPLETED");
    await waitFsm(gate.root, gate.name, "IMPLEMENTATION", 30_000);
  });

  test("列 19｜失敗路徑與人工恢復（C4；D-115-15）：引擎升級 → ESCALATION → 顯示的指令原樣恢復 → 下一批次 201", async ({ page, request }) => {
    const fail = makeFixture("alpha-fail", "e2e17-alpha-fail", `TCS-AlphaFail-${RUN}.md`, FAIL_ROWS);
    const pid = await frozenImportedProject(request, fail);
    const r1 = await execute(request, pid);
    expect(r1.status, JSON.stringify(r1.json).slice(0, 400)).toBe(201);
    const run1 = dataOf<RunData>(r1);
    const failed = await waitRun(request, run1.id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000);
    expect(failed.status).toBe("FAILED");
    expect(failed.reason ?? "").toMatch(/^引擎升級（ESCALATION）/);
    const esc = await waitFsm(fail.root, fail.name, "ESCALATION", 30_000);
    expect(esc.escalation_provenance?.source).toBe("autoclaude_delegated_failed");
    expect(esc.escalation_history[esc.escalation_history.length - 1].resolved_at ?? null).toBeNull();
    const view = (await statusOf(request, `?projectId=${pid}`)).fsm!;
    expect(view.currentState).toBe("ESCALATION");
    expect(view.phase).toEqual({ name: "BLOCKED", order: 0, blocking: true, observation: false });
    expect(view.escalationProvenance?.source).toBe("autoclaude_delegated_failed");
    expect(view.escalationHistory[view.escalationHistory.length - 1]).toMatchObject(esc.escalation_history[esc.escalation_history.length - 1] as Json);
    expect(view.recovery?.target).toBe("IMPLEMENTATION");
    for (const form of ["powershell", "posix"] as const) {
      const cmd = view.recovery![form];
      expect(cmd).toContain("resume-from-escalation");
      expect(cmd).toContain("--to IMPLEMENTATION");
      expect(cmd).toContain(fail.fsmDir);
    }
    expect((await call(request, "viewer", "GET", `/api/v1/executions/${run1.id}/rtm`)).status, "失敗批次沒有 RTM").toBe(404);
    // 畫面：紅色阻塞橫幅、ESCALATION 區塊、兩段恢復指令
    await signIn(page, request, "operator");
    await page.goto(`/projects/${pid}`);
    await expect(page.getByTestId("project-title")).toHaveText(fail.name, FIRST_LOAD);
    await expect(page.getByTestId("sdd-gov-state")).toHaveText("ESCALATION", FIRST_LOAD);
    await expect(page.getByTestId("sdd-blocked-banner")).toBeVisible();
    await expect(page.getByTestId("sdd-recovery-command-powershell")).toContainText("resume-from-escalation");
    await expect(page.getByTestId("sdd-recovery-command-posix")).toContainText("resume-from-escalation");
    // 監控頁 SDD 卡（專案模式）：同樣的阻塞橫幅與恢復指令（UI-SDD-03）
    await page.goto(`/projects/${pid}/monitor`);
    await expect(page.getByTestId("sdd-card")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("sdd-state")).toHaveText("ESCALATION", FIRST_LOAD);
    await expect(page.getByTestId("sdd-blocked-banner")).toBeVisible();
    await expect(page.getByTestId("sdd-recovery-command-powershell")).toContainText("resume-from-escalation");
    // 恢復前再 execute：409 且零副作用
    const runsBefore = await psql(`select count(*) from console.execution_runs where project_id = ${sqlq(pid)}`);
    const blocked = await execute(request, pid);
    expect(blocked.status).toBe(409);
    expect(errOf(blocked).reason).toBe("sdd_fsm_state_conflict");
    expect(errOf(blocked).details).toMatchObject({ currentState: "ESCALATION" });
    expect((await psql(`select count(*) from console.execution_runs where project_id = ${sqlq(pid)}`))[0][0]).toBe(runsBefore[0][0]);
    // 人在 SDD session 照「卡片顯示的那條指令」恢復（Windows：5.1 的 powershell.exe 跑 BOM＋CRLF 的 .ps1；其餘跑 POSIX 形）
    const placeholder = '"<人工原因>"';
    const reason = "E2E 人工恢復";
    const env = cliEnv(fail.root);
    delete env.SDD_STATE_DIR; // 顯示的指令自帶 SDD_STATE_DIR
    let rc = 1;
    let outText = "";
    if (process.platform === "win32") {
      const script = view.recovery!.powershell;
      expect(script).toContain(placeholder);
      const ps1 = path.join(SUITE, "recover-fail.ps1");
      writeFileSync(ps1, "﻿" + script.replace(placeholder, `"${reason}"`).replace(/\r?\n/g, "\r\n"), { encoding: "utf-8" });
      try {
        const { stdout } = await execFileAsync("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1], { env, encoding: "utf8", timeout: 180_000, windowsHide: true });
        rc = 0;
        outText = stdout;
      } catch (e) {
        const x = e as { code?: number; stdout?: string; stderr?: string };
        rc = typeof x.code === "number" ? x.code : 1;
        outText = `${x.stdout ?? ""}${x.stderr ?? ""}`;
      }
    } else {
      const posix = view.recovery!.posix;
      expect(posix).toContain(placeholder);
      try {
        const { stdout } = await execFileAsync("sh", ["-c", posix.replace(placeholder, `"${reason}"`)], { env, encoding: "utf8", timeout: 180_000 });
        rc = 0;
        outText = stdout;
      } catch (e) {
        const x = e as { code?: number; stdout?: string; stderr?: string };
        rc = typeof x.code === "number" ? x.code : 1;
        outText = `${x.stdout ?? ""}${x.stderr ?? ""}`;
      }
    }
    expect(rc, outText).toBe(0);
    const healed = await fsmOf(fail.root, fail.name);
    expect(healed.current_state).toBe("IMPLEMENTATION");
    expect(healed.escalation_history[healed.escalation_history.length - 1].resolved_at).toBeTruthy();
    expect(String(healed.escalation_history[healed.escalation_history.length - 1].resolution)).toContain(reason);
    expect(healed.escalation_provenance?.source, "恢復後 provenance 不清除").toBe("autoclaude_delegated_failed");
    const after = (await statusOf(request, `?projectId=${pid}`)).fsm!;
    expect(after.currentState).toBe("IMPLEMENTATION");
    expect(after.recovery ?? null).toBeNull();
    await page.goto(`/projects/${pid}`); // 前面停在監控頁；治理區在專案詳情頁
    await expect(page.getByTestId("sdd-gov-state")).toHaveText("IMPLEMENTATION", FIRST_LOAD);
    await expect(page.getByTestId("sdd-blocked-banner")).toHaveCount(0);
    await expectDigestGate(request, fail, pid, "IMPLEMENTATION"); // 列 18 的 IMPLEMENTATION 態版本：恢復後任務仍可執行，改檔 → 409、零副作用、FSM 不動
    const next = await execute(request, pid);
    expect(next.status, "下一個批次可直接啟動").toBe(201);
    expect((await waitRun(request, dataOf<RunData>(next).id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000)).status).toBe("FAILED");
    await waitFsm(fail.root, fail.name, "ESCALATION", 30_000);
  });

  test("列 20｜取消交還控制權（D-115-15；BR-31）：CANCELLED → delegate-exit done（reason …CANCELLED）→ FSM 回 IMPLEMENTATION；再 execute 回 201", async ({ request }) => {
    const cancel = makeFixture("cancel", "e2e17-cancel", `TCS-Cancel-${RUN}.md`, OK_ROWS);
    const pid = await frozenImportedProject(request, cancel);
    const r1 = await execute(request, pid);
    expect(r1.status, JSON.stringify(r1.json).slice(0, 300)).toBe(201);
    const run1 = dataOf<RunData>(r1);
    await waitFsm(cancel.root, cancel.name, "AUTOCLAUDE_DELEGATED", 30_000);
    const c = await call(request, "operator", "POST", `/api/v1/executions/${run1.id}/cancel`);
    expect(c.status, JSON.stringify(c.json).slice(0, 300)).toBe(200);
    expect((await waitRun(request, run1.id, ["COMPLETED", "FAILED", "CANCELLED"], 90_000)).status).toBe("CANCELLED");
    const fsm = await waitFsm(cancel.root, cancel.name, "IMPLEMENTATION", 30_000);
    const last = fsm.decision_trace[fsm.decision_trace.length - 1];
    expect([last.from, last.to, last.reason]).toEqual(["AUTOCLAUDE_DELEGATED", "IMPLEMENTATION", `console-run run=${run1.id} CANCELLED`]);
    const r2 = await execute(request, pid);
    expect(r2.status, JSON.stringify(r2.json).slice(0, 300)).toBe(201);
    const run2 = dataOf<RunData>(r2);
    const again = await waitFsm(cancel.root, cancel.name, "AUTOCLAUDE_DELEGATED", 30_000);
    expect(again.autoclaude_delegated_tracking?.playbook_ref, "第二次 execute 重新 delegate-enter，playbook_ref 換成新 run").toBe(`run:${run2.id}`);
    expect((await waitRun(request, run2.id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000)).status).toBe("COMPLETED");
    await waitFsm(cancel.root, cancel.name, "IMPLEMENTATION", 30_000);
  });

  test("列 21①｜回收點（D-115-15）：外部殺掉引擎行程 → run FAILED、FSM 不動（仍 AUTOCLAUDE_DELEGATED）；再 execute 回 201，軌跡寫回收兩跳、Bridge 稽核記回收", async ({ request }) => {
    const rec = makeFixture("reclaim", "e2e17-reclaim", `TCS-Reclaim-${RUN}.md`, OK_ROWS);
    const pid = await frozenImportedProject(request, rec);
    const r1 = await execute(request, pid);
    expect(r1.status, JSON.stringify(r1.json).slice(0, 300)).toBe(201);
    const run1 = dataOf<RunData>(r1);
    await waitFsm(rec.root, rec.name, "AUTOCLAUDE_DELEGATED", 30_000);
    // 取引擎行程 pid（直讀 Bridge 的 run 快照）後由外部殺掉整棵樹（Windows：taskkill /T /F；其餘平台：SIGKILL 根行程）
    const live = (await bridge("GET", `/autoclaude/runs/${run1.id}`)).json as { pid?: number | null };
    expect(typeof live.pid, "引擎行程存在").toBe("number");
    if (process.platform === "win32") await execFileAsync("taskkill", ["/PID", String(live.pid), "/T", "/F"], { windowsHide: true });
    else process.kill(live.pid as number, "SIGKILL");
    const dead = await waitRun(request, run1.id, ["COMPLETED", "FAILED", "CANCELLED"], 90_000);
    expect(dead.status, JSON.stringify(dead)).toBe("FAILED");
    const stuck = await fsmOf(rec.root, rec.name);
    expect(stuck.current_state, "引擎異常結束：FSM 不動，仍在委派態").toBe("AUTOCLAUDE_DELEGATED");
    expect(stuck.autoclaude_delegated_tracking?.playbook_ref).toBe(`run:${run1.id}`);
    // 再 execute：回收點（舊 run 已是終態）→ 先 delegate-exit done 再 delegate-enter
    const r2 = await execute(request, pid);
    expect(r2.status, JSON.stringify(r2.json).slice(0, 400)).toBe(201);
    const run2 = dataOf<RunData>(r2);
    const after = await poll(
      () => fsmOf(rec.root, rec.name),
      (s) => s.autoclaude_delegated_tracking?.playbook_ref === `run:${run2.id}`,
      `FSM 的 playbook_ref 換成新 run ${run2.id}`,
      30_000,
      1000,
    );
    expect(after.decision_trace.slice(-2).map((t) => [t.from, t.to, t.reason])).toEqual([
      ["AUTOCLAUDE_DELEGATED", "IMPLEMENTATION", `console-run run=${run1.id} RECLAIMED old_status=FAILED by=${run2.id}`],
      ["IMPLEMENTATION", "AUTOCLAUDE_DELEGATED", `console-run run=${run2.id} START`],
    ]);
    const reclaimAudit = auditRows().find((a) => a.event === "sdd_write" && a.verb === "reclaim" && a.run_id === run2.id);
    expect(reclaimAudit, "Bridge 稽核記一筆回收（含舊 run id 與舊終態）").toMatchObject({ old_run_id: run1.id, old_status: "FAILED", result: "ok" });
    expect((await waitRun(request, run2.id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000)).status).toBe("COMPLETED");
    await waitFsm(rec.root, rec.name, "IMPLEMENTATION", 30_000);
  });

  test("列 21②＋22｜外來委派 409（foreign_delegation）與混合批次 warnings（sdd_governance_inactive／mixed_scope）；沒有 SDD 來源任務的專案不帶 warnings", async ({ request }) => {
    // 21②：IMPLEMENTATION 時由人以真 CLI delegate-enter（不帶 playbook-ref）→ execute 409 foreign_delegation，FSM 不動
    const foreign = makeFixture("foreign", "e2e17-foreign", `TCS-Foreign-${RUN}.md`, ONE_ROW(1));
    const pidF = await frozenImportedProject(request, foreign);
    // 契約夾具清單：`foreign/` 只推進到 IMPLEMENTATION——由人以真 CLI 走談判閘，不跑批次（跑完批次任務全完成，再 execute 會先卡在 7c「沒有可執行的任務」）
    const n1 = await sdd(foreign.root, "negotiate-enter", "--project", foreign.name, "--reason", "外來：E2E 談判開始", "--contract-ref", foreign.tcsRel);
    expect(n1.rc, `${n1.out}${n1.err}`).toBe(0);
    const n2 = await sdd(foreign.root, "negotiate-exit", "--project", foreign.name, "--outcome", "agreed", "--reason", "外來：E2E 談判通過");
    expect(n2.rc, `${n2.out}${n2.err}`).toBe(0);
    expect((await fsmOf(foreign.root, foreign.name)).current_state).toBe("IMPLEMENTATION");
    const de = await sdd(foreign.root, "delegate-enter", "--project", foreign.name, "--reason", "外來委派：E2E");
    expect(de.rc, `${de.out}${de.err}`).toBe(0);
    const snap = fsmDirSnapshot(foreign.root);
    const blocked = await execute(request, pidF);
    expect(blocked.status, JSON.stringify(blocked.json).slice(0, 300)).toBe(409);
    expect(errOf(blocked).reason).toBe("sdd_fsm_state_conflict");
    expect(errOf(blocked).details).toMatchObject({ currentState: "AUTOCLAUDE_DELEGATED", cause: "foreign_delegation" });
    expect(fsmDirSnapshot(foreign.root), "Bridge 不碰外來委派").toEqual(snap);
    // 22：混合批次
    const mixed = makeFixture("mixed", "e2e17-mixed", `TCS-Mixed-${RUN}.md`, ONE_ROW(1));
    const pidM = await frozenImportedProject(request, mixed);
    const detail = await projectOf(request, pidM);
    const goalId = detail.goals![0].id;
    const t = await call(request, "operator", "POST", `/api/v1/goals/${goalId}/tasks`, {
      name: "手動任務",
      description: "請輸出 [T9_DONE]",
      passCriteria: "輸出含 [T9_DONE]",
      expectedOutputRegex: "\\[T9_DONE\\]",
      maxRetries: 1,
      draft: false,
    });
    expect(t.status, JSON.stringify(t.json)).toBe(201);
    const snapM = fsmDirSnapshot(mixed.root);
    const rm = await execute(request, pidM);
    expect(rm.status, JSON.stringify(rm.json).slice(0, 400)).toBe(201);
    const runM = dataOf<RunData>(rm);
    expect(runM.warnings?.[0]).toMatchObject({ code: "sdd_governance_inactive", cause: "mixed_scope" });
    expect((await waitRun(request, runM.id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000)).status).toBe("COMPLETED");
    const idsM = await stepIds(request, runM.id); // 步驟列在 run 開始後才陸續出現：等終態再讀，並要求非空（空陣列的 every 恆為真）
    expect(idsM, "混合批次的步驟：SDD 來源任務與手動任務各一").toHaveLength(2);
    expect(
      idsM.every((s) => /^G\d+-T\d+$/.test(s)),
      `step_id 是 G<g>-T<t>：${idsM.join("、")}`,
    ).toBe(true);
    expect(fsmDirSnapshot(mixed.root), "混合批次不碰 FSM").toEqual(snapM);
    expect((await call(request, "viewer", "GET", `/api/v1/executions/${runM.id}/rtm`)).status, "沒有治理＝沒有追溯報告").toBe(404);
    // P6：只有手動任務、但 sddProject 已有值
    const manualDir = path.join(E2E_ROOT, "projects", `e2e17-p6-${RUN}`);
    mkdirSync(manualDir, { recursive: true });
    const pid6 = await consoleProject(request, `e2e17-p6-${RUN}`, manualDir);
    const g = await call(request, "operator", "POST", `/api/v1/projects/${pid6}/goals`, { name: "手動目標", passCriteria: "完成", description: "", dependsOn: [], draft: false });
    expect(g.status, JSON.stringify(g.json)).toBe(201);
    const t6 = await call(request, "operator", "POST", `/api/v1/goals/${dataOf<{ id: string }>(g).id}/tasks`, {
      name: "手動任務",
      description: "請輸出 [T1_DONE]",
      passCriteria: "輸出含 [T1_DONE]",
      expectedOutputRegex: "\\[T1_DONE\\]",
      maxRetries: 1,
      draft: false,
    });
    expect(t6.status).toBe(201);
    expect((await call(request, "operator", "PUT", `/api/v1/projects/${pid6}/sdd-binding`, { sddProject: "e2e17-p6" })).status).toBe(200);
    await signProject(request, pid6);
    const r6 = await execute(request, pid6);
    expect(r6.status, JSON.stringify(r6.json).slice(0, 300)).toBe(201);
    const run6 = dataOf<RunData>(r6);
    expect(run6.warnings ?? [], "沒有 SDD 來源任務＝不帶 warnings").toEqual([]);
    expect((await waitRun(request, run6.id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000)).status).toBe("COMPLETED");
    expect(await stepIds(request, run6.id)).toEqual(["G1-T1"]);
  });

  test("列 23｜權限與錯誤形狀（API-EXE-16、API-ENG-02、API-SGN-06、API-PRJ-08）：401／403 與 ApiError 封包的 traceId", async ({ request }) => {
    const pid = ctx.pid!;
    const runId = ctx.runId!;
    const anon = async (method: "GET" | "POST" | "PUT", p: string, data?: unknown) => request.fetch(`${API_URL}${p}`, { method, data, failOnStatusCode: false });
    for (const [m, p] of [
      ["GET", `/api/v1/executions/${runId}/rtm`],
      ["GET", `/api/v1/engines/sdd?projectId=${pid}`],
      ["POST", `/api/v1/projects/${pid}/sdd/freeze`],
      ["PUT", `/api/v1/projects/${pid}/sdd-binding`],
    ] as const) {
      expect((await anon(m, p, m === "GET" ? undefined : {})).status(), `${m} ${p}`).toBe(401);
    }
    expect((await call(request, "viewer", "GET", `/api/v1/executions/${runId}/rtm`)).status).toBe(200);
    expect((await engines(request, `?projectId=${pid}`, "viewer")).status).toBe(200);
    expect((await freezeApi(request, "viewer", pid, { reason: "x", docs: ["a.md"] })).status).toBe(403);
    expect((await call(request, "viewer", "PUT", `/api/v1/projects/${pid}/sdd-binding`, { sddProject: "x" })).status).toBe(403);
    const bad = await freezeApi(request, "operator", pid, { reason: "x", docs: [ctx.alpha!.tcsRel] });
    expect(bad.status).toBe(409);
    expect(errOf(bad).traceId, "ApiError 封包的 traceId 等於 X-Trace-Id").toBe(bad.headers["x-trace-id"]);
    const text = JSON.stringify(bad.json) + JSON.stringify(bad.headers);
    expect(text.includes(TOKEN), "回應不含權杖值").toBe(false);
  });

  test("列 24｜唯讀不變（A1；BR-33）：GET 類端點前後，FSM 狀態目錄內每個檔案的 mtime 與大小完全相同", async ({ request }) => {
    const alpha = ctx.alpha!;
    const names = path.join(SUITE, "names");
    const multi = path.join(SUITE, "multi");
    const stats = (root: string): Record<string, string> => {
      const dir = path.join(root, "build", "reports", "fsm");
      const out: Record<string, string> = {};
      if (!existsSync(dir)) return out;
      for (const n of readdirSync(dir)) {
        const s = statSync(path.join(dir, n));
        out[n] = `${s.mtimeMs}:${s.size}`;
      }
      return out;
    };
    const roots = [alpha.root, names, multi, SDD_DIR];
    const before = roots.map(stats);
    expect(before[0], "alpha 的 FSM 目錄有檔可比").not.toEqual({});
    await bridge("GET", `/sdd/fsm?root=${encodeURIComponent(alpha.root)}`);
    await bridgeFsm(alpha.name, alpha.root);
    await bridgeFsm("訂單系統 v2", names);
    await bridge("GET", `/sdd/fsm?root=${encodeURIComponent(multi)}`);
    await bridge("GET", "/sdd/version");
    await bridge("GET", `/autoclaude/runs/${ctx.runId}/rtm`);
    await engines(request, `?projectId=${ctx.pid}`);
    await engines(request, `?project=${encodeURIComponent(alpha.name)}`);
    await call(request, "viewer", "GET", `/api/v1/executions/${ctx.runId}/rtm`);
    expect(roots.map(stats), "GET 前後 FSM 檔的 mtime 與大小完全相同").toEqual(before);
  });

  test("列 25｜SDD run 的 resume／restore 重驗與權杖（D-115-18）：直打 Bridge 缺／錯權杖皆 403；PAUSED 期間改檔 → resume 409；還原後 resume 200", async ({ request }) => {
    const rs = makeFixture("resume", "e2e17-resume", `TCS-Resume-${RUN}.md`, OK_ROWS);
    const pid = await frozenImportedProject(request, rs);
    const started = await execute(request, pid);
    expect(started.status, JSON.stringify(started.json).slice(0, 300)).toBe(201);
    const run = dataOf<RunData>(started);
    await waitFsm(rs.root, rs.name, "AUTOCLAUDE_DELEGATED", 30_000);
    const pause = await call(request, "operator", "POST", `/api/v1/executions/${run.id}/pause`);
    expect(pause.status, JSON.stringify(pause.json).slice(0, 300)).toBe(200);
    expect((await waitRun(request, run.id, ["PAUSED", "COMPLETED", "FAILED", "CANCELLED"], 90_000)).status, "暫停在步驟邊界").toBe("PAUSED");
    const paused = await fsmOf(rs.root, rs.name);
    expect(paused.current_state, "PAUSED 期間 FSM 仍在委派態").toBe("AUTOCLAUDE_DELEGATED");
    expect(paused.autoclaude_delegated_tracking?.playbook_ref).toBe(`run:${run.id}`);
    const snap = fsmDirSnapshot(rs.root);
    const runState = async () => (await bridge("GET", `/autoclaude/runs/${run.id}`)).json as { status: string; pid: number | null };
    // 直打 Bridge：:resume 與 /restore 各做 ① 不帶權杖 ② 帶錯值 → 四次皆 403 sdd_write_forbidden；run 仍 PAUSED、沒有 spawn（pid 為 null）、FSM 檔不變
    const wrong = "wrong-token-value-for-qa-0123456789abcdefghij";
    for (const token of [null, wrong]) {
      const a = await bridge("POST", `/autoclaude/runs/${run.id}:resume`, { token });
      expect([a.status, a.json.reason], a.text).toEqual([403, "sdd_write_forbidden"]);
      const b = await bridge("POST", `/autoclaude/runs/${run.id}/restore`, { token, body: { checkpoint_id: "none" } });
      expect([b.status, b.json.reason], b.text).toEqual([403, "sdd_write_forbidden"]);
    }
    expect(await runState()).toMatchObject({ status: "PAUSED", pid: null });
    expect(fsmDirSnapshot(rs.root), "被拒的 resume／restore 沒碰 FSM").toEqual(snap);
    // 規格檔末尾加一行 → Console resume → 409 sdd_spec_digest_changed（frozen_vs_file）；run 維持 PAUSED、沒有 spawn
    writeFileSync(rs.tcsAbs, rs.text + "\n暫停期間多的一行\n", "utf-8");
    try {
      const r1 = await call(request, "operator", "POST", `/api/v1/executions/${run.id}/resume`);
      expect(r1.status, JSON.stringify(r1.json).slice(0, 400)).toBe(409);
      expect(errOf(r1).reason).toBe("sdd_spec_digest_changed");
      expect(errOf(r1).details).toMatchObject({ pair: "frozen_vs_file" });
      expect(await runState()).toMatchObject({ status: "PAUSED", pid: null });
      expect(fsmDirSnapshot(rs.root)).toEqual(snap);
    } finally {
      writeFileSync(rs.tcsAbs, rs.text, "utf-8");
    }
    // 還原後 resume → 200；FSM 沿用同一個委派（沒有新增軌跡）；console-api 有附權杖，所以這一步成功本身就是權杖附上的證據
    const r2 = await call(request, "operator", "POST", `/api/v1/executions/${run.id}/resume`);
    expect(r2.status, JSON.stringify(r2.json).slice(0, 400)).toBe(200);
    const resumed = await fsmOf(rs.root, rs.name);
    expect(resumed.current_state).toBe("AUTOCLAUDE_DELEGATED");
    expect(resumed.autoclaude_delegated_tracking?.playbook_ref).toBe(`run:${run.id}`);
    expect(resumed.decision_trace.length, "resume 沒有新增軌跡").toBe(paused.decision_trace.length);
    expect((await waitRun(request, run.id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000)).status).toBe("COMPLETED");
    await waitFsm(rs.root, rs.name, "IMPLEMENTATION", 30_000);
  });
});
