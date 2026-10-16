import { spawn, type ChildProcess } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { E2E_ROOT, NEEDS_BRIDGE, poll } from "./realBackend";
import { BRIDGE_URL } from "./w5";

/**
 * W5 複驗：Bridge 深度探針 GET /health/deep（契約 v1.2 §3.1.1；E2E-13 列 13 的本機半邊；DEF-AC-003、RTM BR-26）。
 *  1) e2e 環境的 Bridge（DB 模式、真 git、真引擎）：200，四項檢查 git／autoclaude／workspace／db 都 ok。
 *  2) 另起一個 Bridge（埠 18082、純檔案模式），PATH 只剩一個空目錄 → git 找不到：/health/deep 503 degraded、checks.git 帶 reason，
 *     而淺層 /health 仍 200（為什麼要有深度探針：DEF-AC-003 時容器永遠 healthy、批次卻一律 FAILED）。
 *  3) 同一個 Bridge 把工作區整個刪掉 → workspace 也帶 reason（與 git 各自獨立失敗）；補回工作區後只剩 git 一項失敗。
 * Docker 側（映像內 git --version、全棧 healthcheck 打這一支、批次跑到 COMPLETED）由 p8-docker-stack.stack.ts 與 QA_W5_Reverification.md §6 的指令驗。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const VARIANT_PORT = 18082;
const VARIANT = `http://127.0.0.1:${VARIANT_PORT}`;
const REPO_PY = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const BRIDGE_DIR = path.resolve(process.cwd(), "..", "engine-bridge");

type Deep = {
  status: string;
  reason?: string;
  checks: { git: { ok: boolean; version?: string; reason?: string }; autoclaude: { ok: boolean; version?: string }; workspace: { ok: boolean; reason?: string }; db: { ok: boolean | null } };
};

async function deep(base: string): Promise<{ status: number; body: Deep; traceId: string | null }> {
  const res = await fetch(`${base}/health/deep`);
  return { status: res.status, body: (await res.json()) as Deep, traceId: res.headers.get("x-trace-id") };
}

/** 環境變數的副本：清掉引擎相關變數（契約 §5.0.1）；Windows 的 Path 大小寫不一，要先刪掉所有 path 鍵再設單一個。 */
function cleanEnv(extra: Record<string, string>): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env };
  for (const k of Object.keys(env)) {
    if (/^(AUTOSDD_|AUTOCLAUDE_|MINIMAX_|MOCK_CLAUDE_|BRIDGE_|ENGINE_)/.test(k) || k.toLowerCase() === "path") delete env[k];
  }
  return { ...env, ...extra };
}

function killTree(child: ChildProcess): Promise<void> {
  return new Promise((resolve) => {
    child.once("exit", () => resolve());
    if (child.exitCode !== null) return resolve();
    child.kill();
    setTimeout(resolve, 5_000);
  });
}

test.describe("Bridge 深度探針 /health/deep（C-2、BR-26）", () => {
  test.setTimeout(180_000);

  test("e2e 環境的 Bridge：200、四項檢查都 ok（git 版本非空、db 為 true）、回應帶 X-Trace-Id；淺層 /health 不變", async () => {
    const r = await deep(BRIDGE_URL);
    expect(r.status, JSON.stringify(r.body)).toBe(200);
    expect(r.body.status).toBe("ok");
    expect(r.body.checks.git.ok).toBe(true);
    expect(r.body.checks.git.version ?? "").toMatch(/^git version \d+\.\d+/);
    expect(r.body.checks.autoclaude).toMatchObject({ ok: true });
    expect(r.body.checks.workspace.ok).toBe(true);
    expect(r.body.checks.db.ok, "DB 模式：有 DSN 時真的 ping").toBe(true);
    expect(r.traceId, "回應帶 X-Trace-Id").toBeTruthy();
    expect(r.body.reason, "200 時沒有頂層 reason").toBeUndefined();
    const shallow = await fetch(`${BRIDGE_URL}/health`);
    expect(shallow.status).toBe(200);
    expect(((await shallow.json()) as { status: string }).status).toBe("ok");
  });

  test("git 找不到（PATH 只剩空目錄）→ 503 degraded、checks.git 帶 reason、淺層 /health 仍 200；之後把工作區刪掉 → 503、workspace 帶 reason", async () => {
    test.skip(!existsSync(REPO_PY), `找不到根層 .venv 的 Python：${REPO_PY}`);
    const root = mkdtempSync(path.join(tmpdir(), "w5qa-bridge-"));
    const workspace = path.join(root, "ws");
    const emptyPath = path.join(root, "empty-path");
    mkdirSync(workspace, { recursive: true });
    mkdirSync(emptyPath, { recursive: true });
    const env = cleanEnv({
      PATH: emptyPath, // 沒有 git
      ENGINE_WORKSPACE: workspace,
      BRIDGE_ALLOWED_PATH_ROOTS: root,
      BRIDGE_OUTBOUND_ALLOWLIST: "127.0.0.1,localhost",
      BRIDGE_INSTANCE: "w5qa-no-git",
    });
    const child = spawn(REPO_PY, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(VARIANT_PORT), "--workers", "1"], {
      cwd: BRIDGE_DIR,
      env,
      stdio: "ignore",
      windowsHide: true,
    });
    try {
      await poll(
        async () =>
          fetch(`${VARIANT}/health`)
            .then((r) => r.status)
            .catch(() => 0),
        (s) => s === 200,
        `變體 Bridge（${VARIANT}）啟動`,
        60_000,
        1000,
      );
      const noGit = await deep(VARIANT);
      expect(noGit.status, JSON.stringify(noGit.body)).toBe(503);
      expect(noGit.body.status).toBe("degraded");
      expect(noGit.body.checks.git.ok).toBe(false);
      expect(noGit.body.checks.git.reason ?? "").toContain("git");
      expect(noGit.body.reason ?? "", "頂層 reason 帶出失敗項").toContain("git:");
      expect(noGit.body.checks.autoclaude.ok).toBe(true);
      expect(noGit.body.checks.workspace.ok).toBe(true);
      expect(noGit.body.checks.db.ok, "純檔案模式沒有 DB：null，不算失敗").toBeNull();
      expect((await fetch(`${VARIANT}/health`)).status, "淺層 /health 仍 200——這正是 DEF-AC-003 當時看不見問題的原因").toBe(200);

      // 工作區不可寫（整個目錄被刪掉）：另一項檢查獨立失敗
      rmSync(workspace, { recursive: true, force: true });
      const noWs = await deep(VARIANT);
      expect(noWs.status).toBe(503);
      expect(noWs.body.checks.workspace.ok).toBe(false);
      expect(noWs.body.checks.workspace.reason ?? "").toContain("工作區不可寫");
      expect(noWs.body.reason ?? "").toContain("workspace:");
      // 補回工作區：只剩 git 一項失敗
      mkdirSync(workspace, { recursive: true });
      const back = await deep(VARIANT);
      expect(back.status).toBe(503);
      expect([back.body.checks.git.ok, back.body.checks.workspace.ok]).toEqual([false, true]);
    } finally {
      await killTree(child);
      rmSync(root, { recursive: true, force: true });
    }
  });
});
