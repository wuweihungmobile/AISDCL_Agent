import { execFile, spawn, type ChildProcess } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { createServer, type Server } from "node:http";
import path from "node:path";
import { promisify } from "node:util";

import { expect, type APIRequestContext } from "@playwright/test";

import { E2E_ROOT, call, dataOf, type Fixture } from "./realBackend";

/**
 * W7 收斂波複驗（契約 v1.3／v1.4、E2E-14～E2E-16）共用的小工具：
 *  - 假模型伺服器（E2E-14：引擎的 Brain 校正／演化提案／目標驗證請求，依 messages[0].content 分類，立即回應）；
 *  - YAML 讀寫：node_modules 沒有直接相依的 YAML 套件（只有 js-yaml 的傳遞相依、無型別），所以走根層 .venv 的 PyYAML（Bridge 與引擎本來就用它），
 *    磁碟上的引擎設定檔「用 YAML 解析器讀，不比對文字」（契約 E2E-14 前置）；
 *  - 變體 Bridge（E2E-15／16：另起 18082～18086，環境同契約 §5.0.1，但純檔案模式、各自的工作區，不碰共用的 18081）；
 *  - 目錄 mtime 快照（E2E-15 第 11 列：Bridge 與 console-api 都不改動 SDD 目錄）。
 */
const execFileAsync = promisify(execFile);

export const REPO_ROOT = path.resolve(process.cwd(), "..", "..");
export const REPO_PY = path.join(REPO_ROOT, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
export const BRIDGE_DIR = path.resolve(process.cwd(), "..", "engine-bridge");
export const MOCK_CLAUDE = path.join(REPO_ROOT, ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");
/** 本機 monorepo 內 AISDLC_SDD 的最新版本目錄名（目錄名「數字」最大者，與 Bridge 的探索語意相同；LATEST 不寫死在 spec 裡）；找不到回 null。 */
export function realSddLatest(): string | null {
  const dir = path.join(REPO_ROOT, "AISDLC_SDD");
  if (!existsSync(dir)) return null;
  let best: { key: [number, number]; name: string } | null = null;
  for (const name of readdirSync(dir)) {
    const m = /^AISDLC_SDD_v(\d+)\.(\d+)$/.exec(name);
    if (!m || !statSync(path.join(dir, name)).isDirectory()) continue;
    const key: [number, number] = [Number(m[1]), Number(m[2])];
    if (!best || key[0] > best.key[0] || (key[0] === best.key[0] && key[1] > best.key[1])) best = { key, name };
  }
  return best?.name ?? null;
}

/** 真實的 FSM 狀態檔（被 git 忽略，乾淨 clone 沒有）；找不到 AISDLC_SDD 時是空字串。 */
export const REAL_FSM = ((): string => {
  const latest = realSddLatest();
  return latest ? path.join(REPO_ROOT, "AISDLC_SDD", latest, "build", "reports", "fsm", "FSM-STATE-AISDLC_SDD.yaml") : "";
})();

// ── YAML（經 PyYAML；一律 UTF-8） ────────────────────────────────────────────────────────────────────────────────

/** 讀 YAML 檔並轉成 JS 值（safe_load → JSON）。日期時間字面保持字串（YAML 1.1 的 timestamp 會被 PyYAML 轉成 datetime，這裡以 isoformat 輸出）。 */
export async function yamlLoad<T = unknown>(file: string): Promise<T> {
  const code = [
    "import sys, json, yaml, datetime",
    "def enc(o):",
    "    if isinstance(o, (datetime.datetime, datetime.date)): return o.isoformat()",
    "    raise TypeError(type(o))",
    "with open(sys.argv[1], 'r', encoding='utf-8') as fh:",
    "    data = yaml.safe_load(fh)",
    "sys.stdout.buffer.write(json.dumps(data, ensure_ascii=False, default=enc).encode('utf-8'))",
  ].join("\n");
  const { stdout } = await execFileAsync(REPO_PY, ["-X", "utf8", "-c", code, file], { timeout: 30_000, encoding: "buffer", maxBuffer: 16 * 1024 * 1024 });
  return JSON.parse(stdout.toString("utf-8")) as T;
}

/** 把 JS 值寫成 YAML 檔（safe_dump，保序、允許非 ASCII）；字串型的時間戳以原樣單引號輸出，讀回仍是字串。 */
export async function yamlDump(file: string, data: unknown): Promise<void> {
  mkdirSync(path.dirname(file), { recursive: true });
  const code = [
    "import sys, json, yaml",
    "data = json.loads(sys.stdin.buffer.read().decode('utf-8'))",
    "with open(sys.argv[1], 'w', encoding='utf-8', newline='\\n') as fh:",
    "    yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)",
  ].join("\n");
  await new Promise<void>((resolve, reject) => {
    const child = spawn(REPO_PY, ["-X", "utf8", "-c", code, file], { stdio: ["pipe", "ignore", "pipe"], windowsHide: true });
    let err = "";
    child.stderr.on("data", (c: Buffer) => (err += c.toString("utf-8")));
    child.on("error", reject);
    child.on("exit", (rc) => (rc === 0 ? resolve() : reject(new Error(`yamlDump rc=${rc}：${err}`))));
    child.stdin.end(Buffer.from(JSON.stringify(data), "utf-8"));
  });
}

// ── 假模型伺服器（E2E-14） ───────────────────────────────────────────────────────────────────────────────────────

export type ModelRequestKind = "correction" | "evolution" | "goal" | "other";
export type ModelRequest = { at: number; kind: ModelRequestKind; auth: string | null; system: string; body: Record<string, unknown> };

/** 契約 E2E-14：用請求 JSON 的 messages[0].content（system 訊息）分類。 */
export function classifyModelRequest(system: string): ModelRequestKind {
  if (system.includes("correction_prompt")) return "correction";
  if (system.includes("evolution_type")) return "evolution";
  if (system.includes("is_achieved")) return "goal";
  return "other";
}

/**
 * 假的 OpenAI／MiniMax 相容伺服器：立即回應（契約要求不得掛住或延遲），記下每個請求並分類。
 * status＝要回的 HTTP 狀態（200 回一個結構合法但內容空泛的回應；500 讓引擎走重試與失敗路徑）。
 */
export class FakeModelServer {
  readonly requests: ModelRequest[] = [];
  status = 200;
  port = 0;
  private server: Server | null = null;

  get endpoint(): string {
    return `http://127.0.0.1:${this.port}/v1/chat/completions`;
  }

  count(kind?: ModelRequestKind): number {
    return kind ? this.requests.filter((r) => r.kind === kind).length : this.requests.length;
  }

  reset(): void {
    this.requests.length = 0;
  }

  async listen(): Promise<void> {
    this.server = createServer((req, res) => {
      const chunks: Buffer[] = [];
      req.on("data", (c: Buffer) => chunks.push(c));
      req.on("end", () => {
        let body: Record<string, unknown> = {};
        try {
          body = JSON.parse(Buffer.concat(chunks).toString("utf-8")) as Record<string, unknown>;
        } catch {
          body = {};
        }
        const messages = Array.isArray(body.messages) ? (body.messages as Array<{ role?: string; content?: unknown }>) : [];
        const system = typeof messages[0]?.content === "string" ? (messages[0].content as string) : JSON.stringify(messages[0]?.content ?? "");
        this.requests.push({ at: Date.now(), kind: classifyModelRequest(system), auth: (req.headers.authorization as string | undefined) ?? null, system, body });
        const payload =
          this.status === 200
            ? {
                id: "chatcmpl-w7",
                object: "chat.completion",
                model: "e2e-model",
                choices: [{ index: 0, finish_reason: "stop", message: { role: "assistant", content: "{}" } }],
                usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
              }
            : { error: "boom" };
        res.writeHead(this.status, { "content-type": "application/json; charset=utf-8" });
        res.end(JSON.stringify(payload));
      });
    });
    await new Promise<void>((resolve) => this.server!.listen(0, "127.0.0.1", resolve));
    this.port = (this.server!.address() as { port: number }).port;
  }

  async close(): Promise<void> {
    const s = this.server;
    this.server = null;
    if (s) await new Promise<void>((resolve) => s.close(() => resolve()));
  }
}

// ── 檔案系統小工具 ───────────────────────────────────────────────────────────────────────────────────────────────

/** 遞迴列出目錄下的全部檔案（相對路徑，正斜線，排序）。 */
export function walkFiles(dir: string): string[] {
  const out: string[] = [];
  const visit = (d: string, rel: string) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const r = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) visit(path.join(d, e.name), r);
      else out.push(r);
    }
  };
  if (existsSync(dir)) visit(dir, "");
  return out.sort();
}

/** 目錄（遞迴）的 mtime／大小快照：把每個檔案與目錄的 `相對路徑 → mtimeMs:size` 收成一個物件，兩次快照相等＝沒有任何新增、刪除或改寫。 */
export function dirSnapshot(dir: string): Record<string, string> {
  const snap: Record<string, string> = {};
  const visit = (d: string, rel: string) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const r = rel ? `${rel}/${e.name}` : e.name;
      const st = statSync(path.join(d, e.name));
      snap[r + (e.isDirectory() ? "/" : "")] = `${Math.round(st.mtimeMs)}:${e.isDirectory() ? 0 : st.size}`;
      if (e.isDirectory()) visit(path.join(d, e.name), r);
    }
  };
  if (existsSync(dir)) visit(dir, "");
  return snap;
}

/** run 工作區內（契約 §5.0.4 A5）找金鑰明文：回傳含該字串的檔案相對路徑（二進位也以 latin1 比對）。 */
export function filesContaining(dir: string, needle: string): string[] {
  const hits: string[] = [];
  for (const rel of walkFiles(dir)) {
    const buf = readFileSync(path.join(dir, rel));
    if (buf.includes(Buffer.from(needle, "utf-8")) || buf.toString("latin1").includes(needle)) hits.push(rel);
  }
  return hits;
}

export function writeText(file: string, text: string): void {
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, text, { encoding: "utf-8" });
}

// ── 變體 Bridge（純檔案模式，各自的工作區） ───────────────────────────────────────────────────────────────────────

export type VariantBridge = { port: number; url: string; child: ChildProcess; stop: () => Promise<void>; alive: () => boolean };

/** 環境變數副本：清掉引擎相關變數（契約 §5.0.1 第 3 點）；Windows 的 Path 大小寫不一，要先刪掉所有 path 鍵再設單一個。 */
export function cleanBridgeEnv(extra: Record<string, string>): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env };
  for (const k of Object.keys(env)) {
    if (/^(AUTOSDD_|AUTOCLAUDE_|MINIMAX_|MOCK_CLAUDE_|BRIDGE_|ENGINE_|SDD_)/.test(k) || k.toLowerCase() === "path") delete env[k];
  }
  return { ...env, ...extra };
}

/** Windows 結束整棵行程樹（Bridge 與它的引擎子行程）；POSIX 直接 kill。 */
export async function killTree(child: ChildProcess): Promise<void> {
  if (child.exitCode !== null || child.pid === undefined) return;
  const exited = new Promise<void>((resolve) => child.once("exit", () => resolve()));
  if (process.platform === "win32") {
    await execFileAsync("taskkill", ["/PID", String(child.pid), "/T", "/F"]).catch(() => undefined);
  } else {
    child.kill("SIGKILL");
  }
  await Promise.race([exited, new Promise<void>((resolve) => setTimeout(resolve, 8_000))]);
}

/**
 * 另起一個 Bridge（`python -m uvicorn app.main:app`，單一 worker，純檔案模式）。
 * root＝這個 Bridge 的專屬根目錄（工作區與允許路徑都在其下）；sddRoot＝SDD_ROOT（不給就不設，Bridge 走預設探索）；
 * emptyPath＝true 時 PATH 只剩一個空目錄（git 解析不到，E2E-16 第 2 列）；otherwise PATH 前置根層 .venv 的 Scripts／bin。
 */
export async function startBridge(opts: { port: number; root: string; instance: string; sddRoot?: string; emptyPath?: boolean; extraEnv?: Record<string, string> }): Promise<VariantBridge> {
  const workspace = path.join(opts.root, "ws");
  mkdirSync(workspace, { recursive: true });
  const venvBin = path.join(REPO_ROOT, ".venv", process.platform === "win32" ? "Scripts" : "bin");
  let pathValue = [venvBin, process.env.PATH ?? process.env.Path ?? ""].join(path.delimiter);
  if (opts.emptyPath) {
    const empty = path.join(opts.root, "empty-bin");
    mkdirSync(empty, { recursive: true });
    pathValue = empty;
  }
  const env = cleanBridgeEnv({
    PATH: pathValue,
    ENGINE_WORKSPACE: workspace,
    BRIDGE_ALLOWED_PATH_ROOTS: opts.root,
    BRIDGE_OUTBOUND_ALLOWLIST: "127.0.0.1,localhost",
    BRIDGE_STOP_GRACE_SECONDS: "5",
    BRIDGE_INSTANCE: opts.instance,
    AUTOSDD_QUOTA_CACHE_DIR: path.join(opts.root, "quota-cache"),
    ...(opts.sddRoot ? { SDD_ROOT: opts.sddRoot } : {}),
    ...(opts.extraEnv ?? {}),
  });
  mkdirSync(path.join(opts.root, "quota-cache"), { recursive: true });
  // 用絕對路徑啟動 python：Windows 的 CreateProcess 以 PATH 解析時，空 PATH 會找不到任何東西
  const child = spawn(REPO_PY, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(opts.port), "--workers", "1"], { cwd: BRIDGE_DIR, env, stdio: "ignore", windowsHide: true });
  const url = `http://127.0.0.1:${opts.port}`;
  for (let i = 0; i < 90; i += 1) {
    if (child.exitCode !== null) throw new Error(`變體 Bridge（${opts.port}）啟動即結束：rc=${child.exitCode}`);
    const ok = await fetch(`${url}/health`)
      .then((r) => r.status === 200)
      .catch(() => false);
    if (ok) break;
    await new Promise((r) => setTimeout(r, 1000));
    if (i === 89) throw new Error(`變體 Bridge（${opts.port}）90 秒內沒有起來`);
  }
  return { port: opts.port, url, child, stop: () => killTree(child), alive: () => child.exitCode === null };
}

// ── 長批次夾具 ───────────────────────────────────────────────────────────────────────────────────────────────────

/** 單一目標、N 個任務的長批次夾具（mock claude 每步約 1 秒，N＝40 約撐 1 分鐘；契約 §5.0.3 的 PRJ-A／B 任務數 ≤ 5，撐不住資源取樣與 EXECUTING 狀態的觀察）。 */
export async function createLongFixture(request: APIRequestContext, name: string, tasks: number): Promise<Fixture> {
  const dir = path.join(E2E_ROOT, "projects", name.replace(/[^A-Za-z0-9_-]/g, "_"));
  mkdirSync(dir, { recursive: true });
  const p = await call(request, "operator", "POST", "/api/v1/projects", { name, executionPath: dir, passCriteria: "全部完成", description: "QA 長批次夾具", autonomyLevel: 4, draft: false });
  expect(p.status, JSON.stringify(p.json)).toBe(201);
  const projectId = dataOf<{ id: string }>(p).id;
  const g = await call(request, "operator", "POST", `/api/v1/projects/${projectId}/goals`, { name: "長批次", passCriteria: "全部完成", description: "", dependsOn: [], draft: false });
  expect(g.status, JSON.stringify(g.json)).toBe(201);
  const goalId = dataOf<{ id: string }>(g).id;
  const taskIds: string[] = [];
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
    taskIds.push(dataOf<{ id: string }>(t).id);
  }
  return { projectId, name, dir, goalIds: [goalId], taskIds };
}
