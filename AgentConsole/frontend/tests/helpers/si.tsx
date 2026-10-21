/**
 * SelfImproving 唯讀鏡像頁（P1b）元件測試的共用輔助（TCS-SelfImprovingMirror-P1b §5.4）：
 *  - GA／GB：狀態 A／B 的 camelCase 黃金檔（tests/fixtures/si/，與 Bridge 與 backend 的副本逐位元組相同；真 `si export` 輸出經 R9 對映）；
 *  - renderSi：以真 Providers（AuthProvider＋預設 QueryClient，預設對 5xx 重試一次——SI 查詢必須自己覆寫）渲染 SiView，
 *    以 saveSession 設定角色，以 fetch 替身依網址回放黃金檔，並記錄每次呼叫的方法與網址。
 * 回放的 since／limit 語意與 CLI 相同：`since` 是嚴格大於的游標（取項目 ID 的數字部分，事件取 seq），`limit` 是單頁筆數；
 * 回應帶 truncated 與 nextSince（末頁為 false 與 null）。ne／problems 原樣隨每一頁回傳。
 * 不被 vitest 收集、不在 design-rules 掃描面（tests/ 目錄；沿 tests/helpers/api.tsx 與 sddFixtures.ts 先例）。
 */
import { render, type RenderResult } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { vi } from "vitest";

import { SiView } from "@/components/domain/si/SiView";
import { Providers } from "@/components/providers/Providers";
import type { Role, SiEvent, SiObservationRow, SiPage, SiProposal, SiRun, SiStatusItem } from "@/lib/api/types";
import { clearSession, resetSessionCache, saveSession } from "@/lib/auth/store";
import { envelope, failure } from "./api";

export type SiFixture = {
  observations: SiPage<SiObservationRow>;
  events: SiPage<SiEvent>;
  proposals: SiPage<SiProposal>;
  runs: SiPage<SiRun>;
  status: SiPage<SiStatusItem>;
  /** 單筆提案（只有 A 檔有；缺席時由 proposals 依 id 取） */
  proposalOne?: SiPage<SiProposal>;
};

function loadFixture(name: "A" | "B"): SiFixture {
  return JSON.parse(readFileSync(path.join(process.cwd(), "tests", "fixtures", "si", `${name}.camel.json`), "utf-8")) as SiFixture;
}

export const GA: SiFixture = loadFixture("A");
export const GB: SiFixture = loadFixture("B");

/** 深拷貝（測試要改寫資料時用，不污染共用的 GA／GB）。 */
export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export type SiCall = { method: string; url: string; path: string; query: URLSearchParams; hasBody: boolean };
export type SiEndpoint = "status" | "observations" | "events" | "proposals" | "proposal" | "runs";
/** 逐端點覆寫：回 Response（原樣）、或回 { status, data }（包成封包）；回 undefined＝照黃金檔回放。可為 async（延遲回應）。 */
export type SiOverride = (call: SiCall) => Response | { status?: number; data?: unknown } | undefined | Promise<Response | { status?: number; data?: unknown } | undefined>;

export type SiStub = {
  /** 目前回放的資料；測試可在中途換成 GB 或改寫副本 */
  fixture: SiFixture;
  overrides: Partial<Record<SiEndpoint, SiOverride>>;
  calls: SiCall[];
};

/** 503 `si_unavailable` 的後端錯誤封包（details 帶 Bridge 的 cause 與 detail，逐字轉出）。 */
export function siUnavailable(cause = "nonzero_rc", detail = "rc=2; stderr=boom 全形字元"): Response {
  return failure(503, { message: "SI 資料面不可用", reason: "si_unavailable", details: { cause, detail } });
}

/** 404 `si_not_found`（單筆查無，details.id）。 */
export function siNotFound(id: string): Response {
  return failure(404, { message: "查無此筆", reason: "si_not_found", details: { id } });
}

/** 項目的游標數字：ID 的尾數（OBS-SI-012→12）、事件取 seq、壞列取原文裡的 ID。 */
function cursorOf(item: Record<string, unknown>): number {
  if (typeof item.seq === "number") return item.seq;
  const text = typeof item.id === "string" ? item.id : typeof item.raw === "string" ? item.raw : "";
  const m = /(?:OBS|PROP|RUN)-SI-(\d+)/.exec(text);
  return m ? Number(m[1]) : 0;
}

/** 依 since（嚴格大於）與 limit 切一頁；回應的其餘欄位（ne、problems、generatedAt、headSha…）原樣。 */
function pageOf<T>(source: SiPage<T>, query: URLSearchParams): SiPage<T> {
  const since = query.has("since") ? Number(query.get("since")) : -Infinity;
  const limit = query.has("limit") ? Number(query.get("limit")) : Infinity;
  const after = source.items.filter((item) => cursorOf(item as Record<string, unknown>) > since);
  const items = after.slice(0, limit);
  const truncated = after.length > items.length;
  return { ...source, items, truncated, nextSince: truncated ? cursorOf(items[items.length - 1] as Record<string, unknown>) : null };
}

function endpointOf(pathname: string): { endpoint: SiEndpoint; id?: string } | null {
  const m = /^\/api\/v1\/si\/(status|observations|events|proposals|runs)(?:\/([^/]+))?$/.exec(pathname);
  if (!m) return null;
  if (m[1] === "proposals" && m[2]) return { endpoint: "proposal", id: decodeURIComponent(m[2]) };
  return { endpoint: m[1] as SiEndpoint };
}

function replay(stub: SiStub, endpoint: SiEndpoint, id: string | undefined, query: URLSearchParams): Response {
  const f = stub.fixture;
  switch (endpoint) {
    case "status":
      return envelope(f.status);
    case "observations":
      return envelope(pageOf(f.observations, query));
    case "events":
      return envelope(pageOf(f.events, query));
    case "proposals":
      return envelope(pageOf(f.proposals, query));
    case "runs":
      return envelope(pageOf(f.runs, query));
    case "proposal": {
      const source = f.proposalOne ?? f.proposals;
      const items = source.items.filter((p) => p.id === id);
      return items.length > 0 ? envelope({ ...source, items, truncated: false, nextSince: null }) : siNotFound(id ?? "");
    }
  }
}

/** 以 fetch 替身取代全域 fetch：每次呼叫先記錄，再依覆寫或黃金檔回應。 */
export function stubSiApi(stub: SiStub): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init: RequestInit = {}) => {
      const url = new URL(input, "http://api.test");
      const call: SiCall = { method: init.method ?? "GET", url: url.pathname + url.search, path: url.pathname, query: url.searchParams, hasBody: init.body !== undefined && init.body !== null };
      stub.calls.push(call);
      const target = endpointOf(url.pathname);
      if (!target) return failure(404, { message: `測試沒有處理 ${call.method} ${call.url}` });
      const override = stub.overrides[target.endpoint];
      const reply = override ? await override(call) : undefined;
      if (reply instanceof Response) return reply;
      if (reply) return envelope(reply.data, reply.status ?? 200);
      return replay(stub, target.endpoint, target.id, url.searchParams);
    }),
  );
}

/** 寫入已登入狀態（sessionStorage）。 */
export function signInAs(role: Role = "OPERATOR", username = "operator"): void {
  resetSessionCache();
  clearSession();
  saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role, username });
}

export type RenderSiOptions = { role?: Role; fixture?: SiFixture; overrides?: SiStub["overrides"] };

/** 渲染 SiView（真 Providers）；回傳 testing-library 的結果加上 stub（中途換資料、改覆寫）與 urls()（已發出的網址）。 */
export function renderSi(options: RenderSiOptions = {}): RenderResult & { stub: SiStub; urls: () => string[] } {
  const stub: SiStub = { fixture: options.fixture ?? GA, overrides: { ...options.overrides }, calls: [] };
  signInAs(options.role ?? "OPERATOR");
  stubSiApi(stub);
  const view = render(
    <Providers>
      <SiView />
    </Providers>,
  );
  return { ...view, stub, urls: () => stub.calls.map((c) => c.url) };
}
