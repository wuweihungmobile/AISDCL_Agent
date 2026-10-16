import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { type APIRequestContext } from "@playwright/test";

import { API_URL } from "./helpers";
import { tokenOf, type Role } from "./realBackend";

/**
 * W5 修復波複驗（契約 v1.2、E2E-13）共用的小工具：
 *  - 直連 Bridge、讀 Bridge 檔案日誌（C-12）、對 PostgreSQL 容器下 SQL（C-3 的逾期情境要把 deleted_at 撥到 31 天前）；
 *  - 以原始位元組讀 REST 回應（PDF 報表）。
 * 選配環境變數（沒設就略過依賴它們的情境，見 README〈W5 複驗〉）：E2E_BRIDGE_URL、E2E_BRIDGE_LOG（Bridge 的 BRIDGE_LOG_DIR/bridge.log）、
 * E2E_PG_CONTAINER（本機 e2e 的 PostgreSQL 容器名，例 qa-pg；帳密沿用 README 的 aisdlc／aisdlc）。
 */
const execFileAsync = promisify(execFile);

export const BRIDGE_URL = process.env.E2E_BRIDGE_URL ?? "http://127.0.0.1:18081";
export const BRIDGE_LOG = process.env.E2E_BRIDGE_LOG ?? "";
export const PG_CONTAINER = process.env.E2E_PG_CONTAINER ?? "";

/** 對本機 e2e 的 PostgreSQL 容器執行一句 SQL，回傳 psql -t -A 的輸出（去頭尾空白）。 */
export async function psql(sql: string): Promise<string> {
  const { stdout } = await execFileAsync("docker", ["exec", PG_CONTAINER, "psql", "-U", "aisdlc", "-d", "aisdlc", "-t", "-A", "-c", sql], { timeout: 60_000 });
  return stdout.trim();
}

export type RawReply = { status: number; headers: Record<string, string>; body: Buffer };

/** 以角色的 access token 呼叫 REST，回傳原始位元組（報表 PDF 用；call() 會把本文當 JSON 解析）。 */
export async function fetchRaw(request: APIRequestContext, role: Role, apiPath: string, headers: Record<string, string> = {}): Promise<RawReply> {
  const token = await tokenOf(request, role);
  const res = await request.fetch(`${API_URL}${apiPath}`, { method: "GET", headers: { Authorization: `Bearer ${token}`, ...headers }, failOnStatusCode: false });
  return { status: res.status(), headers: res.headers(), body: await res.body() };
}

/** 本週一 00:00（本機時區）轉 ISO-8601——與儀表板「本週完成」的 from 同一算法（契約 §1.3.8）。 */
export function startOfWeekIso(now = new Date()): string {
  const d = new Date(now);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return d.toISOString();
}
